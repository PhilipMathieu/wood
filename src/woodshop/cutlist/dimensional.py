"""Buy dimensional stock by the lineal foot, when nobody publishes a length.

:mod:`woodshop.cutlist.optimize_1d` answers "which sticks do I cut this from?"
— a cutting-stock problem, and a good one, provided somebody will tell you what
lengths the yard carries.  Lumbery's white cedar guide prices twenty-eight
profiles and lists no lengths at all, which is enough to estimate a fence and
not enough to lay one out.  Inventing an 8 ft default would turn a real price
into a cut list nobody can buy.

So this module does the other half: it groups a cut list by the stock entry
each part actually buys, totals the **lineal feet** in each group, adds a
stated offcut allowance, and prices the result in the unit the supplier
printed.  It is an estimate and says so — but it is an estimate in the units
the money is quoted in, which is what a fence needs before it needs a cut
plan.

Matching a part to an entry
---------------------------
Nominal size does not identify softwood: white cedar 1x6 is eight entries
spanning $1.30 to $3.75 a lineal foot.  Parts therefore carry ``nominal``,
``grade`` and ``stock_profile`` from :class:`woodshop.parts.Board` through to
:class:`~woodshop.cutlist.extract.CutPart`, and a part that names all three
gets the price of the board it is actually specified in.  A part that names
none is reported as unmatched rather than priced off whichever entry happened
to sort first.

Example
-------
>>> from woodshop.cutlist.extract import CutPart
>>> from woodshop.cutlist.dimensional import plan_dimensional
>>> from woodshop.inventory import Inventory
>>> parts = [CutPart("picket", "white_cedar", "length", 1219.2, 152.4, 25.4,
...                  qty=60, nominal="1x6", grade="STK",
...                  stock_profile="rough sawn")]
>>> plan = plan_dimensional(parts, Inventory.load())
>>> plan.lineal_ft > 200
True
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from woodshop.cutlist.extract import CutPart
from woodshop.inventory import DimensionalStock, Inventory
from woodshop.pricing import CostSummary, PriceLine

__all__ = ["StockGroup", "LinealPlan", "plan_dimensional", "OFFCUT_ALLOWANCE"]

_MM_PER_FT = 304.8

#: Shapes whose stock is round, and whose volume is therefore not its blank's.
_ROUND_SHAPES: frozenset[str] = frozenset({"turned", "pole"})

#: Fraction added to a group's lineal footage for offcuts, default 10%.
#:
#: A cutting-stock solver would replace this with an answer.  Without a list
#: of stocked lengths there is nothing to solve, and a flat allowance that
#: says out loud that it is an allowance beats an optimiser run against an
#: invented 8 ft stick.
OFFCUT_ALLOWANCE: float = 0.10


@dataclass
class StockGroup:
    """One inventory entry and the parts bought from it.

    Parameters
    ----------
    stock : DimensionalStock
        The entry these parts come off.
    parts : list[CutPart]
        Parts assigned to it.
    allowance : float
        Fraction added to the measured footage for offcuts.
    """

    stock: DimensionalStock
    parts: list[CutPart] = field(default_factory=list)
    allowance: float = OFFCUT_ALLOWANCE

    @property
    def label(self) -> str:
        """Human-readable group name, from the inventory entry."""
        return self.stock.stock_label

    @property
    def measured_ft(self) -> float:
        """Lineal feet of finished part, before any allowance."""
        return sum(p.length_mm * p.qty for p in self.parts) / _MM_PER_FT

    @property
    def lineal_ft(self) -> float:
        """Lineal feet to buy: the measured footage plus the allowance."""
        return self.measured_ft * (1.0 + self.allowance)

    @property
    def pieces(self) -> int | None:
        """Sticks to buy, when the rate is quoted per piece.

        ``None`` when the rate is per lineal foot, which is the usual case
        here — a footage does not become a stick count until somebody says
        what lengths they carry.
        """
        length_ft = self.stock.priced_length_ft
        if self.stock.price_per_piece is None or not length_ft:
            return None
        return int(-(-self.lineal_ft // length_ft))  # ceil

    @property
    def quantity(self) -> float:
        """How much to buy, in the unit the supplier quotes."""
        pieces = self.pieces
        return self.lineal_ft if pieces is None else float(pieces)

    @property
    def price_line(self) -> PriceLine | None:
        """Quantity times the rate, with the rate's provenance attached.

        ``None`` if the entry carries no price — an unpriced group is *named*
        by :attr:`LinealPlan.cost_summary`, never quietly costed at zero.
        """
        if self.stock.price is None:
            return None
        return self.stock.price_line(self.quantity)

    @property
    def cost(self) -> float | None:
        """Cost of this group, or ``None`` if the entry has no price."""
        line = self.price_line
        return None if line is None else line.amount


@dataclass
class LinealPlan:
    """A complete dimensional-stock buying plan.

    Parameters
    ----------
    groups : list[StockGroup]
        One entry per stock entry bought from, in label order.
    unmatched : list[tuple[CutPart, str]]
        Parts that could not be matched to an entry, each with the reason.
        Reported rather than raised: a design that mixes cedar with plywood
        should still get a cedar plan.
    excluded : list[str]
        Labels of stock this plan is the wrong plan for — material that is
        stocked, and stocked by the roll or the bundle rather than by the
        foot.  They are carried through to :attr:`cost_summary` so that a
        total which leaves them out says which they are: mesh omitted from a
        fence total is exactly as wrong as an unpriced board omitted from one.
    """

    groups: list[StockGroup] = field(default_factory=list)
    unmatched: list[tuple[CutPart, str]] = field(default_factory=list)
    excluded: list[str] = field(default_factory=list)

    @property
    def lineal_ft(self) -> float:
        """Lineal feet to buy across every group."""
        return sum(g.lineal_ft for g in self.groups)

    @property
    def measured_ft(self) -> float:
        """Lineal feet of finished part across every group, before allowance."""
        return sum(g.measured_ft for g in self.groups)

    @property
    def board_feet(self) -> float:
        """Board feet the plan buys, for comparison with hardwood totals.

        Softwood is not sold this way here — the rate is per lineal foot — but
        the figure is what makes a cedar fence comparable with a cherry bed.

        Round stock is measured as the cylinder it is, not as the square blank
        that bounds it: a 4 in log holds pi/4 of the wood a 4x4 does, and
        billing the corners it never had would flatter a log fence by a fifth.
        """
        return sum(
            p.length_mm * p.width_mm * p.thickness_mm * p.qty
            * (math.pi / 4.0 if p.shape in _ROUND_SHAPES else 1.0)
            for g in self.groups
            for p in g.parts
        ) / (25.4**3) / 144.0

    @property
    def cost_summary(self) -> CostSummary:
        """Costed groups, unpriced groups, and the provenance of both."""
        lines = [g.price_line for g in self.groups]
        return CostSummary.of(
            (line for line in lines if line is not None),
            [g.label for g, line in zip(self.groups, lines) if line is None]
            + list(self.excluded),
        )

    @property
    def cost(self) -> float | None:
        """Total of the groups that have a price; ``None`` if none of them do."""
        return self.cost_summary.total

    @property
    def stock_used(self) -> list[DimensionalStock]:
        """The inventory entries this plan buys from, in group order.

        Pass this to :func:`woodshop.checks.check_price_provenance` so the
        provenance report names the four entries a fence buys rather than
        every entry in the species.
        """
        return [g.stock for g in self.groups]

    def to_text(self) -> str:
        """Render the plan as a few lines of plain text."""
        lines: list[str] = []
        for g in self.groups:
            cost = "" if g.price_line is None else f", {g.price_line.to_text()}"
            pieces = "" if g.pieces is None else f" = {g.pieces} pieces"
            lines.append(
                f"  {g.label:<38s} {g.lineal_ft:>7.0f} LF{pieces}  "
                f"({g.measured_ft:.0f} LF cut + "
                f"{g.allowance * 100:.0f}% offcuts{cost})"
            )
        seen: set[str] = set()
        for part, reason in self.unmatched:
            if reason in seen:
                continue
            seen.add(reason)
            lines.append(f"  (!) {part.label}: {reason}")
        summary = self.cost_summary
        for label in summary.unpriced:
            lines.append(
                f"  (!) {label} has no price in stock.yaml — it is missing from "
                "the total below, not free"
            )
        total_cost = "" if summary.total is None else f", {summary.to_text()}"
        lines.append(
            f"  {'total':<38s} {self.lineal_ft:>7.0f} LF"
            f"{total_cost}"
        )
        return "\n".join(lines)


def plan_dimensional(
    parts: list[CutPart],
    inventory: Inventory,
    allowance: float = OFFCUT_ALLOWANCE,
) -> LinealPlan:
    """Group *parts* by the dimensional stock they buy and total the footage.

    Parameters
    ----------
    parts : list[CutPart]
        The cut list.  Parts with no ``nominal`` size, and parts whose
        species is not stocked as dimensional lumber, come back in
        :attr:`LinealPlan.unmatched`.
    inventory : Inventory
        Stock inventory holding the entries and their prices.
    allowance : float, optional
        Fraction added to each group's footage for offcuts, default
        :data:`OFFCUT_ALLOWANCE`.

    Returns
    -------
    LinealPlan
        Groups in stock-label order, plus whatever could not be matched.

    Raises
    ------
    ValueError
        If *allowance* is negative.
    """
    if allowance < 0:
        raise ValueError(f"allowance must be non-negative, got {allowance!r}")

    groups: dict[str, StockGroup] = {}
    unmatched: list[tuple[CutPart, str]] = []
    excluded: list[str] = []

    for part in parts:
        # Some materials are stocked and are simply not lumber: mesh comes off
        # a roll, shakes come in a bundle. Saying "no nominal size" about a
        # roll of wire would be true and useless.
        unit = inventory.unit_stock_for(part.material)
        if unit is not None:
            if unit.stock_label not in excluded:
                excluded.append(unit.stock_label)
            unmatched.append(
                (
                    part,
                    f"{unit.stock_label} is bought by the {unit.unit}, not by "
                    "the foot — it is priced where it is stocked, under "
                    "unit_goods",
                )
            )
            continue
        if not part.nominal:
            unmatched.append(
                (
                    part,
                    f"no nominal size on a {part.material} part — dimensional "
                    "stock is bought by nominal size, so this one cannot be "
                    "priced",
                )
            )
            continue
        try:
            stock = inventory.dimensional_for(
                part.material,
                part.nominal,
                grade=part.grade or None,
                profile=part.stock_profile or None,
            )
        except KeyError as exc:
            unmatched.append((part, str(exc).strip("'")))
            continue
        group = groups.setdefault(
            stock.stock_label, StockGroup(stock=stock, allowance=allowance)
        )
        group.parts.append(part)

    return LinealPlan(
        groups=[groups[key] for key in sorted(groups)],
        unmatched=unmatched,
        excluded=excluded,
    )
