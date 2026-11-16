import { getDesktopBridge } from "./desktop";

export type Theme = "light" | "black";
export type Preferences = { theme: Theme; sidebarCollapsed: boolean };

export const DEFAULT_PREFERENCES: Preferences = {
  theme: "light",
  sidebarCollapsed: false,
};
const STORAGE_KEY = "surrosim.preferences";

export function parsePreferences(value: unknown): Preferences {
  const data = value && typeof value === "object"
    ? value as Partial<Preferences>
    : {};
  return {
    theme: data.theme === "black" ? "black" : "light",
    sidebarCollapsed: data.sidebarCollapsed === true,
  };
}

export async function loadPreferences(): Promise<Preferences> {
  const desktop = getDesktopBridge();
  if (desktop) {
    // Desktop preferences are independent of the service's changing port.
    return parsePreferences(await desktop.getPreferences());
  }
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    return saved ? parsePreferences(JSON.parse(saved)) : {
      ...DEFAULT_PREFERENCES,
      sidebarCollapsed: window.localStorage.getItem("surrosim.sidebar.collapsed") === "1",
    };
  } catch {
    return { ...DEFAULT_PREFERENCES };
  }
}

export async function savePreferences(preferences: Preferences): Promise<void> {
  const desktop = getDesktopBridge();
  if (desktop) {
    await desktop.savePreferences(preferences);
  } else {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
  }
}

export async function applyTheme(theme: Theme): Promise<void> {
  document.documentElement.dataset.theme = theme;
  const styles = getComputedStyle(document.documentElement);
  const canvas = styles.getPropertyValue("--color-surface-canvas").trim();
  const ink = styles.getPropertyValue("--color-text-primary").trim();
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", canvas);
  await getDesktopBridge()?.setAppearance({ canvas, ink });
}
