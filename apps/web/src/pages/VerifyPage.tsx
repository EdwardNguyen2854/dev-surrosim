import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { Page } from "../components/AppShell";
import { FieldViewer } from "../components/FieldViewer";
import { Icon } from "../components/Icon";
import { JobProgress } from "../components/JobProgress";
import {
  Button,
  Chip,
  ErrorNote,
  KeyValue,
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
import { api, type FeaVerifyResult } from "../lib/api";
import { formatFixed, formatNumber, formatSignedPct } from "../lib/format";
import { useDesign } from "../state/design";
import { useJobSlot } from "../state/jobs";

function errorClass(errorPct: number | null): string | undefined {
  if (errorPct === null) {
    return undefined;
  }
  const magnitude = Math.abs(errorPct);
  if (magnitude > 10) {
    return "text-danger";
  }
  if (magnitude > 5) {
    return "text-warning";
  }
  return "text-success";
}

function DesignSummary() {
  const { design, shapeInfo } = useDesign();
  const params = shapeInfo?.params ?? [];
  return (
    <Panel>
      <PanelHeader kicker="Current design" title="Verification target" />
      <PanelBody className="space-y-0.5">
        <KeyValue label="Shape family" mono>
          {shapeInfo?.label ?? design.shape}
        </KeyValue>
        {params.map((param) => (
          <KeyValue key={param.name} label={param.label} mono>
            {(design[param.name] as number).toFixed(2)} {param.unit}
          </KeyValue>
        ))}
        {!params.length && (
          <>
            <KeyValue label="Length L" mono>
              {design.length_mm.toFixed(1)} mm
            </KeyValue>
            <KeyValue label="Force F" mono>
              {design.force_n.toFixed(0)} N
            </KeyValue>
          </>
        )}
      </PanelBody>
    </Panel>
  );
}

function ComparisonTable({ result }: { result: FeaVerifyResult }) {
  return (
    <Panel>
      <PanelHeader
        kicker="Surrogate vs solver"
        title="Comparison against CalculiX"
        description="The solver result is the reference; the surrogate error is the number that matters for trust."
        actions={
          result.cached ? (
            <Chip tone="neutral">reused cached case</Chip>
          ) : (
            <Chip tone="success">fresh solve</Chip>
          )
        }
      />
      <PanelBody className="space-y-4">
        <Table>
          <thead>
            <tr>
              <Th>Quantity</Th>
              <Th align="right">Surrogate</Th>
              <Th align="right">CalculiX FEA</Th>
              <Th align="right">Error</Th>
            </tr>
          </thead>
          <tbody>
            {result.comparison.map((row) => (
              <tr key={row.target}>
                <Td>{row.label}</Td>
                <Td align="right" mono>
                  {formatNumber(row.surrogate, 5)}
                </Td>
                <Td align="right" mono>
                  {formatNumber(row.fea, 5)}
                </Td>
                <Td align="right" mono className={errorClass(row.error_pct)}>
                  {formatSignedPct(row.error_pct, 2)}
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>

        <div className="grid grid-cols-2 gap-4 border-t border-line pt-4 sm:grid-cols-4">
          <Stat
            label="Solver runtime"
            value={formatFixed(result.solver?.runtime_seconds, 2)}
            unit="s"
          />
          <Stat
            label="Surrogate latency"
            value={formatFixed(result.surrogate_latency_ms, 1)}
            unit="ms"
          />
          <Stat label="Mesh nodes" value={result.deck?.nodes.toLocaleString() ?? "n/a"} />
          <Stat
            label="Elements"
            value={result.deck?.volume_elements.toLocaleString() ?? "n/a"}
            sub={result.deck?.element_type}
          />
        </div>
      </PanelBody>
    </Panel>
  );
}

export function VerifyPage() {
  const { design, config } = useDesign();
  const { push } = useToast();
  const { jobId, job, setJobId } = useJobSlot<FeaVerifyResult>("fea_verify");
  const [force, setForce] = useState(false);
  const running = job.data?.status === "running" || job.data?.status === "queued";
  const result = job.data?.status === "succeeded" ? job.data.result : null;
  const calculixReady = config?.capabilities.calculix ?? false;
  const designMatches =
    result !== null && JSON.stringify(result.design) === JSON.stringify(design);

  const start = useMutation({
    mutationFn: () => api.startFeaVerify(design, force),
    onSuccess: (payload) => setJobId(payload.job.id),
    onError: (error) =>
      push({
        tone: "error",
        title: "Could not start verification",
        message: String(error),
      }),
  });

  return (
    <Page
      kicker="Analysis"
      title="FEA verification"
      description="Run the validated CalculiX case for the current design and compare it with the surrogate prediction. Verification is the ground truth; the surrogate is the shortcut."
      actions={
        <Button
          variant="primary"
          disabled={!calculixReady || start.isPending || running}
          onClick={() => start.mutate()}
        >
          <Icon name="play" className="h-4 w-4" />
          {running ? "Running…" : "Run CalculiX verification"}
        </Button>
      }
    >
      {!calculixReady && (
        <div className="mb-5">
          <ErrorNote>
            CalculiX executable not found. Place <code>ccx</code> in{" "}
            <code>tools/calculix/</code>, install it on PATH or set{" "}
            <code>SURROSIM_CCX</code> to enable verification.
          </ErrorNote>
        </div>
      )}

      <div className="grid grid-cols-12 gap-5">
        <div className="col-span-12 space-y-5 xl:col-span-3">
          <DesignSummary />
          <Panel>
            <PanelHeader kicker="Run options" title="Solver settings" />
            <PanelBody>
              <SwitchField
                label="Force re-run"
                description="Ignore an existing cached case for this design and solve again."
                checked={force}
                onCheckedChange={setForce}
              />
            </PanelBody>
          </Panel>
        </div>

        <div className="col-span-12 space-y-5 xl:col-span-9">
          {jobId && (
            <JobProgress
              job={job.data}
              title="CalculiX verification"
              description="Mesh generation, solver execution and extraction run on the server in the background."
            />
          )}

          {!jobId && (
            <Panel>
              <PanelBody>
                <p className="text-xs leading-relaxed text-ink-muted">
                  Press <strong className="text-ink">Run CalculiX verification</strong>{" "}
                  to solve the current design with the production mesh policy.
                  The job streams its log while it runs and typically finishes in
                  a few seconds on this machine.
                </p>
              </PanelBody>
            </Panel>
          )}

          {result && !designMatches && (
            <div className="rounded border border-warning bg-warning-soft px-3 py-2 text-xs text-warning">
              The design changed after this verification. The comparison below
              belongs to the previously verified geometry — re-run to verify the
              current design.
            </div>
          )}

          {result && (
            <>
              <ComparisonTable result={result} />
              <div className="grid grid-cols-12 gap-5">
                <div className="col-span-12 2xl:col-span-6">
                  <FieldViewer
                    jobId={jobId as string}
                    field="von_mises_mpa"
                    title="FEA Von Mises stress"
                  />
                </div>
                <div className="col-span-12 2xl:col-span-6">
                  <FieldViewer
                    jobId={jobId as string}
                    field="displacement_mm"
                    title="FEA displacement magnitude"
                  />
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </Page>
  );
}
