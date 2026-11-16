"use strict";

/**
 * SurroSim desktop shell.
 *
 * Spawns the existing FastAPI service (`python -m surrosim serve`) as a child
 * process of the local repository and opens the built React app in a native
 * window. Everything stays offline: the repository's CalculiX binary, model
 * registries, dataset and reports are resolved at run time.
 *
 * Flags / environment:
 *   SURROSIM_REPO          override the repository root (default: walk up from
 *                          this app until pyproject.toml is found)
 *   SURROSIM_PYTHON        override the Python interpreter (default: .venv)
 *   SURROSIM_PORT          preferred port (default: 8003)
 *   SURROSIM_DESKTOP_DEV=1 load the Vite dev server instead of the built app
 *   --smoke                start, wait for the window to load, exit 0/1 (test)
 */

const { app, BrowserWindow, Menu, dialog, ipcMain, shell } = require("electron");
const { execFile, spawn } = require("child_process");
const fs = require("fs");
const http = require("http");
const net = require("net");
const path = require("path");

const DEV = process.env.SURROSIM_DESKTOP_DEV === "1";
const SMOKE = process.argv.includes("--smoke");
const PREFERRED_PORT = Number(process.env.SURROSIM_PORT || 8003);
const DEV_URL = process.env.SURROSIM_DEV_URL || "http://localhost:5173";
const STARTUP_TIMEOUT_MS = SMOKE ? 120000 : 90000;
const HEALTH_INTERVAL_MS = 400;
const LOG_TAIL_LIMIT = 200;

// DesignKit desktop title bar. The height is declared once here and shared
// with the renderer through the preload bridge, so the bar styles, the native
// window-controls overlay, and the renderer's layout offsets all derive from
// the same number. Initial colors match the default light canvas; the renderer
// syncs the overlay from tokens.css before mounting and whenever theme changes.
const TITLE_BAR_HEIGHT = 42;
const TITLE_BAR_COLORS = { color: "#f6f8fa", symbolColor: "#101214" };

// Model registries are chosen at run time: promoted registries first, then
// the review candidates, then v1. The v2.0.0 promotion only has to land on
// disk — no desktop configuration changes.
const SCALAR_REGISTRIES = [
  "models/scalar/v2",
  "models/scalar/v2_reviewed_candidate",
  "models/scalar/v2_candidate",
  "models/scalar/v1",
];
const FIELD_MODELS = [
  "models/gnn/v2",
  "models/gnn/v2_normalized_candidate",
  "models/gnn/v2_candidate",
  "models/gnn/v1",
];

let mainWindow = null;
let splashWindow = null;
let splashReady = false;
let splashStatus = "Starting SurroSim…";
let backend = null;
let backendPort = null;
let backendExternal = false;
let backendExited = false;
let backendLogStream = null;
let backendLogPath = null;
let quitting = false;
let repoRoot = null;
// name → Menu for the title bar popups; filled by buildMenus().
let popupMenus = new Map();

const logTail = [];

// ---------------------------------------------------------------------------
// Small utilities
// ---------------------------------------------------------------------------

function log(message) {
  const line = `[${new Date().toISOString().slice(11, 19)}] ${message}`;
  logTail.push(line);
  if (logTail.length > LOG_TAIL_LIMIT) logTail.shift();
  if (backendLogStream) backendLogStream.write(`${line}\n`);
  if (!mainWindow) setSplash(message);
}

function tail(count) {
  return logTail.slice(-count).join("\n");
}

function setSplash(text) {
  splashStatus = text;
  if (splashReady && splashWindow && !splashWindow.isDestroyed()) {
    splashWindow.webContents
      .executeJavaScript(`window.__setStatus(${JSON.stringify(text)})`)
      .catch(() => {});
  }
}

function fatal(message, detail) {
  log(`FATAL: ${message}`);
  setSplash(message);
  if (splashWindow && !splashWindow.isDestroyed()) splashWindow.close();
  if (SMOKE) {
    console.error(`SMOKE FAIL: ${message}\n${detail || ""}`);
    app.exit(1);
    return;
  }
  const choice = dialog.showMessageBoxSync({
    type: "error",
    title: "SurroSim",
    message,
    detail: detail || "",
    buttons: ["Open log", "Quit"],
    defaultId: 1,
    cancelId: 1,
  });
  if (choice === 0 && backendLogPath) shell.openPath(backendLogPath);
  app.quit();
}

function findRepoRoot() {
  if (process.env.SURROSIM_REPO) {
    return path.resolve(process.env.SURROSIM_REPO);
  }
  let dir = app.getAppPath();
  for (let i = 0; i < 8; i += 1) {
    if (fs.existsSync(path.join(dir, "pyproject.toml"))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

function findPython(root) {
  const candidates = [];
  if (process.env.SURROSIM_PYTHON) candidates.push(process.env.SURROSIM_PYTHON);
  candidates.push(path.join(root, ".venv", "Scripts", "python.exe"));
  candidates.push(path.join(root, ".venv", "bin", "python"));
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) return candidate;
  }
  return process.platform === "win32" ? "python" : "python3";
}

function resolveRegistry(root, kind) {
  const candidates = kind === "scalar" ? SCALAR_REGISTRIES : FIELD_MODELS;
  for (const relative of candidates) {
    const dir = path.join(root, ...relative.split("/"));
    if (!fs.existsSync(path.join(dir, "metadata.json"))) continue;
    if (kind === "scalar" && !fs.existsSync(path.join(dir, "models"))) continue;
    if (kind === "field" && !fs.existsSync(path.join(dir, "meshgraphnet.pt"))) {
      continue;
    }
    return relative;
  }
  return null;
}

function probePort(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    server.unref();
    server.once("error", () => resolve(null));
    server.listen(port, "127.0.0.1", () => {
      const actual = server.address().port;
      server.close(() => resolve(actual));
    });
  });
}

async function pickPort(preferred) {
  const free = await probePort(preferred);
  if (free) return free;
  const ephemeral = await probePort(0);
  if (!ephemeral) throw new Error("no free TCP port available");
  return ephemeral;
}

function isPortBusy(port) {
  return new Promise((resolve) => {
    const socket = net.connect({ port, host: "127.0.0.1" });
    socket.setTimeout(700);
    socket.once("connect", () => {
      socket.destroy();
      resolve(true);
    });
    const miss = () => {
      socket.destroy();
      resolve(false);
    };
    socket.once("error", miss);
    socket.once("timeout", miss);
  });
}

function healthOk(port) {
  return new Promise((resolve) => {
    const request = http.get(
      { host: "127.0.0.1", port, path: "/api/health", timeout: 2000 },
      (response) => {
        let body = "";
        response.on("data", (chunk) => (body += chunk));
        response.on("end", () => {
          try {
            resolve(response.statusCode === 200 && JSON.parse(body).status === "ok");
          } catch {
            resolve(false);
          }
        });
      },
    );
    request.once("timeout", () => request.destroy());
    request.once("error", () => resolve(false));
  });
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// ---------------------------------------------------------------------------
// Backend process
// ---------------------------------------------------------------------------

function openBackendLog(root) {
  const logDir = path.join(root, "outputs", "desktop");
  fs.mkdirSync(logDir, { recursive: true });
  backendLogPath = path.join(logDir, "backend.log");
  const previous = path.join(logDir, "backend.prev.log");
  if (fs.existsSync(backendLogPath)) {
    try {
      fs.rmSync(previous, { force: true });
      fs.renameSync(backendLogPath, previous);
    } catch {
      /* keep appending if the previous log cannot be rotated */
    }
  }
  backendLogStream = fs.createWriteStream(backendLogPath, { flags: "a" });
}

function startBackend(root, port) {
  const python = findPython(root);
  const scalar = resolveRegistry(root, "scalar");
  const field = resolveRegistry(root, "field");
  if (!scalar) throw new Error("no scalar model registry found under models/scalar");

  openBackendLog(root);
  const args = [
    "-m",
    "surrosim",
    "serve",
    "--host",
    "127.0.0.1",
    "--port",
    String(port),
    "--registry",
    scalar,
  ];
  if (field) args.push("--field-model", field);
  const env = {
    ...process.env,
    PYTHONPATH: [path.join(root, "src"), process.env.PYTHONPATH]
      .filter(Boolean)
      .join(path.delimiter),
    PYTHONUNBUFFERED: "1",
  };

  log(`python: ${python}`);
  log(`registry: ${scalar}${field ? `  field model: ${field}` : ""}`);
  log(`starting service on http://127.0.0.1:${port}`);

  backend = spawn(python, args, { cwd: root, env, windowsHide: true });
  backendPort = port;
  backendExited = false;

  backend.stdout.on("data", (chunk) => {
    for (const line of chunk.toString().split(/\r?\n/)) {
      if (line.trim()) log(line.trim());
    }
  });
  backend.stderr.on("data", (chunk) => {
    for (const line of chunk.toString().split(/\r?\n/)) {
      if (line.trim()) log(line.trim());
    }
  });
  backend.on("error", (error) => {
    fatal("Could not start the Python service", String(error));
  });
  backend.on("exit", (code, signal) => {
    backendExited = true;
    if (quitting) return;
    const detail = `Exit code: ${code === null ? signal : code}\n\n${tail(12)}`;
    if (!mainWindow) {
      // Startup is still in progress; waitForHealth reports the failure.
      log(`backend exited during startup (${code === null ? signal : code})`);
      return;
    }
    if (SMOKE) {
      console.error(`SMOKE FAIL: backend exited\n${detail}`);
      app.exit(1);
      return;
    }
    dialog
      .showMessageBox({
        type: "error",
        title: "SurroSim",
        message: "The SurroSim backend stopped unexpectedly.",
        detail,
        buttons: ["Quit"],
      })
      .then(() => app.quit());
  });
}

async function waitForHealth(port) {
  const deadline = Date.now() + STARTUP_TIMEOUT_MS;
  setSplash("Loading models and starting the service…");
  while (Date.now() < deadline) {
    if (await healthOk(port)) return true;
    if (backendExited && !backendExternal) return false;
    await sleep(HEALTH_INTERVAL_MS);
  }
  return false;
}

function killBackend() {
  if (!backend || backend.killed || backend.exitCode !== null) return;
  try {
    if (process.platform === "win32") {
      execFile("taskkill", ["/PID", String(backend.pid), "/T", "/F"], () => {});
    } else {
      backend.kill("SIGTERM");
    }
  } catch {
    /* the process is already gone */
  }
}

// ---------------------------------------------------------------------------
// Windows
// ---------------------------------------------------------------------------

function createSplash() {
  splashWindow = new BrowserWindow({
    width: 460,
    height: 240,
    frame: false,
    resizable: false,
    show: true,
    backgroundColor: "#f6f8fa",
    webPreferences: { contextIsolation: true, nodeIntegration: false },
  });
  splashWindow.loadFile(path.join(__dirname, "splash.html"));
  splashWindow.webContents.once("did-finish-load", () => {
    splashReady = true;
    setSplash(splashStatus);
  });
  splashWindow.on("closed", () => {
    splashWindow = null;
  });
}

function windowStatePath() {
  return repoRoot ? path.join(repoRoot, "outputs", "desktop", "window-state.json") : null;
}

function loadWindowState() {
  const file = windowStatePath();
  if (!file) return {};
  try {
    const state = JSON.parse(fs.readFileSync(file, "utf8"));
    const valid = ["x", "y", "width", "height"].every(
      (key) => state[key] === undefined || Number.isFinite(state[key]),
    );
    return valid ? state : {};
  } catch {
    return {};
  }
}

function saveWindowState(window) {
  const file = windowStatePath();
  if (!file || window.isDestroyed()) return;
  try {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, JSON.stringify(window.getNormalBounds(), null, 2));
  } catch {
    /* window state is best-effort */
  }
}

function isLocalUrl(url) {
  try {
    const origin = new URL(url).origin;
    if (DEV && origin === new URL(DEV_URL).origin) return true;
    return backendPort !== null && origin === `http://127.0.0.1:${backendPort}`;
  } catch {
    return false;
  }
}

function createMainWindow(url) {
  const state = loadWindowState();
  mainWindow = new BrowserWindow({
    x: state.x,
    y: state.y,
    width: state.width || 1440,
    height: state.height || 920,
    minWidth: 1120,
    minHeight: 720,
    show: false,
    title: "SurroSim",
    backgroundColor: "#f6f8fa",
    // DesignKit title bar: the in-app bar replaces the native one. On
    // Windows/Linux the native window controls stay and overlay the bar
    // (Window Controls Overlay); on macOS the traffic lights remain native
    // and the bar keeps room for them.
    titleBarStyle: "hidden",
    ...(process.platform !== "darwin"
      ? {
          titleBarOverlay: {
            color: TITLE_BAR_COLORS.color,
            symbolColor: TITLE_BAR_COLORS.symbolColor,
            height: TITLE_BAR_HEIGHT,
          },
        }
      : { trafficLightPosition: { x: 12, y: 15 } }),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      spellcheck: false,
      // The renderer derives the bar height from this single declaration.
      additionalArguments: [`--surrosim-title-bar-height=${TITLE_BAR_HEIGHT}`],
    },
  });

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
    if (splashWindow && !splashWindow.isDestroyed()) splashWindow.close();
  });
  mainWindow.on("close", () => saveWindowState(mainWindow));
  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  mainWindow.webContents.setWindowOpenHandler(({ url: target }) => {
    if (isLocalUrl(target)) return { action: "allow" };
    if (/^https?:/.test(target)) shell.openExternal(target);
    return { action: "deny" };
  });
  mainWindow.webContents.on("will-navigate", (event, target) => {
    if (isLocalUrl(target)) return;
    event.preventDefault();
    if (/^https?:/.test(target)) shell.openExternal(target);
  });

  mainWindow.webContents.once("did-finish-load", () => {
    if (SMOKE) {
      setTimeout(() => {
        console.log("SMOKE OK");
        app.quit();
      }, 750);
    }
  });
  mainWindow.webContents.on(
    "did-fail-load",
    (_event, code, description, validatedUrl) => {
      if (SMOKE) {
        console.error(`SMOKE FAIL: page load ${code} ${description} ${validatedUrl}`);
        app.exit(1);
      }
    },
  );

  mainWindow.loadURL(url);
}

// The title bar strip and the native application menu share one template:
// the strip opens each submenu as a native popup, while the application menu
// keeps accelerators (Ctrl+R, Ctrl+Z, F11, …) working when no popup is open.
// Menu content therefore never diverges between the two surfaces.
function buildMenus(root) {
  const template = [
    {
      label: "File",
      submenu: [
        {
          label: "Settings",
          accelerator: "CmdOrCtrl+,",
          click: () => mainWindow?.webContents.send("navigate", "/settings"),
        },
        { type: "separator" },
        { role: "quit" },
      ],
    },
    {
      label: "Edit",
      submenu: [
        { role: "undo" },
        { role: "redo" },
        { type: "separator" },
        { role: "cut" },
        { role: "copy" },
        { role: "paste" },
        { role: "selectAll" },
      ],
    },
    {
      label: "View",
      submenu: [
        { role: "reload" },
        ...(DEV ? [{ role: "toggleDevTools" }] : []),
        { type: "separator" },
        { role: "resetZoom" },
        { role: "zoomIn" },
        { role: "zoomOut" },
        { type: "separator" },
        { role: "togglefullscreen" },
      ],
    },
    {
      label: "Help",
      submenu: [
        {
          label: "Documentation",
          click: () => {
            if (mainWindow && !mainWindow.isDestroyed()) {
              // The Documentation page in the web app (apps/web/src/App.tsx).
              mainWindow.webContents.send("navigate", "/manual");
              mainWindow.focus();
            }
          },
        },
        { type: "separator" },
        {
          label: "Open outputs folder",
          click: () => shell.openPath(path.join(root, "outputs")),
        },
        {
          label: "Open backend log",
          click: () => backendLogPath && shell.openPath(backendLogPath),
        },
        { type: "separator" },
        {
          label: "About SurroSim",
          click: () =>
            dialog.showMessageBox({
              type: "info",
              title: "About SurroSim",
              message: `SurroSim ${app.getVersion()}`,
              detail:
                `Local engineering surrogate workbench.\n\nRepository: ${root}\n` +
                `Electron ${process.versions.electron} · Chromium ${process.versions.chrome}`,
              buttons: ["Close"],
            }),
        },
      ],
    },
  ];
  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
  const popups = new Map();
  for (const item of menu.items) {
    if (item.submenu) popups.set(item.label.toLowerCase(), item.submenu);
  }
  return popups;
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

async function main() {
  repoRoot = findRepoRoot();
  if (!repoRoot) {
    fatal(
      "SurroSim repository not found",
      "Set the SURROSIM_REPO environment variable to the folder that contains pyproject.toml.",
    );
    return;
  }
  log(`repository: ${repoRoot}`);

  createSplash();

  try {
    if (DEV) {
      // Development expects the Vite dev server; the API runs on its proxy
      // target (8003) unless one is already healthy there (start-dev.bat).
      if (await isPortBusy(8003)) {
        if (await healthOk(8003)) {
          backendExternal = true;
          backendPort = 8003;
          log("using the already running service on port 8003");
        } else {
          fatal(
            "Port 8003 is in use but does not answer as a SurroSim service",
            "Stop the process that owns port 8003, or run without SURROSIM_DESKTOP_DEV to let the desktop app pick its own port.",
          );
          return;
        }
      } else {
        startBackend(repoRoot, 8003);
      }
    } else {
      const port = await pickPort(PREFERRED_PORT);
      startBackend(repoRoot, port);
    }

    if (!(await waitForHealth(backendPort))) {
      fatal(
        "The SurroSim service did not become ready",
        `Waited ${Math.round(STARTUP_TIMEOUT_MS / 1000)} s.\n\n${tail(12)}`,
      );
      return;
    }
    log(`service healthy on port ${backendPort}`);

    const url = DEV ? DEV_URL : `http://127.0.0.1:${backendPort}/`;
    log(`loading ${url}`);
    createMainWindow(url);
    popupMenus = buildMenus(repoRoot);
  } catch (error) {
    fatal("SurroSim failed to start", String(error && error.stack ? error.stack : error));
  }
}

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  app.whenReady().then(main);

  app.on("window-all-closed", () => app.quit());

  app.on("before-quit", () => {
    quitting = true;
    killBackend();
  });
}

ipcMain.handle("open-external", (_event, url) => {
  if (typeof url === "string" && /^https?:/.test(url)) {
    return shell.openExternal(url);
  }
  return undefined;
});

// Appearance is the only writable renderer preference boundary. Reject
// unknown fields, subframes, and senders other than the trusted main window.
function requireMainRenderer(event) {
  if (!mainWindow || mainWindow.isDestroyed() ||
      event.sender !== mainWindow.webContents ||
      event.senderFrame !== event.sender.mainFrame ||
      !isLocalUrl(event.senderFrame.url)) {
    throw new Error("Untrusted preferences request");
  }
}

function preferencesPath() {
  return path.join(app.getPath("userData"), "preferences.json");
}

ipcMain.handle("get-preferences", async (event) => {
  requireMainRenderer(event);
  try {
    const value = JSON.parse(await fs.promises.readFile(preferencesPath(), "utf8"));
    return {
      theme: value?.theme === "black" ? "black" : "light",
      sidebarCollapsed: value?.sidebarCollapsed === true,
    };
  } catch (error) {
    if (error.code !== "ENOENT") throw new Error("Could not read appearance preferences");
    return { theme: "light", sidebarCollapsed: false };
  }
});

let preferenceWrites = Promise.resolve();
ipcMain.handle("save-preferences", async (event, value) => {
  requireMainRenderer(event);
  if (!value || typeof value !== "object" || Array.isArray(value) ||
      Object.keys(value).some((key) => !["theme", "sidebarCollapsed"].includes(key)) ||
      !["light", "black"].includes(value.theme) ||
      typeof value.sidebarCollapsed !== "boolean") {
    throw new Error("Invalid appearance preferences");
  }
  const preferences = { theme: value.theme, sidebarCollapsed: value.sidebarCollapsed };
  const write = preferenceWrites.then(async () => {
    const file = preferencesPath();
    await fs.promises.mkdir(path.dirname(file), { recursive: true });
    await fs.promises.writeFile(`${file}.tmp`, JSON.stringify(preferences, null, 2), "utf8");
    await fs.promises.rename(`${file}.tmp`, file);
  });
  preferenceWrites = write.catch(() => {});
  await write;
});

ipcMain.handle("set-appearance", (event, colors) => {
  requireMainRenderer(event);
  if (!colors || typeof colors !== "object" || Array.isArray(colors) ||
      Object.keys(colors).some((key) => !["canvas", "ink"].includes(key)) ||
      typeof colors.canvas !== "string" || !/^#[a-f\d]{6}$/i.test(colors.canvas) ||
      typeof colors.ink !== "string" || !/^#[a-f\d]{6}$/i.test(colors.ink)) {
    throw new Error("Invalid appearance colors");
  }
  mainWindow.setBackgroundColor(colors.canvas);
  if (process.platform !== "darwin") {
    mainWindow.setTitleBarOverlay({
      color: colors.canvas,
      symbolColor: colors.ink,
      height: TITLE_BAR_HEIGHT,
    });
  }
});

// The title bar strip asks for one of the shared menus. The anchor arrives in
// CSS pixels relative to the viewport; the native popup is placed relative to
// the window content in DIP, so account for page zoom and clamp to the window.
ipcMain.handle("open-title-bar-menu", (event, name, anchor) => {
  const window = BrowserWindow.fromWebContents(event.sender);
  const menu = popupMenus.get(typeof name === "string" ? name : "");
  if (!window || window.isDestroyed() || !menu) return false;
  const zoom = event.sender.getZoomFactor();
  const x = Number.isFinite(anchor && anchor.x) ? anchor.x * zoom : 0;
  const y = Number.isFinite(anchor && anchor.y) ? anchor.y * zoom : 0;
  const bounds = window.getContentBounds();
  return new Promise((resolve) => {
    menu.popup({
      window,
      x: Math.round(Math.min(Math.max(x, 0), bounds.width)),
      y: Math.round(Math.min(Math.max(y, 0), bounds.height)),
      callback: () => resolve(true),
    });
  });
});
