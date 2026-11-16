import type { Confidence, Recommendation } from "../lib/api";
import { formatFixed } from "../lib/format";
import { Icon, type IconName } from "./Icon";
import { Chip, Panel, PanelBody, PanelHeader, cx } from "./ui";

const COPY: Record<
  Recommendation,
  {
    tone: "success" | "warning" | "danger";
    label: string;
    body: string;
    icon: IconName;
  }
> = {
  trust: {
    tone: "success",
    label: "Trust",
    body: "Inside the densely sampled training region with low ensemble disagreement. Still a surrogate approximation.",
    icon: "shield-check",
  },
  caution: {
    tone: "warning",
    label: "Caution",
    body: "Near the edge of the training domain. Treat as indicative and verify with FEA for any critical use.",
    icon: "alert-triangle",
  },
  run_fea: {
    tone: "danger",
    label: "Run FEA",
    body: "Outside the supported domain or the ensemble members disagree. Run the real solver before using this result.",
    icon: "shield-alert",
  },
};

function OodMeter({ ratio }: { ratio: number }) {
  const max = 3.5;
  const cautionPct = (1.5 / max) * 100;
  const outPct = (2.5 / max) * 100;
  const pct = Math.min(100, Math.max(0, (ratio / max) * 100));
  return (
    <div>
      <div
        className="relative h-1.5 w-full rounded-full bg-line"
        role="img"
        aria-label={`Out-of-distribution distance ratio ${formatFixed(ratio, 2)}`}
      >
        <div
          className="absolute inset-y-0 left-0 rounded-l-full bg-band-success"
          style={{ width: `${cautionPct}%` }}
        />
        <div
          className="absolute inset-y-0 bg-band-warning"
          style={{ left: `${cautionPct}%`, width: `${outPct - cautionPct}%` }}
        />
        <div
          className="absolute inset-y-0 right-0 rounded-r-full bg-band-danger"
          style={{ left: `${outPct}%` }}
        />
        <div
          className="absolute -top-[3px] h-3 w-[2px] bg-ink"
          style={{ left: `calc(${pct}% - 1px)` }}
        />
      </div>
      <div className="relative mt-1 h-3 text-2xs text-ink-faint">
        <span className="absolute left-0">0</span>
        <span className="absolute -translate-x-1/2" style={{ left: `${cautionPct}%` }}>
          1.5
        </span>
        <span className="absolute -translate-x-1/2" style={{ left: `${outPct}%` }}>
          2.5
        </span>
        <span className="absolute right-0">3.5</span>
      </div>
    </div>
  );
}

export function ConfidencePanel({
  confidence,
  latencyMs,
}: {
  confidence: Confidence;
  latencyMs: number;
}) {
  const copy = COPY[confidence.recommendation];
  return (
    <Panel>
      <PanelHeader
        kicker="Prediction confidence"
        title={
          <span className="flex items-center gap-2">
            <Icon
              name={copy.icon}
              className={cx(
                "h-4 w-4",
                copy.tone === "success" && "text-success",
                copy.tone === "warning" && "text-warning",
                copy.tone === "danger" && "text-danger",
              )}
            />
            {copy.label}
          </span>
        }
        actions={
          <Chip
            tone={
              confidence.ood_level === "in_domain"
                ? "success"
                : confidence.ood_level === "caution"
                  ? "warning"
                  : "danger"
            }
          >
            {confidence.ood_level.replace(/_/g, " ")}
          </Chip>
        }
      />
      <PanelBody className="space-y-4">
        <p className="text-xs leading-relaxed text-ink-muted">{copy.body}</p>

        <div>
          <div className="mb-1.5 flex items-baseline justify-between">
            <span className="text-2xs font-medium uppercase tracking-wider text-ink-faint">
              Distance to training data
            </span>
            <span className="tnum font-mono text-xs text-ink">
              {formatFixed(confidence.ood_ratio, 2)}× reference
            </span>
          </div>
          <OodMeter ratio={confidence.ood_ratio} />
        </div>

        <div className="grid grid-cols-3 gap-3 border-t border-line pt-3">
          <KeyValueRow
            label="Bounds"
            value={confidence.bounds_ok ? "ok" : "violated"}
            tone={confidence.bounds_ok ? "ok" : "bad"}
          />
          <KeyValueRow
            label="Member spread"
            value={`${formatFixed(confidence.max_member_spread_pct, 1)}%`}
            tone={confidence.max_member_spread_pct > 15 ? "warn" : "ok"}
          />
          <KeyValueRow label="Inference" value={`${formatFixed(latencyMs, 1)} ms`} />
        </div>

        {confidence.reasons.length > 0 && (
          <ul className="space-y-1 border-t border-line pt-3">
            {confidence.reasons.map((reason) => (
              <li key={reason} className="flex gap-2 text-xs leading-relaxed text-danger">
                <span className="text-danger">—</span>
                {reason}
              </li>
            ))}
          </ul>
        )}
      </PanelBody>
    </Panel>
  );
}

function KeyValueRow({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string;
  tone?: "default" | "ok" | "warn" | "bad";
}) {
  return (
    <div>
      <div className="text-2xs font-medium uppercase tracking-wider text-ink-faint">
        {label}
      </div>
      <div
        className={cx(
          "tnum mt-0.5 font-mono text-xs",
          tone === "ok" && "text-success",
          tone === "warn" && "text-warning",
          tone === "bad" && "text-danger",
          tone === "default" && "text-ink",
        )}
      >
        {value}
      </div>
    </div>
  );
}
