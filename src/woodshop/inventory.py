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
from typing import Any

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
    """

    material: str
    nominal_thickness: str
    actual_thickness_in: float
    sheet_width_in: float
    sheet_height_in: float
    qty: int = 0
    grain: str = "length"
    price_per_sheet: float | None = None

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

    def sheet_for(self, material: str, nominal_thickness: str) -> SheetStock:
        """Return the sheet stock entry for a material and nominal thickness.

        Parameters
        ----------
        material : str
            Material key, e.g. ``"plywood_baltic_birch"``.
        nominal_thickness : str
            Nominal thickness label, e.g. ``"3/4"``.

        Returns
        -------
        SheetStock
            The matching entry.

        Raises
        ------
        KeyError
            If no entry matches.
        """
        for s in self.sheet_goods:
            if s.material == material and s.nominal_thickness == nominal_thickness:
                return s
        available = sorted(
            f"{s.material} {s.nominal_thickness}" for s in self.sheet_goods
        )
        raise KeyError(
            f"no sheet stock for {material!r} {nominal_thickness!r}; "
            f"stock.yaml has: {available}"
        )

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
