import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useQuery } from "@tanstack/react-query";

import {
  api,
  type ConfigResponse,
  type Design,
  type DesignBounds,
  type ShapeInfo,
} from "../lib/api";

const STORAGE_KEY = "surrosim.design.v2";

export const FALLBACK_DESIGN: Design = {
  shape: "plate",
  length_mm: 120,
  width_mm: 40,
  thickness_mm: 6,
  hole_diameter_mm: 12,
  hole_x_mm: 60,
  hole2_diameter_mm: 0,
  hole2_x_mm: 0,
  tip_width_mm: 40,
  step_x_mm: 60,
  step_thickness_mm: 6,
  fillet_radius_mm: 0,
  flange_width_mm: 40,
  beam_depth_mm: 40,
  flange_thickness_mm: 6,
  web_thickness_mm: 5,
  height_mm: 90,
  force_n: 500,
  youngs_modulus_mpa: 210000,
  poisson_ratio: 0.3,
};

const FALLBACK_SHAPES: Record<string, Design> = {
  plate: FALLBACK_DESIGN,
  multi_hole: {
    ...FALLBACK_DESIGN,
    shape: "multi_hole",
    hole_diameter_mm: 12,
    hole_x_mm: 45,
    hole2_diameter_mm: 9,
    hole2_x_mm: 85,
  },
  taper: { ...FALLBACK_DESIGN, shape: "taper", tip_width_mm: 22 },
  stepped: {
    ...FALLBACK_DESIGN,
    shape: "stepped",
    thickness_mm: 9,
    step_x_mm: 60,
    step_thickness_mm: 4,
    fillet_radius_mm: 1.4,
  },
  i_beam: {
    ...FALLBACK_DESIGN,
    shape: "i_beam",
    beam_depth_mm: 55,
    flange_width_mm: 45,
    flange_thickness_mm: 8,
    web_thickness_mm: 5,
    fillet_radius_mm: 2,
  },
  l_bracket: {
    ...FALLBACK_DESIGN,
    shape: "l_bracket",
    length_mm: 80,
    height_mm: 90,
    width_mm: 30,
    thickness_mm: 8,
    fillet_radius_mm: 2,
  },
};

export const FALLBACK_BOUNDS: DesignBounds = {
  length_mm: [100, 160],
  width_mm: [30, 60],
  thickness_mm: [4, 10],
  force_n: [100, 800],
  hole_diameter_mm: [0, 27],
  hole_position_fraction: [0.35, 0.65],
};

function clamp(value: number, low: number, high: number): number {
  return Math.min(Math.max(value, low), high);
}

function round(value: number, decimals = 3): number {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}

export function normalizeDesign(input: Design): Design {
  const design = { ...FALLBACK_DESIGN, ...input };
  const shape = design.shape || "plate";
  const length = clamp(design.length_mm, 10, 500);
  const width = clamp(design.width_mm, 5, 300);
  const thickness = clamp(design.thickness_mm, 0.5, 100);
  const hasHoles = shape === "plate" || shape === "multi_hole" || shape === "taper";
  const maxDiameter = hasHoles ? Math.min(0.45 * width, 60) : 0;
  const diameter = hasHoles ? clamp(design.hole_diameter_mm, 0, maxDiameter) : 0;
  const radius = diameter / 2;
  const holeX =
    diameter > 0
      ? clamp(design.hole_x_mm, radius + 0.5, length - radius - 0.5)
      : design.hole_x_mm;
  const hole2 =
    shape === "multi_hole" ? clamp(design.hole2_diameter_mm, 0, maxDiameter) : 0;
  const hole2X = hole2 > 0 ? clamp(design.hole2_x_mm, 0.5, length - 0.5) : design.hole2_x_mm;
  const tipWidth =
    shape === "taper"
      ? clamp(design.tip_width_mm, 0.15 * width, width)
      : design.tip_width_mm;
  const stepThickness =
    shape === "stepped"
      ? clamp(design.step_thickness_mm, 0.15 * thickness, 0.95 * thickness)
      : design.step_thickness_mm;
  const stepX = shape === "stepped" ? clamp(design.step_x_mm, 5, length - 5) : design.step_x_mm;
  const fillet = Math.max(design.fillet_radius_mm, 0);
  return {
    ...design,
    shape,
    length_mm: round(length, 2),
    width_mm: round(width, 2),
    thickness_mm: round(thickness, 2),
    hole_diameter_mm: round(diameter, 2),
    hole_x_mm: round(holeX, 2),
    hole2_diameter_mm: round(hole2, 2),
    hole2_x_mm: round(hole2X, 2),
    tip_width_mm: round(tipWidth, 2),
    step_x_mm: round(stepX, 2),
    step_thickness_mm: round(stepThickness, 2),
    fillet_radius_mm: round(fillet, 3),
    force_n: clamp(design.force_n, -5000, 5000),
  };
}

function loadStoredDesign(): Design | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return null;
    }
    const parsed = JSON.parse(raw) as Partial<Design>;
    return normalizeDesign({ ...FALLBACK_DESIGN, ...parsed } as Design);
  } catch {
    return null;
  }
}

type DesignContextValue = {
  design: Design;
  setDesign: (next: Design) => void;
  patch: (partial: Partial<Design>) => void;
  reset: () => void;
  setShape: (kind: string) => void;
  bounds: DesignBounds;
  defaults: Design;
  shapeInfo: ShapeInfo | null;
  config: ConfigResponse | null;
  configLoading: boolean;
  configError: string | null;
};

const DesignContext = createContext<DesignContextValue | null>(null);

export function DesignProvider({ children }: { children: ReactNode }) {
  const configQuery = useQuery({
    queryKey: ["config"],
    queryFn: api.config,
    staleTime: Infinity,
    retry: 1,
  });

  const [design, setDesignState] = useState<Design>(
    () => loadStoredDesign() ?? FALLBACK_DESIGN,
  );

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(design));
  }, [design]);

  const config = configQuery.data ?? null;
  const bounds = config?.design_bounds ?? FALLBACK_BOUNDS;
  const shapeInfo = useMemo<ShapeInfo | null>(() => {
    if (!config?.shapes) {
      return null;
    }
    return config.shapes.find((entry) => entry.kind === design.shape) ?? null;
  }, [config, design.shape]);

  const defaults = useMemo<Design>(() => {
    if (shapeInfo?.defaults) {
      return shapeInfo.defaults;
    }
    if (!config) {
      return FALLBACK_DESIGN;
    }
    const { mesh_size_mm: _meshSize, ...rest } = config.design_defaults;
    return rest as Design;
  }, [config, shapeInfo]);

  const setDesign = useCallback((next: Design) => {
    setDesignState(normalizeDesign(next));
  }, []);

  const patch = useCallback((partial: Partial<Design>) => {
    setDesignState((current) => normalizeDesign({ ...current, ...partial }));
  }, []);

  const setShape = useCallback(
    (kind: string) => {
      setDesignState((current) => {
        const info = config?.shapes?.find((entry) => entry.kind === kind);
        const base =
          info?.defaults ??
          FALLBACK_SHAPES[kind] ?? { ...FALLBACK_DESIGN, shape: kind };
        return normalizeDesign({
          ...base,
          force_n: current.force_n,
          youngs_modulus_mpa: current.youngs_modulus_mpa,
          poisson_ratio: current.poisson_ratio,
        });
      });
    },
    [config],
  );

  const reset = useCallback(() => {
    setDesignState(normalizeDesign(defaults));
  }, [defaults]);

  const value = useMemo<DesignContextValue>(
    () => ({
      design,
      setDesign,
      patch,
      reset,
      setShape,
      bounds,
      defaults,
      shapeInfo,
      config,
      configLoading: configQuery.isLoading,
      configError: configQuery.error ? String(configQuery.error) : null,
    }),
    [
      design,
      setDesign,
      patch,
      reset,
      setShape,
      bounds,
      defaults,
      shapeInfo,
      config,
      configQuery.isLoading,
      configQuery.error,
    ],
  );

  return <DesignContext.Provider value={value}>{children}</DesignContext.Provider>;
}

export function useDesign(): DesignContextValue {
  const context = useContext(DesignContext);
  if (!context) {
    throw new Error("useDesign must be used inside DesignProvider");
  }
  return context;
}
