"""Load the shop's stock inventory from ``stock.yaml``.

The inventory answers two questions the optimisers need to ask:

* *What lengths of solid stock can I cut from?* → :meth:`Inventory.stock_lengths_mm`
* *How big is a sheet of this material?* → :meth:`Inventory.sheet_for`

Three kinds of stock are modelled, because they are bought in genuinely
different ways:

``dimensional``
    Softwood sold by nominal size and length — ``2x4`` × 8 ft.  Thickness and
    width are fixed and known; only length is chosen.

``hardwood``
    Sold rough, in quarter thicknesses (``4/4``, ``8/4``), in random widths,
    and priced by the board foot.  Width is *not* a property of the stock —
    it is an outcome of milling and glue-up — so hardwood entries record a
    typical width for yield estimation and an available quantity in board
    feet.

``sheet_goods``
    Sheets, which are emphatically not all 48" × 96".  Baltic birch arrives as
    60" × 60" (nominally 1525 mm square), and that difference decides whether a
    long part fits at all.

Example
-------
>>> inv = Inventory.load()
>>> sheet = inv.sheet_for("plywood_baltic_birch", "3/4")
>>> round(sheet.width_mm), round(sheet.height_mm)
(1524, 1524)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml

__all__ = [
    "DimensionalStock",
    "HardwoodStock",
    "SheetStock",
    "Inventory",
    "DEFAULT_STOCK_PATH",
]

#: ``stock.yaml`` at the repository root.
DEFAULT_STOCK_PATH: Path = Path(__file__).resolve().parents[2] / "stock.yaml"

_MM_PER_IN = 25.4
_MM_PER_FT = 304.8


@dataclass(frozen=True)
class DimensionalStock:
    """Softwood sold by nominal size and length.

    Parameters
    ----------
    species : str
        Species name, e.g. ``"pine"``.
    nominal : str
        Nominal size string, e.g. ``"2x4"``.
    lengths_ft : list[float]
        Available lengths in feet.
    qty : int
        Pieces on hand (per length, as stocked).
    """

    species: str
    nominal: str
    lengths_ft: list[float]
    qty: int = 0

    @property
    def lengths_mm(self) -> list[float]:
        """Available lengths converted to mm."""
        return [ft * _MM_PER_FT for ft in self.lengths_ft]


@dataclass(frozen=True)
class HardwoodStock:
    """Hardwood sold rough, in random widths, priced by the board foot.

    Parameters
    ----------
    species : str
        Species name, e.g. ``"cherry"``.
    thickness_quarter : str
        Quarter thickness as sold, e.g. ``"4/4"``, ``"8/4"``.
    rough_thickness_in : float
        Thickness as delivered, before surfacing.
    surfaced_thickness_in : float
        Thickness you can reliably hit after milling flat and square.  This is
        the number the model should design to.
    typical_width_in : float
        Representative board width, used for rip-yield estimates only.
    lengths_ft : list[float]
        Available lengths in feet.
    qty_board_feet : float, optional
        Board feet on hand.  ``0`` means "buy to suit".
    price_per_bf : float or None, optional
        Cost per board foot, if known.
    """

    species: str
    thickness_quarter: str
    rough_thickness_in: float
    surfaced_thickness_in: float
    typical_width_in: float
    lengths_ft: list[float]
    qty_board_feet: float = 0.0
    price_per_bf: float | None = None

    @property
    def lengths_mm(self) -> list[float]:
        """Available lengths converted to mm."""
        return [ft * _MM_PER_FT for ft in self.lengths_ft]

    @property
    def surfaced_thickness_mm(self) -> float:
        """Post-milling thickness in mm."""
        return self.surfaced_thickness_in * _MM_PER_IN


@dataclass(frozen=True)
class SheetStock:
    """A sheet good.

    Parameters
    ----------
    material : str
        Material key, e.g. ``"plywood_cherry"``.
    nominal_thickness : str
        Nominal thickness label, e.g. ``"3/4"``.  For metric sheets this is the
        label the supplier uses, which may not be the real thickness.
    actual_thickness_in : float
        Measured thickness in inches.
    sheet_width_in : float
        Sheet width in inches.
    sheet_height_in : float
        Sheet height in inches.
    qty : int, optional
        Sheets on hand.
    grain : str, optional
        ``"length"`` if the face veneer runs along ``sheet_height_in``
        (the usual convention for 4x8 hardwood plywood), ``"none"`` for
        materials with no meaningful face-grain direction.
    price_per_sheet : float or None, optional
        Cost per sheet, if known.
    notes : str, optional
        Free text — grade, glue type, anything that distinguishes two sheets
        of the same material and thickness.

    Notes
    -----
    A material and nominal thickness do **not** identify a sheet uniquely.
    Baltic birch 3/4" is stocked both as 5'x5' with interior glue and as 4'x8'
    with exterior glue, and only the 4x8 will yield a part longer than 60".
    Use :meth:`Inventory.best_sheet_for` to pick between them.
    """

    material: str
    nominal_thickness: str
    actual_thickness_in: float
    sheet_width_in: float
    sheet_height_in: float
    qty: int = 0
    grain: str = "length"
    price_per_sheet: float | None = None
    notes: str = ""

    @property
    def area_mm2(self) -> float:
        """Sheet face area in mm²."""
        return self.width_mm * self.height_mm

    @property
    def size_label(self) -> str:
        """Short size description, e.g. ``'48" x 96"'``."""
        return f'{self.sheet_width_in:g}" x {self.sheet_height_in:g}"'

    @property
    def thickness_mm(self) -> float:
        """Measured thickness in mm."""
        return self.actual_thickness_in * _MM_PER_IN

    @property
    def width_mm(self) -> float:
        """Sheet width in mm."""
        return self.sheet_width_in * _MM_PER_IN

    @property
    def height_mm(self) -> float:
        """Sheet height in mm."""
        return self.sheet_height_in * _MM_PER_IN

    def fits(
        self, length_mm: float, width_mm: float, part_grain: str = "none"
    ) -> bool:
        """Return whether a single part of this size fits on one sheet.

        The sheet's face grain runs along :attr:`height_mm`, matching the
        convention in :mod:`woodshop.cutlist.optimize_2d`.  A part whose grain
        runs along its length must therefore lie with its length along
        ``height_mm`` and cannot be turned to make it fit.

        Parameters
        ----------
        length_mm, width_mm : float
            Part dimensions.
        part_grain : str, optional
            The part's ``grain_direction``: ``"length"``, ``"width"``, or
            ``"none"`` (default), which permits either orientation.

        Returns
        -------
        bool
            ``True`` if the part fits in at least one permitted orientation.
        """
        # (extent along width_mm, extent along height_mm) per orientation.
        along_grain = (width_mm, length_mm)
        across_grain = (length_mm, width_mm)

        if self.grain == "none" or part_grain == "none":
            options = [along_grain, across_grain]
        elif part_grain == "length":
            options = [along_grain]
        else:
            options = [across_grain]

        return any(dx <= self.width_mm and dy <= self.height_mm for dx, dy in options)


@dataclass
class Inventory:
    """The shop's stock on hand.

    Parameters
    ----------
    dimensional : list[DimensionalStock]
        Softwood dimensional lumber.
    hardwood : list[HardwoodStock]
        Rough hardwood.
    sheet_goods : list[SheetStock]
        Sheet materials.
    """

    dimensional: list[DimensionalStock] = field(default_factory=list)
    hardwood: list[HardwoodStock] = field(default_factory=list)
    sheet_goods: list[SheetStock] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Inventory":
        """Read an inventory from a YAML file.

        Parameters
        ----------
        path : str or Path, optional
            Path to the YAML file.  Defaults to :data:`DEFAULT_STOCK_PATH`.

        Returns
        -------
        Inventory
            The parsed inventory.

        Raises
        ------
        FileNotFoundError
            If *path* does not exist.
        """
        p = Path(path) if path is not None else DEFAULT_STOCK_PATH
        data: dict[str, Any] = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Inventory":
        """Build an inventory from an already-parsed mapping.

        Parameters
        ----------
        data : dict
            Mapping with optional ``dimensional``, ``hardwood``, and
            ``sheet_goods`` keys.

        Returns
        -------
        Inventory
            The parsed inventory.
        """
        return cls(
            dimensional=[DimensionalStock(**e) for e in data.get("dimensional") or []],
            hardwood=[HardwoodStock(**e) for e in data.get("hardwood") or []],
            sheet_goods=[SheetStock(**e) for e in data.get("sheet_goods") or []],
        )

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def sheets_for(
        self, material: str, nominal_thickness: str | None = None
    ) -> list[SheetStock]:
        """Return every sheet entry matching a material and optional thickness.

        Parameters
        ----------
        material : str
            Material key, e.g. ``"plywood_baltic_birch"``.
        nominal_thickness : str, optional
            Nominal thickness label to filter on, e.g. ``"3/4"``.

        Returns
        -------
        list[SheetStock]
            Matching entries, smallest sheet first.  Empty if none match.
        """
        return sorted(
            (
                s
                for s in self.sheet_goods
                if s.material == material
                and (nominal_thickness is None or s.nominal_thickness == nominal_thickness)
            ),
            key=lambda s: s.area_mm2,
        )

    def sheet_for(self, material: str, nominal_thickness: str) -> SheetStock:
        """Return the smallest sheet stocked in a material and nominal thickness.

        Where a material is stocked in more than one size, the smallest is
        returned — it is normally the cheapest and easiest to handle.  When the
        part size should decide, use :meth:`best_sheet_for` instead.

        Parameters
        ----------
        material : str
            Material key, e.g. ``"plywood_baltic_birch"``.
        nominal_thickness : str
            Nominal thickness label, e.g. ``"3/4"``.

        Returns
        -------
        SheetStock
            The smallest matching entry.

        Raises
        ------
        KeyError
            If no entry matches.
        """
        matches = self.sheets_for(material, nominal_thickness)
        if matches:
            return matches[0]
        available = sorted(
            f"{s.material} {s.nominal_thickness}" for s in self.sheet_goods
        )
        raise KeyError(
            f"no sheet stock for {material!r} {nominal_thickness!r}; "
            f"stock.yaml has: {available}"
        )

    def best_sheet_for(
        self,
        material: str,
        length_mm: float,
        width_mm: float,
        part_grain: str = "none",
        nominal_thickness: str | None = None,
        thickness_mm: float | None = None,
    ) -> SheetStock:
        """Return the smallest stocked sheet that will yield a given part.

        This is the lookup to use when a material comes in more than one size.
        Baltic birch 3/4" is stocked as both 5'x5' and 4'x8'; a 62-1/2" slat
        fits only the latter, and picking by thickness alone would silently
        choose wrong.

        Parameters
        ----------
        material : str
            Material key.
        length_mm, width_mm : float
            Part dimensions.
        part_grain : str, optional
            The part's grain direction, default ``"none"``.
        nominal_thickness : str, optional
            Restrict to this nominal thickness label.
        thickness_mm : float, optional
            Restrict to the closest actual thickness to this value.  Applied
            after *nominal_thickness* if both are given.

        Returns
        -------
        SheetStock
            The smallest sheet the part fits on.  If the part fits none, the
            largest candidate is returned so callers can report against the
            biggest sheet actually available.

        Raises
        ------
        KeyError
            If the material is not stocked at all.
        """
        return self.best_sheet_for_all(
            material,
            [(length_mm, width_mm, part_grain)],
            nominal_thickness=nominal_thickness,
            thickness_mm=thickness_mm,
        )

    def best_sheet_for_all(
        self,
        material: str,
        requirements: Iterable[tuple[float, float, str]],
        nominal_thickness: str | None = None,
        thickness_mm: float | None = None,
    ) -> SheetStock:
        """Return the smallest stocked sheet that yields *every* requirement.

        Sizing a sheet from one representative part is not enough — a long
        narrow part and a wide short one can each fit a different sheet, and
        choosing by either alone strands the other.

        Parameters
        ----------
        material : str
            Material key.
        requirements : iterable of (float, float, str)
            ``(length_mm, width_mm, part_grain)`` for each part that must come
            off this sheet.
        nominal_thickness : str, optional
            Restrict to this nominal thickness label.
        thickness_mm : float, optional
            Restrict to the closest actual thickness to this value.

        Returns
        -------
        SheetStock
            The smallest sheet on which every requirement fits, or the largest
            candidate if no single size fits them all.

        Raises
        ------
        KeyError
            If the material is not stocked at all.
        """
        candidates = self.sheets_for(material, nominal_thickness)
        if not candidates:
            raise KeyError(
                f"no sheet stock for material {material!r}; stock.yaml has: "
                f"{sorted({s.material for s in self.sheet_goods})}"
            )
        if thickness_mm is not None:
            closest = min(abs(s.thickness_mm - thickness_mm) for s in candidates)
            candidates = [
                s
                for s in candidates
                if abs(abs(s.thickness_mm - thickness_mm) - closest) < 1e-9
            ]

        needed = list(requirements)
        # sheets_for sorts by area, so the first match is the smallest.
        for sheet in candidates:
            if all(sheet.fits(length, width, grain) for length, width, grain in needed):
                return sheet
        return candidates[-1]

    def hardwood_for(self, species: str, thickness_quarter: str) -> HardwoodStock:
        """Return the hardwood entry for a species and quarter thickness.

        Parameters
        ----------
        species : str
            Species name, e.g. ``"cherry"``.
        thickness_quarter : str
            Quarter thickness, e.g. ``"8/4"``.

        Returns
        -------
        HardwoodStock
            The matching entry.

        Raises
        ------
        KeyError
            If no entry matches.
        """
        for h in self.hardwood:
            if h.species == species and h.thickness_quarter == thickness_quarter:
                return h
        available = sorted(f"{h.species} {h.thickness_quarter}" for h in self.hardwood)
        raise KeyError(
            f"no hardwood stock for {species!r} {thickness_quarter!r}; "
            f"stock.yaml has: {available}"
        )

    def stock_lengths_mm(self, species: str) -> list[float]:
        """Return every solid-stock length available in *species*, in mm.

        Both dimensional and hardwood entries are considered.

        Parameters
        ----------
        species : str
            Species name.

        Returns
        -------
        list[float]
            Sorted, de-duplicated lengths in mm.  Empty if the species is not
            stocked.
        """
        lengths: set[float] = set()
        for d in self.dimensional:
            if d.species == species:
                lengths.update(d.lengths_mm)
        for h in self.hardwood:
            if h.species == species:
                lengths.update(h.lengths_mm)
        return sorted(lengths)
