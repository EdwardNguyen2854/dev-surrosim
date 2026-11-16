"""End-to-end tests that need real Gmsh and CalculiX binaries.

The tests are skipped automatically when either dependency is missing, so
``pytest -q`` stays fast on machines without a solver. CI installs both so
the deck -> solver -> FRD path is continuously verified.
"""

from pathlib import Path
import os
import shutil

import pytest

from surrosim.plate import Plate

pytest.importorskip("gmsh", reason="Gmsh is required for integration tests")

pytestmark = pytest.mark.solver


def _ccx() -> str | None:
    candidates = [
        os.environ.get("SURROSIM_CCX"),
        shutil.which("ccx"),
        str(Path(__file__).resolve().parents[1] / "tools" / "calculix" / "ccx.exe"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


@pytest.fixture(scope="module")
def ccx_executable() -> str:
    executable = _ccx()
    if executable is None:
        pytest.skip("CalculiX executable not found")
    return executable


def test_quadratic_case_end_to_end(tmp_path, ccx_executable):
    from surrosim.simulation.pipeline import simulate_case

    plate = Plate(
        length_mm=40, width_mm=20, thickness_mm=4, hole_diameter_mm=4,
        hole_x_mm=20, force_n=200, mesh_size_mm=2, youngs_modulus_mpa=210_000,
    )
    summary = simulate_case(
        plate, tmp_path / "case", ccx_executable, timeout_seconds=300,
        element_order=2,
    )
    assert summary["status"] == "SUCCESS"
    assert summary["deck"]["element_type"] == "C3D10"
    assert summary["deck"]["total_applied_force_n"] == pytest.approx(-200)
    results = summary["results"]
    assert results["max_displacement_mm"] > 0
    assert results["global_max_von_mises_mpa"] > 0
    assert results["max_von_mises_roi_mpa"] is not None
    assert (tmp_path / "case" / "fields.csv").exists()
