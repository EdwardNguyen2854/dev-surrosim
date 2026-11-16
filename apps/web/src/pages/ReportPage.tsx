import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { Page } from "../components/AppShell";
import { Markdown } from "../components/Markdown";
import {
  Chip,
  EmptyState,
  ErrorNote,
  Panel,
  PanelBody,
  PanelHeader,
  Spinner,
  Stat,
  Table,
  Td,
  Th,
  cx,
} from "../components/ui";
import { api } from "../lib/api";
import { formatFixed, shortenHash } from "../lib/format";

const TARGET_LABELS: Record<string, string> = {
  max_displacement_mm: "Max displacement (mm)",
  global_max_von_mises_mpa: "Global max Von Mises (MPa)",
  max_von_mises_roi_mpa: "Hole-ROI max Von Mises (MPa)",
};

const CARD_LABELS: Record<string, string> = {
  model_card: "Scalar model card",
  field_model_card: "Field model card",
  dataset_card: "Dataset card",
  scalar_comparison: "Scalar comparison report",
  gnn_report: "Field prediction report",
  optimization_report: "Optimization report",
};

export function ReportPage() {
  const report = useQuery({
    queryKey: ["report"],
    queryFn: api.report,
    staleTime: Infinity,
  });
  const data = report.data;
  const [tab, setTab] = useState<string | null>(null);

  const cards = useMemo(() => {
    if (!data) {
      return [];
    }
    return Object.entries(data.cards)
      .filter(([, body]) => Boolean(body))
      .map(([key, body]) => ({
        key,
        label: CARD_LABELS[key] ?? key,
        body: body as string,
      }));
  }, [data]);

  const activeCard = cards.find((card) => card.key === (tab ?? cards[0]?.key));

  const figureGroups = useMemo(() => {
    if (!data) {
      return [];
    }
    const groups = new Map<string, typeof data.figures>();
    for (const figure of data.figures) {
      const list = groups.get(figure.group) ?? [];
      list.push(figure);
      groups.set(figure.group, list);
    }
    return [...groups.entries()];
  }, [data]);

  return (
    <Page
      kicker="Evidence"
      title="Model & dataset"
      description="The registry, its dataset of record and the validation reports behind every prediction the app makes."
      actions={
        data?.git?.commit && (
          <Chip tone="neutral">git {shortenHash(data.git.commit, 8)}</Chip>
        )
      }
    >
      {report.isLoading && (
        <Panel>
          <PanelBody className="flex items-center gap-3">
            <Spinner /> <span className="text-xs text-ink-muted">Loading registry report…</span>
          </PanelBody>
        </Panel>
      )}
      {report.error && <ErrorNote>{String(report.error)}</ErrorNote>}

      {data && (
        <div className="space-y-5">
          <Panel>
            <PanelHeader
              kicker="Registry of record"
              title={data.registry.replace(/\\/g, "/").replace(/^.*?models\//, "models/")}
              description={`Created ${new Date(data.created_utc).toLocaleString()}`}
            />
            <PanelBody className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Stat
                label="Dataset sha256"
                value={shortenHash(data.dataset.sha256, 12)}
                sub={data.dataset.path?.split(/[\\/]/).pop()}
              />
              <Stat
                label="Rows"
                value={data.dataset.row_count?.toLocaleString() ?? "n/a"}
              />
              <Stat
                label="Splits"
                value={
                  data.dataset.split_counts
                    ? Object.entries(data.dataset.split_counts)
                        .map(([name, count]) => `${name} ${count}`)
                        .join(" · ")
                    : "n/a"
                }
              />
              <Stat
                label="Targets"
                value={data.targets.length.toString()}
                sub={data.targets.map((target) => target.target.replace(/_/g, " ")).join(", ")}
              />
            </PanelBody>
          </Panel>

          {data.targets.map((target) => (
            <Panel key={target.target}>
              <PanelHeader
                kicker="Model comparison"
                title={TARGET_LABELS[target.target] ?? target.target}
                description={`Selected model: ${target.best_model}`}
              />
              <PanelBody>
                <Table>
                  <thead>
                    <tr>
                      <Th>Model</Th>
                      <Th align="right">Test MAPE</Th>
                      <Th align="right">Test worst</Th>
                      <Th align="right">Test RMSE</Th>
                      <Th align="right">Challenge MAPE</Th>
                      <Th align="right">Challenge worst</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {target.models.map((row) => {
                      const best = row.model === target.best_model;
                      return (
                        <tr key={row.model} className={cx(best && "bg-accent-soft")}>
                          <Td>
                            <span className={cx(best ? "font-medium text-ink" : "text-ink-muted")}>
                              {row.model}
                            </span>
                            {best && (
                              <Chip tone="accent" className="ml-2">
                                selected
                              </Chip>
                            )}
                          </Td>
                          <Td align="right" mono>
                            {formatFixed(row.test_mape_pct, 2)}%
                          </Td>
                          <Td align="right" mono>
                            {formatFixed(row.test_worst_pct, 1)}%
                          </Td>
                          <Td align="right" mono>
                            {row.test_rmse === null ? "n/a" : formatFixed(row.test_rmse, 4)}
                          </Td>
                          <Td align="right" mono>
                            {formatFixed(row.challenge_mape_pct, 2)}%
                          </Td>
                          <Td align="right" mono>
                            {formatFixed(row.challenge_worst_pct, 1)}%
                          </Td>
                        </tr>
                      );
                    })}
                  </tbody>
                </Table>
              </PanelBody>
            </Panel>
          ))}

          {figureGroups.map(([group, figures]) => (
            <Panel key={group}>
              <PanelHeader
                kicker="Validation figures"
                title={`Figures · ${group}`}
                description="Click a figure to open it at full resolution."
              />
              <PanelBody>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {figures.map((figure) => (
                    <a
                      key={figure.url}
                      href={figure.url}
                      target="_blank"
                      rel="noreferrer"
                      className="group block"
                    >
                      <div className="overflow-hidden rounded border border-line bg-wash">
                        <img
                          src={figure.url}
                          alt={figure.name}
                          loading="lazy"
                          className="h-auto w-full transition-transform duration-300 group-hover:scale-[1.015]"
                        />
                      </div>
                      <div className="mt-1.5 truncate text-2xs text-ink-muted">
                        {figure.name.replace(/_/g, " ")}
                      </div>
                    </a>
                  ))}
                </div>
              </PanelBody>
            </Panel>
          ))}

          <Panel>
            <PanelHeader kicker="Documents" title="Reports and cards" />
            {cards.length === 0 ? (
              <PanelBody>
                <EmptyState title="No written reports found" />
              </PanelBody>
            ) : (
              <>
                <div
                  className="flex flex-wrap gap-1 border-b border-line px-4 py-2.5"
                  role="group"
                  aria-label="Reports and cards"
                >
                  {cards.map((card) => (
                    <button
                      key={card.key}
                      type="button"
                      onClick={() => setTab(card.key)}
                      aria-pressed={card.key === activeCard?.key}
                      className={cx(
                        "rounded px-2.5 py-1 text-2xs font-medium uppercase tracking-wider transition-colors",
                        card.key === activeCard?.key
                          ? "bg-accent-soft text-accent-ink"
                          : "text-ink-muted hover:bg-wash hover:text-ink",
                      )}
                    >
                      {card.label}
                    </button>
                  ))}
                </div>
                <PanelBody className="thin-scroll max-h-[36rem] overflow-y-auto">
                  {activeCard && <Markdown>{activeCard.body}</Markdown>}
                </PanelBody>
              </>
            )}
          </Panel>
        </div>
      )}
    </Page>
  );
}
