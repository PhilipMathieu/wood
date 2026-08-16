"""2-D sheet-goods nesting with grain locking and guillotine-safe layouts.

Two constraints separate real sheet-goods nesting from generic rectangle
packing:

**Grain.** A part whose ``grain_direction`` is ``"length"`` must have its
length running along the sheet's face grain.  On a 4x8 hardwood-plywood sheet
the face veneer runs along the 96" dimension, so such a part may not be turned
90°.  Parts with ``grain_direction="none"`` — most Baltic birch utility parts —
may be rotated freely.

**Guillotine cuts.** A table saw and a track saw can only make cuts that run
edge to edge.  A layout that requires lifting a rectangle out of the middle of
a sheet cannot be cut.  The default ``"shelf"`` strategy produces layouts that
are always cuttable: crosscut the sheet into full-width strips, then rip each
strip into parts.

Parts are also grouped by material and thickness, since 3/4" cherry ply and
1/2" birch ply obviously do not share a sheet.

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
from typing import TYPE_CHECKING

from woodshop.cutlist.extract import CutPart
from woodshop.lumber import KERF_MM

if TYPE_CHECKING:
    from woodshop.inventory import Inventory

__all__ = ["Placement", "Cut2DResult", "optimize_2d", "pack_by_material"]


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
        Placed extent along X, kerf excluded.
    height_mm : float
        Placed extent along Y, kerf excluded.
    rotated : bool
        ``True`` if the part was rotated 90° relative to its cut dimensions.
    material : str
        Material of the part, so mixed-material results stay readable.
    grain_direction : str
        The part's grain direction, carried through so a diagram can show
        which way the grain runs and why a part is oriented as it is.
    """

    label: str
    sheet_index: int
    x_mm: float
    y_mm: float
    width_mm: float
    height_mm: float
    rotated: bool = False
    material: str = ""
    grain_direction: str = "none"


@dataclass
class Cut2DResult:
    """Result of a 2-D sheet-goods packing run.

    Parameters
    ----------
    sheets_used : int
        Total number of sheets consumed.
    placements : list[Placement]
        One entry per individual panel cut.
    unpacked : list[str]
        Labels of panels that could not be packed — normally because the part
        is larger than a sheet in every permitted orientation.
    sheet_w_mm : float
        Sheet width used for this run.
    sheet_h_mm : float
        Sheet height used for this run.
    """

    sheets_used: int
    placements: list[Placement] = field(default_factory=list)
    unpacked: list[str] = field(default_factory=list)
    sheet_w_mm: float = 0.0
    sheet_h_mm: float = 0.0

    @property
    def used_area_mm2(self) -> float:
        """Total area of placed parts, in mm²."""
        return sum(p.width_mm * p.height_mm for p in self.placements)

    @property
    def yield_fraction(self) -> float:
        """Fraction of purchased sheet area that ends up in parts (0-1)."""
        total = self.sheets_used * self.sheet_w_mm * self.sheet_h_mm
        return 0.0 if total == 0 else self.used_area_mm2 / total


def _orientations(
    part: CutPart,
    length: float,
    width: float,
    rotation_allowed: bool,
    respect_grain: bool,
    sheet_grain: str,
) -> list[tuple[float, float, bool]]:
    """Return the ``(dx, dy, rotated)`` placements permitted for a part.

    The sheet's face grain is taken to run along +Y (the sheet height), which
    is the usual convention for 4x8 hardwood plywood and the only sensible
    reading for a solid board.  ``rotated`` is relative to the natural
    placement of length along +X.
    """
    unrotated = (length, width, False)
    rotated = (width, length, True)

    if not rotation_allowed:
        return [unrotated]
    if respect_grain and sheet_grain != "none" and part.grain_direction != "none":
        # Whichever part dimension carries the grain must lie along +Y.
        return [rotated] if part.grain_direction == "length" else [unrotated]
    return [unrotated, rotated]


def optimize_2d(
    parts: list[CutPart],
    sheet_w_mm: float,
    sheet_h_mm: float,
    kerf_mm: float = KERF_MM,
    rotation_allowed: bool = True,
    respect_grain: bool = True,
    sheet_grain: str = "length",
    strategy: str = "shelf",
) -> Cut2DResult:
    """Pack panel cuts onto sheets, minimising the number of sheets used.

    Parameters
    ----------
    parts : list[CutPart]
        Required panel cuts (``qty`` honoured — each is expanded).
    sheet_w_mm : float
        Sheet width in mm (1219.2 mm = 48" for a 4x8; 1524 mm = 60" for
        Baltic birch).
    sheet_h_mm : float
        Sheet height in mm, along the face grain.
    kerf_mm : float, optional
        Kerf allowance added to each part dimension before packing.
    rotation_allowed : bool, optional
        Allow 90° rotation where grain permits, default ``True``.
    respect_grain : bool, optional
        Honour each part's ``grain_direction``, default ``True``.  Set
        ``False`` to see the best-case nesting if grain were ignored.
    sheet_grain : str, optional
        ``"length"`` (default) if the sheet's face grain runs along
        ``sheet_h_mm``, or ``"none"`` for materials such as Baltic birch where
        face-grain direction does not constrain layout.
    strategy : str, optional
        ``"shelf"`` (default) produces guillotine-cuttable layouts.
        ``"maxrects"`` uses :mod:`rectpack` for a tighter but generally
        *not* saw-cuttable layout — useful as a lower bound on sheet count.

    Returns
    -------
    Cut2DResult
        Packing result with placements and yield information.

    Raises
    ------
    ValueError
        If ``strategy`` is unknown or the sheet dimensions are non-positive.

    Notes
    -----
    ``"maxrects"`` ignores ``respect_grain``; :mod:`rectpack` has no per-part
    rotation control.  A warning is recorded in :attr:`Cut2DResult.unpacked`
    only for parts that genuinely do not fit.
    """
    if strategy not in ("shelf", "maxrects"):
        raise ValueError(f"strategy must be 'shelf' or 'maxrects', got {strategy!r}")
    if sheet_w_mm <= 0 or sheet_h_mm <= 0:
        raise ValueError("sheet dimensions must be positive")
    if not parts:
        return Cut2DResult(
            sheets_used=0, sheet_w_mm=sheet_w_mm, sheet_h_mm=sheet_h_mm
        )

    # Expand by qty, adding a kerf allowance to each dimension.
    items: list[tuple[CutPart, float, float]] = []
    for p in parts:
        for _ in range(p.qty):
            items.append((p, p.length_mm + kerf_mm, p.width_mm + kerf_mm))

    if strategy == "maxrects":
        return _pack_maxrects(items, sheet_w_mm, sheet_h_mm, kerf_mm, rotation_allowed)
    return _pack_shelf(
        items, sheet_w_mm, sheet_h_mm, kerf_mm, rotation_allowed,
        respect_grain, sheet_grain,
    )


def _pack_shelf(
    items: list[tuple[CutPart, float, float]],
    sheet_w_mm: float,
    sheet_h_mm: float,
    kerf_mm: float,
    rotation_allowed: bool,
    respect_grain: bool,
    sheet_grain: str,
) -> Cut2DResult:
    """Next-fit-decreasing shelf packing — every layout is guillotine-cuttable.

    Sheets are filled with horizontal shelves stacked along +Y.  Cutting a
    shelf layout means crosscutting the sheet into full-width strips and then
    ripping each strip, which is exactly what a table saw can do.
    """
    # Each shelf is [y0, height, x_cursor].
    sheets: list[list[list[float]]] = []
    placements: list[Placement] = []
    unpacked: list[str] = []

    def options(part: CutPart, length: float, width: float) -> list[tuple[float, float, bool]]:
        return _orientations(
            part, length, width, rotation_allowed, respect_grain, sheet_grain
        )

    # Tallest-first keeps shelves dense; sort on the smallest achievable
    # height so a rotatable part is not judged by its worst orientation.
    def sort_height(item: tuple[CutPart, float, float]) -> float:
        part, length, width = item
        return min(dy for _, dy, _ in options(part, length, width))

    for part, length, width in sorted(items, key=sort_height, reverse=True):
        choices = [
            (dx, dy, rot)
            for dx, dy, rot in options(part, length, width)
            if dx <= sheet_w_mm and dy <= sheet_h_mm
        ]
        if not choices:
            unpacked.append(part.label)
            continue

        placed = False
        # Try existing shelves on existing sheets first.
        for sheet_index, shelves in enumerate(sheets):
            for shelf in shelves:
                y0, shelf_h, cursor = shelf
                for dx, dy, rot in choices:
                    if dy <= shelf_h and cursor + dx <= sheet_w_mm:
                        placements.append(
                            Placement(
                                label=part.label,
                                sheet_index=sheet_index,
                                x_mm=cursor,
                                y_mm=y0,
                                width_mm=dx - kerf_mm,
                                height_mm=dy - kerf_mm,
                                rotated=rot,
                                material=part.material,
                                grain_direction=part.grain_direction,
                            )
                        )
                        shelf[2] = cursor + dx
                        placed = True
                        break
                if placed:
                    break
            if placed:
                break
        if placed:
            continue

        # Open a new shelf on an existing sheet, else start a new sheet.
        for sheet_index, shelves in enumerate(sheets):
            top = shelves[-1][0] + shelves[-1][1] if shelves else 0.0
            for dx, dy, rot in choices:
                if top + dy <= sheet_h_mm:
                    shelves.append([top, dy, dx])
                    placements.append(
                        Placement(
                            label=part.label,
                            sheet_index=sheet_index,
                            x_mm=0.0,
                            y_mm=top,
                            width_mm=dx - kerf_mm,
                            height_mm=dy - kerf_mm,
                            rotated=rot,
                            material=part.material,
                            grain_direction=part.grain_direction,
                        )
                    )
                    placed = True
                    break
            if placed:
                break
        if placed:
            continue

        dx, dy, rot = choices[0]
        sheets.append([[0.0, dy, dx]])
        placements.append(
            Placement(
                label=part.label,
                sheet_index=len(sheets) - 1,
                x_mm=0.0,
                y_mm=0.0,
                width_mm=dx - kerf_mm,
                height_mm=dy - kerf_mm,
                rotated=rot,
                material=part.material,
                grain_direction=part.grain_direction,
            )
        )

    return Cut2DResult(
        sheets_used=len(sheets),
        placements=placements,
        unpacked=unpacked,
        sheet_w_mm=sheet_w_mm,
        sheet_h_mm=sheet_h_mm,
    )


def _pack_maxrects(
    items: list[tuple[CutPart, float, float]],
    sheet_w_mm: float,
    sheet_h_mm: float,
    kerf_mm: float,
    rotation_allowed: bool,
) -> Cut2DResult:
    """Pack with :mod:`rectpack`; tighter than shelves but not saw-cuttable."""
    import rectpack  # type: ignore[import]

    packer = rectpack.newPacker(rotation=rotation_allowed)
    for _ in range(len(items)):
        packer.add_bin(sheet_w_mm, sheet_h_mm, count=1)
    for idx, (_, length, width) in enumerate(items):
        packer.add_rect(length, width, rid=idx)
    packer.pack()

    placements: list[Placement] = []
    packed_ids: set[int] = set()
    for bin_index, bin_ in enumerate(packer):
        for rect in bin_:
            rid: int = rect.rid  # type: ignore[attr-defined]
            part, orig_l, orig_w = items[rid]
            rotated = not (
                abs(rect.width - orig_l) < 0.01 and abs(rect.height - orig_w) < 0.01
            )
            placements.append(
                Placement(
                    label=part.label,
                    sheet_index=bin_index,
                    x_mm=rect.x,
                    y_mm=rect.y,
                    width_mm=rect.width - kerf_mm,
                    height_mm=rect.height - kerf_mm,
                    rotated=rotated,
                    material=part.material,
                    grain_direction=part.grain_direction,
                )
            )
            packed_ids.add(rid)

    unpacked = [items[i][0].label for i in range(len(items)) if i not in packed_ids]
    return Cut2DResult(
        sheets_used=len({p.sheet_index for p in placements}),
        placements=placements,
        unpacked=unpacked,
        sheet_w_mm=sheet_w_mm,
        sheet_h_mm=sheet_h_mm,
    )


def pack_by_material(
    parts: list[CutPart],
    inventory: "Inventory",
    kerf_mm: float = KERF_MM,
    **kwargs: object,
) -> dict[str, Cut2DResult]:
    """Pack sheet parts, looking each material's sheet size up in *inventory*.

    Parts are grouped by ``(material, thickness)`` — different materials and
    thicknesses cannot share a sheet — and each group is packed onto the sheet
    size that material actually comes in.

    Parameters
    ----------
    parts : list[CutPart]
        Sheet-goods parts.  Solid-stock parts should be filtered out first.
    inventory : Inventory
        Stock inventory providing sheet sizes and face-grain conventions.
    kerf_mm : float, optional
        Kerf allowance, default ``KERF_MM``.
    **kwargs
        Forwarded to :func:`optimize_2d`.

    Returns
    -------
    dict[str, Cut2DResult]
        Keyed by ``"{material} {nominal_thickness}"``.

    Raises
    ------
    KeyError
        If a part's material and thickness are not in the inventory.
    """
    groups: dict[tuple[str, float], list[CutPart]] = {}
    for p in parts:
        groups.setdefault((p.material, round(p.thickness_mm, 2)), []).append(p)

    results: dict[str, Cut2DResult] = {}
    for (material, thickness_mm), group in groups.items():
        sheet = _match_sheet(inventory, material, thickness_mm, group)
        results[f"{material} {sheet.nominal_thickness} ({sheet.size_label})"] = (
            optimize_2d(
                group,
                sheet_w_mm=sheet.width_mm,
                sheet_h_mm=sheet.height_mm,
                kerf_mm=kerf_mm,
                sheet_grain=sheet.grain,
                **kwargs,  # type: ignore[arg-type]
            )
        )
    return results


def _match_sheet(
    inventory: "Inventory",
    material: str,
    thickness_mm: float,
    parts: list[CutPart],
):
    """Return the smallest stocked sheet that yields every part in *parts*.

    A material may be stocked in several sizes — Baltic birch is both 5'x5'
    and 4'x8' — so the sheet is chosen by what the parts need, falling back to
    the largest available when nothing fits everything.
    """
    biggest = max(parts, key=lambda p: max(p.length_mm, p.width_mm))
    return inventory.best_sheet_for(
        material,
        length_mm=biggest.length_mm,
        width_mm=biggest.width_mm,
        part_grain=biggest.grain_direction,
        thickness_mm=thickness_mm,
    )
