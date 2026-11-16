import { useState } from "react";
import { Link } from "react-router-dom";

import { Icon } from "../../components/Icon";
import {
  Callout,
  Chip,
  Panel,
  PanelBody,
  PanelHeader,
  EmptyState,
} from "../../components/ui";
import { ManualLayout } from "./ManualLayout";
import { MANUAL_GROUPS } from "./model";
import { entryById, MANUAL_ENTRIES } from "./registry";

const READING_PATHS: {
  title: string;
  description: string;
  ids: string[];
}[] = [
  {
    title: "I'm new here",
    description:
      "Understand what the system is, the words it uses, and what it can design.",
    ids: ["overview", "glossary", "design-space", "solver"],
  },
  {
    title: "Show me the evidence",
    description:
      "Start from the solved examples and work up to the models and their limits.",
    ids: ["ground-truth", "surrogates", "trust", "provenance"],
  },
  {
    title: "I want to use the workbench",
    description:
      "One short guide per page of the app, in the order you usually meet them.",
    ids: ["app-explorer", "app-field", "app-verify", "app-optimize"],
  },
];

const RELATED_PAGES: { to: string; label: string; description: string }[] = [
  {
    to: "/solver",
    label: "The solver",
    description:
      "The dedicated page for the physics engine, with validation evidence.",
  },
  {
    to: "/model",
    label: "Model",
    description:
      "Live accuracy tables for the learned models, measured on unseen designs.",
  },
  {
    to: "/dataset",
    label: "Dataset",
    description:
      "The solved-example answer key: live ranges, gates and provenance.",
  },
  {
    to: "/verify",
    label: "FEA Verify",
    description: "Run the real CalculiX solve for the current design.",
  },
];

export function ManualHomePage() {
  const [filter, setFilter] = useState("");
  const query = filter.trim().toLowerCase();
  const entries = MANUAL_ENTRIES.filter((entry) =>
    `${entry.title} ${entry.summary}`.toLowerCase().includes(query),
  );
  return (
    <ManualLayout home
      kicker="Reference"
      title="Documentation"
      description="The SurroSim manual, written for readers without an engineering or software background — with the real depth kept underneath."
    >
      <div className="space-y-5">
        <div className="rounded border border-line bg-surface p-4">
          <label htmlFor="manual-topic-filter" className="text-sm font-semibold">Find a topic</label>
          <p id="manual-filter-hint" className="mt-1 text-xs leading-relaxed text-ink-muted">Filter the manual by topic title or summary. To find a word within an article, use Ctrl+F (Command+F on macOS).</p>
          <div className="relative mt-3">
            <Icon name="search" className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-ink-muted" />
            <input id="manual-topic-filter" type="search" value={filter} onChange={(event) => setFilter(event.target.value)} aria-describedby="manual-filter-hint manual-filter-count" placeholder="Try confidence, solver, or appearance" className="h-11 w-full rounded border border-line-strong bg-canvas pl-10 pr-3 text-sm text-ink placeholder:text-ink-muted" />
          </div>
          <p id="manual-filter-count" role="status" className="mt-2 text-xs text-ink-muted">{entries.length} {entries.length === 1 ? "topic" : "topics"}{query ? " match your filter." : " in the manual."}</p>
        </div>
        {!query && <>
        <Callout title="How this manual is written" icon="book-open">
          Every page starts with the plain-language version of the idea, then
          adds the real detail underneath: names, numbers and trade-offs
          included. Terms are explained where they first appear and collected in
          the{" "}
          <Link to="/manual/glossary" className="text-link hover:underline">
            glossary
          </Link>
          . Nothing here is a shallow summary — simple words, full depth.
        </Callout>

        <Panel>
          <PanelHeader
            kicker="Reading paths"
            title="Where to start"
            description="Three routes through the manual, depending on what you need right now."
          />
          <PanelBody className="grid grid-cols-1 gap-3 md:grid-cols-3">
            {READING_PATHS.map((path) => (
              <div key={path.title} className="rounded border border-line p-3.5">
                <div className="text-xs font-semibold text-ink">
                  {path.title}
                </div>
                <p className="mt-1 text-xs leading-relaxed text-ink-muted">
                  {path.description}
                </p>
                <ol className="mt-2.5 space-y-1">
                  {path.ids.map((id, index) => {
                    const entry = entryById(id);
                    if (!entry) {
                      return null;
                    }
                    return (
                      <li key={id}>
                        <Link
                          to={entry.to}
                          className="flex items-baseline gap-2 text-xs text-link hover:underline"
                        >
                          <span className="tnum font-mono text-2xs text-ink-faint">
                            {index + 1}
                          </span>
                          {entry.title}
                        </Link>
                      </li>
                    );
                  })}
                </ol>
              </div>
            ))}
          </PanelBody>
        </Panel>
        </>}

        {entries.length === 0 && <Panel><PanelBody><EmptyState title="No matching topics" description="Try a broader word such as model, design, or solver, or clear the filter to browse every topic." action={<button type="button" onClick={() => setFilter("")} className="min-h-11 rounded border border-line-strong px-3 text-xs font-medium hover:bg-wash">Clear filter</button>} /></PanelBody></Panel>}

        {MANUAL_GROUPS.map((group) => {
          const groupEntries = entries.filter(
            (entry) => entry.group === group.id,
          );
          if (!groupEntries.length) {
            return null;
          }
          return (
            <Panel key={group.id}>
              <PanelHeader
                kicker="Manual"
                title={group.label}
                description={group.blurb}
              />
              <PanelBody className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {groupEntries.map((entry) => (
                  <Link
                    key={entry.id}
                    to={entry.to}
                    className="group flex flex-col rounded border border-line p-3.5 transition-colors hover:border-accent-border hover:bg-accent-soft"
                  >
                    <span className="flex items-baseline justify-between gap-3">
                      <span className="text-xs font-semibold text-ink transition-colors group-hover:text-accent-ink">
                        {entry.title}
                      </span>
                      <span className="shrink-0 text-2xs text-ink-faint">
                        {entry.minutes} min
                      </span>
                    </span>
                    <span className="mt-1 text-xs leading-relaxed text-ink-muted">
                      {entry.summary}
                    </span>
                    {entry.standalone && (
                      <span className="mt-2">
                        <Chip tone="accent">Dedicated page</Chip>
                      </span>
                    )}
                  </Link>
                ))}
              </PanelBody>
            </Panel>
          );
        })}

        {!query && <Panel>
          <PanelHeader
            kicker="Evidence"
            title="Related pages in the app"
            description="Where the claims in this manual are shown with live numbers."
          />
          <PanelBody className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
            {RELATED_PAGES.map((page) => (
              <Link
                key={page.to}
                to={page.to}
                className="group rounded border border-line p-3.5 transition-colors hover:border-accent-border hover:bg-accent-soft"
              >
                <span className="text-xs font-semibold text-ink transition-colors group-hover:text-accent-ink">
                  {page.label}
                </span>
                <span className="mt-1 block text-xs leading-relaxed text-ink-muted">
                  {page.description}
                </span>
              </Link>
            ))}
          </PanelBody>
        </Panel>}
      </div>
    </ManualLayout>
  );
}
