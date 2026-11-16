# SurroSim web app — DesignKit design record

This app applies the DesignKit system (skill package: `designkit/BRAND.md`)
as a project-level implementation. `BRAND.md` owns the identity and values;
this document records how the app maps them and which project-specific choices
were made.

## Scope

- **Purpose:** an engineering surrogate-model workbench. Engineers explore
  parametric cantilever designs, read surrogate predictions, run real CalculiX
  verification and optimization, and inspect model provenance.
- **Users:** mechanical engineers and reviewers, pointer/keyboard-first on
  desktop browsers; no touch-first workflow is claimed.
- **Surfaces:** web single-page application served by the FastAPI service
  (`apps/web`, Vite + React + TypeScript + Tailwind) and the Electron renderer.
- **Modes:** Light (default) and Black (the DesignKit near-black dark canvas).
  Both map the same roles in `src/tokens.css`. The choice is explicit, not tied
  to the system theme, and persists on the current device/profile.
- **Accessibility target:** WCAG 2.2 AA for text, controls, and status.

## Token mapping

- `src/tokens.css` — the single source of design values. Semantic custom
  properties derived from `BRAND.md` (surfaces, text, borders, accent, action,
  focus, selection, feedback, bands, type stacks, radii, elevation, motion).
- `tailwind.config.ts` — maps Tailwind role names to those variables
  (`canvas`, `surface`, `wash`, `ink`, `line`, `accent`, `link`, `action`,
  `success`, `warning`, `danger`, `info`, `band`, `display`/`sans`/`mono`
  fonts, radii, shadows). Components consume roles, never raw hex values.
- Typography: Fraunces (display) for the page titles and the wordmark; Manrope
  (body/UI) for everything else; IBM Plex Mono for numbers, identifiers, and
  compact labels. Fonts are vendored Latin subsets in `src/assets/fonts/`
  (SIL OFL 1.1, provenance in that folder's README).
- Shape: 4 / 8 / 12 / 16 px steps with 8 px as the default control, panel, and
  card radius; pills use the full radius.
- Modes: `:root, [data-theme="light"]` and `[data-theme="black"]` declare the
  same variable names; `applyTheme` sets `data-theme` and `color-scheme`. A
  contrast test in `apps/web/tests/preferences.test.cjs` asserts the two blocks
  expose identical role keys and that every text/status/action/focus pair meets
  the declared target. `--color-control-thumb` and `--color-action-primary-border`
  are app-specific roles added so slider/switch thumbs and the primary button
  edge stay visible on both canvases.

## Project choices and exceptions

- **Compact desktop density.** The workbench is pointer-first; controls run
  28–36 px high and the slider thumb is 14 px. This intentionally uses the
  adapter's compact-desktop exception rather than the 44 px touch default.
  Sliders keep a full-width track hit area and keyboard operation; the
  exception is recorded here instead of applied silently.
- **Status color use.** Recommendation, job, and comparison states always pair
  color with a label or icon (`Trust`, `Run FEA`, `Failed`, `ok/violated`).
- **Text tiers.** `text-ink-faint` (Light `#7a838d`, Black `#9aa4af`; the
  DesignKit "nonessential supporting labels" role) is reserved for eyebrows,
  table headers, units, timestamps, and decorative markers. Decision-relevant
  sentences use `text-ink-muted` (Light `#3d444d` 9.25:1, Black `#cbd3db`
  13.0:1 on canvas) so they meet AA. Section group labels in the sidebar and
  manual use `text-ink-muted`, not faint, because they name content.
- **Charts and schematics.** Plotly axes keep the mono stack; grid/line colors
  map to border roles. Plotly paints SVG/WebGL and cannot read CSS variables, so
  `src/components/Plotly.tsx` resolves only `var(--color-*)` references to
  computed values at the render boundary (and re-renders on theme change);
  `tokens.css` still owns every value. The FEA field colorscale is a scientific
  visualization palette, deliberately separate from brand and feedback colors
  and identical in both themes. Parametric schematics (`DesignSchematic`,
  `PlateSchematic`) read the same `var(--color-*)` roles inline. The measured
  theme results are in the appearance review addendum below.
- **Black theme values.** Surfaces follow `BRAND.md` (`#0a0b0d` canvas,
  `#101214` surface, `#f1f4f7`/`#cbd3db` text, `#2e353b` border). Feedback,
  link, selection, and non-text roles that `BRAND.md` does not tabulate are
  derived project values chosen for AA on the dark canvas and recorded with
  their contrast ratios in the appearance review addendum below.
- **Navigation and Settings.** The sidebar groups destinations by task
  (Analysis, Evidence), keeps Documentation and Settings in a bottom utility
  group, marks the current page with surface plus weight, uses 44 px targets,
  and continues the existing collapsed icon rail (persisted). Below 768 px it
  becomes a native modal drawer (`aria-expanded`, focus trap, Escape, close on
  choice). The single collapse/expand control follows the DesignKit sidebar
  pattern: it sits at the leading edge of the desktop title bar, sharing that
  bar's baseline with the File/Edit/View/Help strip, and names the state it
  produces (`Collapse sidebar` / `Expand sidebar`) rather than the control.
  Browser builds render no title bar, so there the same control sits at the top
  of the sidebar instead — one control per build, never two. App identity moved
  from the sidebar chrome into a full-width content header (`Brand.tsx`) that
  spans the window above both columns, so the sidebar starts below it rather
  than level with it. Settings is a
  preference surface with one autosave model, Undo, Retry on failure, and
  Restore defaults.
- **Brand mark.** The SurroSim mark is an app-local asset: an ink "S" drawn as
  a single surrogate curve on a transparent background, ending in an
  accent-muted dot (`#40a0c3`, used decoratively here, never as text) for the
  data point the curve fits. Keep the inline SVG in
  `src/components/Brand.tsx` and `public/favicon.svg` in sync; both carry
  the same 32-unit geometry.
- **Feedback borders.** Chips and notes use explicit `*-border` roles
  (`rgba` of the feedback color over the soft surface) because Tailwind
  opacity modifiers cannot resolve `var()` colors.
- **Desktop title bar.** The Electron shell replaces native window chrome with
  the DesignKit in-app title bar (Windows/Linux; on macOS the traffic lights
  and system menu bar stay native). The 42 px bar sits on `canvas`, carries no
  brand, is the window drag region, and holds File/Edit/View/Help as flat text
  buttons that open native Electron popup menus. The same menu template is the
  application menu, so accelerators (Ctrl+R, Ctrl+Z, F11, …) keep working
  while no popup is open. Native window controls are overlaid through the
  Window Controls Overlay, whose `env(titlebar-area-*)` safe area bounds the
  strip. The height is declared once in `apps/desktop/main.js` and reaches CSS
  as `--title-bar-height` (`tokens.css` default `0px`); browser builds render
  no bar and no fake desktop menu. The renderer sends the active canvas/ink
  tokens through a validated, task-specific bridge to sync native control
  colors; the native popups themselves follow the operating-system theme.

## Icons

- The app consumes the owned DesignKit sprite, vendored to
  `public/icons/icons.svg`, through `src/components/Icon.tsx`
  (`<use href="…/icons.svg#dk-icon-{name}">`, `currentColor`, same-origin).
- No third-party icon pack remains; `lucide-react` was removed.
- Fourteen symbols were added to the canonical DesignKit sprite
  (book-open, cpu, git-branch, layers, loader, maximize, minimize, play,
  rotate-ccw, server, shield-alert, shield-check, sliders, target) and the
  sprite catalog in DesignKit (`assets/icons/README.md`, `ui-kit.html`) was
  updated; the app vendors that same file.
- The sidebar's collapse control follows the pattern's panel-chevron pair, so
  `panel-chevron-left` and `panel-chevron-right` were taken from the canonical
  DesignKit sprite (`assets/icons/icons.svg`) and appended to the vendored copy;
  `Icon.tsx` lists both. Byte-identical geometry to the source of truth.

## Interaction and accessibility checks

- Global `:focus-visible` ring: 2 px `--color-focus-ring` with offset; Radix
  slider and switch controls no longer suppress the outline.
- Segmented controls (field selector, report tabs) and the shape selector use
  `aria-pressed`; the tab groups carry group labels.
- Toasts announce through a polite live region; the OOD meter has an image
  role with a numeric label; icon-only controls keep accessible names.
- `prefers-reduced-motion` collapses the fade/shimmer animations.
- Title bar menu buttons are native `<button>`s with `aria-haspopup="menu"`,
  `aria-expanded` while their popup is open, and the global `:focus-visible`
  ring; the popups are native Electron menus, so arrow keys, mnemonics, and
  Escape are handled by the platform.
- Contrast spot checks (WCAG 2.2 AA): primary text/canvas 17.6:1, muted/canvas
  9.25:1, accent-ink/accent-soft ≈ 8.9:1, success 4.72:1 and warning 4.83:1 on
  their soft backgrounds, white on action ink 17.6:1.

## Review record

- Automated: `npm run typecheck`, `npm run build` (Vite 5) — both pass;
  production CSS contains the token variables, @font-face rules, focus ring,
  and reduced-motion block.
- Visual (Vite dev server + local API on the v2 candidate registries):
  Design Explorer, Field Prediction, FEA Verify, Optimization, Model,
  Dataset, Documentation, and the sidebar shell — reviewed as full-page
  captures at a ~1000 CSS px working width (the app's 12-column grids stack
  below the 1280 px `xl` breakpoint, which is pre-existing behavior).
- Interaction: ran a field prediction end to end — job progress, streamed
  log, success state, scalar summary, segmented field selector, and the 3D
  field viewer all reviewed.
- Programmatic checks: body canvas `#f6f8fa`, Manrope body / Fraunces
  headings, sprite symbols resolved (10 `<use>` refs), no console errors,
  six `aria-pressed` shape options, polite live region present, and a real
  Tab keypress produced a `:focus-visible` accent ring on the slider.
- Historical gaps for this light-only review: very narrow mobile widths were not
  a supported target; screenshot review ran at ~1000 px effective width, so the
  ≥1280 px multi-column arrangement was not pixel-reviewed; Safari/other
  browsers and automated a11y tooling (axe/Lighthouse) were not exercised.

### Review record addendum — Solver page and multi-page manual

- New surfaces: `/solver` (dedicated reference page for the real CalculiX
  engine) and `/manual` + `/manual/<slug>` (hub and 13 articles, including a
  plain-language glossary), replacing the single `/docs` page. The manual and
  the solver page share the same reading chrome (grouped table of contents,
  prev/next footer).
- Route note: FastAPI reserves `/docs` for the Swagger UI, so the manual lives
  at `/manual`; `/docs` keeps a client-side redirect for old in-app links. A
  hard load of `/docs` serves the API console, which is pre-existing behavior.
- Checks run: `npm run build` (tsc + Vite) passes; all 14 manual routes plus
  `/solver` were loaded from the built SPA behind the live API (v2 candidate
  registries) and verified for heading structure, sidebar active states,
  prev/next links, live dataset figures (CalculiX 2.23, 2,809 cases, 31,931
  median nodes) and console errors (none). The solver page's equation
  disclosure renders the live unknown count (3 × median nodes).
- Known gaps: full-page captures could not be taken during this pass (the
  desktop window was not visible to the capture tool), so the review was
  DOM- and live-data-based rather than pixel-based.

### Review record addendum — desktop title bar

- Automated: `npm run build` (tsc + Vite) passes; the desktop smoke test
  (`electron . --smoke`) prints `SMOKE OK`.
- Desktop (Windows, Electron 44.5.1, 125% scaling, built SPA + live API): the
  bar renders on the canvas with no branding; File and Help open native popups
  anchored under their buttons; Help → Documentation navigates the SPA to
  `/manual`; the window drags from the bar (moved 192×115 px); F11
  (View → `togglefullscreen`) works with no popup open; at the ~1120×720
  minimum the strip stays clear of the native window controls; the Help and
  File buttons show the open state while their popup is up.
- Renderer probe (built app + the real preload, stubbed menu IPC):
  `--title-bar-height` resolves to 42 px, the bar is 42 px tall on `canvas`,
  `app-region: drag` is active, the strip reads File/Edit/View/Help with no
  branding text, sidebar top and content padding are 42 px, `Tab` reaches the
  File button with a 2 px accent focus ring, Space/Enter open the menu IPC with
  the button's viewport anchor, and a window without the preload renders no
  bar and keeps `--title-bar-height: 0px`.
- Known gaps: macOS and Linux presentation was not run; keyboard activation
  was exercised with synthetic input rather than a physical keyboard; Windows
  high-contrast/forced-colors mode was not reviewed; page zoom scales the
  web-based bar while the native controls stay 42 px, which is accepted for
  this compact desktop target.

### Review record addendum — collapsible sidebar

- The sidebar header carries a collapse/expand toggle (`aria-expanded`,
  `aria-controls`, labelled both ways). Collapsed, the shell keeps a 56 px
  icon rail: the brand block, section headings and registry footer hide, nav
  items stay icon-only with their `aria-label` names and open DesignKit
  tooltips on hover, and the content column's left padding follows the rail.
  The preference persists in `localStorage` (`surrosim.sidebar.collapsed`).
- Implementation note: collapsed items wrap the `NavLink` in a plain element
  before the Radix tooltip trigger, because the slot joins class names as
  strings and would stringify NavLink's function `className`.
- Checks run (built SPA served by the live API): `npm run build` passes; the
  toggle measured 240 px → 56 px both ways (the transition read as frozen only
  because the browser tab was hidden), `aria-expanded`/`aria-label` update,
  the rail tooltip opens on hover ("Design Explorer"), the sidebar starts
  collapsed after reload with the stored preference, and no console errors
  were logged.
- Known gaps: full-page captures could not be taken (no visible desktop
  window), so this pass is DOM- and live-data-based rather than pixel-based;
  the transition itself was verified by class names plus transition-disabled
  measurement; touch and screen-reader output were not exercised.

### Review record addendum — desktop loading screen

- The Electron splash (`apps/desktop/splash.html`) now applies the DesignKit
  identity to a launch surface: the app mark (same 32-unit geometry as
  `AppShell.tsx` / `favicon.svg`), the wordmark in Fraunces 600, the eyebrow
  "AI Simulation Platform" in the faint supporting-label role (the same
  treatment as the sidebar, a documented nonessential-label exception), and a
  progress row with an SVG ring spinner plus "SurroSim is launching" and its
  pulsing dots. Tokens mirror `apps/web/src/tokens.css`; each animation is
  disabled under `prefers-reduced-motion`.
- Fraunces and Manrope Latin subsets were vendored to
  `apps/desktop/assets/fonts/` (copied from the web app; OFL notice retained
  in that folder's README); the packaging `files` list already ships
  `assets/**`. The strict splash CSP gains only `font-src 'self'`.
- Checks run (real Electron, file:// + CSP, 460×240 frameless window):
  `document.fonts` reports Fraunces and Manrope "loaded" and no console/CSP
  messages were logged; the content measures 228×196 px inside the window;
  the ring spinner runs `spin 0.9s linear` and the dot animation is
  staggered. `electron . --smoke` prints `SMOKE OK` and the packaged asar was
  rebuilt.
- Known gaps: no pixel capture (no visible desktop window), so this pass is
  computed-style- and DOM-based; the loading screen was not reviewed on macOS
  or at display scales other than 100%; reduced-motion rendering was verified
  by rule inspection, not by simulating the OS setting.

### Review record addendum — Black theme, Settings, sidebar, and documentation

Scope: the Light/Black modes, the Settings page, the DesignKit sidebar shell
with a narrow drawer, the manual improvements, theme-aware charts and
schematics, and the desktop preference bridge.

- **Automated.** `npm run build` (tsc + Vite 5) passes.
  `npm run test:preferences` passes 7/7 in `apps/web` (browser fallback and
  legacy sidebar key, theme/sidebar round-trip, corrupt and invalid saved
  values, denied storage, the desktop bridge path, identical role keys in both
  theme blocks, and the contrast matrix) and 7/7 in `apps/desktop` (the real
  main-process handlers run through `vm`: defaults, atomic write with no
  leftover temp file, rapid-save ordering, extra-key rejection, corrupt-file
  read failure, subframe / foreign-sender / deceptive-origin rejection, and
  color validation at the shared 42 px height). `npm run smoke` in
  `apps/desktop` prints `SMOKE OK`, so the shell still boots with the new menu
  item and preference handlers.
- **Contrast** (WCAG 2.2 AA, computed from the two `tokens.css` blocks).
  Black: primary/canvas 17.8:1, muted/canvas 13.0:1, accent-ink/accent-soft
  12.2:1, success 10.7:1, warning 8.3:1, danger 8.3:1, action text 16.9:1,
  focus ring 12.2:1 on canvas. Light: 17.6:1, 9.25:1, 8.95:1, 5.21:1, 4.84:1,
  6.59:1, 18.8:1, 5.68:1.
- **Browser / renderer review** (real Electron window with the built SPA behind
  the live API on the review candidates; captures at 360, 768, 1120, 1440 and
  1920 CSS px; no console errors):
  - theme switch applies instantly, survives reload, and keeps the current
    design and an in-progress/completed field result; the SVG schematic and the
    native canvas follow the theme;
  - a forced save failure keeps the choice active for the session and shows
    Retry; Retry, Undo last change, and Restore defaults all behave;
  - the collapsed rail is 64 px, keeps focus on the toggle, and shows a label
    tooltip on keyboard focus; the narrow-window drawer is a native modal
    (focus moved in, Escape closes, focus restored, closes on destination);
  - the manual topic filter reports a live count, shows a recoverable empty
    state, and clears; deep links focus the target heading; section ids are
    unique; the wide "On this page" list tracks the reader; the code copy
    control announces success and explains the denied-permission recovery;
  - no horizontal document overflow at any tested width or at 200 % zoom;
    emulated reduced-motion and forced-colors both resolve; the outline stays
    visible in forced-colors mode.
- **Live charts.** A real Field Prediction and a real Optimization run were
  executed in Black: the 3D scene background, axis walls and labels, the
  scatter/convergence colors, and the Plotly hover labels read the active
  theme roles, while the scientific FEA colorscale is byte-identical to the
  Light theme. Both runs survived a theme change and a route change. No
  console errors were logged.
- **Known gaps.** The automated click-through of the native *File → Settings*
  menu item in a real window was not completed (the harness stalled), so that
  specific round trip is covered indirectly: the menu item and the
  `TitleBar` `onNavigate` wiring are pre-existing and unchanged, `SMOKE OK`
  proves the menu template builds, and the IPC handlers are exercised directly
  by the desktop tests. Screen-reader output, macOS/Linux presentation, Safari,
  and automated a11y tooling (axe/Lighthouse) were not exercised. The clipboard
  test mocked `navigator.clipboard` in both the allowed and denied paths.

### Review record addendum — sidebar collapse control and DesignKit sprite

Scope: the sidebar's collapse/expand control, its placement in the two builds,
the state-naming of that control, and the two sprite symbols it needs. Recorded
against `core/QUALITY-CHECKLIST.md` for this surface.

- **Changed surfaces.** `src/components/AppShell.tsx` (new exported
  `SidebarToggle`; the sidebar's own header no longer carries the control when
  a title bar exists), `src/components/TitleBar.tsx` (optional `leading` slot
  at the bar's leading edge), `src/components/Icon.tsx` (two catalog entries),
  `public/icons/icons.svg` (two symbols), and this document.
- **Structure (intent).** One control per build. In the Electron shell it
  leads the title bar inside the `env(titlebar-area-*)` safe area, sharing the
  baseline with the application-menu strip and inheriting the existing
  `.titlebar button { app-region: no-drag }` exclusion; browser builds render
  no title bar (adapter rule) and show the same control at the top of the
  sidebar. `aria-label` names the resulting state (`Collapse sidebar` /
  `Expand sidebar`) and matches the tooltip wording; `aria-expanded` and
  `aria-controls="app-sidebar"` are present; the icon follows the pattern's
  `panel-chevron-left` (expanded) / `panel-chevron-right` (collapsed) pair.
  The collapsed rail keeps the Analysis/Evidence group names in the
  accessibility tree (`sr-only`) and the destinations stay `aria-label`ed
  behind tooltips. Per project choice the brand stays in the content header,
  so the sidebar carries no wordmark in either state.
- **Automated.** `npm run build` (tsc --noEmit + Vite 5.4.21) passes: 416
  modules transformed, CSS 54.68 kB, app chunk 713.85 kB (the >1200 kB
  advisory is the pre-existing Plotly split).
- **Build-output checks.** `dist/icons/icons.svg` contains both panel-chevron
  symbols with geometry byte-identical to `dnk-design/assets/icons/icons.svg`;
  the emitting CSS contains the classes the shell depends on (`.w-16`,
  `.w-60`, `.h-8`, `.w-8`, `.rounded-md`, `.border-line`, `.justify-end`,
  `.pt-3`, `.pl-1.5`, `.sr-only`), so the literal width strings survive
  Tailwind's scanner.
- **Browser / renderer review.** The built SPA served by the live API (v2
  review candidates) was driven in headless Chrome at 1440×900 through the
  DevTools protocol; the persisted preference was seeded both ways. Measured:
  the labeled sidebar is 240 px and the rail 64 px, with the content column's
  left padding tracking it (64 px collapsed); `aria-expanded` flips true/false
  and the accessible name flips with the state (`Collapse sidebar` /
  `Expand sidebar`), matching the tooltip wording; the icon swaps
  `panel-chevron-left` ↔ `panel-chevron-right`; exactly one element matches
  `[aria-controls="app-sidebar"]` in the browser build; focus stays on the
  control across both transitions (activate, then `document.activeElement` is
  still the button with its updated name); no `<use>` reference to the old
  `chevron-left`/`chevron-right` remains; all nine destinations keep their
  accessible names in the rail; the Analysis/Evidence headings keep their
  group role and stay available to assistive technology in the rail; the
  restored preference round-trips; no console errors. Full-page captures were
  reviewed for both states. The desktop title bar path cannot render in a
  browser (it is gated on the preload bridge), so its leading-edge placement is
  covered by the DOM structure and the build checks below rather than by a
  capture.
- **Desktop shell.** `electron . --smoke` in `apps/desktop` prints `SMOKE OK`
  (exit 0) against the built SPA, so the shell still boots with the title bar
  carrying the new leading control. Note for anyone re-running it: the DSH
  agent session exports `ELECTRON_RUN_AS_NODE=1`, which makes `electron .` run
  as plain Node and fail at `app.requestSingleInstanceLock` before any app code
  loads; clear that variable (or call the `electron.exe` directly) to get a real
  run.
- **Known gaps.** This pass did not visually measure the desktop bar, so the
  toggle's spacing next to the native menu strip, its behaviour as a non-drag
  region, and the native window-controls safe area at the minimum window size
  are reasoned from the shared bar container and the pre-existing
  `.titlebar button { app-region: no-drag }` rule plus a successful window boot
  — not captured or measured. Screen-reader output, macOS/Linux presentation,
  Safari, and automated a11y tooling (axe/Lighthouse) were not exercised, and
  the browser probe covered one viewport (1440×900), not the narrow drawer
  widths.
