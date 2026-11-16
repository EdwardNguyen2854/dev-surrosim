"use strict";

const { contextBridge, ipcRenderer } = require("electron");

// DesignKit title bar height, declared once in main.js and passed down through
// --surrosim-title-bar-height, so the renderer's bar styles, the native
// window-controls overlay, and the renderer's layout offsets always agree.
function readTitleBarHeight() {
  const prefix = "--surrosim-title-bar-height=";
  const arg = process.argv.find((value) => value.startsWith(prefix));
  const height = arg ? Number.parseInt(arg.slice(prefix.length), 10) : NaN;
  return Number.isFinite(height) && height > 0 ? height : 0;
}

// Minimal, task-specific bridge. The web app talks to the local HTTP API;
// this exposes desktop identity, the title bar metrics, native popup menus for
// the title bar strip, in-app navigation requested by those menus, and safe
// external-link handling.
contextBridge.exposeInMainWorld("surrosimDesktop", {
  isDesktop: true,
  platform: process.platform,
  titleBarHeight: readTitleBarHeight(),
  versions: {
    electron: process.versions.electron,
    chrome: process.versions.chrome,
  },
  getPreferences: () => ipcRenderer.invoke("get-preferences"),
  savePreferences: (preferences) => ipcRenderer.invoke("save-preferences", preferences),
  setAppearance: (colors) => ipcRenderer.invoke("set-appearance", colors),
  openExternal: (url) => ipcRenderer.invoke("open-external", url),
  openMenu: (name, anchor) =>
    ipcRenderer.invoke("open-title-bar-menu", name, anchor),
  onNavigate: (handler) => {
    if (typeof handler !== "function") return () => {};
    const listener = (_event, target) => handler(target);
    ipcRenderer.on("navigate", listener);
    return () => ipcRenderer.removeListener("navigate", listener);
  },
});
