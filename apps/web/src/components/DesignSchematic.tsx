import { useId } from "react";

import type { Design } from "../lib/api";
import { PlateSchematic } from "./PlateSchematic";
import { cx } from "./ui";

const INK = "var(--color-text-primary)";
const MUTED = "var(--color-text-muted)";
const FAINT = "var(--color-text-muted)";
const LINE = "var(--color-border-hover)";
const ACCENT = "var(--color-accent-strong)";
const PAPER = "var(--color-surface-default)";

type Defs = { uid: string; arrow: number; hatch: number };

function SchematicDefs({ uid, arrow, hatch }: Defs) {
  return (
    <defs>
      <marker
        id={`${uid}-dim-start`}
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
        id={`${uid}-dim-end`}
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
        id={`${uid}-load`}
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
        width={hatch}
        height={hatch}
        patternUnits="userSpaceOnUse"
        patternTransform="rotate(45)"
      >
        <line
          x1="0"
          y1="0"
          x2="0"
          y2={hatch}
          stroke={LINE}
          strokeWidth={1}
          vectorEffect="non-scaling-stroke"
        />
      </pattern>
    </defs>
  );
}

function Shape({ d }: { d: string }) {
  return (
    <path
      d={d}
      fill={PAPER}
      stroke={INK}
      strokeWidth={1.25}
      vectorEffect="non-scaling-stroke"
    />
  );
}

function Clamp({
  uid,
  x,
  y,
  height,
  fs,
  hatch,
}: {
  uid: string;
  x: number;
  y: number;
  height: number;
  fs: number;
  hatch: number;
}) {
  const wall = Math.max(hatch * 0.5, 4);
  return (
    <g>
      <rect
        x={x - wall}
        y={y}
        width={wall}
        height={height}
        fill={`url(#${uid}-hatch)`}
        stroke={INK}
        strokeWidth={1}
        vectorEffect="non-scaling-stroke"
      />
      <text
        x={x - wall - fs * 0.45}
        y={y + height / 2}
        fontSize={fs * 0.85}
        fill={FAINT}
        textAnchor="middle"
        transform={`rotate(-90 ${x - wall - fs * 0.45} ${y + height / 2})`}
        className="font-mono"
      >
        clamped
      </text>
    </g>
  );
}

function Dim({
  uid,
  x1,
  y1,
  x2,
  y2,
}: {
  uid: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}) {
  return (
    <line
      x1={x1}
      y1={y1}
      x2={x2}
      y2={y2}
      stroke={INK}
      strokeWidth={0.75}
      vectorEffect="non-scaling-stroke"
      markerStart={`url(#${uid}-dim-start)`}
      markerEnd={`url(#${uid}-dim-end)`}
    />
  );
}

function SteppedSchematic({ design }: { design: Design }) {
  const uid = useId().replace(/[^a-zA-Z0-9]/g, "");
  const L = design.length_mm;
  const T = design.thickness_mm;
  const t2 = design.step_thickness_mm;
  const step = design.step_x_mm;
  const r = Math.min(design.fillet_radius_mm, (T - t2) / 2, L - step);
  const top = (T - t2) / 2;
  const bottom = (T + t2) / 2;
  const topArcY = top + r;
  const bottomArcY = bottom - r;

  const leftPad = Math.max(0.12 * L, 12);
  const rightPad = Math.max(0.22 * L, 22);
  const topPad = Math.max(0.7 * T, 16);
  const bottomPad = Math.max(0.6 * T, 14);
  const vbW = L + leftPad + rightPad;
  const vbH = T + topPad + bottomPad;
  const fs = vbW * 0.019;
  const arrow = vbW * 0.013;
  const hatch = T * 0.18;

  const body = [
    `M0,0`,
    `L${step},0`,
    `L${step},${topArcY}`,
    `Q${step},${top} ${step - r},${top}`,
    `L${L},${top}`,
    `L${L},${bottom}`,
    `L${step - r},${bottom}`,
    `Q${step},${bottom} ${step},${bottomArcY}`,
    `L${step},${T}`,
    `L0,${T}`,
    "Z",
  ].join(" ");

  const lDimY = T + bottomPad * 0.55;
  const tDimX = L + rightPad * 0.45;

  return (
    <svg
      viewBox={`${-leftPad} ${-topPad} ${vbW} ${vbH}`}
      className="h-auto w-full"
      role="img"
      aria-label="Stepped plate side elevation"
    >
      <SchematicDefs uid={uid} arrow={arrow} hatch={hatch} />
      <Shape d={body} />
      <g stroke={LINE} strokeWidth={0.75} strokeDasharray={`${fs * 2.4} ${fs * 1.1}`}>
        <line x1={0} y1={T / 2} x2={L} y2={T / 2} />
      </g>
      <Clamp uid={uid} x={0} y={0} height={T} fs={fs} hatch={hatch} />

      <line
        x1={L}
        y1={-0.45 * T}
        x2={L}
        y2={-fs * 0.3}
        stroke={ACCENT}
        strokeWidth={1.4}
        markerEnd={`url(#${uid}-load)`}
        vectorEffect="non-scaling-stroke"
      />
      <text x={L - fs * 0.5} y={-0.62 * T} fontSize={fs} fill={ACCENT} textAnchor="end" className="font-mono">
        F = {design.force_n.toFixed(0)} N
      </text>

      <g>
        <line x1={0} y1={T + fs * 0.4} x2={0} y2={lDimY + fs * 0.4} stroke={INK} strokeWidth={0.75} vectorEffect="non-scaling-stroke" />
        <line x1={L} y1={T + fs * 0.4} x2={L} y2={lDimY + fs * 0.4} stroke={INK} strokeWidth={0.75} vectorEffect="non-scaling-stroke" />
        <Dim uid={uid} x1={0} y1={lDimY} x2={L} y2={lDimY} />
        <line x1={step} y1={-fs * 0.5} x2={step} y2={-fs * 3.2} stroke={INK} strokeWidth={0.75} vectorEffect="non-scaling-stroke" />
        <Dim uid={uid} x1={0} y1={-fs * 2.4} x2={step} y2={-fs * 2.4} />
        <line x1={L + fs * 0.4} y1={top} x2={tDimX + fs * 0.4} y2={top} stroke={INK} strokeWidth={0.75} vectorEffect="non-scaling-stroke" />
        <line x1={L + fs * 0.4} y1={bottom} x2={tDimX + fs * 0.4} y2={bottom} stroke={INK} strokeWidth={0.75} vectorEffect="non-scaling-stroke" />
        <Dim uid={uid} x1={tDimX} y1={top} x2={tDimX} y2={bottom} />
      </g>

      <g className="font-mono" fill={MUTED}>
        <text x={L / 2} y={lDimY + fs * 1.3} fontSize={fs} textAnchor="middle">
          L = {L.toFixed(1)} mm
        </text>
        <text x={step / 2} y={-fs * 3.1} fontSize={fs} textAnchor="middle">
          step x = {step.toFixed(1)} mm
        </text>
        <text x={tDimX + fs * 0.6} y={(top + bottom) / 2 + fs * 0.35} fontSize={fs}>
          t₂ = {t2.toFixed(1)} mm
        </text>
        <text x={fs * 0.6} y={T / 2 + fs * 0.35} fontSize={fs * 0.9}>
          T = {T.toFixed(1)} mm
        </text>
        <text x={step + fs * 0.8} y={bottom + fs * 1.6} fontSize={fs * 0.85} fill={ACCENT}>
          fillet r = {r.toFixed(2)} mm
        </text>
      </g>
    </svg>
  );
}

function IBeamSchematic({ design }: { design: Design }) {
  const uid = useId().replace(/[^a-zA-Z0-9]/g, "");
  const L = design.length_mm;
  const D = design.beam_depth_mm;
  const Fw = design.flange_width_mm;
  const tf = design.flange_thickness_mm;
  const tw = design.web_thickness_mm;
  const r = Math.min(design.fillet_radius_mm, tf * 0.9, (Fw - tw) / 2);

  const leftPad = Math.max(0.35 * Fw, 20);
  const rightPad = Math.max(0.4 * Fw, 24);
  const topPad = Math.max(0.35 * D, 18);
  const bottomPad = Math.max(0.5 * D, 26);
  const vbW = Fw + leftPad + rightPad;
  const vbH = D + topPad + bottomPad;
  const fs = vbW * 0.024;
  const arrow = vbW * 0.015;
  const hatch = Fw * 0.12;

  // Profile in (y, z); SVG x = y + Fw/2, SVG y = D/2 - z.
  const y = Fw / 2;
  const body = [
    `M0,${D}`,
    `L${Fw},${D}`,
    `L${Fw},${D - tf}`,
    `L${y + tw / 2 + r},${D - tf}`,
    `Q${y + tw / 2},${D - tf} ${y + tw / 2},${D - tf - r}`,
    `L${y + tw / 2},${tf + r}`,
    `Q${y + tw / 2},${tf} ${y + tw / 2 + r},${tf}`,
    `L${Fw},${tf}`,
    `L${Fw},0`,
    `L0,0`,
    `L0,${tf}`,
    `L${y - tw / 2 - r},${tf}`,
    `Q${y - tw / 2},${tf} ${y - tw / 2},${tf + r}`,
    `L${y - tw / 2},${D - tf - r}`,
    `Q${y - tw / 2},${D - tf} ${y - tw / 2 - r},${D - tf}`,
    `L0,${D - tf}`,
    "Z",
  ].join(" ");

  return (
    <svg
      viewBox={`${-leftPad} ${-topPad} ${vbW} ${vbH}`}
      className="h-auto w-full"
      role="img"
      aria-label="I-beam cross-section"
    >
      <SchematicDefs uid={uid} arrow={arrow} hatch={hatch} />
      <Shape d={body} />
      <g className="font-mono" fill={MUTED}>
        <text x={Fw / 2} y={-topPad * 0.35} fontSize={fs} textAnchor="middle">
          cross-section · extruded length L = {L.toFixed(0)} mm
        </text>
        <text x={Fw / 2} y={D + bottomPad * 0.7} fontSize={fs} textAnchor="middle">
          flange width {Fw.toFixed(1)} mm
        </text>
        <text x={Fw + rightPad * 0.12} y={D / 2 + fs * 0.35} fontSize={fs}>
          depth {D.toFixed(1)} mm
        </text>
        <text x={Fw * 0.06} y={D - tf / 2 + fs * 0.3} fontSize={fs * 0.85} fill={ACCENT}>
          t_f = {tf.toFixed(1)} mm
        </text>
        <text x={y + tw / 2 + fs * 0.5} y={D / 2 + fs * 0.3} fontSize={fs * 0.85} fill={ACCENT}>
          t_w = {tw.toFixed(1)} mm
        </text>
        <text x={Fw / 2} y={D + bottomPad * 1.35} fontSize={fs * 0.85} fill={ACCENT} textAnchor="middle">
          fillet r = {r.toFixed(2)} mm
        </text>
      </g>
    </svg>
  );
}

function LBracketSchematic({ design }: { design: Design }) {
  const uid = useId().replace(/[^a-zA-Z0-9]/g, "");
  const L = design.length_mm;
  const H = design.height_mm;
  const T = design.thickness_mm;
  const r = Math.min(design.fillet_radius_mm, T * 0.9, L - T, H - T);

  const leftPad = Math.max(0.18 * L, 18);
  const rightPad = Math.max(0.22 * L, 22);
  const topPad = Math.max(0.25 * H, 20);
  const bottomPad = Math.max(0.25 * T, 12);
  const svgH = H + T / 2;
  const vbW = L + leftPad + rightPad;
  const vbH = svgH + topPad + bottomPad;
  const fs = vbW * 0.02;
  const arrow = vbW * 0.014;
  const hatch = T * 0.22;

  // z maps to svg y as H - z; z from -T/2 to H.
  const yOf = (zValue: number) => H - zValue;
  const body = [
    `M0,${yOf(-T / 2)}`,
    `L${L},${yOf(-T / 2)}`,
    `L${L},${yOf(H)}`,
    `L${L - T},${yOf(H)}`,
    `L${L - T},${yOf(T / 2 + r)}`,
    `Q${L - T},${yOf(T / 2)} ${L - T + r},${yOf(T / 2)}`,
    `L0,${yOf(T / 2)}`,
    "Z",
  ].join(" ");

  const lDimY = yOf(-T / 2) + bottomPad * 0.5;
  const hDimX = L + rightPad * 0.45;

  return (
    <svg
      viewBox={`${-leftPad} ${-topPad} ${vbW} ${vbH}`}
      className="h-auto w-full"
      role="img"
      aria-label="L-bracket side elevation"
    >
      <SchematicDefs uid={uid} arrow={arrow} hatch={hatch} />
      <Shape d={body} />
      <g stroke={LINE} strokeWidth={0.75} strokeDasharray={`${fs * 2.4} ${fs * 1.1}`}>
        <line x1={0} y1={yOf(-T / 2)} x2={L - T} y2={yOf(-T / 2)} />
        <line x1={L - T} y1={yOf(T / 2)} x2={L - T} y2={yOf(H)} />
      </g>
      <Clamp uid={uid} x={0} y={yOf(T / 2)} height={T} fs={fs} hatch={hatch} />

      <line
        x1={L + fs * 1.2}
        y1={yOf(H) - fs * 0.4}
        x2={L - T / 2 - fs * 0.2}
        y2={yOf(H) - fs * 0.4}
        stroke={ACCENT}
        strokeWidth={1.4}
        markerEnd={`url(#${uid}-load)`}
        vectorEffect="non-scaling-stroke"
      />
      <text x={L + fs * 1.3} y={yOf(H) - fs * 0.9} fontSize={fs} fill={ACCENT} textAnchor="end" className="font-mono">
        F = {design.force_n.toFixed(0)} N
      </text>

      <g>
        <line x1={0} y1={lDimY - fs * 0.4} x2={0} y2={lDimY + fs * 0.4} stroke={INK} strokeWidth={0.75} vectorEffect="non-scaling-stroke" />
        <line x1={L} y1={yOf(-T / 2) + fs * 0.4} x2={L} y2={lDimY + fs * 0.4} stroke={INK} strokeWidth={0.75} vectorEffect="non-scaling-stroke" />
        <Dim uid={uid} x1={0} y1={lDimY} x2={L} y2={lDimY} />
        <line x1={L + fs * 0.4} y1={yOf(H)} x2={hDimX + fs * 0.4} y2={yOf(H)} stroke={INK} strokeWidth={0.75} vectorEffect="non-scaling-stroke" />
        <line x1={L + fs * 0.4} y1={yOf(H)} x2={hDimX + fs * 0.4} y2={yOf(H)} stroke={INK} strokeWidth={0.75} vectorEffect="non-scaling-stroke" />
        <Dim uid={uid} x1={hDimX} y1={yOf(H)} x2={hDimX} y2={yOf(-T / 2)} />
      </g>

      <g className="font-mono" fill={MUTED}>
        <text x={L / 2} y={lDimY + fs * 1.3} fontSize={fs} textAnchor="middle">
          base L = {L.toFixed(1)} mm
        </text>
        <text x={hDimX + fs * 0.6} y={yOf(H / 2) + fs * 0.35} fontSize={fs}>
          height H = {H.toFixed(1)} mm
        </text>
        <text x={fs * 0.4} y={yOf(T / 2) + fs * 1.5} fontSize={fs * 0.88}>
          T = {T.toFixed(1)} mm · width {design.width_mm.toFixed(0)} mm out of plane
        </text>
        <text x={L - T + r} y={yOf(T / 2) + fs * 1.7} fontSize={fs * 0.85} fill={ACCENT}>
          fillet r = {r.toFixed(2)} mm
        </text>
      </g>
    </svg>
  );
}

export function DesignSchematic({
  design,
  className,
}: {
  design: Design;
  className?: string;
}) {
  switch (design.shape) {
    case "multi_hole":
      return (
        <PlateSchematic
          design={design}
          className={className}
          holes={[
            ...(design.hole_diameter_mm > 0
              ? [{ x: design.hole_x_mm, d: design.hole_diameter_mm }]
              : []),
            ...(design.hole2_diameter_mm > 0
              ? [{ x: design.hole2_x_mm, d: design.hole2_diameter_mm }]
              : []),
          ]}
        />
      );
    case "taper":
      return (
        <PlateSchematic
          design={design}
          className={className}
          tipWidth={design.tip_width_mm}
        />
      );
    case "stepped":
      return (
        <div className={cx(className)}>
          <SteppedSchematic design={design} />
        </div>
      );
    case "i_beam":
      return (
        <div className={cx(className)}>
          <IBeamSchematic design={design} />
        </div>
      );
    case "l_bracket":
      return (
        <div className={cx(className)}>
          <LBracketSchematic design={design} />
        </div>
      );
    default:
      return <PlateSchematic design={design} className={className} />;
  }
}
