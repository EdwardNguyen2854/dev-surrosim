import math

import pytest

from surrosim.plate import Plate
from surrosim.sampling import sample_designs, export_designs
from surrosim.cli import main


def test_nominal_beam_theory_reference():
    p = Plate(length_mm=100, width_mm=20, thickness_mm=5,
              hole_diameter_mm=5, hole_x_mm=50, force_n=100,
              youngs_modulus_mpa=200_000, mesh_size_mm=1)
    result = p.nominal_baseline()
    expected_stress = 6 * 100 * 100 / (20 * 5**2)
    expected_displacement = 4 * 100 * 100**3 / (200_000 * 20 * 5**3)
    assert result["nominal_root_bending_stress_mpa"] == pytest.approx(expected_stress)
    assert result["nominal_tip_displacement_mm"] == pytest.approx(expected_displacement)


@pytest.mark.parametrize("changes", [
    {"hole_diameter_mm": 41}, {"hole_diameter_mm": -1}, {"hole_x_mm": 2},
    {"hole_x_mm": 119}, {"force_n": math.inf},
    {"mesh_size_mm": -1}, {"poisson_ratio": 0.5},
])
def test_invalid_design_rejected(changes):
    p = Plate(**{**Plate().as_dict(), **changes})
    with pytest.raises(ValueError):
        p.validate()


def test_lhs_is_reproducible_and_feasible():
    first, second = sample_designs(50, 42), sample_designs(50, 42)
    assert first == second
    assert sample_designs(50, 43) != first
    assert len(first) == 50
    assert len({p.length_mm for p in first}) == 50
    assert all(p.validate() is None for p in first)


def test_csv_contains_inputs_only(tmp_path):
    destination = tmp_path / "designs.csv"
    assert export_designs(destination, count=3, seed=1) == 3
    lines = destination.read_text().splitlines()
    assert len(lines) == 4
    assert "force_n" in lines[0]
    assert "stress" not in lines[0].lower()


def test_baseline_cli(capsys):
    assert main(["baseline"]) == 0
    output = capsys.readouterr().out
    assert "nominal_beam_baseline_not_fea" in output


def test_missing_gmsh_gives_install_hint(monkeypatch, tmp_path):
    from surrosim.geometry import generate_plate
    import builtins
    actual = builtins.__import__
    def without_gmsh(name, *args, **kwargs):
        if name == "gmsh":
            raise ImportError("simulated absence")
        return actual(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", without_gmsh)
    with pytest.raises(RuntimeError, match="pip install"):
        generate_plate(Plate(), tmp_path / "out")


def test_no_hole_is_valid_for_beam_validation():
    p = Plate(hole_diameter_mm=0)
    p.validate()
    assert p.nominal_baseline()["nominal_tip_displacement_mm"] > 0
