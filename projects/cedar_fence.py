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
from woodshop.cutlist.dimensional import LinealPlan, plan_dimensional
from woodshop.cutlist.extract import CutPart, extract
from woodshop.inventory import Inventory
from woodshop.lumber import mm_to_fractional_inch, rough_dimensions_mm
from woodshop.parts import Board
from woodshop.project import ProjectSpec
from woodshop.render import export_assembly, render_assembly, render_cut_list

IN = 25.4
FT = 304.8

#: The infill styles this project builds.
STYLES: tuple[str, ...] = ("picket", "board_on_board", "horizontal")

#: Orientation of a part standing upright in the fence plane: length up +Z,
#: width along the run (+X), thickness across it (+Y).
UPRIGHT = Rotation(90, 0, 90)

#: Orientation of a part lying along the run: length +X, width up +Z.
ALONG_RUN = Rotation(90, 0, 0)

#: Orientation of a post: square section, length up +Z.
UPRIGHT_POST = Rotation(0, 90, 0)

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
        Gap between adjacent boards, mm.
    cover : float
        Length the row spans, mm.
    """

    count: int
    gap: float
    cover: float


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
    board_nominal, rail_nominal, post_nominal, gate_post_nominal : str, optional
        Nominal stock sizes, default ``"1x6"``, ``"2x4"``, ``"4x4"``,
        ``"6x6"``.
    grade, stock_profile : str, optional
        The grade and profile every part is specified in, default ``"STK"``
        and ``"rough sawn"``.  These are not decoration: rough sawn 1x6 in STK
        is $2.30/LF and the same board in low grade is $1.30, so a design that
        does not name them cannot be priced to better than 77%.
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
    board_nominal: str = "1x6"
    rail_nominal: str = "2x4"
    post_nominal: str = "4x4"
    gate_post_nominal: str = "6x6"
    grade: str = "STK"
    stock_profile: str = "rough sawn"
    species: str = "white_cedar"
    inventory: Inventory = field(default_factory=Inventory.load)

    def __post_init__(self) -> None:
        """Reject a fence that cannot be built as described."""
        if self.style not in STYLES:
            raise ValueError(f"style must be one of {STYLES}, got {self.style!r}")
        if self.gate_leaves not in (1, 2):
            raise ValueError(
                f"gate_leaves must be 1 or 2, got {self.gate_leaves!r}: a gate "
                "with three leaves is a folding screen"
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
        return float(rough_dimensions_mm(self.board_nominal)[0].magnitude)

    @property
    def board_w(self) -> float:
        """Board width, mm."""
        return float(rough_dimensions_mm(self.board_nominal)[1].magnitude)

    @property
    def rail_t(self) -> float:
        """Rail thickness, mm — across the fence."""
        return float(rough_dimensions_mm(self.rail_nominal)[0].magnitude)

    @property
    def rail_w(self) -> float:
        """Rail width, mm — vertical, which is the dimension that carries."""
        return float(rough_dimensions_mm(self.rail_nominal)[1].magnitude)

    @property
    def post_size(self) -> float:
        """Line post face dimension, mm."""
        return float(rough_dimensions_mm(self.post_nominal)[1].magnitude)

    @property
    def gate_post_size(self) -> float:
        """Gate post face dimension, mm."""
        return float(rough_dimensions_mm(self.gate_post_nominal)[1].magnitude)

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
            if kind == "fence":
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
                        self.gate_post_nominal if is_gate_post else self.post_nominal
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
        """
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

    def _stock(self, **kwargs: object) -> dict[str, object]:
        """Return the keyword arguments every part shares."""
        return dict(
            material=self.species,
            rough=self.stock_profile == "rough sawn",
            grade=self.grade,
            stock_profile=self.stock_profile,
            **kwargs,
        )

    def _posts(self) -> list[object]:
        """Return every post, positioned with its front face on ``y = 0``."""
        out: list[object] = []
        for post in self.posts():
            board = Board(
                length_mm=post.length,
                nominal=post.nominal,
                label="gate_post" if post.is_gate_post else "line_post",
                notes=(
                    f"{post.embedment / IN:.0f}\" in the ground, "
                    f"{(post.length - post.embedment) / IN:.0f}\" above grade"
                    + (
                        "; set in a gravel-drained hole and plumbed twice — a "
                        "gate post that leans 1° drops its latch 1\""
                        if post.is_gate_post
                        else ""
                    )
                ),
                **self._stock(),
            )
            z = post.length / 2 - post.embedment
            out.append(Pos(post.x, -post.size / 2, z) * UPRIGHT_POST * board)
        return out

    def _panel_group(self, group: list[Span]) -> list[object]:
        """Return the rails and boards filling a run of panels."""
        out: list[object] = []
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
            x = x_start + self.board_w / 2 + i * pitch
            out.append(
                Pos(x, self.board_t / 2, z)
                * UPRIGHT
                * Board(
                    length_mm=self.board_length,
                    nominal=self.board_nominal,
                    label="board" if self.style == "picket" else "under_board",
                    notes=(
                        f"{mm_to_fractional_inch(run.gap, 32)} gap, "
                        f"{self.ground_clearance_in:g}\" off the ground"
                    ),
                    **self._stock(),
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
                        nominal=self.board_nominal,
                        label="over_board",
                        notes=(
                            "centred on the gap, lapping "
                            f"{mm_to_fractional_inch((self.board_w - run.gap) / 2, 32)}"
                            " each side"
                        ),
                        **self._stock(),
                    )
                )
        return out

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
                        nominal=self.rail_nominal,
                        label="rail",
                        notes=(
                            f"{where} rail, cut to fit between posts; hang it "
                            "on galvanised rail brackets or toe-screw it — end "
                            "grain holds no screw"
                        ),
                        **self._stock(),
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
                z = inches(self.ground_clearance_in) + self.board_w / 2 + row * pitch
                out.append(
                    Pos((x0 + x1) / 2, self.board_t / 2, z)
                    * ALONG_RUN
                    * Board(
                        length_mm=length,
                        nominal=self.board_nominal,
                        label="course",
                        notes=(
                            "spans one bay, joints centred on the posts; "
                            f"{mm_to_fractional_inch(rows.gap, 32)} between "
                            "courses"
                        ),
                        **self._stock(),
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
        stile_w, stile_t = self.rail_w, self.rail_t

        for side in (0, 1):
            out.append(
                Pos(x0 + stile_w / 2 + side * (width - stile_w), -stile_t / 2, z0 + height / 2)
                * UPRIGHT
                * Board(
                    length_mm=height,
                    nominal=self.rail_nominal,
                    label="gate_stile",
                    notes="hinge stile" if side == 0 else "latch stile",
                    **self._stock(),
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
                    nominal=self.rail_nominal,
                    label="gate_rail",
                    notes=f"{where} rail, half-lapped into the stiles",
                    **self._stock(),
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
                nominal=self.rail_nominal,
                label="gate_brace",
                notes=(
                    f"{angle:.0f}° from horizontal, foot at the "
                    f"{'hinge' if hinged_left else 'latch'} side, in "
                    "compression; mitre both ends to the frame"
                ),
                **self._stock(),
            )
        )

        out.extend(self._leaf_infill(x0, width, z0, height))
        return out

    def _leaf_infill(
        self, x0: float, width: float, z0: float, height: float
    ) -> list[object]:
        """Return the boards on the face of one leaf."""
        out: list[object] = []
        if self.style == "horizontal":
            rows = self.board_run(height, self.target_gap)
            pitch = self.board_w + rows.gap
            for row in range(rows.count):
                out.append(
                    Pos(
                        x0 + width / 2,
                        self.board_t / 2,
                        z0 + self.board_w / 2 + row * pitch,
                    )
                    * ALONG_RUN
                    * Board(
                        length_mm=width,
                        nominal=self.board_nominal,
                        label="gate_course",
                        notes="gate infill, flush with the leaf",
                        **self._stock(),
                    )
                )
            return out

        run = self.board_run(width, self.target_gap)
        pitch = self.board_w + run.gap
        for i in range(run.count):
            out.append(
                Pos(x0 + self.board_w / 2 + i * pitch, self.board_t / 2, z0 + height / 2)
                * UPRIGHT
                * Board(
                    length_mm=height,
                    nominal=self.board_nominal,
                    label="gate_board",
                    notes="gate infill, flush with the leaf",
                    **self._stock(),
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
                        nominal=self.board_nominal,
                        label="gate_over_board",
                        notes="gate infill, over course",
                        **self._stock(),
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
            pitch = self.board_w + self.target_gap
            layers = 2 if self.style == "board_on_board" else 1
            volume_per_mm = layers * (self.board_w / pitch) * (
                self.board_length * self.board_t
            )
        return volume_per_mm * density / 1e9

    # ------------------------------------------------------------------
    # Buying
    # ------------------------------------------------------------------

    def plan(self, parts: list[CutPart]) -> LinealPlan:
        """Return the lineal-foot buying plan for *parts*."""
        return plan_dimensional(parts, self.inventory)

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
        report.extend(self._check_infill())
        report.extend(self._check_structure(parts))
        report.extend(self._check_posts())
        report.extend(self._check_gates(parts))
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
                f"{len(gate_posts)} of them {self.gate_post_nominal}",
            )
        ]
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

    def _check_infill(self) -> list[Finding]:
        """Report the board layout: gaps, laps, and what happens as it dries."""
        findings: list[Finding] = []
        if self.style == "horizontal":
            rows = self.course_rows()
            findings.append(
                Finding(
                    Severity.INFO,
                    "infill",
                    f"{rows.count} courses of "
                    f"{mm_to_fractional_inch(self.board_w)} board with "
                    f"{mm_to_fractional_inch(rows.gap, 32)} between them, "
                    f"filling {mm_to_fractional_inch(rows.cover)} from the "
                    f"{self.ground_clearance_in:g}\" ground gap to the top",
                )
            )
            return findings

        for group in self.panel_groups():
            _, cover = self.cover_of(group)
            target = self.target_gap
            run = self.board_run(cover, target)
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

    def _check_structure(self, parts: list[CutPart]) -> list[Finding]:
        """Check the members that span: rails, or the boards that replace them."""
        e_mpa = ELASTIC_MODULUS_MPA[self.species]
        panels = [s for s in self.spans() if s.kind == "panel"]
        if not panels:
            return []
        span = max(s.length for s in panels) - self.post_size

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
                f"{self.rail_nominal} rail over the longest bay "
                f"({mm_to_fractional_inch(span)} clear) carries "
                f"{panel_kg / 2:.0f} kg of boards and deflects "
                f"{deflection:.1f} mm (span/{span / max(deflection, 1e-9):.0f}; "
                f"limit span/240 = {limit:.1f} mm) — set the rails with the "
                "4\" face against the boards, which is fourteen times the "
                "stiffness of the same stick laid flat",
            )
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
            (self.post_nominal, self.post_length),
            (self.gate_post_nominal, self.gate_post_length),
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
                "hinges, latch, drop rod, rail brackets and ring-shank nails "
                "are not in stock.yaml and are not in any total this project "
                "prints — budget them separately; on "
                f"{n_leaves} leaves of {mm_to_fractional_inch(width)} the "
                "hardware is not a rounding error",
            )
        )
        return findings

    def check_prices(self, plan: LinealPlan) -> CheckReport:
        """Return the price-provenance findings for the stock *plan* buys."""
        return CheckReport().extend(
            check_price_provenance(self.inventory, stock=plan.stock_used)
        )

    def check_stock_lengths(self, plan: LinealPlan) -> list[Finding]:
        """Report that a cut plan is impossible from a price list alone."""
        findings: list[Finding] = []
        for group in plan.groups:
            if not group.stock.lengths_ft:
                findings.append(
                    Finding(
                        Severity.WARN,
                        "stock",
                        f"{group.stock.stock_label} is priced per lineal foot "
                        "and stocked in lengths nobody has published, so this "
                        f"is {group.lineal_ft:.0f} LF to buy and not a cut "
                        "list — ask the yard what lengths they carry, then "
                        "run --assume-lengths against the answer",
                    )
                )
        return findings


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

    print(f"\n-- prices {'-' * 68}")
    print(fence.check_prices(plan).to_text())

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
            f"{plan.cost_summary.to_text()}"
        )
    return "\n".join(rows)


def _spec(style: str) -> ProjectSpec:
    """Return the gallery entry for one style."""
    fence = CedarFence(style=style)
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
    }
    return ProjectSpec(
        slug=f"cedar-fence-{style.replace('_', '-')}",
        name=f"Cedar fence — {style.replace('_', ' ')}",
        summary=summaries[style],
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


#: Projects this module contributes to the gallery.
PROJECTS: list[ProjectSpec] = [_spec(style) for style in STYLES]


def main() -> None:
    """Parse arguments and build the requested fence."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--style", choices=[*STYLES, "all"], default="board_on_board")
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
    args = parser.parse_args()

    if args.compare:
        print(compare())
        return

    lengths = [float(v) for v in args.assume_lengths.split(",") if v.strip()]
    styles = STYLES if args.style == "all" else (args.style,)
    for style in styles:
        run(style, args.outdir, gate_leaves=args.gate_leaves, assume_lengths_ft=lengths)


if __name__ == "__main__":
    main()
