from pathlib import Path

import pytest

from surrosim.plate import Plate
from surrosim.simulation.calculix import build_calculix_deck
from surrosim.simulation.msh2 import read_msh2
from surrosim.simulation.runner import CalculixRunner


MSH = """$MeshFormat
2.2 0 8
$EndMeshFormat
$PhysicalNames
3
2 1 "FIXED_FACE"
2 2 "LOAD_FACE"
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
3
1 2 2 1 11 1 3 4
2 2 2 2 12 2 3 4
3 4 2 3 21 1 2 3 4
$EndElements
"""


def _mesh(tmp_path: Path) -> Path:
    path = tmp_path / "mesh.msh"
    path.write_text(MSH, encoding="utf-8")
    return path


def test_read_msh2_preserves_physical_groups(tmp_path):
    mesh = read_msh2(_mesh(tmp_path))
    assert len(mesh.nodes) == 4
    assert mesh.physical_tag(2, "FIXED_FACE") == 1
    assert len(mesh.elements_in_group(3, "SOLID")) == 1
    assert len(mesh.elements_in_group(2, "LOAD_FACE")) == 1


def test_deck_has_exact_total_force(tmp_path):
    plate = Plate(
        length_mm=10, width_mm=4, thickness_mm=2, hole_diameter_mm=0,
        hole_x_mm=5, force_n=500, mesh_size_mm=1,
    )
    summary = build_calculix_deck(_mesh(tmp_path), plate)
    text = summary.path.read_text(encoding="utf-8")
    assert summary.total_applied_force_n == pytest.approx(-500)
    assert summary.nodes == 4
    assert summary.volume_elements == 1
    assert "*ELEMENT, TYPE=C3D4, ELSET=SOLID" in text
    assert "*NSET, NSET=FIXED_FACE" in text
    assert "*NODE FILE\nU" in text
    assert "*EL FILE\nS" in text

    cload = text.split("*CLOAD\n", 1)[1].split("*NODE FILE", 1)[0]
    values = [float(line.split(",")[2]) for line in cload.strip().splitlines()]
    assert sum(values) == pytest.approx(-500)
    assert len(values) == 3


def test_runner_reports_missing_solver(tmp_path):
    deck = tmp_path / "model.inp"
    deck.write_text("*HEADING\n", encoding="utf-8")
    result = CalculixRunner("definitely-not-a-real-ccx-binary").run(deck)
    assert result.status == "SOLVER_NOT_FOUND"
    assert not result.success
    assert result.return_code is None


def test_runner_rejects_wrong_suffix(tmp_path):
    deck = tmp_path / "model.txt"
    deck.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match=".inp"):
        CalculixRunner().run(deck)


def test_msh_parser_rejects_msh4(tmp_path):
    bad = tmp_path / "bad.msh"
    bad.write_text(MSH.replace("2.2 0 8", "4.1 0 8"), encoding="utf-8")
    with pytest.raises(ValueError, match="MSH 2.2"):
        read_msh2(bad)
