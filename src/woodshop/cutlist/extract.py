"""Extract part dimensions and metadata from a build123d assembly Compound.

Walk the build123d ``Compound`` tree and collect every ``Board`` / ``Panel``
(identified by the presence of a ``material`` attribute) into a list of
:class:`CutPart` dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from woodshop.lumber import mm_to_fractional_inch


@dataclass
class CutPart:
    """Metadata for a single part extracted from an assembly.

    Parameters
    ----------
    label : str
        Human-readable name.
    material : str
        Species or sheet-goods material.
    grain_direction : str
        ``"length"``, ``"width"``, or ``"none"``.
    length_mm : float
        Stock length (pre-subtraction, along the grain).
    width_mm : float
        Actual face width in mm.
    thickness_mm : float
        Actual thickness in mm.
    qty : int
        Number of identical parts.
    """

    label: str
    material: str
    grain_direction: str
    length_mm: float
    width_mm: float
    thickness_mm: float
    qty: int = 1
    _extra: dict[str, Any] = field(default_factory=dict, repr=False)

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def length_in(self) -> str:
        """Cut length as a fractional-inch string."""
        return mm_to_fractional_inch(self.length_mm)

    @property
    def width_in(self) -> str:
        """Face width as a fractional-inch string."""
        return mm_to_fractional_inch(self.width_mm)

    @property
    def thickness_in(self) -> str:
        """Thickness as a fractional-inch string."""
        return mm_to_fractional_inch(self.thickness_mm)


def extract(assembly: Any, consolidate_parts: bool = True) -> list[CutPart]:
    """Walk *assembly* and return a flat list of :class:`CutPart` objects.

    The function recognises parts that carry a ``material`` attribute (set by
    :class:`woodshop.parts.Board` and :class:`woodshop.parts.Panel`).

    Parameters
    ----------
    assembly : build123d.Compound | build123d.BuildPart | any part object
        The root of the part/assembly tree to traverse.
    consolidate_parts : bool, optional
        Merge identical parts into a single row with a summed ``qty``,
        default ``True``.  See :func:`consolidate`.

    Returns
    -------
    list[CutPart]
        One entry per distinct part (or per leaf, if *consolidate_parts* is
        ``False``).
    """
    parts: list[CutPart] = []
    _walk(assembly, parts)
    return consolidate(parts) if consolidate_parts else parts


def consolidate(parts: list[CutPart]) -> list[CutPart]:
    """Merge parts that are identical in every respect but quantity.

    Parts are grouped on label, material, grain direction, and all three
    dimensions rounded to 0.01 mm.  Input order of the first occurrence is
    preserved.

    Parameters
    ----------
    parts : list[CutPart]
        Parts to merge.

    Returns
    -------
    list[CutPart]
        Merged parts, with ``qty`` summed within each group.
    """
    merged: dict[tuple[Any, ...], CutPart] = {}
    for p in parts:
        key = (
            p.label,
            p.material,
            p.grain_direction,
            round(p.length_mm, 2),
            round(p.width_mm, 2),
            round(p.thickness_mm, 2),
        )
        if key in merged:
            merged[key].qty += p.qty
        else:
            merged[key] = CutPart(
                label=p.label,
                material=p.material,
                grain_direction=p.grain_direction,
                length_mm=p.length_mm,
                width_mm=p.width_mm,
                thickness_mm=p.thickness_mm,
                qty=p.qty,
                _extra=dict(p._extra),
            )
    return list(merged.values())


def _walk(node: Any, acc: list[CutPart]) -> None:
    """Recursively walk *node* collecting parts into *acc*."""
    # If the node itself has material metadata it is a leaf part.
    if hasattr(node, "material") and hasattr(node, "stock_length_mm"):
        # Prefer the cut dimensions recorded on the part.  Measuring them off
        # the bounding box only works while the part still sits in its local
        # frame — once it is rotated into the assembly, Y and Z no longer mean
        # width and thickness.  Fall back to the bounding box for plain
        # build123d solids that were tagged by hand.
        bb = node.bounding_box()
        width_mm = getattr(node, "width_mm", None)
        thickness_mm = getattr(node, "thickness_mm", None)
        extra: dict[str, Any] = {}
        if getattr(node, "notes", ""):
            extra["notes"] = node.notes
        acc.append(
            CutPart(
                label=getattr(node, "label", "unnamed"),
                material=node.material,
                grain_direction=getattr(node, "grain_direction", "none"),
                length_mm=node.stock_length_mm,
                width_mm=bb.size.Y if width_mm is None else width_mm,
                thickness_mm=bb.size.Z if thickness_mm is None else thickness_mm,
                qty=getattr(node, "qty", 1),
                _extra=extra,
            )
        )
        return

    # Try iterating children (Compound has .children, BuildPart has .part).
    children: list[Any] = []
    if hasattr(node, "children"):
        children = list(node.children)
    elif hasattr(node, "part"):
        children = [node.part]

    for child in children:
        _walk(child, acc)
