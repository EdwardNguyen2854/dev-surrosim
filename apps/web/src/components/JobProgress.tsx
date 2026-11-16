import { useEffect, useRef } from "react";

import type { Job, JobStatus } from "../lib/api";
import { useElapsed } from "../lib/hooks";
import { Icon, type IconName } from "./Icon";
import { Chip, ErrorNote, Panel, PanelBody, PanelHeader, ProgressBar, cx } from "./ui";

const STATUS_META: Record<
  JobStatus,
  {
    label: string;
    tone: "neutral" | "accent" | "success" | "danger";
    icon: IconName;
    spin?: boolean;
  }
> = {
  queued: { label: "Queued", tone: "neutral", icon: "clock" },
  running: { label: "Running", tone: "accent", icon: "loader", spin: true },
  succeeded: { label: "Complete", tone: "success", icon: "check-circle" },
  failed: { label: "Failed", tone: "danger", icon: "x-circle" },
};

export function JobProgress({
  job,
  title = "Job progress",
  description,
}: {
  job: Job | null | undefined;
  title?: string;
  description?: string;
}) {
  const elapsed = useElapsed(job?.started_utc ?? null, job?.finished_utc ?? null);
  const logRef = useRef<HTMLDivElement | null>(null);
  const logCount = job?.logs.length ?? 0;

  useEffect(() => {
    const element = logRef.current;
    if (element) {
      element.scrollTop = element.scrollHeight;
    }
  }, [logCount]);

  const status = job?.status ?? "queued";
  const meta = STATUS_META[status];

  return (
    <Panel>
      <PanelHeader
        kicker="Background job"
        title={title}
        description={description}
        actions={
          <>
            <span className="tnum font-mono text-xs text-ink-muted">
              {elapsed > 0 ? `${elapsed.toFixed(1)} s` : ""}
            </span>
            <Chip tone={meta.tone}>
              <Icon
                name={meta.icon}
                className={cx("h-3 w-3", meta.spin && "animate-spin")}
              />
              {meta.label}
            </Chip>
          </>
        }
      />
      <PanelBody className="space-y-3">
        <div className="flex items-center justify-between gap-3 text-xs">
          <span className="truncate font-mono text-ink-muted">
            {job?.stage ?? "waiting for worker"}
          </span>
          {job?.progress !== null && job?.progress !== undefined && (
            <span className="tnum font-mono text-ink">
              {(job.progress * 100).toFixed(0)}%
            </span>
          )}
        </div>
        <ProgressBar
          value={job?.progress ?? null}
          tone={status === "failed" ? "danger" : status === "succeeded" ? "success" : "accent"}
        />
        {job?.error && <ErrorNote>{job.error}</ErrorNote>}
        <div
          ref={logRef}
          className="thin-scroll max-h-44 overflow-y-auto rounded border border-line bg-wash px-3 py-2"
        >
          {(job?.logs ?? []).map((entry, index) => (
            <div key={`${entry.time}-${index}`} className="flex gap-3 py-0.5">
              <span className="tnum shrink-0 font-mono text-2xs text-ink-faint">
                {new Date(entry.time).toLocaleTimeString()}
              </span>
              <span
                className={cx(
                  "font-mono text-2xs leading-relaxed",
                  entry.level === "error" && "text-danger",
                  entry.level === "warning" && "text-warning",
                  entry.level !== "error" && entry.level !== "warning" && "text-ink-muted",
                )}
              >
                {entry.message}
              </span>
            </div>
          ))}
          {(!job || job.logs.length === 0) && (
            <span className="font-mono text-2xs text-ink-muted">
              no log entries yet
            </span>
          )}
        </div>
      </PanelBody>
    </Panel>
  );
}
