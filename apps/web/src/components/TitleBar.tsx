import { useEffect, useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";

import { cx } from "../lib/cx";
import { getDesktopBridge, type DesktopMenuName } from "../lib/desktop";

const MENUS: { name: DesktopMenuName; label: string }[] = [
  { name: "file", label: "File" },
  { name: "edit", label: "Edit" },
  { name: "view", label: "View" },
  { name: "help", label: "Help" },
];

/**
 * DesignKit desktop title bar: an in-app bar on the app background at the top
 * of the shell. It is brand-free, is the window drag region, and carries the
 * application menu as a strip of flat text buttons whose activation opens
 * native Electron popups. Native window controls stay overlaid on the right
 * (Window Controls Overlay), which the `env(titlebar-area-*)` safe area keeps
 * clear; on macOS the traffic lights and the system menu bar stay native, so
 * only the drag region remains. Browser builds render nothing.
 *
 * `leading` is the shell's own control at the bar's leading edge — in this app
 * the sidebar collapse/expand toggle, which the DesignKit sidebar pattern
 * places here rather than inside the navigation list. It sits on the same
 * baseline as the menu strip.
 */
export function TitleBar({ leading }: { leading?: ReactNode } = {}) {
  const desktop = getDesktopBridge();
  const navigate = useNavigate();
  const [open, setOpen] = useState<DesktopMenuName | null>(null);

  useEffect(() => {
    if (!desktop) return;
    return desktop.onNavigate((path) => navigate(path));
  }, [desktop, navigate]);

  if (!desktop) return null;
  const isMac = desktop.platform === "darwin";

  const showMenu = (name: DesktopMenuName, button: HTMLButtonElement) => {
    const rect = button.getBoundingClientRect();
    setOpen(name);
    desktop
      .openMenu(name, { x: rect.left, y: rect.bottom })
      .catch(() => false)
      .finally(() => setOpen((current) => (current === name ? null : current)));
  };

  return (
    <div
      className="titlebar fixed inset-x-0 top-0 z-40 h-[var(--title-bar-height)] select-none border-b border-line bg-canvas"
    >
      <div
        className="absolute"
        style={{
          left: "env(titlebar-area-x, 0px)",
          top: "env(titlebar-area-y, 0px)",
          width: "env(titlebar-area-width, 100%)",
          height: "env(titlebar-area-height, 100%)",
        }}
      >
        <div className="flex h-full items-center">
          {leading && <div className="flex h-full items-center pl-1.5">{leading}</div>}
          {!isMac && (
            <nav
              aria-label="Application menu"
              className="flex h-full items-center px-1.5"
            >
              {MENUS.map((menu) => (
                <button
                  key={menu.name}
                  type="button"
                  aria-haspopup="menu"
                  aria-expanded={open === menu.name}
                  className={cx(
                    "h-7 rounded px-2.5 text-xs font-medium transition-colors",
                    open === menu.name
                      ? "bg-accent-soft text-accent-ink"
                      : "text-ink-muted hover:bg-wash hover:text-ink",
                  )}
                  onClick={(event) => showMenu(menu.name, event.currentTarget)}
                >
                  {menu.label}
                </button>
              ))}
            </nav>
          )}
        </div>
      </div>
    </div>
  );
}
