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


def extract(assembly: Any) -> list[CutPart]:
    """Walk *assembly* and return a flat list of :class:`CutPart` objects.

    The function recognises parts that carry a ``material`` attribute (set by
    :class:`woodshop.parts.Board` and :class:`woodshop.parts.Panel`).

    Parameters
    ----------
    assembly : build123d.Compound | build123d.BuildPart | any part object
        The root of the part/assembly tree to traverse.

    Returns
    -------
    list[CutPart]
        One entry per part leaf in the assembly tree.
    """
    parts: list[CutPart] = []
    _walk(assembly, parts)
    return parts


def _walk(node: Any, acc: list[CutPart]) -> None:
    """Recursively walk *node* collecting parts into *acc*."""
    # If the node itself has material metadata it is a leaf part.
    if hasattr(node, "material") and hasattr(node, "stock_length_mm"):
        bb = node.bounding_box()
        acc.append(
            CutPart(
                label=getattr(node, "label", "unnamed"),
                material=node.material,
                grain_direction=getattr(node, "grain_direction", "none"),
                length_mm=node.stock_length_mm,
                width_mm=bb.size.Y,
                thickness_mm=bb.size.Z,
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
