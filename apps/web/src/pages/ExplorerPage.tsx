import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { Page } from "../components/AppShell";
import { ConfidencePanel } from "../components/ConfidencePanel";
import { DesignSchematic } from "../components/DesignSchematic";
import { Icon } from "../components/Icon";
import {
  Button,
  Chip,
  KeyValue,
  Panel,
  PanelBody,
  PanelHeader,
  SliderField,
  Stat,
  Table,
  Td,
  Th,
  cx,
} from "../components/ui";
import {
  api,
  type Design,
  type PredictResponse,
  type ShapeParamInfo,
} from "../lib/api";
import { useDebouncedValue } from "../lib/hooks";
import { formatFixed, formatNumber, formatSeconds, shortenHash } from "../lib/format";
import { useDesign } from "../state/design";

function SkeletonValue() {
  return <div className="h-5 w-24 animate-pulse rounded bg-line" />;
}

function stepFor(bounds: [number, number]): number {
  const span = Math.abs(bounds[1] - bounds[0]);
  if (span <= 1) return 0.02;
  if (span <= 3) return 0.05;
  if (span <= 10) return 0.1;
  if (span <= 40) return 0.5;
  if (span <= 120) return 1;
  return 5;
}

function ParamSlider({ param }: { param: ShapeParamInfo }) {
  const { design, patch } = useDesign();
  const value = design[param.name] as number;
  const fallback: [number, number] = [0, Math.max(value * 2, 1)];
  const bounds = param.bounds ?? fallback;
  const isHole =
    param.name === "hole_diameter_mm" || param.name === "hole2_diameter_mm";
  const min = isHole ? 0 : bounds[0];
  const max = bounds[1];
  let hint = `${bounds[0].toFixed(2)} – ${bounds[1].toFixed(2)} ${param.unit}`;
  if (isHole) {
    hint =
      value > 0
        ? `0 = no hole · ${((100 * value) / design.width_mm).toFixed(0)}% of width`
        : "0 = no hole";
  } else if (param.name === "hole_x_mm" || param.name === "hole2_x_mm") {
    hint = `x = ${value.toFixed(1)} mm (${(value / design.length_mm).toFixed(2)} L)`;
  } else if (param.name === "force_n") {
    hint = "applied at the free end";
  }
  return (
    <SliderField
      label={param.label}
      unit={param.unit}
      value={value}
      min={min}
      max={max}
      step={stepFor([min, max])}
      onChange={(next) => patch({ [param.name]: next } as Partial<Design>)}
      hint={hint}
    />
  );
}

function ParametersPanel() {
  const { reset, setShape, shapeInfo, config } = useDesign();
  const shapeList = config?.shapes ?? [];

  return (
    <Panel>
      <PanelHeader
        title="Design parameters"
        kicker="Inputs"
        actions={
          <Button size="sm" variant="ghost" onClick={reset}>
            <Icon name="rotate-ccw" className="h-3.5 w-3.5" />
            Reset
          </Button>
        }
      />
      <PanelBody className="space-y-5">
        <div className="space-y-2">
          <div className="text-2xs font-medium uppercase tracking-wider text-ink-faint">
            Shape family
          </div>
          <div className="flex flex-wrap gap-1.5">
            {shapeList.map((entry) => (
              <button
                key={entry.kind}
                type="button"
                onClick={() => setShape(entry.kind)}
                aria-pressed={shapeInfo?.kind === entry.kind}
                className={cx(
                  "rounded-full border px-2.5 py-1 text-2xs font-medium transition",
                  shapeInfo?.kind === entry.kind
                    ? "border-accent-border bg-accent-soft text-accent-ink"
                    : "border-line text-ink-muted hover:border-line-strong hover:text-ink",
                )}
              >
                {entry.label}
              </button>
            ))}
            {!shapeList.length && (
              <span className="text-2xs text-ink-muted">loading shapes…</span>
            )}
          </div>
          {shapeInfo?.summary && (
            <p className="text-2xs leading-relaxed text-ink-muted">
              {shapeInfo.summary}
            </p>
          )}
        </div>

        <div className="space-y-4 border-t border-line pt-4">
          <div className="text-2xs font-medium uppercase tracking-wider text-ink-faint">
            Geometry & load
          </div>
          {shapeInfo ? (
            shapeInfo.params.map((param) => (
              <ParamSlider key={param.name} param={param} />
            ))
          ) : (
            <div className="h-40 animate-pulse rounded bg-wash" />
          )}
        </div>

        <div className="border-t border-line pt-4">
          <div className="text-2xs font-medium uppercase tracking-wider text-ink-faint">
            Material
          </div>
          <div className="mt-2 space-y-0.5">
            <KeyValue label="Young's modulus E" mono>
              210 000 MPa
            </KeyValue>
            <KeyValue label="Poisson ratio ν" mono>
              0.30
            </KeyValue>
          </div>
          <p className="mt-2 text-2xs leading-relaxed text-ink-muted">
            Steel is fixed by the dataset; the surrogate was not trained on
            other materials.
          </p>
        </div>
      </PanelBody>
    </Panel>
  );
}

function PredictionPanel({ result, loading }: { result?: PredictResponse; loading: boolean }) {
  const entries = result?.predictions;
  return (
    <Panel>
      <PanelHeader
        kicker="Surrogate prediction"
        title="Predicted response"
        actions={
          result && (
            <span className="tnum font-mono text-2xs text-ink-faint">
              {formatFixed(result.latency_ms, 1)} ms
            </span>
          )
        }
      />
      <PanelBody className="space-y-5">
        <div>
          <Stat
            label="Max displacement"
            value={
              loading || !entries ? (
                <SkeletonValue />
              ) : (
                formatNumber(entries.max_displacement_mm.value, 4)
              )
            }
            unit="mm"
            sub={
              entries?.max_displacement_mm.member_spread_pct !== undefined
                ? `ensemble spread ±${formatFixed(entries.max_displacement_mm.member_spread_pct, 1)}%`
                : undefined
            }
          />
        </div>
        <div className="border-t border-line pt-4">
          <Stat
            label="Global max Von Mises"
            value={
              loading || !entries ? (
                <SkeletonValue />
              ) : (
                formatNumber(entries.global_max_von_mises_mpa.value, 4)
              )
            }
            unit="MPa"
            sub={
              entries?.global_max_von_mises_mpa.member_spread_pct !== undefined
                ? `ensemble spread ±${formatFixed(entries.global_max_von_mises_mpa.member_spread_pct, 1)}%`
                : undefined
            }
          />
        </div>
        <div className="border-t border-line pt-4">
          <Stat
            label="Stress-riser ROI max Von Mises"
            value={
              loading || !entries ? (
                <SkeletonValue />
              ) : entries.max_von_mises_roi_mpa.value === null ? (
                "n/a"
              ) : (
                formatNumber(entries.max_von_mises_roi_mpa.value, 4)
              )
            }
            unit={entries?.max_von_mises_roi_mpa.value === null ? undefined : "MPa"}
            sub={
              entries?.max_von_mises_roi_mpa.reason ??
              (entries?.max_von_mises_roi_mpa.member_spread_pct !== undefined
                ? `ensemble spread ±${formatFixed(entries.max_von_mises_roi_mpa.member_spread_pct, 1)}%`
                : undefined)
            }
          />
        </div>
      </PanelBody>
    </Panel>
  );
}

function AnalyticalPanel({ result }: { result?: PredictResponse }) {
  if (!result || !result.nominal_beam_baseline) {
    return null;
  }
  const { predictions, nominal_beam_baseline: nominal } = result;
  const beamTip = nominal.nominal_tip_displacement_mm;
  const beamStress = nominal.nominal_root_bending_stress_mpa;
  const surrogateTip = predictions.max_displacement_mm.value;
  const surrogateStress = predictions.global_max_von_mises_mpa.value;

  const rows = [
    {
      label: "Tip displacement (mm)",
      beam: beamTip,
      surrogate: surrogateTip,
    },
    {
      label: "Root bending stress (MPa)",
      beam: beamStress,
      surrogate: surrogateStress,
    },
  ];

  return (
    <Panel>
      <PanelHeader
        kicker="Sanity reference"
        title="Analytical beam comparison"
        description="Transparent shape-specific beam reference (ignores holes, fillets and shear). It is a reference, not a training label."
      />
      <PanelBody>
        <Table>
          <thead>
            <tr>
              <Th>Quantity</Th>
              <Th align="right">Beam theory</Th>
              <Th align="right">Surrogate</Th>
              <Th align="right">Δ</Th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const delta =
                row.surrogate !== null && row.beam
                  ? (100 * (row.surrogate - row.beam)) / row.beam
                  : null;
              return (
                <tr key={row.label}>
                  <Td>{row.label}</Td>
                  <Td align="right" mono>
                    {formatNumber(row.beam, 4)}
                  </Td>
                  <Td align="right" mono>
                    {formatNumber(row.surrogate, 4)}
                  </Td>
                  <Td
                    align="right"
                    mono
                    className={
                      delta !== null && Math.abs(delta) > 40
                        ? "text-warning"
                        : undefined
                    }
                  >
                    {delta === null ? "n/a" : `${delta > 0 ? "+" : ""}${formatFixed(delta, 1)}%`}
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      </PanelBody>
    </Panel>
  );
}

function ActionsPanel({ result }: { result?: PredictResponse }) {
  const median = result?.fea_reference.median_solve_seconds;
  return (
    <Panel>
      <PanelHeader kicker="Next steps" title="Verify or inspect the field" />
      <PanelBody className="space-y-3">
        <Link to="/verify" className="block">
          <Button variant="primary" className="w-full justify-between">
            Run FEA verification
            <Icon name="arrow-right" className="h-4 w-4" />
          </Button>
        </Link>
        <Link to="/field" className="block">
          <Button variant="secondary" className="w-full justify-between">
            Predict full field
            <Icon name="arrow-right" className="h-4 w-4" />
          </Button>
        </Link>
        <p className="text-2xs leading-relaxed text-ink-muted">
          CalculiX solves the same design in{" "}
          {median ? `about ${formatSeconds(median)}` : "seconds"}; field
          prediction runs a MeshGraphNet on a coarse graph mesh in a few
          seconds.
        </p>
      </PanelBody>
    </Panel>
  );
}

function ProvenancePanel({ result }: { result?: PredictResponse }) {
  if (!result) {
    return null;
  }
  return (
    <Panel>
      <PanelHeader kicker="Traceability" title="Model provenance" />
      <PanelBody className="space-y-0.5">
        <KeyValue label="Registry" mono>
          {result.model.registry.replace(/\\/g, "/").replace(/^.*?models\//, "models/")}
        </KeyValue>
        <KeyValue label="Dataset sha" mono>
          {shortenHash(result.model.dataset_sha256, 12)}
        </KeyValue>
        <KeyValue label="Git commit" mono>
          {shortenHash(result.model.git_commit, 10)}
        </KeyValue>
        <KeyValue label="Median FEA solve" mono>
          {formatSeconds(result.fea_reference.median_solve_seconds)}
        </KeyValue>
        <KeyValue label="Surrogate latency" mono>
          {formatFixed(result.latency_ms, 1)} ms
        </KeyValue>
      </PanelBody>
    </Panel>
  );
}

export function ExplorerPage() {
  const { design, shapeInfo } = useDesign();
  const debounced = useDebouncedValue(design, 120);
  const prediction = useQuery({
    queryKey: ["predict", debounced],
    queryFn: () => api.predict(debounced),
    placeholderData: (previous) => previous,
    staleTime: 30_000,
  });
  const result = prediction.data;

  return (
    <Page
      kicker="Analysis"
      title="Design Explorer"
      description="Move a parameter and the surrogate answers in microseconds. Every response carries an out-of-distribution score, ensemble disagreement and a recommendation to trust it or run the solver."
      actions={
        result && (
          <Chip
            tone={
              result.confidence.recommendation === "trust"
                ? "success"
                : result.confidence.recommendation === "caution"
                  ? "warning"
                  : "danger"
            }
          >
            {result.confidence.recommendation === "run_fea"
              ? "run FEA"
              : result.confidence.recommendation}
          </Chip>
        )
      }
    >
      <div className="grid grid-cols-12 gap-5">
        <div className="col-span-12 xl:col-span-3">
          <ParametersPanel />
        </div>

        <div className="col-span-12 space-y-5 xl:col-span-6">
          <Panel>
            <PanelHeader
              kicker="Geometry"
              title={shapeInfo?.label ?? "Parametric design"}
              description={
                shapeInfo?.summary ??
                "Clamped at x = 0, transverse force applied at the free end."
              }
            />
            <PanelBody className="pb-2 pt-4">
              <DesignSchematic design={design} />
            </PanelBody>
          </Panel>

          {result ? (
            <ConfidencePanel
              confidence={result.confidence}
              latencyMs={result.latency_ms}
            />
          ) : (
            <Panel>
              <PanelBody>
                <div className="h-32 animate-pulse rounded bg-wash" />
              </PanelBody>
            </Panel>
          )}

          <AnalyticalPanel result={result} />
        </div>

        <div className="col-span-12 space-y-5 xl:col-span-3">
          <PredictionPanel result={result} loading={prediction.isLoading} />
          <ActionsPanel result={result} />
          <ProvenancePanel result={result} />
        </div>
      </div>
    </Page>
  );
}
