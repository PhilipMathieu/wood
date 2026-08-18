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

All three can carry a price, and a price is not just a number.  Lumber moves,
hardwood moves a lot, and even a real quote is only true on the day it was
given — so every price travels with ``price_as_of`` and ``price_source``.  A
price with no ``price_as_of`` is *unverified* rather than trusted, which is how
a placeholder invented to give the cost machinery something to multiply stays
visibly a placeholder instead of quietly becoming a quote.

Example
-------
>>> inv = Inventory.load()
>>> sheet = inv.sheet_for("plywood_baltic_birch", "3/4")
>>> round(sheet.width_mm), round(sheet.height_mm)
(1524, 1524)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

import yaml

from woodshop.pricing import PriceLine

__all__ = [
    "PricedStock",
    "DimensionalStock",
    "HardwoodStock",
    "SheetStock",
    "UnitStock",
    "Supplier",
    "VolumeDiscount",
    "Inventory",
    "DEFAULT_STOCK_PATH",
]

#: ``stock.yaml`` at the repository root.
DEFAULT_STOCK_PATH: Path = Path(__file__).resolve().parents[2] / "stock.yaml"

_MM_PER_IN = 25.4
_MM_PER_FT = 304.8


class PricedStock:
    """Price provenance shared by every kind of stock.

    Subclasses supply three things: the money (:attr:`price`), the unit it is
    quoted in (:attr:`price_unit`), and a name for the entry
    (:attr:`stock_label`).  Everything about *believing* the money lives here,
    so the rule is written once and cannot differ between a board and a sheet.

    This is a plain mixin, not a dataclass: the three provenance fields are
    declared on each stock class so that they keep their place at the end of
    the field order and ``Stock(**entry)`` keeps working.
    """

    price: float | None
    price_unit: str
    stock_label: str
    price_as_of: date | None
    price_valid_until: date | None
    price_source: str
    price_url: str

    @property
    def price_is_verified(self) -> bool:
        """``True`` only if there is a price *and* a date it was true on."""
        return self.price is not None and self.price_as_of is not None

    @property
    def price_is_a_special(self) -> bool:
        """``True`` if this rate is a sale price with an end date on it."""
        return self.price_valid_until is not None

    def price_age_days(self, today: date | None = None) -> int | None:
        """Days since the price was quoted, or ``None`` if it carries no date."""
        if self.price_as_of is None:
            return None
        return ((today or date.today()) - self.price_as_of).days

    def price_has_expired(self, today: date | None = None) -> bool:
        """Return ``True`` if this is a sale price whose end date has passed."""
        if self.price_valid_until is None:
            return False
        return (today or date.today()) > self.price_valid_until

    def price_note(self) -> str:
        """Describe where the price came from and when, for a report or a page.

        Returns
        -------
        str
            e.g. ``"O'Brien Hardwoods, phone quote, 2026-08-16"``, or a plain
            statement that the number is unverified.
        """
        if self.price is None:
            return "no price recorded"
        source = self.price_source or "source not recorded"
        if self.price_as_of is None:
            return f"{source}, undated — unverified placeholder"
        note = f"{source}, {self.price_as_of.isoformat()}"
        if self.price_valid_until is not None:
            note += f", sale price through {self.price_valid_until.isoformat()}"
        return note

    def price_line(self, quantity: float) -> PriceLine:
        """Return a :class:`~woodshop.pricing.PriceLine` for *quantity* units.

        Parameters
        ----------
        quantity : float
            How much stock, in :attr:`price_unit`.

        Returns
        -------
        PriceLine
            The quantity, the rate, and the rate's provenance.

        Raises
        ------
        ValueError
            If the entry has no price — an unpriced material must be *named*
            as unpriced, never multiplied by a guess.
        """
        if self.price is None:
            raise ValueError(f"{self.stock_label} has no price in stock.yaml")
        return PriceLine(
            label=self.stock_label,
            quantity=quantity,
            unit=self.price_unit,
            unit_price=self.price,
            as_of=self.price_as_of,
            valid_until=self.price_valid_until,
            source=self.price_source,
            source_url=self.price_url,
        )


@dataclass(frozen=True)
class DimensionalStock(PricedStock):
    """Softwood sold by nominal size and length.

    Parameters
    ----------
    species : str
        Species name, e.g. ``"pine"``.
    nominal : str
        Nominal size string, e.g. ``"2x4"``.
    lengths_ft : list[float]
        Available lengths in feet.  Empty when the supplier publishes a price
        but not a length list — the rate is still usable, the cut plan is not.
    qty : int
        Pieces on hand (per length, as stocked).
    grade : str, optional
        Grade as the supplier names it, e.g. ``"STK"``, ``"low"``.  Free text,
        because every yard grades softwood by its own vocabulary.
    profile : str, optional
        How the stock is worked — ``"rough sawn"``, ``"dressed"``,
        ``"tongue & groove"``, ``"shiplap"``.  With *grade*, this is what
        separates two entries of the same nominal size and very different
        prices.
    price_per_piece : float or None, optional
        Cost of one piece, if that is how it is sold — of the length in
        *price_length_ft*.
    price_length_ft : float or None, optional
        Which stocked length *price_per_piece* refers to.  Defaults to the
        shortest length stocked, because a price per piece means nothing
        without the length attached to it.
    price_per_lineal_ft : float or None, optional
        Cost per lineal foot, if that is how it is sold.  Softwood is quoted
        both ways and the unit is not interchangeable, so recording the one
        the supplier printed beats converting to a house unit.
    price_as_of : datetime.date or None, optional
        The day the price was true.  ``None`` marks the price unverified.
    price_valid_until : datetime.date or None, optional
        Last day a *sale* price holds.  See :class:`PricedStock`.
    price_source : str, optional
        Where the price came from.
    price_url : str, optional
        A link to that source, where one exists.

    Raises
    ------
    ValueError
        If both *price_per_piece* and *price_per_lineal_ft* are set.  One
        entry, one rate: two would silently disagree the moment a supplier
        changed either.
    """

    species: str
    nominal: str
    lengths_ft: list[float]
    qty: int = 0
    grade: str = ""
    profile: str = ""
    price_per_piece: float | None = None
    price_length_ft: float | None = None
    price_per_lineal_ft: float | None = None
    price_as_of: date | None = None
    price_valid_until: date | None = None
    price_source: str = ""
    price_url: str = ""

    def __post_init__(self) -> None:
        """Reject an entry priced two ways at once."""
        if self.price_per_piece is not None and self.price_per_lineal_ft is not None:
            raise ValueError(
                f"{self.species} {self.nominal}: set price_per_piece or "
                "price_per_lineal_ft, not both"
            )

    @property
    def lengths_mm(self) -> list[float]:
        """Available lengths converted to mm."""
        return [ft * _MM_PER_FT for ft in self.lengths_ft]

    @property
    def price(self) -> float | None:
        """Cost of one :attr:`price_unit`, if known."""
        if self.price_per_piece is not None:
            return self.price_per_piece
        return self.price_per_lineal_ft

    @property
    def priced_length_ft(self) -> float | None:
        """The length :attr:`price_per_piece` refers to."""
        if self.price_length_ft is not None:
            return self.price_length_ft
        return min(self.lengths_ft) if self.lengths_ft else None

    @property
    def price_unit(self) -> str:
        """Unit the price is quoted in, e.g. ``'8 ft piece'`` or ``'lineal ft'``."""
        if self.price_per_piece is None and self.price_per_lineal_ft is not None:
            return "lineal ft"
        length = self.priced_length_ft
        return "piece" if length is None else f"{length:g} ft piece"

    @property
    def stock_label(self) -> str:
        """Human-readable entry name, e.g. ``'cedar 1x6 rough sawn (STK)'``."""
        label = f"{self.species} {self.nominal}"
        if self.profile:
            label = f"{label} {self.profile}"
        if self.grade:
            label = f"{label} ({self.grade})"
        return label


@dataclass(frozen=True)
class HardwoodStock(PricedStock):
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
    price_as_of : datetime.date or None, optional
        The day the price was true.  ``None`` marks the price unverified — see
        :class:`PricedStock`.
    price_valid_until : datetime.date or None, optional
        Last day a *sale* price holds.  See :class:`PricedStock`.
    price_source : str, optional
        Where the price came from, e.g. ``"O'Brien Hardwoods, phone quote"``.
    price_url : str, optional
        A link to that source, where one exists.

    Notes
    -----
    Grade is not modelled, and it should be: FAS and #1 Common are a large
    price difference in the same species and thickness, and they yield
    differently, so a single ``price_per_bf`` on an entry is really a price
    *and* an unstated grade.
    """

    species: str
    thickness_quarter: str
    rough_thickness_in: float
    surfaced_thickness_in: float
    typical_width_in: float
    lengths_ft: list[float]
    qty_board_feet: float = 0.0
    price_per_bf: float | None = None
    price_as_of: date | None = None
    price_valid_until: date | None = None
    price_source: str = ""
    price_url: str = ""

    @property
    def lengths_mm(self) -> list[float]:
        """Available lengths converted to mm."""
        return [ft * _MM_PER_FT for ft in self.lengths_ft]

    @property
    def surfaced_thickness_mm(self) -> float:
        """Post-milling thickness in mm."""
        return self.surfaced_thickness_in * _MM_PER_IN

    @property
    def price(self) -> float | None:
        """Cost per board foot, if known."""
        return self.price_per_bf

    @property
    def price_unit(self) -> str:
        """Unit the price is quoted in."""
        return "bd ft"

    @property
    def stock_label(self) -> str:
        """Human-readable entry name, e.g. ``'cherry 4/4'``."""
        return f"{self.species} {self.thickness_quarter}"


@dataclass(frozen=True)
class SheetStock(PricedStock):
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
    price_as_of : datetime.date or None, optional
        The day the price was true.  ``None`` marks the price unverified — see
        :class:`PricedStock`.
    price_valid_until : datetime.date or None, optional
        Last day a *sale* price holds.  See :class:`PricedStock`.
    price_source : str, optional
        Where the price came from.
    price_url : str, optional
        A link to that source, where one exists.
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
    price_as_of: date | None = None
    price_valid_until: date | None = None
    price_source: str = ""
    price_url: str = ""
    notes: str = ""

    @property
    def price(self) -> float | None:
        """Cost per sheet, if known."""
        return self.price_per_sheet

    @property
    def price_unit(self) -> str:
        """Unit the price is quoted in."""
        return "sheet"

    @property
    def stock_label(self) -> str:
        """Human-readable entry name, e.g. ``'plywood_cherry 3/4 (48" x 96")'``."""
        return f"{self.material} {self.nominal_thickness} ({self.size_label})"

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


def _supplier(entry: dict[str, Any]) -> Supplier:
    """Build a :class:`Supplier` from a parsed YAML mapping."""
    data = dict(entry)
    tiers = data.pop("volume_discounts", None) or []
    return Supplier(
        volume_discounts=[VolumeDiscount(**t) for t in tiers],
        **data,
    )


def _with_dates(entry: dict[str, Any]) -> dict[str, Any]:
    """Return *entry* with ``price_as_of`` coerced to a :class:`datetime.date`.

    PyYAML already parses a bare ``2026-08-16`` as a date, but a quoted one is
    a string and a hand-edited file will contain both.  Anything that is
    neither is rejected rather than carried: an unparseable date would satisfy
    "has a ``price_as_of``" while telling nobody when the price was true.
    """
    out = entry
    for field_name in ("price_as_of", "price_valid_until"):
        raw = out.get(field_name)
        if raw is None or (isinstance(raw, date) and not isinstance(raw, datetime)):
            continue
        if isinstance(raw, datetime):
            out = {**out, field_name: raw.date()}
            continue
        if isinstance(raw, str):
            try:
                out = {**out, field_name: date.fromisoformat(raw.strip())}
                continue
            except ValueError as exc:
                raise ValueError(
                    f"{field_name} must be an ISO date (YYYY-MM-DD), got {raw!r}"
                ) from exc
        raise ValueError(
            f"{field_name} must be an ISO date (YYYY-MM-DD), got {raw!r}"
        )
    return out


@dataclass(frozen=True)
class UnitStock(PricedStock):
    """Stock sold by the item, where the item is neither a length nor a sheet.

    A bundle of shakes and a lattice panel are real products with real prices
    and no dimension this file can reason about: the guide does not say how
    much wall a bundle covers, or how thick a lattice sheet is.  They were left
    out of ``stock.yaml`` for exactly that reason, which had the perverse
    effect that the only prices *missing* from a complete price list were the
    two nobody could model.

    A price is worth recording whether or not the geometry is.  This class
    records it, and records the missing figures as missing — ``coverage_sqft``
    and ``thickness_in`` default to ``None`` and stay ``None`` until somebody
    asks the yard.

    Parameters
    ----------
    species : str
        Species name, e.g. ``"white_cedar"``.
    item : str
        What the thing is, as the supplier names it, e.g. ``'shakes 3/8"'``.
    unit : str
        What one of them is sold as — ``"bundle"``, ``"sheet"``, ``"each"``.
    material : str, optional
        The material key a part made of this carries, e.g.
        ``"steel_mesh_black"``.  Empty for stock nothing is modelled in yet,
        which is most of it: a bundle of shakes has no part to be.
    grade : str, optional
        Grade as the supplier names it, e.g. ``"clear"``, ``"wall"``.
    qty : int, optional
        Units on hand.
    size : str, optional
        Size as published, e.g. ``"4x8"``.  Free text, because a bundle has no
        size and a lattice sheet's is quoted in feet.
    coverage_sqft : float or None, optional
        Square feet one unit covers, where the supplier says.  ``None`` means
        nobody has said, and a design that needs the number has to ask rather
        than assume one.
    count_per_unit : int or None, optional
        How many pieces are in one unit, where the package says — 25 bolts in
        a box, 340 staples in a 5 lb carton.  It is what turns a count derived
        from geometry into a number of packages to buy, and it is ``None``
        until somebody reads the label, for the same reason as the rest.
    thickness_in : float or None, optional
        Thickness where published.  ``None`` for the same reason.
    price_per_unit : float or None, optional
        Cost of one *unit*.
    price_as_of : datetime.date or None, optional
        The day the price was true.  ``None`` marks it unverified.
    price_valid_until : datetime.date or None, optional
        Last day a *sale* price holds.  See :class:`PricedStock`.
    price_source : str, optional
        Where the price came from.
    price_url : str, optional
        A link to that source.
    notes : str, optional
        Free text.
    """

    species: str
    item: str
    unit: str
    material: str = ""
    grade: str = ""
    qty: int = 0
    size: str = ""
    coverage_sqft: float | None = None
    count_per_unit: int | None = None
    thickness_in: float | None = None
    price_per_unit: float | None = None
    price_as_of: date | None = None
    price_valid_until: date | None = None
    price_source: str = ""
    price_url: str = ""
    notes: str = ""

    @property
    def price(self) -> float | None:
        """Cost of one unit, if known."""
        return self.price_per_unit

    @property
    def price_unit(self) -> str:
        """Unit the price is quoted in, e.g. ``"bundle"``."""
        return self.unit

    def packages_for(self, count: int) -> int | None:
        """Return how many units hold *count* pieces, rounding up.

        ``None`` when the package does not say how many are in it, which is
        the difference between "buy two boxes" and "buy some boxes": a design
        that cannot count the pieces in a carton has to ask rather than divide
        by a number it made up.

        Parameters
        ----------
        count : int
            Pieces the design needs.
        """
        if not self.count_per_unit:
            return None
        return -(-count // self.count_per_unit)  # ceil

    @property
    def stock_label(self) -> str:
        """Human-readable name, e.g. ``'white_cedar shakes 3/8" (clear)'``."""
        label = f"{self.species} {self.item}"
        if self.size:
            label = f"{label} {self.size}"
        if self.grade:
            label = f"{label} ({self.grade})"
        return label


@dataclass(frozen=True)
class VolumeDiscount:
    """One tier of a supplier's volume discount.

    Parameters
    ----------
    over : float
        Order total above which the tier applies.
    percent : float
        Percentage off.
    """

    over: float
    percent: float


@dataclass(frozen=True)
class Supplier:
    """A yard, and the terms that apply to an order rather than to a board.

    A discount is a property of the *order*, not of any entry in it, which is
    why it cannot live on a stock entry: 15% off a $10,000 order changes every
    line at once or none of them.

    Parameters
    ----------
    name : str
        Supplier name.
    location : str, optional
        Street address, as published.
    phone : str, optional
        Phone number — the thing that turns a published guide into a quote.
    url : str, optional
        Where the prices are published.
    volume_discounts : list[VolumeDiscount], optional
        Tiers, in any order.
    notes : str, optional
        Free text.
    """

    name: str
    location: str = ""
    phone: str = ""
    url: str = ""
    volume_discounts: list[VolumeDiscount] = field(default_factory=list)
    notes: str = ""

    def discount_for(self, total: float) -> VolumeDiscount | None:
        """Return the best tier an order of *total* qualifies for.

        Parameters
        ----------
        total : float
            Order total before discount.

        Returns
        -------
        VolumeDiscount or None
            The largest applicable tier, or ``None`` if the order is below
            every threshold.
        """
        applicable = [t for t in self.volume_discounts if total >= t.over]
        return max(applicable, key=lambda t: t.percent) if applicable else None

    def next_tier(self, total: float) -> VolumeDiscount | None:
        """Return the cheapest tier an order of *total* has not yet reached."""
        ahead = [t for t in self.volume_discounts if total < t.over]
        return min(ahead, key=lambda t: t.over) if ahead else None


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
    unit_goods : list[UnitStock]
        Stock sold by the item — bundles, panels — whose geometry the supplier
        does not publish.
    suppliers : list[Supplier]
        Yards, and the order-level terms they publish.
    """

    dimensional: list[DimensionalStock] = field(default_factory=list)
    hardwood: list[HardwoodStock] = field(default_factory=list)
    sheet_goods: list[SheetStock] = field(default_factory=list)
    unit_goods: list[UnitStock] = field(default_factory=list)
    suppliers: list[Supplier] = field(default_factory=list)

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
            Mapping with optional ``dimensional``, ``hardwood``,
            ``sheet_goods``, ``unit_goods`` and ``suppliers`` keys.

        Returns
        -------
        Inventory
            The parsed inventory.

        Raises
        ------
        ValueError
            If a ``price_as_of`` is not a date — a price dated ``"soon"`` is
            worse than a price with no date, because the check that looks for
            provenance would accept it.
        """
        return cls(
            dimensional=[
                DimensionalStock(**_with_dates(e)) for e in data.get("dimensional") or []
            ],
            hardwood=[
                HardwoodStock(**_with_dates(e)) for e in data.get("hardwood") or []
            ],
            sheet_goods=[
                SheetStock(**_with_dates(e)) for e in data.get("sheet_goods") or []
            ],
            unit_goods=[
                UnitStock(**_with_dates(e)) for e in data.get("unit_goods") or []
            ],
            suppliers=[_supplier(e) for e in data.get("suppliers") or []],
        )

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def all_stock(self) -> list[PricedStock]:
        """Return every entry of every kind, in a stable order.

        Useful to anything that asks a question of the whole inventory rather
        than of one material — auditing price provenance, for instance.
        """
        return [
            *self.dimensional,
            *self.hardwood,
            *self.sheet_goods,
            *self.unit_goods,
        ]

    def supplier(self, name: str) -> Supplier:
        """Return the supplier called *name*.

        Parameters
        ----------
        name : str
            Supplier name as recorded.

        Returns
        -------
        Supplier
            The matching entry.

        Raises
        ------
        KeyError
            If no supplier matches.
        """
        for entry in self.suppliers:
            if entry.name == name:
                return entry
        raise KeyError(
            f"no supplier named {name!r}; stock.yaml has: "
            f"{sorted(s.name for s in self.suppliers)}"
        )

    def unit_goods_for(self, species: str) -> list[UnitStock]:
        """Return every unit-priced entry in *species*, in label order."""
        return sorted(
            (u for u in self.unit_goods if u.species == species),
            key=lambda u: u.stock_label,
        )

    def unit_stock_for(self, material: str) -> UnitStock | None:
        """Return the unit-priced entry a part of *material* is bought as.

        ``None`` when nothing matches, which is the usual answer: most
        materials are lumber and are bought by the foot or the board foot.

        Parameters
        ----------
        material : str
            Material key from a part, e.g. ``"steel_mesh_black"``.
        """
        for entry in self.unit_goods:
            if entry.material and entry.material == material:
                return entry
        return None

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

    def dimensional_for(
        self,
        species: str,
        nominal: str,
        grade: str | None = None,
        profile: str | None = None,
    ) -> DimensionalStock:
        """Return the dimensional entry a part of this description buys.

        Nominal size alone does not identify softwood.  White cedar 1x6 is
        eight entries in ``stock.yaml`` — rough sawn, dressed, shiplap,
        tongue and groove, in two grades — spanning $1.30 to $3.75 a lineal
        foot.  Asking for "cedar 1x6" and getting whichever one came first in
        the file would be a 3x error wearing the clothes of a lookup.

        Parameters
        ----------
        species : str
            Species name, e.g. ``"white_cedar"``.
        nominal : str
            Nominal size, e.g. ``"1x6"``.
        grade : str, optional
            Grade as the supplier names it, e.g. ``"STK"``.  ``None`` matches
            any grade, which is only useful where one entry exists.
        profile : str, optional
            How the stock is worked, e.g. ``"rough sawn"``.  ``None`` matches
            any profile.

        Returns
        -------
        DimensionalStock
            The one matching entry.

        Raises
        ------
        KeyError
            If nothing matches, or if more than one entry does — an ambiguous
            match names the candidates rather than picking one.
        """
        matches = [
            d
            for d in self.dimensional
            if d.species == species
            and d.nominal == nominal
            and (grade is None or d.grade == grade)
            and (profile is None or d.profile == profile)
        ]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            available = sorted(
                d.stock_label for d in self.dimensional if d.species == species
            )
            raise KeyError(
                f"no {species} {nominal} in stock.yaml"
                + (
                    f" with grade={grade!r} profile={profile!r}"
                    if grade is not None or profile is not None
                    else ""
                )
                + f"; stock.yaml has: {available}"
            )
        raise KeyError(
            f"{species} {nominal} is ambiguous — {len(matches)} entries match: "
            f"{sorted(m.stock_label for m in matches)}; name the grade and "
            "profile, because they are most of the price"
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
