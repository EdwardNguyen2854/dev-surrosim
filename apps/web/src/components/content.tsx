import type { ReactNode } from "react";

import { cx } from "../lib/cx";
import { Icon, type IconName } from "./Icon";
import { CodeBlock } from "./CodeBlock";

/*
 * Small presentational blocks for explanatory content (the Solver reference
 * page and the manual). They mirror the pipeline lists and definition styles
 * already used on the evidence pages so the whole app reads the same way.
 */

export function Steps({
  items,
}: {
  items: { icon?: IconName; title: ReactNode; body: ReactNode }[];
}) {
  return (
    <ol className="space-y-3">
      {items.map((item, index) => (
        <li key={index} className="flex gap-3">
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded border border-line bg-wash">
            {item.icon ? (
              <Icon
                name={item.icon}
                className="h-3.5 w-3.5 text-accent-strong"
              />
            ) : (
              <span className="tnum font-mono text-2xs text-ink-faint">
                {String(index + 1).padStart(2, "0")}
              </span>
            )}
          </div>
          <div className="min-w-0">
            <div className="flex items-baseline gap-2">
              <span className="tnum font-mono text-2xs text-ink-faint">
                {String(index + 1).padStart(2, "0")}
              </span>
              <span className="text-xs font-medium text-ink">{item.title}</span>
            </div>
            <div className="mt-0.5 text-xs leading-relaxed text-ink-muted">
              {item.body}
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}

export function Terms({
  items,
  columns = 2,
}: {
  items: { term: ReactNode; body: ReactNode }[];
  columns?: 1 | 2;
}) {
  return (
    <dl
      className={cx(
        "grid grid-cols-1 gap-x-8 gap-y-3",
        columns === 2 && "md:grid-cols-2",
      )}
    >
      {items.map((item, index) => (
        <div key={index}>
          <dt className="text-xs font-medium text-ink">{item.term}</dt>
          <dd className="mt-0.5 text-xs leading-relaxed text-ink-muted">
            {item.body}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function QA({
  items,
}: {
  items: { q: ReactNode; a: ReactNode }[];
}) {
  return (
    <div>
      {items.map((item, index) => (
        <div
          key={index}
          className="border-t border-line py-3.5 first:border-t-0 first:pt-0 last:pb-0"
        >
          <div className="text-xs font-semibold text-ink">{item.q}</div>
          <div className="mt-1 text-xs leading-relaxed text-ink-muted">
            {item.a}
          </div>
        </div>
      ))}
    </div>
  );
}

export function Chain({ lines }: { lines: string[] }) {
  return (
    <CodeBlock language="text" label="Pipeline reference">{lines.join("\n")}</CodeBlock>
  );
}
