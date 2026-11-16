import type { Preferences } from "./preferences";

/**
 * Typed access to the Electron shell's preload bridge
 * (`apps/desktop/preload.js`). The value is `undefined` in a browser, so every
 * desktop-only surface checks for it before rendering.
 */

export type DesktopMenuName = "file" | "edit" | "view" | "help";

export type DesktopBridge = {
  isDesktop: true;
  platform: string;
  /**
   * DesignKit title bar height in CSS pixels. Declared once in
   * `apps/desktop/main.js` (`TITLE_BAR_HEIGHT`) and shared with the native
   * window-controls overlay.
   */
  titleBarHeight: number;
  versions: { electron: string; chrome: string };
  /** Device-local appearance preferences, validated and stored by the shell. */
  getPreferences: () => Promise<Preferences>;
  savePreferences: (preferences: Preferences) => Promise<void>;
  /** Sync native window controls to the renderer's semantic color tokens. */
  setAppearance: (colors: { canvas: string; ink: string }) => Promise<void>;
  /** Opens a link in the operating system's default browser. */
  openExternal: (url: string) => Promise<void>;
  /**
   * Opens the native popup for one of the title bar menus, anchored at a
   * viewport point (CSS pixels). Resolves when the popup closes.
   */
  openMenu: (
    name: DesktopMenuName,
    anchor: { x: number; y: number },
  ) => Promise<boolean>;
  /**
   * Registers a handler for in-app navigation requested by the native menus
   * (for example Help → Documentation). Returns an unsubscribe function.
   */
  onNavigate: (handler: (path: string) => void) => () => void;
};

declare global {
  interface Window {
    surrosimDesktop?: DesktopBridge;
  }
}

export function getDesktopBridge(): DesktopBridge | undefined {
  return typeof window === "undefined" ? undefined : window.surrosimDesktop;
}
