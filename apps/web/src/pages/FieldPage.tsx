import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { Page } from "../components/AppShell";
import { FieldViewer } from "../components/FieldViewer";
import { Icon } from "../components/Icon";
import { JobProgress } from "../components/JobProgress";
import {
  Button,
  ErrorNote,
  KeyValue,
  Panel,
  PanelBody,
  PanelHeader,
  Stat,
  cx,
} from "../components/ui";
import { useToast } from "../components/toast";
import { api, type FieldPredictResult } from "../lib/api";
import { formatFixed } from "../lib/format";
import { useDesign } from "../state/design";
import { useJobSlot } from "../state/jobs";

const FIELDS = [
  { id: "von_mises_mpa", label: "Von Mises stress" },
  { id: "displacement_mm", label: "Displacement" },
] as const;

type FieldId = (typeof FIELDS)[number]["id"];

export function FieldPage() {
  const { design, config } = useDesign();
  const { push } = useToast();
  const [field, setField] = useState<FieldId>("von_mises_mpa");
  const { jobId, job, setJobId } = useJobSlot<FieldPredictResult>("field_predict");
  const running = job.data?.status === "running" || job.data?.status === "queued";
  const result = job.data?.status === "succeeded" ? job.data.result : null;
  const fieldReady = config?.capabilities.field_model ?? false;

  const start = useMutation({
    mutationFn: () => api.startFieldPredict(design),
    onSuccess: (payload) => setJobId(payload.job.id),
    onError: (error) =>
      push({
        tone: "error",
        title: "Could not start field prediction",
        message: String(error),
      }),
  });

  const designMatches =
    result !== null && JSON.stringify(result.design) === JSON.stringify(design);

  return (
    <Page
      kicker="Analysis"
      title="Field prediction"
      description="A MeshGraphNet predicts nodal displacement and stress on the coarse graph mesh used during training. Scalar extremes from the ensemble remain the more accurate choice for peak values."
      actions={
        <Button
          variant="primary"
          disabled={!fieldReady || start.isPending || running}
          onClick={() => start.mutate()}
        >
          <Icon name="play" className="h-4 w-4" />
          {running ? "Predicting…" : "Predict field"}
        </Button>
      }
    >
      {!fieldReady && (
        <div className="mb-5">
          <ErrorNote>
            No trained field model found in <code>models/gnn/v1</code>. Train
            one with <code>surrosim train gnn</code> to enable field prediction.
          </ErrorNote>
        </div>
      )}

      <div className="grid grid-cols-12 gap-5">
        <div className="col-span-12 xl:col-span-3">
          <Panel>
            <PanelHeader kicker="Current design" title="Prediction target" />
            <PanelBody className="space-y-0.5">
              <KeyValue label="Length L" mono>
                {design.length_mm.toFixed(1)} mm
              </KeyValue>
              <KeyValue label="Width W" mono>
                {design.width_mm.toFixed(1)} mm
              </KeyValue>
              <KeyValue label="Thickness T" mono>
                {design.thickness_mm.toFixed(1)} mm
              </KeyValue>
              <KeyValue label="Hole diameter d" mono>
                {design.hole_diameter_mm.toFixed(2)} mm
              </KeyValue>
              <KeyValue label="Hole position x" mono>
                {design.hole_x_mm.toFixed(1)} mm
              </KeyValue>
              <KeyValue label="Force F" mono>
                {design.force_n.toFixed(0)} N
              </KeyValue>
            </PanelBody>
          </Panel>
        </div>

        <div className="col-span-12 space-y-5 xl:col-span-9">
          {jobId && (
            <JobProgress
              job={job.data}
              title="MeshGraphNet field prediction"
              description="The server generates a coarse graph mesh, runs message passing and returns nodal fields."
            />
          )}

          {result && !designMatches && (
            <div className="rounded border border-warning bg-warning-soft px-3 py-2 text-xs text-warning">
              The design changed after this prediction; the field below belongs
              to the previous geometry.
            </div>
          )}

          {result && (
            <>
              <Panel>
                <PanelHeader
                  kicker="Predicted extremes"
                  title="Scalar summary"
                  description="Read from the predicted nodal field; the scalar ensemble remains more accurate for peak values."
                  actions={
                    <div
                      className="inline-flex gap-0.5 rounded border border-line bg-surface p-0.5"
                      role="group"
                      aria-label="Predicted field"
                    >
                      {FIELDS.map((entry) => (
                        <button
                          key={entry.id}
                          type="button"
                          onClick={() => setField(entry.id)}
                          aria-pressed={field === entry.id}
                          className={cx(
                            "rounded-sm px-2.5 py-1 text-2xs font-medium uppercase tracking-wider transition-colors",
                            field === entry.id
                              ? "bg-accent-soft text-accent-ink"
                              : "text-ink-muted hover:bg-wash hover:text-ink",
                          )}
                        >
                          {entry.label}
                        </button>
                      ))}
                    </div>
                  }
                />
                <PanelBody className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                  <Stat
                    label="Max displacement"
                    value={formatFixed(result.scalars.max_displacement_mm, 3)}
                    unit="mm"
                  />
                  <Stat
                    label="Global max Von Mises"
                    value={formatFixed(result.scalars.global_max_von_mises_mpa, 1)}
                    unit="MPa"
                  />
                  <Stat
                    label="ROI max Von Mises"
                    value={
                      result.scalars.roi_max_von_mises_mpa === null
                        ? "n/a"
                        : formatFixed(result.scalars.roi_max_von_mises_mpa, 1)
                    }
                    unit={
                      result.scalars.roi_max_von_mises_mpa === null ? undefined : "MPa"
                    }
                  />
                  <Stat
                    label="Field runtime"
                    value={formatFixed(result.runtime_ms / 1000, 2)}
                    unit="s"
                    sub={`${result.graph_nodes.toLocaleString()} graph nodes`}
                  />
                </PanelBody>
              </Panel>

              <FieldViewer
                jobId={jobId as string}
                field={field}
                title={
                  field === "von_mises_mpa"
                    ? "Predicted Von Mises stress"
                    : "Predicted displacement magnitude"
                }
                height={460}
              />
            </>
          )}
        </div>
      </div>
    </Page>
  );
}
