import { useMemo } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { Page } from "../components/AppShell";
import { Markdown } from "../components/Markdown";
import { Icon, type IconName } from "../components/Icon";
import {
  Callout,
  Chip,
  Disclosure,
  EmptyState,
  ErrorNote,
  KeyValue,
  Panel,
  PanelBody,
  PanelHeader,
  Spinner,
  Stat,
  Table,
  Td,
  Th,
} from "../components/ui";
import { api, type RangeStat } from "../lib/api";
import { shortenHash } from "../lib/format";

/*
 * The evidence page for the training dataset. Same layered structure as the
 * Model page: plain language first, measured tables second, provenance and
 * regeneration commands last.
 */

const VARIABLE_INFO: Record<string, { label: string; note?: string }> = {
  length_mm: { label: "Length", note: "how long the part is" },
  width_mm: { label: "Width" },
  thickness_mm: { label: "Thickness", note: "drives bending stiffness the most" },
  hole_diameter_mm: { label: "Hole diameter", note: "0 means no hole" },
  hole_x_mm: { label: "Hole position", note: "distance from the clamped end" },
  hole2_diameter_mm: {
    label: "Second hole diameter",
    note: "two-hole plates only; 0 means none",
  },
  hole2_x_mm: { label: "Second hole position" },
  tip_width_mm: { label: "Tip width", note: "free-end width of tapered parts" },
  step_x_mm: { label: "Step position", note: "where the section height changes" },
  step_thickness_mm: { label: "Step thickness" },
  fillet_radius_mm: { label: "Corner radius", note: "0 means a sharp corner" },
  flange_width_mm: { label: "Flange width", note: "I-beam and L-bracket only" },
  beam_depth_mm: { label: "Beam depth" },
  flange_thickness_mm: { label: "Flange thickness" },
  web_thickness_mm: { label: "Web thickness" },
  height_mm: { label: "Height", note: "L-bracket leg length" },
  force_n: { label: "Force", note: "pull at the free end" },
  youngs_modulus_mpa: {
    label: "Young's modulus",
    note: "steel stiffness — fixed, not varied",
  },
  poisson_ratio: {
    label: "Poisson's ratio",
    note: "how the material bulges sideways — fixed at 0.30",
  },
  mesh_size_mm: { label: "Mesh size", note: "how finely the part was divided" },
};

const TARGET_INFO: Record<string, { label: string; plain: string }> = {
  max_displacement_mm: {
    label: "Max displacement",
    plain: "How far the free end moved. Smaller is stiffer.",
  },
  global_max_von_mises_mpa: {
    label: "Global max stress",
    plain: "The highest stress found anywhere in the part.",
  },
  max_von_mises_roi_mpa: {
    label: "Weak-spot stress",
    plain:
      "The highest stress around the hole or rounded corner. Empty for shapes without a weak-spot region (no-hole plates).",
  },
};

const GATE_PLAIN: Record<string, string> = {
  "solver status == SUCCESS": "The solver must report a clean finish.",
  "deck total force matches requested force":
    "The load actually applied must equal the load we asked for.",
  "mesh nodes >= 500": "The mesh must be fine enough to trust.",
  "fields.npz present": "The full-field file must exist for the picture model.",
  "displacement and global stress finite and positive":
    "Answers must be real numbers, not zeros or infinities.",
  "ROI stress finite and positive when defined":
    "Weak-spot stress must be valid wherever the shape has one.",
};

const SPLIT_INFO: Record<
  string,
  { title: string; plain: string; tone: "accent" | "neutral" | "success" | "warning" }
> = {
  train: {
    title: "Training pile",
    plain: "The study material — the models learn from these cases.",
    tone: "accent",
  },
  val: {
    title: "Validation pile",
    plain:
      "A practice exam — used to choose between competing model designs.",
    tone: "neutral",
  },
  test: {
    title: "Test pile",
    plain:
      "The final exam — untouched until the model was frozen, then checked once.",
    tone: "success",
  },
  challenge: {
    title: "Challenge pile",
    plain:
      "The hardest pile — corner cases at the edges of the range, never used for tuning. The honest stress test.",
    tone: "warning",
  },
};

const PIPELINE: { icon: IconName; title: string; body: string }[] = [
  {
    icon: "sliders",
    title: "Pick a design",
    body: "A sampling routine chooses parameter combinations across the whole range, plus deliberately awkward corner cases. The choices are frozen into a table with fixed splits before any solving starts.",
  },
  {
    icon: "package",
    title: "Build the shape",
    body: "The numbers become a real CAD geometry: plate with hole, two-hole plate, tapered plate, stepped plate, I-beam or L-bracket.",
  },
  {
    icon: "layers",
    title: "Cut it into a mesh",
    body: "The part is divided into small quadratic tetrahedra (C3D10) so the physics can be computed piece by piece. The mesh is refined around holes and rounded corners, where stress changes fastest.",
  },
  {
    icon: "cpu",
    title: "Solve for real",
    body: "The finite-element solver CalculiX applies the load, clamps the base and solves the static problem. Median solve time: 9.8 s per case; the whole dataset used about 11 hours of pure solver time.",
  },
  {
    icon: "file-text",
    title: "Record the answers",
    body: "Each solved case keeps the three peak values plus a full-field file (displacement and stress at every mesh point) — the same files the picture model later learned from.",
  },
  {
    icon: "shield-check",
    title: "Pass the quality gates",
    body: "A case becomes training material only after every gate passes: clean solver finish, exact force balance, enough mesh points, field files present and finite positive answers. Failures are logged and excluded.",
  },
];

function formatMeasure(value: number): string {
  return Number(value.toFixed(3)).toLocaleString(undefined, {
    maximumFractionDigits: 3,
  });
}

function unitFor(name: string): string {
  if (name.endsWith("_mm")) return "mm";
  if (name.endsWith("_n")) return "N";
  if (name.endsWith("_mpa")) return "MPa";
  return "–";
}

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

function hoursFromSeconds(seconds?: number | null): string {
  if (!seconds || !Number.isFinite(seconds)) {
    return "n/a";
  }
  return `${(seconds / 3600).toFixed(1)} h`;
}

function RangeTable({
  rows,
  emptyText,
}: {
  rows: RangeStat[];
  emptyText: string;
}) {
  if (rows.length === 0) {
    return <EmptyState title={emptyText} />;
  }
  return (
    <Table>
      <thead>
        <tr>
          <Th>Quantity</Th>
          <Th align="right">Smallest seen</Th>
          <Th align="right">Typical</Th>
          <Th align="right">Largest seen</Th>
          <Th>In plain words</Th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => {
          const info = VARIABLE_INFO[row.name];
          const unit = unitFor(row.name);
          return (
            <tr key={row.name}>
              <Td>
                <div className="text-ink">{info?.label ?? row.name}</div>
                <div className="font-mono text-2xs text-ink-faint">
                  {row.name}
                  {unit !== "–" ? ` · ${unit}` : ""}
                </div>
              </Td>
              <Td align="right" mono>
                {formatMeasure(row.min)}
              </Td>
              <Td align="right" mono>
                {formatMeasure(row.mean)}
              </Td>
              <Td align="right" mono>
                {formatMeasure(row.max)}
              </Td>
              <Td className="max-w-[22rem] text-ink-muted">
                {info?.note ?? ""}
              </Td>
            </tr>
          );
        })}
      </tbody>
    </Table>
  );
}

export function DatasetPage() {
  const dataset = useQuery({
    queryKey: ["dataset-report"],
    queryFn: api.datasetReport,
    staleTime: Infinity,
  });
  const config = useQuery({
    queryKey: ["config"],
    queryFn: api.config,
    staleTime: Infinity,
  });
  const data = dataset.data;
  const shapeCounts = data?.shape_counts ?? {};
  const designRanges = data?.design_ranges ?? [];
  const targetRanges = data?.target_ranges ?? [];
  const splitCounts = data?.split_counts ?? {};
  const mesh = data?.mesh ?? {
    median_nodes: null,
    median_elements: null,
    element_type: null,
  };

  const shapeRows = useMemo(() => {
    const shapes = config.data?.shapes ?? [];
    return Object.entries(shapeCounts).map(([kind, count]) => {
      const spec = shapes.find((shape) => shape.kind === kind);
      return {
        kind,
        count,
        label: spec?.label ?? kind.replace(/_/g, " "),
        summary: spec?.summary ?? "",
      };
    });
  }, [shapeCounts, config.data]);

  const orderedSplits = ["train", "val", "test", "challenge"]
    .map((key) => [key, splitCounts[key]] as const)
    .filter(([, count]) => typeof count === "number");

  return (
    <Page
      kicker="Evidence"
      title="The dataset"
      description="The solved examples behind every prediction: how they were built, what they cover, and how each one earned its place as training material."
      actions={
        data && (
          <Chip tone="neutral">sha {shortenHash(data.sha256, 10)}</Chip>
        )
      }
    >
      {dataset.isLoading && (
        <Panel>
          <PanelBody className="flex items-center gap-3">
            <Spinner />{" "}
            <span className="text-xs text-ink-muted">
              Loading dataset evidence…
            </span>
          </PanelBody>
        </Panel>
      )}
      {dataset.error && <ErrorNote>{String(dataset.error)}</ErrorNote>}

      {data && (
        <div className="space-y-5">
          <Callout title="In plain words">
            This is the answer key the models studied. It holds{" "}
            {data.row_count?.toLocaleString() ?? "the"} cantilever designs, and
            every single one was solved with a real physics solver — no
            shortcuts, no estimates. The models only ever see these examples, so
            this page doubles as the trust boundary: it shows exactly which
            designs the predictions can be relied on for, and which are outside
            the evidence. The models trained on it are on the{" "}
            <Link to="/model" className="text-link hover:underline">
              Model page
            </Link>
            .
          </Callout>

          <Panel>
            <PanelHeader
              kicker="At a glance"
              title="What is in the dataset"
              description="Counts and cost taken from the dataset manifest and the data table itself."
            />
            <PanelBody className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-6">
              <Stat
                label="Solved cases"
                value={data.row_count?.toLocaleString() ?? "n/a"}
                sub="all with complete results"
              />
              <Stat
                label="Shape families"
                value={Object.keys(shapeCounts).length || "n/a"}
                sub="from simple plates to I-beams"
              />
              <Stat
                label="Rejected cases"
                value={data.manifest?.cases_failed ?? 0}
                tone={data.manifest?.cases_failed ? "warning" : "success"}
                sub="failed or gated out"
              />
              <Stat
                label="Solver"
                value={`CalculiX ${data.manifest?.solver?.versions?.join(", ") ?? ""}`}
                sub="real finite-element solves"
              />
              <Stat
                label="Solver time"
                value={hoursFromSeconds(data.manifest?.solver?.total_solver_seconds)}
                sub="pure compute, no training"
              />
              <Stat
                label="Content hash"
                value={
                  <span className="font-mono text-sm">
                    {shortenHash(data.sha256, 12)}
                  </span>
                }
                sub={`created ${shortDate(data.created_utc)}`}
              />
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader
              kicker="How it was made"
              title="From parameters to a solved case"
              description="Every row in the dataset went through the same six steps. Each step has a quality gate, so no estimate ever becomes training material."
            />
            <PanelBody>
              <ol className="space-y-3">
                {PIPELINE.map((stage, index) => (
                  <li key={stage.title} className="flex gap-3">
                    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded border border-line bg-wash">
                      <Icon
                        name={stage.icon}
                        className="h-3.5 w-3.5 text-accent-strong"
                      />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-baseline gap-2">
                        <span className="tnum font-mono text-2xs text-ink-faint">
                          {String(index + 1).padStart(2, "0")}
                        </span>
                        <span className="text-xs font-medium text-ink">
                          {stage.title}
                        </span>
                      </div>
                      <p className="mt-0.5 text-xs leading-relaxed text-ink-muted">
                        {stage.body}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader
              kicker="Coverage"
              title="The six shape families"
              description="The dataset deliberately covers several beam-like geometries. Each family contributes solved cases with its own parameter ranges."
            />
            <PanelBody>
              <Table>
                <thead>
                  <tr>
                    <Th>Shape family</Th>
                    <Th align="right">Cases</Th>
                    <Th>What it is</Th>
                  </tr>
                </thead>
                <tbody>
                  {shapeRows.map((row) => (
                    <tr key={row.kind}>
                      <Td>
                        <span className="font-medium text-ink">{row.label}</span>
                        <div className="font-mono text-2xs text-ink-faint">
                          {row.kind}
                        </div>
                      </Td>
                      <Td align="right" mono>
                        {row.count}
                      </Td>
                      <Td className="max-w-[34rem] text-ink-muted">
                        {row.summary}
                      </Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader
              kicker="Inputs"
              title="What goes in: the design variables"
              description="The smallest, typical and largest value observed for each quantity across every case in the dataset."
            />
            <PanelBody className="space-y-3">
              <Callout tone="warning" title="This box is the model's world">
                A design built from values inside these ranges has verified
                examples behind it. Change a value beyond them and the model has
                nothing to compare with — the app flags it and recommends a real
                solve instead.
              </Callout>
              <RangeTable
                rows={designRanges}
                emptyText="No design ranges could be computed"
              />
              <p className="text-2xs leading-relaxed text-ink-faint">
                Values are per shape family, so a column that does not apply to
                a family still carries a neutral constant. Some quantities are
                fixed rather than varied: all cases use steel (210,000 MPa,
                0.30) and a single static load case.
              </p>
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader
              kicker="Answers"
              title="What comes out: the solved results"
              description="The range of answers in the dataset. These are computed by the solver, never estimated — the models later learn to reproduce them."
            />
            <PanelBody className="space-y-3">
              <Table>
                <thead>
                  <tr>
                    <Th>Target</Th>
                    <Th align="right">Smallest</Th>
                    <Th align="right">Typical</Th>
                    <Th align="right">Largest</Th>
                    <Th>In plain words</Th>
                  </tr>
                </thead>
                <tbody>
                  {targetRanges.map((row) => {
                    const info = TARGET_INFO[row.name];
                    return (
                      <tr key={row.name}>
                        <Td>
                          <div className="text-ink">
                            {info?.label ?? row.name}
                          </div>
                          <div className="font-mono text-2xs text-ink-faint">
                            {row.name} · {unitFor(row.name)}
                          </div>
                        </Td>
                        <Td align="right" mono>
                          {formatMeasure(row.min)}
                        </Td>
                        <Td align="right" mono>
                          {formatMeasure(row.mean)}
                        </Td>
                        <Td align="right" mono>
                          {formatMeasure(row.max)}
                        </Td>
                        <Td className="max-w-[24rem] text-ink-muted">
                          {info?.plain ?? ""}
                        </Td>
                      </tr>
                    );
                  })}
                </tbody>
              </Table>
              <p className="text-2xs leading-relaxed text-ink-faint">
                The spread is wide on purpose: some parts barely move, others
                bend by tens of millimetres. Training on the extremes is what
                teaches the models where their limits are.
              </p>
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader
              kicker="Splits"
              title="Four piles, one answer key"
              description="The cases are divided once, before training, and the division never changes. This is what makes the accuracy numbers honest."
            />
            <PanelBody className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
              {orderedSplits.map(([key, count]) => {
                const info = SPLIT_INFO[key] ?? {
                  title: key,
                  plain: "",
                  tone: "neutral" as const,
                };
                return (
                  <div key={key} className="rounded border border-line p-3.5">
                    <div className="flex items-center justify-between gap-2">
                      <Chip tone={info.tone}>{info.title}</Chip>
                      <span className="tnum font-mono text-sm text-ink">
                        {count?.toLocaleString() ?? "n/a"}
                      </span>
                    </div>
                    <div className="mt-2 font-mono text-2xs text-ink-faint">
                      split = “{key}”
                    </div>
                    <p className="mt-1.5 text-xs leading-relaxed text-ink-muted">
                      {info.plain}
                    </p>
                  </div>
                );
              })}
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader
              kicker="Quality"
              title="The gates every case had to pass"
              description="These checks are what let a claim like “every label is a completed simulation” be made. A row only exists here if the solver succeeded and its numbers are physical."
            />
            <PanelBody className="space-y-4">
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <Stat
                  label="Cases admitted"
                  value={data.manifest?.cases_in_dataset?.toLocaleString() ?? "n/a"}
                  sub={`from ${data.manifest?.cases_in_designs?.toLocaleString() ?? "n/a"} planned designs`}
                />
                <Stat
                  label="Cases rejected"
                  value={data.manifest?.cases_failed ?? 0}
                  tone="success"
                  sub="nothing was silently dropped"
                />
                <Stat
                  label="Median mesh"
                  value={mesh.median_nodes?.toLocaleString() ?? "n/a"}
                  sub={`${mesh.median_elements?.toLocaleString() ?? "n/a"} elements per case (${mesh.element_type ?? "n/a"})`}
                />
                <Stat
                  label="Median solve"
                  value={
                    data.median_runtime_seconds === null
                      ? "n/a"
                      : `${data.median_runtime_seconds.toFixed(1)} s`
                  }
                  sub="per case, on the build machine"
                />
              </div>
              <ul className="space-y-2 border-t border-line pt-4 text-xs leading-relaxed text-ink-muted">
                {(data.manifest?.gates ?? []).map((gate) => (
                  <li key={gate} className="flex gap-2">
                    <Icon
                      name="check-circle"
                      className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success"
                    />
                    <span>
                      {GATE_PLAIN[gate] ?? gate}
                      <span className="ml-2 font-mono text-2xs text-ink-faint">
                        {gate}
                      </span>
                    </span>
                  </li>
                ))}
              </ul>
              <p className="text-2xs leading-relaxed text-ink-faint">
                On top of the gates, an independent validation study measured
                the mesh discretisation itself: about 0.5% uncertainty on stress
                and less on displacement. That is the noise floor of the labels
                the models learned from.
              </p>
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader
              kicker="Provenance"
              title="Where this dataset came from"
              description="The chain of custody behind the file. Any prediction can be walked back to this exact content hash."
            />
            <PanelBody className="grid grid-cols-1 gap-x-10 gap-y-1 lg:grid-cols-2">
              <div>
                <KeyValue label="Dataset file" mono>
                  {data.path}
                </KeyValue>
                <KeyValue label="Content hash (sha256)" mono>
                  {data.sha256}
                </KeyValue>
                <KeyValue label="Built" mono>
                  {shortDate(data.created_utc)}
                </KeyValue>
                <KeyValue label="Schema version" mono>
                  {data.manifest?.schema_version ?? "n/a"}
                </KeyValue>
              </div>
              <div>
                <KeyValue label="Design table" mono>
                  {data.manifest?.designs_file ?? "n/a"}
                </KeyValue>
                <KeyValue label="Designs hash" mono>
                  {shortenHash(data.manifest?.designs_sha256, 16)}
                </KeyValue>
                <KeyValue label="Git commit" mono>
                  {shortenHash(data.manifest?.git?.commit, 12)}
                  {data.manifest?.git?.dirty ? " (dirty)" : ""}
                </KeyValue>
                <KeyValue label="Built with" mono>
                  {[
                    data.manifest?.environment?.surrosim,
                    data.manifest?.environment?.python
                      ? `Python ${data.manifest.environment.python}`
                      : null,
                  ]
                    .filter(Boolean)
                    .join(" · ") || "n/a"}
                </KeyValue>
              </div>
            </PanelBody>
            {data.manifest && data.manifest.base_datasets.length > 0 && (
              <PanelBody className="border-t border-line pt-4">
                <div className="text-2xs font-medium uppercase tracking-wider text-ink-faint">
                  Built on earlier work
                </div>
                <p className="mt-1 text-xs leading-relaxed text-ink-muted">
                  {data.manifest.base_datasets
                    .map(
                      (base) =>
                        `${
                          base.path.split(/[\\/]/).slice(-3).join("/") || base.path
                        } (${base.cases.toLocaleString()} plate cases, sha ${shortenHash(
                          base.sha256,
                          10,
                        )})`,
                    )
                    .join(", ")}{" "}
                  — reused only after their inputs and splits were checked
                  against the new table.
                </p>
              </PanelBody>
            )}
            <PanelBody className="border-t border-line pt-3">
              <Disclosure
                title="Reproduce this dataset"
                description="The commands that rebuild the design table, the solves and the assembled dataset."
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
                  ].join("\n")}
                </pre>
                <p className="mt-2 text-2xs leading-relaxed text-ink-faint">
                  The pipeline is resumable: completed case artifacts are reused,
                  and re-calculated rows are only accepted when their dataset
                  hash matches. CalculiX is deterministic for these linear
                  static cases up to the last digit.
                </p>
              </Disclosure>
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader
              kicker="Document"
              title="Full dataset card"
              description="The complete written record: every variable range, every caveat, in the original formatting."
            />
            {data.card ? (
              <PanelBody className="thin-scroll max-h-[40rem] overflow-y-auto">
                <Markdown>{data.card}</Markdown>
              </PanelBody>
            ) : (
              <PanelBody>
                <EmptyState title="No dataset card was found" />
              </PanelBody>
            )}
          </Panel>
        </div>
      )}
    </Page>
  );
}
