"""Media console — a slide-together grid: five record bays, a CD row, clear top.

Inspiration
-----------
https://luccahouse.com/ — the Grid System: prefinished maple plywood panels,
notched so that they slide together, assembled or taken apart in under a minute
with no tools, no glue and no hardware, and named by the grid they make (5x1,
4x2, 5x4).  Three part sizes produce six products, and a unit is resized by
swapping the long parts rather than by rebuilding it.

Where the joinery came from
---------------------------
Two things in this file *are* measured off that maker's own published images,
and it is worth saying which, because the first draft of this model guessed
both and got one of them backwards.  The site was unreachable at first and the
model was built from prose; once it could be read, the manufacturer's
dimensioned tearsheets and product photographs settled two questions:

* **Which member owns the front.**  At every crossing the *upright's* banded
  front edge runs through unbroken and the *shelf's* stops against it — so the
  uprights are slotted from the back and the shelves from the front, which is
  the opposite of what this model did until the photographs were read.
* **The overrun: about 0.35 of the panel's width, in both directions.**  The
  slot positions give it exactly — 4.03" and 4.06" from the ends of the
  23-1/2" parts, 4.03" and 4.4" on the 47-1/2" ones.  Every member runs past
  its outermost crossing, so *every joint in that system is a full-width lap
  with stock on both sides of it*, and nothing terminates at a joint.  That,
  more than the corners, is why it reads as a grid and not as a box — and it
  is the thing this model was missing longest.
* **The corner radius: about 0.07 of the panel's width.**  Measured off three
  self-calibrating tearsheets (whose parts scale exactly to their published
  11-1/2" x 23-1/2" and 11-1/2" x 47-1/2"), the radius is 13-14 px against
  17.1 px/in — **0.79" to 0.88"** on an 11-1/2" panel, the same on long parts
  and short, and the same ratio across three products.  The edge banding
  sweeps round each curve, which is what proves the radius is in the plane of
  the panel rather than a roundover on its edge.

The published sizes were read too: 1/2" prefinished maple plywood, 11-1/2"
deep, exteriors 47-1/2" and 59-1/2" wide.  This console is a different piece —
sized to a record rather than to a 12" module, and thicker because a bay of
records is heavier than a row of books — so it borrows the *system* and its
proportions, not the dimensions.

The brief, as given::

    Media console — 80" x 24" x 13", cherry plywood

    Bottom row  five bays, each 15" wide and 13-1/2" tall — a record stands
                upright with a finger's room above the sleeve, and the bay is
                narrow enough that the stack never leans
    Above it    a shallower 8" row, CDs two deep
    Top         left clear for the turntable and the player
    Material    3/4" cherry plywood with solid cherry front edges, finished
                clear, no stain

    …made modular: a kit of interlocking parts rather than a glued case.

The kit
-------
Three panel parts, nine pieces, in a 5x2 grid — the cherry build::

    upright   x6   23-9/16" x 12-3/4", two back-open slots
    shelf     x2   80" x 12-3/4", six front-open slots
    top       x1   80" x 12-3/4", six stopped housings in the underside

Every crossing is a half-lap: the upright is notched 6-3/8" forward from its
**back** edge, the shelf 6-3/8" back from its **front** edge, and the two slide
together front to back until each fills the other.  The uprights are therefore
all one part — a slot open at an edge has no left hand and no right hand — and
so are the two shelves, which is the whole economy of the system.

The upright keeps its front half-depth, so the front of the case reads as six
verticals running floor to top with shelf edges between them.  That is not a
styling choice: it follows from which member is notched where, and the
photographs are unambiguous about it.

The horizontals then run 4-7/16" past the outermost uprights at each end, which
is what makes every crossing a full-width lap rather than a notch in the corner
of a part.  It costs an inch and three quarters off every bay and it is the
whole difference between a grid and a box.  The uprights would overrun top and
bottom in the same way if there were room; there is not — see *What the
arithmetic decides*.

The top is the one part that does not slide.  Its housings are 1/4" deep and
stopped by its own front edging, so no slot reaches the surface the turntable
stands on; it drops straight down onto the uprights, squares the grid, and
lifts off first when the piece is taken apart.

Assembly is: stand the uprights, push a shelf on from the front, push the
second on, drop the top.  Disassembly is the same in reverse.  There is no glue
anywhere in the case — only the front edging is glued, and that is done to a
part rather than to an assembly.

What the arithmetic decides
---------------------------
Five of the brief's numbers cannot all be exact at once, and the plywood is
what decides which one gives.  ``3/4"`` cherry plywood measures **45/64"**, so
six uprights take 4-7/32" of the 80" rather than 4-1/2", and three horizontals
take 2-3/32" of the 24" rather than 2-1/4":

* **Bay width comes out 13-3/8"** — the width is fixed at 80" and three things
  share it: six uprights of 45/64", and the 4-7/16" the horizontals run past
  the end uprights at each end.  The overrun is the expensive one, and it buys
  the joinery: with flush ends the bays go back to 15-5/32" and the four
  crossings at the ends become corner notches.  ``end_overhang_in=0`` is that
  trade, and the report prints both numbers so it is made on purpose.
* **The openings still hit 13-1/2" and 8" exactly**, and the 3/8" the thin
  plywood gives back becomes the **toe reveal**: the bottom shelf crosses the
  uprights 25/64" off the floor, and the piece stands on six panel feet.  A
  floor is never flat, and a panel bearing on one telegraphs every hump in it.

Cutting the slots to the sheet rather than to its label matters more here than
in a glued case.  A dado 1/32" wide of the panel is a glue line; a *slot* 1/32"
wide of it is a wobble, and there is no glue in this piece to take up the
difference.

Those numbers are the cherry build's.  The painted one is cut from a sheet that
measures 23/32", and every one of them lands somewhere else — see *Two builds*.

What is inferred rather than given
----------------------------------
* **Solid edges are 1/4" thick**, on the front edge of every panel, so the
  panels are cut 12-3/4" deep and the console is 13" deep with the cherry on.
  Because the uprights pass the shelves at the front, each upright's edging is
  a single strip from the floor to the underside of the top — which also
  covers its foot, so nothing is needed at the toe — and the shelves' edging is
  one piece per bay between them.
* **There is no back**, and the case wants cables through it.  With no glue,
  racking is resisted by the fit of twenty-four slots and by the top's
  housings — which is why the top is a structural part and not a lid.
* **Capacities and weights** — 5 records to the inch at 250 g each, jewel cases
  at 10 mm and 100 g — are ordinary figures, not measurements of anybody's
  collection.  They set the load the shelves are checked against.

Why five bays
-------------
Not stiffness.  :func:`woodshop.checks.check_shelf_deflection` puts the sag of
a full bay at a tenth of a millimetre and says **three** bays would be enough
to keep an undivided shelf inside span/360 — the fourth and the fifth are there
because a run of records much over 15" leans, slumps and bends the sleeves at
the ends of it.  Both findings are in the report, so the reason the piece looks
the way it does is written down rather than implied.

Resizing
--------
A column costs one upright and a longer pair of shelves and top; a row costs
one shelf and taller uprights.  Nothing else in the kit changes, and no part is
handed, which is what makes ``n_bays`` and the row heights honest parameters
rather than a redraw.

Two builds
----------
``cherry``
    As briefed.  Cherry plywood throughout, solid cherry on every front edge,
    the top a member of the grid, finished clear and no stain — cherry darkens
    on its own from pale amber to deep red-brown over the first year, so the
    piece is meant to leave the shop a little pale.  That is why the edging
    matters more than it looks: solid cherry and rotary cherry veneer start at
    slightly different colours and darken at slightly different rates, and
    sapwood in the edging never catches up.

``painted``
    The plain build, and a genuinely different piece rather than the same one
    in cheaper clothes:

    * **Paint-grade birch plywood**, which measures **23/32"** where cherry ply
      measures 45/64".  Every slot in the kit is cut to that instead, so the
      bays come out 14-15/16" and the toe reveal 5/16" — the same design, told
      by a different sheet.
    * **No edging at all.**  Paint is the reason it does not need any and the
      reason the edges have to be filled: eight bare plywood edges face the
      room, and paint does not fill a void.
    * **A solid cherry top**, 3/4" and overhanging 1/2" at each end, oiled
      rather than painted.  The overhang comes out of the *case* — the console
      is still 80" wide — which hands the bays back nearly the eighth of an
      inch the thicker plywood took, and lands them within a sixteenth of the
      15" the brief asked for.

    The top is also the one part of either build that *moves*: 13" of cherry
    across the grain travels about 3/16" a year, and
    :func:`woodshop.checks.check_wood_movement` says so.  The housings run
    front to back — the same way it moves — so nothing restrains it, and the
    slab simply lies on the grid under its own weight.  Screwing it down would
    be the one mistake that splits it.

Corners
-------
``corner_radius_in`` rounds the panels' outer corners — every corner of the top
in plan, every corner of an upright in its own plane — which is the other half
of what the Grid System looks like.  The parts become
:class:`woodshop.parts.ShapedBoard` profiles sawn from the same rectangles, so
nothing about the grid, the openings or the envelope moves.

**Size it by the ratio, not by eye.**  The measured radius is 0.07 of the
panel's width (see *Where the joinery came from*), which on these 12-3/4"
panels is :data:`REFERENCE_RADIUS_RATIO` x 12-3/4" = **7/8"**.  The first
attempt used 2", which is more than twice the reference and reads as a
different piece of furniture: at that size the curve starts eating the case
rather than softening it.

Two consequences, both reported rather than assumed: the shelves stay square,
because their corners are inside the case where nobody sees them, and the
radius interrupts the outer end of each end upright's housing in the top —
about 1% of the engagement at 7/8", and all of the fit.

Run it
------
::

    uv run python projects/media_console.py
    uv run python projects/media_console.py --variant painted --outdir build
    uv run python projects/media_console.py --variant both --outdir build

and in a REPL, to see the corner treatment::

    MediaConsole(variant="painted", corner_radius_in=2.0).build()
"""

from __future__ import annotations

import argparse
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from build123d import Compound, Mode, Pos, Rotation

from woodshop.checks import (
    CheckReport,
    Finding,
    Severity,
    check_clearance,
    check_envelope,
    check_material_suitability,
    check_price_provenance,
    check_sheet_fit,
    check_shelf_deflection,
    check_thickness_substitution,
    check_wood_movement,
    estimate_mass_kg,
)
from woodshop.cutlist.extract import CutPart, extract
from woodshop.cutlist.hardwood import nest_hardwood
from woodshop.cutlist.optimize_2d import pack_by_material
from woodshop.inventory import Inventory
from woodshop.joinery import Dado
from woodshop.lumber import mm_to_fractional_inch
from woodshop.parts import Board, Panel, ShapedBoard, retag
from woodshop.pricing import sheet_cost_summary
from woodshop.project import ProjectSpec
from woodshop.render import (
    export_assembly,
    render_assembly,
    render_board_diagram,
    render_cut_list,
    render_sheet_diagram,
)
from woodshop.render.sheets import cut_sequence

IN = 25.4

#: A 12" LP jacket is square, and 12-3/8" of it.
LP_SLEEVE_IN: float = 12.375

#: Records to the inch of shelf, jackets included.  Five is the usual figure
#: for ordinary single LPs; gatefolds and box sets are thicker and rarer.
LP_PER_IN: float = 5.0

#: Mass of one LP in its jacket, kg.  A 140 g pressing in a paper sleeve and a
#: card jacket lands near this; 180 g audiophile reissues run heavier.
LP_MASS_KG: float = 0.25

#: A 7" single in its sleeve, which is 7-1/4" square.
SINGLE_SLEEVE_IN: float = 7.25

#: A CD jewel case: 5-9/16" tall, 4-15/16" deep front to back, 3/8" thick.
CD_CASE_H_IN: float = 5.5625
CD_CASE_D_IN: float = 4.9375
CD_CASE_T_IN: float = 0.39

#: Mass of one CD in a jewel case, kg.
CD_MASS_KG: float = 0.1

#: What the top is expected to carry over one span: a turntable, or an
#: amplifier, at the heavy end of either.
TOP_LOAD_KG: float = 15.0


@dataclass(frozen=True)
class Variant:
    """What a version of the console is made of, and how it is finished.

    The grid, the openings and the envelope are the same in both; everything
    below is what changes when the piece stops being a cherry one.

    Parameters
    ----------
    name : str
        Key in :data:`VARIANTS`.
    panel_material : str
        Sheet-goods key for uprights and shelves.
    edge_species : str
        Solid species for the front edging, or ``""`` for none — a painted
        case has no reason to hide a plywood edge under cherry.
    edge_thickness_in : float
        Thickness of that edging, ``0`` when there is none.
    top_kind : str
        ``"panel"`` — the top is a grid member in the same sheet — or
        ``"solid"``, a slab that lies over the kit.
    top_species : str
        Species of a solid top.  Ignored when *top_kind* is ``"panel"``.
    top_thickness_in : float
        Thickness of a solid top.  Ignored when *top_kind* is ``"panel"``.
    top_overhang_in : float
        How far a solid top projects past each end of the case.
    finish : str
        What goes on it, in a sentence.
    """

    name: str
    panel_material: str
    edge_species: str
    edge_thickness_in: float
    top_kind: str
    top_species: str
    top_thickness_in: float
    top_overhang_in: float
    finish: str


#: The two versions of the console.
#:
#: ``cherry``
#:     The piece as briefed: cherry plywood throughout, solid cherry on every
#:     front edge, the top a grid member like any other, clear finish.
#:
#: ``painted``
#:     The plain version.  Paint-grade birch plywood — which measures 23/32"
#:     where cherry ply measures 45/64", so every slot in the kit changes with
#:     it — no edging at all, and a solid cherry top overhanging each end.
#:     Fewer parts, one species of solid stock, and the only thing that shows
#:     is the top.
VARIANTS: dict[str, Variant] = {
    "cherry": Variant(
        name="cherry",
        panel_material="plywood_cherry",
        edge_species="cherry",
        edge_thickness_in=0.25,
        top_kind="panel",
        top_species="",
        top_thickness_in=0.0,
        top_overhang_in=0.0,
        finish="clear, no stain — the cherry darkens on its own",
    ),
    "painted": Variant(
        name="painted",
        panel_material="plywood_birch",
        edge_species="",
        edge_thickness_in=0.0,
        top_kind="solid",
        top_species="cherry",
        top_thickness_in=0.75,
        top_overhang_in=0.5,
        finish=(
            "case filled and painted, top oiled — the paint is what makes a "
            "plywood edge an acceptable edge"
        ),
    ),
}

#: How far a slot cutter is run past the edge it opens on, mm.
#:
#: Cutting exactly to the edge leaves the boolean two coincident faces and,
#: often enough, a film of geometry between them.  It has no effect on the
#: part: the material beyond the edge is not there to remove.
_CUTTER_OVERRUN_MM: float = 2.0


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


#: Corner radius as a fraction of the panel's width, measured off the maker's
#: own tearsheets.
#:
#: Three products, long parts and short, all give 0.069-0.075: a radius of
#: 0.79" to 0.88" on an 11-1/2" panel.  Held as a ratio rather than an inch
#: because it is the ratio that stays constant across their range, and because
#: this console's panels are not 11-1/2" wide.
REFERENCE_RADIUS_RATIO: float = 0.07

#: How far a member runs past its outermost crossing, as a fraction of the
#: panel's width.
#:
#: Measured off the maker's parts drawings, where the slot positions give it
#: directly: on the 23-1/2" parts the two slots sit 4.03" from one end and
#: 4.06" from the other, and on the 47-1/2" parts the outer slots sit 4.03" and
#: 4.4" in.  A constant ~4" on an 11-1/2" panel, the same in both directions —
#: which is what makes every joint in that system a full-width crossing with
#: material on both sides of it, and nothing terminating at a joint.
REFERENCE_OVERHANG_RATIO: float = 0.35

#: Segments per quarter-circle when a radius is sampled into a polyline.
#:
#: :class:`woodshop.parts.ShapedBoard` takes a polygon, so a curve is however
#: many straight lines you are willing to give it.  Twelve is past the point
#: where the facets show at gallery sizes and well short of where the booleans
#: start to labour.
_ARC_SEGMENTS: int = 12


def _rounded_rectangle(
    length_mm: float,
    width_mm: float,
    radius_mm: float,
    segments: int = _ARC_SEGMENTS,
) -> list[tuple[float, float]]:
    """Return a rectangle's outline with all four corners rounded off.

    Drawn in the part frame :class:`woodshop.parts.ShapedBoard` expects: X
    along the part's length, Y across its width.

    All four corners, and not a chosen two, for two reasons.  The pair at the
    top show as much as the pair at the floor — under the overhang at the ends
    of the case, and against the top's own rounded corners.  And rounding a
    chosen pair means naming them: the first draft of this set out to round
    "the two corners at the floor" and silently rounded the two at the ceiling,
    because the rotation that stands an upright on end reverses its length
    axis.  A shape with no chosen end cannot be got the wrong way up.

    Parameters
    ----------
    length_mm, width_mm : float
        The rectangle the panel would be without the radius.
    radius_mm : float
        Corner radius.  Must fit twice over across the shorter side.
    segments : int, optional
        Straight segments per quarter-circle, default :data:`_ARC_SEGMENTS`.

    Returns
    -------
    list of (float, float)
        The closed outline, anticlockwise, without repeating the first point.

    Raises
    ------
    ValueError
        If the radius is not positive, or does not fit twice across the
        shorter side.
    """
    if radius_mm <= 0:
        raise ValueError(f"radius must be positive, got {radius_mm!r}")
    if radius_mm * 2 > min(length_mm, width_mm):
        raise ValueError(
            f"a {mm_to_fractional_inch(radius_mm, 16)} radius does not fit "
            f"twice across {mm_to_fractional_inch(min(length_mm, width_mm))}"
        )

    # Each corner's arc centre, and the angle its quarter starts at.
    corners = (
        ((radius_mm, radius_mm), 180.0),
        ((length_mm - radius_mm, radius_mm), 270.0),
        ((length_mm - radius_mm, width_mm - radius_mm), 0.0),
        ((radius_mm, width_mm - radius_mm), 90.0),
    )
    points: list[tuple[float, float]] = []
    for (cx, cy), start_deg in corners:
        for i in range(segments + 1):
            theta = math.radians(start_deg + 90.0 * i / segments)
            points.append(
                (cx + radius_mm * math.cos(theta), cy + radius_mm * math.sin(theta))
            )
    return points


@dataclass
class MediaConsole:
    """A parametric media console built as an interlocking grid.

    Every dimension below is a *published* one — the envelope and the two
    opening heights.  Everything else (bay width, toe reveal, panel and slot
    sizes) is derived from them and from the thickness the plywood actually
    measures, so changing the sheet changes the kit rather than silently
    changing the fit.

    Parameters
    ----------
    overall_w_in, overall_h_in, overall_d_in : float, optional
        Published envelope, default 80" x 24" x 13".
    n_bays : int, optional
        Bays across — the grid's columns, default 5.
    record_bay_h_in : float, optional
        Clear height of a record bay, default 13-1/2" — a 12-3/8" sleeve and a
        finger above it.
    cd_row_h_in : float, optional
        Clear height of the row above, default 8".
    variant : str, optional
        Key in :data:`VARIANTS`, default ``"cherry"``.  ``"painted"`` is the
        plain build: birch plywood, no edging, a solid cherry top.
    panel_nominal_thickness : str, optional
        Nominal sheet thickness, default ``"3/4"``.  The *actual* thickness is
        read from the inventory and is what the geometry uses.
    dado_depth_in : float, optional
        Depth of the top's stopped housings, default 1/4".
    corner_radius_in : float, optional
        Radius on the panels' outer corners — every corner of the top in plan,
        every corner of an upright in its own plane — default ``0`` for square.
    end_overhang_in : float, optional
        How far the horizontals run past the outermost upright.  ``None``, the
        default, takes the maker's own proportion
        (:data:`REFERENCE_OVERHANG_RATIO` of the panel's width); ``0`` puts the
        end uprights flush with the ends and turns those crossings back into
        corner notches.
    inventory : Inventory, optional
        Stock inventory.  Loaded from ``stock.yaml`` if not given.

    Raises
    ------
    ValueError
        If the variant is unknown, if fewer than two bays are asked for, if the
        edging or the housings are deeper than the stock they land in, or if
        the rows and their shelves are taller than the published height — in
        which case there is no console to model, only a stack that does not fit
        in one.
    """

    variant: str = "cherry"

    overall_w_in: float = 80.0
    overall_h_in: float = 24.0
    overall_d_in: float = 13.0

    n_bays: int = 5
    record_bay_h_in: float = 13.5
    cd_row_h_in: float = 8.0

    panel_nominal_thickness: str = "3/4"
    dado_depth_in: float = 0.25
    corner_radius_in: float = 0.0
    end_overhang_in: float | None = None

    inventory: Inventory = field(default_factory=Inventory.load)

    def __post_init__(self) -> None:
        """Reject a console whose numbers do not describe a case."""
        if self.variant not in VARIANTS:
            raise ValueError(
                f"variant must be one of {sorted(VARIANTS)}, got {self.variant!r}"
            )
        if self.n_bays < 2:
            raise ValueError(
                f"a run of bays needs at least 2 of them, got {self.n_bays}"
            )
        if self.spec.edge_thickness_in >= self.overall_d_in:
            raise ValueError(
                f"{self.spec.edge_thickness_in:g}\" of edging on a "
                f"{self.overall_d_in:g}\" deep case leaves no panel"
            )
        if self.dado_depth_in >= self.panel_t / IN:
            raise ValueError(
                f"a {self.dado_depth_in:g}\" housing goes through "
                f"{mm_to_fractional_inch(self.panel_t, 64)} stock"
            )
        if self.toe_reveal < 0:
            rows = ", ".join(mm_to_fractional_inch(h) for h in self.row_heights)
            raise ValueError(
                f"{self.n_rows} rows of {rows}, {self.n_shelves} shelves and a "
                f"{mm_to_fractional_inch(self.top_t, 64)} top come to "
                f"{mm_to_fractional_inch(self.overall_h - self.toe_reveal)}, "
                f"which does not fit inside {self.overall_h_in:g}\""
            )

    # ------------------------------------------------------------------
    # What the variant decides
    # ------------------------------------------------------------------

    @property
    def spec(self) -> Variant:
        """The :class:`Variant` this console is built to."""
        return VARIANTS[self.variant]

    @property
    def panel_material(self) -> str:
        """Sheet-goods key for the uprights and shelves."""
        return self.spec.panel_material

    @property
    def species(self) -> str:
        """Solid species this build buys — the edging's, or the top's."""
        return self.spec.edge_species or self.spec.top_species

    @property
    def has_edging(self) -> bool:
        """Whether the front edges are covered in solid stock."""
        return self.spec.edge_thickness_in > 0 and bool(self.spec.edge_species)

    @property
    def has_solid_top(self) -> bool:
        """Whether the top is a slab rather than a member of the grid."""
        return self.spec.top_kind == "solid"

    @property
    def top_material(self) -> str:
        """Material of the top."""
        return self.spec.top_species if self.has_solid_top else self.panel_material

    @property
    def top_t(self) -> float:
        """Thickness of the top in mm."""
        if self.has_solid_top:
            return inches(self.spec.top_thickness_in)
        return self.panel_t

    @property
    def top_overhang(self) -> float:
        """How far the top projects past each end of the case, mm."""
        return inches(self.spec.top_overhang_in)

    # ------------------------------------------------------------------
    # Stock
    # ------------------------------------------------------------------

    @property
    def sheet(self):
        """The sheet the kit is cut from."""
        return self.inventory.sheet_for(
            self.panel_material, self.panel_nominal_thickness
        )

    @property
    def panel_t(self) -> float:
        """Measured panel thickness in mm.

        Never the nominal 3/4": cherry ply measures 45/64" and paint-grade
        birch 23/32", and every slot in the kit is cut to whichever it is.
        """
        return self.sheet.thickness_mm

    @property
    def edge_t(self) -> float:
        """Thickness of the solid front edging in mm, ``0`` when there is none."""
        return inches(self.spec.edge_thickness_in)

    @property
    def dado_depth(self) -> float:
        """Depth of the top's stopped housings in mm."""
        return inches(self.dado_depth_in)

    @property
    def corner_radius(self) -> float:
        """Radius on the panels' outer corners in mm, ``0`` for square."""
        return inches(self.corner_radius_in)

    @property
    def end_overhang(self) -> float:
        """How far the horizontals run past the outermost upright, mm.

        The reason the reference reads as a grid rather than as a box: every
        crossing has material on both sides of it, so no joint is a corner
        notch and no member stops at a joint.  It is bought out of the bays —
        the envelope is published, so an inch of ear is an inch the openings
        do not get.
        """
        if self.end_overhang_in is None:
            return REFERENCE_OVERHANG_RATIO * self.panel_depth
        return inches(self.end_overhang_in)

    @property
    def reference_corner_radius(self) -> float:
        """The radius this piece would have at the measured proportion, mm.

        :data:`REFERENCE_RADIUS_RATIO` of the panel's width — 7/8" on a 12-3/4"
        panel.  Not applied automatically: it is what to pass to
        ``corner_radius_in`` if you want the maker's proportion rather than a
        number somebody liked the look of.
        """
        return REFERENCE_RADIUS_RATIO * self.panel_depth

    # ------------------------------------------------------------------
    # The published envelope
    # ------------------------------------------------------------------

    @property
    def overall_w(self) -> float:
        """Published overall width in mm."""
        return inches(self.overall_w_in)

    @property
    def overall_h(self) -> float:
        """Published overall height in mm."""
        return inches(self.overall_h_in)

    @property
    def overall_d(self) -> float:
        """Published overall depth in mm."""
        return inches(self.overall_d_in)

    # ------------------------------------------------------------------
    # The grid
    # ------------------------------------------------------------------

    @property
    def row_heights(self) -> tuple[float, ...]:
        """Clear height of each row in mm, bottom first."""
        return (inches(self.record_bay_h_in), inches(self.cd_row_h_in))

    @property
    def n_rows(self) -> int:
        """Rows in the grid."""
        return len(self.row_heights)

    @property
    def n_uprights(self) -> int:
        """Two ends plus the dividers between the bays."""
        return self.n_bays + 1

    @property
    def n_shelves(self) -> int:
        """Slotted horizontals: one under each row.  The top is not one."""
        return self.n_rows

    @property
    def grid_label(self) -> str:
        """The grid, in the system's own notation — ``"5x2"``."""
        return f"{self.n_bays}x{self.n_rows}"

    # ------------------------------------------------------------------
    # Derived geometry
    # ------------------------------------------------------------------

    @property
    def case_w(self) -> float:
        """Width the horizontals run, mm — the envelope less any top overhang.

        A solid top that projects past the ends takes its overhang out of the
        case rather than out of the room: the piece is 80" wide either way.
        """
        return self.overall_w - 2 * self.top_overhang

    @property
    def upright_span(self) -> float:
        """Across the outer faces of the two end uprights, mm.

        The horizontals overrun this at both ends, which is what makes every
        crossing a full-width lap.
        """
        return self.case_w - 2 * self.end_overhang

    @property
    def panel_depth(self) -> float:
        """Depth of a plywood panel in mm — the case less its front edging."""
        return self.overall_d - self.edge_t

    @property
    def lap_depth(self) -> float:
        """How far each slot runs into its panel, mm — half the depth.

        Half and half is what lets one part be both members: cut deeper on the
        shelf and the upright would have to be cut shallower, and the two would
        stop being the same joint seen from two sides.
        """
        return self.panel_depth / 2

    @property
    def bay_clear_w(self) -> float:
        """Clear width of one bay in mm.

        The width is published and the uprights and the ears take what they
        take, so this is an outcome rather than a choice.  Two things eat it:
        six panels of 45/64", and the overrun at each end that the joinery
        wants.  Set ``end_overhang_in=0`` and the bays go back over 15" —
        along with the corner notches at the ends.
        """
        return (self.upright_span - self.n_uprights * self.panel_t) / self.n_bays

    @property
    def toe_reveal(self) -> float:
        """Height of the bottom shelf off the floor, mm.

        What is left of the published height once every row and every
        horizontal panel has had theirs.
        """
        return (
            self.overall_h
            - self.top_t
            - self.n_shelves * self.panel_t
            - sum(self.row_heights)
        )

    @property
    def upright_h(self) -> float:
        """Length of an upright in mm, its housing in the top included."""
        return self.overall_h - self.top_t + self.dado_depth

    @property
    def upright_edge_h(self) -> float:
        """Exposed height of an upright's front edge, mm.

        Floor to the underside of the top: the top's own edging caps it, and
        the strip covers the foot on the way down.
        """
        return self.overall_h - self.top_t

    @property
    def shelf_len(self) -> float:
        """Length of a shelf in mm — the case width, ends flush with the sides."""
        return self.case_w

    @property
    def top_underside_z(self) -> float:
        """Underside of the top, mm off the floor."""
        return self.overall_h - self.top_t

    @property
    def clear_run(self) -> float:
        """Width the bays share between the two end uprights, mm."""
        return self.upright_span - 2 * self.panel_t

    def shelf_z(self, row: int) -> float:
        """Return the underside of the shelf below *row*, mm off the floor.

        Parameters
        ----------
        row : int
            ``0`` is the bottom row, so ``shelf_z(0)`` is the bottom shelf and
            sits at the toe reveal.

        Returns
        -------
        float
            Height of the shelf's underside off the floor.
        """
        z = self.toe_reveal
        for h in self.row_heights[:row]:
            z += self.panel_t + h
        return z

    def upright_x(self, i: int) -> float:
        """Return the centre line of upright *i* in mm, ``0`` at the middle.

        Parameters
        ----------
        i : int
            ``0`` is the left end, :attr:`n_uprights` - 1 the right.

        Returns
        -------
        float
            Distance from the console's centre line, negative to the left.
        """
        pitch = self.bay_clear_w + self.panel_t
        return -self.upright_span / 2 + self.panel_t / 2 + i * pitch

    @property
    def panel_y(self) -> float:
        """Centre of a panel front to back, mm — the edging is in front of it."""
        return -self.overall_d / 2 + self.edge_t + self.panel_depth / 2

    @property
    def panel_front_y(self) -> float:
        """Front face of the plywood, behind the edging, mm."""
        return -self.overall_d / 2 + self.edge_t

    @property
    def panel_back_y(self) -> float:
        """Back face of the plywood, mm."""
        return self.overall_d / 2

    @property
    def edge_y(self) -> float:
        """Centre of the solid front edging, front to back, mm."""
        return -self.overall_d / 2 + self.edge_t / 2

    # ------------------------------------------------------------------
    # What it holds
    # ------------------------------------------------------------------

    @property
    def records_per_bay(self) -> int:
        """Records one bay holds, at :data:`LP_PER_IN` to the inch."""
        return int(self.bay_clear_w / IN * LP_PER_IN)

    @property
    def record_load_kg(self) -> float:
        """Mass of a full bay of records, kg."""
        return self.records_per_bay * LP_MASS_KG

    @property
    def cd_ranks(self) -> int:
        """How many ranks of jewel cases fit front to back in the CD row."""
        return int(self.overall_d / inches(CD_CASE_D_IN))

    @property
    def cds_per_bay(self) -> int:
        """Jewel cases one bay of the CD row holds, in every rank."""
        return int(self.bay_clear_w / inches(CD_CASE_T_IN)) * self.cd_ranks

    @property
    def cd_load_kg(self) -> float:
        """Mass of a full bay of CDs, kg."""
        return self.cds_per_bay * CD_MASS_KG

    # ------------------------------------------------------------------
    # Assembly
    # ------------------------------------------------------------------

    def build(self) -> Compound:
        """Build the console as a positioned build123d assembly.

        Laid out with +X across the front, +Y from the front face toward the
        back, and +Z up from the floor, centred on the footprint.

        Returns
        -------
        build123d.Compound
            Every panel and edging strip, positioned, with the slots and
            housings cut — so the model shows parts that interlock rather than
            parts that claim to.
        """
        children: list[object] = [self._placed_top()]

        for i in range(self.n_uprights):
            children.append(self._placed_upright(i))
        for row in range(self.n_shelves):
            children.append(self._placed_shelf(row))

        children.extend(self._edging())
        return Compound(
            children=children,
            label=f"media_console_{self.variant}_{self.grid_label}",
        )

    # -- The three panel parts -----------------------------------------

    def _placed_upright(self, i: int):
        """Return upright *i*, positioned, with a slot at every shelf.

        The slots open at the **back** edge, so the upright keeps its front
        half-depth and runs unbroken from the floor to the top.  That is the
        way round the photographs show (see *Where the joinery came from*): at
        every crossing the vertical's banded front edge runs through and the
        shelf's stops against it.  A slot open at an edge is symmetrical about
        the panel's centre line, which is why all six uprights are the same
        part and none of them is handed.
        """
        part = self._upright()
        placed = (
            Pos(self.upright_x(i), self.panel_y, self.upright_h / 2)
            * Rotation(0, 90, 0)
            * part
        )
        for row in range(self.n_shelves):
            placed = placed - (
                Pos(
                    self.upright_x(i),
                    self.panel_back_y
                    - (self.lap_depth - _CUTTER_OVERRUN_MM) / 2,
                    self.shelf_z(row) + self.panel_t / 2,
                )
                * Rotation(90, 90, 0)
                * self._slot()
            )
        return retag(placed, like=part)

    def _placed_shelf(self, row: int):
        """Return the shelf under *row*, positioned, slotted for every upright.

        These slots open at the **front** edge, so a shelf goes on from the
        front and slides back until each part fills the other, and its own
        front edge stops at every upright it crosses.
        """
        part = self._shelf()
        placed = (
            Pos(0.0, self.panel_y, self.shelf_z(row) + self.panel_t / 2) * part
        )
        for i in range(self.n_uprights):
            placed = placed - (
                Pos(
                    self.upright_x(i),
                    self.panel_front_y
                    + (self.lap_depth - _CUTTER_OVERRUN_MM) / 2,
                    self.shelf_z(row) + self.panel_t / 2,
                )
                * Rotation(0, 0, 90)
                * self._slot()
            )
        return retag(placed, like=part)

    def _placed_top(self):
        """Return the top, positioned, housed for every upright.

        The housings are 1/4" deep in the underside and stopped short of the
        front, so nothing shows on the surface the turntable stands on.  The
        top drops straight down, which is what squares the grid and holds the
        upright spacing.

        A solid top runs the housings *across* its grain — which is the safe
        way round, because the grooves then run the same way the top moves and
        cannot restrain it.  See :func:`woodshop.checks.check_wood_movement`.
        """
        part = self._top()
        top_y = 0.0 if self.has_solid_top else self.panel_y
        top = Pos(0.0, top_y, self.top_underside_z + self.top_t / 2) * part
        for i in range(self.n_uprights):
            top = top - (
                Pos(
                    self.upright_x(i),
                    self.panel_y,
                    self.top_underside_z + self.dado_depth / 2,
                )
                * Rotation(0, 0, 90)
                * Dado(
                    width_mm=self.panel_t,
                    depth_mm=self.dado_depth,
                    length_mm=self.panel_depth,
                    mode=Mode.PRIVATE,
                )
            )
        return retag(top, like=part)

    def _slot(self) -> Dado:
        """Return one half-lap slot, drawn in its own frame.

        Every crossing in the kit is this cut and no other: the mating panel's
        measured thickness wide, right through the stock, and half the panel's
        depth long — run past the edge it opens on so the boolean has no
        coincident faces to argue with.
        """
        return Dado(
            width_mm=self.panel_t,
            depth_mm=self.panel_t + 2 * _CUTTER_OVERRUN_MM,
            length_mm=self.lap_depth + _CUTTER_OVERRUN_MM,
            mode=Mode.PRIVATE,
        )

    def _upright(self):
        """Return one upright: a rectangle, or a rounded one."""
        if self.corner_radius > 0:
            return ShapedBoard(
                profile=_rounded_rectangle(
                    self.upright_h, self.panel_depth, self.corner_radius
                ),
                thickness_mm=self.panel_t,
                material=self.panel_material,
                label="upright",
                grain_direction="length",
                blank_margin_mm=0.0,
                notes=(
                    f"face grain runs up the case; {self.n_shelves} slots, and "
                    "all four corners rounded to "
                    f"{mm_to_fractional_inch(self.corner_radius, 16)} — every "
                    "corner, so the part still has no top and no bottom"
                ),
            )
        return Panel(
            length_mm=self.upright_h,
            width_mm=self.panel_depth,
            thickness_mm=self.panel_t,
            material=self.panel_material,
            label="upright",
            grain_direction="length",
            notes=(
                f"face grain runs up the case; {self.n_shelves} slots "
                f"{mm_to_fractional_inch(self.panel_t, 64)} wide x "
                f"{mm_to_fractional_inch(self.lap_depth, 32)} deep, cut from "
                "the BACK edge so the front runs unbroken; top end housed in "
                f"the top. All {self.n_uprights} are the same part, ends "
                "included"
            ),
        )

    def _shelf(self) -> Panel:
        """Return one shelf — the long part, and there are only two."""
        return Panel(
            length_mm=self.shelf_len,
            width_mm=self.panel_depth,
            thickness_mm=self.panel_t,
            material=self.panel_material,
            label="shelf",
            grain_direction="length",
            notes=(
                f"runs the full width; {self.n_uprights} slots "
                f"{mm_to_fractional_inch(self.panel_t, 64)} wide x "
                f"{mm_to_fractional_inch(self.lap_depth, 32)} deep, cut from "
                "the FRONT edge — every one of them interior, because the "
                f"shelf runs {mm_to_fractional_inch(self.end_overhang, 16)} "
                "past the end uprights. Bottom shelf and CD shelf are one part"
            ),
        )

    def _top(self):
        """Return the top: a member of the grid, or a slab that lies over it."""
        housed = (
            f"underside housed {mm_to_fractional_inch(self.dado_depth, 32)} "
            f"deep for all {self.n_uprights} uprights"
        )
        if self.corner_radius > 0:
            return ShapedBoard(
                profile=_rounded_rectangle(
                    self.overall_w,
                    self.overall_d if self.has_solid_top else self.panel_depth,
                    self.corner_radius,
                ),
                thickness_mm=self.top_t,
                material=self.top_material,
                label="top",
                grain_direction="length",
                blank_margin_mm=0.0,
                notes=(
                    "all four corners rounded to "
                    f"{mm_to_fractional_inch(self.corner_radius, 16)} in plan; "
                    f"{housed}, which the radius interrupts at the two ends"
                ),
            )
        if self.has_solid_top:
            return Board(
                length_mm=self.overall_w,
                width_mm=self.overall_d,
                thickness_mm=self.top_t,
                material=self.top_material,
                label="top",
                grain_direction="length",
                notes=(
                    f"glue-up, grain running the length; {housed}, the grooves "
                    "running the same way it moves so they cannot restrain it. "
                    f"Overhangs {mm_to_fractional_inch(self.top_overhang, 32)} "
                    "at each end and simply lies on the grid — no fixing across "
                    "its width, ever"
                ),
            )
        return Panel(
            length_mm=self.overall_w,
            width_mm=self.panel_depth,
            thickness_mm=self.panel_t,
            material=self.panel_material,
            label="top",
            grain_direction="length",
            notes=(
                f"{housed}, stopped at the front by its own edging so nothing "
                "shows on the top face"
            ),
        )

    # -- Solid cherry on every front edge -------------------------------

    def _edging(self) -> list[object]:
        """Return every strip of solid front edging, positioned.

        The uprights run unbroken and the shelves' edging sits between them,
        because that is what the joinery has already decided: where a shelf
        crosses an upright, the front of the case *is* the upright.  Every
        strip runs the full length of the edge it covers, so the front reads
        as five verticals from floor to top with shelf edges between — which
        is what the photographs show, and it is also why this build needs no
        rail at the floor: the uprights' own edging covers their feet.

        The painted build has none of this.  Paint is the reason it does not
        need any, and the reason it has to be filled instead.
        """
        if not self.has_edging:
            return []

        out: list[object] = [
            Pos(0.0, self.edge_y, self.top_underside_z + self.panel_t / 2)
            * Rotation(90, 0, 0)
            * self._edge_strip(
                "top_edge",
                length_mm=self.case_w,
                height_mm=self.panel_t,
                notes=(
                    "runs the full width and caps the uprights; glued and "
                    "planed flush before the kit goes together"
                ),
            )
        ]

        for i in range(self.n_uprights):
            out.append(
                Pos(self.upright_x(i), self.edge_y, self.upright_edge_h / 2)
                * Rotation(90, 0, 90)
                * self._edge_strip(
                    "upright_edge",
                    length_mm=self.upright_edge_h,
                    height_mm=self.panel_t,
                    notes=(
                        "one piece, floor to the underside of the top — it "
                        "covers the foot, so nothing is needed at the toe"
                    ),
                )
            )

        for row in range(self.n_shelves):
            z = self.shelf_z(row) + self.panel_t / 2
            for bay in range(self.n_bays):
                x = (self.upright_x(bay) + self.upright_x(bay + 1)) / 2
                out.append(
                    Pos(x, self.edge_y, z)
                    * Rotation(90, 0, 0)
                    * self._edge_strip(
                        "shelf_edge",
                        length_mm=self.bay_clear_w,
                        height_mm=self.panel_t,
                        notes=(
                            "one per bay per shelf, fitted between the "
                            "uprights' edging after the kit is dry-fitted"
                        ),
                    )
                )
            if self.end_overhang > 0:
                for sign in (-1, 1):
                    x = sign * (self.upright_span / 2 + self.end_overhang / 2)
                    out.append(
                        Pos(x, self.edge_y, z)
                        * Rotation(90, 0, 0)
                        * self._edge_strip(
                            "shelf_ear_edge",
                            length_mm=self.end_overhang,
                            height_mm=self.panel_t,
                            notes=(
                                "the ear outside the end upright; it returns "
                                "round the rounded end, so mitre or wrap it "
                                "rather than butting a short grain end"
                            ),
                        )
                    )
        return out

    def _edge_strip(
        self, label: str, length_mm: float, height_mm: float, notes: str
    ) -> Board:
        """Return one strip of solid front edging.

        All of them are the same section: the board is planed to the edging's
        thickness and ripped into strips as wide as the panel edge they cover,
        so a strip's *width* is what matches the panel.

        Parameters
        ----------
        label : str
            Part name: ``"top_edge"``, ``"upright_edge"``, ``"shelf_edge"``,
            ``"shelf_ear_edge"``.
        length_mm : float
            Finished length.  Cut long — every one of these is fitted.
        height_mm : float
            How much of the panel edge it covers.
        notes : str
            What this strip is doing, carried to the cut list.

        Returns
        -------
        woodshop.parts.Board
            The strip, unplaced.
        """
        milling = (
            f"4/4 {self.species} planed to "
            f"{mm_to_fractional_inch(self.edge_t, 32)} and ripped "
            f"{mm_to_fractional_inch(height_mm, 64)} wide"
        )
        return Board(
            length_mm=length_mm,
            thickness_mm=self.edge_t,
            width_mm=height_mm,
            material=self.species,
            label=label,
            trim_allowance_mm=inches(0.5),
            notes=f"{milling}; {notes}",
        )

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def check(self, assembly: Compound, parts: list[CutPart]) -> CheckReport:
        """Run every design check against a built assembly.

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
        bb = assembly.bounding_box()
        report = CheckReport()
        report.extend(
            check_envelope(
                actual_l_mm=bb.size.X,
                actual_w_mm=bb.size.Y,
                actual_h_mm=bb.size.Z,
                published_l_mm=self.overall_w,
                published_w_mm=self.overall_d,
                published_h_mm=self.overall_h,
            )
        )
        report.extend(check_sheet_fit(parts, self.inventory))
        report.extend(check_thickness_substitution(parts, self.inventory))
        report.extend(check_material_suitability(parts, self.inventory))

        report.extend(self._kit_findings(parts))
        report.extend(self._fit_findings())
        report.extend(self._load_findings(parts))
        report.extend(self._construction_findings())
        return report

    def _kit_findings(self, parts: list[CutPart]) -> list[Finding]:
        """Describe the kit: what it is made of, and what a slot fit costs."""
        plywood = [p for p in parts if p.material == self.panel_material]
        distinct = {p.label for p in plywood}
        pieces = sum(p.qty for p in plywood)
        slots = self.n_uprights * self.n_shelves * 2
        top = (
            f"a solid {self.top_material} top over it"
            if self.has_solid_top
            else "a top in the same sheet"
        )
        return [
            Finding(
                Severity.INFO,
                "kit",
                f"the {self.variant} build: a {self.grid_label} grid from "
                f"{len(distinct)} panel parts and {pieces} pieces — "
                f"{self.n_uprights} uprights, {self.n_shelves} shelves — with "
                f"{top}. No part is handed, because a slot open at an edge is "
                f"symmetrical. Finish: {self.spec.finish}",
            ),
            Finding(
                Severity.INFO,
                "kit",
                f"{slots} slots, each "
                f"{mm_to_fractional_inch(self.lap_depth, 32)} of engagement "
                f"({self.lap_depth / self.panel_depth * 100:.0f}% of the "
                "depth): shelves slide on from the front, the top drops on "
                "last, and it comes apart in that order. No glue and no "
                "fasteners anywhere in the case",
            ),
            Finding(
                Severity.WARN,
                "kit",
                f"the slots are cut to the sheet's "
                f"{mm_to_fractional_inch(self.panel_t, 64)}, not to its 3/4\" "
                "label: in a glued case that difference is a glue line, here "
                "it is the whole joint. Cut one test slot in an offcut and fit "
                "it before the rest — nothing downstream takes up slack",
            ),
            Finding(
                Severity.INFO,
                "kit",
                "adding a column costs one upright and a longer pair of "
                "shelves and top; adding a row costs one shelf and taller "
                "uprights. Nothing else in the kit changes",
            ),
            *self._overhang_findings(),
        ]

    def _overhang_findings(self) -> list[Finding]:
        """Report the overrun, what it buys, and what it costs."""
        if self.end_overhang <= 0:
            return [
                Finding(
                    Severity.WARN,
                    "kit",
                    "no overrun: the end uprights sit flush with the ends, so "
                    f"the {2 * self.n_shelves} crossings there are corner "
                    "notches rather than full-width laps, and the top's outer "
                    "housings are rabbets. It holds together and it reads as "
                    "a box rather than as a grid",
                )
            ]

        flush_bay = (self.case_w - self.n_uprights * self.panel_t) / self.n_bays
        return [
            Finding(
                Severity.INFO,
                "kit",
                f"the horizontals run "
                f"{mm_to_fractional_inch(self.end_overhang, 16)} past the end "
                f"uprights, so all {self.n_uprights * self.n_shelves} "
                "crossings are full-width laps with stock on both sides and "
                "nothing stopping at a joint — which is what makes the "
                "reference read as a grid rather than as a case",
            ),
            Finding(
                Severity.INFO,
                "bay",
                "the ears are bought out of the openings: "
                f"{mm_to_fractional_inch(2 * self.end_overhang, 16)} of "
                f"overrun inside a published {self.overall_w_in:g}\" takes "
                f"{mm_to_fractional_inch((flush_bay - self.bay_clear_w), 32)} "
                f"off every bay, which is why they come out "
                f"{mm_to_fractional_inch(self.bay_clear_w, 32)} and not "
                f"{mm_to_fractional_inch(flush_bay, 32)}",
            ),
            Finding(
                Severity.WARN,
                "capacity",
                f"an ear is a ledge, not a bay: there is no upright beyond it, "
                f"so records in the outer "
                f"{mm_to_fractional_inch(self.end_overhang, 16)} have nothing "
                "to lean on and will slide off the end. Keep the run inboard "
                "of the last upright and treat the ears as somewhere to put a "
                "record down while the other side plays",
            ),
            Finding(
                Severity.INFO,
                "kit",
                "the uprights cannot overrun the same way: the reference "
                f"stands them about {REFERENCE_OVERHANG_RATIO:.2f} of a panel "
                "width proud top and bottom, and a "
                f"{self.overall_h_in:g}\" envelope with "
                f"{self.record_bay_h_in:g}\" and {self.cd_row_h_in:g}\" "
                f"openings has {mm_to_fractional_inch(self.toe_reveal, 64)} "
                "left over. The toe reveal is what survives of that idea; "
                "matching it properly would mean a "
                f"{(self.overall_h + 2 * self.end_overhang) / IN:.0f}\" "
                "console or shorter rows",
            ),
        ]

    def _fit_findings(self) -> list[Finding]:
        """Compare the openings against the things they are sized for."""
        findings: list[Finding] = []

        findings.append(
            Finding(
                Severity.INFO,
                "bay",
                f"{self.n_bays} bays come out "
                f"{mm_to_fractional_inch(self.bay_clear_w, 32)} clear across a "
                f"{mm_to_fractional_inch(self.upright_span, 32)} span: "
                f"{self.n_uprights} uprights of "
                f"{mm_to_fractional_inch(self.panel_t, 64)} take "
                f"{mm_to_fractional_inch(self.n_uprights * self.panel_t, 32)} "
                f"of it, where {self.n_uprights} of a true 3/4\" would take "
                f"{mm_to_fractional_inch(self.n_uprights * inches(0.75), 32)}",
            )
        )
        if self.top_overhang > 0:
            findings.append(
                Finding(
                    Severity.INFO,
                    "bay",
                    f"the top's {mm_to_fractional_inch(self.top_overhang, 32)} "
                    "overhang at each end comes out of the case rather than "
                    f"the room: {self.overall_w_in:g}\" of console over "
                    f"{mm_to_fractional_inch(self.case_w, 32)} of grid, which "
                    "hands the bays back most of what the thick paint-grade "
                    "plywood took",
                )
            )

        sleeve = inches(LP_SLEEVE_IN)
        findings.extend(
            check_clearance(
                "room beside a record sleeve",
                self.bay_clear_w - sleeve,
                min_mm=inches(0.75),
                max_mm=inches(4.0),
                tight_note="fingers cannot get either side of the stack",
                loose_note="the stack leans before the bay is full",
            )
        )
        findings.extend(
            check_clearance(
                "room above a record sleeve",
                inches(self.record_bay_h_in) - sleeve,
                min_mm=inches(0.75),
                max_mm=inches(2.0),
                tight_note="a sleeve comes out two-handed, or not at all",
                loose_note="the row stops reading as a band of spines",
            )
        )
        findings.append(
            Finding(
                Severity.INFO,
                "clearance",
                f"a {mm_to_fractional_inch(sleeve, 16)} sleeve in a "
                f"{self.overall_d_in:g}\" deep case sits fully inside by "
                f"{mm_to_fractional_inch(self.overall_d - sleeve, 32)} — it "
                "does not hang past the front",
            )
        )
        findings.append(
            Finding(
                Severity.INFO,
                "clearance",
                f"the {self.cd_row_h_in:g}\" row clears a "
                f"{mm_to_fractional_inch(inches(CD_CASE_H_IN), 16)} jewel case "
                f"by "
                f"{mm_to_fractional_inch(inches(self.cd_row_h_in - CD_CASE_H_IN), 32)}"
                f", and still takes a 7\" single in its "
                f"{mm_to_fractional_inch(inches(SINGLE_SLEEVE_IN), 16)} sleeve",
            )
        )
        findings.append(
            Finding(
                Severity.INFO,
                "clearance",
                f"jewel cases go {self.cd_ranks} deep in "
                f"{self.overall_d_in:g}\" ({self.cd_ranks} x "
                f"{mm_to_fractional_inch(inches(CD_CASE_D_IN), 16)} = "
                f"{mm_to_fractional_inch(inches(self.cd_ranks * CD_CASE_D_IN), 16)})"
                ", the back rank reached over the front one",
            )
        )
        return findings

    def _load_findings(self, parts: list[CutPart]) -> list[Finding]:
        """Weigh what the console holds, and sag the shelves under it."""
        findings: list[Finding] = [
            Finding(
                Severity.INFO,
                "capacity",
                f"{self.records_per_bay * self.n_bays} records "
                f"({self.records_per_bay} to a bay at {LP_PER_IN:g} to the "
                f"inch) and {self.cds_per_bay * self.n_bays} CDs; the records "
                f"alone weigh {self.record_load_kg * self.n_bays:.0f} kg "
                f"({self.record_load_kg * self.n_bays * 2.2046:.0f} lb), "
                f"against {estimate_mass_kg(parts):.0f} kg of console",
            )
        ]

        findings.extend(
            check_shelf_deflection(
                self.panel_material,
                span_mm=self.bay_clear_w,
                depth_mm=self.panel_depth,
                thickness_mm=self.panel_t,
                load_kg=self.record_load_kg,
                label="bay of records, between two uprights",
            )
        )
        # The lap halves the shelf at every crossing — which is exactly where a
        # shelf continuous over six supports is worked hardest.  Rather than
        # model a stepped section, sag the whole span as if it were all lap:
        # an upper bound that is far past pessimistic and still nothing.
        findings.extend(
            check_shelf_deflection(
                self.panel_material,
                span_mm=self.bay_clear_w,
                depth_mm=self.lap_depth,
                thickness_mm=self.panel_t,
                load_kg=self.record_load_kg,
                label="the same bay if the half-lap ran its whole length",
            )
        )
        findings.extend(
            check_shelf_deflection(
                self.panel_material,
                span_mm=self.bay_clear_w,
                depth_mm=self.panel_depth,
                thickness_mm=self.panel_t,
                load_kg=self.cd_load_kg,
                label="CD shelf, full",
            )
        )
        findings.extend(
            check_shelf_deflection(
                self.panel_material,
                span_mm=self.bay_clear_w,
                depth_mm=self.panel_depth,
                thickness_mm=self.panel_t,
                load_kg=TOP_LOAD_KG,
                label="top, under a turntable over one span",
            )
        )

        # The counterfactual the five bays exist to avoid — and the honest
        # answer to why there are five rather than three.
        undivided = check_shelf_deflection(
            self.panel_material,
            span_mm=self.clear_run,
            depth_mm=self.panel_depth,
            thickness_mm=self.panel_t,
            load_kg=self.record_load_kg * self.n_bays,
            label="the same shelf with no uprights under it",
            run_mm=self.clear_run,
        )
        findings.extend(undivided)
        if undivided and undivided[0].severity is Severity.WARN:
            findings.append(
                Finding(
                    Severity.INFO,
                    "bay",
                    f"so sag alone does not ask for {self.n_bays} bays — the "
                    "extra uprights are for the records, which lean and warp "
                    "in any run much over "
                    f"{mm_to_fractional_inch(self.bay_clear_w, 8)}",
                )
            )
        return findings

    def _construction_findings(self) -> list[Finding]:
        """Report what holds the kit together, and what does not."""
        footprint = self.n_uprights * self.panel_t * self.panel_depth
        findings: list[Finding] = [
            Finding(
                Severity.INFO,
                "stability",
                f"the case stands on {self.n_uprights} panel feet — "
                f"{footprint / IN**2:.0f} sq in of bearing over "
                f"{self.overall_w_in:g}\" — with the bottom shelf crossing "
                f"them {mm_to_fractional_inch(self.toe_reveal, 64)} clear of "
                "the floor, so an uneven floor cannot telegraph through a "
                "panel and the feet can be shimmed",
            ),
            Finding(
                Severity.INFO,
                "racking",
                "no back and no glue: racking is resisted by the fit of the "
                f"{self.n_uprights * self.n_shelves} crossings and by the "
                "top's housings, which is why the top is a structural part "
                "rather than a lid. Slack slots show up as sway, not as a gap",
            ),
            Finding(
                Severity.INFO,
                "racking",
                "nothing but friction stops a shelf sliding back out the front "
                "— loaded, it never will, and empty the piece is meant to come "
                "apart. A 1/4\" dowel through each crossing locks it if it has "
                "to travel loaded",
            ),
        ]

        if self.has_edging:
            findings.append(
                Finding(
                    Severity.INFO,
                    "material",
                    f"solid {self.species} edging against {self.panel_material} "
                    "veneer: the two start at different colours and darken at "
                    "different rates, and sapwood in the edging never catches "
                    "up — pull every strip from one board, and keep the piece "
                    "out of direct sun for its first months so it darkens "
                    "evenly",
                )
            )
        else:
            findings.append(
                Finding(
                    Severity.INFO,
                    "material",
                    f"no edging: {self.n_uprights + self.n_shelves} panels show "
                    "a bare plywood edge at the front, and paint does not fill "
                    "a void — grain filler or two coats of sanding sealer, "
                    "sanded back each time, or the voids telegraph through the "
                    "topcoat by the second summer",
                )
            )

        if self.has_solid_top:
            findings.append(
                Finding(
                    Severity.INFO,
                    "material",
                    f"a solid {self.top_material} top on a "
                    f"{self.panel_material} case: the two finish differently on "
                    "purpose — oil on the top, paint on the grid — and the "
                    "only piece that has to be selected for grain is the one "
                    "part anybody looks at",
                )
            )
            findings.extend(
                check_wood_movement(
                    self.top_material,
                    width_mm=self.overall_d,
                    label="the solid top, across its depth",
                )
            )
            findings.append(
                Finding(
                    Severity.INFO,
                    "movement",
                    "which the grid allows: the housings run front to back, "
                    "the same way the top moves, so nothing pins it. It lies "
                    "on the kit under its own weight — screws through the "
                    "shelves into it, or glue in the housings, would be the "
                    "one mistake that splits it",
                )
            )
        return findings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def run(variant: str, outdir: Path) -> CheckReport:
    """Build one console, write its cut list and diagrams, print the report.

    Parameters
    ----------
    variant : str
        Key in :data:`VARIANTS` — ``"cherry"`` or ``"painted"``.
    outdir : Path
        Directory for the generated CSV, Markdown, PDF, and CAD files.

    Returns
    -------
    CheckReport
        The design-check findings.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    console = MediaConsole(variant=variant)
    assembly = console.build()
    parts = extract(assembly)

    stem = f"media_console_{variant}"
    print(
        f"\n{'=' * 78}\n  Media console — {variant}, "
        f"a {console.grid_label} grid\n{'=' * 78}"
    )

    df = render_cut_list(
        parts,
        output_csv=outdir / f"{stem}_cutlist.csv",
        output_md=outdir / f"{stem}_cutlist.md",
    )
    print(df.to_string(index=False))

    report = console.check(assembly, parts)
    print(f"\n-- design checks {'-' * 61}")
    print(report.to_text())

    # Kept out of the design report: an undated price is a problem with the
    # quote, not with the joinery.
    print(f"\n-- prices {'-' * 68}")
    print(
        CheckReport()
        .extend(check_price_provenance(console.inventory, parts))
        .to_text()
    )

    sheet_materials = {s.material for s in console.inventory.sheet_goods}
    solid = [p for p in parts if p.material not in sheet_materials]
    sheet = [p for p in parts if p.material in sheet_materials]

    if solid:
        print(f"\n-- {console.species} to buy {'-' * 55}")
        plan = nest_hardwood(solid, console.inventory, console.species)
        print(plan.to_text())
        render_board_diagram(plan, output_pdf=outdir / f"{stem}_boards.pdf")

    if sheet:
        print(f"\n-- sheet goods {'-' * 63}")
        packed = pack_by_material(sheet, console.inventory)
        for key, res in packed.items():
            print(
                f"  {key:<28s} {res.sheets_used} sheet(s) of "
                f"{res.sheet_w_mm / IN:.0f}\"x{res.sheet_h_mm / IN:.0f}\", "
                f"{res.yield_fraction * 100:.0f}% yield"
            )
            if res.unpacked:
                print(f"    could not be nested: {sorted(set(res.unpacked))}")
            if res.sheets_used:
                slug = re.sub(r"[^0-9a-zA-Z]+", "_", key).strip("_")
                render_sheet_diagram(
                    res, output_pdf=outdir / f"{stem}_{slug}_sheets.pdf"
                )
                (outdir / f"{stem}_{slug}_cutorder.txt").write_text(
                    "\n".join(cut_sequence(res)) + "\n", encoding="utf-8"
                )
        summary = sheet_cost_summary(packed, console.inventory)
        print(f"  {'total':<28s} {summary.to_text()}")

    render_assembly(
        assembly,
        output_png=outdir / f"{stem}.png",
        title=f"Media console — {variant}, a {console.grid_label} grid",
    )
    export_assembly(
        assembly,
        output_step=outdir / f"{stem}.step",
        output_stl=outdir / f"{stem}.stl",
    )

    print(f"\nWrote cut list, diagrams, views and CAD export to {outdir}/")
    return report


def _spec(variant: str) -> ProjectSpec:
    """Return the gallery entry for one variant."""
    console = MediaConsole(variant=variant)
    if console.has_solid_top:
        material = (
            f"paint-grade {console.panel_material.replace('plywood_', '')} "
            f"plywood, painted, under a solid {console.top_material} top "
            f"overhanging {mm_to_fractional_inch(console.top_overhang, 32)} "
            "at each end"
        )
    else:
        material = (
            f"{console.panel_material.replace('plywood_', '')} plywood with "
            f"solid {console.species} front edges, finished clear"
        )
    return ProjectSpec(
        slug=f"media-console-{variant}",
        name=f"Media console — {variant}",
        summary=(
            f'{console.overall_w_in:g}"W x {console.overall_h_in:g}"H x '
            f'{console.overall_d_in:g}"D: a {console.grid_label} grid of '
            f"half-lapped panels that slide together — {console.n_bays} record "
            f'bays {console.record_bay_h_in:g}" tall under a '
            f'{console.cd_row_h_in:g}" CD row, and a clear top for the '
            f"turntable. {material.capitalize()}."
        ),
        species=console.species,
        source_url="https://luccahouse.com/",
        build=console.build,
        check=console.check,
        inventory=console.inventory,
        notes=(
            "A kit rather than a case: six uprights, two shelves and a top, "
            "no glue and no fasteners. Sized to a record rather than to a "
            "catalogue — the openings are held exactly and the bay width, the "
            "toe reveal and the sheet count are whatever the plywood actually "
            "measures."
        ),
        tags=["case", "storage", "flatpack", variant],
    )


#: Projects this module contributes to the gallery.
PROJECTS: list[ProjectSpec] = [_spec("cherry"), _spec("painted")]


def main() -> None:
    """Parse arguments and build the requested console or consoles."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--variant", choices=[*sorted(VARIANTS), "both"], default="cherry"
    )
    parser.add_argument("--outdir", type=Path, default=Path("build"))
    args = parser.parse_args()

    variants = sorted(VARIANTS) if args.variant == "both" else [args.variant]
    for variant in variants:
        run(variant, args.outdir)


if __name__ == "__main__":
    main()
