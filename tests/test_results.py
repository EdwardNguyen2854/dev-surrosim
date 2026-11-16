from pathlib import Path

import pytest

from surrosim.plate import Plate
from surrosim.simulation.msh2 import GmshMesh
from surrosim.simulation.results import FrdFields, parse_frd, summarize_fields, von_mises


FRD = """    1Cexample
  100CL  102 1.00000E+00
 -4  DISP        4    1
 -5  D1          1    2    1    0
 -5  D2          1    2    2    0
 -5  D3          1    2    3    0
 -5  ALL         1    2    0    0
 -1    1 0.00000E+00 0.00000E+00 0.00000E+00
 -1    2 3.00000E+00 4.00000E+00 0.00000E+00
 -3
  100CL  102 1.00000E+00
 -4  STRESS      6    1
 -5  SXX         1    4    1    1
 -5  SYY         1    4    2    2
 -5  SZZ         1    4    3    3
 -5  SXY         1    4    1    2
 -5  SYZ         1    4    2    3
 -5  SZX         1    4    3    1
 -1    1 1.00000E+02 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00
 -1    2 2.00000E+02 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00 0.00000E+00
 -3
 9999
"""


def test_parse_frd_and_von_mises(tmp_path):
    path = tmp_path / "model.frd"
    path.write_text(FRD, encoding="utf-8")
    fields = parse_frd(path)
    assert fields.displacement[2] == pytest.approx((3, 4, 0))
    assert fields.stress[1][0] == pytest.approx(100)
    assert von_mises(fields.stress[1]) == pytest.approx(100)


def test_summary_reports_maxima_and_hole_roi():
    plate = Plate(length_mm=100, width_mm=40, thickness_mm=5,
                  hole_diameter_mm=10, hole_x_mm=50, force_n=100, mesh_size_mm=1)
    mesh = GmshMesh(
        nodes={1: (0, 0, 0), 2: (50, 5, 0), 3: (100, 0, 0)},
        physical_names={}, elements=(),
    )
    fields = FrdFields(
        displacement={1: (0, 0, 0), 2: (0, 0, 1), 3: (0, 0, 3)},
        stress={
            1: (500, 0, 0, 0, 0, 0),
            2: (200, 0, 0, 0, 0, 0),
            3: (100, 0, 0, 0, 0, 0),
        },
    )
    result = summarize_fields(fields, mesh, plate)
    assert result["max_displacement_mm"] == pytest.approx(3)
    assert result["global_max_von_mises_mpa"] == pytest.approx(500)
    assert result["max_von_mises_roi_mpa"] == pytest.approx(200)
    assert result["max_von_mises_roi_node"] == 2


def test_von_mises_pure_shear():
    assert von_mises((0, 0, 0, 10, 0, 0)) == pytest.approx(3**0.5 * 10)
