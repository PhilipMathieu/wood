"""Basement wall bench — 80" of bench hung on exposed studs, totes underneath.

The brief, as given::

    A workbench roughly 80" wide, to be mounted to exposed studs in the
    basement, with racks for project source storage bins underneath — a mix
    of 16 and 17 gallon bins, the medium options.  Simple: 2x4 framing and
    rails for the bins to slide on, not a plywood rack.

An earlier version of this model built the rack out of plywood: full-depth
ribs, housed shelf dadoes, a rebated front rail.  It worked, and it was more
than this job asks for — a shop-built cabinet where a stack of shelf brackets
would do.  This version is the "two by fours and rails" build: every framing
member below the benchtop is dimensional lumber, and the only joinery is a
notch and some screws.

The bracket, unchanged
-----------------------
The one idea worth keeping from the plywood version is the reason the bench
does not need legs.  A wall-hung bench rotates about the bottom of whatever
holds it — the load is out in front of the wall, so the top of the fixing is
pulled *away* from the studs and the bottom is pushed *into* them.  The only
thing a design controls is the **lever arm** between those two reactions,
because the pull on each lag is the overturning moment divided by it.

Two ledgers, lagged to the same studs, one near the top and one near the
floor, still do that job: :attr:`BasementBench.bracket_depth` is the same
number it was in the plywood version, because it depends only on where the
two ledgers sit, not on what spans between them.  What spans between them is
what got simpler.

Two by fours instead of a plywood cabinet
------------------------------------------
Each bay boundary gets one vertical **divider** — a 2x4 stud, full rack
height, notched at both ends to seat over the two ledgers exactly the way
the old plywood rib did.  It carries the compression/tension couple; nothing
else needs to.

At each tier, a pair of horizontal **rails** — also 2x4, on edge — run front
to back, one on each side of a bay, screwed toward the divider nearest them.
A tote's base is much narrower than its rim (see *Why the rails are spaced
to the base*), so they are positioned from the *bay's own centre*, not from
the divider, and the tote's base rests on top of them.  Each rail is a plain
cantilever with nothing tying its free end — the deflection finding for that
number is what decided *on edge* over *flat*, not a guess.

A separate **front rail**, laid flat, ties the tops of all the dividers
together at the very front of the bench and gives the benchtop's front edge
a screw line — the same part, and the same job, the plywood version had.  It
sits well above either tier's rails and has nothing to do with holding a
tote up; it is there for the top.

Why the rails are spaced to the base, not the bay opening
-----------------------------------------------------------
This is the mistake the plywood version's first draft made with its own
runners, and it is worth stating so it does not get made again: **a tote
tapers**.  Its widest point is the rim, at the top; a pair of rails spaced to
clear the *rim* — which is what the bay opening has to clear, so a tote can
be lowered in without binding on the dividers — is far wider than the tote's
*base*, and the tote drops straight through them.

So the bay opening (divider to divider) is sized to the tote's **rim**
plus clearance, and the **rails** are a separate, narrower pair, positioned
to the tote's **base** width plus a small bearing margin.  The gap between a
rail and the divider behind it is not wasted — it is exactly the width the
taper needs to clear on its way down.

The two totes
-------------
Two stock totes, read off the same kind of retailer listing the rest of this
project's prices come from, each governing a different dimension:

======================  ======================  ============  ===========
Tote                    Exterior (L x W x H)     Base (est.)   Governs
======================  ======================  ============  ===========
"17 gal" (68 qt)        26-7/8 x 18 x 12-1/2"    13-3/4"        tier pitch
"16 gal"                30-3/5 x 20-3/5 x 9-1/2" 15-3/4"* est.  bay width,
                                                                 bench depth
======================  ======================  ============  ===========

The 17-gallon figures are corroborated across two retailers (see
:data:`BIN_TYPES`) and its interior width is a published number, not a guess.
The 16-gallon figures are read off a listing with no interior dimension
published at all — its base width is *estimated* by applying the 17-gallon
tote's own measured taper ratio to the 16-gallon's rim width, and
:class:`Bin` carries an ``interior_measured=False`` flag wherever that is
true.  It is the one number in this file worth a tape measure before any rail
is cut.

Because the 16-gallon tote is now both the widest and the longest of the two,
it — not the 17-gallon — sets the bay width and the overall depth of the
bench.  Depth is still derived, not chosen: :attr:`BasementBench.overall_d`
comes out wider than the last version, because the longer tote does.

What simple costs
------------------
The one place this design gives something up rather than only saving effort:
a rail on edge is what keeps its own sag under a full tote inside span/240
(see the deflection findings), but "on edge" costs 2" more of vertical rack
per tier than the plywood version's thin shelf did.  Over two tiers that is
4" less clearance between the bottom rail and the slab, and at these tote
heights the report comes back with the gap under the rack reading as a
``WARN`` rather than the comfortable margin the plywood version had.  It is
still a positive number — the bench still hangs clear of the floor — and the
trade is real: a stiffer rail against a lower sweep clearance.  Nothing here
hides that trade or claims it away.

Two builds
----------
``hung``
    As briefed.  Nothing touches the floor — the lowest part of the bench is
    the bottom tier's rails — so the slab sweeps clean and there is no leg to
    kick or level.

``legged``
    Every divider runs down to a pair of 2x4 foot rails and the bench stands
    on the floor, for a wall that turns out to be furring strips rather than
    framing, or for hand work whose cyclic load walks a lag out of a stud.

Run it
------
::

    uv run python projects/basement_bench.py
    uv run python projects/basement_bench.py --mount legged --outdir build
    uv run python projects/basement_bench.py --mount both --outdir build
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, field
from pathlib import Path

from build123d import Box, Compound, Pos, Rotation

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
    estimate_mass_kg,
)
from woodshop.cutlist.extract import CutPart, extract
from woodshop.cutlist.optimize_1d import optimize_1d
from woodshop.cutlist.optimize_2d import pack_by_material
from woodshop.inventory import Inventory
from woodshop.lumber import actual_dimensions_mm, mm_to_fractional_inch
from woodshop.parts import Board, Panel, retag
from woodshop.pricing import sheet_cost_summary
from woodshop.project import ProjectSpec
from woodshop.render import (
    export_assembly,
    render_assembly,
    render_cut_list,
    render_sheet_diagram,
)
from woodshop.render.sheets import cut_sequence

IN = 25.4

#: Newtons per pound-force.
N_PER_LBF: float = 4.4482216

G_M_S2: float = 9.80665

#: Specific gravity of SPF framing lumber, oven-dry volume basis.
#:
#: NDS Table 12.3.3A gives G = 0.42 for Spruce-Pine-Fir, which is what a yard
#: in Maine sells as "whitewood" or "2x4".  Douglas fir-larch is 0.50 and every
#: capacity below scales as G**1.5, so a DF wall is about 30% stronger than
#: this model assumes — the safe direction to be wrong in.
SPF_SPECIFIC_GRAVITY: float = 0.42

#: Reference lateral design value ``Z`` for one lag screw in single shear,
#: 1-1/2" side member, into a main member of G = 0.42, lb, by shank diameter.
#:
#: NDS Table 12E, nearest tabulated case, rounded down, no adjustment factors
#: (C_D = 1.0, dry service).  A diameter not in this table is not checked for
#: shear rather than interpolated.
LAG_SHEAR_LB: dict[float, float] = {0.375: 210.0, 0.5: 270.0}

#: Reference compression design value perpendicular to grain for SPF, psi.
#:
#: NDS Supplement Table 4A, ``Fc_perp = 425 psi`` — what a divider's notch
#: bears against on the lower ledger.
_FC_PERP_PSI: float = 425.0

#: Allowable lateral load on one #10 x 3" structural wood screw into SPF, lb.
SCREW_SHEAR_LB: float = 130.0

#: Spacing of the screws that fasten the top's back edge into the top ledger.
_TOP_SCREW_SPACING_IN: float = 4.0

#: Wall thickness assumed when working a tote's base width back out of its
#: published interior width, inches — a tote's interior is quoted at the
#: bottom of the box, where it is narrowest, so interior + two walls is
#: roughly the base's outside width.
TOTE_WALL_IN: float = 0.125

#: Design mass of one full tote, kg — about 40 lb.  Not a volume calculation:
#: what sets the number is that the tote has to come out and go back, so the
#: design load is what a person will lift rather than what the box will hold.
BIN_DESIGN_MASS_KG: float = 18.0

#: What the top is expected to carry, kg.
TOP_LOAD_KG: float = 45.0

#: A person leaning hard on the front edge, kg — the load case that sizes the
#: wall, applied on top of a full rack and a loaded top.
FRONT_EDGE_LOAD_KG: float = 100.0

#: How far a person works comfortably across a bench at standing height, in.
COMFORTABLE_REACH_IN: float = 25.0

#: How far a cutter runs past the edge it opens on, mm.
_CUTTER_OVERRUN_MM: float = 2.0

#: How close a notch has to come to a part's edge before the cutter is run
#: past that edge rather than stopped on it, mm.
_EDGE_TOL_MM: float = 0.01

#: How far a rail sits inboard of a tote's true base edge, inches — the base
#: overlaps the rail rather than landing right at its inner corner.
#:
#: This is what the rails are spaced to, not the bay opening: a bay is wider
#: than the tote's base (that width has to clear the *rim*, which is wider
#: still), so a rail flush against the divider would be too far out to catch
#: anything.  The rails are positioned from the tote's own centreline
#: outward, independent of how wide the bay ended up.
RAIL_BEARING_MARGIN_IN: float = 0.5

#: length along +X, width up (+Z), thickness through (+Y) — a board laid flat
#: against the wall.
_ON_EDGE = Rotation(90, 0, 0)

#: thickness across (+X), width up (+Z), length through (+Y) — a rail: a 2x4
#: on edge, running front to back.  On edge rather than flat because a 2x4
#: laid flat sags noticeably more under a tote's weight over this span; see
#: the deflection findings for the number that decided it.
_ACROSS = Rotation(0, 0, 90) * Rotation(90, 0, 0)

#: thickness across (+X), width through (+Y), length up (+Z) — a divider: a
#: stud standing on end, its narrow face to the wall.
_UPRIGHT = Rotation(0, 90, 0)


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


def newtons(mass_kg: float) -> float:
    """Convert a mass to the force it applies under gravity.

    Parameters
    ----------
    mass_kg : float
        Mass in kilograms.

    Returns
    -------
    float
        Force in newtons.
    """
    return mass_kg * G_M_S2


def pounds_force(newtons_: float) -> float:
    """Convert newtons to pounds-force, the unit the fastener code is in.

    Parameters
    ----------
    newtons_ : float
        Force in newtons.

    Returns
    -------
    float
        Force in pounds-force.
    """
    return newtons_ / N_PER_LBF


def lag_withdrawal_lb_per_in(
    specific_gravity: float = SPF_SPECIFIC_GRAVITY,
    diameter_in: float = 0.5,
) -> float:
    """Return the reference withdrawal design value for a lag screw.

    In lb per inch of thread penetration, which is how NDS tabulates it.
    NDS equation 12.2-1, ``W = 1800 * G**1.5 * D**0.75``, for a lag screw
    inserted into the side grain of the main member.

    Parameters
    ----------
    specific_gravity : float, optional
        Main-member specific gravity, default :data:`SPF_SPECIFIC_GRAVITY`.
    diameter_in : float, optional
        Unthreaded shank diameter in inches, default 1/2".

    Returns
    -------
    float
        Allowable withdrawal, lb per inch of thread penetration into the stud.
    """
    return 1800.0 * specific_gravity**1.5 * diameter_in**0.75


@dataclass(frozen=True)
class Bin:
    """One stock storage tote the rack is sized to hold.

    Parameters
    ----------
    key : str
        Short name used in :data:`BIN_TYPES` and on the command line.
    name : str
        What it is called on the shelf.
    gallons : float
        Nominal capacity, as printed on the box.
    length_in, width_in, height_in : float
        Exterior, measured at the rim, which on a tapered box is the widest
        point and therefore what a bay opening has to clear.
    interior_w_in : float
        Interior width at the base, if published.  :attr:`base_w_in` is
        worked back from this — the number the rails are spaced to.
    interior_measured : bool
        Whether ``interior_w_in`` is a published figure (``True``) or
        estimated from another tote's taper ratio (``False``).  A ``False``
        entry is the one dimension in this file worth a tape measure before
        cutting anything.
    source, source_url, read_on : str
        Provenance, on the same principle as a price in ``stock.yaml``: a
        number without a date behind it is a number somebody remembered.
    """

    key: str
    name: str
    gallons: float
    length_in: float
    width_in: float
    height_in: float
    interior_w_in: float
    interior_measured: bool
    source: str
    source_url: str
    read_on: str

    @property
    def base_w_in(self) -> float:
        """Outside width of the tote's base, inches.

        The interior width plus two walls of :data:`TOTE_WALL_IN`.
        """
        return self.interior_w_in + 2 * TOTE_WALL_IN

    @property
    def label(self) -> str:
        """Short human label — ``17 gal``."""
        return f"{self.gallons:g} gal"

    @property
    def size_label(self) -> str:
        """The tote's exterior, as it would be written on a cut list."""
        return (
            f"{mm_to_fractional_inch(inches(self.length_in))} x "
            f"{mm_to_fractional_inch(inches(self.width_in))} x "
            f"{mm_to_fractional_inch(inches(self.height_in))}"
        )


#: The totes this rack is designed around, read from retailer listings.
#:
#: ``17gal``
#:     The medium tote sold as Project Source Commander at Lowe's and as the
#:     HDX Tough Tote at Home Depot — the same 26-7/8" x 18" x 12-1/2" box
#:     either way.  The **taller** one, so it sets the tier pitch, and its
#:     interior width is a published figure.
#:
#: ``16gal``
#:     A wider, longer, and noticeably shallower medium tote — 30-3/5" x
#:     20-3/5" x 9-1/2" — read off a listing that gives exterior dimensions
#:     only.  It is now the **widest and longest** of the two, so it sets the
#:     bay width and the depth of the whole bench.  Its base width is
#:     estimated from the 17-gallon tote's own measured taper (base is about
#:     76% of rim width) rather than measured, and :attr:`Bin.interior_measured`
#:     is ``False`` for exactly that reason.
BIN_TYPES: dict[str, Bin] = {
    "17gal": Bin(
        key="17gal",
        name="Project Source Commander / HDX 17 gal tough tote (68 qt)",
        gallons=17.0,
        length_in=26.875,
        width_in=18.0,
        height_in=12.5,
        interior_w_in=13.5,
        interior_measured=True,
        source="Lowe's and Home Depot listings, which agree to a tenth of an inch",
        source_url=(
            "https://www.homedepot.com/p/HDX-17-Gal-Tough-Storage-Tote-in-"
            "Black-with-Red-Lid-999-17G-HDX-R/330324132"
        ),
        read_on="2026-09-22",
    ),
    "16gal": Bin(
        key="16gal",
        name="16 gal medium tote",
        gallons=16.0,
        length_in=30.6,
        width_in=20.6,
        height_in=9.5,
        # (17gal interior + 2 walls) / 17gal rim = the 17-gallon tote's own
        # base/rim ratio, applied to this tote's rim because no interior
        # figure is published for it, then converted back to an interior
        # width the same way every other entry's is.
        interior_w_in=((13.5 + 2 * TOTE_WALL_IN) / 18.0) * 20.6 - 2 * TOTE_WALL_IN,
        interior_measured=False,
        source="retailer listing (exterior dimensions only), no interior figure published",
        source_url="",
        read_on="2026-09-22",
    ),
}


@dataclass(frozen=True)
class Mount:
    """How a build of this bench gets its load into the ground.

    Parameters
    ----------
    name : str
        Key in :data:`MOUNTS`.
    on_floor : bool
        Whether the dividers run down to foot rails on the slab.
    summary : str
        One line on what this build is for, printed in the report.
    """

    name: str
    on_floor: bool
    summary: str


#: The two builds.
MOUNTS: dict[str, Mount] = {
    "hung": Mount(
        name="hung",
        on_floor=False,
        summary=(
            "nothing on the floor — the wall carries the bench, the rack is "
            "the bracket, and the slab can be swept"
        ),
    ),
    "legged": Mount(
        name="legged",
        on_floor=True,
        summary=(
            "every divider down onto foot rails — the floor carries the "
            "bench and the wall only keeps it upright"
        ),
    ),
}


@dataclass
class BasementBench:
    """A parametric wall-hung workbench with a 2x4-and-rails tote rack.

    Three numbers are published — the width, the height of the work surface,
    and the number of tiers.  The depth is not a choice: it is derived from
    the longest tote in the mix, and so are the bay count and bay widths.

    Parameters
    ----------
    mount : str, optional
        Key in :data:`MOUNTS`, default ``"hung"``.
    bins : tuple of str, optional
        Keys in :data:`BIN_TYPES` — the totes on hand, default both.
    overall_w_in : float, optional
        Published width, default 80".
    overall_d_in : float, optional
        Published depth.  ``None``, the default, derives it from the longest
        tote plus the ledger behind it and the front overhang.
    top_height_in : float, optional
        Height of the finished work surface off the slab, default 36".
    top_overhang_end_in, top_overhang_front_in : float, optional
        How far the top runs past the frame at each end and at the front,
        default 1" and 2".
    n_tiers : int, optional
        Tiers of totes in the rack, default 2.
    n_bays : int, optional
        Bays across.  ``None``, the default, derives the most bays that hold
        the narrowest tote and then widens as many as will fit to the widest.
    bin_side_clearance_in : float, optional
        Minimum clear space between a tote's rim and the divider beside it,
        default 3/8" — what the bay opening has to clear, not what supports
        the tote.
    rail_bearing_margin_in : float, optional
        How far a rail sits inboard of a tote's base edge, default
        :data:`RAIL_BEARING_MARGIN_IN` — this is what the rails are spaced
        to, independent of the bay's own (rim-derived) clear width.
    bin_head_clearance_in : float, optional
        Clear space above the tallest tote, default 1/2".
    bin_back_clearance_in : float, optional
        Clear space behind the longest tote, in front of the ledgers,
        default 1/2" — what the bench's depth is built out of.
    bin_mass_kg : float, optional
        Mass of one full tote, default :data:`BIN_DESIGN_MASS_KG`.
    open_bays : tuple of int, optional
        Bays left without rails, for a shop vac, a bucket or a stool.
    frame_species : str, optional
        Solid stock for everything below the top, default ``"pine"``.
    ledger_nominal : str, optional
        Nominal ledger size, default ``"2x6"`` — two rows of lags need the
        edge distance, and it is what makes the bracket as deep as it is.
    frame_nominal : str, optional
        Nominal size for the dividers and the rails, default ``"2x4"`` — the
        one size this whole rack is built from.
    tie_rail_nominal, foot_nominal : str, optional
        Nominal sizes for the front tie rail and the foot rails, default
        ``"1x4"`` and ``"2x4"``.
    panel_material, panel_nominal_thickness : str, optional
        Sheet goods for the top, default 3/4" birch plywood.
    top_layers : int, optional
        Structural layers in the top, default 2.
    surface_material, surface_nominal_thickness : str, optional
        The sacrificial top sheet, default 1/4" Baltic birch — screwed down
        and not glued.
    stud_spacing_in : float, optional
        Stud spacing on centre, default 16".
    stud_nominal : str, optional
        What the studs actually are, default ``"2x4"``.  A ``1x`` entry means
        furring strips on masonry, and the wall findings become an ERROR.
    first_stud_offset_in : float, optional
        Distance from the left end of the ledger to the first stud centre.
        ``None``, the default, centres the studs in the ledger.
    lag_diameter_in, lag_length_in : float, optional
        Lag screw size, default 1/2" x 4".
    lags_per_stud : int, optional
        Lags into each stud, per ledger, default 2.
    top_load_kg, front_edge_load_kg : float, optional
        The two live-load cases: what sits on the top, and what leans on its
        front edge.  Defaults :data:`TOP_LOAD_KG` and
        :data:`FRONT_EDGE_LOAD_KG`.
    inventory : Inventory, optional
        Stock inventory.  Loaded from ``stock.yaml`` if not given.

    Raises
    ------
    ValueError
        If the mount or a bin key is unknown, if fewer than two bays or one
        tier are asked for, if a tote will not fit the width or the depth at
        all, or if the tiers come to more than the published height leaves
        under the top.
    """

    mount: str = "hung"
    bins: tuple[str, ...] = ("17gal", "16gal")

    overall_w_in: float = 80.0
    overall_d_in: float | None = None
    top_height_in: float = 36.0
    top_overhang_end_in: float = 1.0
    top_overhang_front_in: float = 2.0

    n_tiers: int = 2
    n_bays: int | None = None

    bin_side_clearance_in: float = 0.375
    rail_bearing_margin_in: float = RAIL_BEARING_MARGIN_IN
    bin_head_clearance_in: float = 0.5
    bin_back_clearance_in: float = 0.5
    bin_mass_kg: float = BIN_DESIGN_MASS_KG
    open_bays: tuple[int, ...] = ()

    frame_species: str = "pine"
    ledger_nominal: str = "2x6"
    frame_nominal: str = "2x4"
    tie_rail_nominal: str = "1x4"
    foot_nominal: str = "2x4"

    panel_material: str = "plywood_birch"
    panel_nominal_thickness: str = "3/4"
    top_layers: int = 2
    surface_material: str = "plywood_baltic_birch"
    surface_nominal_thickness: str = "1/4"

    stud_spacing_in: float = 16.0
    stud_nominal: str = "2x4"
    first_stud_offset_in: float | None = None
    lag_diameter_in: float = 0.5
    lag_length_in: float = 4.0
    lags_per_stud: int = 2

    top_load_kg: float = TOP_LOAD_KG
    front_edge_load_kg: float = FRONT_EDGE_LOAD_KG

    inventory: Inventory = field(default_factory=Inventory.load)

    def __post_init__(self) -> None:
        """Reject a bench whose numbers do not describe one."""
        if self.mount not in MOUNTS:
            raise ValueError(
                f"mount must be one of {sorted(MOUNTS)}, got {self.mount!r}"
            )
        unknown = [key for key in self.bins if key not in BIN_TYPES]
        if unknown:
            raise ValueError(f"unknown bin(s) {unknown}; known: {sorted(BIN_TYPES)}")
        if not self.bins:
            raise ValueError("a tote rack needs at least one kind of tote")
        if self.n_tiers < 1:
            raise ValueError(f"a rack needs at least one tier, got {self.n_tiers}")
        if len(self.bay_bins) < 2:
            raise ValueError(
                f"a {self.narrowest.label} tote is "
                f"{mm_to_fractional_inch(inches(self.narrowest.width_in))} wide "
                f"and needs {mm_to_fractional_inch(self.bay_cell(self.narrowest))} "
                f"of bench per bay; {mm_to_fractional_inch(self.frame_w)} of "
                "frame gives fewer than two"
            )
        if self.rack_bottom_z <= 0.0:
            raise ValueError(
                f"{self.n_tiers} tiers at "
                f"{mm_to_fractional_inch(self.tier_pitch)} come to "
                f"{mm_to_fractional_inch(self.rack_h)}, which hangs the bottom "
                f"rail {mm_to_fractional_inch(-self.rack_bottom_z)} below the "
                f'slab under a {self.top_height_in:g}" top'
            )
        if self.rail_run < inches(self.longest.length_in):
            raise ValueError(
                f"a {self.longest.label} tote is "
                f"{mm_to_fractional_inch(inches(self.longest.length_in))} long "
                f"and the rack is only {mm_to_fractional_inch(self.rail_run)} "
                f"deep behind the front rail"
            )
        for bay, bin_ in enumerate(self.bay_bins):
            base = inches(bin_.base_w_in)
            margin_mm = inches(self.rail_bearing_margin_in)
            if 2 * margin_mm >= base:
                raise ValueError(
                    f"rail_bearing_margin_in={self.rail_bearing_margin_in:g} "
                    f"leaves no channel at all under the {bin_.label} tote's "
                    f"{mm_to_fractional_inch(base)} base"
                )
            rail_outer_half = base / 2 - margin_mm + self.rail_w
            if rail_outer_half > self.bay_clear_w(bay) / 2:
                raise ValueError(
                    f"bay {bay}: a {self.frame_nominal} rail sized to the "
                    f"{bin_.label} tote's base reaches "
                    f"{mm_to_fractional_inch(rail_outer_half)} from centre, "
                    f"past the {mm_to_fractional_inch(self.bay_clear_w(bay) / 2)} "
                    "to the divider — it would run through it"
                )
        if self.divider_w >= self.rack_h:
            raise ValueError(
                f"a {self.frame_nominal} divider is "
                f"{mm_to_fractional_inch(self.divider_w)} deep and the rack "
                f"is only {mm_to_fractional_inch(self.rack_h)} tall"
            )

    # ------------------------------------------------------------------
    # What the build decides
    # ------------------------------------------------------------------

    @property
    def spec(self) -> Mount:
        """The :class:`Mount` this bench is built to."""
        return MOUNTS[self.mount]

    @property
    def on_floor(self) -> bool:
        """Whether the dividers run down to foot rails on the slab."""
        return self.spec.on_floor

    # ------------------------------------------------------------------
    # The totes
    # ------------------------------------------------------------------

    @property
    def bin_types(self) -> list[Bin]:
        """The totes on hand, widest first."""
        return sorted(
            (BIN_TYPES[key] for key in dict.fromkeys(self.bins)),
            key=lambda b: (-b.width_in, -b.height_in, b.key),
        )

    @property
    def widest(self) -> Bin:
        """The tote that sets the bay width."""
        return max(self.bin_types, key=lambda b: b.width_in)

    @property
    def narrowest(self) -> Bin:
        """The tote that sets how many bays can exist at all."""
        return min(self.bin_types, key=lambda b: b.width_in)

    @property
    def tallest(self) -> Bin:
        """The tote that sets the tier pitch."""
        return max(self.bin_types, key=lambda b: b.height_in)

    @property
    def longest(self) -> Bin:
        """The tote that sets the depth of the bench."""
        return max(self.bin_types, key=lambda b: b.length_in)

    def bay_cell(self, bin_: Bin) -> float:
        """Width one bay takes up for *bin_*, divider excluded, mm.

        The tote's rim plus its minimum clearance either side — what the
        divider-to-divider opening has to clear so the tote can be lowered in
        without binding.  The rails that actually support it are narrower
        than this and do not affect it.

        Parameters
        ----------
        bin_ : Bin
            The tote that bay holds.

        Returns
        -------
        float
            The width of bench one bay of this tote consumes.
        """
        return inches(bin_.width_in) + 2 * inches(self.bin_side_clearance_in)

    @property
    def bay_bins(self) -> tuple[Bin, ...]:
        """Which tote goes in which bay, left to right.

        Fit as many bays of the narrowest tote as the frame holds; then widen
        as many of them as will still fit to the widest tote.

        Returns
        -------
        tuple of Bin
            One entry per bay, widest first.
        """
        divider = self.divider_t
        narrow, wide = self.narrowest, self.widest
        if self.n_bays is not None:
            count = self.n_bays
        else:
            count = 0
            while (count + 1) * self.bay_cell(narrow) + (count + 2) * divider <= (
                self.frame_w
            ):
                count += 1
        if count <= 0:
            return ()
        budget = self.frame_w - (count + 1) * divider
        step = self.bay_cell(wide) - self.bay_cell(narrow)
        wide_count = count
        if step > 0:
            while (
                wide_count > 0
                and wide_count * self.bay_cell(wide)
                + (count - wide_count) * self.bay_cell(narrow)
                > budget
            ):
                wide_count -= 1
        return tuple([wide] * wide_count + [narrow] * (count - wide_count))

    @property
    def derived_n_bays(self) -> int:
        """Bays across — an outcome of the totes and the wall, not a choice."""
        return len(self.bay_bins)

    @property
    def n_dividers(self) -> int:
        """Dividers: one each side of every bay."""
        return self.derived_n_bays + 1

    @property
    def bay_slack(self) -> float:
        """Width left over after every bay has its tote and clearance, mm.

        Shared equally between the bays.
        """
        used = sum(self.bay_cell(b) for b in self.bay_bins)
        return self.frame_w - self.n_dividers * self.divider_t - used

    def bay_clear_w(self, bay: int) -> float:
        """Clear width between the two dividers of one bay, mm.

        Parameters
        ----------
        bay : int
            Bay index, 0 at the left.

        Returns
        -------
        float
            Divider face to divider face.
        """
        return self.bay_cell(self.bay_bins[bay]) + self.bay_slack / self.derived_n_bays

    def rail_channel(self, bay: int) -> float:
        """Clear channel between the two rails of one bay, mm.

        Sized to the tote's own base, not to the bay's (rim-derived) clear
        width — a bay is often wider than its tote needs, because the rim it
        was sized to is wider than the base, and any slack shared into the
        bay widens the opening further still.  Flushing a rail against the
        divider would follow that slack outward and let the tote fall
        through it; instead each rail is positioned from the tote's own
        centreline, independent of how wide the bay ended up.

        Parameters
        ----------
        bay : int
            Bay index.

        Returns
        -------
        float
            Inner-face-to-inner-face rail spacing.
        """
        base = inches(self.bay_bins[bay].base_w_in)
        return base - 2 * inches(self.rail_bearing_margin_in)

    def rail_overlap(self, bay: int) -> float:
        """How much of a rail's face sits under the tote's base, per side, mm.

        Parameters
        ----------
        bay : int
            Bay index.

        Returns
        -------
        float
            Equal to ``rail_bearing_margin_in`` by construction; the useful
            question is whether the rail's *own* footprint also clears the
            divider, which :meth:`check` verifies separately.
        """
        base = inches(self.bay_bins[bay].base_w_in)
        return (base - self.rail_channel(bay)) / 2

    @property
    def n_bins(self) -> int:
        """Totes the rack holds — bays that were left open hold none."""
        return (self.derived_n_bays - len(set(self.open_bays))) * self.n_tiers

    @property
    def rack_load_kg(self) -> float:
        """Mass of a full rack, kg."""
        return self.n_bins * self.bin_mass_kg

    @property
    def bin_tally(self) -> dict[str, int]:
        """How many of each tote the rack takes, by :class:`Bin` label."""
        tally: dict[str, int] = {}
        for bay, bin_ in enumerate(self.bay_bins):
            if bay in set(self.open_bays):
                continue
            tally[bin_.label] = tally.get(bin_.label, 0) + self.n_tiers
        return tally

    # ------------------------------------------------------------------
    # Stock
    # ------------------------------------------------------------------

    @property
    def sheet(self):
        """The sheet the top is cut from."""
        return self.inventory.sheet_for(
            self.panel_material, self.panel_nominal_thickness
        )

    @property
    def surface_sheet(self):
        """The sheet the sacrificial top surface is cut from."""
        return self.inventory.sheet_for(
            self.surface_material, self.surface_nominal_thickness
        )

    @property
    def panel_t(self) -> float:
        """Measured thickness of the top's structural plywood, mm."""
        return self.sheet.thickness_mm

    @property
    def surface_t(self) -> float:
        """Measured thickness of the sacrificial top sheet, mm."""
        return self.surface_sheet.thickness_mm

    @property
    def ledger_t(self) -> float:
        """Thickness of a ledger — how far it stands off the studs, mm."""
        return float(actual_dimensions_mm(self.ledger_nominal)[0].magnitude)

    @property
    def ledger_w(self) -> float:
        """Face width of a ledger — its vertical depth on the wall, mm."""
        return float(actual_dimensions_mm(self.ledger_nominal)[1].magnitude)

    @property
    def divider_t(self) -> float:
        """Thickness of a divider stud — its across-bench footprint, mm."""
        return float(actual_dimensions_mm(self.frame_nominal)[0].magnitude)

    @property
    def divider_w(self) -> float:
        """Width of a divider stud — how far it stands off the wall, mm."""
        return float(actual_dimensions_mm(self.frame_nominal)[1].magnitude)

    @property
    def rail_t(self) -> float:
        """Vertical footprint of a rail on edge, mm — the stock's own width.

        Contributes to :attr:`tier_pitch`.  A 2x4 on edge stands 3-1/2" tall,
        not 1-1/2" — the price of the stiffness that keeps it off a WARN.
        """
        return self.divider_w

    @property
    def rail_w(self) -> float:
        """Across-bench footprint of a rail on edge, mm.

        The stock's own thickness.  What :meth:`_rails` positions from the
        bay's centre, and what ``__post_init__`` checks clears the divider.
        """
        return self.divider_t

    @property
    def tie_rail_t(self) -> float:
        """Thickness of the front tie rail, mm — how far it hangs below the top."""
        return float(actual_dimensions_mm(self.tie_rail_nominal)[0].magnitude)

    @property
    def tie_rail_w(self) -> float:
        """Face width of the front tie rail, mm."""
        return float(actual_dimensions_mm(self.tie_rail_nominal)[1].magnitude)

    @property
    def foot_t(self) -> float:
        """Thickness of a foot rail, mm — zero in the hung build."""
        if not self.on_floor:
            return 0.0
        return float(actual_dimensions_mm(self.foot_nominal)[0].magnitude)

    @property
    def foot_w(self) -> float:
        """Face width of a foot rail, mm."""
        return float(actual_dimensions_mm(self.foot_nominal)[1].magnitude)

    @property
    def stud_t(self) -> float:
        """Thickness of a wall stud, mm — what a lag has to get through."""
        return float(actual_dimensions_mm(self.stud_nominal)[0].magnitude)

    @property
    def studs_are_furring(self) -> bool:
        """Whether the "studs" are 3/4" strapping rather than framing."""
        return self.stud_t < inches(1.0)

    # ------------------------------------------------------------------
    # The envelope, most of which the totes decide
    # ------------------------------------------------------------------

    @property
    def overall_w(self) -> float:
        """Published overall width, mm."""
        return inches(self.overall_w_in)

    @property
    def derived_overall_d(self) -> float:
        """Depth the longest tote requires, mm.

        The tote, the gap behind it, the ledger it stops against and the
        front overhang the top needs for a clamp.
        """
        return (
            inches(self.longest.length_in)
            + inches(self.bin_back_clearance_in)
            + self.ledger_t
            + inches(self.top_overhang_front_in)
        )

    @property
    def overall_d(self) -> float:
        """Overall depth, mm — derived unless it was given."""
        if self.overall_d_in is None:
            return self.derived_overall_d
        return inches(self.overall_d_in)

    @property
    def top_height(self) -> float:
        """Height of the finished work surface off the slab, mm."""
        return inches(self.top_height_in)

    @property
    def top_t(self) -> float:
        """Total thickness of the top, structural layers plus sacrificial, mm."""
        return self.top_layers * self.panel_t + self.surface_t

    @property
    def structural_top_t(self) -> float:
        """Thickness of the glued-up structural top alone, mm."""
        return self.top_layers * self.panel_t

    @property
    def frame_x0(self) -> float:
        """X of the frame's left end — the top overhangs it, mm."""
        return inches(self.top_overhang_end_in)

    @property
    def frame_w(self) -> float:
        """Width of the frame: the ledgers, the dividers, the feet, mm."""
        return self.overall_w - 2 * inches(self.top_overhang_end_in)

    @property
    def frame_d(self) -> float:
        """Depth of the frame from the stud faces forward, mm."""
        return self.overall_d - inches(self.top_overhang_front_in)

    @property
    def reach_over(self) -> float:
        """How much of the depth is past a comfortable reach, mm."""
        return max(0.0, self.overall_d - inches(COMFORTABLE_REACH_IN))

    # ------------------------------------------------------------------
    # Heights off the slab
    # ------------------------------------------------------------------

    @property
    def top_underside_z(self) -> float:
        """Underside of the top, and the top of every divider, mm off the slab."""
        return self.top_height - self.top_t

    @property
    def divider_top_z(self) -> float:
        """Top edge of a divider, mm — the top ledger bears here."""
        return self.top_underside_z

    @property
    def rack_top_z(self) -> float:
        """Ceiling a tote has to clear on its way out, mm.

        The front tie rail's underside: it is laid flat at the front and a
        tote slides out under it.
        """
        return self.top_underside_z - self.tie_rail_t

    @property
    def tier_pitch(self) -> float:
        """Vertical spacing from one tier's rail to the next, mm."""
        return (
            self.rail_t
            + inches(self.tallest.height_in)
            + inches(self.bin_head_clearance_in)
        )

    @property
    def rack_h(self) -> float:
        """Total height of the rack, mm."""
        return self.n_tiers * self.tier_pitch

    @property
    def rack_bottom_z(self) -> float:
        """Underside of the bottom tier's rail, mm off the slab.

        In the hung build this is the lowest point on the whole bench.
        """
        return self.rack_top_z - self.rack_h

    @property
    def divider_bottom_z(self) -> float:
        """Bottom edge of a divider, mm off the slab."""
        return self.foot_t if self.on_floor else self.rack_bottom_z

    @property
    def divider_h(self) -> float:
        """Height of a divider, mm."""
        return self.divider_top_z - self.divider_bottom_z

    @property
    def top_ledger_z(self) -> tuple[float, float]:
        """(bottom, top) of the top ledger, mm.

        Its top face is where the dividers and the top bear.
        """
        return (self.divider_top_z - self.ledger_w, self.divider_top_z)

    @property
    def rack_ledger_z(self) -> tuple[float, float]:
        """(bottom, top) of the lower ledger, mm.

        Flush with the bottom of the rack, which makes the bracket as deep
        as the design allows.
        """
        return (self.rack_bottom_z, self.rack_bottom_z + self.ledger_w)

    @property
    def bracket_depth(self) -> float:
        """Lever arm of the wall bracket, mm.

        Centroid to centroid of the two ledgers.  Depends only on where the
        ledgers sit, not on what spans between them — unchanged by whether
        that span is plywood or 2x4s.
        """
        top = sum(self.top_ledger_z) / 2
        bottom = sum(self.rack_ledger_z) / 2
        return top - bottom

    def tier_z(self, tier: int) -> tuple[float, float]:
        """(rail bottom, tote bottom) for one tier, mm off the slab.

        Parameters
        ----------
        tier : int
            Tier index, 0 at the top.

        Returns
        -------
        tuple of float
            Underside of that tier's rails, and the height a tote stands at.
        """
        top = self.rack_top_z - tier * self.tier_pitch - inches(
            self.bin_head_clearance_in
        )
        bottom = top - inches(self.tallest.height_in)
        return (bottom - self.rail_t, bottom)

    def head_clearance(self, bin_: Bin) -> float:
        """Clear space above one tote in its tier, mm.

        Parameters
        ----------
        bin_ : Bin
            The tote.

        Returns
        -------
        float
            The head clearance the tallest tote was given, plus whatever this
            one is shorter by.
        """
        return inches(
            self.bin_head_clearance_in + self.tallest.height_in - bin_.height_in
        )

    # ------------------------------------------------------------------
    # Positions across and through the bench
    # ------------------------------------------------------------------

    def divider_x(self, i: int) -> float:
        """X of divider *i*'s centreline, mm from the left end of the top.

        Parameters
        ----------
        i : int
            Divider index, 0 at the left end of the frame.

        Returns
        -------
        float
            Centre of the divider in assembly coordinates.
        """
        x = self.frame_x0 + self.divider_t / 2
        for bay in range(i):
            x += self.bay_clear_w(bay) + self.divider_t
        return x

    def bay_centre_x(self, bay: int) -> float:
        """X of the centre of one bay, mm.

        Parameters
        ----------
        bay : int
            Bay index.

        Returns
        -------
        float
            Midway between its two dividers.
        """
        return (self.divider_x(bay) + self.divider_x(bay + 1)) / 2

    @property
    def rail_run(self) -> float:
        """Length of a rail or the front tie rail, mm.

        It stops at the ledgers' front faces rather than running back to the
        wall, because the bottom tier sits at exactly the height of the lower
        ledger and would otherwise run into it.
        """
        return self.frame_d - self.ledger_t

    @property
    def stud_positions(self) -> list[float]:
        """X of every stud centre the ledgers cross, mm from the left of the top.

        Returns
        -------
        list of float
            Stud centres in assembly coordinates, left to right.
        """
        spacing = inches(self.stud_spacing_in)
        min_end = 2 * inches(self.lag_diameter_in)
        if self.first_stud_offset_in is None:
            span = self.frame_w - 2 * min_end
            count = max(1, int(span // spacing) + 1)
            offset = (self.frame_w - (count - 1) * spacing) / 2
        else:
            offset = inches(self.first_stud_offset_in)
            count = 0
            while offset + count * spacing <= self.frame_w:
                count += 1
        return [
            self.frame_x0 + offset + i * spacing
            for i in range(count)
            if 0.0 <= offset + i * spacing <= self.frame_w
        ]

    @property
    def n_lags_per_ledger(self) -> int:
        """Lags holding one ledger to the wall."""
        return len(self.stud_positions) * self.lags_per_stud

    @property
    def lag_dia_label(self) -> str:
        """Lag diameter as a fractional-inch string."""
        return mm_to_fractional_inch(inches(self.lag_diameter_in), 32)

    @property
    def lag_len_label(self) -> str:
        """Lag length as a fractional-inch string."""
        return mm_to_fractional_inch(inches(self.lag_length_in), 32)

    @property
    def lag_label(self) -> str:
        """The lag, as it is written on the box — ``1/2" x 4"``."""
        return f"{self.lag_dia_label} x {self.lag_len_label}"

    @property
    def lag_penetration(self) -> float:
        """Thread penetration of a lag into a stud, mm."""
        tip = inches(self.lag_diameter_in)
        return max(0.0, inches(self.lag_length_in) - self.ledger_t - tip)

    # ------------------------------------------------------------------
    # Assembly
    # ------------------------------------------------------------------

    def build(self) -> Compound:
        """Build the bench as a positioned build123d assembly.

        The origin is the one a wall-mounted piece is actually measured from:
        ``x`` runs along the wall from the left end of the top, ``y`` runs out
        from the **face of the studs**, and ``z`` is height off the slab.  So
        ``y = 0`` is the wall, ``z = 0`` is the floor, and in the hung build
        nothing in the model touches ``z = 0`` at all.

        Returns
        -------
        build123d.Compound
            Top, ledgers, dividers, rails, front tie rail, and — in the
            legged build — the foot rails, positioned.
        """
        children: list[object] = []
        mid_x = self.frame_x0 + self.frame_w / 2

        for i in range(self.top_layers):
            z = self.top_underside_z + self.panel_t * (i + 0.5)
            children.append(
                Pos(self.overall_w / 2, self.overall_d / 2, z) * self._top_skin()
            )
        children.append(
            Pos(
                self.overall_w / 2,
                self.overall_d / 2,
                self.top_underside_z + self.structural_top_t + self.surface_t / 2,
            )
            * self._top_surface()
        )

        for name, (z0, z1) in (
            ("top_ledger", self.top_ledger_z),
            ("rack_ledger", self.rack_ledger_z),
        ):
            children.append(
                Pos(mid_x, self.ledger_t / 2, (z0 + z1) / 2)
                * _ON_EDGE
                * self._ledger(name)
            )

        children.append(
            Pos(
                mid_x,
                self.frame_d - self.tie_rail_w / 2,
                self.rack_top_z + self.tie_rail_t / 2,
            )
            * self._front_rail()
        )

        divider_cz = self.divider_bottom_z + self.divider_h / 2
        for i in range(self.n_dividers):
            children.append(
                Pos(self.divider_x(i), self.divider_w / 2, divider_cz)
                * _UPRIGHT
                * self._divider()
            )

        children.extend(self._rails())

        if self.on_floor:
            for y in (
                self.ledger_t + self.foot_w / 2,
                self.frame_d - self.foot_w / 2,
            ):
                children.append(Pos(mid_x, y, self.foot_t / 2) * self._foot_rail())

        return Compound(children=children, label=f"basement_bench_{self.mount}")

    def _rails(self) -> list[object]:
        """Return every tote-support rail, positioned.

        Two per bay per tier, positioned from the bay's own centre by the
        tote's base width rather than flush against a divider — a bay is
        wider than its tote's base (it was sized to the wider rim, plus
        whatever slack the frame had left over), so a rail hung off the
        divider would follow that slack outward and miss the base entirely.
        Bays in ``open_bays`` get none.

        Returns
        -------
        list
            Placed :class:`~woodshop.parts.Board` rails.
        """
        placed: list[object] = []
        open_bays = set(self.open_bays)
        rail_cy = self.ledger_t + self.rail_run / 2
        for bay in range(self.derived_n_bays):
            if bay in open_bays:
                continue
            centre_x = self.bay_centre_x(bay)
            half_gap = self.rail_channel(bay) / 2 + self.rail_w / 2
            left_x = centre_x - half_gap
            right_x = centre_x + half_gap
            for tier in range(self.n_tiers):
                cz = self.tier_z(tier)[0] + self.rail_t / 2
                for x in (left_x, right_x):
                    placed.append(
                        Pos(x, rail_cy, cz) * _ACROSS * self._rail()
                    )
        return placed

    def _top_skin(self) -> Panel:
        """Return one structural layer of the top."""
        return Panel(
            length_mm=self.overall_w,
            width_mm=self.overall_d,
            material=self.panel_material,
            nominal_thickness=self.panel_nominal_thickness,
            label="top_skin",
            grain_direction="length",
            notes=(
                f"{self.top_layers} layers glued and screwed into one slab "
                f"{mm_to_fractional_inch(self.structural_top_t, 32)} thick; "
                "screwed down into the top ledger along the back edge at "
                f'{_TOP_SCREW_SPACING_IN:g}" o.c. — those screws are the '
                "bench's tension connection and work in shear, which is why "
                "they are not into a plywood edge"
            ),
        )

    def _top_surface(self) -> Panel:
        """Return the sacrificial top sheet."""
        return Panel(
            length_mm=self.overall_w,
            width_mm=self.overall_d,
            material=self.surface_material,
            nominal_thickness=self.surface_nominal_thickness,
            label="top_surface",
            grain_direction="none",
            notes=(
                "sacrificial: screwed down, never glued, countersunk well "
                "below the surface — the one part of this bench that is meant "
                "to be cut into and thrown away"
            ),
        )

    def _ledger(self, name: str) -> Board:
        """Return one wall ledger.

        Parameters
        ----------
        name : str
            ``"top_ledger"`` or ``"rack_ledger"`` — what the part is called on
            the cut list.  They are the same board and are deliberately not
            consolidated, because they do different structural jobs and the
            notes have to say which.

        Returns
        -------
        Board
            The ledger, with its own fixing schedule in its notes.
        """
        if name == "top_ledger":
            note = (
                f"lagged to {len(self.stud_positions)} studs, "
                f"{self.lags_per_stud} lags per stud, {self.lag_label}; the "
                "dividers bear on its top face and the top screws down into it"
            )
        else:
            note = (
                "lagged to the same studs; the dividers are notched over it "
                "and bear against its front face — the bottom of the bracket "
                "is compression and needs no fastener to work"
            )
        return Board(
            length_mm=self.frame_w,
            nominal=self.ledger_nominal,
            material=self.frame_species,
            label=name,
            notes=note,
        )

    def _divider(self):
        """Return one vertical divider stud, notched over both ledgers.

        The divider is the whole bracket in one piece: it bears on the top
        ledger's top face, carries every load hung below it down to that
        bearing, and its lower end is notched to press against the bottom
        ledger's front face.  It is one 2x4, one saw setup for each notch, no
        dado, no rebate.
        """
        divider = Board(
            length_mm=self.divider_h,
            nominal=self.frame_nominal,
            material=self.frame_species,
            label="divider",
            notes=(
                "stands on end against the wall, notched over both ledgers; "
                "bears the whole rack's weight down to the top ledger, and "
                "presses against the lower ledger's front face — that "
                "connection is compression and needs no fastener"
            ),
        )
        cz = self.divider_bottom_z + self.divider_h / 2
        cuts = [
            self._divider_notch(z0, z1, cz)
            for z0, z1 in (self.top_ledger_z, self.rack_ledger_z)
        ]
        cut = divider
        for solid in cuts:
            cut = cut - solid
        return retag(cut, like=divider)

    def _divider_notch(self, z0: float, z1: float, divider_cz: float):
        """Return the cutter for one ledger notch, in the divider's local frame.

        A divider is born with its length along +X (this becomes the
        assembly's vertical +Z once :data:`_UPRIGHT` is applied) and its
        width along +Y (becomes assembly +Y, depth).  The notch is described
        here in that *unrotated* local frame: local X is height, local Y is
        depth.

        Parameters
        ----------
        z0, z1 : float
            Bottom and top of the ledger, mm off the slab.
        divider_cz : float
            Height of the divider's centre, mm off the slab.

        Returns
        -------
        build123d.Box
            A positioned cutter, run past the divider's back edge — and past
            its top or bottom edge when the notch opens on one.
        """
        ov = _CUTTER_OVERRUN_MM
        x0 = z0 - divider_cz
        x1 = z1 - divider_cz
        # The divider's back face sits at local y = -width/2 (assembly y=0,
        # against the wall); the notch reaches ledger_t forward from there.
        y0 = -self.divider_w / 2 - ov
        y1 = -self.divider_w / 2 + self.ledger_t
        if x0 <= -self.divider_h / 2 + _EDGE_TOL_MM:
            x0 -= ov
        if x1 >= self.divider_h / 2 - _EDGE_TOL_MM:
            x1 += ov
        return Pos((x0 + x1) / 2, (y0 + y1) / 2, 0.0) * Box(
            x1 - x0, y1 - y0, self.divider_t + 2 * ov
        )

    def _rail(self) -> Board:
        """Return one tote-support rail.

        A length of the same 2x4 the divider is cut from, on edge — narrow
        face up — and screwed toward the divider it is nearest, close
        enough that a bracket or a couple of screws reaches it.  Nothing is
        notched or dadoed; the connection is butted and screwed, which is
        the whole reason this rack has three kinds of part instead of six.
        On edge rather than flat: a flat 2x4 sags noticeably more under a
        tote's weight over this span, and standing it up costs nothing but
        the screw angle.
        """
        return Board(
            length_mm=self.rail_run,
            nominal=self.frame_nominal,
            material=self.frame_species,
            label="rail",
            notes=(
                "on edge, narrow face up; screwed toward the nearby divider, "
                "no notch — a tote's base rests directly on the pair"
            ),
        )

    def _front_rail(self) -> Board:
        """Return the front tie rail.

        Laid flat across the tops of every divider at the front, tying them
        together and giving the top's front edge a screw line.  It sits at
        the top tier only: nothing below needs a front tie, because nothing
        below carries a load that depends on one — see the deflection
        findings for the number that backs that up.
        """
        return Board(
            length_mm=self.frame_w,
            nominal=self.tie_rail_nominal,
            material=self.frame_species,
            label="front_rail",
            notes=(
                "laid flat across the divider tops at the front; the top "
                "screws down into it"
            ),
        )

    def _foot_rail(self) -> Board:
        """Return one foot rail — the legged build only.

        Laid flat under every divider, front and back.  It is the part that
        meets the slab, so it is the part that gets wet: plan on replacing
        it, keep it off the concrete on plastic shims or levellers, and do
        not glue the dividers to it.
        """
        return Board(
            length_mm=self.frame_w,
            nominal=self.foot_nominal,
            material=self.frame_species,
            label="foot_rail",
            notes=(
                "laid flat under the dividers; screwed, never glued — it is "
                "the sacrificial part between the frame and a damp slab, and "
                "it is what takes the levellers"
            ),
        )

    # ------------------------------------------------------------------
    # Loads
    # ------------------------------------------------------------------

    def _load_cases(self, parts: list[CutPart]) -> list[tuple[str, float, float]]:
        """Return ``(name, mass_kg, lever_arm_mm)`` for every load on the bench.

        The lever arm is measured from the face of the studs.  The totes are
        summed bay by bay rather than lumped, because the two sizes are
        different lengths and the shorter one therefore sits with its mass
        further forward.

        Parameters
        ----------
        parts : list[CutPart]
            The cut list, used for the dead load.

        Returns
        -------
        list of tuple
            One entry per load case.
        """
        top_labels = {"top_skin", "top_surface"}
        top_mass = estimate_mass_kg([p for p in parts if p.label in top_labels])
        frame_mass = estimate_mass_kg([p for p in parts if p.label not in top_labels])

        open_bays = set(self.open_bays)
        tote_mass = 0.0
        tote_moment = 0.0
        for bay, bin_ in enumerate(self.bay_bins):
            if bay in open_bays:
                continue
            mass = self.bin_mass_kg * self.n_tiers
            arm = self.frame_d - inches(bin_.length_in) / 2
            tote_mass += mass
            tote_moment += mass * arm
        tote_arm = tote_moment / tote_mass if tote_mass else 0.0

        return [
            ("the top itself", top_mass, self.overall_d / 2),
            ("frame and rails", frame_mass, self.frame_d / 2),
            (f"{self.n_bins} full totes", tote_mass, tote_arm),
            ("tools and work on the top", self.top_load_kg, self.overall_d / 2),
            (
                "somebody leaning on the front edge",
                self.front_edge_load_kg,
                self.overall_d,
            ),
        ]

    def overturning_moment_nmm(self, parts: list[CutPart]) -> float:
        """Total moment trying to peel the bench off the wall, N-mm.

        Parameters
        ----------
        parts : list[CutPart]
            The cut list.

        Returns
        -------
        float
            Sum of every load times its distance forward of the studs.
        """
        return sum(newtons(kg) * arm for _, kg, arm in self._load_cases(parts))

    def total_load_n(self, parts: list[CutPart]) -> float:
        """Total vertical force on the bench, N.

        Parameters
        ----------
        parts : list[CutPart]
            The cut list.

        Returns
        -------
        float
            Dead plus live, in newtons.
        """
        return sum(newtons(kg) for _, kg, _ in self._load_cases(parts))

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def check(self, assembly: Compound, parts: list[CutPart]) -> CheckReport:
        """Run every design check against a built bench.

        Parameters
        ----------
        assembly : build123d.Compound
            The built bench, used for its envelope.
        parts : list[CutPart]
            The consolidated cut list.

        Returns
        -------
        CheckReport
            Every finding, in the order the questions get asked on site: does
            it fit, is the wall real, will the wall hold it, does a tote go
            in and stay up, does anything sag, and what does a basement do
            to it.
        """
        bb = assembly.bounding_box()
        report = CheckReport()
        report.extend(
            check_envelope(
                bb.size.X,
                bb.size.Y,
                bb.max.Z,
                self.overall_w,
                self.overall_d,
                self.top_height,
            )
        )
        report.extend(self._depth_findings())
        report.extend(self._stud_findings())
        report.extend(self._wall_findings(parts))
        report.extend(self._rack_findings())
        report.extend(self._stiffness_findings())
        report.extend(check_sheet_fit(parts, self.inventory))
        report.extend(check_thickness_substitution(parts, self.inventory))
        report.extend(check_material_suitability(parts, self.inventory))
        report.extend(self._basement_findings())
        return report

    def _depth_findings(self) -> list[Finding]:
        """Report where the bench's depth came from and what it costs.

        Returns
        -------
        list[Finding]
            The derivation, the reach it buys past, and the sheet of plywood
            it spends.
        """
        longest = self.longest
        findings = [
            Finding(
                Severity.INFO,
                "envelope",
                f"the depth is the tote's, not a choice: a {longest.label} tote "
                f"is {mm_to_fractional_inch(inches(longest.length_in))} long, "
                f"plus {mm_to_fractional_inch(inches(self.bin_back_clearance_in))} "
                f"behind it, a {mm_to_fractional_inch(self.ledger_t)} ledger and "
                f"{mm_to_fractional_inch(inches(self.top_overhang_front_in))} of "
                f"front overhang makes {mm_to_fractional_inch(self.overall_d)}",
            )
        ]
        if self.overall_d_in is not None:
            findings.append(
                Finding(
                    Severity.WARN,
                    "envelope",
                    f'overall_d_in={self.overall_d_in:g}" was given rather than '
                    f"derived; the totes need "
                    f"{mm_to_fractional_inch(self.derived_overall_d)}",
                )
            )
        if self.reach_over > 0:
            findings.append(
                Finding(
                    Severity.WARN,
                    "ergonomics",
                    f"at {mm_to_fractional_inch(self.overall_d)} deep the back "
                    f"{mm_to_fractional_inch(self.reach_over)} is past a "
                    f'comfortable {COMFORTABLE_REACH_IN:g}" reach: a shelf you '
                    "reach over, not bench. That is where the power strip, the "
                    "task light and the job in progress live — and it is also "
                    "why the leaning-on-the-front-edge load case is real rather "
                    "than hypothetical",
                )
            )

        sheet = self.sheet
        across = int(sheet.width_mm // self.overall_d)
        findings.append(
            Finding(
                Severity.INFO,
                "material",
                f"a {mm_to_fractional_inch(self.overall_d)} top takes a whole "
                f"{sheet.width_mm / IN:.0f}\"x{sheet.height_mm / IN:.0f}\" sheet "
                f"per layer — {across} of them fit across the sheet, where a "
                f"24\" top gets {int(sheet.width_mm // inches(24.0))}. The "
                "tote's length is paid for in plywood as well as in reach",
            )
        )
        return findings

    def _stud_findings(self) -> list[Finding]:
        """Report what the wall offers, and what would invalidate it.

        How many studs the ledger crosses, where the lags land on it, and what
        is behind them.

        Returns
        -------
        list[Finding]
            The stud layout, plus a WARN for anything that makes it worse than
            the model assumes and an ERROR for the one thing that makes it
            meaningless.
        """
        findings: list[Finding] = []
        studs = self.stud_positions
        n = len(studs)
        if n == 0:
            return [
                Finding(
                    Severity.ERROR,
                    "wall",
                    f"no stud falls within the {mm_to_fractional_inch(self.frame_w)} "
                    "ledger — there is nothing to lag to",
                )
            ]

        left = studs[0] - self.frame_x0
        right = self.frame_x0 + self.frame_w - studs[-1]
        min_end = 4 * inches(self.lag_diameter_in)
        severity = Severity.INFO if min(left, right) >= min_end else Severity.WARN
        findings.append(
            Finding(
                severity,
                "wall",
                f'{n} studs at {self.stud_spacing_in:g}" o.c. under a '
                f"{mm_to_fractional_inch(self.frame_w)} ledger, "
                f"{self.lags_per_stud} lags each: "
                f"{mm_to_fractional_inch(left)} of ledger past the left lag "
                f"and {mm_to_fractional_inch(right)} past the right "
                f"(want {mm_to_fractional_inch(min_end, 32)}, 4 diameters)",
            )
        )

        if self.studs_are_furring:
            findings.append(
                Finding(
                    Severity.ERROR,
                    "wall",
                    f"stud_nominal={self.stud_nominal!r} is strapping, not "
                    f"framing: a {self.lag_len_label} lag finds "
                    f"{mm_to_fractional_inch(self.stud_t)} of wood and then "
                    "masonry. Every wall finding below assumes a framed stud "
                    "wall and none of them holds — this needs concrete "
                    "anchors into the foundation, or the legged build",
                )
            )
        elif self.lag_penetration < 2 * self.stud_t / 3:
            findings.append(
                Finding(
                    Severity.WARN,
                    "wall",
                    f"a {self.lag_len_label} lag through a "
                    f"{mm_to_fractional_inch(self.ledger_t)} ledger reaches "
                    f"only {mm_to_fractional_inch(self.lag_penetration)} into "
                    f"a {mm_to_fractional_inch(self.stud_t)} stud",
                )
            )

        if self.stud_spacing_in > 16.5:
            findings.append(
                Finding(
                    Severity.WARN,
                    "wall",
                    f'{self.stud_spacing_in:g}" o.c. studs give {n} fixings '
                    f'where 16" would give '
                    f"{int(self.frame_w // inches(16.0)) + 1} — every "
                    "per-lag figure below scales straight with that",
                )
            )

        clash = inches(self.lag_diameter_in) + self.divider_t / 2
        for x in studs:
            nearest = min(
                (abs(x - self.divider_x(i)), i) for i in range(self.n_dividers)
            )
            if nearest[0] < clash:
                findings.append(
                    Finding(
                        Severity.WARN,
                        "wall",
                        f"the lag at {mm_to_fractional_inch(x)} lands under "
                        f"divider {nearest[1]}, whose notch bears on the "
                        "ledger's front face: counterbore that lag head and "
                        "its washer flush, or the divider will not seat",
                    )
                )
        return findings

    def _wall_findings(self, parts: list[CutPart]) -> list[Finding]:
        """Work the load path into the studs, in pounds, and show the margins.

        Everything here is a serviceability-level estimate against *reference*
        (allowable) design values with no adjustment factors applied.

        Parameters
        ----------
        parts : list[CutPart]
            The cut list, for the dead load.

        Returns
        -------
        list[Finding]
            The load cases, the bracket, and one finding per connection.
        """
        findings: list[Finding] = []
        cases = self._load_cases(parts)
        total_kg = sum(kg for _, kg, _ in cases)
        breakdown = ", ".join(f"{name} {kg:.0f} kg" for name, kg, _ in cases)
        findings.append(
            Finding(
                Severity.INFO,
                "load",
                f"{total_kg:.0f} kg ({pounds_force(newtons(total_kg)):.0f} lb) "
                f"all told — {breakdown}",
            )
        )

        studs = self.stud_positions
        if not studs:
            return findings

        n_lags = len(studs) * self.lags_per_stud
        v_lb = pounds_force(self.total_load_n(parts))
        m_nmm = self.overturning_moment_nmm(parts)
        t_lb = pounds_force(m_nmm / self.bracket_depth)

        findings.append(
            Finding(
                Severity.INFO,
                "bracket",
                "the rack is the bracket: "
                f"{mm_to_fractional_inch(self.bracket_depth)} between the two "
                f"ledgers' centroids, so "
                f"{m_nmm / (25.4 * N_PER_LBF):.0f} lb-in of overturning "
                f"becomes {t_lb:.0f} lb pulling the top ledger off the wall "
                f"and the same pushing the bottom one into it",
            )
        )
        shallow_lb = pounds_force(m_nmm / self.ledger_w)
        findings.append(
            Finding(
                Severity.INFO,
                "bracket",
                "on one ledger alone it would be "
                f"{mm_to_fractional_inch(self.ledger_w)} of lever arm and "
                f"{shallow_lb:.0f} lb — {shallow_lb / t_lb:.1f}x as much. This "
                "does not depend on what spans between the ledgers, which is "
                "why swapping the plywood rack for 2x4s changes none of it",
            )
        )

        if self.on_floor:
            findings.append(
                Finding(
                    Severity.INFO,
                    "wall",
                    "the legged build puts every divider on a foot rail, so "
                    f"the floor takes the {v_lb:.0f} lb and the lags below are "
                    "checked against the hung case anyway — the wall still "
                    "restrains the moment, and a bench that is also standing "
                    "on the floor is the conservative one",
                )
            )

        pen_in = self.lag_penetration / IN
        cap_lb = lag_withdrawal_lb_per_in(diameter_in=self.lag_diameter_in) * pen_in
        demand_lb = t_lb / n_lags
        findings.append(
            self._margin(
                "wall",
                f"withdrawal: {demand_lb:.0f} lb per lag against {cap_lb:.0f} lb "
                f"({self.lag_dia_label} lag, "
                f"{mm_to_fractional_inch(self.lag_penetration, 32)} of thread "
                f"in SPF at G={SPF_SPECIFIC_GRAVITY:g})",
                cap_lb / demand_lb if demand_lb > 0 else math.inf,
            )
        )

        shear_cap = LAG_SHEAR_LB.get(self.lag_diameter_in)
        shear_demand_lb = v_lb / n_lags
        if shear_cap is None:
            findings.append(
                Finding(
                    Severity.WARN,
                    "wall",
                    f"shear: {shear_demand_lb:.0f} lb per lag, but no tabulated "
                    f"value for a {self.lag_dia_label} lag — not checked. "
                    f"Tabulated: {sorted(LAG_SHEAR_LB)}",
                )
            )
        else:
            findings.append(
                self._margin(
                    "wall",
                    f"shear: {shear_demand_lb:.0f} lb per lag against "
                    f"{shear_cap:.0f} lb, with the whole vertical load put on "
                    f"the top ledger's {n_lags} lags",
                    shear_cap / shear_demand_lb
                    if shear_demand_lb > 0
                    else math.inf,
                    remedy=(
                        f"lags_per_stud={self.lags_per_stud + 1} would make it "
                        f"{v_lb / (len(studs) * (self.lags_per_stud + 1)):.0f} lb "
                        "each"
                    ),
                )
            )

        n_screws = int(self.frame_w // inches(_TOP_SCREW_SPACING_IN)) + 1
        screw_cap = n_screws * SCREW_SHEAR_LB
        findings.append(
            self._margin(
                "joint",
                f"the top's back edge into the top ledger: {t_lb:.0f} lb of "
                f"tension across {n_screws} screws at "
                f'{_TOP_SCREW_SPACING_IN:g}" o.c., {screw_cap:.0f} lb of shear '
                "capacity",
                screw_cap / t_lb if t_lb > 0 else math.inf,
            )
        )

        bearing_mm2 = self.n_dividers * self.divider_t * self.ledger_w
        bearing_mpa = (m_nmm / self.bracket_depth) / bearing_mm2
        findings.append(
            self._margin(
                "joint",
                "the dividers' notches bearing on the lower ledger: "
                f"{bearing_mpa:.2f} MPa ({bearing_mpa * 145.0:.0f} psi) over "
                f"{self.n_dividers} notches, against {_FC_PERP_PSI:.0f} psi "
                "perpendicular to grain",
                _FC_PERP_PSI / (bearing_mpa * 145.0) if bearing_mpa > 0 else math.inf,
            )
        )

        per_stud_lb = t_lb / len(studs)
        findings.append(
            Finding(
                Severity.INFO,
                "wall",
                f"each stud is pulled {per_stud_lb:.0f} lb away from its "
                "plates, which a framed wall shrugs off and a furred-out one "
                "does not — this is the number that makes stud_nominal the "
                "most important parameter in the file",
            )
        )
        return findings

    @staticmethod
    def _margin(
        category: str, message: str, ratio: float, remedy: str = ""
    ) -> Finding:
        """Turn a capacity-over-demand ratio into a finding of the right weight.

        Parameters
        ----------
        category : str
            Finding category.
        message : str
            The comparison, already written out in the caller's own units.
        ratio : float
            Capacity divided by demand.  Both sides are allowable values, so
            this is margin on top of a code safety factor, not instead of one.
        remedy : str, optional
            What would improve it, appended when it needs improving.

        Returns
        -------
        Finding
            ``INFO`` at 2.5x or better, ``WARN`` down to 1.0, ``ERROR`` below.
        """
        if ratio >= 2.5:
            severity = Severity.INFO
        elif ratio >= 1.0:
            severity = Severity.WARN
        else:
            severity = Severity.ERROR
        text = f"{message} — {ratio:.1f}x"
        if severity is not Severity.INFO and remedy:
            text += f"; {remedy}"
        return Finding(severity, category, text)

    def _rack_findings(self) -> list[Finding]:
        """Report whether a tote goes in, comes out, and stays up.

        Returns
        -------
        list[Finding]
            The grid the totes produced, the rim clearance, the rail bearing,
            and what the rack gave up to be a bracket.
        """
        tally = ", ".join(f"{n} x {label}" for label, n in self.bin_tally.items())
        findings: list[Finding] = [
            Finding(
                Severity.INFO,
                "rack",
                f"{self.derived_n_bays} bays x {self.n_tiers} tiers = "
                f"{self.n_bins} totes ({tally}), {self.rack_load_kg:.0f} kg "
                f"full, about "
                f"{sum(b.gallons for b in self.bay_bins) * self.n_tiers:.0f} "
                "gallons of project stock",
            )
        ]

        wide, narrow = self.widest, self.narrowest
        if wide is not narrow:
            dividers = self.n_dividers * self.divider_t
            over = self.derived_n_bays * self.bay_cell(wide) + dividers - self.frame_w
            spare = self.frame_w - self.derived_n_bays * self.bay_cell(narrow) - dividers
            if over > 0:
                findings.append(
                    Finding(
                        Severity.INFO,
                        "rack",
                        f"the mix is what makes {self.derived_n_bays} bays fit: "
                        f"{self.derived_n_bays} bays of the {wide.label} tote "
                        f"would want {mm_to_fractional_inch(over)} more bench "
                        f"than there is, and {self.derived_n_bays} of the "
                        f"{narrow.label} would leave "
                        f"{mm_to_fractional_inch(spare)} doing nothing",
                    )
                )
            elif narrow not in self.bay_bins:
                findings.append(
                    Finding(
                        Severity.INFO,
                        "rack",
                        f"every bay ended up sized for the {wide.label} tote "
                        f"— {self.derived_n_bays} of them fit with "
                        f"{mm_to_fractional_inch(-over)} to spare, so a "
                        f"{narrow.label} tote was never forced into a bay of "
                        "its own. It still goes in any bay here; it just "
                        "rides with more clearance than it needs",
                    )
                )

        for bay, bin_ in enumerate(self.bay_bins):
            if bay in set(self.open_bays):
                continue
            findings.extend(
                check_clearance(
                    f"bay {bay} ({bin_.label}, "
                    f"{mm_to_fractional_inch(self.bay_clear_w(bay))} clear), "
                    "each side of the tote's rim",
                    self.bin_side_clearance_in * IN,
                    inches(0.25),
                    inches(2.0),
                    tight_note=(
                        "a tote is floppy plastic and goes in crooked; under a "
                        "quarter inch it binds"
                    ),
                    loose_note=(
                        "past 2\" a side you are buying bench width to store "
                        "air — try a narrower bay or one more of them"
                    ),
                )
            )
            findings.append(
                Finding(
                    Severity.INFO,
                    "rail",
                    f"bay {bay}: rails {mm_to_fractional_inch(self.rail_channel(bay))} "
                    f"apart under a {bin_.label} tote whose base is about "
                    f"{mm_to_fractional_inch(inches(bin_.base_w_in))} wide — "
                    f"{mm_to_fractional_inch(self.rail_overlap(bay))} of "
                    "bearing a side"
                    + ("" if bin_.interior_measured else
                       f"; the {bin_.label} tote's base is estimated, not "
                       "measured — check it before cutting the rails"),
                )
            )

        for bin_ in self.bin_types:
            if bin_ is self.tallest:
                continue
            findings.append(
                Finding(
                    Severity.INFO,
                    "rack",
                    f"the {bin_.label} tote stands "
                    f"{mm_to_fractional_inch(inches(self.tallest.height_in - bin_.height_in))} "
                    f"lower than the {self.tallest.label}, so it rides with "
                    f"{mm_to_fractional_inch(self.head_clearance(bin_))} over "
                    "it. Uniform tiers are what let any tote go in any slot, "
                    "and that is worth more in a shop than the inch",
                )
            )

        if not self.on_floor:
            findings.extend(
                check_clearance(
                    "gap under the rack",
                    self.rack_bottom_z,
                    inches(3.0),
                    inches(10.0),
                    tight_note=(
                        "a push broom will not go under it, which is most of "
                        "why the bench is off the floor at all"
                    ),
                    loose_note="a tier's worth of storage given back to the slab",
                )
            )

        behind = self.rail_run - inches(self.longest.length_in)
        findings.append(
            Finding(
                Severity.INFO,
                "rack",
                f"a {self.longest.label} tote sits on a "
                f"{mm_to_fractional_inch(self.rail_run)} rail with "
                f"{mm_to_fractional_inch(behind)} to spare, and the "
                f"{mm_to_fractional_inch(self.ledger_t)} behind that is the "
                "ledger — the dead space and the structure are the same space",
            )
        )

        if not self.open_bays:
            findings.append(
                Finding(
                    Severity.WARN,
                    "rack",
                    "every bay is full, so a shop vac, a bucket and a floor "
                    "fan have nowhere to go and this bench has no knee space "
                    f"anywhere; open_bays=({self.derived_n_bays // 2},) gives "
                    "back one bay "
                    f"{mm_to_fractional_inch(self.bay_clear_w(self.derived_n_bays // 2))} "
                    f"wide and {mm_to_fractional_inch(self.rack_h)} tall",
                )
            )
        else:
            findings.append(
                Finding(
                    Severity.INFO,
                    "rack",
                    f"bay(s) {sorted(set(self.open_bays))} left open at the "
                    f"cost of {self.n_tiers * len(set(self.open_bays))} totes",
                )
            )
        return findings

    def _stiffness_findings(self) -> list[Finding]:
        """Report what actually moves when the bench is loaded.

        The benchtop, spanning divider to divider, is one candidate; the
        rails, cantilevered off a divider with nothing tying their far end,
        are another and are new to this build — the plywood rack's ribs were
        so deep this never mattered, and a 2x4 rail is a different animal.

        Returns
        -------
        list[Finding]
            One deflection finding per member, and one honest disclaimer.
        """
        findings: list[Finding] = []
        widest_bay = max(
            range(self.derived_n_bays), key=lambda b: self.bay_clear_w(b)
        )
        findings.extend(
            check_shelf_deflection(
                self.panel_material,
                span_mm=self.bay_clear_w(widest_bay),
                depth_mm=self.overall_d,
                thickness_mm=self.structural_top_t,
                load_kg=self.front_edge_load_kg,
                label=(
                    f"the top between two dividers, {self.front_edge_load_kg:.0f} "
                    "kg over one bay"
                ),
                run_mm=self.frame_w,
            )
        )

        e_mpa = 8_500.0  # pine, ELASTIC_MODULUS_MPA
        i_mm4 = self.rail_w * self.rail_t**3 / 12.0
        for tier in range(self.n_tiers):
            tip_n = newtons(self.bin_mass_kg)
            tip_mm = tip_n * self.rail_run**3 / (3.0 * e_mpa * i_mm4)
            limit_mm = self.rail_run / 240.0
            ratio = self.rail_run / tip_mm if tip_mm > 0 else math.inf
            severity = Severity.INFO if tip_mm <= limit_mm else Severity.WARN
            findings.append(
                Finding(
                    severity,
                    "deflection",
                    f"tier {tier} rail as a cantilever, {self.frame_nominal} "
                    f"on edge over {mm_to_fractional_inch(self.rail_run)}, a "
                    f"full {self.bin_mass_kg:.0f} kg tote on its nose: "
                    f"{tip_mm:.1f} mm at the tip (span/{ratio:.0f}; limit "
                    f"span/240 = {limit_mm:.1f} mm) — nothing ties its front "
                    "end; on edge rather than flat is what keeps that "
                    "acceptable without one",
                )
            )

        findings.append(
            Finding(
                Severity.WARN,
                "deflection",
                "the wall joint is also still what moves under real use — lag "
                "slip, the ledger crushing into the studs, and the studs "
                "themselves bowing. None of it is in a beam formula and all "
                "of it is why the hung build is for assembly and wiring "
                "rather than for planing: a hand plane is a cyclic horizontal "
                "load at exactly the height of the tension connection",
            )
        )
        return findings

    def _basement_findings(self) -> list[Finding]:
        """Report the things about a basement that a cut list cannot see.

        Returns
        -------
        list[Finding]
            Moisture, what is inside a stud bay, and the two obvious
            additions the geometry is already ready for.
        """
        findings = [
            Finding(
                Severity.WARN,
                "site",
                "before any lag goes in, find out what is in those stud bays. "
                "An exposed basement wall is where the wiring, the water line "
                f"and the old phone cable run, and a {self.lag_len_label} lag "
                f"reaches {mm_to_fractional_inch(self.lag_penetration)} past "
                "the far face of nothing — but a drill bit wandering off a "
                "stud edge reaches whatever is behind it",
            ),
            Finding(
                Severity.INFO,
                "site",
                "a wall-mounted bench cannot tip, which is the one thing a "
                "freestanding bench of this size has to buy with a heavy "
                "base. It is also why the rack can be loaded top-heavy "
                "without anybody thinking about it",
            ),
            Finding(
                Severity.INFO,
                "site",
                "plastic totes, not cardboard: a basement crosses its dew "
                "point several times a year, and a cardboard box is a "
                "humidity sponge with your hardware in it",
            ),
        ]
        if self.on_floor:
            findings.append(
                Finding(
                    Severity.WARN,
                    "site",
                    "the foot rails sit on a slab that wicks: put them on "
                    "plastic shims or levellers, leave them unglued, and "
                    "expect to replace them before anything else on the bench",
                )
            )
        else:
            findings.append(
                Finding(
                    Severity.INFO,
                    "site",
                    "nothing touches the slab: the lowest part of the bench "
                    f"is {mm_to_fractional_inch(self.rack_bottom_z)} up, so "
                    "the floor sweeps clean, a wet spring does not reach the "
                    "frame, and there is no foot to level on a floor that "
                    "was never flat",
                )
            )
        findings.append(
            Finding(
                Severity.INFO,
                "site",
                "the top overhangs the front rail by "
                f"{mm_to_fractional_inch(inches(self.top_overhang_front_in))} "
                "and each end by "
                f"{mm_to_fractional_inch(inches(self.top_overhang_end_in))} — "
                "that reveal is what a clamp jaw or a vice needs. A face vice "
                "at the left end wants the front rail and the end divider "
                "doubled behind it; nothing else in the design has to change",
            )
        )
        findings.append(
            Finding(
                Severity.INFO,
                "site",
                "the stud bays behind the bench are open, which is where the "
                "power strip, the cords and the task light go — screw the "
                "strip to the front face of the top ledger, above the totes "
                "and below the top, where nothing can sit on it",
            )
        )
        return findings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def run(bench: BasementBench, outdir: Path) -> CheckReport:
    """Build one bench, write its cut list and diagrams, print the report.

    Parameters
    ----------
    bench : BasementBench
        The bench to build.
    outdir : Path
        Directory for the generated CSV, Markdown, PDF, PNG and CAD files.

    Returns
    -------
    CheckReport
        The design-check findings.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    assembly = bench.build()
    parts = extract(assembly)

    stem = f"basement_bench_{bench.mount}"
    print(
        f"\n{'=' * 78}\n  Basement wall bench — {bench.mount}: "
        f"{bench.spec.summary}\n{'=' * 78}"
    )

    df = render_cut_list(
        parts,
        output_csv=outdir / f"{stem}_cutlist.csv",
        output_md=outdir / f"{stem}_cutlist.md",
    )
    print(df.to_string(index=False))

    report = bench.check(assembly, parts)
    print(f"\n-- design checks {'-' * 61}")
    print(report.to_text())

    print(f"\n-- prices {'-' * 68}")
    print(
        CheckReport().extend(check_price_provenance(bench.inventory, parts)).to_text()
    )

    sheet_materials = {s.material for s in bench.inventory.sheet_goods}
    solid = [p for p in parts if p.material not in sheet_materials]
    sheet = [p for p in parts if p.material in sheet_materials]

    if solid:
        print(f"\n-- {bench.frame_species} to buy {'-' * 56}")
        lengths = bench.inventory.stock_lengths_mm(bench.frame_species)
        if lengths:
            _print_board_plan(solid, lengths)
        else:
            print(
                f"  no stocked lengths for {bench.frame_species!r} in "
                "stock.yaml — nothing to optimise against"
            )

    if sheet:
        print(f"\n-- sheet goods {'-' * 63}")
        packed = pack_by_material(sheet, bench.inventory)
        for key, res in packed.items():
            print(
                f"  {key:<32s} {res.sheets_used} sheet(s) of "
                f"{res.sheet_w_mm / IN:.0f}\"x{res.sheet_h_mm / IN:.0f}\", "
                f"{res.yield_fraction * 100:.0f}% yield"
            )
            if res.unpacked:
                print(f"    could not be nested: {sorted(set(res.unpacked))}")
            if res.sheets_used:
                slug = _slug(key)
                render_sheet_diagram(
                    res, output_pdf=outdir / f"{stem}_{slug}_sheets.pdf"
                )
                (outdir / f"{stem}_{slug}_cutorder.txt").write_text(
                    "\n".join(cut_sequence(res)) + "\n", encoding="utf-8"
                )
        summary = sheet_cost_summary(packed, bench.inventory)
        print(f"  {'total':<32s} {summary.to_text()}")

    render_assembly(
        assembly,
        output_png=outdir / f"{stem}.png",
        title=f"Basement wall bench — {bench.mount}",
    )
    export_assembly(
        assembly,
        output_step=outdir / f"{stem}.step",
        output_stl=outdir / f"{stem}.stl",
    )

    print(f"\nWrote cut list, diagrams, views and CAD export to {outdir}/")
    return report


def _print_board_plan(parts: list[CutPart], stock_lengths_mm: list[float]) -> None:
    """Solve and print the dimensional-lumber cutting plan.

    Parameters
    ----------
    parts : list[CutPart]
        Solid-stock parts.
    stock_lengths_mm : list[float]
        Lengths the yard carries.
    """
    result = optimize_1d(parts, stock_lengths_mm=stock_lengths_mm)
    print(
        f"  {result.stock_used} boards, "
        f"{result.total_length_mm / IN / 12:.1f} linear ft, "
        f"{result.yield_fraction * 100:.0f}% yield"
    )
    for piece, cuts in zip(result.pieces, result.assignments):
        labels = ", ".join(f"{lbl} {mm_to_fractional_inch(mm)}" for lbl, mm in cuts)
        print(
            f"    {piece.stock_length_mm / IN / 12:.0f} ft: {labels}  "
            f"| offcut {mm_to_fractional_inch(piece.waste_mm)}"
        )


def _slug(text: str) -> str:
    """Return *text* as a filename-safe slug.

    Parameters
    ----------
    text : str
        Any label, e.g. ``'plywood_birch 3/4 (48" x 96")'``.

    Returns
    -------
    str
        Lower-case, alphanumerics and single underscores only.
    """
    out = "".join(c if c.isalnum() else "_" for c in text)
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_").lower()


def _spec(mount: str) -> ProjectSpec:
    """Return the gallery entry for one build.

    Parameters
    ----------
    mount : str
        Key in :data:`MOUNTS`.

    Returns
    -------
    ProjectSpec
        The registry entry :func:`woodshop.project.discover_projects` finds.
    """
    bench = BasementBench(mount=mount)
    tally = ", ".join(f"{n} x {label}" for label, n in bench.bin_tally.items())
    return ProjectSpec(
        slug=f"basement-bench-{mount}",
        name=f"Basement wall bench — {mount}",
        summary=(
            f'{bench.overall_w_in:g}"W x '
            f"{mm_to_fractional_inch(bench.overall_d)}D with a "
            f'{bench.top_height_in:g}" top, lagged to '
            f"{len(bench.stud_positions)} exposed studs at "
            f'{bench.stud_spacing_in:g}" o.c. Underneath, '
            f"{bench.derived_n_bays} bays x {bench.n_tiers} tiers of medium "
            f"storage totes ({tally}) on 2x4 dividers and rails — no plywood "
            f"below the top. {bench.spec.summary.capitalize()}."
        ),
        species=bench.frame_species,
        build=bench.build,
        check=bench.check,
        inventory=bench.inventory,
        notes=(
            "The storage is the structure: two 2x6 ledgers into the studs and "
            "2x4 dividers spanning between them turn a shelf into a "
            "cantilever bracket, exactly as a plywood rack would, and the "
            "check report works the load path into pounds rather than "
            "asserting it. Rails are 2x4 on edge, positioned from each bay's "
            "own centre by a tote's base rather than its rim, because a tote "
            "tapers and a pair of rails spaced to the rim lets it fall "
            "through. The one assumption the model cannot verify is that the "
            "exposed studs are framing and not furring strips on masonry — "
            "set stud_nominal to what is actually there."
        ),
        tags=["shop", "storage", "wall-mounted", mount],
    )


#: Projects this module contributes to the gallery.
PROJECTS: list[ProjectSpec] = [_spec("hung"), _spec("legged")]


def main() -> None:
    """Parse arguments and build the requested bench or benches."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mount", choices=[*sorted(MOUNTS), "both"], default="hung")
    parser.add_argument(
        "--bin",
        dest="bins",
        action="append",
        choices=sorted(BIN_TYPES),
        default=[],
        help="tote to size the rack around; repeatable, defaults to both",
    )
    parser.add_argument("--width", type=float, default=80.0)
    parser.add_argument(
        "--depth",
        type=float,
        default=None,
        help="overall depth; omit to derive it from the longest tote",
    )
    parser.add_argument("--height", type=float, default=36.0)
    parser.add_argument("--tiers", type=int, default=2)
    parser.add_argument("--stud-spacing", type=float, default=16.0)
    parser.add_argument(
        "--open-bay",
        type=int,
        action="append",
        default=[],
        help="leave this bay without rails; repeatable",
    )
    parser.add_argument("--outdir", type=Path, default=Path("build"))
    args = parser.parse_args()

    mounts = sorted(MOUNTS) if args.mount == "both" else [args.mount]
    bins = tuple(args.bins) if args.bins else ("17gal", "16gal")
    for mount in mounts:
        run(
            BasementBench(
                mount=mount,
                bins=bins,
                overall_w_in=args.width,
                overall_d_in=args.depth,
                top_height_in=args.height,
                n_tiers=args.tiers,
                stud_spacing_in=args.stud_spacing,
                open_bays=tuple(args.open_bay),
            ),
            args.outdir,
        )


if __name__ == "__main__":
    main()
