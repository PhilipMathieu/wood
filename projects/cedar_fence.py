"""Cedar fence — 38 ft at 4 ft high, in three styles, plus two gated sections.

The brief
---------
About 38 ft of northern white cedar fence, 4 ft high, in a couple of sensible
design options, plus two 10 ft sections with gates.  That is 58 ft of fence in
total: 38 ft of run, and two 10 ft sections that are mostly gate.

Everything below is measured **post centre to post centre**, because that is
what a tape measure along a property line gives you and what the lumber list
has to be derived from.  A 10 ft gate section is therefore 10 ft on centre and
a 9'-6" hole, once the two 6x6 posts take 6" out of it.

Three styles, one frame
-----------------------
The posts, the rails and the holes are the same in all three.  Only the infill
changes, and with it the price and how much of the neighbours you see:

``picket``
    1x6 boards, vertical, spaced about 1-3/4" apart.  Cheapest, dries fastest,
    and sees the most wind through it rather than against it.

``board_on_board``
    1x6 boards, vertical, in two layers: an under course spaced 4" apart and an
    over course centred on each gap, lapping 1" each side.  Full privacy, and
    the lap is what keeps it private after the boards shrink — a butted board
    fence opens a 1/4" slot at every joint in its first summer.

``horizontal``
    1x6 boards run horizontally between the posts, no rails.  The modern look,
    and the one with a structural catch: the boards *are* the rails, so the
    bays have to be shorter or the boards cup and sag between posts.

What is chosen rather than given
--------------------------------
The brief gives a length, a height and a number of gates.  Everything else is a
decision, and they are gathered here so they can be argued with:

* **Posts are 8 ft, cut flush at 48"** — 4 ft in the ground, 4 ft in the air.
  Southern Maine frost goes to about 4 ft, and an 8 ft post is the one length
  that puts the fence at 4 ft with the bottom of the post below it.  A post cap
  or a 2" reveal is 2" more post; ``post_proud_in`` builds it that way.
* **Gate posts are 6x6 and 6" deeper**, because a gate is a lever that spends
  its life trying to pull its hinge post over.
* **Bays are whatever divides the run** into spans of 8 ft or less (6 ft for
  the horizontal style, where the boards do the spanning).  38 ft comes out as
  six bays of 6'-4" with a gate section between the halves.
* **Boards stop 2" above grade** and the gates 3", so nothing wicks water out
  of the ground and a rake can get under the gate.
* **The rot risk is the buried post and nothing else.**  Northern white cedar
  heartwood is rot resistant; its sapwood is not, and a fence post is bought by
  the stick rather than sorted for heartwood.  See the check.

Prices
------
Real, and the first project in this repository where they are: Lumbery's
published white cedar guide, per lineal foot, read 2026-08-17.  The same guide
prices the stock and lists **no lengths at all**, so this project buys by the
foot and says so — there is no cut plan here, because a cut plan needs a list
of sticks nobody has published.  ``--assume-lengths`` will lay one out against
lengths you supply, and every finding it produces is labelled as resting on
your assumption rather than on the guide.

Run it
------
::

    uv run python projects/cedar_fence.py
    uv run python projects/cedar_fence.py --style all --outdir build
    uv run python projects/cedar_fence.py --style picket --gate-leaves 1
    uv run python projects/cedar_fence.py --compare
"""

from __future__ import annotations

import argparse
import copy
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from build123d import Compound, Pos, Rotation

from woodshop.checks import (
    DENSITY_KG_M3,
    ELASTIC_MODULUS_MPA,
    CheckReport,
    Finding,
    Severity,
    beam_deflection_mm,
    check_envelope,
    check_material_suitability,
    check_price_provenance,
    estimate_mass_kg,
)
from woodshop.cutlist.dimensional import (
    OFFCUT_ALLOWANCE,
    LinealPlan,
    plan_dimensional,
)
from woodshop.cutlist.extract import CutPart, extract
from woodshop.inventory import Inventory
from woodshop.lumber import (
    actual_dimensions_mm,
    mm_to_fractional_inch,
    rough_dimensions_mm,
)
from woodshop.parts import Board, Panel, Pole
from woodshop.pricing import CostSummary, PriceLine, format_money
from woodshop.project import ProjectSpec
from woodshop.render import export_assembly, render_assembly, render_cut_list

IN = 25.4
FT = 304.8

#: The infill styles this project builds.
STYLES: tuple[str, ...] = (
    "picket",
    "board_on_board",
    "horizontal",
    "log_and_mesh",
)

#: Styles whose infill is boards rather than something bought by the roll.
BOARD_STYLES: tuple[str, ...] = ("picket", "board_on_board", "horizontal")

#: Orientation of a part standing upright in the fence plane: length up +Z,
#: width along the run (+X), thickness across it (+Y).
UPRIGHT = Rotation(90, 0, 90)

#: Orientation of a part lying along the run: length +X, width up +Z.
ALONG_RUN = Rotation(90, 0, 0)

#: Orientation of a post: square section, length up +Z.
UPRIGHT_POST = Rotation(0, 90, 0)

#: Orientation of a pole lying along the run: its axis, which is +Z as built,
#: swung onto +X.
POLE_ALONG_RUN = Rotation(0, 90, 0)

#: Frost depth in southern Maine, in inches.  A post whose bottom sits above
#: this is a post that gets jacked out of the ground a little every spring.
FROST_DEPTH_IN = 48.0

#: Longest bay worth building at this height, in feet, and the shorter limit
#: for the horizontal style where the boards do the spanning.
#:
#: These are what the checks measure against.  ``max_bay_ft`` is the knob that
#: divides the run; these two are the opinion about where the answer stops
#: being a fence, so raising the knob past them gets a finding rather than
#: silence.
RECOMMENDED_MAX_BAY_FT = 8.0
RECOMMENDED_MAX_HORIZONTAL_BAY_FT = 6.0

#: Lengths softwood is commonly stocked in, in feet.  Lumbery publishes none,
#: so this is what to *ask* for rather than what is known to be there.
COMMON_LENGTHS_FT: tuple[float, ...] = (8.0, 10.0, 12.0, 14.0, 16.0)


def inches(value: float) -> float:
    """Convert inches to mm.

    Parameters
    ----------
    value : float
        Length in inches.

    Returns
    -------
    float
        Length in mm.
    """
    return value * IN


#: What a milled profile *covers* when it is butted to its neighbour, in
#: inches, keyed by ``(nominal, profile)``.
#:
#: ASSUMED, every one of them.  Lumbery prices twelve milled profiles and
#: publishes the coverage of none: what a tongue and groove board shows is set
#: by how deep the groove is cut, and that is a property of the moulder rather
#: than of the price list.  These are the industry-standard figures for stock
#: of this nominal size, and a fence built on them is a fence whose board count
#: is right to about one board in forty — worth having, and worth a finding
#: that says where the number came from.
#:
#: A clapboard is the odd one out: it is tapered, and its coverage is the
#: *exposure* the person nailing it up chooses, not a property of the board.
#: 4" is a common exposure for a 6" clapboard and nothing more authoritative
#: than that.
ASSUMED_COVERAGE_IN: dict[tuple[str, str], float] = {
    ("1x4", "tongue & groove, dressed"): 3.125,
    ("1x6", "tongue & groove, dressed"): 5.125,
    ("1x6", "nickel gap shiplap, dressed"): 5.125,
    ("1x6", "shiplap (standard), dressed"): 5.125,
    ("1x6", "drop siding, tongue & groove"): 5.125,
    ("1x6", "clapboard"): 4.0,
}


@dataclass(frozen=True)
class StockChoice:
    """One inventory entry chosen for one role, and what it measures.

    A fence is four material decisions — boards, rails, line posts, gate posts
    — and each of them is a choice among entries that share a nominal size and
    do not share a price.  This is the object that makes the choice explicit,
    so that "the boards" can be rough sawn 1x6 in STK at $2.30/LF or dressed
    1x6 tongue and groove at $3.60/LF without anything else in the model
    caring which.

    Parameters
    ----------
    nominal : str
        Nominal size, e.g. ``"1x6"``, or the size label of round stock, e.g.
        ``"log 5"``.
    grade : str, optional
        Grade as the supplier names it, default ``"STK"``.  Round stock is
        usually ungraded, so an empty string is normal there.
    profile : str, optional
        How the stock is worked, exactly as ``stock.yaml`` spells it, default
        ``"rough sawn"``.
    actual_in : tuple[float, float] or None, optional
        The stock's real (thickness, width) in inches, where the supplier
        publishes it.  Neither table applies then: AVO's panel rail is "2" x
        3" S2S", which is not the dressed answer for a 2x3 and not a rough
        one either — it is simply what they mill it to, and a catalogue that
        states the section should be believed over a table that guesses it.
    diameter_in : float or None, optional
        Diameter of round stock, in inches.  Setting it makes this a **pole**:
        sized from the diameter rather than from a nominal-size table, bought
        by the foot as the round thing it is, and modelled as a cylinder.
        Round stock is graded in ranges — a "4 to 5 inch" post — so this is
        the size to design to and not a promise about any one stick.

    Raises
    ------
    ValueError
        If the nominal size is not one this toolkit can size.
    """

    nominal: str
    grade: str = "STK"
    profile: str = "rough sawn"
    actual_in: tuple[float, float] | None = None
    diameter_in: float | None = None

    @property
    def round(self) -> bool:
        """``True`` if this is round stock bought round."""
        return self.diameter_in is not None

    @property
    def rough(self) -> bool:
        """``True`` if this is rough sawn stock, and therefore full dimension."""
        return "rough sawn" in self.profile

    @property
    def thickness(self) -> float:
        """Thickness, mm."""
        return self._dims()[0]

    @property
    def width(self) -> float:
        """Width across the face — what the board measures, mm."""
        return self._dims()[1]

    @property
    def milled(self) -> bool:
        """``True`` if the face is worked so that it covers less than it measures."""
        return (self.nominal, self.profile) in ASSUMED_COVERAGE_IN

    @property
    def covers(self) -> float:
        """Width one board covers when butted to its neighbour, mm.

        The same as :attr:`width` for a square-edged board.  Less for anything
        milled to interlock, and that difference is assumed rather than
        published — see :data:`ASSUMED_COVERAGE_IN`.
        """
        assumed = ASSUMED_COVERAGE_IN.get((self.nominal, self.profile))
        return self.width if assumed is None else inches(assumed)

    @property
    def label(self) -> str:
        """Name this choice the way ``stock.yaml`` names the entry."""
        label = f"{self.nominal} {self.profile}" if self.profile else self.nominal
        return f"{label} ({self.grade})" if self.grade else label

    def entry(self, inventory: Inventory, species: str = "white_cedar"):
        """Return the :class:`~woodshop.inventory.DimensionalStock` this buys.

        Parameters
        ----------
        inventory : Inventory
            Stock to look it up in.
        species : str, optional
            Species, default ``"white_cedar"``.

        Returns
        -------
        DimensionalStock
            The one matching entry.

        Raises
        ------
        KeyError
            If nothing matches, or if more than one entry does.
        """
        return inventory.dimensional_for(
            species, self.nominal, grade=self.grade or None, profile=self.profile or None
        )

    def _dims(self) -> tuple[float, float]:
        """Return (thickness, width) in mm, from the table this profile lives in."""
        if self.actual_in is not None:
            return inches(self.actual_in[0]), inches(self.actual_in[1])
        if self.diameter_in is not None:
            # A log has no nominal-size table to look up: it is as round as it
            # is, and the square it fits inside is the diameter both ways.
            return inches(self.diameter_in), inches(self.diameter_in)
        sizes = rough_dimensions_mm if self.rough else actual_dimensions_mm
        try:
            thickness, width = sizes(self.nominal)
        except KeyError as exc:
            raise ValueError(
                f"{self.nominal!r} is not a size this toolkit can dress; add it "
                "to lumber.NOMINAL_TO_ACTUAL or specify rough sawn stock"
            ) from exc
        return float(thickness.magnitude), float(width.magnitude)


@dataclass(frozen=True)
class Span:
    """One gap between two adjacent posts, and what fills it.

    Parameters
    ----------
    kind : str
        ``"panel"`` for fence infill, ``"gate"`` for an opening a leaf hangs
        in.
    x0, x1 : float
        Post centres bounding the span, in mm along the run.
    """

    kind: str
    x0: float
    x1: float

    @property
    def length(self) -> float:
        """Post centre to post centre, mm."""
        return self.x1 - self.x0


@dataclass(frozen=True)
class PostPlan:
    """One post: where it stands, how big it is, and how deep it goes.

    Parameters
    ----------
    x : float
        Centre of the post along the run, mm.
    nominal : str
        Nominal size, e.g. ``"4x4"``.
    size : float
        Actual (rough sawn) face dimension, mm.
    embedment : float
        Depth below grade, mm.
    length : float
        Overall length of the stick, mm.
    is_gate_post : bool
        ``True`` if a gate hangs on or latches to it.
    """

    x: float
    nominal: str
    size: float
    embedment: float
    length: float
    is_gate_post: bool


@dataclass(frozen=True)
class BoardRun:
    """A row of boards across a stretch of fence, and the gap it works out at.

    Parameters
    ----------
    count : int
        Boards in the row.
    gap : float
        Gap between adjacent boards, mm.  Zero for stock milled to interlock,
        which has no gap to set.
    cover : float
        Length the row spans, mm.
    last_width : float or None
        Width the final board is ripped to, mm, where the row cannot be made
        of whole boards.  ``None`` when every board is full width, which is
        the case whenever a gap exists to absorb the remainder.
    """

    count: int
    gap: float
    cover: float
    last_width: float | None = None

    @property
    def full_boards(self) -> int:
        """Boards in the row that are not ripped."""
        return self.count - 1 if self.last_width is not None else self.count


#: What fills each role when the caller does not say, by style.
#:
#: A log fence is a different set of materials, not a different arrangement of
#: the same ones, which is why this is a table rather than four more defaults
#: with conditionals hung off them.  The gate frame stays sawn in every style:
#: see :meth:`CedarFence._leaf`.
DEFAULT_STOCK: dict[str, StockChoice] = {
    "board": StockChoice("1x6"),
    "rail": StockChoice("2x4"),
    "post": StockChoice("4x4"),
    "gate_post": StockChoice("6x6"),
    "gate_frame": StockChoice("2x4"),
}

#: What a log fence uses instead.  Peeled round cedar, ungraded, by the foot.
LOG_STOCK: dict[str, StockChoice] = {
    "post": StockChoice("log 5", grade="", profile="round post", diameter_in=5.0),
    "rail": StockChoice("log 4", grade="", profile="round rail", diameter_in=4.0),
    "gate_post": StockChoice(
        "log 6", grade="", profile="round post", diameter_in=6.0
    ),
}

#: Rail lengths AVO's post and rail system comes in, in feet.  The bay is the
#: rail, exactly as the bay is the panel on the other side of their catalogue.
POST_AND_RAIL_LENGTHS_FT: tuple[float, ...] = (8.0, 10.0)

#: Rails they offer: square cedar 4", round cedar 3", 3-1/2" or 4", or
#: hardwood split rail.  Round rails pair with round posts and square with
#: square, which is their own advice and the reason this is a table rather
#: than two free choices.
POST_AND_RAIL_RAILS: dict[str, StockChoice] = {
    "round_4": StockChoice("log 4", grade="", profile="round rail", diameter_in=4.0),
    "square_4": StockChoice("4x4", grade="STK", profile="rough sawn"),
}

#: The mesh a log fence is built around: the material key its parts carry, and
#: the key ``stock.yaml`` files the roll under.
MESH_MATERIAL: str = "steel_mesh_black"

#: Thickness the mesh is modelled at, mm (1/8").
#:
#: A 2" x 4" mesh is 90% air, and drawing every wire would be four hundred
#: solids a bay for a picture that reads as a grey haze anyway.  It is modelled
#: as a thin sheet standing in for the mesh, which is honest about the
#: envelope and silent about the pattern — see the finding that says so.
MESH_THICKNESS_MM: float = 3.175


@dataclass(frozen=True)
class MeshPlan:
    """What mesh a fence needs, in the unit mesh is actually sold in.

    Mesh is not lumber and it is not sheet goods: it comes off a roll of a
    fixed height, and the only question is how many feet of fence there are to
    cover.  Area is the wrong unit to buy in — a 400 sq ft roll does not cover
    400 sq ft of a 4 ft fence in any useful sense unless it is exactly 4 ft
    tall, which is the assumption this plan checks rather than makes.

    Parameters
    ----------
    stock : UnitStock or None
        The inventory entry, or ``None`` if nothing matching is stocked.
    run_ft : float
        Lineal feet of fence to cover, before allowance.
    allowance : float
        Fraction added for trimming and for the wrap onto each post.
    height : float
        Height of mesh on the fence, mm.
    roll_height : float
        Height of the roll it comes off, mm.
    """

    stock: Any
    run_ft: float
    height: float
    roll_height: float
    allowance: float = 0.05

    @property
    def buy_ft(self) -> float:
        """Lineal feet of mesh to buy."""
        return self.run_ft * (1.0 + self.allowance)

    @property
    def roll_length_ft(self) -> float | None:
        """How long one roll is, from its area and the height it is sold at.

        ``None`` when the entry publishes no coverage — which is a fact about
        the entry, not a reason to guess a hundred feet.
        """
        if self.stock is None or self.stock.coverage_sqft is None:
            return None
        return self.stock.coverage_sqft / (self.roll_height / FT)

    @property
    def rolls(self) -> int | None:
        """Rolls to buy, or ``None`` if the roll length is unpublished."""
        length = self.roll_length_ft
        if not length:
            return None
        return int(-(-self.buy_ft // length))  # ceil

    @property
    def price_line(self) -> PriceLine | None:
        """Rolls times the rate, with its provenance — ``None`` if unpriced."""
        if self.stock is None or self.stock.price is None or self.rolls is None:
            return None
        return self.stock.price_line(self.rolls)

    @property
    def cost_summary(self) -> CostSummary:
        """The mesh line, or the reason there is not one."""
        line = self.price_line
        if line is not None:
            return CostSummary.of([line])
        label = "mesh" if self.stock is None else self.stock.stock_label
        return CostSummary.of((), [label])

    def to_text(self) -> str:
        """Render the plan as a couple of lines of plain text."""
        if self.stock is None:
            return (
                f"  (!) {self.run_ft:.0f} ft of fence wants mesh, and no mesh "
                "is stocked in stock.yaml"
            )
        rolls = (
            "roll length not published, so this is feet and not rolls"
            if self.rolls is None
            else f"{self.rolls} roll(s) of {self.roll_length_ft:.0f} ft"
        )
        cost = "" if self.price_line is None else f", {self.price_line.to_text()}"
        lines = [
            f"  {self.stock.stock_label:<52s} {self.buy_ft:>6.0f} LF  "
            f"({self.run_ft:.0f} LF of fence + "
            f"{self.allowance * 100:.0f}% trim and wrap){cost}",
            f"  {'':<52s} {rolls}",
        ]
        if self.price_line is None:
            lines.append(
                f"  (!) {self.stock.stock_label} has no price in stock.yaml — "
                "it is missing from the total, not free"
            )
        return "\n".join(lines)


@dataclass
class CedarFence:
    """A parametric cedar fence: a run, some gates, and one of three infills.

    Parameters
    ----------
    style : str, optional
        One of :data:`STYLES`, default ``"board_on_board"``.
    run_ft : float, optional
        Total length of plain fence, post centre to post centre, default 38.
    height_in : float, optional
        Finished height above grade — the top of the boards and, unless
        *post_proud_in* says otherwise, the top of the posts.  Default 48.
    gates : int, optional
        How many gate sections, default 2.
    gate_section_ft : float, optional
        Length of one gate section on centre, default 10.
    gate_leaves : int, optional
        ``2`` for a pair of leaves filling the opening (the usual answer for a
        10 ft section), or ``1`` for a single walk gate with a fixed panel
        beside it.
    walk_gate_in : float, optional
        On-centre width of the opening when *gate_leaves* is 1, default 48.
    max_bay_ft : float, optional
        Longest bay allowed between line posts, default 8.  Forced down to
        *max_horizontal_bay_ft* for the horizontal style.
    max_horizontal_bay_ft : float, optional
        Longest bay allowed when the boards span between posts, default 6.
    bay_ft : float or None, optional
        Fix the bay at this length instead of dividing the run evenly.  For a
        system bought in fixed lengths — AVO's rails come in 8 and 10 ft —
        the bay *is* the stick, and a run that does not divide by it ends in
        a short bay rather than in six slightly shorter ones.
    embedment_in : float, optional
        Depth of a line post below grade, default 48.
    gate_post_extra_in : float, optional
        Extra depth for a gate post, default 6.
    post_proud_in : float, optional
        How far the post tops stand above the boards, default 0 (cut flush).
    ground_clearance_in : float, optional
        Gap between grade and the bottom of the boards, default 2.
    gate_clearance_in : float, optional
        Gap between grade and the bottom of a gate leaf, default 3.
    picket_gap_in : float, optional
        Target gap between boards in the ``picket`` style, default 1.75.
    overlap_in : float, optional
        Target lap of an over board onto its neighbours in the
        ``board_on_board`` style, default 1.
    horizontal_gap_in : float, optional
        Target gap between courses in the ``horizontal`` style, default 0.5.
    board, rail, post, gate_post, gate_frame : StockChoice, optional
        Which inventory entry fills each role.  ``None`` takes the default for
        the style — rough sawn STK in 1x6, 2x4, 4x4 and 6x6 for the board
        styles, peeled logs for ``log_and_mesh``.  A choice names a grade and
        a profile as well as a size, and that is not decoration: rough sawn
        1x6 in STK is $2.30/LF and the same board in low grade is $1.30, so a
        design that does not name them cannot be priced to better than 77%.
        See :func:`variants` for every entry that will serve.
    log_rails : int, optional
        How many rails a log-and-mesh bay carries, default 3.  The mesh is
        stapled to them, so this is a question about how much unsupported
        mesh is acceptable rather than about strength.
    tenon_in, tenon_diameter_in : float, optional
        Length and diameter of the round tenon on each end of a log rail,
        default 3" long and 2" across, into a bored post.
    mesh_roll_height_in : float, optional
        Height of the roll the mesh comes off, default 48.
    mesh_material : str, optional
        Material key for the mesh, default :data:`MESH_MATERIAL`.
    species : str, optional
        Species, default ``"white_cedar"``.
    inventory : Inventory, optional
        Stock to price against.  ``None`` loads ``stock.yaml``.

    Raises
    ------
    ValueError
        If *style* is not one of :data:`STYLES`, if *gate_leaves* is not 1 or
        2, or if a gate section is too short to hold the opening asked of it.
    """

    style: str = "board_on_board"
    run_ft: float = 38.0
    height_in: float = 48.0
    gates: int = 2
    gate_section_ft: float = 10.0
    gate_leaves: int = 2
    walk_gate_in: float = 48.0
    max_bay_ft: float = RECOMMENDED_MAX_BAY_FT
    max_horizontal_bay_ft: float = RECOMMENDED_MAX_HORIZONTAL_BAY_FT
    bay_ft: float | None = None
    embedment_in: float = FROST_DEPTH_IN
    gate_post_extra_in: float = 6.0
    post_proud_in: float = 0.0
    ground_clearance_in: float = 2.0
    gate_clearance_in: float = 3.0
    picket_gap_in: float = 1.75
    overlap_in: float = 1.0
    horizontal_gap_in: float = 0.5
    hinge_gap_in: float = 0.375
    leaf_gap_in: float = 0.75
    board: StockChoice | None = None
    rail: StockChoice | None = None
    post: StockChoice | None = None
    gate_post: StockChoice | None = None
    gate_frame: StockChoice | None = None
    log_rails: int = 3
    tenon_in: float = 3.0
    tenon_diameter_in: float = 2.0
    mesh_roll_height_in: float = 48.0
    mesh_material: str = MESH_MATERIAL
    species: str = "white_cedar"
    inventory: Inventory = field(default_factory=Inventory.load)

    def __post_init__(self) -> None:
        """Fill in the stock this style implies, and reject what cannot be built."""
        if self.style not in STYLES:
            raise ValueError(f"style must be one of {STYLES}, got {self.style!r}")
        defaults = dict(DEFAULT_STOCK)
        if self.style == "log_and_mesh":
            defaults.update(LOG_STOCK)
        for role, choice in defaults.items():
            if getattr(self, role) is None:
                setattr(self, role, choice)
        if self.style == "log_and_mesh" and self.log_rails < 2:
            raise ValueError(
                "a log-and-mesh bay needs at least a top and a bottom rail to "
                f"staple the mesh to, got log_rails={self.log_rails!r}"
            )
        if self.gate_leaves not in (1, 2):
            raise ValueError(
                f"gate_leaves must be 1 or 2, got {self.gate_leaves!r}: a gate "
                "with three leaves is a folding screen"
            )
        if self.board is not None and self.board.milled and (
            self.style == "board_on_board"
        ):
            raise ValueError(
                f"{self.board.label} interlocks, so it cannot be laid board on "
                "board — there is nothing to lap over, and the second course "
                "would have no gap to cover; use picket, which butts milled "
                "stock into a solid fence, or horizontal"
            )
        if self.gate_leaves == 1 and inches(self.walk_gate_in) >= self.gate_section:
            raise ValueError(
                f"a {self.walk_gate_in:g}\" walk gate does not fit in a "
                f"{self.gate_section_ft:g} ft section with a panel beside it"
            )

    # ------------------------------------------------------------------
    # Stock sizes.  Rough sawn, so full nominal dimension — a rough 1x6 is
    # about a full 1" x 6" where the dressed board of that name is 3/4" x
    # 5-1/2".  Laid out from the dressed table this fence would be short a
    # board in every bay.
    # ------------------------------------------------------------------

    @property
    def board_t(self) -> float:
        """Board thickness, mm."""
        return self.board.thickness

    @property
    def board_w(self) -> float:
        """Width one board covers, mm.

        What it *covers*, not what it measures, because that is the number the
        layout runs on.  They differ only for stock milled to interlock, where
        the tongue lives inside the next board.
        """
        return self.board.covers

    @property
    def rail_t(self) -> float:
        """Rail thickness, mm — across the fence."""
        return self.rail.thickness

    @property
    def rail_w(self) -> float:
        """Rail width, mm — vertical, which is the dimension that carries."""
        return self.rail.width

    @property
    def frame_t(self) -> float:
        """Gate frame thickness, mm — across the leaf."""
        return self.gate_frame.thickness

    @property
    def frame_w(self) -> float:
        """Gate frame width, mm — in the plane of the leaf."""
        return self.gate_frame.width

    @property
    def post_size(self) -> float:
        """Line post face dimension, mm.

        The diameter for a log, which is the square it fits inside — the right
        answer for where the boards stop and the wrong one for what it costs.
        """
        return self.post.width

    @property
    def gate_post_size(self) -> float:
        """Gate post face dimension, mm."""
        return self.gate_post.width

    # ------------------------------------------------------------------
    # Derived dimensions
    # ------------------------------------------------------------------

    @property
    def height(self) -> float:
        """Finished height above grade, mm."""
        return inches(self.height_in)

    @property
    def run(self) -> float:
        """Length of plain fence, mm."""
        return self.run_ft * FT

    @property
    def gate_section(self) -> float:
        """Length of one gate section on centre, mm."""
        return self.gate_section_ft * FT

    @property
    def overall_length(self) -> float:
        """Run plus gate sections, post centre to post centre, mm."""
        return self.run + self.gates * self.gate_section

    @property
    def max_bay(self) -> float:
        """Longest bay this style allows, mm."""
        limit = (
            self.max_horizontal_bay_ft
            if self.style == "horizontal"
            else self.max_bay_ft
        )
        return limit * FT

    @property
    def recommended_max_bay(self) -> float:
        """Longest bay this style is good for, mm, whatever *max_bay_ft* says."""
        limit = (
            RECOMMENDED_MAX_HORIZONTAL_BAY_FT
            if self.style == "horizontal"
            else RECOMMENDED_MAX_BAY_FT
        )
        return limit * FT

    @property
    def post_length(self) -> float:
        """Length of a line post, mm."""
        return inches(self.embedment_in + self.height_in + self.post_proud_in)

    @property
    def gate_post_length(self) -> float:
        """Length of a gate post, mm."""
        return self.post_length + inches(self.gate_post_extra_in)

    @property
    def mesh_bottom(self) -> float:
        """Where the mesh starts, mm above grade.

        Boards are held clear of the ground so they do not wick water out of
        it.  Mesh is not: it is there to stop a dog, and a dog goes under a
        2" gap without breaking stride.  So the mesh runs to grade, and the
        finding tells you to bury an apron of it.
        """
        return 0.0 if self.style == "log_and_mesh" else inches(
            self.ground_clearance_in
        )

    @property
    def mesh_height(self) -> float:
        """Height of mesh on the fence, mm — from where it starts to the top."""
        return self.height - self.mesh_bottom

    @property
    def board_length(self) -> float:
        """Length of a vertical board, mm — grade clearance to fence top."""
        return self.height - inches(self.ground_clearance_in)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def spans(self) -> list[Span]:
        """Return every span between adjacent posts, left to right.

        The run is split evenly around the gate sections, so two gates in
        38 ft of fence give 19 ft, a gate, 19 ft, a gate.  Where the gates
        actually fall is a question about the site, and it changes nothing in
        the cut list except which posts are 6x6 — but a drawing has to put
        them somewhere, and the middle of the run is a more honest somewhere
        than the end.

        Returns
        -------
        list[Span]
            Panels and gate openings, in order along the run.
        """
        segments: list[tuple[str, float]] = []
        if self.gates:
            share = self.run / self.gates
            for _ in range(self.gates):
                segments.append(("fence", share))
                segments.append(("gate", self.gate_section))
        else:
            segments.append(("fence", self.run))

        spans: list[Span] = []
        x = 0.0
        for kind, length in segments:
            if kind == "fence" and self.bay_ft:
                # Bought in fixed lengths: whole bays, then whatever is left.
                bay = self.bay_ft * FT
                full = int(length // bay)
                for i in range(full):
                    spans.append(Span("panel", x + i * bay, x + (i + 1) * bay))
                remainder = length - full * bay
                if remainder > 1.0:
                    spans.append(
                        Span("panel", x + full * bay, x + full * bay + remainder)
                    )
            elif kind == "fence":
                n_bays = max(1, math.ceil(length / self.max_bay - 1e-9))
                bay = length / n_bays
                for i in range(n_bays):
                    spans.append(Span("panel", x + i * bay, x + (i + 1) * bay))
            elif self.gate_leaves == 2:
                spans.append(Span("gate", x, x + length))
            else:
                # A single walk gate does not fill a 10 ft section, so the
                # section is an opening plus a fixed panel, with a post
                # between them.
                opening = inches(self.walk_gate_in)
                spans.append(Span("gate", x, x + opening))
                spans.append(Span("panel", x + opening, x + length))
            x += length
        return spans

    def posts(self) -> list[PostPlan]:
        """Return every post, left to right.

        A post is a 6x6 gate post when a gate hangs on it or latches to it,
        and a 4x4 line post otherwise.  Nothing else distinguishes them: the
        holes are the same size, and the two extra inches of depth on a gate
        post cost one shovelful.
        """
        spans = self.spans()
        boundaries = [spans[0].x0] + [s.x1 for s in spans]
        gate_x = {(s.x0, s.x1) for s in spans if s.kind == "gate"}
        flat = {x for pair in gate_x for x in pair}

        out: list[PostPlan] = []
        for x in boundaries:
            is_gate_post = any(abs(x - gx) < 1e-6 for gx in flat)
            out.append(
                PostPlan(
                    x=x,
                    nominal=(
                        self.gate_post.nominal if is_gate_post else self.post.nominal
                    ),
                    size=self.gate_post_size if is_gate_post else self.post_size,
                    embedment=inches(
                        self.embedment_in
                        + (self.gate_post_extra_in if is_gate_post else 0.0)
                    ),
                    length=(
                        self.gate_post_length if is_gate_post else self.post_length
                    ),
                    is_gate_post=is_gate_post,
                )
            )
        return out

    def panel_groups(self) -> list[list[Span]]:
        """Return runs of consecutive panels, which is what boards cover.

        Boards are nailed to the rails and run *past* the line posts, so the
        row that has to divide evenly is the whole stretch between gates, not
        one bay.  Dividing bay by bay is how a fence ends up with a 1" sliver
        against every second post.
        """
        groups: list[list[Span]] = []
        current: list[Span] = []
        for span in self.spans():
            if span.kind == "panel":
                current.append(span)
            elif current:
                groups.append(current)
                current = []
        if current:
            groups.append(current)
        return groups

    def edge_x(self, x: float, is_left: bool) -> float:
        """Return where boards stop at the post standing at *x*, in mm.

        Three cases, and they are the difference between a fence that looks
        built and one that looks assembled:

        * **At either end of the run** the boards carry past the post to its
          outside face, so no post shows at the end of the line.
        * **At a gate post** they stop at its near face, leaving the hinge and
          latch faces clear for hardware.
        * **At a line post** they run straight past, and a horizontal board's
          joint lands on the post centre where the next board meets it.

        Parameters
        ----------
        x : float
            Post centre, mm along the run.
        is_left : bool
            Whether this is the left-hand end of the stretch being covered.

        Returns
        -------
        float
            Where the boards stop, mm along the run.
        """
        post = self._post_at(x)
        if abs(x) < 1e-6:
            return x - post.size / 2
        if abs(x - self.overall_length) < 1e-6:
            return x + post.size / 2
        if post.is_gate_post:
            return x + post.size / 2 if is_left else x - post.size / 2
        return x

    def _post_at(self, x: float) -> PostPlan:
        """Return the post standing at *x*."""
        return {round(p.x, 6): p for p in self.posts()}[round(x, 6)]

    def cover_of(self, group: list[Span]) -> tuple[float, float]:
        """Return ``(x_start, cover)`` for the boards over a run of panels."""
        x_start = self.edge_x(group[0].x0, is_left=True)
        return x_start, self.edge_x(group[-1].x1, is_left=False) - x_start

    def board_run(self, cover: float, target_gap: float) -> BoardRun:
        """Fit whole boards across *cover* and report the gap that results.

        Parameters
        ----------
        cover : float
            Length to fill, mm.
        target_gap : float
            The gap you would like between boards, mm.

        Returns
        -------
        BoardRun
            Board count and the actual gap.  The count is chosen to put the
            gap as close to *target_gap* as whole boards allow, and the gap
            absorbs the remainder — which is why a fence laid out this way has
            no sliver at the end and a fence laid out by dividing the cover by
            a fixed pitch always does.

            Milled stock is the exception, and it is not a gap problem: a
            tongue and groove board has nowhere to put a remainder, so the
            boards butt at their published coverage and the last one in each
            stretch is ripped narrow.  That is how the stuff is laid, and the
            rip is reported rather than hidden.
        """
        if self.board.milled:
            count = max(1, math.ceil(cover / self.board_w - 1e-9))
            last = cover - (count - 1) * self.board_w
            return BoardRun(
                count=count,
                gap=0.0,
                cover=cover,
                last_width=None if abs(last - self.board_w) < 0.5 else last,
            )
        pitch = self.board_w + target_gap
        count = max(2, round((cover + target_gap) / pitch))
        gap = (cover - count * self.board_w) / (count - 1)
        return BoardRun(count=count, gap=gap, cover=cover)

    @property
    def target_gap(self) -> float:
        """The gap the infill is laid out to, mm, before it is fitted.

        For ``picket`` it is the gap itself.  For ``board_on_board`` it is what
        the under course is spaced at, which is the board width less the lap
        each side — the gap is a consequence of the lap, not a choice.
        """
        if self.style == "picket":
            return inches(self.picket_gap_in)
        if self.style == "horizontal":
            return inches(self.horizontal_gap_in)
        return self.board_w - 2 * inches(self.overlap_in)

    def course_rows(self) -> BoardRun:
        """Fit horizontal courses between the ground clearance and the top."""
        cover = self.height - inches(self.ground_clearance_in)
        return self.board_run(cover, inches(self.horizontal_gap_in))

    # ------------------------------------------------------------------
    # Gates
    # ------------------------------------------------------------------

    @property
    def gate_openings(self) -> list[Span]:
        """Every gate opening, in order."""
        return [s for s in self.spans() if s.kind == "gate"]

    def clear_opening(self, span: Span) -> float:
        """Clear width between the gate posts of *span*, mm."""
        return span.length - self.gate_post_size

    def leaf_width(self, span: Span) -> float:
        """Width of one leaf in *span*, mm.

        The clear opening less a hinge gap at each jamb and, for a pair, the
        gap down the middle where the drop rod goes.
        """
        clear = self.clear_opening(span)
        gaps = 2 * inches(self.hinge_gap_in) + (self.gate_leaves - 1) * inches(
            self.leaf_gap_in
        )
        return (clear - gaps) / self.gate_leaves

    def leaf_infill(self, span: Span) -> BoardRun:
        """Return the board layout across one leaf in *span*.

        A leaf is laid out on its own rather than continuing the fence's
        rhythm, because a gate has two edges that both have to land on a whole
        board.  What that costs is a spacing that does not quite match the
        fence beside it, which the checks measure rather than leave to be
        noticed on site.
        """
        if self.style == "horizontal":
            return self.board_run(self.leaf_height, self.target_gap)
        return self.board_run(self.leaf_width(span), self.target_gap)

    @property
    def leaf_height(self) -> float:
        """Height of a gate leaf, mm — top flush with the fence."""
        return self.height - inches(self.gate_clearance_in)

    # ------------------------------------------------------------------
    # Assembly
    # ------------------------------------------------------------------

    def build(self) -> Compound:
        """Build the fence as a positioned build123d assembly.

        Grade is ``z = 0``; the posts run below it.  The front faces of every
        post are coplanar at ``y = 0`` with the boards in front of them, which
        is what makes a 6x6 gate post and a 4x4 line post read as one line
        rather than as a 1" step.

        Returns
        -------
        build123d.Compound
            Posts, rails, boards and gates, positioned.
        """
        children: list[object] = []
        children.extend(self._posts())
        for group in self.panel_groups():
            children.extend(self._panel_group(group))
        for span in self.gate_openings:
            children.extend(self._gate(span))
        return Compound(children=children, label=f"cedar_fence_{self.style}")

    def _stock(
        self, choice: StockChoice, covers_mm: float | None = None, **kwargs: object
    ) -> dict[str, object]:
        """Return the keyword arguments a part cut from *choice* needs.

        Parameters
        ----------
        choice : StockChoice
            The entry this part is cut from.
        covers_mm : float, optional
            Override the covering width — used for the last board in a run of
            milled stock, which is ripped narrow to finish the stretch.
        **kwargs
            Anything else to pass to :class:`~woodshop.parts.Board`.
        """
        covers = covers_mm
        if covers is None and choice.milled:
            covers = choice.covers
        return dict(
            material=self.species,
            nominal=choice.nominal,
            rough=choice.rough,
            grade=choice.grade,
            stock_profile=choice.profile,
            covers_mm=covers,
            **kwargs,
        )

    def _posts(self) -> list[object]:
        """Return every post, positioned with its front face on ``y = 0``."""
        out: list[object] = []
        for post in self.posts():
            choice = self.gate_post if post.is_gate_post else self.post
            notes = (
                f"{post.embedment / IN:.0f}\" in the ground, "
                f"{(post.length - post.embedment) / IN:.0f}\" above grade"
                + (
                    "; set in a gravel-drained hole and plumbed twice — a "
                    "gate post that leans 1° drops its latch 1\""
                    if post.is_gate_post
                    else ""
                )
            )
            label = "gate_post" if post.is_gate_post else "line_post"
            solid = self._post_solid(choice, post.length, label, notes)
            z = post.length / 2 - post.embedment
            out.append(Pos(post.x, -post.size / 2, z) * solid)
        return out

    def _post_solid(
        self, choice: StockChoice, length: float, label: str, notes: str
    ) -> object:
        """Return one post standing on its own axis, round or square as it is.

        The two kinds of stock arrive at +Z from opposite directions.  A
        :class:`~woodshop.parts.Pole` is *born* on the +Z axis, because that is
        where a turned part's axis lives; a :class:`Board` is born along +X and
        has to be stood up.  Returning both upright keeps that difference here
        rather than in the caller.
        """
        if choice.round:
            return Pole(
                length_mm=length,
                diameter_mm=choice.width,
                material=self.species,
                label=label,
                nominal=choice.nominal,
                grade=choice.grade,
                stock_profile=choice.profile,
                notes=notes,
            )
        return UPRIGHT_POST * Board(
            length_mm=length,
            label=label,
            notes=notes,
            **self._stock(choice),
        )

    def _panel_group(self, group: list[Span]) -> list[object]:
        """Return the rails and infill filling a run of panels."""
        out: list[object] = []
        if self.style == "log_and_mesh":
            return self._log_and_mesh(group)
        if self.style == "horizontal":
            out.extend(self._horizontal_courses(group))
            return out

        out.extend(self._rails(group))
        x_start, cover = self.cover_of(group)
        run = self.board_run(
            cover,
            self.target_gap,
        )
        pitch = self.board_w + run.gap
        z = inches(self.ground_clearance_in) + self.board_length / 2

        for i in range(run.count):
            width = self._board_width(run, i)
            x = x_start + self._board_offset(run, i, pitch) + width / 2
            out.append(
                Pos(x, self.board_t / 2, z)
                * UPRIGHT
                * Board(
                    length_mm=self.board_length,
                    label="board" if self.style == "picket" else "under_board",
                    notes=self._board_note(run, i),
                    **self._stock(self.board, covers_mm=width),
                )
            )
        if self.style == "board_on_board":
            for i in range(run.count - 1):
                x = x_start + self.board_w + run.gap / 2 + i * pitch
                out.append(
                    Pos(x, self.board_t * 1.5, z)
                    * UPRIGHT
                    * Board(
                        length_mm=self.board_length,
                        label="over_board",
                        notes=(
                            "centred on the gap, lapping "
                            f"{mm_to_fractional_inch((self.board_w - run.gap) / 2, 32)}"
                            " each side"
                        ),
                        **self._stock(self.board),
                    )
                )
        return out

    def _board_width(self, run: BoardRun, index: int) -> float:
        """Return the width of board *index* in *run*, ripped or full."""
        if run.last_width is not None and index == run.count - 1:
            return run.last_width
        return self.board_w

    def _board_offset(self, run: BoardRun, index: int, pitch: float) -> float:
        """Return the distance from the start of the row to board *index*."""
        return index * pitch

    def _board_note(self, run: BoardRun, index: int) -> str:
        """Return the cut-list note for board *index* in *run*."""
        if run.last_width is not None and index == run.count - 1:
            return (
                "ripped to "
                f"{mm_to_fractional_inch(run.last_width, 32)} to finish the "
                "stretch — the tongue edge comes off, so plan it for the end "
                "that meets a post"
            )
        if self.board.milled:
            return (
                f"butted, covering {mm_to_fractional_inch(self.board_w, 32)} "
                f"of a {mm_to_fractional_inch(self.board.width)} face"
            )
        return (
            f"{mm_to_fractional_inch(run.gap, 32)} gap, "
            f"{self.ground_clearance_in:g}\" off the ground"
        )

    def _log_and_mesh(self, group: list[Span]) -> list[object]:
        """Return the log rails and the mesh filling a run of panels.

        Each bay is its own frame and its own sheet of mesh: a log rail is
        tenoned into the post it lands on, and mesh is stapled to the rails
        rather than run past them.  Nothing here crosses a post, which is the
        opposite of every board style in this file.
        """
        out: list[object] = []
        posts = {round(p.x, 6): p for p in self.posts()}
        for span in group:
            left, right = posts[round(span.x0, 6)], posts[round(span.x1, 6)]
            clear = span.length - left.size / 2 - right.size / 2
            centre = (span.x0 + span.x1) / 2
            rail_y = -self.post_size / 2

            for z, where in self._log_rail_heights():
                out.append(
                    Pos(centre, rail_y, z)
                    * POLE_ALONG_RUN
                    * Pole(
                        # A log rail is tenoned into a hole bored in the post,
                        # so the stick is longer than the gap it crosses.
                        length_mm=clear + 2 * inches(self.tenon_in),
                        diameter_mm=self.rail.width,
                        material=self.species,
                        label="log_rail",
                        nominal=self.rail.nominal,
                        grade=self.rail.grade,
                        stock_profile=self.rail.profile,
                        notes=(
                            f"{where} rail; each end turned down to a "
                            f"{self.tenon_diameter_in:g}\" round tenon "
                            f"{self.tenon_in:g}\" long, into a bored post — "
                            "bore the holes before the posts go in the ground"
                        ),
                    )
                )

            # The mesh goes on the far face of the rails, so the fence shows
            # its logs from the front and the mesh is what the dog meets.
            out.append(
                Pos(
                    centre,
                    rail_y - self.rail.width / 2 - MESH_THICKNESS_MM / 2,
                    self.mesh_bottom + self.mesh_height / 2,
                )
                * ALONG_RUN
                * Panel(
                    length_mm=clear,
                    width_mm=self.mesh_height,
                    thickness_mm=MESH_THICKNESS_MM,
                    material=self.mesh_material,
                    label="mesh",
                    grain_direction="none",
                    notes=(
                        f"{mm_to_fractional_inch(self.mesh_height)} off a "
                        f"{self.mesh_roll_height_in:g}\" roll, stapled to the "
                        "far face of every rail and trapped under a batten at "
                        "the posts, so the logs show from the front; drawn as "
                        "a sheet, and it is 2\" x 4\" mesh"
                    ),
                )
            )
        return out

    def _log_rail_heights(self) -> list[tuple[float, str]]:
        """Return the centre height and name of each log rail, bottom up.

        The top and bottom rails sit where the mesh ends, because their job is
        to give it an edge to be stapled to.  Anything between them is there
        to stop the middle of the sheet bellying out when a dog leans on it.
        """
        radius = self.rail.width / 2
        bottom = inches(self.ground_clearance_in) + radius
        top = self.height - radius
        # The mesh hangs on the rails, so the bottom rail is where the mesh
        # stops being held: low enough that a dog cannot lift it.
        if self.log_rails == 2:
            return [(bottom, "bottom"), (top, "top")]
        step = (top - bottom) / (self.log_rails - 1)
        names = ["bottom"] + ["middle"] * (self.log_rails - 2) + ["top"]
        return [(bottom + i * step, names[i]) for i in range(self.log_rails)]

    def _rails(self, group: list[Span]) -> list[object]:
        """Return the two rails in each bay of *group*."""
        posts = {round(p.x, 6): p for p in self.posts()}
        out: list[object] = []
        for span in group:
            left, right = posts[round(span.x0, 6)], posts[round(span.x1, 6)]
            length = span.length - left.size / 2 - right.size / 2
            centre = (span.x0 + span.x1) / 2
            for z, where in self._rail_heights():
                out.append(
                    Pos(centre, -self.rail_t / 2, z)
                    * ALONG_RUN
                    * Board(
                        length_mm=length,
                        label="rail",
                        notes=(
                            f"{where} rail, cut to fit between posts; hang it "
                            "on galvanised rail brackets or toe-screw it — end "
                            "grain holds no screw"
                        ),
                        **self._stock(self.rail),
                    )
                )
        return out

    def _rail_heights(self) -> list[tuple[float, str]]:
        """Return the centre height and name of each rail."""
        return [
            (self.height - inches(6.0) - self.rail_w / 2, "top"),
            (inches(10.0), "bottom"),
        ]

    def _horizontal_courses(self, group: list[Span]) -> list[object]:
        """Return the horizontal boards spanning each bay of *group*."""
        rows = self.course_rows()
        pitch = self.board_w + rows.gap
        out: list[object] = []
        for span in group:
            # A board joint has to land on a post, so a board runs post centre
            # to post centre — except at the ends of the run and at a gate,
            # where `edge_x` says what happens instead.
            x0 = self.edge_x(span.x0, is_left=True)
            x1 = self.edge_x(span.x1, is_left=False)
            length = x1 - x0
            for row in range(rows.count):
                width = self._board_width(rows, row)
                z = inches(self.ground_clearance_in) + row * pitch + width / 2
                out.append(
                    Pos((x0 + x1) / 2, self.board_t / 2, z)
                    * ALONG_RUN
                    * Board(
                        length_mm=length,
                        label="course",
                        notes=(
                            "spans one bay, joints centred on the posts; "
                            + self._board_note(rows, row)
                        ),
                        **self._stock(self.board, covers_mm=width),
                    )
                )
        return out

    def _gate(self, span: Span) -> list[object]:
        """Return every leaf hanging in *span*."""
        out: list[object] = []
        clear_x0 = span.x0 + self.gate_post_size / 2
        width = self.leaf_width(span)
        x = clear_x0 + inches(self.hinge_gap_in)
        for leaf in range(self.gate_leaves):
            out.extend(self._leaf(x, width, hinged_left=leaf == 0))
            x += width + inches(self.leaf_gap_in)
        return out

    def _leaf(self, x0: float, width: float, hinged_left: bool) -> list[object]:
        """Return one gate leaf, its left edge at *x0*.

        The frame is a 2x4 rectangle with a diagonal in it.  The diagonal runs
        from the **bottom hinge corner up to the top latch corner**, which puts
        it in compression: a gate braced the other way hangs its far corner off
        a wooden strut in tension, and wood in tension across a screwed joint is
        a gate that sags in a season.  Wire braces run the other way for
        exactly the same reason.
        """
        out: list[object] = []
        z0 = inches(self.gate_clearance_in)
        height = self.leaf_height
        stile_w, stile_t = self.frame_w, self.frame_t

        for side in (0, 1):
            out.append(
                Pos(x0 + stile_w / 2 + side * (width - stile_w), -stile_t / 2, z0 + height / 2)
                * UPRIGHT
                * Board(
                    length_mm=height,
                    label="gate_stile",
                    notes="hinge stile" if side == 0 else "latch stile",
                    **self._stock(self.gate_frame),
                )
            )

        rail_length = width - 2 * stile_w
        for z, where in (
            (z0 + stile_w / 2, "bottom"),
            (z0 + height - stile_w / 2, "top"),
        ):
            out.append(
                Pos(x0 + width / 2, -stile_t / 2, z)
                * ALONG_RUN
                * Board(
                    length_mm=rail_length,
                    label="gate_rail",
                    notes=f"{where} rail, half-lapped into the stiles",
                    **self._stock(self.gate_frame),
                )
            )

        inner_h = height - 2 * stile_w
        brace_length = math.hypot(rail_length, inner_h)
        angle = math.degrees(math.atan2(inner_h, rail_length))
        # Rotate the upright brace into the plane of the leaf.  The sign puts
        # its foot at the hinge side, which is the whole point of the brace.
        tilt = (90.0 - angle) if hinged_left else -(90.0 - angle)
        out.append(
            Pos(x0 + width / 2, -stile_t / 2, z0 + height / 2)
            * Rotation(0, tilt, 0)
            * UPRIGHT
            * Board(
                length_mm=brace_length,
                label="gate_brace",
                notes=(
                    f"{angle:.0f}° from horizontal, foot at the "
                    f"{'hinge' if hinged_left else 'latch'} side, in "
                    "compression; mitre both ends to the frame"
                ),
                **self._stock(self.gate_frame),
            )
        )

        out.extend(self._leaf_infill(x0, width, z0, height))
        return out

    def _leaf_infill(
        self, x0: float, width: float, z0: float, height: float
    ) -> list[object]:
        """Return the infill on the face of one leaf."""
        out: list[object] = []
        if self.style == "log_and_mesh":
            return [
                Pos(x0 + width / 2, -self.frame_t / 2 - MESH_THICKNESS_MM / 2,
                    z0 + height / 2)
                * ALONG_RUN
                * Panel(
                    length_mm=width,
                    width_mm=height,
                    thickness_mm=MESH_THICKNESS_MM,
                    material=self.mesh_material,
                    label="gate_mesh",
                    grain_direction="none",
                    notes=(
                        "stapled to the leaf and trapped under a batten all "
                        "round — a cut mesh edge at hand height on a gate is "
                        "the one place this fence can draw blood"
                    ),
                )
            ]
        if self.style == "horizontal":
            rows = self.board_run(height, self.target_gap)
            pitch = self.board_w + rows.gap
            for row in range(rows.count):
                course_w = self._board_width(rows, row)
                out.append(
                    Pos(
                        x0 + width / 2,
                        self.board_t / 2,
                        z0 + row * pitch + course_w / 2,
                    )
                    * ALONG_RUN
                    * Board(
                        length_mm=width,
                        label="gate_course",
                        notes="gate infill, flush with the leaf",
                        **self._stock(self.board, covers_mm=course_w),
                    )
                )
            return out

        run = self.board_run(width, self.target_gap)
        pitch = self.board_w + run.gap
        for i in range(run.count):
            board_w = self._board_width(run, i)
            out.append(
                Pos(x0 + i * pitch + board_w / 2, self.board_t / 2, z0 + height / 2)
                * UPRIGHT
                * Board(
                    length_mm=height,
                    label="gate_board",
                    notes="gate infill, flush with the leaf",
                    **self._stock(self.board, covers_mm=board_w),
                )
            )
        if self.style == "board_on_board":
            for i in range(run.count - 1):
                out.append(
                    Pos(
                        x0 + self.board_w + run.gap / 2 + i * pitch,
                        self.board_t * 1.5,
                        z0 + height / 2,
                    )
                    * UPRIGHT
                    * Board(
                        length_mm=height,
                        label="gate_over_board",
                        notes="gate infill, over course",
                        **self._stock(self.board),
                    )
                )
        return out

    def infill_kg_per_mm(self) -> float:
        """Mass of infill per mm of run, kg — what the rails have to carry.

        Taken from the board pitch rather than from the extracted cut list, so
        that it is the load on *one bay* rather than the weight of the whole
        fence divided by something.
        """
        density = DENSITY_KG_M3[self.species]
        if self.style == "horizontal":
            rows = self.course_rows()
            volume_per_mm = rows.count * self.board_w * self.board_t
        else:
            pitch = self.board_w + (0.0 if self.board.milled else self.target_gap)
            layers = 2 if self.style == "board_on_board" else 1
            # Milled stock is billed by the face you buy, not the face that
            # shows, and it is the bought width that weighs something.
            volume_per_mm = layers * (self.board.width / pitch) * (
                self.board_length * self.board_t
            )
        return volume_per_mm * density / 1e9

    # ------------------------------------------------------------------
    # Buying
    # ------------------------------------------------------------------

    def plan(self, parts: list[CutPart]) -> LinealPlan:
        """Return the lineal-foot buying plan for the *timber* in *parts*.

        Mesh is bought by the roll and priced by the roll, so it is not in
        here: see :meth:`mesh_plan`, and see :meth:`cost_summary`, which is
        what adds the two together and names what neither of them could price.
        """
        timber = [p for p in parts if p.material == self.species]
        return plan_dimensional(timber, self.inventory)

    def mesh_stock(self) -> Any:
        """Return the mesh entry from ``stock.yaml``, or ``None`` if absent.

        Found by the material key the parts carry rather than by name, which
        is what makes the mesh a material this project *specifies* rather than
        one it hard-codes.
        """
        return self.inventory.unit_stock_for(self.mesh_material)

    def mesh_plan(self, parts: list[CutPart]) -> MeshPlan | None:
        """Return the mesh buying plan, or ``None`` for a fence with no mesh."""
        mesh = [p for p in parts if p.material == self.mesh_material]
        if not mesh:
            return None
        run_ft = sum(p.length_mm * p.qty for p in mesh) / FT
        return MeshPlan(
            stock=self.mesh_stock(),
            run_ft=run_ft,
            height=self.mesh_height,
            roll_height=inches(self.mesh_roll_height_in),
        )

    def cost_summary(self, parts: list[CutPart]) -> CostSummary:
        """Return timber and mesh together, with every gap in the total named."""
        summary = self.plan(parts).cost_summary
        mesh = self.mesh_plan(parts)
        return summary if mesh is None else summary + mesh.cost_summary

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def check(self, assembly: Compound, parts: list[CutPart]) -> CheckReport:
        """Run every design check against a built fence.

        Parameters
        ----------
        assembly : build123d.Compound
            The result of :meth:`build`.
        parts : list[CutPart]
            The result of extracting a cut list from *assembly*.

        Returns
        -------
        CheckReport
            All findings, in reporting order.
        """
        report = CheckReport()
        layers = 2 if self.style == "board_on_board" else 1
        thickness = self.gate_post_size + layers * self.board_t
        report.extend(
            check_envelope(
                actual_l_mm=self.overall_length,
                actual_w_mm=thickness,
                actual_h_mm=self.height,
                published_l_mm=self.run + self.gates * self.gate_section,
                published_w_mm=thickness,
                published_h_mm=inches(48.0),
            )
        )
        report.extend(self._check_layout())
        report.extend(self._check_infill(parts))
        report.extend(self._check_structure(parts))
        report.extend(self._check_posts())
        report.extend(self._check_gates(parts))
        report.extend(self._check_fasteners())
        report.extend(check_material_suitability(parts, self.inventory))
        return report

    def _check_layout(self) -> list[Finding]:
        """Report the bay layout and the post schedule it implies."""
        spans = self.spans()
        panels = [s for s in spans if s.kind == "panel"]
        posts = self.posts()
        gate_posts = [p for p in posts if p.is_gate_post]
        bays = sorted({round(s.length, 1) for s in panels})
        bay_text = ", ".join(mm_to_fractional_inch(b) for b in bays)
        findings = [
            Finding(
                Severity.INFO,
                "layout",
                f"{self.overall_length / FT:.0f} ft overall: "
                f"{self.run_ft:g} ft of fence in {len(panels)} bays of "
                f"{bay_text} on centre, plus {self.gates} gate "
                f"section{'s' if self.gates != 1 else ''} of "
                f"{self.gate_section_ft:g} ft — {len(posts)} posts, "
                f"{len(gate_posts)} of them {self.gate_post.nominal}",
            )
        ]
        if self.bay_ft:
            short = [
                s for s in panels if abs(s.length - self.bay_ft * FT) > 1.0
            ]
            if short:
                widths = ", ".join(mm_to_fractional_inch(s.length) for s in short)
                findings.append(
                    Finding(
                        Severity.INFO,
                        "layout",
                        f"the rails come in {self.bay_ft:g} ft, so the bay is "
                        f"the rail: {len(panels) - len(short)} full bays and "
                        f"{len(short)} short one{'s' if len(short) != 1 else ''} "
                        f"({widths}), whose rails are cut from full ones. A "
                        "rail is a stick and can be cut; a panel cannot, which "
                        "is the one way this system is more forgiving than the "
                        "panel line",
                    )
                )
        longest = max((s.length for s in panels), default=0.0)
        if longest > self.recommended_max_bay + 1e-6:
            findings.append(
                Finding(
                    Severity.WARN,
                    "layout",
                    f"a bay of {mm_to_fractional_inch(longest)} is past the "
                    f"{self.recommended_max_bay / FT:g} ft this style is good "
                    "for — the rails will hold it up and the fence will still "
                    "rack, because what a long bay costs is stiffness against "
                    "somebody leaning on it, not strength",
                )
            )
        return findings

    def _check_infill(self, parts: list[CutPart] | None = None) -> list[Finding]:
        """Report the infill: gaps, laps, rolls, and what time does to them."""
        findings: list[Finding] = []
        if self.style == "log_and_mesh":
            return self._check_mesh(parts or [])
        if self.board.milled:
            findings.append(
                Finding(
                    Severity.WARN,
                    "coverage",
                    f"{self.board.label} covers "
                    f"{mm_to_fractional_inch(self.board_w, 32)} of its "
                    f"{mm_to_fractional_inch(self.board.width)} face — an "
                    "ASSUMED figure. Lumbery prices the profile and publishes "
                    "no coverage, because what a board shows is set by the "
                    "moulder that cut it. Every board count below rests on "
                    "that number; measure a sample before ordering",
                )
            )
        if self.style == "horizontal":
            rows = self.course_rows()
            spacing = (
                "butted"
                if self.board.milled
                else f"with {mm_to_fractional_inch(rows.gap, 32)} between them"
            )
            ripped = (
                ""
                if rows.last_width is None
                else ", the top course ripped to "
                f"{mm_to_fractional_inch(rows.last_width, 32)}"
            )
            findings.append(
                Finding(
                    Severity.INFO,
                    "infill",
                    f"{rows.count} courses of "
                    f"{mm_to_fractional_inch(self.board_w)} board {spacing}"
                    f"{ripped}, filling "
                    f"{mm_to_fractional_inch(rows.cover)} from the "
                    f"{self.ground_clearance_in:g}\" ground gap to the top",
                )
            )
            return findings

        for group in self.panel_groups():
            _, cover = self.cover_of(group)
            target = self.target_gap
            run = self.board_run(cover, target)
            if self.board.milled:
                ripped = (
                    "every board full width"
                    if run.last_width is None
                    else "the last ripped to "
                    f"{mm_to_fractional_inch(run.last_width, 32)}"
                )
                findings.append(
                    Finding(
                        Severity.INFO,
                        "infill",
                        f"{mm_to_fractional_inch(cover)} of fence takes "
                        f"{run.count} boards butted, {ripped} — an "
                        "interlocking board has no gap to stretch, so the "
                        "remainder comes off the last one",
                    )
                )
                continue
            findings.append(
                Finding(
                    Severity.INFO,
                    "infill",
                    f"{mm_to_fractional_inch(cover)} of fence takes "
                    f"{run.count} boards at "
                    f"{mm_to_fractional_inch(run.gap, 32)} apart "
                    f"(asked for {mm_to_fractional_inch(target, 32)}) — the "
                    "gap absorbs the remainder, so there is no sliver at the "
                    "end",
                )
            )
            if self.style == "board_on_board":
                lap = (self.board_w - run.gap) / 2
                severity = Severity.INFO if lap >= inches(0.75) else Severity.WARN
                findings.append(
                    Finding(
                        severity,
                        "infill",
                        f"over boards lap {mm_to_fractional_inch(lap, 32)} onto "
                        "each neighbour; rough sawn cedar at 6\" wide gives up "
                        "about 1/8\" across the grain going from green to a "
                        "dry August, so a lap under 3/4\" is a fence that opens"
                        + ("" if lap >= inches(0.75) else " — widen the gap"),
                    )
                )
            elif run.gap < inches(0.5):
                findings.append(
                    Finding(
                        Severity.WARN,
                        "infill",
                        f"a {mm_to_fractional_inch(run.gap, 32)} gap is tight "
                        "for boards nailed up green: they swell before they "
                        "shrink, and neighbours that touch will cup",
                    )
                )
        return findings

    def _check_mesh(self, parts: list[CutPart]) -> list[Finding]:
        """Check the mesh: how much, how tall, and what it does and does not stop."""
        findings: list[Finding] = []
        plan = self.mesh_plan(parts)

        if self.mesh_height > inches(self.mesh_roll_height_in) + 1e-6:
            findings.append(
                Finding(
                    Severity.ERROR,
                    "mesh",
                    f"the fence wants {mm_to_fractional_inch(self.mesh_height)} "
                    f"of mesh off a {self.mesh_roll_height_in:g}\" roll — mesh "
                    "cannot be stretched, and a seam across a fence is a line "
                    "everybody sees",
                )
            )
        else:
            spare = inches(self.mesh_roll_height_in) - self.mesh_height
            if spare > inches(0.5):
                findings.append(
                    Finding(
                        Severity.INFO,
                        "mesh",
                        f"{mm_to_fractional_inch(self.mesh_height)} of mesh on "
                        f"a {self.mesh_roll_height_in:g}\" roll leaves "
                        f"{mm_to_fractional_inch(spare)} spare — run the "
                        "roll's own selvedge at the top where it shows, and "
                        "trim the bottom",
                    )
                )
            else:
                findings.append(
                    Finding(
                        Severity.WARN,
                        "mesh",
                        f"{mm_to_fractional_inch(self.mesh_height)} of mesh off "
                        f"a {self.mesh_roll_height_in:g}\" roll is the whole "
                        "roll: both selvedges show and there is nothing to "
                        "trim, so any error in the post spacing shows as a "
                        "wavy top edge. A 60\" roll gives a foot to bury as an "
                        "apron, which is the detail that actually stops a dog "
                        "— they go under, not over",
                    )
                )

        if plan is not None:
            rolls = (
                "the roll length is not published, so this is feet and not "
                "rolls"
                if plan.rolls is None
                else f"{plan.rolls} roll(s) of {plan.roll_length_ft:.0f} ft"
            )
            findings.append(
                Finding(
                    Severity.INFO,
                    "mesh",
                    f"{plan.run_ft:.0f} ft of fence to cover, "
                    f"{plan.buy_ft:.0f} ft to buy with "
                    f"{plan.allowance * 100:.0f}% for trim and the wrap onto "
                    f"each post — {rolls}",
                )
            )
            if plan.price_line is None:
                findings.append(
                    Finding(
                        Severity.WARN,
                        "price",
                        "the mesh carries no price, so every total this "
                        "project prints for it is timber only. It is a "
                        "stocked retail product with published prices; the "
                        "retail domains are blocked from this environment, so "
                        "nothing could be read from a page and nothing was "
                        "invented. One dated line in stock.yaml closes it",
                    )
                )

        findings.append(
            Finding(
                Severity.INFO,
                "mesh",
                "2\" x 4\" mesh keeps a dog in and a deer out and stops "
                "nothing smaller: a rabbit walks through it and a chick falls "
                "through it — if that matters, line the bottom 18\" with 1\" "
                "hex and bury an apron of it, because a dog digs where the "
                "fence meets the ground",
            )
        )
        findings.append(
            Finding(
                Severity.INFO,
                "mesh",
                "drawn as a thin sheet, not as wires: the model is honest "
                "about where the mesh is and says nothing about the pattern. "
                "The mass estimate uses the mesh's own areal weight, not a "
                "sheet of steel",
            )
        )
        return findings

    def _check_fasteners(self) -> list[Finding]:
        """Report what cedar does to the wrong fastener.

        Every style has this problem and no cut list can show it: cedar's own
        extractives corrode plain steel, and the wood around each fastener
        goes black within a season.  On a mesh fence there are several hundred
        staples, which makes it several hundred black marks.
        """
        finding = [
            Finding(
                Severity.WARN,
                "fasteners",
                "cedar's extractives eat plain steel and stain the wood black "
                "around every fastener — hot-dip galvanised, stainless or "
                "polymer-coated only, throughout, including the staples and "
                "the hinge screws",
            )
        ]
        if self.style == "log_and_mesh":
            finding.append(
                Finding(
                    Severity.INFO,
                    "fasteners",
                    "the mesh's black coating is what stops it rusting, and "
                    "every cut end is a place it is not coated — cut into the "
                    "line wire where you can, and touch the ends in with black "
                    "paint where you cannot",
                )
            )
        return finding

    def _check_structure(self, parts: list[CutPart]) -> list[Finding]:
        """Check the members that span: rails, or the boards that replace them."""
        e_mpa = ELASTIC_MODULUS_MPA[self.species]
        panels = [s for s in self.spans() if s.kind == "panel"]
        if not panels:
            return []
        span = max(s.length for s in panels) - self.post_size

        if self.style == "log_and_mesh":
            return self._check_log_rails(e_mpa, span)

        if self.style == "horizontal":
            # Nothing spans but the boards themselves, one bay at a time,
            # carrying only their own weight.
            board_kg = (
                self.board_w * self.board_t * span / 1e9 * DENSITY_KG_M3[self.species]
            )
            deflection = beam_deflection_mm(
                e_mpa=e_mpa,
                span_mm=span,
                breadth_mm=self.board_t,
                depth_mm=self.board_w,
                load_kg=board_kg,
            )
            sag = (
                "less than 0.1 mm"
                if deflection < 0.1
                else f"{deflection:.1f} mm"
            )
            return [
                Finding(
                    Severity.INFO
                    if span <= self.recommended_max_bay
                    else Severity.WARN,
                    "deflection",
                    f"a course spans {mm_to_fractional_inch(span)} between "
                    f"posts and sags {sag} under its own weight, on edge — "
                    "sag is not what limits this style and the arithmetic is "
                    "not the reason for the short bays.  Cupping is: a 1x6 "
                    "screwed at its ends only will cup across its width long "
                    "before it sags along its length, which is why the bays "
                    f"are held to {self.max_horizontal_bay_ft:g} ft and every "
                    "course is fastened at every post",
                )
            ]

        # Two rails carry the boards between them, so each takes half the
        # weight of one bay of infill.
        panel_kg = self.infill_kg_per_mm() * span
        deflection = beam_deflection_mm(
            e_mpa=e_mpa,
            span_mm=span,
            breadth_mm=self.rail_t,
            depth_mm=self.rail_w,
            load_kg=panel_kg / 2,
        )
        limit = span / 240.0
        severity = Severity.INFO if deflection <= limit else Severity.WARN
        return [
            Finding(
                severity,
                "deflection",
                f"{self.rail.nominal} rail over the longest bay "
                f"({mm_to_fractional_inch(span)} clear) carries "
                f"{panel_kg / 2:.0f} kg of boards and deflects "
                f"{deflection:.1f} mm (span/{span / max(deflection, 1e-9):.0f}; "
                f"limit span/240 = {limit:.1f} mm) — set the rails with the "
                "4\" face against the boards, which is fourteen times the "
                "stiffness of the same stick laid flat",
            )
        ]

    def _check_log_rails(self, e_mpa: float, span: float) -> list[Finding]:
        """Check a round rail, which is stiffer than the square it fits in.

        :func:`~woodshop.checks.beam_deflection_mm` bends a rectangle, and a
        log is a circle: its second moment is ``pi d^4 / 64`` where a square's
        is ``d^4 / 12``, so a round rail is 59% of the square it fits inside
        rather than 100%.  Passing the diameter as both dimensions would
        overstate a log rail's stiffness by 70%, which is the sort of error
        that only shows up as a sagging fence.
        """
        diameter = self.rail.width
        equivalent_breadth = 12.0 * math.pi / 64.0 * diameter
        # The rails carry the mesh, which weighs almost nothing, and then
        # whatever leans on it.  200 lb of somebody is the load worth asking
        # about; the mesh itself is a rounding error.
        lean_kg = 90.0
        deflection = beam_deflection_mm(
            e_mpa=e_mpa,
            span_mm=span,
            breadth_mm=equivalent_breadth,
            depth_mm=diameter,
            load_kg=lean_kg / max(self.log_rails, 1),
        )
        limit = span / 240.0
        return [
            Finding(
                Severity.INFO if deflection <= limit else Severity.WARN,
                "deflection",
                f"{self.log_rails} log rails of "
                f"{mm_to_fractional_inch(diameter)} over the longest bay "
                f"({mm_to_fractional_inch(span)} clear): "
                f"{lean_kg:.0f} kg of somebody leaning on the mesh puts "
                f"{deflection:.1f} mm into the rail carrying it "
                f"(limit span/240 = {limit:.1f} mm) — a round rail is 59% as "
                "stiff as the square it fits inside, which is worth knowing "
                "before swapping a 4\" log for a 4x4",
            ),
            Finding(
                Severity.INFO,
                "joinery",
                f"each rail is tenoned {self.tenon_in:g}\" into a "
                f"{self.tenon_diameter_in:g}\" hole bored in the post, which "
                "is the joint this fence has instead of a bracket: bore every "
                "hole before the posts are set, because a brace and bit is no "
                "use against a post already in the ground",
            ),
        ]

    def _check_posts(self) -> list[Finding]:
        """Check what goes in the ground, which is what the fence dies of."""
        posts = self.posts()
        # Every post on a very short run can be a gate post, in which case the
        # gate post is the representative one.
        line = next((p for p in posts if not p.is_gate_post), posts[0])
        findings: list[Finding] = []

        embedment_in = line.embedment / IN
        # Floating-point slack: 48" of embedment converted to mm and back is
        # not exactly 48, and a fence should not be warned about a rounding
        # error a shovel could not measure.
        deep_enough = embedment_in >= FROST_DEPTH_IN - 1e-6
        severity = Severity.INFO if deep_enough else Severity.WARN
        findings.append(
            Finding(
                severity,
                "frost",
                f"line posts go {embedment_in:.0f}\" into the ground against a "
                f"{FROST_DEPTH_IN:.0f}\" frost depth for southern Maine"
                + (
                    ""
                    if deep_enough
                    else " — a post whose foot is inside the frost zone gets "
                    "jacked a little every spring, and a fence that has been "
                    "jacked cannot be plumbed back"
                ),
            )
        )

        for nominal, length in (
            (self.post.nominal, self.post_length),
            (self.gate_post.nominal, self.gate_post_length),
        ):
            length_ft = length / FT
            fits = [ft for ft in COMMON_LENGTHS_FT if ft >= length_ft - 1e-6]
            shortest = fits[0] if fits else None
            if shortest is None:
                findings.append(
                    Finding(
                        Severity.WARN,
                        "stock",
                        f"{nominal} posts are {length_ft:.1f} ft, longer than "
                        "any length softwood is commonly stocked in",
                    )
                )
            elif abs(shortest - length_ft) > 1e-6:
                findings.append(
                    Finding(
                        Severity.INFO,
                        "stock",
                        f"{nominal} posts are "
                        f"{mm_to_fractional_inch(length)} — off a "
                        f"{shortest:g} ft stick that is "
                        f"{mm_to_fractional_inch(shortest * FT - length)} of "
                        "offcut each, so ask the yard what lengths they cut "
                        "cedar posts to before ordering",
                    )
                )

        findings.append(
            Finding(
                Severity.WARN,
                "durability",
                "northern white cedar heartwood is rot resistant; its sapwood "
                "is not, and a post is bought by the stick rather than sorted "
                "for heartwood — set every post on 6\" of crushed stone in a "
                "hole backfilled with stone rather than concrete, so water "
                "drains away from the post instead of standing in a concrete "
                "cup around it",
            )
        )
        if self.post.round:
            findings.append(
                Finding(
                    Severity.WARN,
                    "durability",
                    "a peeled log keeps the tree's sapwood band as its outer "
                    "skin, and that skin is the whole of what touches soil — "
                    "a sawn 4x4 out of the middle of the same log shows "
                    "heartwood on all four faces. Round posts are the look "
                    "and the cheaper stick; they are not the more durable one",
                )
            )
        findings.append(
            Finding(
                Severity.INFO,
                "durability",
                f"boards stop {self.ground_clearance_in:g}\" above grade and "
                f"the gates {self.gate_clearance_in:g}\": end grain touching "
                "soil is the one detail that decides whether this fence is "
                "twenty years old or five",
            )
        )
        return findings

    def _check_gates(self, parts: list[CutPart]) -> list[Finding]:
        """Check the gates, which are the only part of a fence that moves."""
        findings: list[Finding] = []
        openings = self.gate_openings
        if not openings:
            return findings

        leaf_labels = {
            "gate_stile",
            "gate_rail",
            "gate_brace",
            "gate_board",
            "gate_over_board",
            "gate_course",
            "gate_mesh",
        }
        leaf_parts = [p for p in parts if p.label in leaf_labels]
        # Everything gate-shaped in the cut list, divided by how many leaves
        # there are — every leaf in this design is identical.
        n_leaves = len(openings) * self.gate_leaves
        leaf_kg = estimate_mass_kg(leaf_parts) / max(n_leaves, 1)

        span = openings[0]
        width = self.leaf_width(span)
        clear = self.clear_opening(span)
        findings.append(
            Finding(
                Severity.INFO,
                "gate",
                f"{self.gate_section_ft:g} ft section on centre is a "
                f"{mm_to_fractional_inch(clear)} clear opening — "
                f"{self.gate_leaves} "
                f"{'leaves' if self.gate_leaves > 1 else 'leaf'} at "
                f"{mm_to_fractional_inch(width)}, {leaf_kg:.0f} kg each",
            )
        )

        # A leaf is a cantilever off two hinges. The couple they resist is the
        # leaf's weight acting at half its width, over the hinge spacing.
        hinge_spacing = self.leaf_height - inches(6.0)
        pull_kg = leaf_kg * (width / 2) / hinge_spacing
        findings.append(
            Finding(
                Severity.INFO if width <= inches(60.0) else Severity.WARN,
                "gate",
                f"the leaf's weight acts {mm_to_fractional_inch(width / 2)} out "
                f"from the hinges, so hinges "
                f"{mm_to_fractional_inch(hinge_spacing)} apart pull "
                f"{pull_kg:.0f} kg on the top one — use three strap hinges "
                "bolted through the stile, not screwed into it"
                + (
                    ""
                    if width <= inches(60.0)
                    else "; a leaf over 5 ft is where an anti-sag cable stops "
                    "being optional"
                ),
            )
        )
        if self.style == "log_and_mesh":
            findings.append(
                Finding(
                    Severity.INFO,
                    "gate",
                    "the leaves are a sawn 2x4 frame with the same mesh in "
                    "them, not logs: a round rail cannot be half-lapped into a "
                    "round stile, and a gate with nothing but tenons in it "
                    "racks the first time somebody swings on it",
                )
            )
            return findings + self._gate_common(leaf_kg, width)

        leaf_run = self.leaf_infill(span)
        if self.style == "horizontal":
            # Courses stack to the same height everywhere, so there is one
            # fence spacing rather than one per stretch.
            panel_gaps = [self.course_rows().gap]
        else:
            panel_gaps = [
                self.board_run(self.cover_of(group)[1], self.target_gap).gap
                for group in self.panel_groups()
            ]
        if panel_gaps:
            fence_gap = sum(panel_gaps) / len(panel_gaps)
            mismatch = abs(leaf_run.gap - fence_gap)
            findings.append(
                Finding(
                    Severity.INFO if mismatch <= inches(0.25) else Severity.WARN,
                    "gate",
                    f"a leaf takes {leaf_run.count} boards at "
                    f"{mm_to_fractional_inch(leaf_run.gap, 32)}, against "
                    f"{mm_to_fractional_inch(fence_gap, 32)} in the fence "
                    f"beside it — a {mm_to_fractional_inch(mismatch, 32)} "
                    "difference in rhythm, which is read at a glance from ten "
                    "feet away because the gate is the one place two spacings "
                    "meet"
                    + (
                        ""
                        if mismatch <= inches(0.25)
                        else "; hold the leaf to the fence pitch and let the "
                        "board against the latch stile run narrow if that "
                        "matters more than a whole board at each edge"
                    ),
                )
            )
        return findings + self._gate_common(leaf_kg, width)

    def _gate_common(self, leaf_kg: float, width: float) -> list[Finding]:
        """Return the findings every gate gets, whatever fills its frame.

        Parameters
        ----------
        leaf_kg : float
            Mass of one leaf.
        width : float
            Width of one leaf, mm.
        """
        n_leaves = len(self.gate_openings) * self.gate_leaves
        findings: list[Finding] = []
        findings.append(
            Finding(
                Severity.INFO,
                "gate",
                "the diagonal runs from the bottom hinge corner up to the top "
                "latch corner, so it works in compression — braced the other "
                "way the joint at the top of the brace is holding the gate up "
                "in tension on two screws",
            )
        )
        if self.gate_leaves == 2:
            findings.append(
                Finding(
                    Severity.INFO,
                    "gate",
                    "the pair needs a drop rod into a sleeve in the ground on "
                    "the inactive leaf and a stop for it to close against — "
                    "without one the latch carries both leaves and the pair "
                    "rattles",
                )
            )
        findings.append(
            Finding(
                Severity.WARN,
                "hardware",
                "hinges, latch, drop rod, "
                + (
                    "and a keg of galvanised staples "
                    if self.style == "log_and_mesh"
                    else "rail brackets and ring-shank nails "
                )
                + "are not in stock.yaml and are not in any total this "
                "project prints — budget them separately; on "
                f"{n_leaves} leaves of {mm_to_fractional_inch(width)} the "
                "hardware is not a rounding error",
            )
        )
        return findings

    def check_prices(
        self, plan: LinealPlan, mesh: "MeshPlan | None" = None
    ) -> CheckReport:
        """Return the price-provenance findings for everything a fence buys.

        Parameters
        ----------
        plan : LinealPlan
            The timber plan.
        mesh : MeshPlan, optional
            The mesh plan, where there is mesh.  Its entry is audited with the
            timber rather than beside it: a fence buys one order.
        """
        stock = list(plan.stock_used)
        if mesh is not None and mesh.stock is not None:
            stock.append(mesh.stock)
        return CheckReport().extend(
            check_price_provenance(self.inventory, stock=stock)
        )

    def check_stock_lengths(self, plan: LinealPlan) -> list[Finding]:
        """Report that a cut plan is impossible from a price list alone."""
        findings: list[Finding] = []
        for group in plan.groups:
            if not group.stock.lengths_ft:
                priced = (
                    "is priced per lineal foot and stocked"
                    if group.stock.price is not None
                    else "is stocked"
                )
                findings.append(
                    Finding(
                        Severity.WARN,
                        "stock",
                        f"{group.stock.stock_label} {priced} in lengths nobody "
                        f"has published, so this is {group.lineal_ft:.0f} LF "
                        "to buy and not a cut list — ask the yard what lengths "
                        "they carry, then run --assume-lengths against the "
                        "answer",
                    )
                )
        return findings



# ---------------------------------------------------------------------------
# The panel catalogue: what The Lumbery actually sells over the counter
# ---------------------------------------------------------------------------
#
# Everything above builds a fence out of sticks.  The Lumbery sells AVO's
# pre-assembled panels, which is a different product and a different job: an
# 8 ft panel hangs between two posts bored at the mill for its dowelled rail
# ends, and nothing on site gets cut at all.
#
# Read from lumberystore.com/fence-panels-and-posts and its product pages,
# 2026-08-18.  Board sizes, rail sections, grades, heights and the post
# sizing table are theirs; the prices are not published in the page and are
# recorded as missing.


@dataclass(frozen=True)
class PanelStyle:
    """One style in AVO's panel line, as their catalogue describes it.

    Parameters
    ----------
    key : str
        Short name used on the command line.
    name : str
        Name as the catalogue prints it.
    board_t_in, board_w_in : float
        Board thickness and width in inches.  Their two board sizes are
        7/8" x 2-7/8" (stockade and picket stock) and 3/4" x 3-1/2" (board
        stock); the difference is a third of the wood in the fence.
    infill : str
        ``"solid"``, ``"spaced"``, ``"tongue_and_groove"`` or ``"baluster"``.
    grades : tuple of str
        Grades offered, in the catalogue's own words.
    options : tuple of str
        Custom options offered for this style.  Each is sold *per panel* and
        its quantity has to match the panel count.
    summary : str
        What the catalogue says the style is for.
    """

    key: str
    name: str
    board_t_in: float
    board_w_in: float
    infill: str
    grades: tuple[str, ...]
    options: tuple[str, ...]
    summary: str

    @property
    def board_t(self) -> float:
        """Board thickness, mm."""
        return inches(self.board_t_in)

    @property
    def board_w(self) -> float:
        """Board width, mm."""
        return inches(self.board_w_in)


#: AVO's panel styles.  Every one comes 4, 5 and 6 ft high by 8 ft long.
AVO_STYLES: dict[str, PanelStyle] = {
    "stockade": PanelStyle(
        key="stockade",
        name="Stockade",
        board_t_in=0.875,
        board_w_in=2.875,
        infill="solid",
        grades=("Premium (#1)", "#2", "Economy (#3)"),
        options=("scalloped", "board toppers", "cap strips"),
        summary="privacy and security, boards butted tight",
    ),
    "privacy_board": PanelStyle(
        key="privacy_board",
        name="Privacy Board",
        board_t_in=0.75,
        board_w_in=3.5,
        infill="solid",
        grades=("Premium (#1)", "#2", "Economy (#3)"),
        options=("scalloped", "capped"),
        summary="the same privacy in a wider, thinner board",
    ),
    "spaced_picket": PanelStyle(
        key="spaced_picket",
        name="Spaced Picket",
        board_t_in=0.875,
        board_w_in=2.875,
        infill="spaced",
        grades=("Premium (#1)", "#2"),
        options=("scalloped", "board toppers", "cap strips"),
        summary="the classic open picket line",
    ),
    "spaced_board": PanelStyle(
        key="spaced_board",
        name="Spaced Board",
        board_t_in=0.75,
        board_w_in=3.5,
        infill="spaced",
        grades=("Premium (#1)", "#2"),
        options=("scalloped", "board toppers", "cap strips"),
        summary="spaced, in the wider board — airflow with more coverage",
    ),
    "universal": PanelStyle(
        key="universal",
        name="Universal",
        board_t_in=0.75,
        board_w_in=3.5,
        infill="tongue_and_groove",
        grades=("Premium (#1)", "#2"),
        options=("scalloped", "reverse scalloped", "capped", "molded rails"),
        summary=(
            "the good-neighbour panel: 1x4 tongue and groove picture-framed "
            "in 6/4x4, no backing rails, identical from both sides"
        ),
    ),
    "chestnut_hill": PanelStyle(
        key="chestnut_hill",
        name="Chestnut Hill",
        board_t_in=1.5,
        board_w_in=1.5,
        infill="baluster",
        grades=("Premium", "Economy"),
        options=("scalloped", "capped", "alternating", "molded rails"),
        summary=(
            "2x2 balusters between doubled rails — decorative, and the same "
            "from both sides"
        ),
    ),
}

#: Panel heights the catalogue stocks, in feet.  Anything else is custom.
AVO_PANEL_HEIGHTS_FT: tuple[float, ...] = (4.0, 5.0, 6.0)

#: Panel length, in feet.  Every style, one length.
AVO_PANEL_LENGTH_FT: float = 8.0

#: Their post sizing table: fence height in feet -> (post length, burial).
#:
#: This is the supplier telling you how deep to dig, and it is the one place
#: their catalogue and this project disagree — see
#: :meth:`PanelFence._check_posts`, which measures 2 ft of burial against a
#: 4 ft frost depth and says what that costs.
AVO_POST_TABLE: dict[float, tuple[float, float]] = {
    4.0: (6.0, 2.0),
    5.0: (8.0, 3.0),
    6.0: (10.0, 4.0),
    8.0: (12.0, 4.0),
}

#: The rail every panel is framed with: 2" x 3" S2S, dowelled into the post.
AVO_RAIL = StockChoice(
    "2x3", grade="", profile="S2S dowelled Colonial rail", actual_in=(2.0, 3.0)
)

#: The post most panels hang on, bored at the mill for those dowels.
AVO_POST = StockChoice("4x4", grade="#1", profile="chamfered top, pre-routed")

#: The post a gate hangs on.  Their widths are 4x4, 5x5 and 6x6; a gate wants
#: the big one for the same reason it does in every other design here.
AVO_GATE_POST = StockChoice("6x6", grade="#1", profile="chamfered top, pre-routed")


@dataclass(frozen=True)
class PanelOrder:
    """What a panel fence is bought as: pieces, not feet.

    Nothing in a panel fence is cut, so it has no cut list in the sense the
    rest of this repository means: it has an order.  Panels, posts and caps
    are counted, and every one of them is a line on an invoice rather than a
    length off a stick.

    Parameters
    ----------
    lines : list[tuple[str, int, str]]
        ``(what, how many, in what unit)``, in order.
    unpriced : list[str]
        Labels of everything the catalogue publishes without a price.
    quoted : list[str]
        Things the catalogue will not price online at all — the gates, which
        it says are custom and quoted by email.
    stock_used : list
        The inventory entries this order buys, for the provenance report.
        Without it the report falls back to auditing every entry in the
        species, which for cedar is now forty-seven of them.
    """

    lines: list[tuple[str, int, str]] = field(default_factory=list)
    unpriced: list[str] = field(default_factory=list)
    quoted: list[str] = field(default_factory=list)
    stock_used: list[Any] = field(default_factory=list)

    @property
    def cost_summary(self) -> CostSummary:
        """A summary with nothing in it but the names of what it cannot price."""
        return CostSummary.of((), self.unpriced)

    def to_text(self) -> str:
        """Render the order as the list you would email the yard."""
        out = [
            f"  {count:>3d} x {what:<52s} ({unit})"
            for what, count, unit in self.lines
        ]
        for label in self.quoted:
            out.append(f"  (?) {label}: custom, and the catalogue quotes it by email")
        for label in self.unpriced:
            out.append(
                f"  (!) {label} carries no published price — it is missing from "
                "any total, not free"
            )
        return "\n".join(out)


@dataclass
class PanelFence:
    """A fence assembled from The Lumbery's pre-built AVO panels.

    The same run as :class:`CedarFence`, bought the other way.  A stick-built
    fence is boards, rails and posts, and the design question is how the boards
    divide; a panel fence is 8 ft assemblies hung between pre-bored posts, and
    the design question is whether the run divides into panels at all.

    Parameters
    ----------
    style : str
        A key of :data:`AVO_STYLES`, default ``"stockade"``.
    run_ft : float, optional
        Length of plain fence, post centre to post centre, default 38.
    height_ft : float, optional
        Panel height in feet, default 4.  The catalogue stocks
        :data:`AVO_PANEL_HEIGHTS_FT`; anything else is a custom panel and the
        checks say so.
    grade : str, optional
        Which grade to order, in the catalogue's words.  Defaults to the first
        one the style offers.
    gates : int, optional
        How many gate sections, default 2.
    gate_section_ft : float, optional
        Length of a gate section on centre, default 10.
    gate_leaves : int, optional
        Leaves per gate, default 2.
    panel_ft : float, optional
        Panel length, default :data:`AVO_PANEL_LENGTH_FT`.
    ground_clearance_in : float, optional
        Gap between grade and the bottom of a panel, default 2.
    spacing_in : float, optional
        Gap between boards in the spaced styles, default 1.75.  The catalogue
        does not publish it; see the finding that says so.
    rail_inset_in : float, optional
        How far the rail centres sit inside the top and bottom of a panel,
        default 6.  Also unpublished, and also flagged.
    post, gate_post, rail : StockChoice, optional
        Which post and rail entries to order.
    species : str, optional
        Species, default ``"white_cedar"``.
    inventory : Inventory, optional
        Stock to price against.  ``None`` loads ``stock.yaml``.

    Raises
    ------
    ValueError
        If *style* is not in the catalogue, or *grade* is not one that style
        is offered in.
    """

    style: str = "stockade"
    run_ft: float = 38.0
    height_ft: float = 4.0
    grade: str = ""
    gates: int = 2
    gate_section_ft: float = 10.0
    gate_leaves: int = 2
    panel_ft: float = AVO_PANEL_LENGTH_FT
    ground_clearance_in: float = 2.0
    spacing_in: float = 1.75
    rail_inset_in: float = 6.0
    post: StockChoice = field(default_factory=lambda: AVO_POST)
    gate_post: StockChoice = field(default_factory=lambda: AVO_GATE_POST)
    rail: StockChoice = field(default_factory=lambda: AVO_RAIL)
    species: str = "white_cedar"
    inventory: Inventory = field(default_factory=Inventory.load)

    def __post_init__(self) -> None:
        """Check the style and grade against the catalogue."""
        if self.style not in AVO_STYLES:
            raise ValueError(
                f"style must be one of {sorted(AVO_STYLES)}, got {self.style!r}"
            )
        if not self.grade:
            self.grade = self.spec.grades[0]
        elif self.grade not in self.spec.grades:
            raise ValueError(
                f"{self.spec.name} is offered in {list(self.spec.grades)}, "
                f"not {self.grade!r}"
            )

    # ------------------------------------------------------------------
    # The catalogue's numbers
    # ------------------------------------------------------------------

    @property
    def spec(self) -> PanelStyle:
        """The catalogue entry this fence is built from."""
        return AVO_STYLES[self.style]

    @property
    def height(self) -> float:
        """Panel height, mm."""
        return self.height_ft * FT

    @property
    def panel_length(self) -> float:
        """Panel length, mm."""
        return self.panel_ft * FT

    @property
    def run(self) -> float:
        """Length of plain fence, mm."""
        return self.run_ft * FT

    @property
    def gate_section(self) -> float:
        """Length of one gate section on centre, mm."""
        return self.gate_section_ft * FT

    @property
    def overall_length(self) -> float:
        """Run plus gate sections, post centre to post centre, mm."""
        return self.run + self.gates * self.gate_section

    @property
    def post_length_ft(self) -> float:
        """Post length from the catalogue's own sizing table, in feet."""
        table = AVO_POST_TABLE.get(self.height_ft)
        if table is not None:
            return table[0]
        # Off their table: the shortest stocked post that leaves the burial
        # their table would have asked for at the next height down.
        return self.height_ft + 2.0

    @property
    def post_length(self) -> float:
        """Post length, mm."""
        return self.post_length_ft * FT

    @property
    def above_grade(self) -> float:
        """How much post stands above grade, mm.

        The panel hangs clear of the ground and the post has to reach its top,
        so this is the panel height plus the gap under it — which is where the
        catalogue's own "4 ft above ground, 2 ft below" stops being exact.
        """
        return self.height + inches(self.ground_clearance_in)

    @property
    def embedment(self) -> float:
        """How much post is in the ground, mm."""
        return self.post_length - self.above_grade

    @property
    def post_size(self) -> float:
        """Line post face dimension, mm."""
        return self.post.width

    @property
    def gate_post_size(self) -> float:
        """Gate post face dimension, mm."""
        return self.gate_post.width

    # ------------------------------------------------------------------
    # Layout: the run divided into panels, which is the whole question
    # ------------------------------------------------------------------

    def spans(self) -> list[Span]:
        """Return every span between adjacent posts, left to right.

        A panel fence cannot choose its bay: the bay *is* the panel.  So the
        run is laid out in whole panels and whatever is left over becomes one
        odd panel, which the catalogue will build to size and which nobody
        should discover on site.
        """
        segments: list[tuple[str, float]] = []
        if self.gates:
            share = self.run / self.gates
            for _ in range(self.gates):
                segments.append(("fence", share))
                segments.append(("gate", self.gate_section))
        else:
            segments.append(("fence", self.run))

        spans: list[Span] = []
        x = 0.0
        for kind, length in segments:
            if kind == "gate":
                spans.append(Span("gate", x, x + length))
                x += length
                continue
            full = int(length // self.panel_length)
            for _ in range(full):
                spans.append(Span("panel", x, x + self.panel_length))
                x += self.panel_length
            remainder = length - full * self.panel_length
            if remainder > 1.0:
                spans.append(Span("panel", x, x + remainder))
                x += remainder
        return spans

    def panels(self) -> list[Span]:
        """Every panel span, in order."""
        return [s for s in self.spans() if s.kind == "panel"]

    def odd_panels(self) -> list[Span]:
        """Panels that are not a full catalogue length — the custom ones."""
        return [
            s for s in self.panels() if abs(s.length - self.panel_length) > 1.0
        ]

    def gate_openings(self) -> list[Span]:
        """Every gate opening, in order."""
        return [s for s in self.spans() if s.kind == "gate"]

    def posts(self) -> list[PostPlan]:
        """Return every post, left to right, sized as the catalogue sells them."""
        spans = self.spans()
        boundaries = [spans[0].x0] + [s.x1 for s in spans]
        gate_x = {x for s in spans if s.kind == "gate" for x in (s.x0, s.x1)}
        out: list[PostPlan] = []
        for x in boundaries:
            is_gate_post = any(abs(x - gx) < 1e-6 for gx in gate_x)
            choice = self.gate_post if is_gate_post else self.post
            # A gate hangs on the next post length up, which the catalogue
            # sells: the extra two feet all go in the ground, where a gate
            # post needs them.
            length = self.post_length + (inches(24.0) if is_gate_post else 0.0)
            out.append(
                PostPlan(
                    x=x,
                    nominal=choice.nominal,
                    size=choice.width,
                    embedment=length - self.above_grade,
                    length=length,
                    is_gate_post=is_gate_post,
                )
            )
        return out

    def post_kinds(self) -> dict[str, int]:
        """Count posts by the routing the catalogue sells them with.

        A pre-routed post is bored on the faces the rails come into, so an end
        post and a line post are different products and turning up with the
        wrong mix means a hole in the wrong side of a post.
        """
        posts = self.posts()
        kinds = {"end": 0, "line": 0}
        for index, _post in enumerate(posts):
            kinds["end" if index in (0, len(posts) - 1) else "line"] += 1
        return kinds

    def board_run(self, cover: float) -> BoardRun:
        """Fit the infill across one panel of *cover* mm."""
        board_w = self.spec.board_w
        if self.spec.infill == "solid":
            count = max(1, int(-(-cover // board_w)))
            last = cover - (count - 1) * board_w
            return BoardRun(
                count=count,
                gap=0.0,
                cover=cover,
                last_width=None if abs(last - board_w) < 0.5 else last,
            )
        if self.spec.infill == "tongue_and_groove":
            # A tongue and groove board covers less than it measures; the
            # catalogue does not publish how much less.
            covers = board_w - inches(0.375)
            count = max(1, int(-(-cover // covers)))
            last = cover - (count - 1) * covers
            return BoardRun(
                count=count,
                gap=0.0,
                cover=cover,
                last_width=None if abs(last - covers) < 0.5 else last,
            )
        target = inches(self.spacing_in)
        pitch = board_w + target
        count = max(2, round((cover + target) / pitch))
        gap = (cover - count * board_w) / (count - 1)
        return BoardRun(count=count, gap=gap, cover=cover)

    # ------------------------------------------------------------------
    # Assembly
    # ------------------------------------------------------------------

    def build(self) -> Compound:
        """Build the fence as a positioned build123d assembly.

        Grade is ``z = 0``.  The panels are drawn as what they are made of —
        boards, rails, balusters — because a picture of a box labelled "panel"
        would check nothing, but nothing here is a cut list: see
        :meth:`order`.
        """
        children: list[object] = []
        children.extend(self._posts())
        for span in self.panels():
            children.extend(self._panel(span))
        for span in self.gate_openings():
            children.extend(self._gate(span))
        return Compound(children=children, label=f"avo_fence_{self.style}")

    def _stock(self, choice: StockChoice, **kwargs: object) -> dict[str, object]:
        """Return the keyword arguments a part made from *choice* needs."""
        if choice.actual_in is not None:
            kwargs["actual_mm"] = (choice.thickness, choice.width)
        return dict(
            material=self.species,
            nominal=choice.nominal,
            rough=choice.rough,
            grade=choice.grade,
            stock_profile=choice.profile,
            **kwargs,
        )

    def _posts(self) -> list[object]:
        """Return every post, front faces coplanar at ``y = 0``."""
        out: list[object] = []
        kinds = self.posts()
        for index, post in enumerate(kinds):
            choice = self.gate_post if post.is_gate_post else self.post
            where = "end" if index in (0, len(kinds) - 1) else "line"
            board = Board(
                length_mm=post.length,
                label="gate_post" if post.is_gate_post else f"{where}_post",
                notes=(
                    f"{self.post_length_ft:g} ft post, bored at the mill for "
                    f"the rail dowels; {post.embedment / IN:.0f}\" in the "
                    f"ground, {(post.length - post.embedment) / IN:.0f}\" above "
                    "grade"
                ),
                **self._stock(choice),
            )
            z = post.length / 2 - post.embedment
            out.append(
                Pos(post.x, -post.size / 2, z) * UPRIGHT_POST * board
            )
        return out

    def _panel(self, span: Span) -> list[object]:
        """Return one panel, drawn as the parts it is assembled from."""
        posts = {round(p.x, 6): p for p in self.posts()}
        left, right = posts[round(span.x0, 6)], posts[round(span.x1, 6)]
        clear = span.length - left.size / 2 - right.size / 2
        centre = (span.x0 + span.x1) / 2
        z0 = inches(self.ground_clearance_in)
        custom = span in self.odd_panels()
        tag = "custom_" if custom else ""

        if self.spec.infill == "tongue_and_groove":
            return self._framed_panel(centre, clear, z0, tag)
        if self.spec.infill == "baluster":
            return self._baluster_panel(span, centre, clear, z0, tag)
        return self._railed_panel(span, centre, clear, z0, tag)

    def _railed_panel(
        self, span: Span, centre: float, clear: float, z0: float, tag: str
    ) -> list[object]:
        """Return a stockade, privacy or spaced panel: two rails and boards."""
        out: list[object] = []
        rail_y = -self.post_size / 2
        for z, where in (
            (z0 + inches(self.rail_inset_in), "bottom"),
            (z0 + self.height - inches(self.rail_inset_in), "top"),
        ):
            out.append(
                Pos(centre, rail_y, z)
                * ALONG_RUN
                * Board(
                    length_mm=span.length,
                    label=f"{tag}panel_rail",
                    notes=(
                        f"{where} rail, dowelled into the post at each end and "
                        "double-nailed"
                    ),
                    **self._stock(self.rail),
                )
            )
        out.extend(
            self._boards(centre, clear, z0, rail_y + self.rail.thickness / 2, tag)
        )
        return out

    def _framed_panel(
        self, centre: float, clear: float, z0: float, tag: str
    ) -> list[object]:
        """Return a Universal panel: tongue and groove inside a picture frame."""
        out: list[object] = []
        # 6/4x4, as the catalogue names it.  It does not publish the dressed
        # size, so the frame is drawn at the full quarter thickness.
        frame = StockChoice(
            "6/4x4", grade=self.grade, profile="dressed", actual_in=(1.5, 4.0)
        )
        rail_y = -self.post_size / 2
        f_w, f_t = frame.width, frame.thickness
        for z in (z0 + f_w / 2, z0 + self.height - f_w / 2):
            out.append(
                Pos(centre, rail_y, z)
                * ALONG_RUN
                * Board(
                    length_mm=clear,
                    label=f"{tag}frame_rail",
                    notes="6/4x4 picture frame — the panel reads the same from "
                    "both sides, which is the whole point of it",
                    **self._stock(frame),
                )
            )
        for side in (-1, 1):
            out.append(
                Pos(centre + side * (clear - f_w) / 2, rail_y, z0 + self.height / 2)
                * UPRIGHT
                * Board(
                    length_mm=self.height,
                    label=f"{tag}frame_stile",
                    notes="6/4x4 picture frame",
                    **self._stock(frame),
                )
            )
        inner = clear - 2 * f_w
        out.extend(
            self._boards(
                centre,
                inner,
                z0 + f_w,
                rail_y + f_t / 2,
                tag,
                height=self.height - 2 * f_w,
            )
        )
        return out

    def _baluster_panel(
        self, span: Span, centre: float, clear: float, z0: float, tag: str
    ) -> list[object]:
        """Return a Chestnut Hill panel: 2x2 balusters between doubled rails."""
        out: list[object] = []
        top_rail = StockChoice(
            "6/4x4", grade=self.grade, profile="dressed", actual_in=(1.5, 4.0)
        )
        bottom_rail = StockChoice(
            "6/4x6", grade=self.grade, profile="dressed", actual_in=(1.5, 6.0)
        )
        baluster = StockChoice("2x2", grade=self.grade, profile="dressed")
        rail_y = -self.post_size / 2
        for choice, z, where in (
            (bottom_rail, z0 + bottom_rail.width / 2, "bottom"),
            (top_rail, z0 + self.height - top_rail.width / 2, "top"),
        ):
            # Both sides: the rails sandwich the balusters, which is why this
            # style looks the same from the neighbour's garden.
            for side in (-1, 1):
                out.append(
                    Pos(
                        centre,
                        rail_y + side * (baluster.thickness + choice.thickness) / 2,
                        z,
                    )
                    * ALONG_RUN
                    * Board(
                        length_mm=span.length,
                        label=f"{tag}chestnut_{where}_rail",
                        notes=f"{where} rail, one each side of the balusters",
                        **self._stock(choice),
                    )
                )
        inner_z0 = z0 + bottom_rail.width
        inner_h = self.height - bottom_rail.width - top_rail.width
        run = self.board_run(clear)
        pitch = baluster.width + run.gap
        x0 = centre - clear / 2
        for i in range(run.count):
            out.append(
                Pos(x0 + i * pitch + baluster.width / 2, rail_y, inner_z0 + inner_h / 2)
                * UPRIGHT
                * Board(
                    length_mm=inner_h,
                    label=f"{tag}baluster",
                    notes=f"2x2 baluster, {mm_to_fractional_inch(run.gap, 32)} apart",
                    **self._stock(baluster),
                )
            )
        return out

    def _boards(
        self,
        centre: float,
        cover: float,
        z0: float,
        y: float,
        tag: str,
        height: float | None = None,
    ) -> list[object]:
        """Return the infill boards across *cover*, centred on *centre*."""
        out: list[object] = []
        # The board is given its size directly rather than through a nominal
        # lookup: the catalogue publishes 7/8" x 2-7/8" and 3/4" x 3-1/2",
        # which are milled sizes and not any nominal size's dressed answer.
        board_h = self.height if height is None else height
        run = self.board_run(cover)
        pitch = (
            self.spec.board_w + run.gap
            if self.spec.infill == "spaced"
            else cover / run.count
        )
        x0 = centre - cover / 2
        for i in range(run.count):
            width = self.spec.board_w
            if run.last_width is not None and i == run.count - 1:
                width = run.last_width
            out.append(
                Pos(
                    x0 + i * pitch + width / 2,
                    y + self.spec.board_t / 2,
                    z0 + board_h / 2,
                )
                * UPRIGHT
                * Board(
                    length_mm=board_h,
                    thickness_mm=self.spec.board_t,
                    width_mm=width,
                    material=self.species,
                    label=f"{tag}board",
                    grade=self.grade,
                    stock_profile=f"{self.spec.name.lower()} board",
                    notes=(
                        f'{self.spec.board_t_in:g}" x {self.spec.board_w_in:g}" '
                        + (
                            "butted"
                            if self.spec.infill != "spaced"
                            else f"at {mm_to_fractional_inch(run.gap, 32)} apart"
                        )
                    ),
                )
            )
        return out

    def _gate(self, span: Span) -> list[object]:
        """Return the leaves hanging in *span*.

        Drawn, and deliberately not costed: the catalogue says every gate is
        custom and quoted by email, so what this produces is a picture and a
        specification to send them, not a line item.
        """
        out: list[object] = []
        clear = span.length - self.gate_post_size
        hinge, middle = inches(0.375), inches(0.75)
        width = (clear - 2 * hinge - (self.gate_leaves - 1) * middle) / self.gate_leaves
        z0 = inches(3.0)
        height = self.height - inches(1.0)
        x = span.x0 + self.gate_post_size / 2 + hinge
        for leaf in range(self.gate_leaves):
            out.extend(self._leaf(x, width, z0, height, hinged_left=leaf == 0))
            x += width + middle
        return out

    def _leaf(
        self, x0: float, width: float, z0: float, height: float, hinged_left: bool
    ) -> list[object]:
        """Return one gate leaf: a braced frame with the panel's own infill."""
        out: list[object] = []
        frame = self.rail
        f_w, f_t = frame.width, frame.thickness
        y = -f_t / 2
        for side in (0, 1):
            out.append(
                Pos(x0 + f_w / 2 + side * (width - f_w), y, z0 + height / 2)
                * UPRIGHT
                * Board(
                    length_mm=height,
                    label="gate_stile",
                    notes="hinge stile" if side == 0 else "latch stile",
                    **self._stock(frame),
                )
            )
        rail_length = width - 2 * f_w
        for z in (z0 + f_w / 2, z0 + height - f_w / 2):
            out.append(
                Pos(x0 + width / 2, y, z)
                * ALONG_RUN
                * Board(
                    length_mm=rail_length,
                    label="gate_rail",
                    **self._stock(frame),
                )
            )
        inner_h = height - 2 * f_w
        brace_length = math.hypot(rail_length, inner_h)
        angle = math.degrees(math.atan2(inner_h, rail_length))
        tilt = (90.0 - angle) if hinged_left else -(90.0 - angle)
        out.append(
            Pos(x0 + width / 2, y, z0 + height / 2)
            * Rotation(0, tilt, 0)
            * UPRIGHT
            * Board(
                length_mm=brace_length,
                label="gate_brace",
                notes=f"{angle:.0f}° from horizontal, foot at the hinge side",
                **self._stock(frame),
            )
        )
        out.extend(
            self._boards(x0 + width / 2, width, z0, y + f_t / 2, "gate_", height=height)
        )
        return out

    # ------------------------------------------------------------------
    # Ordering, which is what a panel fence has instead of a cut list
    # ------------------------------------------------------------------

    def panel_stock(self, height_ft: float | None = None) -> Any:
        """Return the catalogue entry for this style's panel, or ``None``."""
        want = f"AVO {self.spec.name} fence panel"
        size = f"{height_ft or self.height_ft:g} ft H x 8 ft L"
        for entry in self.inventory.unit_goods:
            if entry.item == want and entry.size == size:
                return entry
        return None

    def post_stock(self, choice: StockChoice) -> Any:
        """Return the catalogue entry for a post, or ``None``."""
        try:
            return choice.entry(self.inventory, self.species)
        except KeyError:
            return None

    def cap_stock(self) -> Any:
        """Return the catalogue entry for a post cap, or ``None``."""
        for entry in self.inventory.unit_goods:
            if entry.item == "AVO post cap":
                return entry
        return None

    def order(self) -> PanelOrder:
        """Return what to put on the order: panels, posts, caps, and gates.

        Nothing here is a length.  A panel fence is bought by the piece, and
        the only arithmetic is counting — which is exactly why the run not
        dividing into 8 ft matters so much more here than it would on a fence
        somebody cuts on site.
        """
        lines: list[tuple[str, int, str]] = []
        unpriced: list[str] = []
        quoted: list[str] = []
        stock_used: list[Any] = []

        full = [s for s in self.panels() if s not in self.odd_panels()]
        entry = self.panel_stock()
        label = (
            f"{self.spec.name} panel, {self.height_ft:g} ft H x "
            f"{self.panel_ft:g} ft L, {self.grade}"
        )
        if full:
            lines.append((label, len(full), "panel"))
        for span in self.odd_panels():
            lines.append(
                (
                    f"{self.spec.name} panel, {self.height_ft:g} ft H x "
                    f"{mm_to_fractional_inch(span.length)} L, {self.grade} "
                    "— CUSTOM",
                    1,
                    "panel",
                )
            )
        if entry is not None:
            stock_used.append(entry)
            if entry.price is None:
                unpriced.append(entry.stock_label)

        kinds = self.post_kinds()
        gate_posts = [p for p in self.posts() if p.is_gate_post]
        line_posts = kinds["line"] - len(gate_posts)
        for count, what in (
            (kinds["end"], f"{self.post.nominal} end post, pre-routed"),
            (line_posts, f"{self.post.nominal} line post, pre-routed"),
            (
                len(gate_posts),
                f"{self.gate_post.nominal} gate post, pre-routed",
            ),
        ):
            if count:
                length_ft = (
                    self.post_length_ft + 2.0
                    if "gate" in what
                    else self.post_length_ft
                )
                lines.append((f"{what}, {length_ft:g} ft", count, "post"))
        for choice in (self.post, self.gate_post):
            stock = self.post_stock(choice)
            if stock is None or any(stock is used for used in stock_used):
                continue
            stock_used.append(stock)
            if stock.price is None:
                unpriced.append(stock.stock_label)

        caps = len(self.posts())
        lines.append(("post cap", caps, "each"))
        cap = self.cap_stock()
        if cap is not None:
            stock_used.append(cap)
            if cap.price is None:
                unpriced.append(cap.stock_label)

        leaves = len(self.gate_openings()) * self.gate_leaves
        if leaves:
            quoted.append(
                f"{leaves} gate leaves for "
                f"{len(self.gate_openings())} openings of "
                f"{self.gate_section_ft:g} ft"
            )
        return PanelOrder(
            lines=lines, unpriced=unpriced, quoted=quoted, stock_used=stock_used
        )

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def check(self, assembly: Compound, parts: list[CutPart]) -> CheckReport:
        """Run every design check against a built panel fence.

        Parameters
        ----------
        assembly : build123d.Compound
            The result of :meth:`build`.
        parts : list[CutPart]
            The extracted parts.  Useful for mass and materials; it is *not*
            an order — see :meth:`order`.

        Returns
        -------
        CheckReport
            All findings, in reporting order.
        """
        report = CheckReport()
        report.extend(self._check_layout())
        report.extend(self._check_catalogue())
        report.extend(self._check_posts())
        report.extend(self._check_assumptions())
        report.extend(self._check_gates())
        report.extend(check_material_suitability(parts, self.inventory))
        return report

    def _check_layout(self) -> list[Finding]:
        """Report how the run divides into panels, which it usually does not."""
        panels = self.panels()
        odd = self.odd_panels()
        findings = [
            Finding(
                Severity.INFO,
                "layout",
                f"{self.overall_length / FT:.0f} ft overall: "
                f"{len(panels)} panels and {len(self.posts())} posts, plus "
                f"{len(self.gate_openings())} gate opening"
                f"{'s' if len(self.gate_openings()) != 1 else ''} of "
                f"{self.gate_section_ft:g} ft",
            )
        ]
        if odd:
            widths = ", ".join(mm_to_fractional_inch(s.length) for s in odd)
            stretch_ft = (self.run_ft / self.gates) if self.gates else self.run_ft
            down = int(stretch_ft // self.panel_ft) * self.panel_ft
            up = down + self.panel_ft
            findings.append(
                Finding(
                    Severity.WARN,
                    "layout",
                    f"{self.run_ft:g} ft of fence does not divide into "
                    f"{self.panel_ft:g} ft panels: {len(panels) - len(odd)} "
                    f"come off the shelf and {len(odd)} ({widths}) have to be "
                    "made to size. The catalogue builds custom panels and does "
                    "not stock them, so that is lead time and a separate "
                    f"price — each stretch here is {stretch_ft:g} ft, and "
                    f"{down:g} ft or {up:g} ft would take whole panels",
                )
            )
        else:
            findings.append(
                Finding(
                    Severity.INFO,
                    "layout",
                    f"the run divides into {len(panels)} whole panels, which "
                    "is the cheapest thing a panel fence can do",
                )
            )
        return findings

    def _check_catalogue(self) -> list[Finding]:
        """Report what was ordered against what the catalogue actually sells."""
        findings: list[Finding] = []
        spec = self.spec
        findings.append(
            Finding(
                Severity.INFO,
                "catalogue",
                f"{spec.name}: {spec.summary}. Boards "
                f'{spec.board_t_in:g}" x {spec.board_w_in:g}", rails 2" x 3" '
                f"S2S dowelled Colonial, {self.grade} — the other grades are "
                f"{', '.join(g for g in spec.grades if g != self.grade)}",
            )
        )
        if self.height_ft in AVO_PANEL_HEIGHTS_FT:
            findings.append(
                Finding(
                    Severity.INFO,
                    "catalogue",
                    f"{self.height_ft:g} ft is a stocked height "
                    f"({', '.join(f'{h:g}' for h in AVO_PANEL_HEIGHTS_FT)} ft "
                    "in every style)",
                )
            )
        else:
            findings.append(
                Finding(
                    Severity.WARN,
                    "catalogue",
                    f"{self.height_ft:g} ft is not a stocked height — the "
                    "catalogue lists "
                    f"{', '.join(f'{h:g}' for h in AVO_PANEL_HEIGHTS_FT)} ft, "
                    "so every panel here is custom",
                )
            )
        findings.append(
            Finding(
                Severity.INFO,
                "catalogue",
                f"top and board options for this style: "
                f"{', '.join(spec.options)} — each sold per panel, and each "
                "quantity has to match the panel count exactly",
            )
        )
        panels = self.panels()
        if panels and self.spec.infill != "baluster":
            first = panels[0]
            clear = first.length - self.post_size
            run = self.board_run(clear)
            if run.last_width is not None and run.last_width < inches(1.0):
                findings.append(
                    Finding(
                        Severity.WARN,
                        "infill",
                        f"an {self.panel_ft:g} ft panel of "
                        f'{spec.board_w_in:g}" boards ends on a '
                        f"{mm_to_fractional_inch(run.last_width, 32)} sliver. "
                        "The mill will not build it that way — it rips two "
                        "boards to share the remainder — so treat the board "
                        "count here as one board and a rip, not as gospel",
                    )
                )
        findings.append(
            Finding(
                Severity.INFO,
                "ordering",
                "nothing in this design is cut: it is an order for panels, "
                "posts and caps. The parts below are what the panels are made "
                "of, drawn so the checks have something to measure",
            )
        )
        return findings

    def _check_posts(self) -> list[Finding]:
        """Check the posts against the catalogue's own sizing table."""
        findings: list[Finding] = []
        table = AVO_POST_TABLE.get(self.height_ft)
        embed_in = self.embedment / IN
        if table is not None:
            _length, burial_ft = table
            findings.append(
                Finding(
                    Severity.INFO,
                    "stock",
                    f"the catalogue pairs a {self.height_ft:g} ft fence with a "
                    f"{self.post_length_ft:g} ft post: "
                    f"{self.height_ft:g} ft up and {burial_ft:g} ft down",
                )
            )
            if abs(embed_in - burial_ft * 12) > 1.0:
                findings.append(
                    Finding(
                        Severity.INFO,
                        "stock",
                        f"hanging the panel {self.ground_clearance_in:g}\" clear "
                        f"of grade puts its top at "
                        f"{self.above_grade / IN:.0f}\", so the post has to "
                        f"stand that high and only {embed_in:.0f}\" is left in "
                        f"the ground rather than the {burial_ft * 12:.0f}\" "
                        "their table assumes — the gap under a panel comes out "
                        "of the hole",
                    )
                )

        deep_enough = embed_in >= FROST_DEPTH_IN - 1e-6
        findings.append(
            Finding(
                Severity.INFO if deep_enough else Severity.WARN,
                "frost",
                f"{embed_in:.0f}\" of post in the ground against a "
                f"{FROST_DEPTH_IN:.0f}\" frost depth for southern Maine"
                + (
                    ""
                    if deep_enough
                    else " — this is the catalogue's own sizing, and it is "
                    "half the depth the frost line asks for. It is what most "
                    "of these fences are built to and it is why they lean; "
                    f"the next post up ({self.post_length_ft + 2:g} ft) buys "
                    f"{embed_in + 24:.0f}\" and costs one post size"
                ),
            )
        )
        kinds = self.post_kinds()
        findings.append(
            Finding(
                Severity.INFO,
                "ordering",
                f"pre-routed posts are bored on the faces the rails come into, "
                f"so they are ordered by position: {kinds['end']} end and "
                f"{kinds['line']} line. A line post in an end position is a "
                "post with a hole in the wrong side of it",
            )
        )
        findings.append(
            Finding(
                Severity.INFO,
                "ordering",
                f"{len(self.posts())} post caps, sold separately — the posts "
                "come without them, and a chamfered top without a cap is the "
                "end grain the chamfer is there to protect",
            )
        )
        return findings

    def _check_assumptions(self) -> list[Finding]:
        """Report the numbers the catalogue does not publish."""
        findings = [
            Finding(
                Severity.WARN,
                "assumed",
                f"the rails are drawn {self.rail_inset_in:g}\" in from the top "
                "and bottom of each panel, which the catalogue does not "
                "publish. It changes nothing you buy and everything about "
                "where the fence looks strongest",
            )
        ]
        if self.spec.infill == "spaced":
            findings.append(
                Finding(
                    Severity.WARN,
                    "assumed",
                    f"the gap between boards is drawn at "
                    f"{self.spacing_in:g}\", which the catalogue does not "
                    "publish either — it is the number that decides how many "
                    "boards are in a panel, so ask before comparing prices "
                    "between styles",
                )
            )
        if self.spec.infill == "tongue_and_groove":
            findings.append(
                Finding(
                    Severity.WARN,
                    "assumed",
                    "a 1x4 tongue and groove board is drawn covering 3/8\" "
                    "less than it measures; the catalogue gives the board and "
                    "not the coverage",
                )
            )
        return findings

    def _check_gates(self) -> list[Finding]:
        """Report what the catalogue says about gates, which is: ask."""
        openings = self.gate_openings()
        if not openings:
            return []
        clear = openings[0].length - self.gate_post_size
        return [
            Finding(
                Severity.WARN,
                "gate",
                f"{len(openings)} openings of "
                f"{mm_to_fractional_inch(clear)} clear are drawn here as "
                f"{self.gate_leaves} braced leaves each, and the catalogue "
                "will not price them: it says every gate is custom and quoted "
                "by email. This drawing is the specification to send, not a "
                "line on the order",
            ),
            Finding(
                Severity.INFO,
                "gate",
                f"the gate posts here are {self.gate_post.nominal} and "
                f"{self.post_length_ft + 2:g} ft — one length up from the line "
                "posts, with every extra inch of it in the ground, which is "
                "where a gate post earns it",
            ),
        ]


# ---------------------------------------------------------------------------
# What Lumbery sells, and what a fence can do with it
# ---------------------------------------------------------------------------

#: Nominal sizes that will serve as fence infill.
BOARD_NOMINALS: frozenset[str] = frozenset(
    {"1x3", "1x4", "1x6", "1x8", "5/4x3", "5/4x4", "5/4x6"}
)

#: Nominal sizes that will serve as rails and gate frames.
RAIL_NOMINALS: frozenset[str] = frozenset({"2x4", "2x6"})

#: Nominal sizes that will serve as posts.
POST_NOMINALS: frozenset[str] = frozenset({"4x4", "6x6"})

#: How ``stock.yaml`` spells round stock.
LOG_PROFILES: frozenset[str] = frozenset({"round post", "round rail"})

#: Smallest log worth a post rather than a rail, in inches.
LOG_POST_DIAMETER_IN: float = 5.0

#: Profiles that mark an entry as part of the pre-assembled panel line.
#:
#: They are cedar, they are stocked, and a stick-built fence cannot use them:
#: a pre-routed post is bored for somebody else's rails and a Colonial rail is
#: half of a panel.  Naming them keeps the stick-built catalogue honest about
#: what it is leaving out.
AVO_COMPONENT_PROFILES: tuple[str, ...] = (
    "pre-routed",
    "Colonial rail",
    "fence picket",
)


@dataclass(frozen=True)
class Variant:
    """One inventory entry, the role it can fill, and what it costs.

    Parameters
    ----------
    choice : StockChoice or None
        The entry, as a design would name it.  ``None`` for stock that is not
        lumber and cannot fill a lumber role — the mesh, which is bought by
        the roll.
    role : str
        ``"board"``, ``"rail"``, ``"post"`` or ``"mesh"``.
    stock : DimensionalStock or UnitStock
        The inventory entry itself, for its rate and provenance.
    note : str, optional
        What is worth knowing before choosing it.
    requires_style : str or None, optional
        The style this entry can only be built in.  Logs and mesh belong to
        ``"log_and_mesh"`` and to nothing else: a log is not a picket and a
        roll of wire is not a board.
    """

    choice: StockChoice | None
    role: str
    stock: Any
    note: str = ""
    requires_style: str | None = None

    @property
    def rate(self) -> float | None:
        """Cost of one unit of this entry."""
        return self.stock.price


def variants(
    inventory: Inventory, species: str = "white_cedar"
) -> tuple[list[Variant], list[tuple[str, str]]]:
    """Return every stocked entry a fence can use, and every one it cannot.

    The point of the second list is that a catalogue which silently drops what
    it cannot handle reads exactly like a catalogue of everything available.
    Lumbery sells shakes by the bundle and lattice by the sheet, and this
    fence can use neither; that is a fact about the fence, and it belongs on
    the page next to the things it can use.

    Parameters
    ----------
    inventory : Inventory
        Stock to read.
    species : str, optional
        Species, default ``"white_cedar"``.

    Returns
    -------
    usable : list[Variant]
        Entries that will serve, in role then price order.
    unusable : list[tuple[str, str]]
        ``(stock_label, reason)`` for everything else the supplier sells.
    """
    usable: list[Variant] = []
    unusable: list[tuple[str, str]] = []

    for entry in inventory.dimensional:
        if entry.species != species:
            continue
        if entry.profile in LOG_PROFILES:
            usable.append(_log_variant(entry))
            continue
        if any(mark in entry.profile for mark in AVO_COMPONENT_PROFILES):
            unusable.append(
                (
                    entry.stock_label,
                    "part of the AVO panel line, sold by the piece rather than "
                    "by the foot — see --panels",
                )
            )
            continue
        choice = StockChoice(entry.nominal, entry.grade, entry.profile)
        if entry.price_per_piece is not None:
            unusable.append(
                (
                    entry.stock_label,
                    f"sold as a {entry.priced_length_ft:g} ft piece — shorter "
                    "than anything in this fence",
                )
            )
            continue
        if entry.nominal in BOARD_NOMINALS:
            note = ""
            if choice.milled:
                note = (
                    f"covers {mm_to_fractional_inch(choice.covers, 32)} of a "
                    f"{mm_to_fractional_inch(choice.width)} face (assumed); "
                    "butts solid, so it cannot be spaced or lapped"
                )
            elif not choice.rough:
                note = "dressed, so narrower than its nominal size"
            usable.append(Variant(choice, "board", entry, note))
        elif entry.nominal in RAIL_NOMINALS:
            usable.append(Variant(choice, "rail", entry))
        elif entry.nominal in POST_NOMINALS:
            note = "" if entry.nominal == "6x6" else "line posts; a gate wants 6x6"
            usable.append(Variant(choice, "post", entry, note))
        else:  # pragma: no cover - every stocked size is classified today
            unusable.append((entry.stock_label, "no role in this fence"))

    for entry in inventory.unit_goods:
        if entry.material == MESH_MATERIAL:
            usable.append(
                Variant(
                    choice=None,
                    role="mesh",
                    stock=entry,
                    note=(
                        "bought by the roll and cut to the bay; the infill of "
                        "the log fence and of nothing else here"
                    ),
                    requires_style="log_and_mesh",
                )
            )
            continue
        if entry.species != species:
            continue
        unusable.append(
            (
                entry.stock_label,
                f"sold by the {entry.unit}, and nothing in these designs is "
                "laid up that way"
                + (
                    ""
                    if entry.coverage_sqft is not None
                    else " — the guide publishes no coverage for it either"
                ),
            )
        )

    order = {"board": 0, "rail": 1, "post": 2, "mesh": 3}
    usable.sort(key=lambda v: (order[v.role], v.rate or 0.0))
    return usable, unusable


def _log_variant(entry: Any) -> Variant:
    """Return the :class:`Variant` for one round-stock entry.

    Its diameter is in its size label — ``"log 5"`` is a five inch post — and
    the diameter is what decides whether it is a post or a rail.  Nothing else
    in the entry says: round stock has no nominal-size table to consult.
    """
    diameter = float(entry.nominal.split()[-1])
    role = "post" if diameter >= LOG_POST_DIAMETER_IN else "rail"
    return Variant(
        choice=StockChoice(
            entry.nominal, entry.grade, entry.profile, diameter_in=diameter
        ),
        role=role,
        stock=entry,
        note=(
            f"{diameter:g}\" peeled round, bought by the foot; "
            + ("posts and gate posts" if role == "post" else "rails")
        ),
        requires_style="log_and_mesh",
    )


def style_for(choice: StockChoice, style: str) -> str:
    """Return the style *choice* can actually be built in.

    Milled stock interlocks, so it cannot be lapped: a board-on-board fence in
    tongue and groove is a contradiction, and the honest resolution is to butt
    it into a solid fence rather than to refuse to price it.
    """
    if choice.milled and style == "board_on_board":
        return "picket"
    return style


@dataclass(frozen=True)
class PricedVariant:
    """One variant, the fence built from it, and what that fence costs.

    Parameters
    ----------
    variant : Variant
        The entry and its role.
    fence : CedarFence
        The fence built with it.
    parts : list[CutPart]
        That fence's cut list.
    plan : LinealPlan
        Its timber buying plan.
    """

    variant: Variant
    fence: CedarFence
    parts: list[CutPart]
    plan: LinealPlan

    @property
    def summary(self) -> CostSummary:
        """Timber and mesh together, with every gap named."""
        return self.fence.cost_summary(self.parts)

    @property
    def total(self) -> float | None:
        """What is priced, or ``None`` when nothing in it is."""
        return self.summary.total

    @property
    def complete(self) -> bool:
        """``True`` when the total leaves nothing out."""
        return self.summary.complete

    @property
    def lineal_ft(self) -> float:
        """Lineal feet of timber."""
        return self.plan.lineal_ft

    def total_text(self) -> str:
        """Render the total, or say why there is not one."""
        if self.total is None:
            return "unpriced"
        return format_money(self.total) + ("" if self.complete else " part")


def price_variants(
    role: str,
    inventory: Inventory | None = None,
    style: str = "board_on_board",
    **fence_kwargs: Any,
) -> list[PricedVariant]:
    """Build and price the same fence in every entry that fills *role*.

    Parameters
    ----------
    role : str
        ``"board"``, ``"rail"`` or ``"post"``.
    inventory : Inventory, optional
        Stock to price against.  ``None`` loads ``stock.yaml``.
    style : str, optional
        Style to build, default ``"board_on_board"``.  Overridden per variant
        by :attr:`Variant.requires_style`, and adjusted by :func:`style_for`.
    **fence_kwargs
        Passed through to :class:`CedarFence`.

    Returns
    -------
    list[PricedVariant]
        One entry per variant that can fill the role: complete totals first,
        cheapest to dearest, then the partial ones, then anything with no
        price at all.  A partial total is not a cheap one, and sorting the two
        kinds together would put the fence nobody has priced at the top of a
        price table.
    """
    inv = inventory or Inventory.load()
    out: list[PricedVariant] = []
    for variant in variants(inv)[0]:
        if variant.role != role or variant.choice is None:
            continue
        kwargs = dict(fence_kwargs)
        kwargs[role] = variant.choice
        # Varying the rail varies the gate frame with it; they are the same
        # stick in every design here, and a table that changed one without the
        # other would price a fence nobody would build.
        if role == "rail" and variant.requires_style is None:
            kwargs["gate_frame"] = variant.choice
        built = variant.requires_style or style_for(variant.choice, style)
        fence = CedarFence(style=built, inventory=inv, **kwargs)
        parts = extract(fence.build())
        out.append(PricedVariant(variant, fence, parts, fence.plan(parts)))
    return sorted(
        out,
        key=lambda row: (not row.complete, row.total is None, row.total or 0.0),
    )


def discount_note(total: float, inventory: Inventory, supplier: str = "Lumbery") -> str:
    """Say what an order of *total* is worth after the supplier's volume terms.

    A discount is the one price that is a property of the order rather than of
    any board in it, so nothing in the cut list can know about it and every
    total printed elsewhere is the pre-discount one.
    """
    try:
        yard = inventory.supplier(supplier)
    except KeyError:
        return f"no volume terms recorded for {supplier}"
    if not yard.volume_discounts:
        return f"{supplier} publishes no volume discount"

    tier = yard.discount_for(total)
    ahead = yard.next_tier(total)
    if tier is None:
        assert ahead is not None
        short = ahead.over - total
        return (
            f"{format_money(total)} is below {supplier}'s first volume tier: "
            f"{ahead.percent:g}% starts at {format_money(ahead.over)}, "
            f"{format_money(short)} away"
        )
    after = total * (1 - tier.percent / 100)
    text = (
        f"{format_money(total)} qualifies for {supplier}'s "
        f"{tier.percent:g}% tier (over {format_money(tier.over)}) — "
        f"{format_money(after)} after it"
    )
    if ahead is not None:
        text += (
            f"; {ahead.percent:g}% starts at {format_money(ahead.over)}, "
            f"{format_money(ahead.over - total)} away"
        )
    return text


def catalogue(
    inventory: Inventory | None = None,
    style: str = "board_on_board",
) -> str:
    """Return every Lumbery cedar variant, priced as this fence would buy it.

    Parameters
    ----------
    inventory : Inventory, optional
        Stock to read and price against.  ``None`` loads ``stock.yaml``.
    style : str, optional
        Style to price the infill variants in, default ``"board_on_board"``.

    Returns
    -------
    str
        Three tables — infill, rails, posts — plus what the guide sells that
        this fence cannot use, and the volume terms that apply to the order.
    """
    inv = inventory or Inventory.load()
    lines: list[str] = []

    for role, title in (
        ("board", "INFILL — 38 ft of fence and two gates, boards varied"),
        ("rail", "RAILS AND GATE FRAMES — infill and posts held at the default"),
        ("post", "LINE POSTS — gate posts stay 6x6, infill and rails default"),
    ):
        lines.append(f"\n{title}")
        lines.append(
            f"  {'stock':<38s}{'$/LF':>7s}{'lineal ft':>11s}{'total':>10s}  notes"
        )
        for row in price_variants(role, inv, style):
            variant = row.variant
            built = variant.requires_style or style_for(variant.choice, style)
            note = variant.note
            if built != style:
                note = f"built as {built}; {note}" if note else f"built as {built}"
            rate = "     —" if variant.rate is None else f"{variant.rate:>6.2f}"
            lines.append(
                f"  {variant.choice.label:<38s}"
                f" {rate}{row.lineal_ft:>11.0f}"
                f"{row.total_text():>10s}  {note}"
            )

    mesh = [v for v in variants(inv)[0] if v.role == "mesh"]
    if mesh:
        lines.append("\nMESH — the infill of the log fence, bought by the roll")
        lines.append(
            f"  {'stock':<38s}{'$/roll':>7s}{'covers':>11s}{'':>10s}  notes"
        )
        for variant in mesh:
            rate = "     —" if variant.rate is None else f"{variant.rate:>6.2f}"
            covers = (
                "unpublished"
                if variant.stock.coverage_sqft is None
                else f"{variant.stock.coverage_sqft:g} sq ft"
            )
            # This label is longer than the column, and truncating the one
            # entry that says what the mesh actually is would be the wrong
            # economy: it gets its own line.
            lines.append(f"  {variant.stock.stock_label}")
            lines.append(
                f"  {'':<38s} {rate}{covers:>11s}{'':>10s}  {variant.note}"
            )

    lines.append("\nSOLD BY LUMBERY, NOT USABLE HERE")
    for label, reason in variants(inv)[1]:
        lines.append(f"  {label:<38s} {reason}")

    default = CedarFence(style=style, inventory=inv)
    default_parts = extract(default.build())
    default_total = default.cost_summary(default_parts).total or 0.0
    lines.append(
        "\nRates are per lineal foot unless the column says otherwise, quoted "
        "2026-08-17, and every total is materials only.\nA dash is an entry "
        "nobody has priced: 'unpriced' means the whole fence rests on one, "
        "'part' means the total leaves one out."
        f"\nOn the default build: {discount_note(default_total, inv)}."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def run(
    style: str,
    outdir: Path,
    gate_leaves: int = 2,
    assume_lengths_ft: list[float] | None = None,
) -> CheckReport:
    """Build one fence, write its cut list and views, print the report.

    Parameters
    ----------
    style : str
        One of :data:`STYLES`.
    outdir : Path
        Directory for the generated CSV, Markdown, PNG and CAD files.
    gate_leaves : int, optional
        1 or 2, default 2.
    assume_lengths_ft : list[float], optional
        Stock lengths to lay a cut plan out against.  Nothing in
        ``stock.yaml`` says cedar comes in these lengths — that is the point
        of the flag, and every line it prints says so.

    Returns
    -------
    CheckReport
        The design-check findings.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    fence = CedarFence(style=style, gate_leaves=gate_leaves)
    assembly = fence.build()
    parts = extract(assembly)

    stem = f"cedar_fence_{style}"
    print(f"\n{'=' * 78}\n  Cedar fence — {style.replace('_', ' ')}\n{'=' * 78}")

    df = render_cut_list(
        parts,
        output_csv=outdir / f"{stem}_cutlist.csv",
        output_md=outdir / f"{stem}_cutlist.md",
    )
    print(df.to_string(index=False))

    report = fence.check(assembly, parts)
    print(f"\n-- design checks {'-' * 61}")
    print(report.to_text())

    plan = fence.plan(parts)
    print(f"\n-- cedar to buy {'-' * 62}")
    print(plan.to_text())
    print(CheckReport().extend(fence.check_stock_lengths(plan)).to_text())

    mesh = fence.mesh_plan(parts)
    if mesh is not None:
        print(f"\n-- mesh to buy {'-' * 63}")
        print(mesh.to_text())
        print(f"\n  everything together: {fence.cost_summary(parts).to_text()}")

    print(f"\n-- prices {'-' * 68}")
    print(fence.check_prices(plan, mesh).to_text())
    total = fence.cost_summary(parts).total
    if total is not None:
        print(f"      {discount_note(total, fence.inventory)}")

    if assume_lengths_ft:
        print(f"\n-- cut plan against ASSUMED lengths {'-' * 42}")
        print(_assumed_cut_plan(parts, assume_lengths_ft))

    render_assembly(
        assembly,
        output_png=outdir / f"{stem}.png",
        title=f"Cedar fence — {style.replace('_', ' ')}",
    )
    # The four-up view of a 58 ft fence is 58 ft of fence in a 6" strip. A
    # detail of one bay and one gate is the drawing somebody can actually read.
    render_assembly(
        _detail(fence, assembly),
        output_png=outdir / f"{stem}_detail.png",
        title=f"Cedar fence — {style.replace('_', ' ')} (one bay and a gate)",
    )
    export_assembly(
        assembly,
        output_step=outdir / f"{stem}.step",
        output_stl=outdir / f"{stem}.stl",
    )
    print(f"\nWrote cut list, views and CAD export to {outdir}/")
    return report


def _detail(fence: CedarFence, assembly: Compound) -> Compound:
    """Return the last bay before the first gate, and the gate, as one drawing.

    Four orthographic views of 58 ft of 4 ft fence are 58 ft of fence rendered
    into a strip an inch tall: technically the model, and unreadable.  This
    crops the same model to the stretch where anything happens.

    The children are copied rather than moved.  A build123d ``Compound``
    adopts what it is given, and building the detail out of the real parts
    would quietly empty the assembly it was cropped from.
    """
    gates = fence.gate_openings
    if not gates:
        return assembly
    gate = gates[0]
    before = [s for s in fence.spans() if s.kind == "panel" and s.x1 <= gate.x0 + 1e-6]
    x_lo = before[-1].x0 if before else gate.x0
    x_hi = gate.x1 + fence.gate_post_size
    children = [
        copy.copy(child)
        for child in assembly.children
        if x_lo - 1e-6 <= child.center().X <= x_hi + 1e-6
    ]
    return Compound(children=children, label=f"{assembly.label}_detail")


def _assumed_cut_plan(parts: list[CutPart], lengths_ft: list[float]) -> str:
    """Lay a cut plan out against lengths the supplier has not published."""
    from woodshop.cutlist.optimize_1d import optimize_1d

    lengths_mm = [ft * FT for ft in lengths_ft]
    header = (
        "  ASSUMED: stock.yaml records no lengths for white cedar. These "
        f"{', '.join(f'{ft:g} ft' for ft in lengths_ft)} sticks are your "
        "assumption, not the supplier's, and every number below rests on it."
    )
    try:
        result = optimize_1d(parts, stock_lengths_mm=lengths_mm)
    except ValueError as exc:
        return f"{header}\n  (!) {exc}"
    return (
        f"{header}\n  {result.stock_used} pieces, "
        f"{sum(result.waste_mm) / FT:.0f} ft of offcut"
    )


#: What each panel component is *priced as* when a panel fence is benchmarked
#: against the sawn price guide, and how good the substitution is.
#:
#: Every one of these is a substitution, because AVO mills to sizes the guide
#: does not sell: a 7/8" x 2-7/8" board is not any line on that list.  The
#: benchmark exists to answer "what is the wood in this panel worth at the
#: yard's own sawn rates?", which is a floor and not a price — a panel also
#: buys the milling, the assembly, the dowelling, stainless nails, delivery
#: and the mill's margin, none of which are wood.
BENCHMARK_AS: dict[str, tuple[StockChoice | None, str]] = {
    'board 7/8" x 2-7/8"': (
        StockChoice("1x3", "STK", "dressed"),
        'priced as a dressed 1x3, which is 3/4" x 2-1/2" — a little less wood',
    ),
    'board 3/4" x 3-1/2"': (
        StockChoice("1x4", "STK", "dressed"),
        "priced as a dressed 1x4, which is exactly that size",
    ),
    "rail 2x3": (
        StockChoice("2x4", "STK", "rough sawn"),
        "the guide has no 2x3; a rough 2x4 is a third bigger",
    ),
    "post 4x4": (
        StockChoice("4x4", "STK", "rough sawn"),
        "the same size, sawn rather than bored and chamfered",
    ),
    "post 6x6": (
        StockChoice("6x6", "STK", "rough sawn"),
        "the same size, sawn rather than bored and chamfered",
    ),
    "frame 6/4x4": (
        StockChoice("5/4x4", "STK", "rough sawn"),
        "the guide stops at 5/4, so this is one quarter thin",
    ),
    "frame 6/4x6": (
        StockChoice("5/4x6", "STK", "eased edge decking"),
        "as above, in the nearest 6\" item the guide carries",
    ),
    "baluster 2x2": (
        None,
        "the guide has no 2x2 at all — this wood is not benchmarked",
    ),
}


def _benchmark_key(part: CutPart) -> str:
    """Return the :data:`BENCHMARK_AS` key for a drawn panel part."""
    if part.label.endswith("baluster"):
        return "baluster 2x2"
    if "frame" in part.label:
        return f"frame 6/4x{'6' if part.width_mm > 5 * IN else '4'}"
    if "chestnut" in part.label:
        return f"frame 6/4x{'6' if part.width_mm > 5 * IN else '4'}"
    if part.label.endswith("post"):
        return f"post {part.nominal}"
    if "rail" in part.label or "stile" in part.label or "brace" in part.label:
        return "rail 2x3"
    return (
        f'board {mm_to_fractional_inch(part.thickness_mm, 32)} x '
        f"{mm_to_fractional_inch(part.width_mm, 32)}"
    )


def benchmark(fence: PanelFence) -> tuple[CostSummary, list[str]]:
    """Price the wood in a panel fence at the yard's own sawn rates.

    Not a panel price, and it must never be read as one.  It answers the
    narrower question a published price list *can* answer: if you bought this
    much cedar as sticks off the guide, what would it come to?  The difference
    between that and what the panels cost is what the mill's work is worth,
    and the only way to learn it is to ask them.

    Parameters
    ----------
    fence : PanelFence
        The panel design to weigh.

    Returns
    -------
    summary : CostSummary
        The benchmark, with the guide's own dates on it.
    notes : list[str]
        One line per substitution made, because every one of them is an
        assumption and the total is only as good as they are.
    """
    parts = extract(fence.build())
    feet: dict[str, float] = {}
    for part in parts:
        if part.material != fence.species:
            continue
        key = _benchmark_key(part)
        feet[key] = feet.get(key, 0.0) + part.length_mm * part.qty / FT

    lines: list[PriceLine] = []
    unpriced: list[str] = []
    notes: list[str] = []
    for key, lineal_ft in sorted(feet.items()):
        mapped = BENCHMARK_AS.get(key)
        if mapped is None or mapped[0] is None:
            reason = "no equivalent on the guide" if mapped is None else mapped[1]
            unpriced.append(f"{key} ({lineal_ft:.0f} LF)")
            notes.append(f"{key}: {reason}")
            continue
        choice, note = mapped
        try:
            entry = choice.entry(fence.inventory, fence.species)
        except KeyError:
            unpriced.append(f"{key} ({lineal_ft:.0f} LF)")
            notes.append(f"{key}: {note} — and that entry is not in stock.yaml")
            continue
        if entry.price is None:
            unpriced.append(entry.stock_label)
            notes.append(f"{key}: {note} — and that entry has no price")
            continue
        lines.append(entry.price_line(lineal_ft * (1.0 + OFFCUT_ALLOWANCE)))
        notes.append(f"{key} ({lineal_ft:.0f} LF): {note}")
    return CostSummary.of(lines, unpriced), notes


def compare_designs() -> str:
    """Compare the three designs, as far as the published prices allow.

    None of the three can be costed from a published price: two are panels
    and one is post and rail components, and The Lumbery publishes the
    catalogue in the page and the money behind an API.  So this compares what
    *can* be compared — the wood in each, the pieces, what each buys that the
    others do not — and prices that wood at the yard's own sawn rates so the
    gap between "what the material is worth" and "what they charge" has a
    floor under it.
    """
    out: list[str] = []
    out.append("THE THREE DESIGNS — 38 ft at 4 ft, plus two 10 ft gate sections")
    out.append(
        f"  {'design':<30s}{'bd ft':>7s}{'pieces':>10s}{'posts':>7s}"
        f"{'catalogue':>11s}   wood at guide rates"
    )
    for key, (name, factory, _summary) in DESIGNS.items():
        fence = factory()
        parts = extract(fence.build())
        # Round rails and posts hold pi/4 of the wood their blank would, the
        # same correction :attr:`LinealPlan.board_feet` makes, so a log fence
        # is not credited with corners it never had.
        board_feet = sum(
            p.length_mm * p.width_mm * p.thickness_mm * p.qty
            * (math.pi / 4.0 if p.shape in ("pole", "turned") else 1.0)
            for p in parts
            if p.material == fence.species
        ) / (25.4**3) / 144.0
        if isinstance(fence, PanelFence):
            pieces = f"{len(fence.panels())} panels"
            mark, _notes = benchmark(fence)
        else:
            pieces = f"{len(fence.spans()) - len(fence.gate_openings)} bays"
            mark = fence.cost_summary(parts)
        floor = (
            format_money(mark.total) if mark.total is not None else "unpriced"
        )
        if not mark.complete:
            floor += "+"
        out.append(
            f"  {name:<30s}{board_feet:>7.0f}{pieces:>10s}"
            f"{len(fence.posts()):>7d}{'unpriced':>11s}   {floor}"
        )

    out.append("")
    out.append(
        "Nothing in the catalogue column is a price, because the catalogue "
        "does not publish one:\nthe panels, the posts, the caps and the mesh "
        "are all recorded with their sizes and no\nmoney. The right-hand "
        "column is the *wood*, priced as the nearest sticks on the sawn\n"
        "guide, and it is a floor: a panel also buys milling, assembly, "
        "stainless nails and\ndelivery, and every gate in all three is quoted "
        "by email rather than priced at all."
    )
    out.append("")
    out.append("FOR REFERENCE — the same run built from sticks, which the guide does price")
    out.append(
        f"  {'style':<30s}{'bd ft':>7s}{'lineal ft':>10s}{'posts':>7s}"
        f"{'total':>11s}"
    )
    for style in ("picket", "board_on_board"):
        fence = CedarFence(style=style)
        parts = extract(fence.build())
        plan = fence.plan(parts)
        summary = fence.cost_summary(parts)
        total = (
            format_money(summary.total)
            if summary.total is not None
            else "unpriced"
        )
        out.append(
            f"  {style:<30s}{plan.board_feet:>7.0f}{plan.lineal_ft:>10.0f}"
            f"{len(fence.posts()):>7d}{total:>11s}"
        )
    out.append(
        "  ...excluding hardware, stone and labour, and cut on site rather "
        "than delivered."
    )
    return "\n".join(out)


def compare(styles: tuple[str, ...] = STYLES) -> str:
    """Return a table comparing what each style costs to build.

    Parameters
    ----------
    styles : tuple of str, optional
        Styles to compare, default all of :data:`STYLES`.

    Returns
    -------
    str
        One row per style: boards, lineal feet, mass, and the total with its
        provenance attached.
    """
    rows = [
        f"  {'style':<16s}{'parts':>7s}{'lineal ft':>11s}{'mass':>9s}  total",
    ]
    for style in styles:
        fence = CedarFence(style=style)
        parts = extract(fence.build())
        plan = fence.plan(parts)
        rows.append(
            f"  {style:<16s}{sum(p.qty for p in parts):>7d}"
            f"{plan.lineal_ft:>11.0f}{estimate_mass_kg(parts):>8.0f}kg  "
            f"{fence.cost_summary(parts).to_text()}"
        )
    return "\n".join(rows)


def run_design(key: str, outdir: Path) -> CheckReport:
    """Build one of the three designs and write everything it produces.

    Parameters
    ----------
    key : str
        A key of :data:`DESIGNS`.
    outdir : Path
        Directory for the generated files.

    Returns
    -------
    CheckReport
        The design-check findings.
    """
    name, factory, summary = DESIGNS[key]
    fence = factory()
    if isinstance(fence, PanelFence):
        return run_panels(fence.style, outdir)
    return run(fence.style, outdir)


def run_panels(style: str, outdir: Path, height_ft: float = 4.0) -> CheckReport:
    """Build one AVO panel fence, write its drawings, print its order.

    Parameters
    ----------
    style : str
        A key of :data:`AVO_STYLES`.
    outdir : Path
        Directory for the generated files.
    height_ft : float, optional
        Panel height, default 4.

    Returns
    -------
    CheckReport
        The design-check findings.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    fence = PanelFence(style=style, height_ft=height_ft)
    assembly = fence.build()
    parts = extract(assembly)

    stem = f"avo_fence_{style}"
    name = f"{fence.spec.name} panels — {height_ft:g} ft"
    print(f"\n{'=' * 78}\n  {name}\n{'=' * 78}")

    df = render_cut_list(
        parts,
        output_csv=outdir / f"{stem}_parts.csv",
        output_md=outdir / f"{stem}_parts.md",
    )
    print(df.to_string(index=False))

    report = fence.check(assembly, parts)
    print(f"\n-- design checks {'-' * 61}")
    print(report.to_text())

    order = fence.order()
    print(f"\n-- the order {'-' * 65}")
    print(order.to_text())
    print(f"\n  {order.cost_summary.to_text()}")

    render_assembly(
        assembly, output_png=outdir / f"{stem}.png", title=name
    )
    render_assembly(
        _panel_detail(fence, assembly),
        output_png=outdir / f"{stem}_detail.png",
        title=f"{name} (one panel and a gate)",
    )
    export_assembly(
        assembly,
        output_step=outdir / f"{stem}.step",
        output_stl=outdir / f"{stem}.stl",
    )
    print(f"\nWrote parts list, views and CAD export to {outdir}/")
    return report


def _panel_detail(fence: PanelFence, assembly: Compound) -> Compound:
    """Return the last panel before the first gate, and the gate."""
    gates = fence.gate_openings()
    if not gates:
        return assembly
    gate = gates[0]
    before = [s for s in fence.panels() if s.x1 <= gate.x0 + 1e-6]
    x_lo = before[-1].x0 if before else gate.x0
    x_hi = gate.x1 + fence.gate_post_size
    return Compound(
        children=[
            copy.copy(child)
            for child in assembly.children
            if x_lo - 1e-6 <= child.center().X <= x_hi + 1e-6
        ],
        label=f"{assembly.label}_detail",
    )


def _spec(
    style: str,
    board: StockChoice | None = None,
    slug: str | None = None,
    name: str | None = None,
    summary: str | None = None,
    **fence_kwargs: Any,
) -> ProjectSpec:
    """Return the gallery entry for one style, optionally in a chosen board.

    Parameters
    ----------
    style : str
        One of :data:`STYLES`.
    board : StockChoice, optional
        Infill stock, default rough sawn 1x6 in STK.
    slug, name, summary : str, optional
        Override the defaults derived from *style*, for a variant that is not
        just a style — a solid tongue and groove fence is built as a picket
        and looks nothing like one.
    **fence_kwargs
        Anything else :class:`CedarFence` takes.
    """
    fence = CedarFence(
        style=style, **({"board": board} if board else {}), **fence_kwargs
    )
    summaries = {
        "picket": (
            "1x6 rough sawn cedar boards spaced 1-3/4\" apart on 2x4 rails — "
            "the economy option, and the one that lets the wind through."
        ),
        "board_on_board": (
            "1x6 rough sawn cedar in two overlapping courses: full privacy "
            "that stays private after the boards shrink."
        ),
        "horizontal": (
            "1x6 rough sawn cedar run horizontally between 4x4 posts, no "
            "rails — the modern look, on shorter bays."
        ),
        "log_and_mesh": (
            "Peeled round cedar posts and rails with black coated welded wire "
            "stretched between them: the fence you can see through, and the "
            "one that keeps a dog in and a deer out."
        ),
    }
    return ProjectSpec(
        slug=slug or f"cedar-fence-{style.replace('_', '-')}",
        name=name or f"Cedar fence — {style.replace('_', ' ')}",
        summary=summary or summaries[style],
        species="white_cedar",
        build=fence.build,
        check=fence.check,
        inventory=fence.inventory,
        notes=(
            "38 ft of fence at 4 ft, plus two 10 ft gate sections. The first "
            "project here bought by the lineal foot rather than the board "
            "foot, and the first whose every price is real — Lumbery's "
            "published white cedar guide, read 2026-08-17. Nobody publishes "
            "what lengths that cedar comes in, so this is a buying list and "
            "not a cut plan, and it says so."
        ),
        tags=["outdoor", "fence", "cedar"],
    )


def _panel_spec(style: str) -> ProjectSpec:
    """Return the gallery entry for one AVO panel style."""
    fence = PanelFence(style=style)
    spec = fence.spec
    return ProjectSpec(
        slug=f"avo-fence-{style.replace('_', '-')}",
        name=f"AVO {spec.name} panels",
        summary=(
            f"{spec.summary.capitalize()}. Pre-assembled 8 ft panels, "
            f"{mm_to_fractional_inch(spec.board_t, 32)} x "
            f"{mm_to_fractional_inch(spec.board_w, 32)} boards, hung on "
            "pre-routed cedar posts — bought by the piece, not cut on site."
        ),
        species="white_cedar",
        build=fence.build,
        check=fence.check,
        order=fence.order,
        inventory=fence.inventory,
        notes=(
            "The Lumbery's own catalogue, read 2026-08-18: AVO panels in 4, 5 "
            "and 6 ft heights by 8 ft, posts pre-bored for dowelled rails, "
            "caps and toppers per panel, gates quoted by email. The prices "
            "are not published in the page, so nothing here has one."
        ),
        tags=["outdoor", "fence", "cedar", "avo"],
    )


# ---------------------------------------------------------------------------
# The three designs
# ---------------------------------------------------------------------------
#
# The Lumbery sells three fence *systems*, and these are those three.  An
# earlier version of this file offered ten designs, most of which differed by
# a board width and a gap — six ways to space a picket is not six decisions,
# it is one decision presented six times.  What follows is one design per
# system they actually stock, and the differences between them are differences
# somebody would choose between:
#
#   privacy    a solid wall of board you cannot see through
#   chestnut   an open baluster fence you can, decorative, same both sides
#   rails      posts and rails with wire mesh under them, to hold a dog
#
# Everything else in this module is still here and still reachable — the
# stick-built styles are what the sawn price guide can actually cost, and the
# rest of AVO's panel line is what `--variants` and `--compare-systems` weigh
# against these.  They are catalogue, not choices.


def privacy_board_fence() -> PanelFence:
    """Return the Privacy Board panel design: a solid wall of 3/4" board."""
    return PanelFence(style="privacy_board")


def chestnut_hill_fence() -> PanelFence:
    """Return the Chestnut Hill panel design: 2x2 balusters, doubled rails."""
    return PanelFence(style="chestnut_hill")


def post_and_rail_fence() -> CedarFence:
    """Return the post and rail design, with mesh under the rails for a dog.

    AVO's post and rail system: round cedar posts and round cedar rails, two
    or three rails, rails in 8 and 10 ft.  The bay is therefore the rail, the
    same way the bay is the panel on the other side of their catalogue, so
    this is laid out in 8 ft bays rather than in whatever divides the run.

    The mesh is the addition.  A post and rail fence stops a horse and does
    nothing whatever about a dog; black coated welded wire behind the rails,
    run to grade rather than held clear of it, is what makes it a fence a dog
    stays inside.
    """
    return CedarFence(
        style="log_and_mesh",
        bay_ft=POST_AND_RAIL_LENGTHS_FT[0],
        max_bay_ft=POST_AND_RAIL_LENGTHS_FT[0],
        max_horizontal_bay_ft=POST_AND_RAIL_LENGTHS_FT[0],
        log_rails=3,
    )


#: The three designs, in the order they are offered.
DESIGNS: dict[str, tuple[str, Any, str]] = {
    "privacy": (
        "Privacy Board panels",
        privacy_board_fence,
        "AVO's privacy panel: 3/4\" x 3-1/2\" cedar board butted solid in an "
        "8 ft panel, on pre-routed posts. Nothing sees through it, and the "
        "lap of a board fence is what keeps it that way as the wood dries.",
    ),
    "chestnut": (
        "Chestnut Hill panels",
        chestnut_hill_fence,
        "AVO's decorative panel: 2x2 cedar balusters between 6/4x4 and 6/4x6 "
        "rails, one pair each side, so it reads the same from both gardens. "
        "A boundary rather than a screen.",
    ),
    "rails": (
        "Post and rail with dog mesh",
        post_and_rail_fence,
        "AVO's post and rail system — round cedar posts, three round rails, "
        "8 ft bays — with black coated welded wire behind the rails and run "
        "to grade, which is what turns a horse fence into a dog fence.",
    ),
}


def _design_spec(key: str) -> ProjectSpec:
    """Return the gallery entry for one of the three designs."""
    name, factory, summary = DESIGNS[key]
    fence = factory()
    order = getattr(fence, "order", None)
    return ProjectSpec(
        slug=f"cedar-fence-{key}",
        name=name,
        summary=summary,
        species="white_cedar",
        build=fence.build,
        check=fence.check,
        order=order,
        inventory=fence.inventory,
        notes=(
            "One of the three systems The Lumbery stocks, read from their "
            "catalogue on 2026-08-18. 38 ft of fence at 4 ft, plus two 10 ft "
            "gate sections — and the gates are custom in every one of them, "
            "which the catalogue quotes by email rather than pricing online."
        ),
        tags=["outdoor", "fence", "cedar"],
    )


#: Projects this module contributes to the gallery: three, one per system.
PROJECTS: list[ProjectSpec] = [_design_spec(key) for key in DESIGNS]


def main() -> None:
    """Parse arguments and build the requested fence."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--design",
        choices=[*DESIGNS, "all"],
        default=None,
        help="build one of the three designs The Lumbery's systems come in",
    )
    parser.add_argument(
        "--style",
        choices=[*STYLES, "all"],
        default="board_on_board",
        help="a stick-built style, for the by-the-foot costing the sawn price "
        "guide supports",
    )
    parser.add_argument(
        "--panels",
        choices=[*AVO_STYLES, "all"],
        default=None,
        help="build The Lumbery's pre-assembled AVO panels in this style "
        "instead of a stick-built fence",
    )
    parser.add_argument(
        "--panel-height",
        type=float,
        default=4.0,
        help="panel height in feet; the catalogue stocks 4, 5 and 6",
    )
    parser.add_argument("--outdir", type=Path, default=Path("build"))
    parser.add_argument("--gate-leaves", type=int, choices=[1, 2], default=2)
    parser.add_argument(
        "--assume-lengths",
        type=str,
        default="",
        help="comma-separated stock lengths in feet to lay a cut plan against; "
        "nothing in stock.yaml says cedar comes in them",
    )
    parser.add_argument(
        "--compare",
        action="store_true",
        help="print a cost comparison of every style and stop",
    )
    parser.add_argument(
        "--compare-systems",
        action="store_true",
        help="compare the three designs, as far as the published prices allow",
    )
    parser.add_argument(
        "--benchmark",
        choices=[*AVO_STYLES],
        default=None,
        help="price one panel style's wood at the sawn guide's rates and list "
        "every substitution that took",
    )
    parser.add_argument(
        "--variants",
        action="store_true",
        help="print every cedar variant Lumbery stocks, priced as this fence "
        "would buy it, and stop",
    )
    args = parser.parse_args()

    if args.compare:
        print(compare())
        return

    if args.compare_systems:
        print(compare_designs())
        return

    if args.benchmark:
        fence = PanelFence(style=args.benchmark)
        summary, notes = benchmark(fence)
        print(f"  {fence.spec.name} panels — the wood, priced as sticks")
        for note in notes:
            print(f"    {note}")
        print(f"\n  {summary.to_text()}")
        print(
            "\n  Not a panel price. The panels are not priced anywhere this "
            "can read, and\n  what the difference buys is milling, assembly "
            "and delivery."
        )
        return

    if args.variants:
        style = "board_on_board" if args.style == "all" else args.style
        print(catalogue(style=style))
        return

    if args.design:
        keys = tuple(DESIGNS) if args.design == "all" else (args.design,)
        for key in keys:
            run_design(key, args.outdir)
        return

    if args.panels:
        styles = tuple(AVO_STYLES) if args.panels == "all" else (args.panels,)
        for style in styles:
            run_panels(style, args.outdir, height_ft=args.panel_height)
        return

    lengths = [float(v) for v in args.assume_lengths.split(",") if v.strip()]
    styles = STYLES if args.style == "all" else (args.style,)
    for style in styles:
        run(style, args.outdir, gate_leaves=args.gate_leaves, assume_lengths_ft=lengths)


if __name__ == "__main__":
    main()
