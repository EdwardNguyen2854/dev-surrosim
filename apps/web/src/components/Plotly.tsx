import { useEffect, useRef } from "react";

import { cx } from "./ui";
import { usePreferences } from "../state/preferences";

let basicPromise: Promise<typeof import("plotly.js-basic-dist-min")> | null = null;
let gl3dPromise: Promise<typeof import("plotly.js-gl3d-dist-min")> | null = null;

function loadEngine(engine: "basic" | "gl3d") {
  if (engine === "gl3d") {
    gl3dPromise ??= import("plotly.js-gl3d-dist-min");
    return gl3dPromise;
  }
  basicPromise ??= import("plotly.js-basic-dist-min");
  return basicPromise;
}

type Vec3 = { x: number; y: number; z: number };

type Camera = {
  eye: Vec3;
  center: Vec3;
  up: Vec3;
};

const DEFAULT_CAMERA: Camera = {
  eye: { x: 1.25, y: 1.25, z: 1.25 },
  center: { x: 0, y: 0, z: 0 },
  up: { x: 0, y: 0, z: 1 },
};

const ORBIT_SPEED = 0.008;
const PAN_SPEED = 0.0016;
const DRAG_ZOOM_SPEED = 0.006;
const WHEEL_ZOOM_SPEED = 0.0012;
const MIN_RADIUS = 0.05;
const MAX_RADIUS = 400;

// Plotly paints into SVG/WebGL and cannot resolve CSS variables itself. Resolve
// only semantic references at the render boundary; tokens.css still owns values.
function resolveTokens<T>(value: T, styles: CSSStyleDeclaration): T {
  if (typeof value === "string") {
    const token = /^var\((--[a-z-]+)\)$/.exec(value);
    return (token ? styles.getPropertyValue(token[1]).trim() : value) as T;
  }
  if (Array.isArray(value)) return value.map((item) => resolveTokens(item, styles)) as T;
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, resolveTokens(item, styles)])) as T;
  }
  return value;
}

function add(a: Vec3, b: Vec3): Vec3 {
  return { x: a.x + b.x, y: a.y + b.y, z: a.z + b.z };
}

function sub(a: Vec3, b: Vec3): Vec3 {
  return { x: a.x - b.x, y: a.y - b.y, z: a.z - b.z };
}

function scale(v: Vec3, factor: number): Vec3 {
  return { x: v.x * factor, y: v.y * factor, z: v.z * factor };
}

function cross(a: Vec3, b: Vec3): Vec3 {
  return {
    x: a.y * b.z - a.z * b.y,
    y: a.z * b.x - a.x * b.z,
    z: a.x * b.y - a.y * b.x,
  };
}

function length(v: Vec3): number {
  return Math.hypot(v.x, v.y, v.z);
}

function normalize(v: Vec3): Vec3 {
  const magnitude = length(v);
  return magnitude > 0 ? scale(v, 1 / magnitude) : { x: 0, y: 0, z: 0 };
}

function isVec3(value: unknown): value is Vec3 {
  if (!value || typeof value !== "object") {
    return false;
  }
  const candidate = value as Partial<Vec3>;
  return (
    typeof candidate.x === "number" &&
    typeof candidate.y === "number" &&
    typeof candidate.z === "number"
  );
}

function toVec3(value: unknown): Vec3 | null {
  if (isVec3(value)) {
    return { x: value.x, y: value.y, z: value.z };
  }
  if (value && typeof value === "object") {
    const indexed = value as Record<number, unknown>;
    if (
      typeof indexed[0] === "number" &&
      typeof indexed[1] === "number" &&
      typeof indexed[2] === "number"
    ) {
      return { x: indexed[0], y: indexed[1], z: indexed[2] };
    }
  }
  return null;
}

function cameraFromLayout(layout: Record<string, unknown> | undefined): Camera {
  const scene = layout?.scene as { camera?: Record<string, unknown> } | undefined;
  const camera = scene?.camera;
  if (!camera) {
    return DEFAULT_CAMERA;
  }
  return {
    eye: isVec3(camera.eye) ? camera.eye : DEFAULT_CAMERA.eye,
    center: isVec3(camera.center) ? camera.center : DEFAULT_CAMERA.center,
    up: isVec3(camera.up) ? camera.up : DEFAULT_CAMERA.up,
  };
}

function currentCamera(plot: HTMLDivElement, fallback: Camera): Camera {
  const scene = (
    plot as unknown as {
      _fullLayout?: {
        scene?: {
          camera?: Record<string, unknown>;
          _scene?: { glplot?: { camera?: Record<string, unknown> } };
        };
      };
    }
  )._fullLayout?.scene;
  const camera = scene?._scene?.glplot?.camera ?? scene?.camera;
  if (!camera) {
    return fallback;
  }
  return {
    eye: toVec3(camera.eye) ?? { ...fallback.eye },
    center: toVec3(camera.center) ?? { ...fallback.center },
    up: toVec3(camera.up) ?? { ...fallback.up },
  };
}

function orbit(camera: Camera, dx: number, dy: number): Camera {
  const offset = sub(camera.eye, camera.center);
  const radius = length(offset) || 1;
  const theta = Math.atan2(offset.y, offset.x) - dx * ORBIT_SPEED;
  const phi = Math.min(
    Math.PI - 0.02,
    Math.max(0.02, Math.acos(offset.z / radius) - dy * ORBIT_SPEED),
  );
  return {
    ...camera,
    eye: {
      x: camera.center.x + radius * Math.sin(phi) * Math.cos(theta),
      y: camera.center.y + radius * Math.sin(phi) * Math.sin(theta),
      z: camera.center.z + radius * Math.cos(phi),
    },
  };
}

function pan(camera: Camera, dx: number, dy: number): Camera {
  const forward = normalize(sub(camera.center, camera.eye));
  let right = cross(forward, camera.up);
  if (length(right) < 1e-4) {
    right = cross(forward, { x: 0, y: 1, z: 0 });
  }
  right = normalize(right);
  const up = normalize(cross(right, forward));
  const shift = scale(
    add(scale(right, -dx), scale(up, dy)),
    (length(sub(camera.eye, camera.center)) || 1) * PAN_SPEED,
  );
  return {
    ...camera,
    eye: add(camera.eye, shift),
    center: add(camera.center, shift),
  };
}

function zoom(camera: Camera, factor: number): Camera {
  const offset = sub(camera.eye, camera.center);
  const radius = length(offset) || 1;
  const next = Math.min(MAX_RADIUS, Math.max(MIN_RADIUS, radius * factor));
  return { ...camera, eye: add(camera.center, scale(offset, next / radius)) };
}

export function PlotlyPlot({
  engine = "basic",
  data,
  layout,
  height = 320,
  className,
  navigation = "default",
  config,
}: {
  engine?: "basic" | "gl3d";
  data: unknown[];
  layout?: Record<string, unknown>;
  height?: number | string;
  className?: string;
  navigation?: "default" | "creo";
  config?: Record<string, unknown>;
}) {
  const { preferences } = usePreferences();
  const ref = useRef<HTMLDivElement | null>(null);
  const layoutRef = useRef(layout);
  useEffect(() => {
    layoutRef.current = layout;
  }, [layout]);

  useEffect(() => {
    const element = ref.current;
    if (!element) {
      return;
    }
    let cancelled = false;
    void loadEngine(engine)
      .then((module) => {
        if (cancelled) {
          return undefined;
        }
        const styles = getComputedStyle(document.documentElement);
        return module.default.react(
          element,
          resolveTokens(data, styles),
          resolveTokens({ uirevision: "surrosim-view", ...layout }, styles),
          { displayModeBar: false, responsive: true, ...config },
        );
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [engine, data, layout, config, preferences.theme]);

  useEffect(() => {
    const element = ref.current;
    return () => {
      if (!element) {
        return;
      }
      void loadEngine(engine).then((module) => {
        module.default.purge(element);
      });
    };
  }, [engine]);

  useEffect(() => {
    const element = ref.current;
    if (!element || navigation !== "creo") {
      return;
    }
    let frame = 0;
    let camera: Camera | null = null;

    const flush = () => {
      frame = 0;
      const next = camera;
      if (!next) {
        return;
      }
      void loadEngine(engine).then((module) => {
        void module.default.relayout(element, { "scene.camera": next });
      });
    };

    const schedule = () => {
      if (!frame) {
        frame = window.requestAnimationFrame(flush);
      }
    };

    const onMouseDown = (event: MouseEvent) => {
      if (event.button !== 1) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      camera = currentCamera(element, cameraFromLayout(layoutRef.current));
      const mode =
        event.ctrlKey || event.metaKey ? "zoom" : event.shiftKey ? "pan" : "orbit";
      let lastX = event.clientX;
      let lastY = event.clientY;

      const onMove = (move: MouseEvent) => {
        const dx = move.clientX - lastX;
        const dy = move.clientY - lastY;
        lastX = move.clientX;
        lastY = move.clientY;
        if (!camera || (dx === 0 && dy === 0)) {
          return;
        }
        camera =
          mode === "orbit"
            ? orbit(camera, dx, dy)
            : mode === "pan"
              ? pan(camera, dx, dy)
              : zoom(camera, Math.exp(dy * DRAG_ZOOM_SPEED));
        schedule();
      };

      const onUp = () => {
        window.removeEventListener("mousemove", onMove, true);
        window.removeEventListener("mouseup", onUp, true);
        if (frame) {
          window.cancelAnimationFrame(frame);
          flush();
        }
        camera = null;
      };

      window.addEventListener("mousemove", onMove, true);
      window.addEventListener("mouseup", onUp, true);
    };

    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      event.stopPropagation();
      const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? 100 : 1;
      camera = zoom(
        currentCamera(element, cameraFromLayout(layoutRef.current)),
        Math.exp(event.deltaY * unit * WHEEL_ZOOM_SPEED),
      );
      schedule();
    };

    const onAuxClick = (event: MouseEvent) => {
      if (event.button === 1) {
        event.preventDefault();
      }
    };

    element.addEventListener("mousedown", onMouseDown, true);
    element.addEventListener("wheel", onWheel, { capture: true, passive: false });
    element.addEventListener("auxclick", onAuxClick, true);

    return () => {
      element.removeEventListener("mousedown", onMouseDown, true);
      element.removeEventListener("wheel", onWheel, { capture: true });
      element.removeEventListener("auxclick", onAuxClick, true);
      if (frame) {
        window.cancelAnimationFrame(frame);
      }
    };
  }, [engine, navigation]);

  return (
    <div ref={ref} className={cx("w-full", className)} style={{ height }} />
  );
}

export const PLOT_FONT = {
  family: "IBM Plex Mono, Cascadia Mono, Consolas, monospace",
  size: 11,
  color: "var(--color-text-muted)",
};

export const BASE_LAYOUT: Record<string, unknown> = {
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "var(--color-surface-default)",
  font: PLOT_FONT,
  margin: { l: 58, r: 18, t: 18, b: 46 },
  xaxis: {
    gridcolor: "var(--color-border-default)",
    zerolinecolor: "var(--color-border-hover)",
    linecolor: "var(--color-border-hover)",
    ticks: "outside",
    tickcolor: "var(--color-border-hover)",
  },
  yaxis: {
    gridcolor: "var(--color-border-default)",
    zerolinecolor: "var(--color-border-hover)",
    linecolor: "var(--color-border-hover)",
    ticks: "outside",
    tickcolor: "var(--color-border-hover)",
  },
  legend: { orientation: "h", y: 1.12, x: 0, font: { size: 10 } },
  hoverlabel: {
    bgcolor: "var(--color-text-primary)",
    bordercolor: "var(--color-text-primary)",
    font: { ...PLOT_FONT, color: "var(--color-surface-canvas)" },
  },
};
