"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const vm = require("node:vm");
const { test } = require("node:test");

// Exercise the real main-process handlers without starting a solver or window.
function harness(t) {
  const parent = path.join(os.tmpdir(), "opencode");
  fs.mkdirSync(parent, { recursive: true });
  const dir = fs.mkdtempSync(path.join(parent, "surrosim-preferences-"));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  const handlers = new Map();
  const appearance = {};
  const frame = { url: "http://127.0.0.1:8003/settings" };
  const sender = { mainFrame: frame };
  const window = {
    webContents: sender,
    isDestroyed: () => false,
    setBackgroundColor: (value) => { appearance.canvas = value; },
    setTitleBarOverlay: (value) => { appearance.overlay = value; },
  };
  const electron = {
    app: {
      requestSingleInstanceLock: () => true,
      on: () => {},
      whenReady: () => ({ then: () => {} }),
      getPath: () => dir,
    },
    ipcMain: { handle: (name, callback) => handlers.set(name, callback) },
  };
  const context = vm.createContext({
    require: (name) => name === "electron" ? electron : require(name),
    process: { argv: [], env: {}, platform: "win32" },
    __dirname: path.resolve(__dirname, ".."),
    console,
    URL,
    testWindow: window,
  });
  vm.runInContext(fs.readFileSync(path.join(__dirname, "../main.js"), "utf8"), context);
  vm.runInContext("mainWindow = testWindow; backendPort = 8003;", context);
  return {
    dir, appearance, sender, frame,
    event: { sender, senderFrame: frame },
    call: (name, event, ...args) => handlers.get(name)(event, ...args),
  };
}

test("preferences default to Light with labeled navigation", async (t) => {
  const h = harness(t);
  const preferences = await h.call("get-preferences", h.event);
  assert.equal(preferences.theme, "light");
  assert.equal(preferences.sidebarCollapsed, false);
});

test("preferences save atomically and survive reloads", async (t) => {
  const h = harness(t);
  await h.call("save-preferences", h.event, { theme: "black", sidebarCollapsed: true });
  const saved = JSON.parse(fs.readFileSync(path.join(h.dir, "preferences.json"), "utf8"));
  assert.deepEqual(saved, { theme: "black", sidebarCollapsed: true });
  assert.equal(fs.existsSync(path.join(h.dir, "preferences.json.tmp")), false);
  assert.equal((await h.call("get-preferences", h.event)).theme, "black");
});

test("rapid saves keep the newest snapshot", async (t) => {
  const h = harness(t);
  await Promise.all([
    h.call("save-preferences", h.event, { theme: "black", sidebarCollapsed: true }),
    h.call("save-preferences", h.event, { theme: "light", sidebarCollapsed: false }),
  ]);
  assert.equal((await h.call("get-preferences", h.event)).theme, "light");
});

test("invalid preferences and extra keys are rejected", async (t) => {
  const h = harness(t);
  for (const value of [null, [], {},
    { theme: "system", sidebarCollapsed: false },
    { theme: "black", sidebarCollapsed: "true" },
    { theme: "black", sidebarCollapsed: true, path: "elsewhere" },
  ]) {
    await assert.rejects(h.call("save-preferences", h.event, value), /Invalid appearance/);
  }
  assert.equal(fs.existsSync(path.join(h.dir, "preferences.json")), false);
});

test("untrusted senders, subframes, and deceptive origins are rejected", async (t) => {
  const h = harness(t);
  await assert.rejects(h.call("get-preferences", { sender: {}, senderFrame: h.frame }), /Untrusted/);
  await assert.rejects(h.call("get-preferences", { sender: h.sender, senderFrame: { ...h.frame } }), /Untrusted/);
  h.frame.url = "http://127.0.0.1:80030/settings";
  await assert.rejects(h.call("get-preferences", h.event), /Untrusted/);
  h.frame.url = "http://127.0.0.1:8003.evil.example/settings";
  await assert.rejects(h.call("get-preferences", h.event), /Untrusted/);
});

test("corrupt preference files report a read failure", async (t) => {
  const h = harness(t);
  fs.writeFileSync(path.join(h.dir, "preferences.json"), "{broken");
  await assert.rejects(h.call("get-preferences", h.event), /Could not read/);
});

test("native controls accept only validated colors at the shared height", (t) => {
  const h = harness(t);
  h.call("set-appearance", h.event, { canvas: "#123456", ink: "#abcdef" });
  assert.equal(h.appearance.canvas, "#123456");
  assert.equal(h.appearance.overlay.color, "#123456");
  assert.equal(h.appearance.overlay.symbolColor, "#abcdef");
  assert.equal(h.appearance.overlay.height, 42);
  for (const value of [null, {},
    { canvas: "red", ink: "#abcdef" },
    { canvas: "#123456", ink: "#fff" },
    { canvas: "#123456", ink: "#abcdef", extra: true },
  ]) {
    assert.throws(() => h.call("set-appearance", h.event, value), /Invalid appearance/);
  }
});
