import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";

import { Page } from "../../components/AppShell";
import { Icon } from "../../components/Icon";
import { Drawer } from "../../components/Drawer";
import { DocumentationContext } from "../../components/documentation";
import { cx } from "../../lib/cx";
import { MANUAL_GROUPS, type ManualEntry } from "./model";
import { MANUAL_ENTRIES } from "./registry";

/*
 * Shared chrome for the manual and the solver page: the standard page header
 * plus a grouped table of contents that stays visible while reading.
 */

function ManualNav({ onNavigate }: { onNavigate?: () => void }) {
  return (
        <nav aria-label="Manual topics" className="thin-scroll space-y-5 overflow-y-auto p-3" onClick={(event) => {
          if ((event.target as HTMLElement).closest("a") && !event.ctrlKey && !event.metaKey && !event.shiftKey) onNavigate?.();
        }}>
          <NavLink
            to="/manual"
            end
            className="flex min-h-11 items-center rounded px-2.5 text-xs font-medium text-ink-muted transition-colors hover:bg-wash hover:text-ink aria-[current=page]:bg-accent-soft aria-[current=page]:font-bold aria-[current=page]:text-accent-ink"
          >
            Documentation home
          </NavLink>
          {MANUAL_GROUPS.map((group) => {
            const entries = MANUAL_ENTRIES.filter(
              (entry) => entry.group === group.id,
            );
            if (!entries.length) {
              return null;
            }
            return (
              <div key={group.id}>
                <div className="px-2.5 pb-2 text-2xs font-medium uppercase tracking-wider text-ink-muted">
                  {group.label}
                </div>
                <ul aria-label={group.label} className="space-y-0.5">
                  {entries.map((entry) => (
                    <li key={entry.id}>
                      <NavLink
                        to={entry.to}
                        className="flex min-h-11 items-center gap-2 rounded px-2.5 py-2 text-xs font-medium text-ink-muted transition-colors hover:bg-wash hover:text-ink aria-[current=page]:bg-accent-soft aria-[current=page]:font-bold aria-[current=page]:text-accent-ink"
                      >
                        <span className="min-w-0 flex-1 leading-relaxed">
                          {entry.title}
                        </span>
                        {entry.standalone && (
                          <Icon
                            name="external-link"
                            className="h-3 w-3 shrink-0 text-ink-faint"
                          />
                        )}
                      </NavLink>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </nav>
  );
}

type Heading = { id: string; title: string };

function useArticleOutline(ref: React.RefObject<HTMLElement>, path: string) {
  const [headings, setHeadings] = useState<Heading[]>([]);
  const [active, setActive] = useState("");
  useEffect(() => {
    const article = ref.current;
    if (!article) return;
    let frame = 0;
    const updateActive = () => {
      frame = 0;
      const elements = Array.from(article.querySelectorAll<HTMLElement>("h2[id]"));
      const bar = Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--title-bar-height")) || 0;
      const passed = elements.filter((heading) => heading.getBoundingClientRect().top <= bar + 96);
      setActive((passed[passed.length - 1] ?? elements[0])?.id ?? "");
    };
    const schedule = () => { if (!frame) frame = requestAnimationFrame(updateActive); };
    const collect = () => {
      const next = Array.from(article.querySelectorAll<HTMLElement>("h2[id]"))
        .map((heading) => ({ id: heading.id, title: heading.firstChild?.textContent?.trim() ?? "" }));
      setHeadings((current) => JSON.stringify(current) === JSON.stringify(next) ? current : next);
      schedule();
    };
    collect();
    const observer = new MutationObserver(collect);
    observer.observe(article, { childList: true, subtree: true });
    const resize = new ResizeObserver(schedule);
    resize.observe(article);
    window.addEventListener("scroll", schedule, { passive: true });
    window.addEventListener("resize", schedule);
    return () => {
      observer.disconnect();
      resize.disconnect();
      window.removeEventListener("scroll", schedule);
      window.removeEventListener("resize", schedule);
      cancelAnimationFrame(frame);
    };
  }, [ref, path]);
  return { headings, active };
}

export function ManualLayout({
  kicker,
  title,
  description,
  actions,
  children,
  home = false,
}: {
  kicker: string;
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  home?: boolean;
}) {
  const location = useLocation();
  const article = useRef<HTMLElement>(null);
  const { headings, active } = useArticleOutline(article, location.pathname);
  const [topicsOpen, setTopicsOpen] = useState(false);
  const entry = MANUAL_ENTRIES.find((item) => item.to === location.pathname);

  useEffect(() => {
    const wide = window.matchMedia("(min-width: 1100px)");
    const onResize = () => { if (wide.matches) setTopicsOpen(false); };
    wide.addEventListener("change", onResize);
    return () => wide.removeEventListener("change", onResize);
  }, []);

  useEffect(() => {
    const scrollToSection = () => {
      let id = "";
      try { id = decodeURIComponent(window.location.hash.slice(1)); } catch { /* malformed link */ }
      const target = id ? document.getElementById(id) : null;
      if (target && article.current?.contains(target)) {
        target.scrollIntoView();
        target.focus({ preventScroll: true });
      } else if (!id) {
        window.scrollTo({ top: 0 });
      }
    };
    const frame = requestAnimationFrame(scrollToSection);
    window.addEventListener("hashchange", scrollToSection);
    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener("hashchange", scrollToSection);
    };
  }, [location.pathname, location.hash]);

  return (
    <Page
      kicker={kicker}
      title={title}
      description={description}
      actions={actions}
      breadcrumbs={!home && <nav aria-label="Breadcrumb" className="text-xs text-ink-muted">
        <ol className="flex flex-wrap items-center gap-2">
          <li><Link to="/manual" className="text-link hover:underline">Documentation</Link></li>
          {entry && <li className="flex items-center gap-2"><Icon name="chevron-right" className="h-3 w-3" /><span>{MANUAL_GROUPS.find((group) => group.id === entry.group)?.label}</span></li>}
          <li className="flex items-center gap-2"><Icon name="chevron-right" className="h-3 w-3" /><span aria-current="page">{title}</span></li>
        </ol>
      </nav>}
    >
      <div className="mb-4 min-[1100px]:hidden">
        <button type="button" onClick={() => setTopicsOpen(true)} aria-expanded={topicsOpen} aria-controls="manual-topics-drawer" className="inline-flex min-h-11 items-center gap-2 rounded border border-line-strong bg-surface px-3 text-xs font-medium hover:bg-wash">
          <Icon name="book-open" className="h-4 w-4" />Browse manual topics<Icon name="chevron-down" className="h-3.5 w-3.5" />
        </button>
      </div>
      <Drawer id="manual-topics-drawer" title="Manual topics" open={topicsOpen} onClose={() => setTopicsOpen(false)}>
        <ManualNav onNavigate={() => setTopicsOpen(false)} />
      </Drawer>
      <div className={cx("grid grid-cols-1 items-start gap-6 min-[1100px]:grid-cols-[208px_minmax(0,1fr)]", !home && "min-[1536px]:grid-cols-[208px_minmax(0,1fr)_172px]")}>
        <aside className="sticky top-[calc(var(--title-bar-height)+24px)] hidden max-h-[calc(100dvh-var(--title-bar-height)-48px)] overflow-y-auto rounded border border-line bg-surface min-[1100px]:block">
          <ManualNav />
        </aside>
        <DocumentationContext.Provider value={true}>
          <article ref={article} aria-label={title} className="manual-article space-y-5">{children}</article>
        </DocumentationContext.Provider>
        {!home && headings.length > 0 && <nav aria-label="On this page" className="sticky top-[calc(var(--title-bar-height)+24px)] hidden max-h-[calc(100dvh-var(--title-bar-height)-48px)] overflow-y-auto border-l border-line pl-4 min-[1536px]:block">
          <h2 className="mb-2 text-2xs font-semibold uppercase tracking-wider text-ink-muted">On this page</h2>
          <ul className="space-y-1">
            {headings.map((heading) => <li key={heading.id}><a href={`#${heading.id}`} aria-current={active === heading.id ? "location" : undefined} className="block rounded px-2 py-2.5 text-xs leading-relaxed text-ink-muted hover:bg-wash hover:text-ink aria-[current=location]:bg-accent-soft aria-[current=location]:font-bold aria-[current=location]:text-accent-ink">{heading.title}</a></li>)}
          </ul>
        </nav>}
      </div>
    </Page>
  );
}

export function ManualFooterNav({
  previous,
  next,
}: {
  previous: ManualEntry | null;
  next: ManualEntry | null;
}) {
  return (
    <nav
      aria-label="Manual sections"
      className="grid grid-cols-1 gap-3 border-t border-line pt-5 sm:grid-cols-2"
    >
      {previous ? (
        <Link
          to={previous.to}
          className="group rounded border border-line p-3 transition-colors hover:border-accent-border hover:bg-accent-soft"
        >
          <span className="flex items-center gap-1.5 text-2xs font-medium uppercase tracking-wider text-ink-faint">
            <Icon name="arrow-left" className="h-3 w-3" />
            Previous
          </span>
          <span className="mt-1 block text-xs font-medium text-ink transition-colors group-hover:text-accent-ink">
            {previous.title}
          </span>
        </Link>
      ) : (
        <span className="hidden sm:block" />
      )}
      {next ? (
        <Link
          to={next.to}
          className="group rounded border border-line p-3 text-right transition-colors hover:border-accent-border hover:bg-accent-soft sm:col-start-2"
        >
          <span className="flex items-center justify-end gap-1.5 text-2xs font-medium uppercase tracking-wider text-ink-faint">
            Next
            <Icon name="arrow-right" className="h-3 w-3" />
          </span>
          <span className="mt-1 block text-xs font-medium text-ink transition-colors group-hover:text-accent-ink">
            {next.title}
          </span>
        </Link>
      ) : null}
    </nav>
  );
}
