"""Minimal, strict parser for the ASCII Gmsh MSH 2.2 files SurroSim writes.

The parser intentionally supports only the element families needed by the
v0.2 structural pipeline: linear (MSH type 2, 4) and quadratic (MSH type 9,
11) triangles and tetrahedra. Keeping this boundary explicit prevents an
unsupported mesh from silently entering the FEA/ML dataset.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class MeshElement:
    element_id: int
    element_type: int
    physical_tag: int | None
    nodes: tuple[int, ...]


@dataclass(frozen=True)
class GmshMesh:
    nodes: dict[int, tuple[float, float, float]]
    physical_names: dict[tuple[int, int], str]
    elements: tuple[MeshElement, ...]

    def physical_tag(self, dimension: int, name: str) -> int:
        for (dim, tag), physical_name in self.physical_names.items():
            if dim == dimension and physical_name == name:
                return tag
        raise ValueError(f"Physical group {name!r} (dim={dimension}) not found")

    def elements_in_group(self, dimension: int, name: str) -> tuple[MeshElement, ...]:
        tag = self.physical_tag(dimension, name)
        supported = {2: (2, 9), 3: (4, 11)}.get(dimension)
        if supported is None:
            raise ValueError(f"Unsupported physical-group dimension: {dimension}")
        return tuple(
            element
            for element in self.elements
            if element.physical_tag == tag and element.element_type in supported
        )


def _section(lines: list[str], name: str) -> list[str]:
    start_marker = "$" + name
    end_marker = "$End" + name
    try:
        start = lines.index(start_marker) + 1
        end = lines.index(end_marker, start)
    except ValueError as exc:
        raise ValueError(f"Missing Gmsh section {start_marker}") from exc
    return lines[start:end]


def read_msh2(path: str | Path) -> GmshMesh:
    """Read an ASCII MSH 2.2 mesh and preserve physical group membership."""
    source = Path(path)
    lines = [line.strip() for line in source.read_text(encoding="utf-8").splitlines()]

    mesh_format = _section(lines, "MeshFormat")
    if not mesh_format:
        raise ValueError("Empty $MeshFormat section")
    version, file_type, _ = mesh_format[0].split()
    if version != "2.2" or file_type != "0":
        raise ValueError("SurroSim v0.2 requires ASCII Gmsh MSH 2.2")

    physical_names: dict[tuple[int, int], str] = {}
    physical = _section(lines, "PhysicalNames")
    count = int(physical[0])
    for raw in physical[1 : 1 + count]:
        dim_text, tag_text, quoted_name = raw.split(maxsplit=2)
        name = quoted_name.strip().strip('"')
        physical_names[(int(dim_text), int(tag_text))] = name

    node_lines = _section(lines, "Nodes")
    node_count = int(node_lines[0])
    nodes: dict[int, tuple[float, float, float]] = {}
    for raw in node_lines[1 : 1 + node_count]:
        node_id, x, y, z = raw.split()
        nodes[int(node_id)] = (float(x), float(y), float(z))
    if len(nodes) != node_count:
        raise ValueError("Node count does not match $Nodes section")

    element_lines = _section(lines, "Elements")
    element_count = int(element_lines[0])
    elements: list[MeshElement] = []
    node_counts = {2: 3, 4: 4, 9: 6, 11: 10}
    for raw in element_lines[1 : 1 + element_count]:
        fields = raw.split()
        element_id = int(fields[0])
        element_type = int(fields[1])
        tag_count = int(fields[2])
        tags = [int(value) for value in fields[3 : 3 + tag_count]]
        node_values = tuple(int(value) for value in fields[3 + tag_count :])
        if element_type in node_counts and len(node_values) != node_counts[element_type]:
            raise ValueError(
                f"Element {element_id} type {element_type} has {len(node_values)} nodes"
            )
        elements.append(
            MeshElement(
                element_id=element_id,
                element_type=element_type,
                physical_tag=tags[0] if tags else None,
                nodes=node_values,
            )
        )
    if len(elements) != element_count:
        raise ValueError("Element count does not match $Elements section")

    return GmshMesh(nodes=nodes, physical_names=physical_names, elements=tuple(elements))


def unique_nodes(elements: Iterable[MeshElement]) -> tuple[int, ...]:
    return tuple(sorted({node for element in elements for node in element.nodes}))
