import { useId } from "react";

import type { Design } from "../lib/api";
import { cx } from "./ui";

const INK = "var(--color-text-primary)";
const MUTED = "var(--color-text-muted)";
const FAINT = "var(--color-text-muted)";
const LINE = "var(--color-border-hover)";
const ACCENT = "var(--color-accent-strong)";
const PAPER = "var(--color-surface-default)";

export type SchematicHole = { x: number; d: number };

export function PlateSchematic({
  design,
  className,
  holes,
  tipWidth,
}: {
  design: Design;
  className?: string;
  holes?: SchematicHole[];
  tipWidth?: number;
}) {
  const uid = useId().replace(/[^a-zA-Z0-9]/g, "");
  const {
    length_mm: L,
    width_mm: W,
    hole_diameter_mm: d,
    hole_x_mm: xh,
    force_n: F,
  } = design;

  const activeHoles: SchematicHole[] =
    holes ??
    (d > 0 ? [{ x: xh, d }] : []);
  const tip = tipWidth ?? W;
  const taper = Math.abs(tip - W) > 1e-6;

  const leftPad = Math.max(0.1 * L, 10);
  const rightPad = Math.max(0.17 * L, 16);
  const topPad = Math.max(0.5 * W, 14);
  const bottomPad = Math.max(0.4 * W, 12);
  const vbW = L + leftPad + rightPad;
  const vbH = W + topPad + bottomPad;
  const fs = vbW * 0.0168;
  const wall = Math.max(0.05 * L, 5);
  const arrow = vbW * 0.0115;

  const xDimY = -topPad * 0.45;
  const lDimY = W + bottomPad * 0.52;
  const wDimX = L + rightPad * 0.55;
  const tipTop = (W - tip) / 2;
  const tipBottom = (W + tip) / 2;

  const forceX = L;
  const forceTop = -0.42 * W;
  const forceTip = -fs * 0.35;
  const f = 1 / Math.SQRT2;

  const body = taper
    ? `M0,0 L${L},${tipTop} L${L},${tipBottom} L0,${W} Z`
    : `M0,0 L${L},0 L${L},${W} L0,${W} Z`;
  const firstHole = activeHoles[0] ?? null;

  return (
    <svg
      viewBox={`${-leftPad} ${-topPad} ${vbW} ${vbH}`}
      className={cx("h-auto w-full", className)}
      role="img"
      aria-label="Parametric design schematic with dimensions and boundary conditions"
    >
      <defs>
        <marker
          id={`${uid}-arrow-end`}
          markerUnits="userSpaceOnUse"
          markerWidth={arrow}
          markerHeight={arrow}
          refX={arrow}
          refY={arrow / 2}
          orient="auto"
          viewBox={`0 0 ${arrow} ${arrow}`}
        >
          <path d={`M0,0 L${arrow},${arrow / 2} L0,${arrow}`} fill={INK} />
        </marker>
        <marker
          id={`${uid}-arrow-start`}
          markerUnits="userSpaceOnUse"
          markerWidth={arrow}
          markerHeight={arrow}
          refX={0}
          refY={arrow / 2}
          orient="auto"
          viewBox={`0 0 ${arrow} ${arrow}`}
        >
          <path d={`M${arrow},0 L0,${arrow / 2} L${arrow},${arrow}`} fill={INK} />
        </marker>
        <marker
          id={`${uid}-arrow-load`}
          markerUnits="userSpaceOnUse"
          markerWidth={arrow * 1.15}
          markerHeight={arrow * 1.15}
          refX={arrow * 1.15}
          refY={arrow * 0.575}
          orient="auto"
          viewBox={`0 0 ${arrow * 1.15} ${arrow * 1.15}`}
        >
          <path
            d={`M0,0 L${arrow * 1.15},${arrow * 0.575} L0,${arrow * 1.15}`}
            fill={ACCENT}
          />
        </marker>
        <pattern
          id={`${uid}-hatch`}
          width={W * 0.11}
          height={W * 0.11}
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(45)"
        >
          <line
            x1="0"
            y1="0"
            x2="0"
            y2={W * 0.11}
            stroke={LINE}
            strokeWidth={1}
            vectorEffect="non-scaling-stroke"
          />
        </pattern>
      </defs>

      <path
        d={body}
        fill={PAPER}
        stroke={INK}
        strokeWidth={1.25}
        vectorEffect="non-scaling-stroke"
      />

      <g stroke={LINE} strokeWidth={0.75} strokeDasharray={`${fs * 2.6} ${fs * 1.2} ${fs * 0.4} ${fs * 1.2}`}>
        <line x1={0} y1={W / 2} x2={L} y2={W / 2} />
        {firstHole && <line x1={firstHole.x} y1={0} x2={firstHole.x} y2={W} />}
      </g>

      {activeHoles.map((hole, index) => {
        const r = hole.d / 2;
        if (r <= 0) {
          return null;
        }
        const leader = Math.max(fs * 3.4, r * 1.9);
        return (
          <g key={`${index}-${hole.x}`}>
            <circle
              cx={hole.x}
              cy={W / 2}
              r={r}
              fill={PAPER}
              stroke={ACCENT}
              strokeWidth={1.5}
              vectorEffect="non-scaling-stroke"
            />
            <line
              x1={hole.x + r * f}
              y1={W / 2 - r * f}
              x2={hole.x + f * (r + leader)}
              y2={W / 2 - f * (r + leader)}
              stroke={ACCENT}
              strokeWidth={0.75}
              vectorEffect="non-scaling-stroke"
            />
            <circle cx={hole.x + r * f} cy={W / 2 - r * f} r={fs * 0.16} fill={ACCENT} />
            <text
              x={hole.x + f * (r + leader) + fs * 0.5}
              y={W / 2 - f * (r + leader) + fs * 0.35}
              fontSize={fs}
              fill={ACCENT}
              className="font-mono"
            >
              Ø {hole.d.toFixed(1)} mm
            </text>
          </g>
        );
      })}

      <rect
        x={-wall}
        y={-0.08 * W}
        width={wall}
        height={W + 0.16 * W}
        fill={`url(#${uid}-hatch)`}
        stroke={INK}
        strokeWidth={1}
        vectorEffect="non-scaling-stroke"
      />
      <text
        x={-wall - fs * 0.5}
        y={W / 2}
        fontSize={fs * 0.88}
        fill={FAINT}
        textAnchor="middle"
        transform={`rotate(-90 ${-wall - fs * 0.5} ${W / 2})`}
        className="font-mono"
      >
        clamped
      </text>

      <line
        x1={forceX}
        y1={forceTop}
        x2={forceX}
        y2={forceTip}
        stroke={ACCENT}
        strokeWidth={1.4}
        markerEnd={`url(#${uid}-arrow-load)`}
        vectorEffect="non-scaling-stroke"
      />
      <text
        x={forceX - fs * 0.7}
        y={forceTop - fs * 0.55}
        fontSize={fs}
        fill={ACCENT}
        textAnchor="end"
        className="font-mono"
      >
        F = {F.toFixed(0)} N
      </text>

      <g stroke={INK} strokeWidth={0.75} vectorEffect="non-scaling-stroke" fill="none">
        {firstHole && (
          <>
            <line x1={0} y1={-fs * 0.5} x2={0} y2={xDimY - fs * 0.4} />
            <line
              x1={firstHole.x}
              y1={W / 2 - firstHole.d / 2}
              x2={firstHole.x}
              y2={xDimY - fs * 0.4}
            />
            <line
              x1={0}
              y1={xDimY}
              x2={firstHole.x}
              y2={xDimY}
              markerStart={`url(#${uid}-arrow-start)`}
              markerEnd={`url(#${uid}-arrow-end)`}
            />
          </>
        )}
        <line x1={0} y1={W + fs * 0.4} x2={0} y2={lDimY + fs * 0.4} />
        <line x1={L} y1={W + fs * 0.4} x2={L} y2={lDimY + fs * 0.4} />
        <line
          x1={0}
          y1={lDimY}
          x2={L}
          y2={lDimY}
          markerStart={`url(#${uid}-arrow-start)`}
          markerEnd={`url(#${uid}-arrow-end)`}
        />
        {taper ? (
          <>
            <line x1={L + fs * 0.4} y1={tipTop} x2={wDimX + fs * 0.4} y2={tipTop} />
            <line x1={L + fs * 0.4} y1={tipBottom} x2={wDimX + fs * 0.4} y2={tipBottom} />
            <line
              x1={wDimX}
              y1={tipTop}
              x2={wDimX}
              y2={tipBottom}
              markerStart={`url(#${uid}-arrow-start)`}
              markerEnd={`url(#${uid}-arrow-end)`}
            />
          </>
        ) : (
          <>
            <line x1={L + fs * 0.4} y1={0} x2={wDimX + fs * 0.4} y2={0} />
            <line x1={L + fs * 0.4} y1={W} x2={wDimX + fs * 0.4} y2={W} />
            <line
              x1={wDimX}
              y1={0}
              x2={wDimX}
              y2={W}
              markerStart={`url(#${uid}-arrow-start)`}
              markerEnd={`url(#${uid}-arrow-end)`}
            />
          </>
        )}
      </g>

      <g className="font-mono" fill={MUTED}>
        {firstHole && (
          <text x={firstHole.x / 2} y={xDimY - fs * 0.65} fontSize={fs} textAnchor="middle">
            x = {firstHole.x.toFixed(1)} mm
          </text>
        )}
        <text x={L / 2} y={lDimY + fs * 1.25} fontSize={fs} textAnchor="middle">
          L = {L.toFixed(1)} mm
        </text>
        {taper ? (
          <>
            <text x={fs * 0.6} y={W / 2 + fs * 0.35} fontSize={fs * 0.9}>
              root W
            </text>
            <text x={wDimX + fs * 0.6} y={W / 2 + fs * 0.35} fontSize={fs}>
              tip = {tip.toFixed(1)} mm
            </text>
          </>
        ) : (
          <text x={wDimX + fs * 0.6} y={W / 2 + fs * 0.35} fontSize={fs}>
            W = {W.toFixed(1)} mm
          </text>
        )}
      </g>
    </svg>
  );
}
