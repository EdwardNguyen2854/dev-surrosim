# SurroSim desktop shell

Electron wrapper around the local SurroSim service. The shell spawns
`python -m surrosim serve` from the repository's `.venv`, waits for the API
health check, and opens the built React app in a native window. Nothing in the
web app or the Python service changes — the desktop shell is additive.

```
SurroSim.exe (Electron main)
  ├─ find repo root (pyproject.toml) and .venv Python
  ├─ pick the promoted v2 registry (or the review candidate / v1)
  ├─ spawn: python -m surrosim serve --port <free> --registry ... --field-model ...
  ├─ poll /api/health → open BrowserWindow
  └─ on quit: taskkill /T the backend process tree
```

## Running

From the repository root:

```bat
start-desktop.bat
```

First run builds `apps/web/dist` if needed, installs `apps/desktop/node_modules`
if needed, then launches the app. Afterwards you can also run directly:

```bat
cd apps\desktop
npm start
```

Development against the Vite dev server (run `start-dev.bat` first, or let the
shell start the API on port 8003):

```bat
cd apps\desktop
set SURROSIM_DESKTOP_DEV=1
npm start
```

## Automation / CI smoke test

```bat
cd apps\desktop
npx electron . --smoke
```

Starts the backend, waits for the window to finish loading, prints
`SMOKE OK` and exits 0 (or exits 1 with a reason).

## Title bar and menu

The window uses the DesignKit in-app title bar instead of native window
chrome: a 42 px bar on the active Light or Black canvas, with no logo or app name,
whose flat **File / Edit / View / Help** buttons open native Electron popup
menus. The same menu template is set as the application menu, so accelerators
(Ctrl+R reload, Ctrl+Z undo, F11 fullscreen, …) keep working while no popup is
open. On Windows and Linux the native window controls stay and overlay the bar
(Window Controls Overlay); on macOS the traffic lights and the system menu bar
remain native.

- `TITLE_BAR_HEIGHT` in `main.js` is the single declaration; the preload bridge
  passes it to the renderer (`titleBarHeight`), which maps it to
  `--title-bar-height` for the bar styles and the layout offsets.
- The bar is the window drag region; the menu buttons are excluded, and a
  double-click on the bar maximizes the window.
- Help → *Documentation* opens the in-app manual (`/manual`); the other Help
  items open the outputs folder, the backend log, and the About dialog.
- File → *Settings* (`Ctrl+,` / `Command+,`) opens `/settings`. Native window
  control colors follow the selected theme through the validated preload bridge.
- Browser builds (`npm run dev`) render no title bar and no desktop menu; the
  bar appears only in the Electron shell (use `SURROSIM_DESKTOP_DEV=1` to run
  the shell against the Vite dev server).

## Environment variables

| Variable | Purpose |
| --- | --- |
| `SURROSIM_REPO` | Repository root (default: walk up from this app to `pyproject.toml`) |
| `SURROSIM_PYTHON` | Python interpreter (default: `<repo>/.venv/Scripts/python.exe`, then PATH) |
| `SURROSIM_PORT` | Preferred port (default 8003; an ephemeral port is used if busy) |
| `SURROSIM_DESKTOP_DEV=1` | Load `http://localhost:5173` (Vite) instead of the built app |
| `SURROSIM_DEV_URL` | Override the dev URL (default `http://localhost:5173`) |

## Registry resolution

Model registries are selected at run time, without configuration:

- Scalar: `models/scalar/v2` → `v2_reviewed_candidate` → `v2_candidate` → `v1`
- Field: `models/gnn/v2` → `v2_normalized_candidate` → `v2_candidate` → `v1`

A candidate only counts if it is loadable (metadata plus model files). When the
v2.0.0 registries are promoted to `models/scalar/v2` and `models/gnn/v2`, the
desktop app picks them up automatically.

## Logs and state

- `outputs/desktop/backend.log` — backend stdout/stderr (previous run kept as
  `backend.prev.log`)
- `outputs/desktop/window-state.json` — remembered window position and size
- `<Electron userData>/preferences.json` — Light/Black theme and sidebar choice;
  independent of the backend's port. The renderer can read/write only this
  typed preference record; it has no general filesystem or messaging access.
- Menu → Help → *Open backend log* / *Open outputs folder*

## Appearance and documentation

Settings saves appearance changes immediately, with Undo, Retry on failure,
and Restore defaults (Light + expanded sidebar). It never changes engineering
inputs, running jobs, models, or datasets. Browser preferences are separate,
stored for that site in `localStorage`; neither mode follows the system theme.
Animations continue to respect the system's reduced-motion preference.

The sidebar keeps Settings and Documentation at the bottom. Its compact rail
has labels on hover and keyboard focus; narrow browser windows use a modal
navigation drawer. The manual at `/manual` has a title/summary topic filter,
breadcrumbs, stable section links, a wide-screen contents list, previous/next
links, and a topic drawer at narrower widths. It does not claim full-text search.

## Portable build (optional)

```bat
cd apps\desktop
npm run dist
```

Produces `apps/desktop/release/win-unpacked/SurroSim.exe`. The build contains
the Electron shell only; it still expects the SurroSim repository (`.venv`,
models, dataset, CalculiX) and locates it with `SURROSIM_REPO` or by walking up
from its own folder. Distributing to machines without a repository requires a
frozen Python sidecar (PyInstaller) — deliberately out of scope for the
personal launcher.
