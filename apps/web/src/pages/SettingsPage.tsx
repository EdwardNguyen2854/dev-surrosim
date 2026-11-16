import { Link } from "react-router-dom";

import { Page } from "../components/AppShell";
import { Icon } from "../components/Icon";
import { Button, Panel, PanelBody, PanelHeader, cx } from "../components/ui";
import { getDesktopBridge } from "../lib/desktop";
import { DEFAULT_PREFERENCES, type Theme } from "../lib/preferences";
import { usePreferences } from "../state/preferences";

const THEMES: { value: Theme; label: string; description: string }[] = [
  { value: "light", label: "Light", description: "A light canvas with ink-colored actions." },
  { value: "black", label: "Black", description: "A near-black canvas with softer, high-contrast text." },
];

function ThemePreview({ theme }: { theme: Theme }) {
  return (
    <div data-theme={theme} aria-hidden="true" className="mt-4 flex h-24 overflow-hidden rounded border border-line bg-canvas">
      <div className="w-10 space-y-2 border-r border-line p-2">
        <div className="h-3 rounded-sm bg-accent-soft" />
        <div className="h-2 rounded-sm bg-line" />
        <div className="h-2 rounded-sm bg-line" />
      </div>
      <div className="flex-1 space-y-2 p-3">
        <div className="h-2 w-1/2 rounded-sm bg-ink-muted" />
        <div className="flex h-11 items-end gap-1.5 rounded border border-line bg-surface p-2">
          <div className="h-2 w-1/4 rounded-sm bg-accent" />
          <div className="h-4 w-1/4 rounded-sm bg-accent" />
          <div className="h-6 w-1/4 rounded-sm bg-accent" />
        </div>
      </div>
    </div>
  );
}

export function SettingsPage() {
  const { preferences, status, appearanceError, canUndo, update, undo, retry } = usePreferences();
  const desktop = Boolean(getDesktopBridge());
  const defaultSettings = preferences.theme === DEFAULT_PREFERENCES.theme &&
    preferences.sidebarCollapsed === DEFAULT_PREFERENCES.sidebarCollapsed;

  return (
    <Page kicker="Preferences" title="Settings" description="Make the workbench comfortable to use. Appearance changes apply immediately and save on this device.">
      <div className="max-w-3xl space-y-5">
        <Panel>
          <PanelHeader title="Appearance" description="These preferences change the interface, not your design, models, or simulation results." />
          <PanelBody className="space-y-6">
            <fieldset aria-describedby="theme-hint">
              <legend className="text-sm font-semibold text-ink">Theme</legend>
              <p id="theme-hint" className="mt-1 text-xs leading-relaxed text-ink-muted">Light is the default. Your choice stays the same until you change it.</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {THEMES.map((theme) => (
                  <label key={theme.value} className={cx(
                    "cursor-pointer rounded border p-4 transition-colors focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-focus",
                    preferences.theme === theme.value ? "border-accent-strong bg-accent-soft" : "border-line-strong bg-surface hover:bg-wash",
                  )}>
                    <span className="flex items-center gap-3 text-sm font-semibold">
                      <input
                        type="radio" name="theme" value={theme.value}
                        checked={preferences.theme === theme.value}
                        onChange={() => update({ theme: theme.value })}
                        className="h-4 w-4 accent-accent-strong"
                        aria-describedby={`theme-${theme.value}-hint`}
                      />
                      {theme.label}
                      <Icon name={theme.value === "light" ? "sun" : "moon"} className="ml-auto h-4 w-4 text-ink-muted" />
                    </span>
                    <span id={`theme-${theme.value}-hint`} className="mt-2 block text-xs leading-relaxed text-ink-muted">{theme.description}</span>
                    <ThemePreview theme={theme.value} />
                  </label>
                ))}
              </div>
            </fieldset>

            <div className="border-t border-line pt-5">
              <label className="flex min-h-11 cursor-pointer items-center gap-3">
                <input
                  type="checkbox" checked={preferences.sidebarCollapsed}
                  onChange={(event) => update({ sidebarCollapsed: event.target.checked })}
                  aria-describedby="sidebar-hint" className="h-4 w-4 accent-accent-strong"
                />
                <span className="text-sm font-semibold">Use a compact sidebar</span>
              </label>
              <p id="sidebar-hint" className="pl-7 text-xs leading-relaxed text-ink-muted">Keep navigation as an icon rail to leave more room for your work. Labels appear on hover or keyboard focus. Narrow windows use a navigation drawer instead.</p>
            </div>

            <div className="flex flex-wrap items-center gap-3 border-t border-line pt-4">
              <p role="status" aria-live="polite" className={cx("mr-auto flex items-center gap-2 text-xs", status === "failed" ? "text-danger" : "text-ink-muted")}>
                <Icon name={status === "failed" ? "alert-triangle" : status === "saving" ? "loader" : "check-circle"} className={cx("h-4 w-4", status === "saving" && "animate-spin")} />
                {status === "saving" ? "Saving preferences…" : status === "failed" ? "Not saved. Your changes are active for this session; retry to keep them." : status === "saved" ? "Preferences saved on this device." : "Changes save automatically on this device."}
              </p>
              {status === "failed" && <Button onClick={retry}>Retry save</Button>}
              <Button variant="ghost" onClick={undo} disabled={!canUndo || status === "saving"}>Undo last change</Button>
            </div>
            {appearanceError && <div role="alert" className="rounded border border-warning bg-warning-soft p-3 text-xs text-warning">
              The theme is active, but the native window controls could not be updated. <button type="button" onClick={retry} className="font-semibold underline">Retry</button>.
            </div>}
          </PanelBody>
        </Panel>

        <div className="flex flex-wrap items-center justify-between gap-3 rounded border border-line bg-wash p-4">
          <div className="max-w-lg">
            <h2 className="text-xs font-semibold">Local preferences only</h2>
            <p className="mt-1 text-xs leading-relaxed text-ink-muted">{desktop ? "The desktop app stores these preferences in its local user-data folder, even if the service starts on a different port." : "This browser stores these preferences for the current site. Other browsers and the desktop app keep their own choices."} Reduced motion follows your operating-system preference.</p>
          </div>
          <Button variant="secondary" disabled={defaultSettings || status === "saving"} onClick={() => update(DEFAULT_PREFERENCES)}>Restore defaults</Button>
        </div>
        <p className="text-xs text-ink-muted">Looking for solver or model configuration? Read the <Link to="/manual/app-settings" className="text-link underline underline-offset-2">appearance guide</Link> or open <Link to="/solver" className="text-link underline underline-offset-2">Solver</Link>. Settings here never retrain a model or alter a dataset.</p>
      </div>
    </Page>
  );
}
