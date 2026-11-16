import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { Page } from "../components/AppShell";
import { Markdown } from "../components/Markdown";
import {
  Callout,
  Chip,
  Disclosure,
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
import { api, type ReportResponse } from "../lib/api";
import { formatFixed, formatSeconds, shortenHash } from "../lib/format";

/*
 * The evidence page for the learned models. Layer order is deliberate:
 * plain-language explanation first, measured numbers second, raw training
 * detail behind disclosures at the end, so non-technical readers can stop
 * after the first two layers and reviewers can still audit everything.
 */

const TARGET_INFO: Record<
  string,
  { label: string; short: string; unit: string; plain: string }
> = {
  max_displacement_mm: {
    label: "Max displacement (mm)",
    short: "How far it bends",
    unit: "mm",
    plain:
      "The distance the free end of the part moves under the load — the \"is it stiff enough?\" number.",
  },
  global_max_von_mises_mpa: {
    label: "Global max Von Mises (MPa)",
    short: "Highest stress anywhere",
    unit: "MPa",
    plain:
      "The single highest stress anywhere in the part. This is the number a strength check compares against the material limit.",
  },
  max_von_mises_roi_mpa: {
    label: "Stress-riser ROI (MPa)",
    short: "Stress at the weak spot",
    unit: "MPa",
    plain:
      "The highest stress around the shape's weak point — the hole or a rounded corner. Cracks usually start here, so it gets its own prediction.",
  },
};

const MODEL_PLAIN: Record<string, string> = {
  ridge: "a simple straight-line formula — very fast, but it misses curved behaviour",
  gaussian_process:
    "a statistical curve fitter that also estimates how unsure it is",
  mlp: "a small neural network — a stack of simple maths layers trained on examples",
  random_forest: "many decision trees voting together",
  xgboost: "boosted trees — each new tree fixes the biggest mistakes of the previous ones",
  ensemble: "an average of several different models, which cancels out individual mistakes",
};

const ALGORITHM_ORDER = [
  "mlp",
  "ensemble",
  "gaussian_process",
  "ridge",
  "random_forest",
  "xgboost",
];

function modelPlain(name: string): string {
  return MODEL_PLAIN[name] ?? "a learned model from the training suite";
}

const CARD_LABELS: Record<string, string> = {
  model_card: "Scalar model card",
  field_model_card: "Field model card",
  scalar_comparison: "Scalar comparison report",
  gnn_report: "Field prediction report",
  optimization_report: "Optimization report",
};

function shortDate(value?: string | null): string {
  if (!value) {
    return "n/a";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "n/a";
  }
  return date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function humanize(name: string): string {
  return name.replace(/_/g, " ");
}

function FeatureGroup({
  title,
  description,
  features,
}: {
  title: string;
  description: string;
  features: string[];
}) {
  return (
    <div>
      <div className="text-2xs font-medium uppercase tracking-wider text-ink-faint">
        {title}
      </div>
      <p className="mt-0.5 text-2xs leading-relaxed text-ink-muted">{description}</p>
      <div className="mt-1.5 flex flex-wrap gap-1">
        {features.map((feature) => (
          <span
            key={feature}
            className="rounded-sm border border-line bg-wash px-1.5 py-0.5 font-mono text-2xs text-ink-muted"
          >
            {feature}
          </span>
        ))}
      </div>
    </div>
  );
}

function AccuracyTable({ target }: { target: ReportResponse["targets"][number] }) {
  return (
    <Table>
      <thead>
        <tr>
          <Th>Model</Th>
          <Th align="right">Validation MAPE</Th>
          <Th align="right">Test MAPE</Th>
          <Th align="right">Test worst</Th>
          <Th align="right">Test R²</Th>
          <Th align="right">Challenge MAPE</Th>
          <Th align="right">Challenge worst</Th>
          <Th align="right">Time / 1k</Th>
        </tr>
      </thead>
      <tbody>
        {target.models.map((row) => {
          const best = row.model === target.best_model;
          return (
            <tr key={row.model} className={cx(best && "bg-accent-soft")}>
              <Td>
                <span
                  className={cx(
                    best ? "font-medium text-ink" : "text-ink-muted",
                  )}
                >
                  {row.model}
                </span>
                {best && (
                  <Chip tone="accent" className="ml-2">
                    selected
                  </Chip>
                )}
              </Td>
              <Td align="right" mono>
                {formatFixed(row.val_mape_pct, 2)}%
              </Td>
              <Td align="right" mono>
                {formatFixed(row.test_mape_pct, 2)}%
              </Td>
              <Td align="right" mono>
                {formatFixed(row.test_worst_pct, 1)}%
              </Td>
              <Td align="right" mono>
                {formatFixed(row.test_r2, 4)}
              </Td>
              <Td align="right" mono>
                {formatFixed(row.challenge_mape_pct, 2)}%
              </Td>
              <Td align="right" mono>
                {formatFixed(row.challenge_worst_pct, 1)}%
              </Td>
              <Td align="right" mono>
                {row.latency_ms_per_1k === null
                  ? "n/a"
                  : `${formatFixed(row.latency_ms_per_1k, 1)} ms`}
              </Td>
            </tr>
          );
        })}
        {target.baselines.map((row) => (
          <tr key={row.name}>
            <Td>
              <span className="text-ink-muted">{row.name}</span>
              <Chip className="ml-2">baseline</Chip>
            </Td>
            <Td align="right" mono>
              —
            </Td>
            <Td align="right" mono>
              {formatFixed(row.test_mape_pct, 2)}%
            </Td>
            <Td align="right" mono>
              {formatFixed(row.test_worst_pct, 1)}%
            </Td>
            <Td align="right" mono>
              —
            </Td>
            <Td align="right" mono>
              —
            </Td>
            <Td align="right" mono>
              —
            </Td>
            <Td align="right" mono>
              n/a
            </Td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
}

export function ModelPage() {
  const report = useQuery({
    queryKey: ["report"],
    queryFn: api.report,
    staleTime: Infinity,
  });
  const data = report.data;
  const [docKey, setDocKey] = useState<string | null>(null);

  const cards = useMemo(() => {
    if (!data) {
      return [];
    }
    return Object.entries(data.cards)
      .filter(([key, body]) => Boolean(body) && key !== "dataset_card")
      .map(([key, body]) => ({
        key,
        label: CARD_LABELS[key] ?? key,
        body: body as string,
      }));
  }, [data]);

  const activeCard = cards.find((card) => card.key === (docKey ?? cards[0]?.key));

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

  const field = data?.field_model ?? null;
  const registryMeta = data?.registry_meta;

  const evaluationSplits = ["val", "test", "challenge"].filter(
    (split) => field?.evaluation?.[split],
  );

  const featureGroups = useMemo(() => {
    const features = registryMeta?.features ?? [];
    const flags: string[] = [];
    const ratios: string[] = [];
    const direct: string[] = [];
    for (const feature of features) {
      if (feature.startsWith("shape_is_")) {
        flags.push(feature);
      } else if (feature.includes("ratio") || feature.includes("slenderness")) {
        ratios.push(feature);
      } else {
        direct.push(feature);
      }
    }
    return { flags, ratios, direct };
  }, [registryMeta]);

  const selectionRule = registryMeta
    ? Object.values(registryMeta.selections ?? {})[0]?.selection_rule
    : null;

  return (
    <Page
      kicker="Evidence"
      title="The model"
      description="What SurroSim predicts, how those predictions are produced, and how accurate they have measured to be on designs the model never saw during training."
      actions={
        data?.git?.commit && (
          <Chip tone="neutral">git {shortenHash(data.git.commit, 8)}</Chip>
        )
      }
    >
      {report.isLoading && (
        <Panel>
          <PanelBody className="flex items-center gap-3">
            <Spinner />{" "}
            <span className="text-xs text-ink-muted">Loading model evidence…</span>
          </PanelBody>
        </Panel>
      )}
      {report.error && <ErrorNote>{String(report.error)}</ErrorNote>}

      {data && (
        <div className="space-y-5">
          <Callout title="In plain words">
            SurroSim does not solve the physics from scratch for every question.
            It uses models that were trained on thousands of examples that were
            already solved with a real finite-element solver. One model answers
            with numbers (how far the part bends, how stressed it gets); another
            answers with a full picture across the whole part. This page explains
            what they are, how they were chosen, and where they stop being
            reliable. The examples they learned from are on the{" "}
            <Link to="/dataset" className="text-link hover:underline">
              Dataset page
            </Link>
            .
          </Callout>

          <Panel>
            <PanelHeader
              kicker="At a glance"
              title="The registry of record"
              description="Every number in the app comes from this trained model directory. Nothing is retrained when the app starts."
            />
            <PanelBody className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-5">
              <Stat
                label="Registry"
                value={
                  <span className="font-mono text-sm">
                    {data.registry
                      .replace(/\\/g, "/")
                      .replace(/^.*?models\//, "models/")}
                  </span>
                }
                sub={`created ${shortDate(registryMeta?.created_utc)}`}
              />
              <Stat
                label="Trained on"
                value={`${data.dataset.row_count?.toLocaleString() ?? "n/a"} cases`}
                sub={
                  <Link to="/dataset" className="text-link hover:underline">
                    dataset {shortenHash(data.dataset.sha256, 10)} →
                  </Link>
                }
              />
              <Stat
                label="Answers"
                value={
                  <span className="font-mono text-base">
                    {data.targets.length} numbers
                  </span>
                }
                sub="displacement, stress, weak-spot stress"
              />
              <Stat
                label="Picture model"
                value={field?.present ? "Available" : "Not installed"}
                sub={field?.present ? field.path : "no trained GNN found"}
              />
              <Stat
                label="Speed"
                value="< 1 ms"
                sub="per design, versus ~10 s for a real solve"
              />
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader
              kicker="What it predicts"
              title="Three numbers per design"
              description="The scalar models take the design parameters and return the three engineering answers below. Each target gets its own trained model — they are not forced to share one."
            />
            <PanelBody className="grid grid-cols-1 gap-3 md:grid-cols-3">
              {data.targets.map((target) => {
                const info = TARGET_INFO[target.target] ?? {
                  label: target.target,
                  short: target.target,
                  unit: "",
                  plain: "",
                };
                const best = target.models.find(
                  (row) => row.model === target.best_model,
                );
                return (
                  <div
                    key={target.target}
                    className="rounded border border-line p-3.5"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="text-2xs font-medium uppercase tracking-wider text-ink-faint">
                          {info.unit || "value"}
                        </div>
                        <div className="mt-0.5 text-xs font-semibold text-ink">
                          {info.short}
                        </div>
                      </div>
                      <Chip tone="accent">{target.best_model}</Chip>
                    </div>
                    <p className="mt-2 text-xs leading-relaxed text-ink-muted">
                      {info.plain}
                    </p>
                    <div className="mt-3 flex items-baseline gap-1.5 border-t border-line pt-2.5">
                      <span className="tnum font-mono text-base font-medium text-ink">
                        {formatFixed(best?.test_mape_pct, 2)}%
                      </span>
                      <span className="text-2xs text-ink-faint">
                        typical miss on unseen designs
                      </span>
                    </div>
                    <p className="mt-1.5 text-2xs leading-relaxed text-ink-faint">
                      Selected model: {target.best_model} —{" "}
                      {modelPlain(target.best_model)}.
                    </p>
                  </div>
                );
              })}
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader
              kicker="How accurate"
              title="Measured against real simulations"
              description="After training, every candidate model is tested on designs it has never seen. Lower percentages are better; the selected row is the one the app actually uses."
            />
            <PanelBody className="space-y-4">
              <Callout title="How to read these numbers" tone="neutral" icon="info">
                <strong className="text-ink">MAPE</strong> is the average miss,
                as a percentage of the true value — 2% means a typical
                prediction is about 2% away from the simulated answer.{" "}
                <strong className="text-ink">Worst</strong> is the single biggest
                miss found in that group.{" "}
                <strong className="text-ink">R²</strong> describes how much of
                the variation between cases the model captures (1.000 is
                perfect). <strong className="text-ink">Validation</strong> was
                used to pick the model; <strong className="text-ink">test</strong>{" "}
                and <strong className="text-ink">challenge</strong> were locked
                away until after selection — the challenge group is
                deliberately filled with awkward corner-of-the-range designs.
              </Callout>
              <div className="space-y-5">
                {data.targets.map((target) => (
                  <div key={target.target}>
                    <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
                      <div className="text-xs font-semibold text-ink">
                        {TARGET_INFO[target.target]?.label ?? target.target}
                      </div>
                      <div className="text-2xs text-ink-faint">
                        Selected: {target.best_model} —{" "}
                        {modelPlain(target.best_model)}
                      </div>
                    </div>
                    <AccuracyTable target={target} />
                  </div>
                ))}
              </div>
              <p className="border-t border-line pt-3 text-2xs leading-relaxed text-ink-faint">
                The last row of each table is a classic textbook beam formula
                (Euler–Bernoulli), listed as a reference point. It ignores holes
                and shape changes, so it is not a competitor — it shows what the
                old way of estimating would have given you. Times are for 1,000
                predictions on this machine; a real solve takes seconds to
                minutes.
              </p>
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader
              kicker="The picture model"
              title="Predicting the whole field, not just three numbers"
              description="The graph neural network (GNN) predicts displacement and stress at every point of a coarse mesh, so the app can draw colour maps for a design it has never solved."
            />
            <PanelBody className="space-y-4">
              {!field?.present && (
                <EmptyState
                  title="No field model is installed"
                  description={`No trained field model was found at ${field?.path ?? "models/gnn"}. The numbers model above still works; field prediction, the Field Prediction page, is unavailable.`}
                />
              )}
              {field?.present && (
                <>
                  <Callout title="In plain words" icon="layers">
                    Think of the mesh as a net of points covering the part. Each
                    point sends short messages to its neighbours about where it
                    sits and what is happening around it. After{" "}
                    {field.config?.layers ?? "several"} rounds of this, every
                    point knows enough about the whole part to say how much it
                    moves and how stressed it is. Training taught the message
                    rules from real solved examples. The result is a full colour
                    map in seconds instead of one number.
                  </Callout>
                  {evaluationSplits.length > 0 ? (
                    <Table>
                      <thead>
                        <tr>
                          <Th>Split</Th>
                          <Th align="right">Cases</Th>
                          <Th align="right">Bend MAPE</Th>
                          <Th align="right">Global stress MAPE</Th>
                          <Th align="right">Weak-spot MAPE</Th>
                          <Th align="right">Typical point error</Th>
                          <Th align="right">95% of points below</Th>
                        </tr>
                      </thead>
                      <tbody>
                        {evaluationSplits.map((split) => {
                          const entry = field.evaluation![split];
                          return (
                            <tr key={split}>
                              <Td>
                                <span className="font-medium text-ink">
                                  {split === "val"
                                    ? "Validation"
                                    : split === "test"
                                      ? "Test"
                                      : "Challenge"}
                                </span>
                              </Td>
                              <Td align="right" mono>
                                {entry.cases ?? "n/a"}
                              </Td>
                              <Td align="right" mono>
                                {formatFixed(entry.max_displacement?.mape, 2)}%
                              </Td>
                              <Td align="right" mono>
                                {formatFixed(entry.global_max_vm?.mape, 2)}%
                              </Td>
                              <Td align="right" mono>
                                {formatFixed(entry.roi_max_vm?.mape, 2)}%
                              </Td>
                              <Td align="right" mono>
                                {formatFixed(
                                  entry.field_vm_error_median_pct,
                                  2,
                                )}
                                %
                              </Td>
                              <Td align="right" mono>
                                {formatFixed(
                                  entry.field_vm_error_p95_pct,
                                  1,
                                )}
                                %
                              </Td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </Table>
                  ) : (
                    <p className="text-xs leading-relaxed text-ink-muted">
                      No separate held-out evaluation file sits next to this
                      checkpoint. The written report in the Documents section
                      below holds the measured results for this training run.
                    </p>
                  )}
                  <p className="text-2xs leading-relaxed text-ink-faint">
                    MAPE columns reduce the predicted picture to the same peak
                    numbers the scalar model predicts. The last two columns look
                    at every point on the mesh and measure how far it is off,
                    relative to the part's highest value — “typical point error”
                    is the middle point, and the 95% column is the worst 5%
                    (mostly points where the true stress is near zero, so a tiny
                    absolute difference looks like a big percentage).
                  </p>
                  <Callout tone="warning" title="Use the picture, not the peak">
                    The field model was trained on a deliberately coarse mesh
                    and is meant for seeing the pattern — where stress
                    concentrates, how the part bends. For final peak values,
                    read the numbers model above, and verify with a real solve
                    before an engineering decision.
                  </Callout>
                  <div className="grid grid-cols-2 gap-4 border-t border-line pt-4 sm:grid-cols-4">
                    <Stat
                      label="Message rounds"
                      value={field.config?.layers ?? "n/a"}
                      sub="how far information travels"
                    />
                    <Stat
                      label="Hidden width"
                      value={field.config?.hidden ?? "n/a"}
                      sub="how much detail per point"
                    />
                    <Stat
                      label="Training time"
                      value={formatSeconds(field.training?.seconds)}
                      sub={`${field.training?.epochs_run ?? "n/a"} epochs on ${field.device ?? "cpu"}`}
                    />
                    <Stat
                      label="Inputs → outputs"
                      value={`${field.node_features.length} → ${field.targets.length}`}
                      sub={`numbers per point → values per point (${field.edge_features.length} for each connection)`}
                    />
                  </div>
                </>
              )}
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader
              kicker="Limits"
              title="Where predictions stop being reliable"
              description="A model is only trustworthy where it has evidence. These are the boundaries of that evidence — they are the reason verification stays one click away."
            />
            <PanelBody className="space-y-3">
              <ul className="space-y-2 text-xs leading-relaxed text-ink-muted">
                <li className="flex gap-2">
                  <span className="text-ink-faint">—</span>
                  <span>
                    <strong className="text-ink">Only the trained ranges.</strong>{" "}
                    The model has seen the parameter ranges shown on the{" "}
                    <Link to="/dataset" className="text-link hover:underline">
                      Dataset page
                    </Link>{" "}
                    and nothing beyond them. A design outside those ranges is a
                    guess, not a prediction. The app flags this and recommends a
                    real solve.
                  </span>
                </li>
                <li className="flex gap-2">
                  <span className="text-ink-faint">—</span>
                  <span>
                    <strong className="text-ink">One kind of physics.</strong>{" "}
                    Linear-elastic, small-strain, single steel material, one
                    static load at the free end. No plasticity, buckling,
                    contact, vibration or heat is modelled.
                  </span>
                </li>
                <li className="flex gap-2">
                  <span className="text-ink-faint">—</span>
                  <span>
                    <strong className="text-ink">Average accuracy hides tail cases.</strong>{" "}
                    Typical misses are a few percent, but the worst individual
                    case in the challenge group can be much larger (see the
                    tables above). Extreme corners of the range are exactly
                    where you should verify.
                  </span>
                </li>
                <li className="flex gap-2">
                  <span className="text-ink-faint">—</span>
                  <span>
                    <strong className="text-ink">No safety factor is included.</strong>{" "}
                    A predicted stress of 180 MPa against a 180 MPa limit is not
                    a pass — it is a signal to check carefully with real
                    analysis.
                  </span>
                </li>
              </ul>
              <div className="flex flex-wrap items-center gap-3 border-t border-line pt-3">
                <Link
                  to="/verify"
                  className="text-xs font-medium text-link hover:underline"
                >
                  Run a real simulation on the FEA Verify page →
                </Link>
                <Link
                  to="/manual/limitations"
                  className="text-xs font-medium text-link hover:underline"
                >
                  Read the full limitations →
                </Link>
              </div>
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader
              kicker="Behind the scenes"
              title="Training details"
              description="The layer below the summary. Open a section when you want to audit exactly how this registry was produced."
            />
            <PanelBody className="space-y-1">
              <Disclosure
                title="How the models were chosen"
                description="Why this model and not another — and how the test groups stayed honest."
              >
                <div className="space-y-3 text-xs leading-relaxed text-ink-muted">
                  {selectionRule && (
                    <p>
                      <strong className="text-ink">Selection rule:</strong>{" "}
                      {selectionRule}
                    </p>
                  )}
                  <p>
                    <strong className="text-ink">Target transform:</strong>{" "}
                    models are trained on log-transformed values (
                    {registryMeta?.target_transform ?? "none"}), then converted
                    back before you see them. This keeps errors proportional
                    across parts that differ by orders of magnitude.
                  </p>
                  <p>
                    <strong className="text-ink">Random seed:</strong>{" "}
                    {registryMeta?.seed ?? "n/a"} — every split, shuffle and
                    initialization is reproducible from it.
                  </p>
                  <div>
                    <div className="text-2xs font-medium uppercase tracking-wider text-ink-faint">
                      Candidates and why each exists
                    </div>
                    <ul className="mt-1.5 space-y-1">
                      {ALGORITHM_ORDER.filter(
                        (name) => MODEL_PLAIN[name],
                      ).map((name) => (
                        <li key={name} className="flex gap-2">
                          <span className="w-32 shrink-0 font-mono text-2xs text-ink">
                            {name}
                          </span>
                          <span className="text-2xs">{MODEL_PLAIN[name]}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </Disclosure>

              <Disclosure
                title={`The ${featureGroups.direct.length + featureGroups.ratios.length + featureGroups.flags.length} numbers that describe a design`}
                description="The model never sees a drawing — only this list of numbers, called features."
              >
                <div className="space-y-4">
                  <FeatureGroup
                    title={`Direct design inputs (${featureGroups.direct.length})`}
                    description="The values you set in the Design Explorer."
                    features={featureGroups.direct}
                  />
                  <FeatureGroup
                    title={`Derived features (${featureGroups.ratios.length})`}
                    description="Calculated combinations that make the physics easier to learn — the same trick an engineer uses with dimensionless ratios."
                    features={featureGroups.ratios}
                  />
                  <FeatureGroup
                    title={`Shape flags (${featureGroups.flags.length})`}
                    description="One flag per shape family, so the model knows which geometry it is looking at."
                    features={featureGroups.flags}
                  />
                </div>
              </Disclosure>

              {field?.present && (
                <Disclosure
                  title="Field model internals"
                  description="What each point in the mesh knows, and what the network predicts."
                >
                  <div className="space-y-4">
                    <FeatureGroup
                      title={`Per-point inputs (${field.node_features.length})`}
                      description="Position, boundary flags and the global design parameters, repeated at every point."
                      features={field.node_features}
                    />
                    <FeatureGroup
                      title={`Per-connection inputs (${field.edge_features.length})`}
                      description="How far and in which direction each point is from its neighbour."
                      features={field.edge_features}
                    />
                    <FeatureGroup
                      title={`Per-point outputs (${field.targets.length})`}
                      description="Three displacement components and six stress components at every point."
                      features={field.targets}
                    />
                    {field.config && (
                      <div className="grid grid-cols-2 gap-x-6 gap-y-1 sm:grid-cols-4">
                        {Object.entries(field.config).map(([key, value]) => (
                          <div key={key} className="flex items-baseline justify-between gap-2">
                            <span className="text-2xs text-ink-faint">
                              {humanize(key)}
                            </span>
                            <span className="tnum font-mono text-2xs text-ink">
                              {String(value)}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}
                    <p className="text-2xs leading-relaxed text-ink-muted">
                      Inputs were standardised (zero mean, unit spread) over{" "}
                      {field.normalisation?.nodes?.toLocaleString() ?? "n/a"}{" "}
                      training points before fitting ({field.normalisation?.target_scaling ?? "no"} target scaling). The held-out evaluation was
                      re-run from the saved checkpoint after training.
                    </p>
                  </div>
                </Disclosure>
              )}

              <Disclosure
                title="Reproduce this registry"
                description="The exact commands that regenerate the dataset and both models from scratch."
              >
                <pre className="thin-scroll overflow-x-auto rounded border border-line bg-wash px-3 py-2.5 font-mono text-2xs leading-relaxed text-ink-muted">
                  {[
                    "# one-command pipeline (Windows launcher)",
                    ".venv\\Scripts\\python.exe tools/run_v2.py --jobs 4",
                    "",
                    "# or stage by stage",
                    "surrosim dataset sample --out data/designs_v2.csv",
                    "surrosim dataset run --designs data/designs_v2.csv --out data/runs_v2 --jobs 4",
                    "surrosim dataset build --designs data/designs_v2.csv --runs data/runs_v2 --out data/dataset_v2",
                    "surrosim train scalar --dataset data/dataset_v2/dataset.csv --out models/scalar/v2",
                    "surrosim train gnn --graphs data/graphs_v2 --runs data/runs_v2_graph --out models/gnn/v2",
                  ].join("\n")}
                </pre>
                <p className="mt-2 text-2xs leading-relaxed text-ink-faint">
                  Dataset sampling, splits, model seeds and the optimizer seed
                  are all explicit (default seed 42), and every artifact records
                  the git commit and dataset hash it was built from.
                </p>
              </Disclosure>
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader
              kicker="Documents"
              title="Written reports and model cards"
              description="Source documents kept with the project. Some describe an earlier registry, so trust the live numbers above first and read these for reasoning and method."
            />
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
                      onClick={() => setDocKey(card.key)}
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

          {figureGroups.map(([group, figures]) => (
            <Panel key={group}>
              <PanelHeader
                kicker="Validation figures"
                title={`Figures · ${group}`}
                description="Measured on held-out designs. Click a figure to open it at full resolution."
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
                        {humanize(figure.name)}
                      </div>
                    </a>
                  ))}
                </div>
              </PanelBody>
            </Panel>
          ))}
        </div>
      )}
    </Page>
  );
}
