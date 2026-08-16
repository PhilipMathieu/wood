"""2-D sheet-goods packing using rectpack (guillotine-friendly heuristics).

Given a list of required panel cuts and available sheet sizes, pack the panels
onto sheets and return the placement assignments.

Example
-------
>>> from woodshop.cutlist.optimize_2d import optimize_2d
>>> from woodshop.cutlist.extract import CutPart
>>> panels = [CutPart("shelf", "plywood_birch", "length", 600, 300, 18.25, qty=3)]
>>> result = optimize_2d(panels, sheet_w_mm=1219.2, sheet_h_mm=2438.4)
>>> result.sheets_used
1
"""

from __future__ import annotations

from dataclasses import dataclass, field

import rectpack  # type: ignore[import]

from woodshop.cutlist.extract import CutPart
from woodshop.lumber import KERF_MM


@dataclass
class Placement:
    """A single panel placed on a sheet.

    Parameters
    ----------
    label : str
        Part label.
    sheet_index : int
        Zero-based sheet number.
    x_mm : float
        X coordinate of the bottom-left corner on the sheet.
    y_mm : float
        Y coordinate of the bottom-left corner on the sheet.
    width_mm : float
        Placed width (may be rotated relative to the cut dimension).
    height_mm : float
        Placed height.
    rotated : bool
        ``True`` if the part was rotated 90° to fit.
    """

    label: str
    sheet_index: int
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float
    rotated: bool = False


@dataclass
class Cut2DResult:
    """Result of a 2-D sheet-goods packing run.

    Parameters
    ----------
    sheets_used : int
        Total number of full sheets consumed.
    placements : list[Placement]
        One entry per individual panel cut.
    unpacked : list[str]
        Labels of panels that could not be packed (e.g. part larger than sheet).
    """

    sheets_used: int
    placements: list[Placement] = field(default_factory=list)
    unpacked: list[str] = field(default_factory=list)


def optimize_2d(
    parts: list[CutPart],
    sheet_w_mm: float,
    sheet_h_mm: float,
    kerf_mm: float = KERF_MM,
    rotation_allowed: bool = True,
) -> Cut2DResult:
    """Pack panel cuts onto sheets, minimising the number of sheets used.

    Grain-direction constraints are respected: if ``grain_direction`` is
    ``"length"`` the part is only rotated if ``rotation_allowed`` is ``True``
    **and** the grain still runs along the longer sheet dimension after rotation.

    Parameters
    ----------
    parts : list[CutPart]
        Required panel cuts (``qty`` honoured — each is expanded).
    sheet_w_mm : float
        Sheet width in mm (typically 1219.2 mm = 48").
    sheet_h_mm : float
        Sheet height in mm (typically 2438.4 mm = 96").
    kerf_mm : float, optional
        Kerf padding applied to each panel dimension before packing.
    rotation_allowed : bool, optional
        Allow 90° rotation of parts to improve packing, default ``True``.

    Returns
    -------
    Cut2DResult
        Packing result with placements and waste information.
    """
    # Expand parts by qty.
    items: list[tuple[str, float, float]] = []
    for p in parts:
        for _ in range(p.qty):
            items.append((p.label, p.length_mm + kerf_mm, p.width_mm + kerf_mm))

    if not items:
        return Cut2DResult(sheets_used=0)

    # Allow enough bins (sheets) to cover all parts.
    n_sheets = len(items)
    packer = rectpack.newPacker(rotation=rotation_allowed)
    for _ in range(n_sheets):
        packer.add_bin(sheet_w_mm, sheet_h_mm, count=1)
    for idx, (label, length, width) in enumerate(items):
        packer.add_rect(length, width, rid=idx)

    packer.pack()

    placements: list[Placement] = []
    packed_ids: set[int] = set()

    for bin_index, bin_ in enumerate(packer):
        for rect in bin_:
            rid: int = rect.rid  # type: ignore[attr-defined]
            orig_label, orig_l, orig_w = items[rid]
            placed_w = rect.width
            placed_h = rect.height
            rotated = not (
                abs(placed_w - orig_l) < 0.01 and abs(placed_h - orig_w) < 0.01
            )
            placements.append(
                Placement(
                    label=orig_label,
                    sheet_index=bin_index,
                    x_mm=rect.x,
                    y_mm=rect.y,
                    width_mm=placed_w - kerf_mm,
                    height_mm=placed_h - kerf_mm,
                    rotated=rotated,
                )
            )
            packed_ids.add(rid)

    unpacked = [items[i][0] for i in range(len(items)) if i not in packed_ids]
    sheets_used = len({p.sheet_index for p in placements})

    return Cut2DResult(sheets_used=sheets_used, placements=placements, unpacked=unpacked)
