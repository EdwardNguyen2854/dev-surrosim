"""Generate and tag a 3-D cantilever plate and through-hole using Gmsh OCC."""

from pathlib import Path
import json

from .plate import Plate


def generate_plate(plate: Plate, output_dir: str | Path) -> dict:
    """Export STEP geometry, Gmsh MSH v2 mesh, and descriptive JSON metadata.

    Coordinate frame: fixed end X=0, loaded end X=L; width along Y;
    thickness along Z. The circular hole runs through Z at (hole_x, 0).
    Boundary physical groups FIXED_FACE and LOAD_FACE are surface groups;
    SOLID is the volume group. This function does NOT perform FEA.
    """
    plate.validate()
    try:
        import gmsh
    except ImportError as exc:
        raise RuntimeError(
            "Gmsh is required for mesh generation: pip install -e '.[mesh]'"
        ) from exc

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    initialized = False
    try:
        gmsh.initialize()
        initialized = True
        gmsh.option.setNumber("General.Terminal", 1)
        gmsh.model.add("surrosim_cantilever_plate")
        occ = gmsh.model.occ
        l, w, t = plate.length_mm, plate.width_mm, plate.thickness_mm
        box = occ.addBox(0, -w / 2, -t / 2, l, w, t)
        # Extend tool beyond both planar faces to avoid coincident cutter caps.
        cutter = occ.addCylinder(
            plate.hole_x_mm, 0, -t / 2 - 1.0,
            0, 0, t + 2.0, plate.hole_diameter_mm / 2,
        )
        solids, _ = occ.cut([(3, box)], [(3, cutter)],
                            removeObject=True, removeTool=True)
        occ.synchronize()
        volume_tags = [tag for dim, tag in solids if dim == 3]
        if len(volume_tags) != 1:
            raise RuntimeError(f"Expected one cut solid, found {volume_tags}")

        fixed_faces, load_faces = [], []
        tol = max(l, w, t) * 1e-7
        boundary = gmsh.model.getBoundary(
            [(3, volume_tags[0])], oriented=False, recursive=False
        )
        for dim, tag in boundary:
            if dim != 2:
                continue
            xmin, ymin, zmin, xmax, ymax, zmax = gmsh.model.getBoundingBox(2, tag)
            if abs(xmin) <= tol and abs(xmax) <= tol:
                fixed_faces.append(tag)
            elif abs(xmin - l) <= tol and abs(xmax - l) <= tol:
                load_faces.append(tag)
        if len(fixed_faces) != 1 or len(load_faces) != 1:
            raise RuntimeError(
                f"Cannot identify end faces: fixed={fixed_faces}, load={load_faces}"
            )

        for dim, tags, name in (
            (3, volume_tags, "SOLID"),
            (2, fixed_faces, "FIXED_FACE"),
            (2, load_faces, "LOAD_FACE"),
        ):
            group = gmsh.model.addPhysicalGroup(dim, tags)
            gmsh.model.setPhysicalName(dim, group, name)

        gmsh.write(str(output / "geometry.step"))
        gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)
        gmsh.model.mesh.setSize(gmsh.model.getEntities(0), plate.mesh_size_mm)
        gmsh.model.mesh.generate(3)
        gmsh.write(str(output / "mesh.msh"))
        nodes, _, _ = gmsh.model.mesh.getNodes()
        metadata = {
            "geometry": plate.as_dict(),
            "units": {"length": "mm", "force": "N", "stress": "MPa"},
            "coordinate_frame": "fixed X=0; loaded X=L; transverse load -Z; hole axis Z",
            "physical_groups": ["SOLID", "FIXED_FACE", "LOAD_FACE"],
            "mesh_nodes": len(nodes),
            "nominal_beam_baseline_not_fea": plate.nominal_baseline(),
            "fea_status": "not_run",
        }
        (output / "metadata.json").write_text(
            json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
        )
        return metadata
    finally:
        if initialized:
            gmsh.finalize()
