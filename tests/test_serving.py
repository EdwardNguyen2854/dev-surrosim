from pathlib import Path

import pytest

from surrosim.serving.predictor import ScalarPredictor

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "models" / "scalar" / "v1"
DATASET = ROOT / "data" / "dataset_v1" / "dataset.csv"

pytestmark = pytest.mark.skipif(
    not REGISTRY.exists(), reason="model registry not present"
)


@pytest.fixture(scope="module")
def predictor() -> ScalarPredictor:
    return ScalarPredictor.load(REGISTRY, DATASET)


DEFAULT_PLATE = {
    "length_mm": 120.0,
    "width_mm": 40.0,
    "thickness_mm": 6.0,
    "hole_diameter_mm": 12.0,
    "hole_x_mm": 60.0,
    "force_n": 500.0,
    "youngs_modulus_mpa": 210_000.0,
    "poisson_ratio": 0.3,
}


def test_prediction_reports_values_and_confidence(predictor):
    result = predictor.predict(DEFAULT_PLATE)
    assert result["predictions"]["max_displacement_mm"]["value"] == pytest.approx(
        1.93, rel=0.15
    )
    assert result["predictions"]["global_max_von_mises_mpa"]["value"] > 0
    assert result["predictions"]["max_von_mises_roi_mpa"]["value"] > 0
    confidence = result["confidence"]
    assert confidence["recommendation"] in {"trust", "caution", "run_fea"}
    assert confidence["bounds_ok"] is True
    assert result["latency_ms"] > 0
    assert result["model"]["targets"]


def test_no_hole_has_no_roi_prediction(predictor):
    plate = {**DEFAULT_PLATE, "hole_diameter_mm": 0.0, "hole_x_mm": 60.0}
    result = predictor.predict(plate)
    assert result["predictions"]["max_von_mises_roi_mpa"]["value"] is None
    assert result["predictions"]["max_displacement_mm"]["value"] > 0


def test_out_of_bounds_design_recommends_fea(predictor):
    plate = {**DEFAULT_PLATE, "length_mm": 400.0}
    result = predictor.predict(plate)
    assert result["confidence"]["bounds_ok"] is False
    assert result["confidence"]["recommendation"] == "run_fea"
    assert result["confidence"]["reasons"]


def test_ood_ratio_grows_for_extreme_corner(predictor):
    corner = {
        **DEFAULT_PLATE,
        "length_mm": 160.0,
        "width_mm": 30.0,
        "thickness_mm": 4.0,
        "force_n": 800.0,
    }
    center = predictor.predict(DEFAULT_PLATE)
    extreme = predictor.predict(corner)
    assert extreme["confidence"]["ood_ratio"] > center["confidence"]["ood_ratio"]


def test_api_contract():
    fastapi = pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from surrosim.serving.api import create_app

    client = TestClient(create_app(str(REGISTRY), str(DATASET)))
    assert client.get("/api/health").json()["status"] == "ok"
    model_info = client.get("/api/model").json()
    assert model_info["dataset_sha256"]
    domain = client.get("/api/domain").json()
    assert "length_mm" in domain["bounds"]

    response = client.post("/api/predict", json=DEFAULT_PLATE)
    assert response.status_code == 200
    payload = response.json()
    assert payload["predictions"]["max_displacement_mm"]["value"] > 0

    bad = client.post("/api/predict", json={**DEFAULT_PLATE, "length_mm": -5})
    assert bad.status_code == 422


def test_config_reports_and_job_errors():
    fastapi = pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from surrosim.serving.api import create_app

    client = TestClient(create_app(str(REGISTRY), str(DATASET)))

    config = client.get("/api/config").json()
    assert config["design_defaults"]["length_mm"] == 120.0
    assert "capabilities" in config
    assert config["optimizer_bounds"]["width_mm"] == [30.0, 60.0]

    report = client.get("/api/reports/model").json()
    assert report["targets"]
    assert report["dataset"]["sha256"]
    assert any(entry["test_mape_pct"] >= 0 for entry in report["targets"][0]["models"])
    assert report["registry_meta"]["features"]
    assert "field_model" in report

    dataset_report = client.get("/api/reports/dataset").json()
    assert dataset_report["row_count"] == 644
    assert dataset_report["split_counts"]["train"] == 392
    assert dataset_report["design_ranges"]
    assert dataset_report["target_ranges"]
    assert dataset_report["mesh"]["element_type"] == "C3D10"

    missing = client.get("/api/jobs/does-not-exist")
    assert missing.status_code == 404
    unknown_field = client.get("/api/fields/does-not-exist")
    assert unknown_field.status_code == 404


def test_job_manager_runs_and_reports_progress():
    from surrosim.serving.jobs import Job, JobManager

    manager = JobManager(max_workers=1)

    def worker(job: Job) -> dict:
        job.set_progress(0.5, "halfway")
        job.log("step one")
        return {"answer": 42}

    job = manager.submit("unit", worker)
    for _ in range(200):
        payload = manager.get(job.id).to_dict()
        if payload["status"] in ("succeeded", "failed"):
            break
        import time

        time.sleep(0.02)
    assert payload["status"] == "succeeded"
    assert payload["result"] == {"answer": 42}
    assert payload["progress"] == 1.0
    assert any(entry["message"] == "step one" for entry in payload["logs"])

    def failing(job: Job) -> dict:
        raise ValueError("boom")

    failed = manager.submit("unit", failing)
    for _ in range(200):
        payload = failed_job = manager.get(failed.id).to_dict()
        if payload["status"] in ("succeeded", "failed"):
            break
        import time

        time.sleep(0.02)
    assert failed_job["status"] == "failed"
    assert "boom" in failed_job["error"]


def test_job_process_forwards_progress_and_result():
    import time

    from surrosim.serving.jobs import JobManager, run_in_process
    from surrosim.serving.worker_process import probe_entry

    manager = JobManager(max_workers=1)

    def worker(job):
        return run_in_process(probe_entry, {"value": 7}, job, timeout_seconds=120.0)

    job = manager.submit("probe", worker)
    deadline = time.monotonic() + 120.0
    payload = manager.get(job.id).to_dict()
    while payload["status"] in ("queued", "running") and time.monotonic() < deadline:
        time.sleep(0.1)
        payload = manager.get(job.id).to_dict()
    assert payload["status"] == "succeeded", payload
    assert payload["result"] == {"value": 7}
    assert payload["progress"] == 1.0
    assert any("probing 7" in entry["message"] for entry in payload["logs"])


def test_boundary_triangles_and_field_figure(tmp_path):
    pytest.importorskip("plotly")
    from surrosim.simulation.msh2 import read_msh2
    from surrosim.serving.viz import boundary_triangles, field_figure

    msh = """$MeshFormat
2.2 0 8
$EndMeshFormat
$PhysicalNames
1
3 3 "SOLID"
$EndPhysicalNames
$Nodes
4
1 0 0 0
2 1 0 0
3 0 1 0
4 0 0 1
$EndNodes
$Elements
1
1 4 2 3 21 1 2 3 4
$EndElements
"""
    mesh_path = tmp_path / "mesh.msh"
    mesh_path.write_text(msh, encoding="utf-8")
    faces = boundary_triangles(read_msh2(mesh_path))
    assert len(faces) == 4

    import numpy as np

    npz_path = tmp_path / "fields.npz"
    np.savez(
        npz_path,
        node_id=np.array([1, 2, 3, 4]),
        **{
            "von_mises_mpa": np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32),
            "displacement_mm": np.array([0.1, 0.2, 0.3, 0.4], dtype=np.float32),
        },
    )
    figure = field_figure(mesh_path, npz_path, "von_mises_mpa")
    assert figure.data[0].type == "mesh3d"

    from surrosim.serving.viz import field_payload

    payload = field_payload(mesh_path, npz_path, "von_mises_mpa")
    assert len(payload["vertices"]) == 4
    assert len(payload["faces"]) == 4
    assert payload["unit"] == "MPa"
    assert payload["min"] <= payload["max"]


def test_quadratic_surface_subdivision_and_vertex_intensity(tmp_path):
    import numpy as np

    from surrosim.simulation.msh2 import read_msh2
    from surrosim.serving.viz import boundary_triangles, field_payload

    def write_mesh(midpoint_z: float) -> Path:
        msh = f"""$MeshFormat
2.2 0 8
$EndMeshFormat
$PhysicalNames
1
3 3 "SOLID"
$EndPhysicalNames
$Nodes
10
1 0 0 0
2 1 0 0
3 0 1 0
4 0 0 1
5 0.5 0 {midpoint_z}
6 0.5 0.5 0
7 0 0.5 0
8 0 0 0.5
9 0 0.5 0.5
10 0.5 0 0.5
$EndNodes
$Elements
1
1 11 2 3 22 1 2 3 4 5 6 7 8 9 10
$EndElements
"""
        path = tmp_path / f"mesh_{midpoint_z}.msh"
        path.write_text(msh, encoding="utf-8")
        return path

    flat = read_msh2(write_mesh(0.0))
    assert len(boundary_triangles(flat, subdivide=True)) == 16

    curved_path = write_mesh(-0.25)
    curved = read_msh2(curved_path)
    assert len(boundary_triangles(curved, subdivide=True)) == 16

    npz_path = tmp_path / "fields.npz"
    np.savez(
        npz_path,
        node_id=np.array([1, 2, 3, 4]),
        von_mises_mpa=np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float32),
    )
    payload = field_payload(curved_path, npz_path, "von_mises_mpa")
    assert len(payload["vertices"]) == 10
    assert len(payload["faces"]) == 16
    assert len(payload["intensity"]) == len(payload["vertices"])
    assert payload["intensity_mode"] == "vertex"

    values = dict(zip(map(tuple, payload["vertices"]), payload["intensity"]))
    assert values[(0.5, 0.0, -0.25)] == pytest.approx(1.5)  # mid-edge 1-2
    assert values[(0.0, 0.5, 0.0)] == pytest.approx(2.0)  # mid-edge 1-3
    assert values[(0.0, 0.0, 0.5)] == pytest.approx(2.5)  # mid-edge 1-4
