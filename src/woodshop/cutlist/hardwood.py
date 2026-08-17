"""Nest parts onto random-width hardwood boards and total the board feet.

Dimensional lumber comes in fixed widths, so laying out cuts is a 1-D problem:
you only choose where along the board to cut.  Hardwood does not work that way.
It arrives rough, in whatever widths the log gave, and you rip parts out of a
board's *width* as well as its length.  Treating it as 1-D produces cut lists
that buy a fresh eight-foot board for every 2-1/2" slat.

So hardwood is nested in two dimensions — the same shelf packer the sheet-goods
optimiser uses — against a board of representative width and a chosen length.
The answer is an estimate, because the next board off the pile will be a
different width, but it is an estimate in the right units: board feet, which is
what hardwood is priced in.

Example
-------
>>> from woodshop.inventory import Inventory
>>> from woodshop.cutlist.extract import CutPart
>>> from woodshop.cutlist.hardwood import nest_hardwood
>>> parts = [CutPart("slat", "cherry", "length", 1587.5, 63.5, 19.05, qty=16)]
>>> plan = nest_hardwood(parts, Inventory.load(), "cherry")
>>> plan.boards_needed >= 1
True
"""

from __future__ import annotations

from dataclasses import dataclass, field

from woodshop.cutlist.extract import CutPart
from woodshop.cutlist.optimize_2d import Cut2DResult, optimize_2d
from woodshop.inventory import HardwoodStock, Inventory
from woodshop.lumber import KERF_MM, mm_to_fractional_inch
from woodshop.pricing import CostSummary, PriceLine

__all__ = ["BoardGroup", "HardwoodPlan", "nest_hardwood"]

_MM_PER_IN = 25.4
_MM_PER_FT = 304.8

#: Extra thickness planed away getting rough stock flat, in mm (1/8" total).
SURFACING_ALLOWANCE_MM = 3.175

#: Width lost jointing both edges of a board straight, in mm (1/4" total).
JOINTING_ALLOWANCE_MM = 6.35


@dataclass
class BoardGroup:
    """Boards of one quarter thickness and the parts nested on them.

    Parameters
    ----------
    stock : HardwoodStock
        The inventory entry these boards come from.
    board_length_mm : float
        Length of board chosen for this group.
    nesting : Cut2DResult
        Layout of parts across the board width and length.
    parts : list[CutPart]
        The parts in this group.
    """

    stock: HardwoodStock
    board_length_mm: float
    nesting: Cut2DResult
    parts: list[CutPart] = field(default_factory=list)

    @property
    def boards_needed(self) -> int:
        """How many boards this group consumes."""
        return self.nesting.sheets_used

    @property
    def board_feet(self) -> float:
        """Rough board feet purchased for this group."""
        area_in2 = (
            self.boards_needed
            * (self.stock.typical_width_in * _MM_PER_IN)
            * self.board_length_mm
        ) / (_MM_PER_IN**2)
        return area_in2 * self.stock.rough_thickness_in / 144.0

    @property
    def price_line(self) -> PriceLine | None:
        """Board feet times the rate, with the rate's provenance attached.

        ``None`` if the stock has no price — an unpriced group is *named* by
        :attr:`HardwoodPlan.cost_summary`, never quietly costed at zero.
        """
        if self.stock.price_per_bf is None:
            return None
        return self.stock.price_line(self.board_feet)

    @property
    def cost(self) -> float | None:
        """Cost of this group, or ``None`` if the stock has no price.

        A bare float, so it carries no provenance: use :attr:`price_line` for
        anything a person will read.
        """
        line = self.price_line
        return None if line is None else line.amount

    @property
    def purchased_area_mm2(self) -> float:
        """Face area of the boards bought for this group, in mm².

        Billed at the width you pay for, not the narrower width that survives
        jointing — otherwise the yield quietly excludes the waste it is
        supposed to be measuring.
        """
        return (
            self.boards_needed
            * self.stock.typical_width_in * _MM_PER_IN
            * self.board_length_mm
        )

    @property
    def yield_fraction(self) -> float:
        """Fraction of the boards bought that the nested blanks claim (0-1)."""
        total = self.purchased_area_mm2
        return 0.0 if total == 0 else self.nesting.used_area_mm2 / total

    @property
    def finished_yield_fraction(self) -> float:
        """Fraction of the boards bought that ends up in finished parts."""
        total = self.purchased_area_mm2
        return 0.0 if total == 0 else self.nesting.finished_area_mm2 / total

    @property
    def label(self) -> str:
        """Human-readable group name, e.g. ``'cherry 4/4'``."""
        return f"{self.stock.species} {self.stock.thickness_quarter}"


@dataclass
class HardwoodPlan:
    """A complete hardwood buying plan.

    Parameters
    ----------
    groups : list[BoardGroup]
        One entry per quarter thickness.
    unmatched : list[CutPart]
        Parts whose finished thickness matched no stocked quarter thickness.
    glue_ups : list[tuple[str, int, float]]
        ``(label, n_staves, stave_width_mm)`` for each part too wide to come
        from one board, which must therefore be edge-glued.
    """

    groups: list[BoardGroup] = field(default_factory=list)
    unmatched: list[CutPart] = field(default_factory=list)
    glue_ups: list[tuple[str, int, float]] = field(default_factory=list)

    @property
    def boards_needed(self) -> int:
        """Total boards across all groups."""
        return sum(g.boards_needed for g in self.groups)

    @property
    def board_feet(self) -> float:
        """Total rough board feet across all groups."""
        return sum(g.board_feet for g in self.groups)

    @property
    def cost_summary(self) -> CostSummary:
        """Costed groups, unpriced groups, and the provenance of both.

        The summary is the honest form of :attr:`cost`: it can say "$1,097,
        prices as of 2026-08-16, excluding the birch nobody has priced", which
        a float cannot.
        """
        lines = [g.price_line for g in self.groups]
        return CostSummary.of(
            (line for line in lines if line is not None),
            (g.label for g, line in zip(self.groups, lines) if line is None),
        )

    @property
    def cost(self) -> float | None:
        """Total of the groups that have a price; ``None`` if none of them do.

        This used to return ``None`` when *any* group was unpriced, so a single
        missing price dropped the cost line entirely rather than flagging it.
        It now totals what it can, and :attr:`cost_summary` says what was left
        out — a partial total that names its gaps beats no total at all.
        """
        return self.cost_summary.total

    @property
    def purchased_area_mm2(self) -> float:
        """Face area of every board bought, in mm²."""
        return sum(
            g.boards_needed * g.stock.typical_width_in * _MM_PER_IN * g.board_length_mm
            for g in self.groups
        )

    @property
    def yield_fraction(self) -> float:
        """Fraction of purchased board area taken up by blanks (0-1).

        This measures the nesting: how much of each board the layout claims.
        It says nothing about what happens to a blank afterwards.
        """
        used = sum(g.nesting.used_area_mm2 for g in self.groups)
        total = self.purchased_area_mm2
        return 0.0 if total == 0 else used / total

    @property
    def finished_yield_fraction(self) -> float:
        """Fraction of purchased board area that ends up in finished parts.

        The same number as :attr:`yield_fraction` for a project made entirely
        of rectangles.  Lower as soon as anything is turned: a round top is
        bought as a square, and about a fifth of that square leaves the shop
        as shavings.
        """
        finished = sum(g.nesting.finished_area_mm2 for g in self.groups)
        total = self.purchased_area_mm2
        return 0.0 if total == 0 else finished / total

    def to_text(self) -> str:
        """Render the plan as a few lines of plain text."""
        lines: list[str] = []
        for g in self.groups:
            # Never a bare figure: a price that does not say when it was true
            # says so here, every time it is printed.
            cost = "" if g.price_line is None else f", {g.price_line.to_text()}"
            lines.append(
                f"  {g.label:<12s} {g.boards_needed:>3d} boards of "
                f"{g.stock.typical_width_in:g}\" x "
                f"{g.board_length_mm / _MM_PER_FT:.0f} ft  "
                f"({g.board_feet:.1f} bd ft{cost})"
            )
            for label in sorted(set(g.nesting.unpacked)):
                lines.append(
                    f"    (!) {label} does not fit a "
                    f"{g.stock.typical_width_in:g}\" x "
                    f"{g.board_length_mm / _MM_PER_FT:.0f} ft board"
                )
        for label, n, stave_w in self.glue_ups:
            lines.append(
                f"  glue-up: {label} is {n} staves of "
                f"{mm_to_fractional_inch(stave_w)}, edge-glued"
            )
        for p in self.unmatched:
            lines.append(
                f"  (!) {p.label}: no stocked thickness matches "
                f"{mm_to_fractional_inch(p.thickness_mm)}"
            )
        summary = self.cost_summary
        total_cost = "" if summary.total is None else f", {summary.to_text()}"
        for label in summary.unpriced:
            lines.append(
                f"  (!) {label} has no price in stock.yaml — it is missing from "
                "the total below, not free"
            )
        # Two yields, and they differ only when something is not a rectangle.
        # Printing both then is the honest thing; printing both always is
        # noise.
        yields = f"{self.yield_fraction * 100:.0f}% yield"
        if abs(self.finished_yield_fraction - self.yield_fraction) > 0.005:
            yields += (
                f" nested, {self.finished_yield_fraction * 100:.0f}% after "
                "the lathe"
            )
        lines.append(
            f"  {'total':<12s} {self.boards_needed:>3d} boards, "
            f"{self.board_feet:.1f} bd ft{total_cost}, {yields}"
        )
        return "\n".join(lines)


def stave_wide_parts(
    parts: list[CutPart],
    max_width_mm: float,
) -> tuple[list[CutPart], list[tuple[str, int, float]]]:
    """Split parts wider than a board into edge-glued staves.

    A solid panel wider than the stock it comes from is not a part you cut —
    it is a glue-up.  Nesting it whole reports it as impossible; splitting it
    into equal staves reports what you actually buy and mill.

    Parameters
    ----------
    parts : list[CutPart]
        Solid-wood parts.
    max_width_mm : float
        Widest part obtainable from a single board, after jointing.

    Returns
    -------
    parts : list[CutPart]
        Input parts, with over-wide ones replaced by their staves.
    glue_ups : list[tuple[str, int, float]]
        ``(label, n_staves, stave_width_mm)`` for each part that was split.
    """
    out: list[CutPart] = []
    glue_ups: list[tuple[str, int, float]] = []
    for p in parts:
        if p.width_mm <= max_width_mm:
            out.append(p)
            continue
        n = int(-(-p.width_mm // max_width_mm))  # ceil
        stave_w = p.width_mm / n
        glue_ups.append((p.label, n, stave_w))
        # A stave is a rectangular board however round the finished part is —
        # the shape only appears after the glue-up comes off the clamps — so
        # the stave is nested as a rectangle.  Its share of the finished area
        # rides along so that yield still tells the truth about the shavings.
        profile = p.profile or ""
        if p.shape != "rectangular" and profile:
            profile = f"1 of {n} staves for a {profile}"
        out.append(
            CutPart(
                label=f"{p.label}_stave",
                material=p.material,
                grain_direction=p.grain_direction,
                length_mm=p.length_mm,
                width_mm=stave_w,
                thickness_mm=p.thickness_mm,
                qty=p.qty * n,
                finished_area_each_mm2=p.finished_area_mm2 / (p.qty * n),
                profile=profile,
            )
        )
    return out, glue_ups


def _match_stock(
    thickness_mm: float, candidates: list[HardwoodStock]
) -> HardwoodStock | None:
    """Return the thinnest stock that can be surfaced to *thickness_mm*."""
    usable = [c for c in candidates if c.surfaced_thickness_mm >= thickness_mm - 0.1]
    if not usable:
        return None
    return min(usable, key=lambda c: c.surfaced_thickness_mm)


def nest_hardwood(
    parts: list[CutPart],
    inventory: Inventory,
    species: str,
    kerf_mm: float = KERF_MM,
    board_length_mm: float | None = None,
) -> HardwoodPlan:
    """Nest hardwood parts onto boards and total the board feet.

    Parts are grouped by the quarter thickness they must be milled from — the
    thinnest stocked thickness that will surface to the finished dimension —
    and each group is nested onto a board of the stock's typical width.

    Parameters
    ----------
    parts : list[CutPart]
        Solid-wood parts in *species*.  Parts in other species are ignored.
    inventory : Inventory
        Stock inventory supplying quarter thicknesses and board widths.
    species : str
        Species to plan for, e.g. ``"cherry"``.
    kerf_mm : float, optional
        Saw kerf, default ``KERF_MM``.
    board_length_mm : float, optional
        Board length to buy.  Defaults to the longest length stocked for the
        species.

    Returns
    -------
    HardwoodPlan
        Boards, board feet, cost, and yield.

    Raises
    ------
    KeyError
        If *species* has no hardwood entries in the inventory.
    """
    candidates = [h for h in inventory.hardwood if h.species == species]
    if not candidates:
        raise KeyError(
            f"no hardwood stock for {species!r}; stock.yaml has: "
            f"{sorted({h.species for h in inventory.hardwood})}"
        )

    grouped: dict[str, tuple[HardwoodStock, list[CutPart]]] = {}
    unmatched: list[CutPart] = []
    for p in parts:
        if p.material != species:
            continue
        stock = _match_stock(p.thickness_mm, candidates)
        if stock is None:
            unmatched.append(p)
            continue
        grouped.setdefault(stock.thickness_quarter, (stock, []))[1].append(p)

    groups: list[BoardGroup] = []
    glue_ups: list[tuple[str, int, float]] = []
    for _, (stock, group_parts) in sorted(grouped.items()):
        # Leave room to joint both edges straight before glue-up.
        usable_width = stock.typical_width_in * _MM_PER_IN - JOINTING_ALLOWANCE_MM
        group_parts, group_glue_ups = stave_wide_parts(group_parts, usable_width)
        glue_ups.extend(group_glue_ups)
        lengths = [board_length_mm] if board_length_mm is not None else stock.lengths_mm
        if not lengths:
            raise ValueError(
                f"{stock.species} {stock.thickness_quarter}: no lengths_ft in "
                "stock.yaml, so there is nothing to nest parts onto"
            )
        candidates_for_group = []
        for length in lengths:
            # The board is the "sheet": its length runs along +Y so that parts
            # whose grain runs along their length are laid out along the board,
            # which is the only orientation solid stock allows.
            nesting = optimize_2d(
                group_parts,
                # Nest across the width that survives jointing, not the width
                # as delivered — the first pass over the jointer removes it.
                # Board feet still bill the full width, because that is what
                # you buy.
                sheet_w_mm=usable_width,
                sheet_h_mm=length,
                kerf_mm=kerf_mm,
                sheet_grain="length",
                strategy="shelf",
            )
            candidates_for_group.append(
                BoardGroup(
                    stock=stock,
                    board_length_mm=length,
                    nesting=nesting,
                    parts=group_parts,
                )
            )
        # Longer boards are not automatically cheaper: a 62-1/2" slat wastes
        # less of an 8 ft board than of a 10 ft one.  Buy by the board foot,
        # and prefer a plan that leaves nothing un-nested.
        groups.append(
            min(
                candidates_for_group,
                key=lambda g: (len(g.nesting.unpacked), g.board_feet),
            )
        )

    return HardwoodPlan(groups=groups, unmatched=unmatched, glue_ups=glue_ups)
