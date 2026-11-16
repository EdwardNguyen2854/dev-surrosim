import { useEffect, useState, type ReactNode } from "react";
import { NavLink, Outlet } from "react-router-dom";

import { getDesktopBridge } from "../lib/desktop";
import { useDesign } from "../state/design";
import { usePreferences } from "../state/preferences";
import { Brand } from "./Brand";
import { Drawer } from "./Drawer";
import { Icon, type IconName } from "./Icon";
import { TitleBar } from "./TitleBar";
import { Tooltip, cx } from "./ui";

const NAV_ITEMS: { to: string; label: string; icon: IconName; end?: boolean }[] = [
  { to: "/", label: "Design Explorer", icon: "sliders", end: true },
  { to: "/field", label: "Field Prediction", icon: "layers" },
  { to: "/verify", label: "FEA Verify", icon: "shield-check" },
  { to: "/optimize", label: "Optimization", icon: "target" },
  { to: "/model", label: "Model", icon: "cpu" },
  { to: "/dataset", label: "Dataset", icon: "package" },
  { to: "/solver", label: "Solver", icon: "server" },
];

const UTILITY_ITEMS: typeof NAV_ITEMS = [
  { to: "/manual", label: "Documentation", icon: "book-open" },
  { to: "/settings", label: "Settings", icon: "settings" },
];

const NAV_GROUPS: { heading: string; items: typeof NAV_ITEMS }[] = [
  { heading: "Analysis", items: NAV_ITEMS.slice(0, 4) },
  { heading: "Evidence", items: NAV_ITEMS.slice(4) },
];

/**
 * The one collapse/expand control for the labeled sidebar, in the two places
 * the DesignKit sidebar pattern allows it: the leading edge of the desktop
 * title bar, and the sidebar's own header for browser builds, which render no
 * title bar. Its name changes with the state it produces, not with the control.
 */
export function SidebarToggle({
  collapsed, onToggle, className,
}: {
  collapsed: boolean;
  onToggle: () => void;
  className?: string;
}) {
  const label = collapsed ? "Expand sidebar" : "Collapse sidebar";
  return (
    <Tooltip label={label} side={className ? "bottom" : "right"}>
      <button
        type="button" onClick={onToggle}
        aria-label={label} aria-controls="app-sidebar" aria-expanded={!collapsed}
        className={cx(
          "inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-line text-ink-muted transition-colors hover:bg-wash hover:text-ink",
          className,
        )}
      >
        <Icon name={collapsed ? "panel-chevron-right" : "panel-chevron-left"} className="h-[18px] w-[18px]" />
      </button>
    </Tooltip>
  );
}

function SidebarNavigation({
  collapsed, onNavigate, id,
}: {
  collapsed: boolean;
  onNavigate?: () => void;
  id: string;
}) {
  return (
    <nav aria-label="Primary" className="flex min-h-0 flex-1 flex-col">
      <div className="thin-scroll min-h-0 flex-1 overflow-y-auto px-2 py-3">
        {NAV_GROUPS.map((group, index) => (
          <div key={group.heading} className={cx(index > 0 && "pt-6")}>
            {/*
             * Section headings stay in the accessibility tree when the rail
             * collapses, so the destinations keep their group names.
             */}
            <div id={`${id}-${index}`} className={cx(
              "px-3 pb-2 text-2xs font-medium uppercase tracking-wider text-ink-muted",
              collapsed && "sr-only",
            )}>
              {group.heading}
            </div>
            <ul aria-labelledby={`${id}-${index}`} className="space-y-1">
              {group.items.map((item) => (
                <NavItem key={item.to} {...item} collapsed={collapsed} onNavigate={onNavigate} />
              ))}
            </ul>
          </div>
        ))}
      </div>
      <ul aria-label="Help and preferences" className="shrink-0 space-y-1 border-t border-line px-2 py-3">
        {UTILITY_ITEMS.map((item) => (
          <NavItem key={item.to} {...item} collapsed={collapsed} onNavigate={onNavigate} />
        ))}
      </ul>
    </nav>
  );
}

function ServiceStatus() {
  const { config, configError } = useDesign();
  return (
    <div className="shrink-0 border-t border-line px-4 py-3 text-2xs text-ink-muted">
      <div className="flex items-center gap-2">
        <Icon name={configError ? "alert-triangle" : "server"} className={cx(
          "h-3.5 w-3.5", configError ? "text-danger" : config ? "text-success" : "text-ink-muted",
        )} />
        {configError ? "Service unavailable" : !config ? "Connecting to service…" :
          config.capabilities?.calculix ? "CalculiX ready" : "CalculiX unavailable"}
      </div>
      <p className="mt-1.5 leading-relaxed">Verify predictions before engineering use.</p>
    </div>
  );
}

function NavItem({
  to,
  label,
  icon,
  end,
  collapsed,
  onNavigate,
}: {
  to: string;
  label: string;
  icon: IconName;
  end?: boolean;
  collapsed: boolean;
  onNavigate?: () => void;
}) {
  const link = (
    <NavLink
      to={to}
      end={end}
      aria-label={label}
      onClick={(event) => {
        if (!event.ctrlKey && !event.metaKey && !event.shiftKey && event.button === 0) onNavigate?.();
      }}
      className={cx(
        "flex min-h-11 items-center rounded text-xs font-medium text-ink-muted transition-colors hover:bg-wash hover:text-ink aria-[current=page]:bg-accent-soft aria-[current=page]:font-bold aria-[current=page]:text-accent-ink",
        collapsed ? "justify-center px-0" : "gap-3 px-3",
      )}
    >
      <Icon name={icon} className="h-[18px] w-[18px]" />
      {!collapsed && <span className="min-w-0">{label}</span>}
    </NavLink>
  );

  return (
    <li>
      {collapsed ? (
        <Tooltip label={label} side="right">
          {link}
        </Tooltip>
      ) : (
        link
      )}
    </li>
  );
}

export function AppShell() {
  const { preferences, status, update } = usePreferences();
  const collapsed = preferences.sidebarCollapsed;
  const [drawerOpen, setDrawerOpen] = useState(false);
  /*
   * Stands in for a build fact that cannot change while the app runs: the
   * Electron shell renders a title bar, browser builds render none. It decides
   * only where the one sidebar toggle lives — never two of them.
   */
  const hasTitleBar = Boolean(getDesktopBridge());
  const toggleSidebar = () => update({ sidebarCollapsed: !collapsed });

  useEffect(() => {
    const wide = window.matchMedia("(min-width: 768px)");
    const onResize = () => { if (wide.matches) setDrawerOpen(false); };
    wide.addEventListener("change", onResize);
    return () => wide.removeEventListener("change", onResize);
  }, []);

  return (
    <div className="min-h-screen">
      <a href="#main-content" className="sr-only fixed left-3 top-3 z-[80] rounded bg-surface px-4 py-3 text-sm text-ink shadow-overlay focus:not-sr-only">Skip to content</a>
      {hasTitleBar && <TitleBar leading={<SidebarToggle collapsed={collapsed} onToggle={toggleSidebar} />} />}
      <header className="fixed inset-x-0 top-[var(--title-bar-height)] z-30 flex h-[72px] items-center gap-3 border-b border-line bg-canvas px-4 sm:px-7">
        <button
          type="button" onClick={() => setDrawerOpen(true)}
          aria-label="Open navigation" aria-expanded={drawerOpen} aria-controls="navigation-drawer"
          className="flex h-11 w-11 items-center justify-center rounded text-ink-muted hover:bg-wash md:hidden"
        >
          <Icon name="menu" className="h-5 w-5" />
        </button>
        <Brand />
        <span className="ml-auto hidden text-2xs text-ink-muted sm:inline">Local workbench</span>
      </header>
      <aside id="app-sidebar" className={cx(
        "fixed bottom-0 left-0 top-[calc(var(--title-bar-height)+72px)] z-30 hidden flex-col border-r border-line bg-canvas transition-[width] duration-200 md:flex",
        collapsed ? "w-16" : "w-60",
      )}>
        {!hasTitleBar && (
          <div className={cx("flex shrink-0 items-center px-2 pt-3", collapsed ? "justify-center" : "justify-end")}>
            <SidebarToggle collapsed={collapsed} onToggle={toggleSidebar} />
          </div>
        )}
        <SidebarNavigation id="desktop-nav" collapsed={collapsed} />
        {!collapsed && <ServiceStatus />}
      </aside>
      <Drawer id="navigation-drawer" title="Navigation" open={drawerOpen} onClose={() => setDrawerOpen(false)}>
        <SidebarNavigation id="drawer-nav" collapsed={false} onNavigate={() => setDrawerOpen(false)} />
        <ServiceStatus />
      </Drawer>
      <main id="main-content" tabIndex={-1}
        className={cx(
          "min-w-0 pt-[calc(var(--title-bar-height)+72px)] transition-[padding-left] duration-200",
          collapsed ? "md:pl-16" : "md:pl-60",
        )}
      >
        {status === "failed" && <div role="status" className="border-b border-danger bg-danger-soft px-4 py-2 text-xs text-danger sm:px-7">
          Appearance changes are active, but could not be saved. <NavLink to="/settings" className="font-semibold underline">Open Settings to retry.</NavLink>
        </div>}
        <Outlet />
      </main>
    </div>
  );
}

export function Page({
  title,
  kicker,
  description,
  actions,
  breadcrumbs,
  children,
}: {
  title: string;
  kicker?: string;
  description?: ReactNode;
  actions?: ReactNode;
  breadcrumbs?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto w-full max-w-[1480px]">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-line px-4 py-6 sm:px-7">
        <div className="min-w-0">
          {breadcrumbs && <div className="mb-3">{breadcrumbs}</div>}
          {kicker && (
            <div className="text-2xs font-medium uppercase tracking-wider text-ink-faint">
              {kicker}
            </div>
          )}
          <h1 className="mt-0.5 font-display text-2xl font-bold tracking-tight text-ink">
            {title}
          </h1>
          {description && (
            <p className="mt-1 max-w-3xl text-xs leading-relaxed text-ink-muted">
              {description}
            </p>
          )}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </header>
      <div className="animate-fade-up px-4 py-6 sm:px-7">{children}</div>
    </div>
  );
}
