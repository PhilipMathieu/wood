"""Basement wall bench — 90" of bench hung on exposed studs, totes underneath.

The brief, as given::

    A workbench roughly 80" wide, to be mounted to exposed studs in the
    basement, with racks for project source storage bins underneath — a mix
    of 16 and 17 gallon bins, the medium options.  Simple: 2x4 framing and
    rails for the bins to slide on, not a plywood rack.

An earlier version of this model built the rack out of plywood; a second
rebuilt it in 2x4s but lost the one thing the plywood had — members that
actually reach from the wall to the front.  Its "dividers" were 3-1/2" posts
against the studs, the top was the only thing spanning out to the front
edge, and the tote rails were cantilevers screwed to the side of a post.
This version is the 2x4 build done as framing: every load has a member that
carries it and a joint that works in shear or bearing.

Side frames are the bracket
---------------------------
Every bay boundary is a **side frame** of 2x4s in one plane:

* a **back stile** against the wall, notched to hook over the top wall cleat
  and to seat against the bottom one;
* a **front stile** at the front, full height;
* an **arm** on edge under the top, from the wall to the front stile,
  half-lapped to both stiles at the top corners;
* in the hung build, a **brace** from the foot of the back stile up to the
  front corner — the diagonal that makes the frame a triangle and not a
  parallelogram that folds down the moment somebody leans on it.

A wall-hung bench rotates about the bottom of whatever holds it: the top of
the fixing is pulled *away* from the studs and the bottom is pushed *into*
them.  In each frame the arm carries that pull back to the wall in tension,
the brace carries the thrust down to the foot of the back stile in
compression, and the lever arm between them —
:attr:`BasementBench.bracket_depth` — is what divides the overturning moment
into a pull on each lag.  The frames sit in the planes between bays, so the
diagonal costs no tote space at all.

Two flat back cleats, lagged
----------------------------
A 2x6 **top cleat** and **bottom cleat** run the full width of the frame,
flat against the studs, and every lag goes through one of them.  The back
stiles are notched over both: at the top the stile's notch is closed above
the cleat, so the stile *hangs* on it, and the arm bears on its top edge; at
the bottom the notch seats the stile's foot against the cleat's face, which
is where the brace's thrust goes.  Each stile is screwed to each cleat, and
those screws — in withdrawal from the cleat's face — are the bench's tension
connection.

The bench can be built on the floor as one frame, with the cleats already
on, and lifted onto the wall to be lagged through.

Totes hang by the rim
---------------------
A tote's widest point is its rim, and its rim is a lip: a flange round the
top of the body.  So the totes ride on **runners** — 1x4s screwed flat to the
inside faces of each side frame, lapped onto both stiles — and hang from
their lips, the way every tote rack in a garage does.  Three things follow:

* A runner sits *beside* the tote's body, under its lip, so it costs no
  height at all: the tier pitch is the tote plus its head clearance and
  nothing else.  Three 16-gallon tiers need 30" of rack rather than the
  34-1/2" a rail under each tote's base needed.
* The bay opening is the rim plus a clearance each side, and the runner's
  3/4" projection past the frame face is what catches the lip: 3/8" of
  bearing a side at the default clearance.  Bays are therefore sized
  exactly — no slack is spread into them, because slack widens the bay and
  takes the bearing away with it; whatever width is left over goes to the
  top's end overhangs instead.
* Nothing spans a bay below the top except totes.  There is no rail across
  the front of any tier for a tote below to hit on its way in.

The lip itself is the one dimension neither retailer listing gives.
:class:`Bin` carries ``lip_measured=False`` for both totes; the figures used
are the ones a published tote-rack build works to, and it is the first thing
to put a tape measure on.

Three sixteens or two seventeens
--------------------------------
:attr:`BasementBench.tier_counts`, default :data:`DEFAULT_TIER_COUNTS`, gives
three tiers of the 9-1/2"-tall 16-gallon tote and two of the 12-1/2"-tall
17-gallon — a decision, the same way ``bay_layout`` is.  The frames run the
full height, so every bay shares one :attr:`BasementBench.rack_h`, the
largest of every type's own requirement; the type that needs less gets the
surplus back as head clearance.  Tiers are therefore pitched *per tote*: a
16-gallon slot is 10" apart and a 17-gallon one 15", and neither tote fits
the other's bay.

A replaceable top
-----------------
The arms, the front apron across their ends and the two cleats are the
top's whole substructure.  The top — two plywood layers glued to each other,
and a sacrificial sheet over them — is screwed down to that frame and never
glued to it, so either the sacrificial sheet or the whole slab comes off
without the frame noticing.

Two builds
----------
``hung``
    As briefed.  Nothing touches the floor — the lowest part of the bench is
    the bottom tier of totes — so the slab sweeps clean and there is no leg
    to kick or level.

``legged``
    Both stiles of every frame run down to a pair of 2x4 foot rails and the
    bench stands on the floor, for a wall that turns out to be furring strips
    rather than framing, or for hand work whose cyclic load walks a lag out
    of a stud.  The floor carries it, so the brace is left out.

Coordinates follow the rest of the repo: ``x`` along the wall from the left
end of the top, ``y`` from the room toward the wall (``y = 0`` is the face of
the studs, the front edge of the top is at ``-overall_d``), ``z`` up from the
slab.

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
from dataclasses import dataclass, field, replace
from pathlib import Path

from build123d import Box, Compound, Pos, Rotation

from woodshop.checks import (
    ELASTIC_MODULUS_MPA,
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
#: capacity below scales as G**1.5 or G**2, so a DF wall is stronger than this
#: model assumes — the safe direction to be wrong in.
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
#: NDS Supplement Table 4A, ``Fc_perp = 425 psi`` — what a back stile's notch
#: bears against on the bottom cleat.
_FC_PERP_PSI: float = 425.0

#: Shank diameter of the #10 structural screw that fastens a stile to a cleat.
SCREW_DIAMETER_IN: float = 0.19

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

#: Past this much top overhanging each end of the frame, the width is buying
#: a shelf rather than a bench, inches.
_MAX_END_OVERHANG_IN: float = 6.0

#: How far a cutter runs past the face it opens on, mm.
_CUTTER_OVERRUN_MM: float = 2.0

#: length along +X, width up (+Z), thickness through (+Y) — a cleat or the
#: apron: a board standing on edge, parallel to the wall.
_ON_EDGE = Rotation(90, 0, 0)

#: thickness across (+X), length through (+Y), width up (+Z) — an arm or a
#: runner: a board on edge running from the wall to the front.
_FRONT_TO_BACK = Rotation(0, 90, 90)

#: thickness across (+X), width through (+Y), length up (+Z) — a stile.
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


def screw_withdrawal_lb_per_in(
    specific_gravity: float = SPF_SPECIFIC_GRAVITY,
    diameter_in: float = SCREW_DIAMETER_IN,
) -> float:
    """Return the reference withdrawal design value for a wood screw.

    NDS equation 12.2-2, ``W = 2850 * G**2 * D``, side grain.

    Parameters
    ----------
    specific_gravity : float, optional
        Main-member specific gravity, default :data:`SPF_SPECIFIC_GRAVITY`.
    diameter_in : float, optional
        Shank diameter in inches, default a #10.

    Returns
    -------
    float
        Allowable withdrawal, lb per inch of thread penetration.
    """
    return 2850.0 * specific_gravity**2 * diameter_in


def _box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> Box:
    """Return an axis-aligned box spanning the given world ranges, mm."""
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(
        x1 - x0, y1 - y0, z1 - z0
    )


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
        Exterior, lid on, measured at the rim — the widest point, and what a
        bay opening has to clear.
    lip_in : float
        How far the rim's flange stands out from the body just below it,
        each side.  What a runner catches.
    lip_drop_in : float
        From the top of the lid down to the underside of the flange — where
        the tote's weight lands on a runner.
    lip_measured : bool
        Whether the two lip figures were measured on this tote (``True``) or
        taken from a published tote-rack build (``False``).  A ``False``
        entry is worth a tape measure before any runner is screwed on.
    source, source_url, read_on : str
        Provenance for the exterior dimensions, on the same principle as a
        price in ``stock.yaml``: a number without a date behind it is a
        number somebody remembered.
    lip_source : str
        Where the lip figures came from.
    """

    key: str
    name: str
    gallons: float
    length_in: float
    width_in: float
    height_in: float
    lip_in: float
    lip_drop_in: float
    lip_measured: bool
    source: str
    source_url: str
    read_on: str
    lip_source: str

    @property
    def body_w_in(self) -> float:
        """Width of the body just below the lip, inches."""
        return self.width_in - 2 * self.lip_in

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


_LIP_SOURCE = (
    "Family Handyman's DIY tote storage rack (HDX totes): a 1-1/4\" flange "
    "that is about 1-5/8\" deep — read 2026-09-23 through search summaries, "
    "the article itself was not reachable; not measured on either tote here"
)

#: The totes this rack is designed around, read from retailer listings.
#:
#: ``17gal``
#:     The medium tote sold as Project Source Commander at Lowe's and as the
#:     HDX Tough Tote at Home Depot — the same 26-7/8" x 18" x 12-1/2" box
#:     either way.  The **taller** of the two.
#:
#: ``16gal``
#:     A wider, longer, and noticeably shallower medium tote — 30-3/5" x
#:     20-3/5" x 9-1/2".  The **widest and longest** of the two, so it sets
#:     the depth of the whole bench.
BIN_TYPES: dict[str, Bin] = {
    "17gal": Bin(
        key="17gal",
        name="Project Source Commander / HDX 17 gal tough tote (68 qt)",
        gallons=17.0,
        length_in=26.875,
        width_in=18.0,
        height_in=12.5,
        lip_in=1.25,
        lip_drop_in=1.625,
        lip_measured=False,
        source="Lowe's and Home Depot listings, which agree to a tenth of an inch",
        source_url=(
            "https://www.homedepot.com/p/HDX-17-Gal-Tough-Storage-Tote-in-"
            "Black-with-Red-Lid-999-17G-HDX-R/330324132"
        ),
        read_on="2026-09-22",
        lip_source=_LIP_SOURCE,
    ),
    "16gal": Bin(
        key="16gal",
        name="16 gal medium tote",
        gallons=16.0,
        length_in=30.6,
        width_in=20.6,
        height_in=9.5,
        lip_in=1.25,
        lip_drop_in=1.625,
        lip_measured=False,
        source="retailer listing (exterior dimensions only)",
        source_url="",
        read_on="2026-09-22",
        lip_source=_LIP_SOURCE,
    ),
}

#: The shipped bay composition: two bays for the 16-gallon tote and two for
#: the 17-gallon, each sized to its own tote rather than whatever the
#: fit-and-widen packer would otherwise land on.
#:
#: Left to the packer, these two totes never actually mix in one rack at 80"
#: — the algorithm always prefers the wider tote when it fits.  A dedicated
#: bay for each is a design decision, and it costs bench width to get it,
#: which is why :attr:`BasementBench.overall_w_in` defaults to 90" and not 80".
DEFAULT_BAY_LAYOUT: tuple[str, ...] = ("16gal", "16gal", "17gal", "17gal")

#: Tiers stacked in one bay of each tote: three of the shorter 16-gallon
#: tote, two of the taller 17-gallon — not derived, a decision, the same way
#: :data:`DEFAULT_BAY_LAYOUT` is.
DEFAULT_TIER_COUNTS: dict[str, int] = {"16gal": 3, "17gal": 2}


@dataclass(frozen=True)
class Mount:
    """How a build of this bench gets its load into the ground.

    Parameters
    ----------
    name : str
        Key in :data:`MOUNTS`.
    on_floor : bool
        Whether the stiles run down to foot rails on the slab.
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
            "nothing on the floor — braced side frames on two lagged cleats "
            "carry the bench, and the slab can be swept"
        ),
    ),
    "legged": Mount(
        name="legged",
        on_floor=True,
        summary=(
            "every stile down onto foot rails — the floor carries the bench "
            "and the wall only keeps it upright"
        ),
    ),
}


@dataclass
class BasementBench:
    """A parametric wall-hung workbench over a rack of rim-hung totes.

    Three numbers are published — the width, the height of the work surface,
    and the tiers of each tote.  The depth is derived from the longest tote,
    and the bay widths from each bay's own tote.

    Parameters
    ----------
    mount : str, optional
        Key in :data:`MOUNTS`, default ``"hung"``.
    bins : tuple of str, optional
        Keys in :data:`BIN_TYPES` — the totes on hand, default both.
    overall_w_in : float, optional
        Width of the top, default 90".  The frame is exactly as wide as its
        bays need; the rest is end overhang.
    overall_d_in : float, optional
        Published depth.  ``None``, the default, derives it from the longest
        tote plus the cleat behind it, the apron in front and the overhang.
    top_height_in : float, optional
        Height of the finished work surface off the slab, default 40".
    top_overhang_end_in : float, optional
        The least the top may overhang the frame at each end, default 1".
    top_overhang_front_in : float, optional
        How far the top runs past the apron, default 2".
    tier_counts : dict of str to int, optional
        Tiers stacked in a bay of each tote, default
        :data:`DEFAULT_TIER_COUNTS`.  Every key in ``bins`` needs an entry.
    n_bays : int, optional
        Bays across.  Ignored when ``bay_layout`` is given.  ``None``, the
        default when it is not, derives the most bays that hold the
        narrowest tote and then widens as many as will fit to the widest.
    bay_layout : tuple of str, optional
        Which tote goes in which bay, left to right, default
        :data:`DEFAULT_BAY_LAYOUT`.  ``None`` falls back to the packer.
    bin_side_clearance_in : float, optional
        Clear space between a tote's rim and the frame face each side,
        default 3/8".  With a 3/4" runner it also sets the lip's bearing.
    bin_head_clearance_in : float, optional
        Least clear space above a tote's lid, default 1/2".
    bin_back_clearance_in : float, optional
        Clear space behind the longest tote, in front of the cleats,
        default 1/2".
    bin_mass_kg : float, optional
        Mass of one full tote, default :data:`BIN_DESIGN_MASS_KG`.
    open_bays : tuple of int, optional
        Bays left without runners, for a shop vac, a bucket or a stool.
    frame_species : str, optional
        Solid stock for everything below the top, default ``"pine"``.
    wall_cleat_nominal : str, optional
        The two cleats lagged to the studs, default ``"2x6"`` — two rows of
        lags need its face width.
    frame_nominal : str, optional
        Stiles, arms and braces, default ``"2x4"``.
    runner_nominal : str, optional
        What the totes' lips ride on, default ``"1x4"`` screwed flat to the
        frame: its thickness is how far it reaches under the lip.
    apron_nominal : str, optional
        The front apron across the arms, on edge, default ``"1x4"``.
    foot_nominal : str, optional
        Foot rails in the legged build, default ``"2x4"``.
    panel_material, panel_nominal_thickness : str, optional
        Sheet goods for the top, default 3/4" birch plywood.
    top_layers : int, optional
        Plywood layers in the top, glued to each other, default 2.
    surface_material, surface_nominal_thickness : str, optional
        The sacrificial top sheet, default 1/4" Baltic birch.
    stud_spacing_in : float, optional
        Stud spacing on centre, default 16".
    stud_nominal : str, optional
        What the studs actually are, default ``"2x4"``.  A ``1x`` entry means
        furring strips on masonry, and the wall findings become an ERROR.
    first_stud_offset_in : float, optional
        Distance from the left end of the cleats to the first stud centre.
        ``None``, the default, centres the studs in the cleats.
    lag_diameter_in, lag_length_in : float, optional
        Lag screw size, default 1/2" x 4".
    lags_per_stud : int, optional
        Lags into each stud, per cleat, default 2.
    stile_screws_per_cleat : int, optional
        #10 structural screws from each back stile into each cleat,
        default 4.
    top_load_kg, front_edge_load_kg : float, optional
        The two live-load cases.  Defaults :data:`TOP_LOAD_KG` and
        :data:`FRONT_EDGE_LOAD_KG`.
    inventory : Inventory, optional
        Stock inventory.  Loaded from ``stock.yaml`` if not given.

    Raises
    ------
    ValueError
        If the mount or a bin key is unknown, if fewer than two bays or one
        tier are asked for, if the bays do not fit the width, if a tote will
        not fit the depth, if its lip misses the runners or its body binds
        on them, or if the tiers hang below the slab.
    """

    mount: str = "hung"
    bins: tuple[str, ...] = ("17gal", "16gal")

    overall_w_in: float = 90.0
    overall_d_in: float | None = None
    top_height_in: float = 40.0
    top_overhang_end_in: float = 1.0
    top_overhang_front_in: float = 2.0

    tier_counts: dict[str, int] = field(
        default_factory=lambda: dict(DEFAULT_TIER_COUNTS)
    )
    n_bays: int | None = None
    bay_layout: tuple[str, ...] | None = DEFAULT_BAY_LAYOUT

    bin_side_clearance_in: float = 0.375
    bin_head_clearance_in: float = 0.5
    bin_back_clearance_in: float = 0.5
    bin_mass_kg: float = BIN_DESIGN_MASS_KG
    open_bays: tuple[int, ...] = ()

    frame_species: str = "pine"
    wall_cleat_nominal: str = "2x6"
    frame_nominal: str = "2x4"
    runner_nominal: str = "1x4"
    apron_nominal: str = "1x4"
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
    stile_screws_per_cleat: int = 4

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
        for key in self.bins:
            count = self.tier_counts.get(key)
            if count is None:
                raise ValueError(f"tier_counts has no entry for bin {key!r}")
            if count < 1:
                raise ValueError(
                    f"a rack needs at least one tier, tier_counts[{key!r}]={count}"
                )
        if self.bay_layout is not None:
            bad = [k for k in self.bay_layout if k not in self.bins]
            if bad:
                raise ValueError(f"bay_layout key(s) {bad} not in bins={self.bins}")
        if len(self.bay_bins) < 2:
            if self.bay_layout is not None:
                raise ValueError(
                    f"bay_layout={self.bay_layout} names fewer than two bays"
                )
            raise ValueError(
                f"a {self.narrowest.label} tote is "
                f"{mm_to_fractional_inch(inches(self.narrowest.width_in))} wide "
                f"and needs {mm_to_fractional_inch(self.bay_cell(self.narrowest))} "
                f"of bench per bay; {mm_to_fractional_inch(self._frame_budget)} "
                "of frame gives fewer than two"
            )
        if self.frame_w > self._frame_budget:
            min_overall_in = (
                self.frame_w + 2 * inches(self.top_overhang_end_in)
            ) / IN
            raise ValueError(
                f"bay_layout {self.bay_layout!r} needs "
                f"{mm_to_fractional_inch(self.frame_w)} of frame, but "
                f'overall_w_in={self.overall_w_in:g}" leaves only '
                f"{mm_to_fractional_inch(self._frame_budget)} — widen to at "
                f'least {min_overall_in:.2f}"'
            )
        if self.tote_run < inches(self.longest.length_in):
            raise ValueError(
                f"a {self.longest.label} tote is "
                f"{mm_to_fractional_inch(inches(self.longest.length_in))} long "
                f"and the rack is only {mm_to_fractional_inch(self.tote_run)} "
                "deep between the cleats and the apron"
            )
        for bin_ in dict.fromkeys(self.bay_bins):
            if self.lip_bearing(bin_) <= 0.0:
                raise ValueError(
                    f"a {bin_.label} tote's rim falls between the runners: "
                    f"bin_side_clearance_in={self.bin_side_clearance_in:g} is "
                    f"as much as a {self.runner_nominal} runner reaches out "
                    f"({mm_to_fractional_inch(self.runner_t)})"
                )
            if self.body_clearance(bin_) <= 0.0:
                raise ValueError(
                    f"a {bin_.label} tote's body binds on the runners: its "
                    f"{mm_to_fractional_inch(inches(bin_.lip_in))} lip is less "
                    f"than the {mm_to_fractional_inch(self.lip_bearing(bin_))} "
                    "the runners reach under it"
                )
            stack = (
                inches(bin_.lip_drop_in)
                + self.runner_h
                + inches(self.bin_head_clearance_in)
            )
            if self.tier_pitch_for(bin_) < stack:
                raise ValueError(
                    f"at a {mm_to_fractional_inch(self.tier_pitch_for(bin_))} "
                    f"pitch the runner above a {bin_.label} tote comes down "
                    "onto its lid"
                )
        if self.rack_bottom_z <= 0.0:
            driver = self._driving_bin
            needed_top_height_in = self.top_height_in - self.rack_bottom_z / IN
            raise ValueError(
                f"{self.tiers_for(driver)} tiers of the {driver.label} tote "
                f"at {mm_to_fractional_inch(self._tight_tier_pitch(driver))} "
                f"need {mm_to_fractional_inch(self.rack_h)} of rack, which "
                "hangs the bottom tier's totes "
                f"{mm_to_fractional_inch(-self.rack_bottom_z)} below the slab "
                f'under a {self.top_height_in:g}" top — raise top_height_in '
                f'to at least {needed_top_height_in:.1f}" (that gives zero '
                "floor clearance; add more for a broom to pass under it)"
            )
        if self.brace_run <= 0.0:
            raise ValueError(
                f"a {mm_to_fractional_inch(self.frame_d)}-deep frame leaves no "
                "room between its stiles"
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
        """Whether the stiles run down to foot rails on the slab."""
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
        """The widest tote on hand."""
        return max(self.bin_types, key=lambda b: b.width_in)

    @property
    def narrowest(self) -> Bin:
        """The tote that sets how many bays can exist at all."""
        return min(self.bin_types, key=lambda b: b.width_in)

    @property
    def tallest(self) -> Bin:
        """The tallest tote on hand."""
        return max(self.bin_types, key=lambda b: b.height_in)

    @property
    def longest(self) -> Bin:
        """The tote that sets the depth of the bench."""
        return max(self.bin_types, key=lambda b: b.length_in)

    def bay_cell(self, bin_: Bin) -> float:
        """Clear width of a bay for *bin_*, frame face to frame face, mm.

        The rim plus its clearance each side — exactly, because any slack
        added here would come straight off the lip's bearing on the runners.

        Parameters
        ----------
        bin_ : Bin
            The tote that bay holds.

        Returns
        -------
        float
            The bay's clear width.
        """
        return inches(bin_.width_in) + 2 * inches(self.bin_side_clearance_in)

    @property
    def _frame_budget(self) -> float:
        """The most frame the published width allows, mm."""
        return self.overall_w - 2 * inches(self.top_overhang_end_in)

    @property
    def bay_bins(self) -> tuple[Bin, ...]:
        """Which tote goes in which bay, left to right.

        With ``bay_layout`` set (the default) this is just that layout,
        looked up.  With it cleared to ``None``, bays are packed instead: fit
        as many bays of the narrowest tote as the width holds, then widen as
        many of them as still fit to the widest tote.

        Returns
        -------
        tuple of Bin
            One entry per bay, left to right.
        """
        if self.bay_layout is not None:
            return tuple(BIN_TYPES[key] for key in self.bay_layout)
        stile = self.stile_t
        budget = self._frame_budget
        narrow, wide = self.narrowest, self.widest
        if self.n_bays is not None:
            count = self.n_bays
        else:
            count = 0
            while (count + 1) * self.bay_cell(narrow) + (count + 2) * stile <= budget:
                count += 1
        if count <= 0:
            return ()
        room = budget - (count + 1) * stile
        wide_count = count
        if self.bay_cell(wide) > self.bay_cell(narrow):
            while (
                wide_count > 0
                and wide_count * self.bay_cell(wide)
                + (count - wide_count) * self.bay_cell(narrow)
                > room
            ):
                wide_count -= 1
        return tuple([wide] * wide_count + [narrow] * (count - wide_count))

    @property
    def derived_n_bays(self) -> int:
        """Bays across."""
        return len(self.bay_bins)

    @property
    def n_frames(self) -> int:
        """Side frames: one each side of every bay."""
        return self.derived_n_bays + 1

    def bay_clear_w(self, bay: int) -> float:
        """Clear width between the two frames of one bay, mm.

        Parameters
        ----------
        bay : int
            Bay index, 0 at the left.

        Returns
        -------
        float
            Frame face to frame face.
        """
        return self.bay_cell(self.bay_bins[bay])

    def lip_bearing(self, bin_: Bin) -> float:
        """How far one runner reaches under a tote's lip, mm.

        The runner's projection past the frame face, less the rim's clearance
        to that face.

        Parameters
        ----------
        bin_ : Bin
            The tote.

        Returns
        -------
        float
            Bearing per side; zero or less and the tote drops through.
        """
        return self.runner_t - inches(self.bin_side_clearance_in)

    def body_clearance(self, bin_: Bin) -> float:
        """Clear space between a tote's body and each runner, mm.

        Parameters
        ----------
        bin_ : Bin
            The tote.

        Returns
        -------
        float
            The lip less the bearing; zero or less and the body binds.
        """
        return inches(bin_.lip_in) - self.lip_bearing(bin_)

    @property
    def n_bins(self) -> int:
        """Totes the rack holds — bays that were left open hold none."""
        open_bays = set(self.open_bays)
        return sum(
            self.tiers_for(bin_)
            for bay, bin_ in enumerate(self.bay_bins)
            if bay not in open_bays
        )

    @property
    def rack_load_kg(self) -> float:
        """Mass of a full rack, kg."""
        return self.n_bins * self.bin_mass_kg

    @property
    def bin_tally(self) -> dict[str, int]:
        """How many of each tote the rack takes, by :class:`Bin` label."""
        open_bays = set(self.open_bays)
        tally: dict[str, int] = {}
        for bay, bin_ in enumerate(self.bay_bins):
            if bay in open_bays:
                continue
            tally[bin_.label] = tally.get(bin_.label, 0) + self.tiers_for(bin_)
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
        """Measured thickness of the top's plywood, mm."""
        return self.sheet.thickness_mm

    @property
    def surface_t(self) -> float:
        """Measured thickness of the sacrificial top sheet, mm."""
        return self.surface_sheet.thickness_mm

    @staticmethod
    def _dims(nominal: str) -> tuple[float, float]:
        """Return the (thickness, width) of a nominal size, mm."""
        t, w = actual_dimensions_mm(nominal)
        return float(t.magnitude), float(w.magnitude)

    @property
    def wall_cleat_t(self) -> float:
        """Thickness of a wall cleat — how far it stands off the studs, mm."""
        return self._dims(self.wall_cleat_nominal)[0]

    @property
    def wall_cleat_w(self) -> float:
        """Face width of a wall cleat — its height on the wall, mm."""
        return self._dims(self.wall_cleat_nominal)[1]

    @property
    def stile_t(self) -> float:
        """Thickness of every frame member — the frame's across-bench width, mm."""
        return self._dims(self.frame_nominal)[0]

    @property
    def stile_w(self) -> float:
        """Face width of every frame member, mm — a stile's depth, an arm's height."""
        return self._dims(self.frame_nominal)[1]

    @property
    def runner_t(self) -> float:
        """How far a runner stands out from the frame face, mm."""
        return self._dims(self.runner_nominal)[0]

    @property
    def runner_h(self) -> float:
        """Height of a runner on the frame face, mm."""
        return self._dims(self.runner_nominal)[1]

    @property
    def apron_t(self) -> float:
        """Thickness of the front apron, mm."""
        return self._dims(self.apron_nominal)[0]

    @property
    def apron_w(self) -> float:
        """Height of the front apron on edge, mm."""
        return self._dims(self.apron_nominal)[1]

    @property
    def foot_t(self) -> float:
        """Thickness of a foot rail, mm — zero in the hung build."""
        if not self.on_floor:
            return 0.0
        return self._dims(self.foot_nominal)[0]

    @property
    def foot_w(self) -> float:
        """Face width of a foot rail, mm."""
        return self._dims(self.foot_nominal)[1]

    @property
    def stud_t(self) -> float:
        """Thickness of a wall stud, mm — what a lag has to get through."""
        return self._dims(self.stud_nominal)[0]

    @property
    def studs_are_furring(self) -> bool:
        """Whether the "studs" are 3/4" strapping rather than framing."""
        return self.stud_t < inches(1.0)

    # ------------------------------------------------------------------
    # The envelope, most of which the totes decide
    # ------------------------------------------------------------------

    @property
    def overall_w(self) -> float:
        """Width of the top, mm."""
        return inches(self.overall_w_in)

    @property
    def derived_overall_d(self) -> float:
        """Depth the longest tote requires, mm.

        The cleat, the gap behind the tote, the tote, the apron in front of
        it, and the front overhang the top needs for a clamp.
        """
        return (
            self.wall_cleat_t
            + inches(self.bin_back_clearance_in)
            + inches(self.longest.length_in)
            + self.apron_t
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
        """Total thickness of the top, plywood plus sacrificial, mm."""
        return self.top_layers * self.panel_t + self.surface_t

    @property
    def structural_top_t(self) -> float:
        """Thickness of the glued-up plywood slab alone, mm."""
        return self.top_layers * self.panel_t

    @property
    def frame_w(self) -> float:
        """Width of the frame, end frame to end frame, mm.

        Exactly what the bays need — see :meth:`bay_cell`.
        """
        return (
            sum(self.bay_cell(b) for b in self.bay_bins)
            + self.n_frames * self.stile_t
        )

    @property
    def frame_x0(self) -> float:
        """X of the frame's left end, mm — the top overhangs it equally."""
        return (self.overall_w - self.frame_w) / 2

    @property
    def end_overhang(self) -> float:
        """How far the top runs past the frame at each end, mm."""
        return self.frame_x0

    @property
    def frame_d(self) -> float:
        """Depth of the frame from the stud faces to the apron's face, mm."""
        return self.overall_d - inches(self.top_overhang_front_in)

    @property
    def reach_over(self) -> float:
        """How much of the depth is past a comfortable reach, mm."""
        return max(0.0, self.overall_d - inches(COMFORTABLE_REACH_IN))

    # ------------------------------------------------------------------
    # Depths from the wall (positive into the room; world y is minus this)
    # ------------------------------------------------------------------

    @property
    def front_stile_d(self) -> tuple[float, float]:
        """(back face, front face) of a front stile, mm from the studs."""
        front = self.frame_d - self.apron_t
        return (front - self.stile_w, front)

    @property
    def arm_len(self) -> float:
        """Length of an arm — the studs to the apron, mm."""
        return self.frame_d - self.apron_t

    @property
    def runner_len(self) -> float:
        """Length of a runner — the cleats' face to the apron, mm."""
        return self.frame_d - self.apron_t - self.wall_cleat_t

    @property
    def tote_run(self) -> float:
        """Depth a tote has, between the cleats and the apron's back face, mm."""
        return self.runner_len

    @property
    def brace_run(self) -> float:
        """Clear depth between a frame's two stiles, mm."""
        return self.front_stile_d[0] - self.stile_w

    # ------------------------------------------------------------------
    # Heights off the slab
    # ------------------------------------------------------------------

    @property
    def top_underside_z(self) -> float:
        """Underside of the top, and the top of every stile, mm off the slab."""
        return self.top_height - self.top_t

    @property
    def arm_bottom_z(self) -> float:
        """Underside of the arms, mm — where they bear on the top cleat."""
        return self.top_underside_z - self.stile_w

    @property
    def rack_top_z(self) -> float:
        """Ceiling a tote has to clear on its way out, mm.

        The apron's underside: nothing else spans a bay below the top.
        """
        return self.top_underside_z - max(self.stile_w, self.apron_w)

    def tiers_for(self, bin_: Bin) -> int:
        """Tiers stacked in a bay of this tote.

        Parameters
        ----------
        bin_ : Bin
            The tote.

        Returns
        -------
        int
            From ``tier_counts``, validated in ``__post_init__``.
        """
        return self.tier_counts[bin_.key]

    def _tight_tier_pitch(self, bin_: Bin) -> float:
        """Least vertical pitch one tier of this tote needs, mm.

        The tote and the bare head clearance.  The runner sits beside the
        tote's body, under its lip, and costs no height.

        Parameters
        ----------
        bin_ : Bin
            The tote.

        Returns
        -------
        float
            The pitch this tote would use if the rack were sized to it alone.
        """
        return inches(bin_.height_in) + inches(self.bin_head_clearance_in)

    @property
    def _driving_bin(self) -> Bin:
        """The tote whose tiers need the most rack height."""
        return max(
            dict.fromkeys(self.bay_bins),
            key=lambda b: self.tiers_for(b) * self._tight_tier_pitch(b),
        )

    @property
    def rack_h(self) -> float:
        """Total height of the rack, mm.

        The largest of every tote type's own tight requirement at its own
        tier count — the frames run the full height, so every bay shares it.
        """
        driver = self._driving_bin
        return self.tiers_for(driver) * self._tight_tier_pitch(driver)

    def tier_pitch_for(self, bin_: Bin) -> float:
        """Vertical pitch of this tote's own tiers, mm.

        Parameters
        ----------
        bin_ : Bin
            The tote.

        Returns
        -------
        float
            ``rack_h`` divided evenly among this tote's tiers.
        """
        return self.rack_h / self.tiers_for(bin_)

    def head_clearance(self, bin_: Bin) -> float:
        """Clear space above one tote in its own tier, mm.

        Parameters
        ----------
        bin_ : Bin
            The tote.

        Returns
        -------
        float
            The bare minimum for whichever tote set ``rack_h``, more for the
            other.
        """
        return self.tier_pitch_for(bin_) - inches(bin_.height_in)

    @property
    def rack_bottom_z(self) -> float:
        """Underside of the lowest tote, mm off the slab.

        In the hung build it is also the foot of every stile and the lowest
        point on the bench.
        """
        return self.rack_top_z - self.rack_h

    @property
    def frame_bottom_z(self) -> float:
        """Foot of every stile, mm off the slab."""
        return self.foot_t if self.on_floor else self.rack_bottom_z

    @property
    def stile_h(self) -> float:
        """Length of a stile, mm."""
        return self.top_underside_z - self.frame_bottom_z

    @property
    def top_cleat_z(self) -> tuple[float, float]:
        """(bottom, top) of the top wall cleat, mm — the arms bear on its top."""
        return (self.arm_bottom_z - self.wall_cleat_w, self.arm_bottom_z)

    @property
    def bottom_cleat_z(self) -> tuple[float, float]:
        """(bottom, top) of the bottom wall cleat, mm.

        Flush with the bottom of the rack, which makes the bracket as deep as
        the rack allows.
        """
        return (self.rack_bottom_z, self.rack_bottom_z + self.wall_cleat_w)

    @property
    def bracket_depth(self) -> float:
        """Lever arm of the wall connection, mm.

        Centroid to centroid of the two cleats.
        """
        return sum(self.top_cleat_z) / 2 - sum(self.bottom_cleat_z) / 2

    def tote_z(self, bay: int, tier: int) -> tuple[float, float]:
        """(bottom, top) of one tote, mm off the slab.

        Parameters
        ----------
        bay : int
            Bay index — which tote, and therefore which pitch, is in play.
        tier : int
            Tier index within that bay, 0 at the top.

        Returns
        -------
        tuple of float
            The tote's base and its lid.
        """
        bin_ = self.bay_bins[bay]
        top = (
            self.rack_top_z
            - tier * self.tier_pitch_for(bin_)
            - self.head_clearance(bin_)
        )
        return (top - inches(bin_.height_in), top)

    def runner_z(self, bay: int, tier: int) -> tuple[float, float]:
        """(bottom, top) of the runners one tote hangs on, mm off the slab.

        Parameters
        ----------
        bay : int
            Bay index.
        tier : int
            Tier index, 0 at the top.

        Returns
        -------
        tuple of float
            The runner's top is the underside of the tote's lip.
        """
        top = self.tote_z(bay, tier)[1] - inches(self.bay_bins[bay].lip_drop_in)
        return (top - self.runner_h, top)

    # ------------------------------------------------------------------
    # Positions across the bench
    # ------------------------------------------------------------------

    def frame_x(self, i: int) -> float:
        """X of side frame *i*'s centre plane, mm from the left end of the top.

        Parameters
        ----------
        i : int
            Frame index, 0 at the left end.

        Returns
        -------
        float
            Centre of the frame in assembly coordinates.
        """
        x = self.frame_x0 + self.stile_t / 2
        for bay in range(i):
            x += self.bay_clear_w(bay) + self.stile_t
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
            Midway between its two frames.
        """
        return (self.frame_x(bay) + self.frame_x(bay + 1)) / 2

    @property
    def stud_positions(self) -> list[float]:
        """X of every stud centre the cleats cross, mm from the left of the top.

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
        return max(0.0, inches(self.lag_length_in) - self.wall_cleat_t - tip)

    # ------------------------------------------------------------------
    # Assembly
    # ------------------------------------------------------------------

    def build(self) -> Compound:
        """Build the bench as a positioned build123d assembly.

        ``x`` runs along the wall from the left end of the top, ``y`` runs
        from the room toward the wall with ``y = 0`` at the face of the
        studs, and ``z`` is height off the slab — so the whole bench sits at
        negative ``y``, and in the hung build nothing touches ``z = 0``.

        Returns
        -------
        build123d.Compound
            Top, cleats, side frames, runners, apron and — in the legged
            build — the foot rails, positioned.
        """
        children: list[object] = []
        mid_x = self.frame_x0 + self.frame_w / 2

        for i in range(self.top_layers):
            z = self.top_underside_z + self.panel_t * (i + 0.5)
            children.append(
                Pos(self.overall_w / 2, -self.overall_d / 2, z) * self._top_skin()
            )
        children.append(
            Pos(
                self.overall_w / 2,
                -self.overall_d / 2,
                self.top_underside_z + self.structural_top_t + self.surface_t / 2,
            )
            * self._top_surface()
        )

        for name, (z0, z1) in (
            ("top_cleat", self.top_cleat_z),
            ("bottom_cleat", self.bottom_cleat_z),
        ):
            children.append(
                Pos(mid_x, -self.wall_cleat_t / 2, (z0 + z1) / 2)
                * _ON_EDGE
                * self._wall_cleat(name)
            )

        for i in range(self.n_frames):
            children.extend(self._side_frame(i))

        children.extend(self._runners())

        children.append(
            Pos(
                mid_x,
                -(self.frame_d - self.apron_t / 2),
                self.top_underside_z - self.apron_w / 2,
            )
            * _ON_EDGE
            * self._apron()
        )

        if self.on_floor:
            for d in (self.stile_w / 2, sum(self.front_stile_d) / 2):
                children.append(Pos(mid_x, -d, self.foot_t / 2) * self._foot_rail())

        return Compound(children=children, label=f"basement_bench_{self.mount}")

    def _side_frame(self, i: int) -> list[object]:
        """Return the members of side frame *i*, positioned and jointed.

        Both stiles run from the foot to the underside of the top; the arm
        runs from the studs to the front stile's face at the top, and is
        half-lapped to each stile where they cross.  The back stile is
        notched over both cleats.  In the hung build a brace runs corner to
        corner between the stiles, from the foot of the back stile to the
        underside of the arm at the front.

        Parameters
        ----------
        i : int
            Frame index.

        Returns
        -------
        list
            Placed :class:`~woodshop.parts.Board` members.
        """
        x = self.frame_x(i)
        half = self.stile_t / 2
        ov = _CUTTER_OVERRUN_MM
        z_mid = self.frame_bottom_z + self.stile_h / 2
        top = self.top_underside_z
        arm_z0 = self.arm_bottom_z
        fs0, fs1 = self.front_stile_d

        back = self._frame_member("back_stile", self.stile_h)
        front = self._frame_member("front_stile", self.stile_h)
        arm = self._frame_member("arm", self.arm_len)

        placed_back = Pos(x, -self.stile_w / 2, z_mid) * _UPRIGHT * back
        placed_front = Pos(x, -(fs0 + fs1) / 2, z_mid) * _UPRIGHT * front
        placed_arm = (
            Pos(x, -self.arm_len / 2, top - self.stile_w / 2) * _FRONT_TO_BACK * arm
        )

        # Half-laps at both top corners: the arm keeps the +x half, the
        # stiles the -x half, so the corner is one thickness of wood.
        arm_cuts = [
            _box(x - ov - half, x, -self.stile_w, ov, arm_z0 - ov, top + ov),
            _box(x - ov - half, x, -fs1 - ov, -fs0, arm_z0 - ov, top + ov),
        ]
        back_cuts = [
            _box(x, x + half + ov, -self.stile_w, ov, arm_z0, top + ov),
            _box(
                x - half - ov,
                x + half + ov,
                -self.wall_cleat_t,
                ov,
                *self.top_cleat_z,
            ),
            self._bottom_cleat_notch(x),
        ]
        front_cuts = [_box(x, x + half + ov, -fs1 - ov, -fs0, arm_z0, top + ov)]

        members = [
            _cut(placed_back, back, back_cuts),
            _cut(placed_front, front, front_cuts),
            _cut(placed_arm, arm, arm_cuts),
        ]
        if not self.on_floor:
            members.append(self._brace(x))
        return members

    def _bottom_cleat_notch(self, x: float) -> Box:
        """Return the cutter that seats a back stile over the bottom cleat.

        It opens through the stile's foot in the hung build, where the cleat
        sits flush with the bottom of the rack.

        Parameters
        ----------
        x : float
            The frame's centre plane.

        Returns
        -------
        build123d.Box
            A positioned cutter.
        """
        ov = _CUTTER_OVERRUN_MM
        z0, z1 = self.bottom_cleat_z
        if z0 <= self.frame_bottom_z + 0.01:
            z0 -= ov
        half = self.stile_t / 2
        return _box(x - half - ov, x + half + ov, -self.wall_cleat_t, ov, z0, z1)

    @property
    def brace_len(self) -> float:
        """Long-point length of a brace, mm — corner to corner between stiles."""
        rise = self.arm_bottom_z - self.frame_bottom_z
        return math.hypot(self.brace_run, rise)

    def _brace(self, x: float):
        """Return one frame's brace, positioned and trimmed to fit.

        Cut from a blank :attr:`brace_len` long, laid on the diagonal between
        the stiles, and trimmed square to the back stile's face at its foot
        and to the front stile and the arm at its head.

        Parameters
        ----------
        x : float
            The frame's centre plane.

        Returns
        -------
        build123d.Shape
            The trimmed brace, carrying its blank's cut-list metadata.
        """
        rise = self.arm_bottom_z - self.frame_bottom_z
        brace = self._frame_member("brace", self.brace_len)
        angle = math.degrees(math.atan2(rise, -self.brace_run))
        d_mid = self.stile_w + self.brace_run / 2
        z_mid = self.frame_bottom_z + rise / 2
        placed = (
            Pos(x, -d_mid, z_mid) * Rotation(angle, 0, 0) * _FRONT_TO_BACK * brace
        )
        half = self.stile_t / 2
        ov = _CUTTER_OVERRUN_MM
        window = _box(
            x - half - ov,
            x + half + ov,
            -self.front_stile_d[0],
            -self.stile_w,
            self.frame_bottom_z,
            self.arm_bottom_z,
        )
        return retag(placed & window, like=brace)

    def _runners(self) -> list[object]:
        """Return every runner, positioned on its frame face.

        Two per bay per tier, one on the inside face of each of the bay's
        frames, lapped onto both stiles.  Bays in ``open_bays`` get none.

        Returns
        -------
        list
            Placed :class:`~woodshop.parts.Board` runners.
        """
        placed: list[object] = []
        open_bays = set(self.open_bays)
        cy = -(self.wall_cleat_t + self.runner_len / 2)
        offset = self.stile_t / 2 + self.runner_t / 2
        for bay, bin_ in enumerate(self.bay_bins):
            if bay in open_bays:
                continue
            for tier in range(self.tiers_for(bin_)):
                z0, z1 = self.runner_z(bay, tier)
                for x in (self.frame_x(bay) + offset, self.frame_x(bay + 1) - offset):
                    placed.append(
                        Pos(x, cy, (z0 + z1) / 2) * _FRONT_TO_BACK * self._runner()
                    )
        return placed

    def _frame_member(self, label: str, length_mm: float) -> Board:
        """Return one 2x4 frame member.

        Parameters
        ----------
        label : str
            ``"back_stile"``, ``"front_stile"``, ``"arm"`` or ``"brace"``.
        length_mm : float
            Length of the blank.

        Returns
        -------
        Board
            The member, with its joinery in its notes.
        """
        notes = {
            "back_stile": (
                "against the wall; notched over both cleats — the top notch "
                "is closed above, so the stile hangs on the cleat — and "
                f"screwed to each with {self.stile_screws_per_cleat} #10 x "
                "3-1/2\" structural screws; half-lapped to the arm at the top"
            ),
            "front_stile": (
                "at the front, full height; half-lapped to the arm, glued and "
                "screwed, and hangs from it — the runners' front ends land "
                "on it"
            ),
            "arm": (
                "on edge under the top, studs to apron; bears on the top "
                "cleat's top edge, half-lapped to both stiles, and carries "
                "the frame's pull back to the wall in tension. The top screws "
                "down into it"
            ),
            "brace": (
                "corner to corner between the stiles, long point to long "
                "point; butts the back stile at its foot and the arm and "
                "front stile at its head, in compression, toe-screwed"
            ),
        }[label]
        return Board(
            length_mm=length_mm,
            nominal=self.frame_nominal,
            material=self.frame_species,
            label=label,
            notes=notes,
        )

    def _top_skin(self) -> Panel:
        """Return one plywood layer of the top."""
        return Panel(
            length_mm=self.overall_w,
            width_mm=self.overall_d,
            material=self.panel_material,
            nominal_thickness=self.panel_nominal_thickness,
            label="top_skin",
            grain_direction="length",
            notes=(
                f"{self.top_layers} layers glued to each other into one slab "
                f"{mm_to_fractional_inch(self.structural_top_t, 32)} thick, "
                "then screwed down into the arms and the apron — never glued "
                "to them, so the slab comes off in one piece"
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

    def _wall_cleat(self, name: str) -> Board:
        """Return one wall cleat.

        Parameters
        ----------
        name : str
            ``"top_cleat"`` or ``"bottom_cleat"`` — the same board, kept
            apart on the cut list because they do different structural jobs.

        Returns
        -------
        Board
            The cleat, with its fixing schedule in its notes.
        """
        if name == "top_cleat":
            note = (
                f"flat against the studs, lagged to {len(self.stud_positions)} "
                f"of them, {self.lags_per_stud} lags per stud, {self.lag_label}; "
                "the back stiles hang on it and screw into it, and the arms "
                "bear on its top edge — this is the tension connection"
            )
        else:
            note = (
                "flat against the studs, lagged to the same studs; the back "
                "stiles seat against its face and screw into it — the "
                "braces' thrust arrives here, in compression"
            )
        return Board(
            length_mm=self.frame_w,
            nominal=self.wall_cleat_nominal,
            material=self.frame_species,
            label=name,
            notes=note,
        )

    def _runner(self) -> Board:
        """Return one runner — what a tote's lip rides on."""
        return Board(
            length_mm=self.runner_len,
            nominal=self.runner_nominal,
            material=self.frame_species,
            label="runner",
            notes=(
                "screwed flat to the frame's inside face, lapped onto both "
                "stiles and the brace where it crosses; a tote's lip rides on "
                "its top edge"
            ),
        )

    def _apron(self) -> Board:
        """Return the front apron.

        On edge across the front faces of the front stiles and the ends of
        the arms: it ties the frames together at the front and gives the
        top's front edge something to screw down into.
        """
        return Board(
            length_mm=self.frame_w,
            nominal=self.apron_nominal,
            material=self.frame_species,
            label="front_apron",
            notes=(
                "on edge across the front stiles and arm ends; the top screws "
                "down into it, and the totes slide out beneath it"
            ),
        )

    def _foot_rail(self) -> Board:
        """Return one foot rail — the legged build only.

        Laid flat under every stile, front and back.  It is the part that
        meets the slab, so it is the part that gets wet: plan on replacing
        it, keep it off the concrete on plastic shims or levellers, and do
        not glue the stiles to it.
        """
        return Board(
            length_mm=self.frame_w,
            nominal=self.foot_nominal,
            material=self.frame_species,
            label="foot_rail",
            notes=(
                "laid flat under the stiles; screwed, never glued — it is "
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
        different lengths and each sits with its front against the apron.

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
        tote_front = self.frame_d - self.apron_t
        for bay, bin_ in enumerate(self.bay_bins):
            if bay in open_bays:
                continue
            mass = self.bin_mass_kg * self.tiers_for(bin_)
            tote_mass += mass
            tote_moment += mass * (tote_front - inches(bin_.length_in) / 2)
        tote_arm = tote_moment / tote_mass if tote_mass else 0.0

        return [
            ("the top itself", top_mass, self.overall_d / 2),
            ("frames and runners", frame_mass, self.frame_d / 2),
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

    @property
    def worst_frame_share(self) -> float:
        """Fraction of the bench's width the most-loaded frame carries.

        Half of each bay beside it, plus its own thickness.
        """
        shares = []
        for i in range(self.n_frames):
            trib = self.stile_t
            if i > 0:
                trib += self.bay_clear_w(i - 1) / 2
            if i < self.derived_n_bays:
                trib += self.bay_clear_w(i) / 2
            shares.append(trib / self.frame_w)
        return max(shares)

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
        """Report where the bench's size came from and what it costs.

        Returns
        -------
        list[Finding]
            The derivation of the depth, the reach it buys past, the end
            overhang the width leaves, and the sheet of plywood it spends.
        """
        longest = self.longest
        findings = [
            Finding(
                Severity.INFO,
                "envelope",
                f"the depth is the tote's, not a choice: a "
                f"{mm_to_fractional_inch(self.wall_cleat_t)} cleat, "
                f"{mm_to_fractional_inch(inches(self.bin_back_clearance_in))} "
                f"of gap, a {longest.label} tote "
                f"{mm_to_fractional_inch(inches(longest.length_in))} long, a "
                f"{mm_to_fractional_inch(self.apron_t)} apron and "
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
        if self.end_overhang > inches(_MAX_END_OVERHANG_IN):
            findings.append(
                Finding(
                    Severity.WARN,
                    "envelope",
                    f"the bays need {mm_to_fractional_inch(self.frame_w)} of "
                    f"frame, so the top overhangs each end by "
                    f"{mm_to_fractional_inch(self.end_overhang)} — narrow the "
                    "top or add a bay",
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
                    "cleat — there is nothing to lag to",
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
                f'{n} studs at {self.stud_spacing_in:g}" o.c. behind a '
                f"{mm_to_fractional_inch(self.frame_w)} cleat, "
                f"{self.lags_per_stud} lags each: "
                f"{mm_to_fractional_inch(left)} of cleat past the left lag "
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
                    f"{mm_to_fractional_inch(self.wall_cleat_t)} cleat reaches "
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

        clash = inches(self.lag_diameter_in) + self.stile_t / 2
        for x in studs:
            nearest = min((abs(x - self.frame_x(i)), i) for i in range(self.n_frames))
            if nearest[0] < clash:
                findings.append(
                    Finding(
                        Severity.WARN,
                        "wall",
                        f"the lag at {mm_to_fractional_inch(x)} lands behind "
                        f"frame {nearest[1]}'s back stile, which is notched "
                        "over the cleat: counterbore that lag head and its "
                        "washer flush, or the stile will not seat",
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
                f"{self.n_frames} {'' if self.on_floor else 'braced '}side "
                "frames are the bracket: "
                f"{mm_to_fractional_inch(self.bracket_depth)} between the two "
                f"cleats' centroids, so "
                f"{m_nmm / (25.4 * N_PER_LBF):.0f} lb-in of overturning "
                f"becomes {t_lb:.0f} lb pulling the top cleat off the wall "
                f"and the same pushing the bottom one into it",
            )
        )

        if self.on_floor:
            findings.append(
                Finding(
                    Severity.INFO,
                    "wall",
                    "the legged build puts every stile on a foot rail, so "
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
                    f"the top cleat's {n_lags} lags",
                    shear_cap / shear_demand_lb if shear_demand_lb > 0 else math.inf,
                    remedy=(
                        f"lags_per_stud={self.lags_per_stud + 1} would make it "
                        f"{v_lb / (len(studs) * (self.lags_per_stud + 1)):.0f} lb "
                        "each"
                    ),
                )
            )

        n_screws = self.n_frames * self.stile_screws_per_cleat
        screw_pen_in = (self.wall_cleat_t - inches(SCREW_DIAMETER_IN)) / IN
        screw_cap = n_screws * screw_withdrawal_lb_per_in() * screw_pen_in
        findings.append(
            self._margin(
                "joint",
                f"the back stiles into the top cleat: {t_lb:.0f} lb of pull "
                f"across {n_screws} #10 screws in withdrawal, "
                f"{screw_cap:.0f} lb between them",
                screw_cap / t_lb if t_lb > 0 else math.inf,
                remedy=(
                    f"stile_screws_per_cleat={self.stile_screws_per_cleat + 2}"
                ),
            )
        )

        bearing_mm2 = self.n_frames * self.stile_t * self.wall_cleat_w
        bearing_mpa = (m_nmm / self.bracket_depth) / bearing_mm2
        findings.append(
            self._margin(
                "joint",
                "the back stiles' feet bearing on the bottom cleat: "
                f"{bearing_mpa:.2f} MPa ({bearing_mpa * 145.0:.0f} psi) over "
                f"{self.n_frames} notches, against {_FC_PERP_PSI:.0f} psi "
                "perpendicular to grain",
                _FC_PERP_PSI / (bearing_mpa * 145.0) if bearing_mpa > 0 else math.inf,
            )
        )

        if not self.on_floor:
            findings.append(self._brace_finding(m_nmm))

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

    def _brace_finding(self, moment_nmm: float) -> Finding:
        """Check the most-loaded frame's brace against buckling.

        The frame is a triangle: the arm pulls the top back to the wall, the
        brace pushes its foot into the wall, and the rise between them turns
        the frame's share of the overturning moment into that pull.  The
        brace's horizontal component matches the arm's pull.  Euler buckling
        about the brace's weak axis, over its whole length — the runners
        screwed across it brace it at every tier, which this ignores.

        Parameters
        ----------
        moment_nmm : float
            The whole bench's overturning moment.

        Returns
        -------
        Finding
            The brace force against its buckling load.
        """
        rise = self.arm_bottom_z - self.frame_bottom_z
        pull_n = moment_nmm * self.worst_frame_share / rise
        thrust_n = pull_n * self.brace_len / self.brace_run
        e_mpa = ELASTIC_MODULUS_MPA[self.frame_species]
        i_mm4 = self.stile_w * self.stile_t**3 / 12.0
        p_cr_n = math.pi**2 * e_mpa * i_mm4 / self.brace_len**2
        return self._margin(
            "bracket",
            f"the busiest frame's brace: {pounds_force(thrust_n):.0f} lb of "
            f"thrust along {mm_to_fractional_inch(self.brace_len)} of "
            f"{self.frame_nominal}, against {pounds_force(p_cr_n):.0f} lb to "
            "buckle it unbraced",
            p_cr_n / thrust_n if thrust_n > 0 else math.inf,
        )

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
            The grid the totes produced, the rim clearance, the lip bearing,
            the tier pitches, and the gap under it all.
        """
        open_bays = set(self.open_bays)
        tally = ", ".join(f"{n} x {label}" for label, n in self.bin_tally.items())
        gallons = sum(
            bin_.gallons * self.tiers_for(bin_)
            for bay, bin_ in enumerate(self.bay_bins)
            if bay not in open_bays
        )
        tiers_label = "/".join(
            f"{self.tiers_for(b)} {b.label}" for b in dict.fromkeys(self.bay_bins)
        )
        findings: list[Finding] = [
            Finding(
                Severity.INFO,
                "rack",
                f"{self.derived_n_bays} bays ({tiers_label} tiers each) = "
                f"{self.n_bins} totes ({tally}), {self.rack_load_kg:.0f} kg "
                f"full, about {gallons:.0f} gallons of project stock",
            )
        ]

        wide, narrow = self.widest, self.narrowest
        if wide is not narrow and self.bay_layout is not None:
            packed = replace(self, bay_layout=None).bay_bins
            if set(packed) == {wide, narrow}:
                packed_note = "packed automatically, this width lands on a mix too"
            elif len(set(packed)) == 1:
                packed_note = (
                    f"packed automatically, this width gives every bay to "
                    f"the {packed[0].label} tote instead"
                )
            else:
                packed_note = (
                    f"packed automatically, this width gives "
                    f"{len(packed)} bays instead of {self.derived_n_bays}"
                )
            findings.append(
                Finding(
                    Severity.INFO,
                    "rack",
                    f"bay_layout reserves {self.bay_layout.count(wide.key)} "
                    f"bay(s) for the {wide.label} tote and "
                    f"{self.bay_layout.count(narrow.key)} for the "
                    f"{narrow.label} regardless of what the packer would "
                    f"choose — {packed_note}",
                )
            )

        for bay, bin_ in enumerate(self.bay_bins):
            if bay in open_bays:
                continue
            findings.extend(
                check_clearance(
                    f"bay {bay} ({bin_.label}, "
                    f"{mm_to_fractional_inch(self.bay_clear_w(bay))} clear), "
                    "each side of the tote's rim",
                    inches(self.bin_side_clearance_in),
                    inches(0.25),
                    inches(0.5),
                    tight_note=(
                        "a tote is floppy plastic and goes in crooked; under a "
                        "quarter inch it binds"
                    ),
                    loose_note=(
                        "every bit of clearance past the runner comes off the "
                        "lip's bearing"
                    ),
                )
            )

        for bin_ in dict.fromkeys(
            b for bay, b in enumerate(self.bay_bins) if bay not in open_bays
        ):
            bearing = self.lip_bearing(bin_)
            severity = Severity.INFO if bearing >= inches(0.25) else Severity.WARN
            message = (
                f"{bin_.label} bays: {self.runner_nominal} runners reach "
                f"{mm_to_fractional_inch(self.runner_t)} past the frame, so "
                f"the lip bears {mm_to_fractional_inch(bearing)} a side and "
                f"the body clears the runners by "
                f"{mm_to_fractional_inch(self.body_clearance(bin_))}"
            )
            if not bin_.lip_measured:
                message += (
                    f"; the {mm_to_fractional_inch(inches(bin_.lip_in))} lip is "
                    "a published build's figure, not measured on this tote — "
                    "put a tape on it before screwing a runner on"
                )
            findings.append(Finding(severity, "rack", message))

        kinds = list(dict.fromkeys(self.bay_bins))
        if len(kinds) > 1:
            pitches = ", ".join(
                f"{b.label} {mm_to_fractional_inch(self.tier_pitch_for(b))} "
                f"with {mm_to_fractional_inch(self.head_clearance(b))} over the lid"
                for b in kinds
            )
            findings.append(
                Finding(
                    Severity.INFO,
                    "rack",
                    f"tiers are pitched per tote — {pitches} — and bays are "
                    "sized to their own rim, so a tote only goes in a bay of "
                    "its own kind",
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

        behind = self.tote_run - inches(self.longest.length_in)
        findings.append(
            Finding(
                Severity.INFO,
                "rack",
                f"a {self.longest.label} tote rides "
                f"{mm_to_fractional_inch(self.runner_len)} runners with "
                f"{mm_to_fractional_inch(behind)} between its back and the "
                "cleat, and slides out under the apron",
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
            cost = sum(self.tiers_for(self.bay_bins[b]) for b in open_bays)
            findings.append(
                Finding(
                    Severity.INFO,
                    "rack",
                    f"bay(s) {sorted(open_bays)} left open at the cost of "
                    f"{cost} totes",
                )
            )
        return findings

    def _stiffness_findings(self) -> list[Finding]:
        """Report what actually moves when the bench is loaded.

        Returns
        -------
        list[Finding]
            The top between two arms, a runner between its stiles, and one
            honest disclaimer.
        """
        findings: list[Finding] = []
        widest_bay = max(range(self.derived_n_bays), key=self.bay_clear_w)
        findings.extend(
            check_shelf_deflection(
                self.panel_material,
                span_mm=self.bay_clear_w(widest_bay),
                depth_mm=self.overall_d,
                thickness_mm=self.structural_top_t,
                load_kg=self.front_edge_load_kg,
                label=(
                    f"the top between two arms, {self.front_edge_load_kg:.0f} "
                    "kg over one bay"
                ),
                run_mm=self.frame_w,
            )
        )
        findings.extend(
            check_shelf_deflection(
                self.frame_species,
                span_mm=self.brace_run,
                depth_mm=self.runner_t,
                thickness_mm=self.runner_h,
                load_kg=self.bin_mass_kg,
                label=(
                    f"a runner between its stiles, {self.runner_nominal} on its "
                    f"face, carrying a whole {self.bin_mass_kg:.0f} kg tote as "
                    "if the other side carried none"
                ),
                limit_ratio=240.0,
            )
        )
        findings.append(
            Finding(
                Severity.WARN,
                "deflection",
                "the wall joint is also still what moves under real use — lag "
                "slip, the cleat crushing into the studs, and the studs "
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
            Moisture, what is inside a stud bay, and the obvious additions
            the geometry is already ready for.
        """
        findings = [
            Finding(
                Severity.WARN,
                "site",
                "before any lag goes in, find out what is in those stud bays. "
                "An exposed basement wall is where the wiring, the water line "
                f"and the old phone cable run, and a {self.lag_len_label} lag "
                f"reaches {mm_to_fractional_inch(self.lag_penetration)} into "
                "the stud — but a drill bit wandering off a stud edge reaches "
                "whatever is behind it",
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
                "the top overhangs the apron by "
                f"{mm_to_fractional_inch(inches(self.top_overhang_front_in))} "
                "and each end by "
                f"{mm_to_fractional_inch(self.end_overhang)} — that reveal is "
                "what a clamp jaw needs. A face vice at the left end wants a "
                "block between the apron and the end frame behind it; "
                "nothing else in the design has to change",
            )
        )
        findings.append(
            Finding(
                Severity.INFO,
                "site",
                "the top is screwed down, not glued: back the screws out of "
                "the arms and the apron and the slab lifts off whole, with "
                "every frame, runner and tote left exactly where it was",
            )
        )
        return findings


def _cut(placed, blank: Board, cutters: list) -> object:
    """Subtract *cutters* from a placed member and keep its cut-list identity.

    Parameters
    ----------
    placed : build123d.Shape
        The member, already positioned.
    blank : Board
        The unplaced board it was made from, whose metadata the result keeps.
    cutters : list of build123d.Shape
        Positioned cutters.

    Returns
    -------
    build123d.Shape
        The jointed member.
    """
    result = placed
    for cutter in cutters:
        result = result - cutter
    return retag(result, like=blank)


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
            f'{bench.top_height_in:g}" top on two cleats lagged to '
            f"{len(bench.stud_positions)} exposed studs at "
            f'{bench.stud_spacing_in:g}" o.c. Underneath, '
            f"{bench.derived_n_bays} bays of medium storage totes ({tally}) "
            f"hung by their rims between 2x4 side frames — no plywood "
            f"below the top. {bench.spec.summary.capitalize()}."
        ),
        species=bench.frame_species,
        build=bench.build,
        check=bench.check,
        inventory=bench.inventory,
        notes=(
            "Every bay boundary is a side frame of 2x4s — back stile, front "
            "stile, an arm under the top and a diagonal brace — hooked over "
            "a 2x6 cleat lagged to the studs at the top and seated against a "
            "second at the bottom, so the frames are the bracket and the "
            "check report works the load path into pounds. Totes hang by "
            "their lips from 1x4 runners screwed to the frame faces, which "
            "costs no height per tier and leaves nothing spanning a bay for "
            "a tote below to hit on its way in. The top is screwed down to "
            "the arms and apron, never glued, so it can be replaced. Two "
            "bays are dedicated to each tote size, three tiers of the "
            "16-gallon and two of the 17-gallon, both decisions rather than "
            "whatever an automatic packer would land on. The lip dimensions "
            "come from a published tote-rack build, not a measurement; the "
            "other assumption the model cannot verify is that the exposed "
            "studs are framing and not furring strips on masonry — set "
            "stud_nominal to what is actually there."
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
    parser.add_argument(
        "--bay",
        dest="bay_layout",
        action="append",
        choices=sorted(BIN_TYPES),
        default=None,
        help=(
            "tote for the next bay, left to right; repeatable. Defaults to "
            f"{DEFAULT_BAY_LAYOUT} — two dedicated bays each. Pass "
            "--auto-bays to pack automatically instead"
        ),
    )
    parser.add_argument(
        "--auto-bays",
        action="store_true",
        help="pack bays automatically instead of the two-dedicated-bays default",
    )
    parser.add_argument("--width", type=float, default=90.0)
    parser.add_argument(
        "--depth",
        type=float,
        default=None,
        help="overall depth; omit to derive it from the longest tote",
    )
    parser.add_argument("--height", type=float, default=40.0)
    parser.add_argument(
        "--tier-count",
        dest="tier_counts",
        action="append",
        metavar="KEY=N",
        default=[],
        help=(
            "tiers for one tote type, e.g. 16gal=3; repeatable. Defaults to "
            f"{DEFAULT_TIER_COUNTS}"
        ),
    )
    parser.add_argument("--stud-spacing", type=float, default=16.0)
    parser.add_argument(
        "--open-bay",
        type=int,
        action="append",
        default=[],
        help="leave this bay without runners; repeatable",
    )
    parser.add_argument("--outdir", type=Path, default=Path("build"))
    args = parser.parse_args()

    mounts = sorted(MOUNTS) if args.mount == "both" else [args.mount]
    bins = tuple(args.bins) if args.bins else ("17gal", "16gal")
    if args.auto_bays:
        bay_layout = None
    elif args.bay_layout is not None:
        bay_layout = tuple(args.bay_layout)
    else:
        bay_layout = DEFAULT_BAY_LAYOUT
    tier_counts = dict(DEFAULT_TIER_COUNTS)
    for pair in args.tier_counts:
        key, _, value = pair.partition("=")
        tier_counts[key] = int(value)
    for mount in mounts:
        run(
            BasementBench(
                mount=mount,
                bins=bins,
                bay_layout=bay_layout,
                overall_w_in=args.width,
                overall_d_in=args.depth,
                top_height_in=args.height,
                tier_counts=tier_counts,
                stud_spacing_in=args.stud_spacing,
                open_bays=tuple(args.open_bay),
            ),
            args.outdir,
        )


if __name__ == "__main__":
    main()
