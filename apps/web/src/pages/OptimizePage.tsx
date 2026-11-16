import { useEffect, useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { Page } from "../components/AppShell";
import { Icon } from "../components/Icon";
import { JobProgress } from "../components/JobProgress";
import { BASE_LAYOUT, PlotlyPlot } from "../components/Plotly";
import {
  Button,
  Chip,
  ErrorNote,
  NumberInput,
  Panel,
  PanelBody,
  PanelHeader,
  Stat,
  SwitchField,
  Table,
  Td,
  Th,
} from "../components/ui";
import { useToast } from "../components/toast";
import { api, type OptimizationResult } from "../lib/api";
import { formatFixed } from "../lib/format";
import { useDesign } from "../state/design";
import { useJobSlot } from "../state/jobs";

type FormState = {
  length_mm: number;
  force_n: number;
  sigma_allow_mpa: number;
  displacement_limit_mm: number;
  maxiter: number;
  verify_candidates: boolean;
};

const INITIAL_FORM: FormState = {
  length_mm: 120,
  force_n: 500,
  sigma_allow_mpa: 180,
  displacement_limit_mm: 1.5,
  maxiter: 60,
  verify_candidates: false,
};

function NumberRow({
  label,
  unit,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  unit: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
}) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <label className="text-xs font-medium text-ink-muted">{label}</label>
      <div className="flex items-baseline gap-1.5">
        <NumberInput
          value={value}
          min={min}
          max={max}
          step={step}
          onChange={onChange}
          ariaLabel={label}
          className="w-20"
        />
        <span className="w-7 text-2xs text-ink-faint">{unit}</span>
      </div>
    </div>
  );
}

function OptimizationResults({ result }: { result: OptimizationResult }) {
  const scatter = useMemo(() => {
    const { mass_g, stress_mpa, feasible } = result.evaluations;
    const feasibleX: number[] = [];
    const feasibleY: number[] = [];
    const infeasibleX: number[] = [];
    const infeasibleY: number[] = [];
    for (let index = 0; index < mass_g.length; index += 1) {
      if (feasible[index]) {
        feasibleX.push(stress_mpa[index]);
        feasibleY.push(mass_g[index]);
      } else {
        infeasibleX.push(stress_mpa[index]);
        infeasibleY.push(mass_g[index]);
      }
    }
    const candidateX = result.candidates.map((candidate) => candidate.stress_mpa);
    const candidateY = result.candidates.map((candidate) => candidate.mass_g);
    return [
      {
        type: "scatter",
        mode: "markers",
        name: `infeasible (${infeasibleX.length})`,
        x: infeasibleX,
        y: infeasibleY,
        marker: { size: 4, color: "var(--color-feedback-danger)", opacity: 0.32 },
        hovertemplate: "σ %{x:.1f} MPa · m %{y:.1f} g<extra></extra>",
      },
      {
        type: "scatter",
        mode: "markers",
        name: `feasible (${feasibleX.length})`,
        x: feasibleX,
        y: feasibleY,
        marker: { size: 4, color: "var(--color-accent-default)", opacity: 0.5 },
        hovertemplate: "σ %{x:.1f} MPa · m %{y:.1f} g<extra></extra>",
      },
      {
        type: "scatter",
        mode: "markers",
        name: "candidates",
        x: candidateX,
        y: candidateY,
        marker: {
          size: 11,
          color: "var(--color-text-primary)",
          symbol: "star",
          line: { color: "var(--color-surface-default)", width: 1 },
        },
        hovertemplate: "candidate · σ %{x:.1f} MPa · m %{y:.1f} g<extra></extra>",
      },
    ];
  }, [result]);

  const scatterLayout = useMemo(
    () => ({
      ...BASE_LAYOUT,
      xaxis: { ...(BASE_LAYOUT.xaxis as object), title: { text: "predicted max σ (MPa)" } },
      yaxis: { ...(BASE_LAYOUT.yaxis as object), title: { text: "mass (g)" } },
      margin: { l: 58, r: 18, t: 30, b: 46 },
    }),
    [],
  );

  const convergence = useMemo(() => {
    const { mass_g, feasible } = result.evaluations;
    const xs: number[] = [];
    const ys: number[] = [];
    let best = Number.POSITIVE_INFINITY;
    for (let index = 0; index < mass_g.length; index += 1) {
      if (feasible[index] && mass_g[index] < best) {
        best = mass_g[index];
      }
      if (Number.isFinite(best)) {
        xs.push(index + 1);
        ys.push(best);
      }
    }
    if (xs.length === 0) {
      return null;
    }
    return [
      {
        type: "scatter",
        mode: "lines",
        name: "best feasible mass",
        x: xs,
        y: ys,
        line: { color: "var(--color-accent-default)", width: 2 },
        hovertemplate: "eval %{x} · best %{y:.1f} g<extra></extra>",
      },
    ];
  }, [result]);

  const convergenceLayout = useMemo(
    () => ({
      ...BASE_LAYOUT,
      showlegend: false,
      xaxis: { ...(BASE_LAYOUT.xaxis as object), title: { text: "surrogate evaluation" } },
      yaxis: { ...(BASE_LAYOUT.yaxis as object), title: { text: "best feasible mass (g)" } },
      margin: { l: 58, r: 18, t: 18, b: 46 },
    }),
    [],
  );

  const bestMass = result.candidates[0]?.mass_g ?? null;
  const verified = result.verification.length > 0;

  return (
    <div className="space-y-5">
      <Panel>
        <PanelHeader
          kicker="Result"
          title="Optimizer summary"
          description={`${result.optimizer.method} · seed ${result.optimizer.seed} · ${result.optimizer.maxiter} generations`}
          actions={
            <Chip tone="accent">
              {result.candidates.length} feasible candidate
              {result.candidates.length === 1 ? "" : "s"}
            </Chip>
          }
        />
        <PanelBody className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <Stat
            label="Evaluations"
            value={result.optimizer.evaluations.toLocaleString()}
            sub="surrogate calls"
          />
          <Stat
            label="Optimizer time"
            value={formatFixed(result.optimizer.seconds, 1)}
            unit="s"
          />
          <Stat
            label="Best mass"
            value={bestMass === null ? "n/a" : formatFixed(bestMass, 1)}
            unit="g"
          />
          <Stat
            label="FEA-verified"
            value={verified ? `${result.verification.length}` : "—"}
            sub={verified ? "finalists solved" : "verification disabled"}
          />
        </PanelBody>
      </Panel>

      <div className="grid grid-cols-12 gap-5">
        <div className="col-span-12 2xl:col-span-7">
          <Panel>
            <PanelHeader
              kicker="Design space"
              title="All evaluations"
              description="Mass against predicted peak stress; candidates are the lowest-mass feasible designs."
            />
            <PanelBody>
              <PlotlyPlot data={scatter} layout={scatterLayout} height={340} />
            </PanelBody>
          </Panel>
        </div>
        <div className="col-span-12 2xl:col-span-5">
          <Panel>
            <PanelHeader
              kicker="Convergence"
              title="Best feasible mass"
              description="Running best across surrogate evaluations."
            />
            <PanelBody>
              {convergence ? (
                <PlotlyPlot data={convergence} layout={convergenceLayout} height={340} />
              ) : (
                <p className="py-10 text-center text-xs text-ink-muted">
                  No feasible design found within the constraints.
                </p>
              )}
            </PanelBody>
          </Panel>
        </div>
      </div>

      <Panel>
        <PanelHeader
          kicker="Finalists"
          title="Candidate designs"
          description="Ranked by surrogate mass. FEA columns appear when candidate verification is enabled."
        />
        <PanelBody>
          <Table>
            <thead>
              <tr>
                <Th>#</Th>
                <Th align="right">W (mm)</Th>
                <Th align="right">T (mm)</Th>
                <Th align="right">d (mm)</Th>
                <Th align="right">x (mm)</Th>
                <Th align="right">mass (g)</Th>
                <Th align="right">σ pred (MPa)</Th>
                <Th align="right">δ pred (mm)</Th>
                <Th align="right">σ/σ allow</Th>
                {verified && <Th align="right">σ FEA</Th>}
                {verified && <Th align="right">σ err</Th>}
                {verified && <Th align="center">FEA ok</Th>}
              </tr>
            </thead>
            <tbody>
              {result.candidates.map((candidate, index) => {
                const verification = result.verification[index];
                return (
                  <tr key={`${candidate.design.width_mm}-${candidate.design.thickness_mm}-${index}`}>
                    <Td mono>{index + 1}</Td>
                    <Td align="right" mono>
                      {candidate.design.width_mm.toFixed(2)}
                    </Td>
                    <Td align="right" mono>
                      {candidate.design.thickness_mm.toFixed(2)}
                    </Td>
                    <Td align="right" mono>
                      {candidate.design.hole_diameter_mm.toFixed(2)}
                    </Td>
                    <Td align="right" mono>
                      {candidate.design.hole_x_mm.toFixed(1)}
                    </Td>
                    <Td align="right" mono>
                      {formatFixed(candidate.mass_g, 1)}
                    </Td>
                    <Td align="right" mono>
                      {formatFixed(candidate.stress_mpa, 1)}
                    </Td>
                    <Td align="right" mono>
                      {candidate.displacement_mm.toFixed(4)}
                    </Td>
                    <Td align="right" mono>
                      {candidate.stress_ratio.toFixed(2)}
                    </Td>
                    {verified && (
                      <Td align="right" mono>
                        {verification?.fea_global_stress_mpa
                          ? formatFixed(verification.fea_global_stress_mpa, 1)
                          : "n/a"}
                      </Td>
                    )}
                    {verified && (
                      <Td
                        align="right"
                        mono
                        className={
                          verification?.fea_stress_error_pct !== undefined &&
                          verification?.fea_stress_error_pct !== null &&
                          Math.abs(verification.fea_stress_error_pct) > 10
                            ? "text-danger"
                            : "text-success"
                        }
                      >
                        {verification?.fea_stress_error_pct !== undefined &&
                        verification?.fea_stress_error_pct !== null
                          ? `${verification.fea_stress_error_pct > 0 ? "+" : ""}${formatFixed(verification.fea_stress_error_pct, 1)}%`
                          : "n/a"}
                      </Td>
                    )}
                    {verified && (
                      <Td align="center">
                        {verification?.fea_feasible ? (
                          <span className="text-success">yes</span>
                        ) : (
                          <span className="text-danger">no</span>
                        )}
                      </Td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </Table>
        </PanelBody>
      </Panel>
    </div>
  );
}

export function OptimizePage() {
  const { config } = useDesign();
  const { push } = useToast();
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const { jobId, job, setJobId } = useJobSlot<OptimizationResult>("optimize");
  const running = job.data?.status === "running" || job.data?.status === "queued";
  const result = job.data?.status === "succeeded" ? job.data.result : null;
  const calculixReady = config?.capabilities.calculix ?? false;

  useEffect(() => {
    const defaults = config?.optimizer_defaults;
    if (defaults) {
      setForm((current) => ({ ...current, ...defaults }));
    }
  }, [config?.optimizer_defaults]);

  const start = useMutation({
    mutationFn: () => api.startOptimize(form),
    onSuccess: (payload) => setJobId(payload.job.id),
    onError: (error) =>
      push({
        tone: "error",
        title: "Could not start optimization",
        message: String(error),
      }),
  });

  const patch = (partial: Partial<FormState>) =>
    setForm((current) => ({ ...current, ...partial }));

  return (
    <Page
      kicker="Analysis"
      title="Design optimization"
      description="Minimise mass subject to stress and displacement limits. Differential evolution screens thousands of designs through the surrogate in seconds; only finalists touch the real solver."
      actions={
        <Button
          variant="primary"
          disabled={start.isPending || running}
          onClick={() => start.mutate()}
        >
          <Icon name="play" className="h-4 w-4" />
          {running ? "Optimizing…" : "Run optimization"}
        </Button>
      }
    >
      <div className="grid grid-cols-12 gap-5">
        <div className="col-span-12 space-y-5 xl:col-span-3">
          <Panel>
            <PanelHeader kicker="Problem" title="Constraints" />
            <PanelBody className="space-y-3.5">
              <NumberRow
                label="Length L"
                unit="mm"
                value={form.length_mm}
                min={80}
                max={200}
                step={1}
                onChange={(value) => patch({ length_mm: value })}
              />
              <NumberRow
                label="Force F"
                unit="N"
                value={form.force_n}
                min={10}
                max={2000}
                step={10}
                onChange={(value) => patch({ force_n: value })}
              />
              <NumberRow
                label="Allowable stress"
                unit="MPa"
                value={form.sigma_allow_mpa}
                min={20}
                max={400}
                step={5}
                onChange={(value) => patch({ sigma_allow_mpa: value })}
              />
              <NumberRow
                label="Displacement limit"
                unit="mm"
                value={form.displacement_limit_mm}
                min={0.1}
                max={5}
                step={0.1}
                onChange={(value) => patch({ displacement_limit_mm: value })}
              />
              <div className="border-t border-line pt-3">
                <NumberRow
                  label="Generations"
                  unit=""
                  value={form.maxiter}
                  min={5}
                  max={200}
                  step={5}
                  onChange={(value) => patch({ maxiter: value })}
                />
                <p className="mt-1 text-2xs text-ink-muted">
                  Variables: W 30–60 mm, T 4–10 mm, d/W 0–0.45, x/L 0.35–0.65.
                </p>
              </div>
            </PanelBody>
          </Panel>

          <Panel>
            <PanelHeader kicker="Verification" title="Finalist checks" />
            <PanelBody className="space-y-3">
              <SwitchField
                label="Verify finalists with CalculiX"
                description="Solve the top candidates with the real solver after the surrogate search (~10 s each)."
                checked={form.verify_candidates}
                onCheckedChange={(checked) => patch({ verify_candidates: checked })}
                disabled={!calculixReady}
              />
              {!calculixReady && (
                <ErrorNote>
                  CalculiX was not found; only surrogate ranking is available.
                </ErrorNote>
              )}
            </PanelBody>
          </Panel>
        </div>

        <div className="col-span-12 space-y-5 xl:col-span-9">
          {jobId && (
            <JobProgress
              job={job.data}
              title="Surrogate optimization"
              description="Differential evolution evaluates the surrogate ensemble in the background."
            />
          )}

          {!jobId && (
            <Panel>
              <PanelBody>
                <p className="text-xs leading-relaxed text-ink-muted">
                  Set the problem constraints and run the optimizer. A full
                  search is a few thousand surrogate calls and completes in
                  seconds; enabling FEA verification adds one solver run per
                  finalist.
                </p>
              </PanelBody>
            </Panel>
          )}

          {result && <OptimizationResults result={result} />}
        </div>
      </div>
    </Page>
  );
}
