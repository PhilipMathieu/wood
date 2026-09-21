"""Basement wall bench — 80" of bench hung on exposed studs, bins underneath.

The brief, as given::

    A workbench roughly 80" wide, to be mounted to exposed studs in the
    basement, with racks for project source storage bins underneath.

Three phrases in that sentence decide almost everything, and it is worth
separating them before any lumber is chosen.

**"Roughly 80 inches"** is the only soft number, and softness is useful: the
bench is as wide as its ledgers, the ledgers are as long as the studs they can
reach, and 80" happens to be *five studs at 16" on centre with seven inches of
ledger past the outermost lag at each end* — which is exactly the end distance
a 3/8" lag wants.  A round 80" and a correct lag layout are the same number
here by luck, not by design, and :meth:`BasementBench.stud_positions` recomputes
it the moment the spacing changes.

**"Mounted to exposed studs"** is the structural brief.  It is not a detail of
attachment — it *is* the structure.  There are no legs in the shipped design.
Two ledgers are lagged to the studs, everything else hangs off them, and the
bench is a cantilever whose depth is the distance between those two ledgers.
Which means the interesting question is not "will the lags hold?" but "what is
the bracket, and how deep is it?" — and the answer is the bin rack.  See
*The rack is the bracket*.

**"Racks for project source storage bins"** sets the whole geometry below the
top.  A bin is a rectangle with a size, and a rack is a grid that either fits
it or does not; the bay count, the tier pitch and the height off the floor all
fall out of one bin plus the width the studs allow.

The rack is the bracket
-----------------------
A wall-hung bench rotates about the bottom of whatever holds it: the load is
out in front of the wall, so the top of the bracket is pulled *away* from the
studs and the bottom is pushed *into* them.  Nothing avoids that.  The only
thing a design controls is the **lever arm** — the vertical distance between
the tension at the top and the bearing at the bottom — because the tension
each lag sees is the overturning moment divided by it.

A bench held by a single ledger under its top has a lever arm of a few inches
and needs heroic fasteners.  This one has a lever arm of **21-1/2"**, because
the bin rack's ribs run from the underside of the top down past a second
ledger near the floor, and both ledgers are lagged to the same studs.  The
storage is not hanging off the structure; it *is* the structure, and the check
report prints the moment, the lever arm and the resulting pull on each lag so
the claim can be read rather than believed:

* the ribs are plywood webs 27" deep and 22" long — they are not the flexible
  part of this bench, and the report says so;
* the top's back edge is screwed down into the top ledger along its full
  length, so the tension crosses that joint in **shear** rather than trying to
  pull screws out of a plywood edge;
* the bottom of each rib is notched over the lower ledger, so the thrust at
  the bottom is plain wood-on-wood **bearing** and needs no fastener at all.

What the studs are asked for, and the one thing that invalidates it
-------------------------------------------------------------------
:meth:`BasementBench.check` works both load paths in pounds, because the
withdrawal and shear figures it compares against come from an imperial code
(NDS, and the withdrawal formula ``W = 1800 G**1.5 D**0.75`` lb per inch of
thread penetration at :data:`SPF_SPECIFIC_GRAVITY`).  The numbers are
comfortable in both directions, and the *binding* one is vertical shear rather
than pull-out, which is why :attr:`BasementBench.lags_per_stud` defaults to 2
rather than 1 — one lag per stud passes with a margin of about 1.5, and a
shop bench is the wrong place to run a margin of 1.5.

All of that rests on one assumption the model cannot check and the report
therefore states as loudly as it can: **the exposed studs must be a framed
stud wall, not furring strips on masonry.**  A 1x3 strapping run cut-nailed
to a foundation wall looks exactly like a stud wall with the drywall off, and
a 3-1/2" lag driven into one finds 3/4" of pine and then concrete.  Set
``stud_nominal`` to what is actually there; a 1x entry turns the wall findings
into an ERROR rather than quietly halving the penetration.

Two builds
----------
``hung``
    As briefed, and the default.  Nothing touches the floor — the lowest part
    of the bench is the bottom tier's runners, 3-13/16" up — so the slab can
    be swept under, a wet spring does not reach the plywood, and there is no
    leg to kick or to level on a floor that was never flat.  The wall carries
    all of it.

``legged``
    Every rib runs down to a pair of 2x4 foot rails and the bench stands on
    the floor, with the ledgers reduced to holding it upright.  This is the
    build for a wall that turned out to be furring, for a slab flat enough not
    to care, and for hand work: planing and hammering put cyclic load into a
    connection, and cyclic load is what backs a lag out of a stud over a few
    years.  It costs the swept floor and it costs the feet being the first
    thing to find out that a basement is damp — hence the foot rails, which
    are the sacrificial part and are meant to be replaceable.

What is inferred rather than given
----------------------------------
* **The bin.**  Nobody said which one, so the rack is sized to a *nominal*
  16" x 11" x 7" tote — about 12 quarts — and every one of those three numbers
  is a parameter.  They are plausible, not measured, and the design report
  says which clearances they produce so a real bin can be checked against
  them before anything is cut.  Bins, not cardboard: a basement cycles through
  its dew point several times a year and a cardboard box is a humidity sponge
  with your hardware in it.
* **The bins ride on runners, not shelves.**  Two 3/4" plywood strips per bin,
  screwed to the rib faces, so a bin slides out like a drawer with no drawer
  around it.  A solid shelf under a plastic bin in a basement is a place for
  condensation to sit; a pair of runners is not, and it is also a third of the
  plywood.
* **1-1/8" of slop each side of a bin is deliberate.**  It is what is left of
  a 14-3/4" bay after an 11" bin and its two runners, and it is also how you
  get a hand on the bin to pull it.  A bin that fits its bay exactly is a bin you fight.
* **The top is two layers of 3/4" plywood glued into one 1-7/16" slab, with a
  1/4" sheet screwed down on top of it and not glued.**  The thin sheet is the
  one you saw into, spill epoxy on, and replace; screwing rather than gluing
  it is the whole point of it being there.
* **There is no knee space anywhere.**  The rack fills the full width, so this
  is a bench to stand at.  ``open_bays`` gives a bay back — for a shop vac, a
  bucket, a stool — by leaving its runners out, and the report says when none
  has been.

What the arithmetic decides
---------------------------
Four numbers are published — 80" wide, 24" deep, a 36" top, three tiers — and
the rest is what is left after the plywood has had its say.  3/4" birch ply
measures **23/32"**, so:

* **The top comes out 1-11/16" thick** rather than 1-3/4", which puts the
  joists' underside at 30-13/16" and is where the rack starts.
* **Three tiers at 9" of pitch take 27"**, leaving the rack's bottom runner
  **3-13/16" off the slab**.  That gap is the broom, and it is the first inch
  of a wet basement floor.  A fourth tier does not fit and
  :meth:`BasementBench.__post_init__` says so rather than drawing one
  underground.
* **Five bays, not six.**  Six would give 12-3/16" bays and a 10-3/4" channel
  between runners, which an 11" bin does not enter.  The bay count is derived
  from the bin rather than chosen, which is why it changes when the bin does.

Run it
------
::

    uv run python projects/basement_bench.py
    uv run python projects/basement_bench.py --mount legged --outdir build
    uv run python projects/basement_bench.py --mount both --outdir build

and in a REPL, to ask what a different wall or a different bin gives::

    BasementBench(stud_spacing_in=24.0).stud_positions
    BasementBench(bin_w_in=8.25).derived_n_bays

    furred = BasementBench(stud_nominal="1x3")
    furred.check(furred.build(), extract(furred.build()))   # ERROR, and why
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

#: Newtons per pound-force.  The geometry is metric and the fastener code is
#: not, so the wall checks convert once, here, rather than in six places.
N_PER_LBF: float = 4.4482216

G_M_S2: float = 9.80665

#: Specific gravity of SPF framing lumber, oven-dry volume basis.
#:
#: NDS Table 12.3.3A gives G = 0.42 for Spruce-Pine-Fir, which is what a yard
#: in Maine sells as "whitewood" or "2x4".  Douglas fir-larch is 0.50 and every
#: capacity below scales as G**1.5, so a DF wall is about 30% stronger than
#: this model assumes — the safe direction to be wrong in.
SPF_SPECIFIC_GRAVITY: float = 0.42

#: Reference lateral design value ``Z`` for one 3/8" lag screw in single shear,
#: 1-1/2" side member, into a main member of G = 0.42, lb.
#:
#: Read off NDS Table 12E for the nearest tabulated case rather than computed
#: from the yield-limit equations, and rounded down.  It carries no adjustment
#: factors at all: no load duration (C_D = 1.0, i.e. permanent-ish storage
#: load), no wet service, no temperature.  A basement is not obviously a dry
#: service condition, and if yours runs above 19% moisture content C_M = 0.7
#: applies and every shear margin below drops by a third.
LAG_SHEAR_LB: float = 210.0

#: Reference compression design value perpendicular to grain for SPF, psi.
#:
#: NDS Supplement Table 4A, ``Fc_perp = 425 psi``.  It is what the ribs'
#: notches bear against at the bottom of the bracket, and it is the one place
#: in this bench where wood is loaded across its grain.
_FC_PERP_PSI: float = 425.0

#: Allowable lateral load on one #10 x 3" structural wood screw into SPF, lb.
#:
#: Deliberately conservative — the top-to-ledger screw line has thirteen of
#: them and is nowhere near critical, so there is nothing to buy by sharpening
#: the figure.
SCREW_SHEAR_LB: float = 130.0

#: What one full bin weighs, kg.
#:
#: Six kilos is about thirteen pounds: a 12-quart tote with hardware, offcuts,
#: fasteners or a project's worth of parts in it.  Fill one with lead and the
#: rack does not care; fill all fifteen and the *wall* does, which is why this
#: is a parameter and not a constant in a formula.
BIN_MASS_KG: float = 6.0

#: What the top is expected to carry, kg — 45 kg is about 100 lb of tools,
#: parts and work spread over 80 inches.
TOP_LOAD_KG: float = 45.0

#: A person leaning hard on the front edge, kg.
#:
#: This is the load case that sizes the wall, and it is not a hypothetical: the
#: front edge of a bench is what you put your weight on to reach the back of
#: it.  It acts at the worst possible lever arm — the full depth from the wall
#: — and it is applied *on top of* a full rack and a loaded top.
FRONT_EDGE_LOAD_KG: float = 100.0

#: How far a cutter is run past the edge it opens on, mm.  Cutting exactly to
#: an edge leaves the boolean two coincident faces and sometimes a film of
#: geometry between them; the material beyond the edge is not there to remove.
_CUTTER_OVERRUN_MM: float = 2.0

#: Depth of the dado in a joist's underside that locates its rib, inches.
#:
#: A quarter of an inch into 1-1/2" stock: enough to locate the rib and to
#: make the glue line a joint rather than a butt, nowhere near enough to
#: matter to the joist.
_RIB_DADO_DEPTH_IN: float = 0.25

#: How close a notch has to come to a part's edge before the cutter is run
#: past that edge rather than stopped on it, mm.
_EDGE_TOL_MM: float = 0.01

#: length along +X, width up (+Z), thickness through (+Y) — a board laid flat
#: against the wall, or stood on edge along the bench's width.
_ON_EDGE = Rotation(90, 0, 0)

#: length along +Y, width up (+Z), thickness across (+X) — a joist, a rib, or
#: a runner: anything that runs front to back and stands up.
_ACROSS = Rotation(0, 0, 90) * Rotation(90, 0, 0)


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
    diameter_in: float = 0.375,
) -> float:
    """Return the reference withdrawal design value for a lag screw.

    In lb per inch of thread penetration, which is how NDS tabulates it.

    NDS equation 12.2-1, ``W = 1800 * G**1.5 * D**0.75``, for a lag screw
    inserted into the **side grain** of the main member — which is what a lag
    through a ledger into a stud is, and is the only case this bench uses.
    End-grain values are a fraction of it and do not appear here because no
    fastener in this design is in end grain.

    Parameters
    ----------
    specific_gravity : float, optional
        Main-member specific gravity, default :data:`SPF_SPECIFIC_GRAVITY`.
    diameter_in : float, optional
        Unthreaded shank diameter in inches, default 3/8".

    Returns
    -------
    float
        Allowable withdrawal, lb per inch of thread penetration into the stud.

    Notes
    -----
    A reference design value, with no adjustment factors applied.  It is an
    allowable (ASD) number, not an ultimate one, so the ratios computed against
    it in :meth:`BasementBench.check` are margins on top of a code-level
    safety factor rather than instead of one.
    """
    return 1800.0 * specific_gravity**1.5 * diameter_in**0.75


@dataclass(frozen=True)
class Mount:
    """How a build of this bench gets its load into the ground.

    Parameters
    ----------
    name : str
        Key in :data:`MOUNTS`.
    on_floor : bool
        Whether the rack's ribs run down to foot rails on the slab.  ``False``
        is the wall-hung build, where nothing touches the floor at all.
    summary : str
        One line on what this build is for, printed in the report.
    """

    name: str
    on_floor: bool
    summary: str


#: The two builds.
#:
#: ``hung``
#:     As briefed: two ledgers into the studs and nothing on the slab.
#:
#: ``legged``
#:     Every rib down onto a pair of 2x4 foot rails, the wall reduced to
#:     holding the bench upright.  For a wall that turned out to be furring,
#:     and for hand work, whose cyclic load is what walks a lag out of a stud.
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
            "every rib down onto foot rails — the floor carries the bench and "
            "the wall only keeps it upright"
        ),
    ),
}


@dataclass
class BasementBench:
    """A parametric wall-hung workbench with a bin rack for its bracket.

    Four numbers are published — the width, the depth, the height of the work
    surface, and the number of tiers in the rack.  Everything else is derived
    from those, from the bin the rack is sized to, and from what the plywood
    actually measures, so changing the sheet changes the rack rather than
    silently changing the fit.

    Parameters
    ----------
    mount : str, optional
        Key in :data:`MOUNTS`, default ``"hung"``.  ``"legged"`` runs every
        rib down to foot rails on the slab.
    overall_w_in, overall_d_in : float, optional
        Published width and depth, default 80" x 24".
    top_height_in : float, optional
        Height of the finished work surface off the slab, default 36" —
        standing height for assembly, wiring and repair work rather than the
        33-34" a hand-tool bench wants, because this bench has no leg room and
        is not for planing.  Set it to your table saw's table height to use
        the bench as outfeed.
    top_overhang_end_in, top_overhang_front_in : float, optional
        How far the top runs past the frame at each end and at the front,
        default 1" and 2".  The front overhang is what a clamp or a vice jaw
        needs; without it the front rail is flush with the edge and nothing
        can be gripped.
    n_tiers : int, optional
        Tiers of bins in the rack, default 3.
    n_bays : int, optional
        Bays across.  ``None``, the default, derives the most bays that still
        leave ``bin_side_clearance_in`` around a bin.
    bin_l_in, bin_w_in, bin_h_in : float, optional
        The bin the rack is sized to: length front-to-back, width across,
        height.  Default 16" x 11" x 7", a nominal 12-quart tote.  These are
        plausible figures rather than measured ones — measure yours.
    bin_side_clearance_in : float, optional
        Minimum clear space between a bin and the runner beside it, default
        3/8".  A floor is the minimum, not the target: the bay count is chosen
        to fit as many bays as this allows and the *actual* clearance that
        results is reported.
    bin_head_clearance_in : float, optional
        Clear space above a bin, default 1/2".
    bin_mass_kg : float, optional
        Mass of one full bin, default :data:`BIN_MASS_KG`.
    open_bays : tuple of int, optional
        Bays left without runners, for a shop vac, a bucket or a stool.
        Default none, and the report says so.
    frame_species : str, optional
        Solid stock for ledgers, joists, rails and feet, default ``"pine"`` —
        which is what :mod:`woodshop.inventory` calls the SPF a yard sells as
        framing lumber.
    ledger_nominal, joist_nominal : str, optional
        Nominal sizes, default ``"2x6"`` and ``"2x4"``.  The ledger is a 2x6
        rather than a 2x4 for two reasons and neither is bending: it gives two
        rows of lags proper edge distance, and it deepens the bracket.
    panel_material, panel_nominal_thickness : str, optional
        Sheet goods for the top, ribs and runners, default 3/4" birch plywood.
    top_layers : int, optional
        Structural layers in the top, default 2.
    surface_material, surface_nominal_thickness : str, optional
        The sacrificial top sheet, default 1/4" Baltic birch — screwed down
        and not glued, because the whole point of it is that it comes off.
    runner_w_in : float, optional
        Width (height, in the rack) of a bin runner, default 1-1/2".
    stud_spacing_in : float, optional
        Stud spacing on centre, default 16".
    stud_nominal : str, optional
        What the studs actually are, default ``"2x4"``.  A ``1x`` entry means
        furring strips on masonry, which will not hold a lag, and the wall
        findings become an ERROR.
    first_stud_offset_in : float, optional
        Distance from the left end of the ledger to the first stud centre.
        ``None``, the default, centres the studs in the ledger, which is the
        best case; a real wall decides this for you and a stud finder is how
        you learn it.
    lag_diameter_in, lag_length_in : float, optional
        Lag screw size, default 3/8" x 3-1/2".
    lags_per_stud : int, optional
        Lags into each stud, per ledger, default 2.  One passes; see
        :meth:`check`.
    top_load_kg, front_edge_load_kg : float, optional
        The two live-load cases: what sits on the top, and what leans on its
        front edge.  Defaults :data:`TOP_LOAD_KG` and
        :data:`FRONT_EDGE_LOAD_KG`.
    inventory : Inventory, optional
        Stock inventory.  Loaded from ``stock.yaml`` if not given.

    Raises
    ------
    ValueError
        If the mount is unknown, if fewer than two bays or one tier are asked
        for, if the bin will not fit the width at all, or if the tiers plus
        the top come to more than the published height — in which case there
        is no bench to model, only a rack whose bottom row is underground.
    """

    mount: str = "hung"

    overall_w_in: float = 80.0
    overall_d_in: float = 24.0
    top_height_in: float = 36.0
    top_overhang_end_in: float = 1.0
    top_overhang_front_in: float = 2.0

    n_tiers: int = 3
    n_bays: int | None = None

    bin_l_in: float = 16.0
    bin_w_in: float = 11.0
    bin_h_in: float = 7.0
    bin_side_clearance_in: float = 0.375
    bin_head_clearance_in: float = 0.5
    bin_mass_kg: float = BIN_MASS_KG
    open_bays: tuple[int, ...] = ()

    frame_species: str = "pine"
    ledger_nominal: str = "2x6"
    joist_nominal: str = "2x4"

    panel_material: str = "plywood_birch"
    panel_nominal_thickness: str = "3/4"
    top_layers: int = 2
    surface_material: str = "plywood_baltic_birch"
    surface_nominal_thickness: str = "1/4"
    runner_w_in: float = 1.5

    stud_spacing_in: float = 16.0
    stud_nominal: str = "2x4"
    first_stud_offset_in: float | None = None
    lag_diameter_in: float = 0.375
    lag_length_in: float = 3.5
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
        if self.n_tiers < 1:
            raise ValueError(f"a rack needs at least one tier, got {self.n_tiers}")
        if self.derived_n_bays < 2:
            raise ValueError(
                f'a {self.bin_w_in:g}" bin with '
                f'{self.bin_side_clearance_in:g}" a side needs '
                f"{mm_to_fractional_inch(self.min_bay_pitch)} of bench per bay; "
                f"{mm_to_fractional_inch(self.frame_w)} of frame gives fewer "
                "than two"
            )
        if self.rack_bottom_z <= 0.0:
            raise ValueError(
                f"{self.n_tiers} tiers at "
                f"{mm_to_fractional_inch(self.tier_pitch)} come to "
                f"{mm_to_fractional_inch(self.rack_h)}, which hangs the bottom "
                f"runner {mm_to_fractional_inch(-self.rack_bottom_z)} below the "
                f'slab under a {self.top_height_in:g}" top'
            )
        if self.ledger_w >= self.rack_h:
            raise ValueError(
                f"a {self.ledger_nominal} ledger is "
                f"{mm_to_fractional_inch(self.ledger_w)} deep and the rack is "
                f"only {mm_to_fractional_inch(self.rack_h)} — the two ledgers "
                "have nowhere to sit that is not each other"
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
        """Whether the ribs run down to foot rails on the slab."""
        return self.spec.on_floor

    # ------------------------------------------------------------------
    # Stock
    # ------------------------------------------------------------------

    @property
    def sheet(self):
        """The sheet the top, ribs and runners are cut from."""
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
        """Measured thickness of the structural plywood, mm.

        Never the nominal 3/4": birch ply measures 23/32", and the rib dadoes
        in the joists are cut to that rather than to the label.
        """
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
    def joist_t(self) -> float:
        """Thickness of a joist, mm."""
        return float(actual_dimensions_mm(self.joist_nominal)[0].magnitude)

    @property
    def joist_w(self) -> float:
        """Face width of a joist — its depth on edge, mm."""
        return float(actual_dimensions_mm(self.joist_nominal)[1].magnitude)

    @property
    def stud_t(self) -> float:
        """Thickness of a wall stud, mm — what a lag has to get through."""
        return float(actual_dimensions_mm(self.stud_nominal)[0].magnitude)

    @property
    def studs_are_furring(self) -> bool:
        """Whether the "studs" are 3/4" strapping rather than framing.

        The single assumption that, if wrong, invalidates every wall finding:
        a 1x3 strapping run on a foundation wall and a 2x4 stud wall look
        identical with the drywall off.
        """
        return self.stud_t < inches(1.0)

    # ------------------------------------------------------------------
    # The published envelope
    # ------------------------------------------------------------------

    @property
    def overall_w(self) -> float:
        """Published overall width, mm."""
        return inches(self.overall_w_in)

    @property
    def overall_d(self) -> float:
        """Published overall depth, mm."""
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
        """Thickness of the glued-up structural top alone, mm.

        The sacrificial sheet is screwed down, not glued, so it contributes
        nothing to stiffness and is left out of every deflection figure.
        """
        return self.top_layers * self.panel_t

    @property
    def frame_x0(self) -> float:
        """X of the frame's left end — the top overhangs it, mm."""
        return inches(self.top_overhang_end_in)

    @property
    def frame_w(self) -> float:
        """Width of the frame: the ledgers, the front rail, the feet, mm."""
        return self.overall_w - 2 * inches(self.top_overhang_end_in)

    @property
    def frame_d(self) -> float:
        """Depth of the frame from the stud faces forward, mm."""
        return self.overall_d - inches(self.top_overhang_front_in)

    # ------------------------------------------------------------------
    # The rack: bays across, tiers down
    # ------------------------------------------------------------------

    @property
    def runner_protrusion(self) -> float:
        """How far one runner stands proud of the rib it is screwed to, mm.

        A runner is a strip of the same 3/4" plywood screwed flat to the rib's
        face, so it eats its own thickness out of the bay on each side.  It
        could be let into a 1/4" dado and give two thirds of that back; at six
        kilos a bin, thirty dado setups buy nothing.
        """
        return self.panel_t

    @property
    def min_bay_pitch(self) -> float:
        """Narrowest rib-to-rib pitch that still admits a bin, mm.

        A bin plus its minimum clearance, plus the runner standing proud on
        each side, plus one rib.
        """
        return (
            inches(self.bin_w_in)
            + 2 * inches(self.bin_side_clearance_in)
            + 2 * self.runner_protrusion
            + self.panel_t
        )

    @property
    def derived_n_bays(self) -> int:
        """Bays across: the most the frame holds at the minimum clearance.

        The bay count is an *outcome* of the bin and the wall, not a choice.
        That is the whole reason the shipped bench has five bays and not the
        six a round 80" suggests: six bays leave a 10-5/8" channel between
        runners and an 11" bin does not go into it.
        """
        if self.n_bays is not None:
            return self.n_bays
        usable = self.frame_w - self.panel_t
        return max(0, int(usable // self.min_bay_pitch))

    @property
    def n_ribs(self) -> int:
        """Ribs: one each side of every bay."""
        return self.derived_n_bays + 1

    @property
    def bay_clear_w(self) -> float:
        """Clear width between two ribs, mm."""
        return (self.frame_w - self.n_ribs * self.panel_t) / self.derived_n_bays

    @property
    def bay_pitch(self) -> float:
        """Rib-to-rib spacing on centre, mm."""
        return self.bay_clear_w + self.panel_t

    @property
    def bin_channel_w(self) -> float:
        """Clear width between the two runners in a bay, mm."""
        return self.bay_clear_w - 2 * self.runner_protrusion

    @property
    def bin_side_clearance(self) -> float:
        """Actual clear space each side of a bin in its bay, mm.

        Not the parameter, which is only a floor.  What is left of a bay after
        the bin is also what you get a hand into, which is why the band this
        is checked against is wide at the top and narrow at the bottom.
        """
        return (self.bin_channel_w - inches(self.bin_w_in)) / 2

    @property
    def tier_pitch(self) -> float:
        """Vertical spacing between one tier's runners and the next, mm."""
        return (
            inches(self.runner_w_in)
            + inches(self.bin_h_in)
            + inches(self.bin_head_clearance_in)
        )

    @property
    def rack_h(self) -> float:
        """Total height of the rack, mm."""
        return self.n_tiers * self.tier_pitch

    @property
    def n_bins(self) -> int:
        """Bins the rack holds — bays that were left open hold none."""
        return (self.derived_n_bays - len(set(self.open_bays))) * self.n_tiers

    @property
    def rack_load_kg(self) -> float:
        """Mass of a full rack, kg."""
        return self.n_bins * self.bin_mass_kg

    # ------------------------------------------------------------------
    # Heights off the slab
    # ------------------------------------------------------------------

    @property
    def top_underside_z(self) -> float:
        """Underside of the top, mm off the slab."""
        return self.top_height - self.top_t

    @property
    def joist_bottom_z(self) -> float:
        """Underside of the joists, and therefore the top of the rack, mm."""
        return self.top_underside_z - self.joist_w

    @property
    def rack_top_z(self) -> float:
        """Top of the rack: the ribs hang directly under the joists, mm."""
        return self.joist_bottom_z

    @property
    def rack_bottom_z(self) -> float:
        """Underside of the bottom tier's runners, mm off the slab.

        In the hung build this is the lowest point on the whole bench, and the
        gap under it is what lets a broom through and keeps the plywood out of
        the first inch of a wet spring.
        """
        return self.rack_top_z - self.rack_h

    @property
    def foot_t(self) -> float:
        """Thickness of a foot rail, mm — zero in the hung build."""
        return self.joist_t if self.on_floor else 0.0

    @property
    def rib_bottom_z(self) -> float:
        """Bottom edge of a rib, mm off the slab."""
        return self.foot_t if self.on_floor else self.rack_bottom_z

    @property
    def rib_h(self) -> float:
        """Height of a rib, mm."""
        return self.rack_top_z - self.rib_bottom_z

    @property
    def top_ledger_z(self) -> tuple[float, float]:
        """(bottom, top) of the top ledger, mm.

        Its top face is where the joists bear, which is what fixes it: a
        ledger is positioned by the thing that sits on it.
        """
        return (self.joist_bottom_z - self.ledger_w, self.joist_bottom_z)

    @property
    def rack_ledger_z(self) -> tuple[float, float]:
        """(bottom, top) of the lower ledger, mm.

        Flush with the bottom of the rack, which puts it as low as the design
        allows and therefore makes the bracket as deep as the design allows.
        """
        return (self.rack_bottom_z, self.rack_bottom_z + self.ledger_w)

    @property
    def bracket_depth(self) -> float:
        """Lever arm of the wall bracket, mm.

        Centroid to centroid of the two ledgers: the tension at the top and
        the bearing at the bottom act through these, and the pull on every lag
        is the overturning moment divided by this number.  It is the single
        figure that decides whether a wall-hung bench is sensible or silly.
        """
        top = sum(self.top_ledger_z) / 2
        bottom = sum(self.rack_ledger_z) / 2
        return top - bottom

    def tier_z(self, tier: int) -> tuple[float, float]:
        """(runner bottom, bin bottom) for one tier, mm off the slab.

        Parameters
        ----------
        tier : int
            Tier index, 0 at the top.

        Returns
        -------
        tuple of float
            Underside of that tier's runners, and the height a bin sits at.
        """
        bin_top = self.rack_top_z - tier * self.tier_pitch - inches(
            self.bin_head_clearance_in
        )
        bin_bottom = bin_top - inches(self.bin_h_in)
        return (bin_bottom - inches(self.runner_w_in), bin_bottom)

    # ------------------------------------------------------------------
    # Positions across the bench
    # ------------------------------------------------------------------

    def rib_x(self, i: int) -> float:
        """X of rib *i*'s centreline, mm from the left end of the top.

        Parameters
        ----------
        i : int
            Rib index, 0 at the left end of the frame.

        Returns
        -------
        float
            Centre of the rib in assembly coordinates.
        """
        return self.frame_x0 + self.panel_t / 2 + i * self.bay_pitch

    @property
    def runner_len(self) -> float:
        """Length of a bin runner, mm.

        It stops at the ledgers' front faces rather than running back to the
        wall, because the bottom tier's runners are at exactly the height of
        the lower ledger and would otherwise run into it.
        """
        return self.frame_d - self.ledger_t

    @property
    def joist_len(self) -> float:
        """Length of a joist, mm — wall to the back of the front rail."""
        return self.frame_d - self.joist_t

    @property
    def stud_positions(self) -> list[float]:
        """X of every stud centre the ledgers cross, mm from the left of the top.

        With no ``first_stud_offset_in`` given, the studs are centred in the
        ledger: as many as fit with a comfortable end distance, and the
        remainder split between the two ends.  At the shipped 80" and 16" on
        centre that is five studs with 7" of ledger past the outermost lag,
        which is where the "roughly 80 inches" in the brief lands.

        A real wall does not offer this choice.  The parameter is there so the
        layout can be set from a stud finder and the findings recomputed
        against what is actually behind the drywall.

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
        """The lag, as it is written on the box — ``3/8" x 3-1/2"``."""
        return f"{self.lag_dia_label} x {self.lag_len_label}"

    @property
    def lag_penetration(self) -> float:
        """Thread penetration of a lag into a stud, mm.

        The lag's length less the ledger it passes through, less the tapered
        tip, which NDS does not count as thread.  Anything the ledger is
        shimmed off the studs by — strapping, a vapour membrane, a furred-out
        wall left proud — comes off this too and is not modelled, because the
        model cannot see it and you can.
        """
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
        nothing in the model touches ``z = 0`` at all — which is the point of
        that build and is visible in the plan and side views.

        Returns
        -------
        build123d.Compound
            Top, ledgers, joists, front rail, ribs, runners, and — in the
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

        joist_cz = self.joist_bottom_z + self.joist_w / 2
        for i in range(self.n_ribs):
            children.append(
                Pos(self.rib_x(i), self.joist_len / 2, joist_cz)
                * _ACROSS
                * self._joist()
            )
        children.append(
            Pos(mid_x, self.frame_d - self.joist_t / 2, joist_cz)
            * _ON_EDGE
            * self._front_rail()
        )

        rib_cz = self.rib_bottom_z + self.rib_h / 2
        for i in range(self.n_ribs):
            children.append(
                Pos(self.rib_x(i), self.frame_d / 2, rib_cz) * _ACROSS * self._rib()
            )

        runner_cy = self.ledger_t + self.runner_len / 2
        open_bays = set(self.open_bays)
        for bay in range(self.derived_n_bays):
            if bay in open_bays:
                continue
            xs = (
                self.rib_x(bay) + self.panel_t,
                self.rib_x(bay + 1) - self.panel_t,
            )
            for tier in range(self.n_tiers):
                z = self.tier_z(tier)[0] + inches(self.runner_w_in) / 2
                for x in xs:
                    children.append(Pos(x, runner_cy, z) * _ACROSS * self._runner())

        if self.on_floor:
            for y in (
                self.ledger_t + self.joist_w / 2,
                self.frame_d - self.joist_w / 2,
            ):
                children.append(Pos(mid_x, y, self.foot_t / 2) * self._foot_rail())

        return Compound(children=children, label=f"basement_bench_{self.mount}")

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
                "screwed down into the top ledger along the back edge at 6\" "
                "o.c. — those screws are the bench's tension connection and "
                "work in shear, which is why they are not into a plywood edge"
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
        """
        if name == "top_ledger":
            note = (
                f"lagged to {len(self.stud_positions)} studs, "
                f"{self.lags_per_stud} lags per stud, "
                f"{self.lag_label}; the "
                "joists bear on its top face and the top screws down into it"
            )
        else:
            note = (
                "lagged to the same studs; the ribs are notched over it and "
                "bear against its front face — the bottom of the bracket is "
                "compression and needs no fastener to work"
            )
        return Board(
            length_mm=self.frame_w,
            nominal=self.ledger_nominal,
            material=self.frame_species,
            label=name,
            notes=note,
        )

    def _joist(self):
        """Return one joist, dadoed on its underside to locate a rib.

        The dado is cut to the plywood's *measured* thickness rather than to
        3/4".  It is what locates every rib, and it is the joint that turns a
        rib from a hanging panel into the web of a cantilever: a glued dado
        over 20-1/2" is a fixed connection, and nothing else in the rack has
        to resist the rib rotating.
        """
        joist = Board(
            length_mm=self.joist_len,
            nominal=self.joist_nominal,
            material=self.frame_species,
            label="joist",
            notes=(
                "on edge, front to back; bears on the top ledger at the back "
                f"and butts the front rail; "
                f"{mm_to_fractional_inch(inches(_RIB_DADO_DEPTH_IN), 32)}-deep "
                f"x {mm_to_fractional_inch(self.panel_t, 64)} dado in the "
                "underside for its rib, glued and pocket-screwed"
            ),
        )
        depth = inches(_RIB_DADO_DEPTH_IN)
        dado = Pos(0.0, -self.joist_w / 2, 0.0) * Box(
            self.joist_len + 2 * _CUTTER_OVERRUN_MM, 2 * depth, self.panel_t
        )
        return retag(joist - dado, like=joist)

    def _front_rail(self) -> Board:
        """Return the front rail.

        A 2x4 rather than a 2x6, and the reason is the bins rather than the
        beam: on edge with its top flush with the joists it stops exactly at
        their underside, which is where the rack begins.  Two inches deeper
        and it would hang into the top tier and the top row of bins could not
        come out.
        """
        return Board(
            length_mm=self.frame_w,
            nominal=self.joist_nominal,
            material=self.frame_species,
            label="front_rail",
            notes=(
                "on edge across the joists' front ends, top flush with them; "
                "spans rib to rib, not end to end — every rib carries it"
            ),
        )

    def _rib(self) -> Panel:
        """Return one rack rib, notched over both ledgers.

        The rib is the part that makes this bench a bench rather than a shelf:
        a plywood web the full depth of the rack, dadoed into the joist above
        it and notched over the two ledgers behind it.  Both notches are the
        same size, and in the hung build both are at a corner, so the part is
        two saw cuts past a rectangle and has no left hand or right hand.
        """
        rib = Panel(
            length_mm=self.frame_d,
            width_mm=self.rib_h,
            material=self.panel_material,
            nominal_thickness=self.panel_nominal_thickness,
            label="rib",
            grain_direction="none",
            notes=(
                "front to back; glued into the joist's dado above, notched "
                f"over both ledgers behind; carries {self.n_tiers} pairs of "
                "runners, one pair per tier per face. Face grain either way — "
                "see the nesting finding"
            ),
        )
        cz = self.rib_bottom_z + self.rib_h / 2
        cuts = [
            self._ledger_notch(z0, z1, cz)
            for z0, z1 in (self.top_ledger_z, self.rack_ledger_z)
        ]
        notched = rib
        for cut in cuts:
            notched = notched - cut
        return retag(notched, like=rib)

    def _ledger_notch(self, z0: float, z1: float, rib_cz: float):
        """Return the cutter for one ledger notch, in the rib's local frame.

        A rib is born with its length along +X and its width along +Y, then
        rotated so that length runs front-to-back and width runs up.  The
        notch is therefore described here in the *unrotated* part's frame:
        local +X is the bench's +Y, local +Y is height.

        Parameters
        ----------
        z0, z1 : float
            Bottom and top of the ledger, mm off the slab.
        rib_cz : float
            Height of the rib's centre, mm off the slab.

        Returns
        -------
        build123d.Box
            A positioned cutter, run past the part's back edge — and past its
            top or bottom edge when the notch opens on one.
        """
        ov = _CUTTER_OVERRUN_MM
        x0 = -self.frame_d / 2 - ov
        x1 = -self.frame_d / 2 + self.ledger_t
        y0 = z0 - rib_cz
        y1 = z1 - rib_cz
        if y0 <= -self.rib_h / 2 + _EDGE_TOL_MM:
            y0 -= ov
        if y1 >= self.rib_h / 2 - _EDGE_TOL_MM:
            y1 += ov
        return Pos((x0 + x1) / 2, (y0 + y1) / 2, 0.0) * Box(
            x1 - x0, y1 - y0, self.panel_t + 2 * ov
        )

    def _runner(self) -> Panel:
        """Return one bin runner.

        Thirty identical strips of the same plywood as everything else in the
        rack, which is the point: a basement runs through its dew point
        several times a year, and a solid-stock runner would cup while a
        plywood one does not.
        """
        return Panel(
            length_mm=self.runner_len,
            width_mm=inches(self.runner_w_in),
            material=self.panel_material,
            nominal_thickness=self.panel_nominal_thickness,
            label="runner",
            grain_direction="length",
            notes=(
                "glued and screwed to the rib face; the pair either side of "
                "one rib can be screwed through to each other, which is "
                "stronger than either into 3/4\" ply on its own"
            ),
        )

    def _foot_rail(self) -> Board:
        """Return one foot rail — the legged build only.

        Laid flat under every rib, front and back.  It is the part that meets
        the slab, so it is the part that gets wet: plan on replacing it, keep
        it off the concrete on plastic shims or levellers, and do not glue the
        ribs to it.
        """
        return Board(
            length_mm=self.frame_w,
            nominal=self.joist_nominal,
            material=self.frame_species,
            label="foot_rail",
            notes=(
                "laid flat under the ribs; screwed, never glued — it is the "
                "sacrificial part between the plywood and a damp slab, and it "
                "is what takes the levellers"
            ),
        )

    # ------------------------------------------------------------------
    # Loads
    # ------------------------------------------------------------------

    def _load_cases(self, parts: list[CutPart]) -> list[tuple[str, float, float]]:
        """Return ``(name, mass_kg, lever_arm_mm)`` for every load on the bench.

        The lever arm is measured from the **face of the studs**, because that
        is the axis everything on a wall-hung piece turns about.  Splitting the
        dead load into the top and everything else matters: the top is the
        deepest part on the bench and reaches 2" further forward than the
        frame under it.

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
        return [
            ("the top itself", top_mass, self.overall_d / 2),
            ("frame, ribs and runners", frame_mass, self.frame_d / 2),
            (
                f"{self.n_bins} full bins",
                self.rack_load_kg,
                self.frame_d - inches(self.bin_l_in) / 2,
            ),
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
            Every finding, in the order the questions get asked on site:
            does it fit, is the wall real, will the wall hold it, does a bin
            go in, does anything sag, and what does a basement do to it.
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
        report.extend(self._stud_findings())
        report.extend(self._wall_findings(parts))
        report.extend(self._rack_findings())
        report.extend(self._stiffness_findings())
        report.extend(check_sheet_fit(parts, self.inventory))
        report.extend(check_thickness_substitution(parts, self.inventory))
        report.extend(check_material_suitability(parts, self.inventory))
        report.extend(self._basement_findings())
        return report

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
                f"{n} studs at {self.stud_spacing_in:g}\" o.c. under a "
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
                    f"{self.stud_spacing_in:g}\" o.c. studs give {n} fixings "
                    f"where 16\" would give "
                    f"{int(self.frame_w // inches(16.0)) + 1} — every "
                    "per-lag figure below scales straight with that",
                )
            )

        clash = inches(self.lag_diameter_in) + self.panel_t / 2
        for x in studs:
            nearest = min(
                (abs(x - self.rib_x(i)), i) for i in range(self.n_ribs)
            )
            if nearest[0] < clash:
                findings.append(
                    Finding(
                        Severity.WARN,
                        "wall",
                        f"the lag at {mm_to_fractional_inch(x)} lands under "
                        f"rib {nearest[1]}, whose notch bears on the ledger's "
                        "front face: counterbore that lag head and its washer "
                        "flush, or the rib will not seat",
                    )
                )
        return findings

    def _wall_findings(self, parts: list[CutPart]) -> list[Finding]:
        """Work the load path into the studs, in pounds, and show the margins.

        Everything here is a serviceability-level estimate against *reference*
        (allowable) design values with no adjustment factors applied.  It is
        arithmetic anyone can check, not a stamped design, and it is
        deliberately pessimistic in three places: the whole vertical load is
        put on the top ledger although the lower one carries some of it, the
        leaning load is added on top of a full rack rather than instead of
        one, and SPF is assumed where a yard may well have sold you fir.

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
                f"the rack is the bracket: "
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
                f"on one ledger alone it would be "
                f"{mm_to_fractional_inch(self.ledger_w)} of lever arm and "
                f"{shallow_lb:.0f} lb — {shallow_lb / t_lb:.1f}x as much. That "
                "ratio is the entire argument for running the ribs past a "
                "second ledger near the floor",
            )
        )

        if self.on_floor:
            findings.append(
                Finding(
                    Severity.INFO,
                    "wall",
                    "the legged build puts every rib on a foot rail, so the "
                    f"floor takes the {v_lb:.0f} lb and the lags below are "
                    "checked against the hung case anyway — the wall still "
                    "restrains the moment, and a bench that is also standing "
                    "on the floor is the conservative one",
                )
            )

        pen_in = self.lag_penetration / IN
        cap_lb = lag_withdrawal_lb_per_in(
            diameter_in=self.lag_diameter_in
        ) * pen_in
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

        shear_demand_lb = v_lb / n_lags
        findings.append(
            self._margin(
                "wall",
                f"shear: {shear_demand_lb:.0f} lb per lag against "
                f"{LAG_SHEAR_LB:.0f} lb, with the whole vertical load put on "
                f"the top ledger's {n_lags} lags",
                LAG_SHEAR_LB / shear_demand_lb if shear_demand_lb > 0 else math.inf,
                remedy=(
                    f"lags_per_stud={self.lags_per_stud + 1} would make it "
                    f"{v_lb / (len(studs) * (self.lags_per_stud + 1)):.0f} lb "
                    "each"
                ),
            )
        )

        n_screws = int(self.frame_w // inches(6.0)) + 1
        screw_cap = n_screws * SCREW_SHEAR_LB
        findings.append(
            self._margin(
                "joint",
                f"the top's back edge into the top ledger: {t_lb:.0f} lb of "
                f"tension across {n_screws} screws at 6\" o.c., "
                f"{screw_cap:.0f} lb of shear capacity",
                screw_cap / t_lb if t_lb > 0 else math.inf,
            )
        )

        bearing_mm2 = self.n_ribs * self.panel_t * self.ledger_w
        bearing_mpa = (m_nmm / self.bracket_depth) / bearing_mm2
        findings.append(
            self._margin(
                "joint",
                f"the ribs' notches bearing on the lower ledger: "
                f"{bearing_mpa:.2f} MPa ({bearing_mpa * 145.0:.0f} psi) over "
                f"{self.n_ribs} notches, against {_FC_PERP_PSI:.0f} psi "
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
        """Report whether a bin goes in, comes out, and what is left over.

        Returns
        -------
        list[Finding]
            The grid the bin produced, the three clearances that decide
            whether it is usable, and what the rack gave up to be a bracket.
        """
        findings: list[Finding] = [
            Finding(
                Severity.INFO,
                "rack",
                f"{self.derived_n_bays} bays x {self.n_tiers} tiers = "
                f"{self.n_bins} bins of "
                f"{self.bin_l_in:g}\" x {self.bin_w_in:g}\" x "
                f"{self.bin_h_in:g}\", {self.rack_load_kg:.0f} kg full; bays "
                f"are {mm_to_fractional_inch(self.bay_clear_w)} clear on a "
                f"{mm_to_fractional_inch(self.bay_pitch)} pitch",
            )
        ]
        findings.extend(
            check_clearance(
                "clearance each side of a bin",
                self.bin_side_clearance,
                inches(0.375),
                inches(2.0),
                tight_note=(
                    "a bin that fits its bay exactly is a bin you fight, and "
                    "nothing in a shop is square"
                ),
                loose_note=(
                    "which is finger room, not waste — but past 2\" a side "
                    "you are buying bench width to store air; try a wider bin "
                    "or one more bay"
                ),
            )
        )
        findings.extend(
            check_clearance(
                "clearance over a bin",
                inches(self.bin_head_clearance_in),
                inches(0.25),
                inches(1.5),
                tight_note="a lidded bin will catch on the runner above it",
                loose_note="which is a tier's worth of height spread thin",
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

        dead = self.bay_clear_w - self.bin_channel_w
        findings.append(
            Finding(
                Severity.INFO,
                "rack",
                f"the runners take {mm_to_fractional_inch(dead)} out of every "
                f"bay ({mm_to_fractional_inch(self.runner_protrusion, 64)} a "
                f"side): {mm_to_fractional_inch(self.bin_channel_w)} of "
                f"channel to take a bin {self.bin_w_in:g}\" wide. Letting them "
                "into a "
                "1/4\" dado gives two thirds of that back and costs thirty "
                "dado setups",
            )
        )

        bin_depth = inches(self.bin_l_in)
        behind = self.frame_d - bin_depth
        findings.append(
            Finding(
                Severity.INFO,
                "rack",
                f"a bin sits flush with the rib noses and leaves "
                f"{mm_to_fractional_inch(behind)} behind it — which is where "
                f"the two {self.ledger_nominal} ledgers already are, so the "
                "dead space and the structure are the same space",
            )
        )

        if not self.open_bays:
            findings.append(
                Finding(
                    Severity.WARN,
                    "rack",
                    "every bay is full of runners, so a shop vac, a bucket "
                    "and a floor fan have nowhere to go and this bench has no "
                    f"knee space anywhere; open_bays=({self.derived_n_bays // 2},) "
                    f"gives back one bay "
                    f"{mm_to_fractional_inch(self.bay_clear_w)} wide and "
                    f"{mm_to_fractional_inch(self.rack_h)} tall",
                )
            )
        else:
            findings.append(
                Finding(
                    Severity.INFO,
                    "rack",
                    f"bay(s) {sorted(set(self.open_bays))} left open: "
                    f"{mm_to_fractional_inch(self.bay_clear_w)} x "
                    f"{mm_to_fractional_inch(self.rack_h)} of clear space, at "
                    f"the cost of {self.n_tiers * len(set(self.open_bays))} bins",
                )
            )
        return findings

    def _stiffness_findings(self) -> list[Finding]:
        """Report what actually moves when the bench is loaded.

        Three candidates, and the report is worth reading for which one wins:
        the top between its joists, the front rail between its ribs, and the
        ribs themselves.  The ribs are 27" deep and 22" long, which makes them
        the stiffest thing in the building; what moves on a bench like this is
        the wall connection, and no beam formula reaches that.

        Returns
        -------
        list[Finding]
            One deflection finding per member, and one honest disclaimer.
        """
        findings: list[Finding] = []
        # Not the top load spread over the whole bench, which is nothing per
        # bay: the case that decides a bench top is the heavy thing that lands
        # on one bay of it.
        bay_kg = self.front_edge_load_kg
        findings.extend(
            check_shelf_deflection(
                self.panel_material,
                span_mm=self.bay_clear_w,
                depth_mm=self.overall_d,
                thickness_mm=self.structural_top_t,
                load_kg=bay_kg,
                label="the top between two joists",
                run_mm=self.frame_w,
            )
        )
        findings.extend(
            check_shelf_deflection(
                self.frame_species,
                span_mm=self.bay_clear_w,
                depth_mm=self.joist_t,
                thickness_mm=self.joist_w,
                label="the front rail between two ribs",
                load_kg=bay_kg,
                run_mm=self.frame_w,
            )
        )

        e_mpa = 6_900.0
        i_mm4 = self.panel_t * self.rib_h**3 / 12.0
        tip_n = newtons(self.front_edge_load_kg)
        tip_mm = tip_n * self.frame_d**3 / (3.0 * e_mpa * i_mm4)
        findings.append(
            Finding(
                Severity.INFO,
                "deflection",
                f"one rib as a cantilever: "
                f"{mm_to_fractional_inch(self.rib_h)} deep over "
                f"{mm_to_fractional_inch(self.frame_d)}, the whole "
                f"{self.front_edge_load_kg:.0f} kg leaning load on its nose, "
                f"{tip_mm:.3f} mm at the tip. The ribs are not what bends on "
                "this bench",
            )
        )
        findings.append(
            Finding(
                Severity.INFO,
                "material",
                "which is why the ribs declare no face-grain direction: at "
                f"{tip_mm:.3f} mm the difference between a rib cut along the "
                "sheet and one cut across it is not a number anybody can "
                "measure, and letting the nester turn them 90 degrees is "
                "worth a whole sheet of plywood. The runners keep theirs — a "
                f"{mm_to_fractional_inch(inches(self.runner_w_in))} strip cut "
                "across the face grain is a strip that splits at the screw",
            )
        )
        findings.append(
            Finding(
                Severity.WARN,
                "deflection",
                "what does move is the wall joint — lag slip, the ledger "
                "crushing into the studs, and the studs themselves bowing. "
                "None of it is in a beam formula and all of it is why the "
                "hung build is for assembly and wiring rather than for "
                "planing: a hand plane is a cyclic horizontal load at exactly "
                "the height of the tension connection",
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
                f"and the old phone cable run, and a "
                f"{self.lag_len_label} lag reaches "
                f"{mm_to_fractional_inch(self.lag_penetration)} past the far "
                "face of nothing — but a drill bit wandering off a stud edge "
                "reaches whatever is behind it",
            ),
            Finding(
                Severity.INFO,
                "site",
                "a wall-mounted bench cannot tip, which is the one thing a "
                "freestanding bench of this size has to buy with a heavy "
                "base. It is also why the rack can be loaded top-heavy "
                "without anybody thinking about it",
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
                    f"nothing touches the slab: the lowest part of the bench "
                    f"is {mm_to_fractional_inch(self.rack_bottom_z)} up, so "
                    "the floor sweeps clean, a wet spring does not reach the "
                    "plywood, and there is no foot to level on a floor that "
                    "was never flat",
                )
            )
        findings.append(
            Finding(
                Severity.INFO,
                "site",
                f"the top overhangs the front rail by "
                f"{mm_to_fractional_inch(inches(self.top_overhang_front_in))} "
                f"and each end by "
                f"{mm_to_fractional_inch(inches(self.top_overhang_end_in))} — "
                "that reveal is what a clamp jaw or a vice needs. A face vice "
                "at the left end wants the front rail and the end rib doubled "
                "behind it; nothing else in the design has to change",
            )
        )
        findings.append(
            Finding(
                Severity.INFO,
                "site",
                "the stud bays behind the bench are open, which is where the "
                "power strip, the cords and the task light go — screw the "
                "strip to the front face of the top ledger, above the bins "
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

    # Kept out of the design report: an undated price is a problem with the
    # quote, not with the joinery.
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
                render_sheet_diagram(res, output_pdf=outdir / f"{stem}_{slug}_sheets.pdf")
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

    Framing lumber is the one stock in this project whose width is fixed by
    the mill, so length is the only thing left to choose and
    :func:`woodshop.cutlist.optimize_1d.optimize_1d` is the right optimiser —
    a 2x6 ledger and a 2x4 joist cannot come off the same stick, which is why
    it groups by cross-section before it solves.

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
    return ProjectSpec(
        slug=f"basement-bench-{mount}",
        name=f"Basement wall bench — {mount}",
        summary=(
            f'{bench.overall_w_in:g}"W x {bench.overall_d_in:g}"D with a '
            f'{bench.top_height_in:g}" top, lagged to '
            f"{len(bench.stud_positions)} exposed studs at "
            f"{bench.stud_spacing_in:g}\" o.c. Underneath, "
            f"{bench.derived_n_bays} bays x {bench.n_tiers} tiers of "
            f"pull-out bins on plywood runners — and the rack's ribs are what "
            f"make the bracket "
            f"{mm_to_fractional_inch(bench.bracket_depth)} deep instead of "
            f"{mm_to_fractional_inch(bench.ledger_w)}. {bench.spec.summary.capitalize()}."
        ),
        species=bench.frame_species,
        build=bench.build,
        check=bench.check,
        inventory=bench.inventory,
        notes=(
            "The storage is the structure: two 2x6 ledgers into the studs and "
            "plywood ribs spanning between them turn a shelf into a "
            "cantilever bracket, and the check report works the load path "
            "into pounds rather than asserting it. The one assumption it "
            "cannot verify is that the exposed studs are framing and not "
            "furring strips on masonry — set stud_nominal to what is actually "
            "there."
        ),
        tags=["shop", "storage", "wall-mounted", mount],
    )


#: Projects this module contributes to the gallery.
PROJECTS: list[ProjectSpec] = [_spec("hung"), _spec("legged")]


def main() -> None:
    """Parse arguments and build the requested bench or benches."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--mount", choices=[*sorted(MOUNTS), "both"], default="hung"
    )
    parser.add_argument("--width", type=float, default=80.0)
    parser.add_argument("--depth", type=float, default=24.0)
    parser.add_argument("--height", type=float, default=36.0)
    parser.add_argument("--tiers", type=int, default=3)
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
    for mount in mounts:
        run(
            BasementBench(
                mount=mount,
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
