export type Design = {
  shape: string;
  length_mm: number;
  width_mm: number;
  thickness_mm: number;
  hole_diameter_mm: number;
  hole_x_mm: number;
  hole2_diameter_mm: number;
  hole2_x_mm: number;
  tip_width_mm: number;
  step_x_mm: number;
  step_thickness_mm: number;
  fillet_radius_mm: number;
  flange_width_mm: number;
  beam_depth_mm: number;
  flange_thickness_mm: number;
  web_thickness_mm: number;
  height_mm: number;
  force_n: number;
  youngs_modulus_mpa: number;
  poisson_ratio: number;
};

export type ShapeParamInfo = {
  name: keyof Design;
  label: string;
  unit: string;
  default: number;
  bounds: [number, number] | null;
};

export type ShapeInfo = {
  kind: string;
  label: string;
  summary: string;
  has_hole: boolean;
  has_fillet: boolean;
  load_dof: number;
  defaults: Design;
  bounds: Partial<Record<keyof Design, [number, number]>>;
  params: ShapeParamInfo[];
};

export type PredictionEntry = {
  value: number | null;
  reason?: string;
  member_spread_pct?: number;
};

export type Predictions = {
  max_displacement_mm: PredictionEntry;
  global_max_von_mises_mpa: PredictionEntry;
  max_von_mises_roi_mpa: PredictionEntry;
};

export type Recommendation = "trust" | "caution" | "run_fea";

export type Confidence = {
  bounds_ok: boolean;
  bound_violations: string[];
  ood_ratio: number;
  ood_level: "in_domain" | "caution" | "out_of_domain";
  max_member_spread_pct: number;
  recommendation: Recommendation;
  reasons: string[];
};

export type PredictResponse = {
  inputs: Design;
  predictions: Predictions;
  nominal_beam_baseline: {
    nominal_tip_displacement_mm: number;
    nominal_root_bending_stress_mpa: number;
  } | null;
  confidence: Confidence;
  model: {
    registry: string;
    dataset_sha256: string;
    dataset: string;
    created_utc: string;
    targets: Record<string, string>;
    git_commit: string | null;
  };
  fea_reference: { median_solve_seconds: number | null };
  latency_ms: number;
};

export type DesignBounds = {
  length_mm: [number, number];
  width_mm: [number, number];
  thickness_mm: [number, number];
  force_n: [number, number];
  hole_diameter_mm: [number, number];
  hole_position_fraction: [number, number];
};

export type ConfigResponse = {
  design_defaults: Design & { mesh_size_mm: number };
  design_bounds: DesignBounds;
  shapes: ShapeInfo[];
  optimizer_defaults: {
    length_mm: number;
    force_n: number;
    sigma_allow_mpa: number;
    displacement_limit_mm: number;
  };
  optimizer_bounds: Record<string, [number, number]>;
  mesh_policy: Record<string, number | string>;
  capabilities: {
    calculix: boolean;
    field_model: boolean;
    max_job_workers: number;
  };
};

export type JobStatus = "queued" | "running" | "succeeded" | "failed";

export type JobLogEntry = {
  time: string;
  level: "info" | "warning" | "error" | string;
  message: string;
};

export type Job<T = unknown> = {
  id: string;
  kind: string;
  status: JobStatus;
  stage: string;
  progress: number | null;
  created_utc: string;
  started_utc: string | null;
  finished_utc: string | null;
  elapsed_seconds: number;
  logs: JobLogEntry[];
  result: T | null;
  error: string | null;
};

export type ComparisonRow = {
  target: string;
  label: string;
  unit: string;
  surrogate: number | null;
  fea: number | null;
  error_pct: number | null;
};

export type FeaVerifyResult = {
  case_id: string;
  status: string;
  cached: boolean;
  design: Design;
  deck: {
    nodes: number;
    volume_elements: number;
    fixed_nodes: number;
    load_nodes: number;
    total_applied_force_n: number;
    element_type: string;
    element_order: number;
  } | null;
  solver: { status: string; runtime_seconds: number | null } | null;
  fea: Record<string, number | null>;
  surrogate: Predictions;
  confidence: Confidence;
  comparison: ComparisonRow[];
  available_fields: string[];
  surrogate_latency_ms: number;
};

export type FieldPredictResult = {
  design: Design;
  model: string;
  graph_nodes: number;
  runtime_ms: number;
  scalars: {
    max_displacement_mm: number;
    global_max_von_mises_mpa: number;
    roi_max_von_mises_mpa: number | null;
  };
  available_fields: string[];
};

export type FieldPayload = {
  field: string;
  label: string;
  unit: string;
  vertices: [number, number, number][];
  faces: [number, number, number][];
  intensity: number[];
  intensity_mode?: "vertex";
  min: number;
  max: number;
};

export type OptimizationCandidate = {
  design: Design;
  mass_g: number;
  stress_mpa: number;
  displacement_mm: number;
  feasible: boolean;
  stress_ratio: number;
  displacement_ratio: number;
};

export type VerificationRecord = {
  case_id: string;
  status: string;
  design: Design;
  fea_global_stress_mpa?: number | null;
  fea_roi_stress_mpa?: number | null;
  fea_max_displacement_mm?: number | null;
  fea_stress_error_pct?: number | null;
  fea_displacement_error_pct?: number | null;
  fea_feasible?: boolean;
  solver_seconds?: number | null;
};

export type OptimizationResult = {
  created_utc: string;
  problem: {
    length_mm: number;
    force_n: number;
    sigma_allow_mpa: number;
    displacement_limit_mm: number;
    width_bounds: [number, number];
    thickness_bounds: [number, number];
    diameter_ratio_bounds: [number, number];
    hole_x_ratio_bounds: [number, number];
  };
  optimizer: {
    method: string;
    seed: number;
    maxiter: number;
    popsize: number;
    evaluations: number;
    seconds: number;
    best_objective: number;
  };
  candidates: OptimizationCandidate[];
  verification: VerificationRecord[];
  evaluations: {
    mass_g: number[];
    stress_mpa: number[];
    displacement_mm: number[];
    feasible: boolean[];
  };
  surrogate_model: Record<string, string>;
  dataset_sha256: string;
};

export type ReportModelRow = {
  model: string;
  params: unknown;
  val_mape_pct: number | null;
  test_mape_pct: number;
  test_worst_pct: number;
  test_rmse: number | null;
  test_r2: number | null;
  challenge_mape_pct: number;
  challenge_worst_pct: number;
  latency_ms_per_1k: number | null;
  path: string | null;
};

export type FieldModelInfo = {
  present: boolean;
  path: string;
  schema_version?: string | null;
  created_utc?: string | null;
  device?: string | null;
  config?: Record<string, number | string> | null;
  split_counts?: Record<string, number> | null;
  node_features: string[];
  edge_features: string[];
  targets: string[];
  normalisation?: {
    nodes?: number | null;
    target_scaling?: string | null;
  } | null;
  training?: {
    seconds?: number | null;
    epochs_run?: number | null;
    best_val_loss?: number | null;
  } | null;
  evaluation?: Record<
    string,
    {
      cases?: number | null;
      max_displacement?: { mape: number; worst: number } | null;
      global_max_vm?: { mape: number; worst: number } | null;
      roi_max_vm?: { mape: number; worst: number } | null;
      field_vm_error_median_pct?: number | null;
      field_vm_error_p95_pct?: number | null;
    }
  > | null;
};

export type ReportResponse = {
  registry: string;
  created_utc: string;
  git: { commit?: string; describe?: string } | null;
  dataset: {
    path: string;
    sha256: string;
    created_utc: string;
    row_count: number | null;
    split_counts: Record<string, number> | null;
  };
  targets: {
    target: string;
    best_model: string;
    selection_rule: string | null;
    models: ReportModelRow[];
    baselines: {
      name: string;
      test_mape_pct: number | null;
      test_worst_pct: number | null;
      test_rmse: number | null;
    }[];
  }[];
  figures: { name: string; group: string; url: string }[];
  cards: Record<string, string | null>;
  registry_meta: {
    schema_version?: string | null;
    seed?: number | null;
    created_utc?: string | null;
    dataset?: string | null;
    target_transform?: string | null;
    features: string[];
    selections: Record<
      string,
      { best_model: string | null; selection_rule: string | null }
    >;
  };
  field_model: FieldModelInfo | null;
};

export type RangeStat = {
  name: string;
  min: number;
  mean: number;
  max: number;
};

export type DatasetReportResponse = {
  path: string;
  sha256: string;
  created_utc: string;
  row_count: number | null;
  split_counts: Record<string, number>;
  shape_counts: Record<string, number>;
  manifest: {
    schema_version?: string | null;
    designs_file?: string | null;
    designs_sha256?: string | null;
    cases_in_designs?: number | null;
    cases_from_base?: number | null;
    cases_in_dataset?: number | null;
    cases_failed?: number | null;
    solver?: { versions?: string[]; total_solver_seconds?: number } | null;
    environment?: Record<string, string> | null;
    git?: { commit?: string; dirty?: boolean } | null;
    gates: string[];
    mesh_policy?: Record<string, number | string> | null;
    base_datasets: { path: string; sha256: string; cases: number }[];
  } | null;
  design_ranges: RangeStat[];
  target_ranges: RangeStat[];
  median_runtime_seconds: number | null;
  mesh: {
    median_nodes: number | null;
    median_elements: number | null;
    element_type: string | null;
  };
  card: string | null;
};

export type ModelInfo = {
  registry: string;
  dataset_sha256: string;
  created_utc: string;
  targets: Record<string, string>;
  git_commit: string | null;
};

export class ApiError extends Error {
  status: number;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") {
        detail = body.detail;
      } else if (body.detail) {
        detail = JSON.stringify(body.detail);
      }
    } catch {
      // keep status text
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

export const api = {
  config: () => request<ConfigResponse>("/api/config"),
  model: () => request<ModelInfo>("/api/model"),
  predict: (design: Design) =>
    request<PredictResponse>("/api/predict", {
      method: "POST",
      body: JSON.stringify(design),
    }),
  report: () => request<ReportResponse>("/api/reports/model"),
  datasetReport: () => request<DatasetReportResponse>("/api/reports/dataset"),
  job: (jobId: string) => request<Job>(`/api/jobs/${jobId}`),
  field: (jobId: string, field: string) =>
    request<FieldPayload>(`/api/fields/${jobId}?field=${field}`),
  startFeaVerify: (design: Design, force: boolean) =>
    request<{ job: Job }>("/api/jobs/fea-verify", {
      method: "POST",
      body: JSON.stringify({ ...design, force }),
    }),
  startFieldPredict: (design: Design) =>
    request<{ job: Job }>("/api/jobs/field-predict", {
      method: "POST",
      body: JSON.stringify(design),
    }),
  startOptimize: (payload: {
    shape?: string;
    length_mm: number;
    force_n: number;
    sigma_allow_mpa: number;
    displacement_limit_mm: number;
    maxiter: number;
    verify_candidates: boolean;
  }) =>
    request<{ job: Job }>("/api/jobs/optimize", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
