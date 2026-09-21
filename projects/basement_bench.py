"""Basement wall bench — 80" of bench hung on exposed studs, totes underneath.

The brief, as given::

    A workbench roughly 80" wide, to be mounted to exposed studs in the
    basement, with racks for project source storage bins underneath — a mix
    of 16 and 17 gallon bins, the slightly taller and slightly wider medium
    options.

Three phrases in that sentence decide almost everything, and it is worth
separating them before any lumber is chosen.

**"Roughly 80 inches"** is the only soft number, and softness is useful: the
bench is as wide as its ledgers, the ledgers are as long as the studs they can
reach, and 80" happens to be *five studs at 16" on centre with seven inches of
ledger past the outermost lag at each end* — which is exactly the end distance
a lag wants.  A round 80" and a correct lag layout are the same number here by
luck, not by design, and :meth:`BasementBench.stud_positions` recomputes it the
moment the spacing changes.

**"Mounted to exposed studs"** is the structural brief.  It is not a detail of
attachment — it *is* the structure.  There are no legs in the shipped design.
Two ledgers are lagged to the studs, everything else hangs off them, and the
bench is a cantilever whose depth is the distance between those two ledgers.
Which means the interesting question is not "will the lags hold?" but "what is
the bracket, and how deep is it?" — and the answer is the tote rack.  See
*The rack is the bracket*.

**"A mix of 16 and 17 gallon bins"** is the rest of the design, and it turns
out to be the most demanding clause of the three.  These are not parts bins.
They are furniture-sized boxes, and every dimension of the rack, the depth of
the bench, the number of tiers and the way a tote is held up all fall out of
them.

The two totes
-------------
Both are stock items, both are sold as *medium*, and each of them governs a
different dimension of the rack — which is exactly what the brief said about
them:

======================  =========================  ==========  ==========
Tote                    Exterior (at the rim)      Interior    Governs
======================  =========================  ==========  ==========
Sterilite 64 qt (1497)  23-3/4 x 16 x **13-1/2**   19-3/8 x    **tier
                                                   13-1/8 x    height**
                                                   13
Project Source /        **26-7/8 x 18** x 12-1/2   22-1/4 x    **bay width
HDX 17 gal (68 qt)                                 13-1/2 x    and bench
                                                   11          depth**
======================  =========================  ==========  ==========

Exterior sizes are the manufacturers' and retailers' own published figures,
read 2026-09-21 (see :data:`BIN_TYPES` for the sources).  The interiors come
from retailer Q&A rather than a spec sheet, which matters because of what they
imply — see *Why a tote will not sit on runners*.

Three things follow immediately, and all three change the bench:

* **The bench has to be about 31" deep.**  A 17-gallon tote is 26-7/8" long.
  It does not go into a 24"-deep bench front to back in any orientation, so
  the depth is derived from the tote rather than chosen:
  :attr:`BasementBench.overall_d` comes out **30-7/8"**, and the report says
  what that costs.
* **Two tiers, not three.**  A 13-1/2" tote on a 3/4" shelf with head room
  wants 14-23/32" of pitch, and two of those is 29-7/16" — which is more than
  a 36" bench had to give until the joists came out of it.  See *The joists
  had to go*.
* **Four bays, and only because of the mix.**  Four 17-gallon bays do not fit
  across 78" with any usable clearance; four 16-gallon bays waste seven
  inches; **three wide and one narrow fits exactly, with 9/16" a side
  everywhere**.  The mix is not a preference here.  It is what makes the
  fourth column exist.

The rack is the bracket
-----------------------
A wall-hung bench rotates about the bottom of whatever holds it: the load is
out in front of the wall, so the top of the bracket is pulled *away* from the
studs and the bottom is pushed *into* them.  Nothing avoids that.  The only
thing a design controls is the **lever arm** — the vertical distance between
the tension at the top and the bearing at the bottom — because the tension
each lag sees is the overturning moment divided by it.

A bench held by a single ledger under its top has a lever arm of a few inches
and needs heroic fasteners.  This one has **24-11/16"**, because the rack's
ribs run from the underside of the top down past a second ledger near the
floor, and both ledgers are lagged to the same studs.  The storage is not
hanging off the structure; it *is* the structure, and the check report prints
the moment, the lever arm and the resulting pull on each lag so the claim can
be read rather than believed:

* the ribs are plywood webs 30" deep and 29" long — they are not the flexible
  part of this bench, and the report says so;
* the top's back edge is screwed down into the top ledger at 4" centres, so
  the tension crosses that joint in **shear** rather than trying to pull screws
  out of a plywood edge;
* the bottom of each rib is notched over the lower ledger, so the thrust at
  the bottom is plain wood-on-wood **bearing** and needs no fastener at all.

Why a tote will not sit on runners
----------------------------------
The first version of this bench carried small parts bins on pairs of plywood
runners screwed to the rib faces — cheap, light, a third of the plywood, and
air moves under a bin instead of condensation sitting under it.  That does not
survive a 17-gallon tote, and the reason is in the table above.

**A tote tapers.**  Its published interior width is measured at the *bottom*:
13-1/2" inside on a box that is 18" across the rim.  So the base is roughly
13-3/4" wide.  Asking for runners changes the bay arithmetic as well, because
a runner stands 23/32" proud of its rib on each side — and even after the bays
have been widened to swallow that, the runners are **nearly four inches
further apart than the tote's base is wide**, and the tote drops straight
between them.

So the tiers are **shelves**, housed in 1/4" dadoes in the rib faces, and that
is a decision the geometry made rather than a preference:
:meth:`BasementBench.check` compares each tote's base against the span between
runners and turns ``support="runners"`` into an ERROR with the numbers in it.
The shelf is not all loss — it is also 3/4" of tier pitch instead of 1-1/2",
which is three quarters of an inch of floor clearance back.

The joists had to go
--------------------
The small-bin version of this bench had 2x4 joists on edge between the ledger
and the front rail, with the rack hanging below them.  Two tiers of 13-1/2"
totes need 29-7/16", and under a 36" top with a 1-11/16" slab and 3-1/2" of
joist there was 30-13/16" — which is not enough once the bottom shelf needs to
be off a basement floor.

The joists were doing two jobs and the ribs already do both: the ribs bear on
the top ledger themselves, and the top spans rib to rib — 19" of 1-7/16"
plywood, which does not move.  So the ribs now run in one piece from the
underside of the top to the bottom of the rack, a **1x4 front rail laid flat**
is let into their top front corners to give the top's front edge a screw line
and tie the rib noses, and a whole part family is gone.

That recovered 3-1/2".  It also deepened the bracket by four inches, because
the lower ledger went down with the rack.  A part deleted for one reason
paying off in another is usually a sign the part was in the wrong place.

Two builds
----------
``hung``
    As briefed, and the default.  Nothing touches the floor — the lowest part
    of the bench is the bottom shelf, 4-1/8" up — so the slab can be swept
    under, a wet spring does not reach the plywood, and there is no leg to
    kick or to level on a floor that was never flat.  The wall carries all of
    it.

``legged``
    Every rib runs down to a pair of 2x4 foot rails and the bench stands on
    the floor, with the ledgers reduced to holding it upright.  This is the
    build for a wall that turned out to be furring, for a slab flat enough not
    to care, and for hand work: planing and hammering put cyclic load into a
    connection, and cyclic load is what backs a lag out of a stud over a few
    years.  It costs the swept floor and it costs the feet being the first
    thing to find out that a basement is damp — hence the foot rails, which
    are the sacrificial part and are meant to be replaceable.

What the studs are asked for, and the one thing that invalidates it
-------------------------------------------------------------------
:meth:`BasementBench.check` works both load paths in pounds, because the
withdrawal and shear figures it compares against come from an imperial code
(NDS, and the withdrawal formula ``W = 1800 G**1.5 D**0.75`` lb per inch of
thread penetration at :data:`SPF_SPECIFIC_GRAVITY`).  Eight full totes are
about 320 lb of live load that a rack of parts bins never had, and the binding
number is **vertical shear, not pull-out** — which is why this bench is lagged
with **1/2" x 4"** lags rather than the 3/8" ones a lighter rack would take,
and why :attr:`BasementBench.lags_per_stud` is 2.

All of that rests on one assumption the model cannot check and the report
therefore states as loudly as it can: **the exposed studs must be a framed
stud wall, not furring strips on masonry.**  A 1x3 strapping run cut-nailed
to a foundation wall looks exactly like a stud wall with the drywall off, and
a 4" lag driven into one finds 3/4" of pine and then concrete.  Set
``stud_nominal`` to what is actually there; a 1x entry turns the wall findings
into an ERROR rather than quietly halving the penetration.

What is inferred rather than given
----------------------------------
* **A tote's base width.**  Nobody publishes it.  It is taken as the published
  interior width plus two wall thicknesses (:data:`TOTE_WALL_IN`), which is
  the number the runner-versus-shelf decision turns on, so it is worth
  measuring before cutting dadoes.
* **What a full tote weighs**, :data:`BIN_DESIGN_MASS_KG` — 18 kg, about 40 lb.
  Not a volume calculation: 17 gallons of anything dense is far heavier than
  that, and the real limit is that **the tote has to come out and go back**.
  A tote nobody can lift down is a tote that never moves, so the design load
  is what a person will carry rather than what the box will hold.
* **Plastic totes, not cardboard.**  A basement crosses its dew point several
  times a year and a cardboard box is a humidity sponge with your hardware in
  it.  That is most of why the brief's bins are the right answer.
* **The top is two layers of 3/4" plywood glued into one 1-7/16" slab, with a
  1/4" sheet screwed down on top of it and not glued.**  The thin sheet is the
  one you saw into, spill epoxy on, and replace; screwing rather than gluing
  it is the whole point of it being there.
* **There is no knee space anywhere.**  The rack fills the full width, so this
  is a bench to stand at.  ``open_bays`` gives a bay back — for a shop vac, a
  bucket, a stool — by leaving its shelves out, and the report says when none
  has been.

What the depth costs
--------------------
A 30-7/8" deep bench is not free, and the report prices it in three currencies:

* **Reach.**  Most people work comfortably to about 25" over a 36" surface, so
  the back five inches are a shelf you reach over rather than work on.  That
  is where the power strip, the task light and the job in progress live, and
  it is not wasted — but it is not bench either.
* **Plywood.**  At 24" deep both layers of an 80" top came off one 4x8 sheet.
  At 30-7/8" each layer needs its own, so the top alone is two sheets instead
  of one.
* **The alternative.**  A 24"-deep bench can still hold these totes — turned
  sideways, one per 27" of width, which is two of them instead of eight.  The
  depth is what buys the other six.

Run it
------
::

    uv run python projects/basement_bench.py
    uv run python projects/basement_bench.py --mount legged --outdir build
    uv run python projects/basement_bench.py --mount both --outdir build

and in a REPL, to ask what a different wall, a different tote or the runners
would give::

    BasementBench(stud_spacing_in=24.0).stud_positions
    BasementBench(bins=("16gal",)).bay_bins
    runners = BasementBench(support="runners")
    runners.check(runners.build(), extract(runners.build()))    # ERROR, and why
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

#: Reference lateral design value ``Z`` for one lag screw in single shear,
#: 1-1/2" side member, into a main member of G = 0.42, lb, by shank diameter.
#:
#: Read off NDS Table 12E for the nearest tabulated case rather than computed
#: from the yield-limit equations, and rounded down.  These carry no adjustment
#: factors at all: no load duration (C_D = 1.0, i.e. permanent-ish storage
#: load), no wet service, no temperature.  A basement is not obviously a dry
#: service condition, and if yours runs above 19% moisture content C_M = 0.7
#: applies and every shear margin below drops by a third.
#:
#: A diameter that is not in this table is not checked for shear, and the
#: report says so rather than interpolating.
LAG_SHEAR_LB: dict[float, float] = {0.375: 210.0, 0.5: 270.0}

#: Reference compression design value perpendicular to grain for SPF, psi.
#:
#: NDS Supplement Table 4A, ``Fc_perp = 425 psi``.  It is what the ribs'
#: notches bear against at the bottom of the bracket, and it is the one place
#: in this bench where wood is loaded across its grain.
_FC_PERP_PSI: float = 425.0

#: Allowable lateral load on one #10 x 3" structural wood screw into SPF, lb.
#:
#: Deliberately conservative — the top-to-ledger screw line has twenty of them
#: and is nowhere near critical, so there is nothing to buy by sharpening the
#: figure.
SCREW_SHEAR_LB: float = 130.0

#: Spacing of the screws that fasten the top's back edge into the top ledger.
#:
#: Four inches rather than the six a top would normally get, because this is
#: not a fastening detail — it is the bench's tension connection, and it is
#: the cheapest place on the whole piece to buy margin.
_TOP_SCREW_SPACING_IN: float = 4.0

#: Wall thickness assumed when working a tote's base width back out of its
#: published interior width, inches.
#:
#: **Inferred, and the one number in this file worth measuring before cutting
#: dadoes.**  A tote's interior is quoted at the bottom of the box, where it is
#: narrowest; add two walls and you have roughly the base's outside width,
#: which is what decides whether a pair of runners can catch it.
TOTE_WALL_IN: float = 0.125

#: Design mass of one full tote, kg — about 40 lb.
#:
#: Not a volume calculation.  Seventeen gallons of fasteners is several hundred
#: pounds and seventeen gallons of foam is nothing; what sets the number is
#: that **the tote has to come out and go back**, so the design load is what a
#: person will lift down off a shelf at chest height rather than what the box
#: will hold.  A tote nobody can lift is a tote that never moves, and this rack
#: exists to be rummaged in.
BIN_DESIGN_MASS_KG: float = 18.0

#: What the top is expected to carry, kg — 45 kg is about 100 lb of tools,
#: parts and work spread over 80 inches.
TOP_LOAD_KG: float = 45.0

#: A person leaning hard on the front edge, kg.
#:
#: This is the load case that sizes the wall, and it is not a hypothetical: the
#: front edge of a bench is what you put your weight on to reach the back of
#: it — and on a bench this deep, you will.  It acts at the worst possible
#: lever arm, the full depth from the wall, and it is applied *on top of* a
#: full rack and a loaded top.
FRONT_EDGE_LOAD_KG: float = 100.0

#: How far a person works comfortably across a bench at standing height, mm.
#:
#: A rule of thumb rather than an anthropometric table: past about 25" you are
#: leaning on the front edge to reach, which is exactly the load case above.
COMFORTABLE_REACH_IN: float = 25.0

#: How far a cutter is run past the edge it opens on, mm.  Cutting exactly to
#: an edge leaves the boolean two coincident faces and sometimes a film of
#: geometry between them; the material beyond the edge is not there to remove.
_CUTTER_OVERRUN_MM: float = 2.0

#: Depth of the dadoes in the rib faces that carry the shelves, inches.
_SHELF_DADO_DEPTH_IN: float = 0.25

#: How close a notch has to come to a part's edge before the cutter is run
#: past that edge rather than stopped on it, mm.
_EDGE_TOL_MM: float = 0.01

#: length along +X, width up (+Z), thickness through (+Y) — a board laid flat
#: against the wall.
_ON_EDGE = Rotation(90, 0, 0)

#: length along +Y, width up (+Z), thickness across (+X) — a rib or a runner:
#: anything that runs front to back and stands up.
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
    diameter_in: float = 0.5,
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
        Unthreaded shank diameter in inches, default 1/2".

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
class Bin:
    """One stock storage tote the rack is sized to hold.

    Every dimension here is the manufacturer's or the retailer's own published
    figure, with the source recorded, because the whole rack is derived from
    them: get the tote wrong and the bench is the wrong depth.

    Parameters
    ----------
    key : str
        Short name used in :data:`BIN_TYPES` and on the command line.
    name : str
        What it is called on the shelf.
    gallons : float
        Nominal capacity, as printed on the box.
    length_in, width_in, height_in : float
        Exterior, **measured at the rim**, which on a tapered box is its
        widest point and therefore the number a bay has to clear.  Length runs
        front to back in this rack; width runs across the bench.
    interior_w_in : float
        Published interior width.  A tote's interior is quoted at the *bottom*
        of the box, so this is what :attr:`base_w_in` is worked back from — and
        it is the number that decides shelves versus runners.
    source : str
        Where the figures were read.
    source_url : str
        A link to it.
    read_on : str
        ISO date the specification was read, on the same principle as a price
        in ``stock.yaml``: a number without a date behind it is a number
        somebody remembered.
    """

    key: str
    name: str
    gallons: float
    length_in: float
    width_in: float
    height_in: float
    interior_w_in: float
    source: str
    source_url: str
    read_on: str

    @property
    def base_w_in(self) -> float:
        """Outside width of the tote's base, inches — **inferred**.

        The interior width plus two walls of :data:`TOTE_WALL_IN`.  Nobody
        publishes a base dimension, and this is the number a pair of runners
        would have to catch, so it is the one worth a tape measure before any
        dado is cut.
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


#: The totes this rack is designed around, read 2026-09-21.
#:
#: Two medium totes, a gallon apart in capacity and nothing alike in shape,
#: and between them they set every dimension of the rack:
#:
#: ``16gal``
#:     Sterilite's 64-quart latching box, model 1497.  The **taller** one at
#:     13-1/2", so it sets the tier pitch and the 17-gallon tote rides with an
#:     inch of spare headroom.
#:
#: ``17gal``
#:     The 68-quart medium tote sold as Project Source Commander at Lowe's and
#:     as the HDX Tough Tote at Home Depot — the same 26-7/8" x 18" x 12-1/2"
#:     box either way, which is a useful corroboration of a figure that decides
#:     how deep the bench is.  The **wider and longer** one, so it sets both
#:     the bay width and the depth of the whole bench.
BIN_TYPES: dict[str, Bin] = {
    "16gal": Bin(
        key="16gal",
        name="Sterilite 64 qt latching box (1497)",
        gallons=16.0,
        length_in=23.75,
        width_in=16.0,
        height_in=13.5,
        interior_w_in=13.125,
        source="Sterilite product page, 64 Qt. Latching Box",
        source_url="https://www.sterilite.com/product/64-qt-latching-box/",
        read_on="2026-09-21",
    ),
    "17gal": Bin(
        key="17gal",
        name="Project Source Commander / HDX 17 gal tough tote (68 qt)",
        gallons=17.0,
        length_in=26.875,
        width_in=18.0,
        height_in=12.5,
        interior_w_in=13.5,
        source="Lowe's and Home Depot listings, which agree to a tenth of an inch",
        source_url=(
            "https://www.homedepot.com/p/HDX-17-Gal-Tough-Storage-Tote-in-"
            "Black-with-Red-Lid-999-17G-HDX-R/330324132"
        ),
        read_on="2026-09-21",
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

#: How a tier holds a tote up.
#:
#: ``shelf``
#:     A plywood panel housed in 1/4" dadoes in the rib faces.  The shipped
#:     answer, and not a preference: see :meth:`BasementBench._support_findings`.
#:
#: ``runners``
#:     A pair of plywood strips on the rib faces, which is what a rack of
#:     *small* bins wants and what this rack had until the totes got big.
SUPPORTS: frozenset[str] = frozenset({"shelf", "runners"})


@dataclass
class BasementBench:
    """A parametric wall-hung workbench with a tote rack for its bracket.

    Three numbers are published — the width, the height of the work surface,
    and the number of tiers.  The **depth is not a choice**: it is derived from
    the longest tote in the mix, and so are the bay count, the bay widths and
    the tier pitch.  Change the tote and the bench changes with it, rather than
    the totes quietly failing to fit later.

    Parameters
    ----------
    mount : str, optional
        Key in :data:`MOUNTS`, default ``"hung"``.  ``"legged"`` runs every
        rib down to foot rails on the slab.
    bins : tuple of str, optional
        Keys in :data:`BIN_TYPES` — the totes on hand, default both.  Order is
        only cosmetic; the bays are laid out widest first either way.
    overall_w_in : float, optional
        Published width, default 80".
    overall_d_in : float, optional
        Published depth.  ``None``, the default, derives it from the longest
        tote plus the ledger behind it and the front overhang, which is the
        only way a 26-7/8" box fits front to back.
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
        Tiers of totes in the rack, default 2.  Three does not fit under a 36"
        top and ``__post_init__`` says so rather than drawing one underground.
    n_bays : int, optional
        Bays across.  ``None``, the default, derives the most bays that hold
        the *narrowest* tote and then widens as many of them as will fit to
        the widest one — which is how the mix earns the fourth column.
    support : str, optional
        ``"shelf"`` (default) or ``"runners"``.  Both build; only one of them
        holds a tapered tote up, and :meth:`check` works out which.
    bin_side_clearance_in : float, optional
        Minimum clear space between a tote and the rib beside it, default 3/8".
        A floor, not a target: the bay count is chosen to fit as many bays as
        this allows and the *actual* clearance that results is reported.
    bin_head_clearance_in : float, optional
        Clear space above the tallest tote, default 1/2".
    bin_back_clearance_in : float, optional
        Clear space behind the longest tote, in front of the ledgers, default
        1/2".  This is what the bench's depth is built out of.
    bin_mass_kg : float, optional
        Mass of one full tote, default :data:`BIN_DESIGN_MASS_KG`.
    open_bays : tuple of int, optional
        Bays left without shelves, for a shop vac, a bucket or a stool.
        Default none, and the report says so.
    frame_species : str, optional
        Solid stock for ledgers, rails and feet, default ``"pine"`` — which is
        what :mod:`woodshop.inventory` calls the SPF a yard sells as framing
        lumber.
    ledger_nominal, rail_nominal, foot_nominal : str, optional
        Nominal sizes, default ``"2x6"``, ``"1x4"`` and ``"2x4"``.  The ledger
        is a 2x6 rather than a 2x4 for two reasons and neither is bending: it
        gives two rows of lags proper edge distance, and it deepens the
        bracket.  The front rail is a 1x4 *laid flat* because every inch it
        hangs below the top is an inch off the top tier.
    panel_material, panel_nominal_thickness : str, optional
        Sheet goods for the top, ribs and shelves, default 3/4" birch plywood.
    top_layers : int, optional
        Structural layers in the top, default 2.
    surface_material, surface_nominal_thickness : str, optional
        The sacrificial top sheet, default 1/4" Baltic birch — screwed down
        and not glued, because the whole point of it is that it comes off.
    runner_w_in : float, optional
        Width (height, in the rack) of a bin runner, default 1-1/2".  Only
        used when ``support="runners"``.
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
        Lag screw size, default 1/2" x 4".  Eight full totes are about 320 lb
        of live load and the binding number is shear, not pull-out; 3/8" lags
        carry it, but not with a margin worth having.
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
        If the mount, the support or a bin key is unknown, if fewer than two
        bays or one tier are asked for, if a tote will not fit the width or
        the depth at all, or if the tiers come to more than the published
        height leaves under the top.
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
    support: str = "shelf"

    bin_side_clearance_in: float = 0.375
    bin_head_clearance_in: float = 0.5
    bin_back_clearance_in: float = 0.5
    bin_mass_kg: float = BIN_DESIGN_MASS_KG
    open_bays: tuple[int, ...] = ()

    frame_species: str = "pine"
    ledger_nominal: str = "2x6"
    rail_nominal: str = "1x4"
    foot_nominal: str = "2x4"

    panel_material: str = "plywood_birch"
    panel_nominal_thickness: str = "3/4"
    top_layers: int = 2
    surface_material: str = "plywood_baltic_birch"
    surface_nominal_thickness: str = "1/4"
    runner_w_in: float = 1.5

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
        if self.support not in SUPPORTS:
            raise ValueError(
                f"support must be one of {sorted(SUPPORTS)}, got {self.support!r}"
            )
        unknown = [key for key in self.bins if key not in BIN_TYPES]
        if unknown:
            raise ValueError(
                f"unknown bin(s) {unknown}; known: {sorted(BIN_TYPES)}"
            )
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
                f"{self.support} {mm_to_fractional_inch(-self.rack_bottom_z)} "
                f'below the slab under a {self.top_height_in:g}" top'
            )
        if self.shelf_depth < inches(self.longest.length_in):
            raise ValueError(
                f"a {self.longest.label} tote is "
                f"{mm_to_fractional_inch(inches(self.longest.length_in))} long "
                f"and the rack is only {mm_to_fractional_inch(self.shelf_depth)} "
                f"deep behind the front rail"
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

    @property
    def on_shelves(self) -> bool:
        """Whether the totes sit on shelves rather than runners."""
        return self.support == "shelf"

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
        """Width one bay takes up for *bin_*, rib excluded, mm.

        The tote, its minimum clearance either side, and — with runners — the
        runner standing proud of each rib.  A shelf is housed in the rib and
        costs nothing sideways, which is one more reason the shipped build has
        shelves: runners take 1-7/16" out of every bay on top of not holding a
        tote up, and that is enough to price the wider tote out of the bench
        altogether.

        Parameters
        ----------
        bin_ : Bin
            The tote that bay holds.

        Returns
        -------
        float
            The width of bench one bay of this tote consumes.
        """
        return (
            inches(bin_.width_in)
            + 2 * inches(self.bin_side_clearance_in)
            + 2 * self.runner_protrusion
        )

    @property
    def bay_bins(self) -> tuple[Bin, ...]:
        """Which tote goes in which bay, left to right.

        The bay count is not chosen and neither is the mix.  Fit as many bays
        of the **narrowest** tote as the frame holds; then widen as many of
        them as will still fit to the **widest** tote.  With an 80" bench and
        these two totes that lands on three wide bays and one narrow one — and
        four bays of the wide tote do not fit, which is why the mix is what
        makes the fourth column exist rather than a matter of taste.

        Returns
        -------
        tuple of Bin
            One entry per bay, widest first.
        """
        rib = self.panel_t
        narrow, wide = self.narrowest, self.widest
        if self.n_bays is not None:
            count = self.n_bays
        else:
            count = 0
            while (count + 1) * self.bay_cell(narrow) + (count + 2) * rib <= (
                self.frame_w
            ):
                count += 1
        if count <= 0:
            return ()
        budget = self.frame_w - (count + 1) * rib
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
    def n_ribs(self) -> int:
        """Ribs: one each side of every bay."""
        return self.derived_n_bays + 1

    @property
    def bay_slack(self) -> float:
        """Width left over after every bay has its tote and clearance, mm.

        Shared equally between the bays, so the clearance a tote actually gets
        is the minimum plus half of this.
        """
        used = sum(self.bay_cell(b) for b in self.bay_bins)
        return self.frame_w - self.n_ribs * self.panel_t - used

    def bay_clear_w(self, bay: int) -> float:
        """Clear width between the two ribs of one bay, mm.

        Parameters
        ----------
        bay : int
            Bay index, 0 at the left.

        Returns
        -------
        float
            Rib face to rib face.
        """
        return self.bay_cell(self.bay_bins[bay]) + self.bay_slack / self.derived_n_bays

    def bin_side_clearance(self, bay: int) -> float:
        """Actual clear space each side of the tote in one bay, mm.

        Parameters
        ----------
        bay : int
            Bay index.

        Returns
        -------
        float
            Half of what is left after the tote and, with runners, after the
            runners standing proud of the ribs.
        """
        channel = self.bay_clear_w(bay) - 2 * self.runner_protrusion
        return (channel - inches(self.bay_bins[bay].width_in)) / 2

    @property
    def runner_protrusion(self) -> float:
        """How far one support stands proud of the rib, mm.

        Zero for a shelf, which is housed in the rib rather than screwed to
        its face.
        """
        return 0.0 if self.on_shelves else self.panel_t

    @property
    def support_t(self) -> float:
        """Vertical height a tier's support takes under a tote, mm.

        3/4" for a shelf, 1-1/2" for a pair of runners on edge — three
        quarters of an inch per tier, which at two tiers is most of an inch of
        floor clearance.
        """
        return self.panel_t if self.on_shelves else inches(self.runner_w_in)

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
        """The sheet the top, ribs and shelves are cut from."""
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

        Never the nominal 3/4": birch ply measures 23/32", and the shelf
        dadoes in the ribs are cut to that rather than to the label.
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
    def rail_t(self) -> float:
        """Thickness of the front rail, mm — how far it hangs below the top."""
        return float(actual_dimensions_mm(self.rail_nominal)[0].magnitude)

    @property
    def rail_w(self) -> float:
        """Face width of the front rail, mm — how far back it reaches."""
        return float(actual_dimensions_mm(self.rail_nominal)[1].magnitude)

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
        """Whether the "studs" are 3/4" strapping rather than framing.

        The single assumption that, if wrong, invalidates every wall finding:
        a 1x3 strapping run on a foundation wall and a 2x4 stud wall look
        identical with the drywall off.
        """
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

        The tote, the gap behind it, the ledger it stops against and the front
        overhang the top needs for a clamp.  This is what ``overall_d_in=None``
        uses, and it is the clearest case in the piece of a dimension being an
        *outcome*: a 26-7/8" box does not go into a 24" bench, so the bench is
        30-7/8".
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

    @property
    def reach_over(self) -> float:
        """How much of the depth is past a comfortable reach, mm.

        Not wasted — it is where the power strip, the task light and the job
        in progress live — but it is not bench either, and a bench this deep
        should say so.
        """
        return max(0.0, self.overall_d - inches(COMFORTABLE_REACH_IN))

    # ------------------------------------------------------------------
    # Heights off the slab
    # ------------------------------------------------------------------

    @property
    def top_underside_z(self) -> float:
        """Underside of the top, and the top of every rib, mm off the slab."""
        return self.top_height - self.top_t

    @property
    def rib_top_z(self) -> float:
        """Top edge of a rib, mm.

        The ribs carry the top directly.  There are no joists — two tiers of
        13-1/2" totes needed the 3-1/2" they were taking.
        """
        return self.top_underside_z

    @property
    def rack_top_z(self) -> float:
        """Ceiling a tote has to clear on its way out, mm.

        The front rail's underside, not the top's: the rail is laid flat at
        the front and a tote slides out under it.  Every extra inch of rail
        is an inch off the top tier, which is why it is a 1x4 and not a 2x4.
        """
        return self.top_underside_z - self.rail_t

    @property
    def tier_pitch(self) -> float:
        """Vertical spacing from one tier's support to the next, mm."""
        return (
            self.support_t
            + inches(self.tallest.height_in)
            + inches(self.bin_head_clearance_in)
        )

    @property
    def rack_h(self) -> float:
        """Total height of the rack, mm."""
        return self.n_tiers * self.tier_pitch

    @property
    def rack_bottom_z(self) -> float:
        """Underside of the bottom tier's support, mm off the slab.

        In the hung build this is the lowest point on the whole bench, and the
        gap under it is what lets a broom through and keeps the plywood out of
        the first inch of a wet spring.
        """
        return self.rack_top_z - self.rack_h

    @property
    def rib_bottom_z(self) -> float:
        """Bottom edge of a rib, mm off the slab."""
        return self.foot_t if self.on_floor else self.rack_bottom_z

    @property
    def rib_h(self) -> float:
        """Height of a rib, mm."""
        return self.rib_top_z - self.rib_bottom_z

    @property
    def top_ledger_z(self) -> tuple[float, float]:
        """(bottom, top) of the top ledger, mm.

        Its top face is where the ribs and the top bear, which is what fixes
        it: a ledger is positioned by the thing that sits on it.
        """
        return (self.rib_top_z - self.ledger_w, self.rib_top_z)

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
        """(support bottom, tote bottom) for one tier, mm off the slab.

        Parameters
        ----------
        tier : int
            Tier index, 0 at the top.

        Returns
        -------
        tuple of float
            Underside of that tier's shelf or runners, and the height a tote
            stands at.
        """
        top = self.rack_top_z - tier * self.tier_pitch - inches(
            self.bin_head_clearance_in
        )
        bottom = top - inches(self.tallest.height_in)
        return (bottom - self.support_t, bottom)

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

    def rib_x(self, i: int) -> float:
        """X of rib *i*'s centreline, mm from the left end of the top.

        Bays are not all the same width — the wide totes' bays are two inches
        wider than the narrow one's — so this accumulates rather than
        multiplying.

        Parameters
        ----------
        i : int
            Rib index, 0 at the left end of the frame.

        Returns
        -------
        float
            Centre of the rib in assembly coordinates.
        """
        x = self.frame_x0 + self.panel_t / 2
        for bay in range(i):
            x += self.bay_clear_w(bay) + self.panel_t
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
            Midway between its two ribs.
        """
        return (self.rib_x(bay) + self.rib_x(bay + 1)) / 2

    @property
    def shelf_depth(self) -> float:
        """Depth of a shelf or the length of a runner, mm.

        It stops at the ledgers' front faces rather than running back to the
        wall, because the bottom tier sits at exactly the height of the lower
        ledger and would otherwise run into it.  What is left in front of it
        is what the tote's length had to fit in.
        """
        return self.frame_d - self.ledger_t

    @property
    def shelf_len(self) -> float:
        """Nominal length of a shelf before its bay's width is added, mm.

        A shelf is housed in a dado in each rib, so it is its bay's clear
        width plus two dado depths.
        """
        return 2 * inches(_SHELF_DADO_DEPTH_IN)

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
        """The lag, as it is written on the box — ``1/2" x 4"``."""
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
            Top, ledgers, front rail, ribs, shelves (or runners), and — in the
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
                self.frame_d - self.rail_w / 2,
                self.rib_top_z - self.rail_t / 2,
            )
            * self._front_rail()
        )

        rib_cz = self.rib_bottom_z + self.rib_h / 2
        for i in range(self.n_ribs):
            children.append(
                Pos(self.rib_x(i), self.frame_d / 2, rib_cz) * _ACROSS * self._rib(i)
            )

        children.extend(self._tote_supports())

        if self.on_floor:
            for y in (
                self.ledger_t + self.foot_w / 2,
                self.frame_d - self.foot_w / 2,
            ):
                children.append(Pos(mid_x, y, self.foot_t / 2) * self._foot_rail())

        return Compound(children=children, label=f"basement_bench_{self.mount}")

    def _tote_supports(self) -> list[object]:
        """Return every shelf, or every pair of runners, positioned.

        Returns
        -------
        list
            One placed part per shelf, or two per bay per tier for runners.
            Bays in ``open_bays`` get neither.
        """
        placed: list[object] = []
        open_bays = set(self.open_bays)
        cy = self.ledger_t + self.shelf_depth / 2
        for bay in range(self.derived_n_bays):
            if bay in open_bays:
                continue
            for tier in range(self.n_tiers):
                bottom = self.tier_z(tier)[0]
                if self.on_shelves:
                    placed.append(
                        Pos(
                            self.bay_centre_x(bay),
                            cy,
                            bottom + self.panel_t / 2,
                        )
                        * self._shelf(bay)
                    )
                    continue
                for x in (
                    self.rib_x(bay) + self.panel_t,
                    self.rib_x(bay + 1) - self.panel_t,
                ):
                    placed.append(
                        Pos(x, cy, bottom + self.support_t / 2)
                        * _ACROSS
                        * self._runner()
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
                "ribs bear on its top face and the top screws down into it"
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

    def _front_rail(self) -> Board:
        """Return the front rail, laid flat under the top's front edge.

        Laid flat rather than on edge, and a 1x rather than a 2x, because the
        rack's ceiling is this rail's underside: every inch it hangs below the
        top is an inch the top tier's totes cannot use, and at 13-1/2" a tote
        there is no inch going spare.  Flat it still gives the top's front
        edge a screw line and ties the rib noses together, which is all it was
        ever for — the top spans rib to rib on its own.
        """
        return Board(
            length_mm=self.frame_w,
            nominal=self.rail_nominal,
            material=self.frame_species,
            label="front_rail",
            notes=(
                "laid flat, let into a rebate in each rib's top front corner, "
                "top flush with the ribs; the top screws down into it"
            ),
        )

    def _rib(self, index: int):
        """Return one rack rib, notched over both ledgers and the front rail.

        The rib is the part that makes this bench a bench rather than a shelf:
        a plywood web the full height of the rack, bearing on the top ledger,
        notched over the lower one, and housing the shelves that carry the
        totes.  It is also the whole reason there are no joists — see the
        module docstring.

        Parameters
        ----------
        index : int
            Rib index, 0 at the left.  Only the two end ribs differ, and only
            in having shelf dadoes on their inner face alone; the blank is the
            same for all of them, which is why they consolidate to one row on
            the cut list.

        Returns
        -------
        build123d.Shape
            The rib, re-tagged after its cuts.
        """
        rib = Panel(
            length_mm=self.frame_d,
            width_mm=self.rib_h,
            material=self.panel_material,
            nominal_thickness=self.panel_nominal_thickness,
            label="rib",
            grain_direction="none",
            notes=(
                "front to back; bears on the top ledger, notched over the "
                "lower one, rebated at the top front for the rail. "
                f"{self.n_tiers} shelf dadoes per face "
                f"({mm_to_fractional_inch(inches(_SHELF_DADO_DEPTH_IN), 32)} "
                "deep) — inner face only on the two end ribs. Face grain "
                "either way: see the nesting finding"
                if self.on_shelves
                else (
                    "front to back; bears on the top ledger, notched over the "
                    "lower one, rebated at the top front for the rail; "
                    f"carries {self.n_tiers} pairs of runners"
                )
            ),
        )
        cz = self.rib_bottom_z + self.rib_h / 2
        cuts = [
            self._ledger_notch(z0, z1, cz)
            for z0, z1 in (self.top_ledger_z, self.rack_ledger_z)
        ]
        cuts.append(self._rail_rebate(cz))
        if self.on_shelves:
            cuts.extend(self._shelf_dadoes(index, cz))
        cut = rib
        for solid in cuts:
            cut = cut - solid
        return retag(cut, like=rib)

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

    def _rail_rebate(self, rib_cz: float):
        """Return the cutter for the front rail's rebate, in the local frame.

        Parameters
        ----------
        rib_cz : float
            Height of the rib's centre, mm off the slab.

        Returns
        -------
        build123d.Box
            A positioned cutter at the rib's top front corner.
        """
        ov = _CUTTER_OVERRUN_MM
        x0 = self.frame_d / 2 - self.rail_w
        x1 = self.frame_d / 2 + ov
        y0 = self.rack_top_z - rib_cz
        y1 = self.rib_h / 2 + ov
        return Pos((x0 + x1) / 2, (y0 + y1) / 2, 0.0) * Box(
            x1 - x0, y1 - y0, self.panel_t + 2 * ov
        )

    def _shelf_dadoes(self, index: int, rib_cz: float) -> list[object]:
        """Return the shelf dadoes for one rib, in its local frame.

        A dado is cut only where a shelf actually lands, so the two end ribs
        get them on their inner face only and a bay left open gets none —
        which is the difference between a housed shelf and a decorative
        groove.

        Parameters
        ----------
        index : int
            Rib index.
        rib_cz : float
            Height of the rib's centre, mm off the slab.

        Returns
        -------
        list
            Positioned cutters, one per shelf that meets this rib.
        """
        ov = _CUTTER_OVERRUN_MM
        depth = inches(_SHELF_DADO_DEPTH_IN)
        open_bays = set(self.open_bays)
        # A rib serves the bay to its left (index - 1) and to its right.
        faces = []
        if index - 1 >= 0 and index - 1 not in open_bays:
            faces.append(-1.0)
        if index < self.derived_n_bays and index not in open_bays:
            faces.append(1.0)

        x0 = self.ledger_t - self.frame_d / 2
        x1 = self.frame_d / 2 + ov
        cutters: list[object] = []
        for sign in faces:
            for tier in range(self.n_tiers):
                bottom = self.tier_z(tier)[0]
                y0 = bottom - rib_cz
                y1 = y0 + self.panel_t
                cutters.append(
                    Pos(
                        (x0 + x1) / 2,
                        (y0 + y1) / 2,
                        sign * self.panel_t / 2,
                    )
                    * Box(x1 - x0, y1 - y0, 2 * depth)
                )
        return cutters

    def _shelf(self, bay: int) -> Panel:
        """Return one tier's shelf for one bay.

        Parameters
        ----------
        bay : int
            Bay index — the bays are not all the same width, so neither are
            the shelves.

        Returns
        -------
        Panel
            The shelf, housed a quarter inch into each rib.
        """
        return Panel(
            length_mm=self.bay_clear_w(bay) + self.shelf_len,
            width_mm=self.shelf_depth,
            material=self.panel_material,
            nominal_thickness=self.panel_nominal_thickness,
            label="shelf",
            grain_direction="none",
            notes=(
                f"housed {mm_to_fractional_inch(inches(_SHELF_DADO_DEPTH_IN), 32)} "
                "into a dado in each rib, glued; a tote tapers and its base is "
                "nowhere near as wide as its rim, which is why this is a shelf "
                "and not a pair of runners. Face grain either way — see the "
                "nesting finding"
            ),
        )

    def _runner(self) -> Panel:
        """Return one bin runner — the ``support="runners"`` build only.

        Kept because it is the right answer for small bins and because the
        design report can then compare the two rather than assert one.  For
        the totes in :data:`BIN_TYPES` it is the wrong answer, and
        :meth:`_support_findings` says so with the numbers.
        """
        return Panel(
            length_mm=self.shelf_depth,
            width_mm=inches(self.runner_w_in),
            material=self.panel_material,
            nominal_thickness=self.panel_nominal_thickness,
            label="runner",
            grain_direction="length",
            notes=(
                "glued and screwed to the rib face; the pair either side of "
                "one rib can be screwed through to each other, which is "
                'stronger than either into 3/4" ply on its own'
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
            nominal=self.foot_nominal,
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

        The totes are summed bay by bay rather than lumped, because the two
        sizes are different lengths and the shorter one therefore sits with
        its mass further forward.

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
            ("frame, ribs and shelves", frame_mass, self.frame_d / 2),
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
            it fit, is the wall real, will the wall hold it, does a tote go in
            and stay up, does anything sag, and what does a basement do to it.
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
        report.extend(self._support_findings())
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
                f"a {mm_to_fractional_inch(self.overall_d)} top takes a "
                f"whole {sheet.width_mm / IN:.0f}\"x"
                f"{sheet.height_mm / IN:.0f}\" sheet per layer — {across} of "
                f"them fit across the sheet, where a 24\" top gets "
                f"{int(sheet.width_mm // inches(24.0))}. The tote's length is "
                "paid for in plywood as well as in reach",
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

        clash = inches(self.lag_diameter_in) + self.panel_t / 2
        for x in studs:
            nearest = min((abs(x - self.rib_x(i)), i) for i in range(self.n_ribs))
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

        bearing_mm2 = self.n_ribs * self.panel_t * self.ledger_w
        bearing_mpa = (m_nmm / self.bracket_depth) / bearing_mm2
        findings.append(
            self._margin(
                "joint",
                "the ribs' notches bearing on the lower ledger: "
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
        """Report whether a tote goes in, comes out, and what is left over.

        Returns
        -------
        list[Finding]
            The grid the totes produced, the clearances that decide whether it
            is usable, and what the rack gave up to be a bracket.
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
            ribs = self.n_ribs * self.panel_t
            over = self.derived_n_bays * self.bay_cell(wide) + ribs - self.frame_w
            spare = self.frame_w - self.derived_n_bays * self.bay_cell(narrow) - ribs
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

        for bay, bin_ in enumerate(self.bay_bins):
            if bay in set(self.open_bays):
                continue
            findings.extend(
                check_clearance(
                    f"bay {bay} ({bin_.label}, "
                    f"{mm_to_fractional_inch(self.bay_clear_w(bay))} clear), "
                    "each side of the tote",
                    self.bin_side_clearance(bay),
                    inches(0.25),
                    inches(2.0),
                    tight_note=(
                        "a tote is floppy plastic and goes in crooked; under a "
                        "quarter inch it binds"
                    ),
                    loose_note=(
                        "past 2\" a side you are buying bench width to store "
                        "air — try a wider tote or one more bay"
                    ),
                )
            )

        homeless = [b for b in self.bin_types if b not in self.bay_bins]
        for bin_ in homeless:
            findings.append(
                Finding(
                    Severity.WARN,
                    "rack",
                    f"the {bin_.label} tote gets no bay in this build: it "
                    f"wants {mm_to_fractional_inch(self.bay_cell(bin_))} of "
                    f"bench each and there is "
                    f"{mm_to_fractional_inch(self.frame_w)} to share between "
                    f"{self.derived_n_bays} bays and {self.n_ribs} ribs",
                )
            )

        for bin_ in self.bin_types:
            if bin_ is self.tallest or bin_ in homeless:
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

        behind = self.shelf_depth - inches(self.longest.length_in)
        findings.append(
            Finding(
                Severity.INFO,
                "rack",
                f"a {self.longest.label} tote sits on a "
                f"{mm_to_fractional_inch(self.shelf_depth)} shelf with "
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

    def _support_findings(self) -> list[Finding]:
        """Report whether the tiers can actually hold a tote up.

        The check that changed this design.  A tote tapers: its published
        interior width is measured at the base, so a box 18" across the rim is
        under 14" across the bottom.  Runners at the edges of a bay are
        further apart than that however the bay is sized, and the tote goes
        between them.

        Returns
        -------
        list[Finding]
            One finding per tote: INFO when the support holds it, ERROR when
            it does not.
        """
        findings: list[Finding] = []
        for bay, bin_ in enumerate(self.bay_bins):
            if bay in set(self.open_bays):
                continue
            base = inches(bin_.base_w_in)
            if self.on_shelves:
                findings.append(
                    Finding(
                        Severity.INFO,
                        "support",
                        f"bay {bay}: a {bin_.label} tote is "
                        f"{mm_to_fractional_inch(inches(bin_.width_in))} across "
                        f"the rim and about {mm_to_fractional_inch(base)} across "
                        "the base — a shelf does not care, which is why it is "
                        "a shelf",
                    )
                )
                continue
            span = self.bay_clear_w(bay) - 2 * self.runner_protrusion
            short_by = span - base
            severity = Severity.INFO if short_by < 0 else Severity.ERROR
            verdict = (
                f"{mm_to_fractional_inch(-short_by)} of bearing a side"
                if short_by < 0
                else (
                    f"{mm_to_fractional_inch(short_by)} wider than the base — "
                    "the tote drops between them; use support='shelf'"
                )
            )
            findings.append(
                Finding(
                    severity,
                    "support",
                    f"bay {bay}: runners {mm_to_fractional_inch(span)} apart "
                    f"under a {bin_.label} tote whose base is about "
                    f"{mm_to_fractional_inch(base)} wide — {verdict}",
                )
            )
        if not self.on_shelves:
            findings.append(
                Finding(
                    Severity.INFO,
                    "support",
                    "base widths are inferred from the published interior "
                    f"width plus two {mm_to_fractional_inch(inches(TOTE_WALL_IN), 32)} "
                    "walls, because nobody publishes a base dimension. Measure "
                    "yours before cutting anything to this number",
                )
            )
        return findings

    def _stiffness_findings(self) -> list[Finding]:
        """Report what actually moves when the bench is loaded.

        Three candidates, and the report is worth reading for which one wins:
        the shelf under a full tote, the top between its ribs, and the ribs
        themselves.  The ribs are 30" deep and 29" long, which makes them the
        stiffest thing in the building; what moves on a bench like this is the
        wall connection, and no beam formula reaches that.

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
                depth_mm=self.shelf_depth,
                thickness_mm=self.panel_t,
                load_kg=self.bin_mass_kg,
                label=f"a shelf under one {self.bay_bins[widest_bay].label} tote",
                run_mm=self.frame_w,
            )
        )
        findings.extend(
            check_shelf_deflection(
                self.panel_material,
                span_mm=self.bay_clear_w(widest_bay),
                depth_mm=self.overall_d,
                thickness_mm=self.structural_top_t,
                load_kg=self.front_edge_load_kg,
                label=(
                    f"the top between two ribs, {self.front_edge_load_kg:.0f} kg "
                    "over one bay"
                ),
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
                "one rib as a cantilever: "
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
                "which is why neither the ribs nor the shelves declare a "
                f"face-grain direction: at {tip_mm:.3f} mm on a rib and a "
                "tenth of a millimetre on a shelf, the difference between "
                "cutting one along the sheet and across it is not a number "
                "anybody can measure — and letting the nester turn them 90 "
                "degrees is worth a whole sheet of plywood. Only the top "
                "keeps its grain, because it is the face you look at and "
                "freeing it saved nothing",
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
                "humidity sponge with your hardware in it. The shelves are "
                "plywood for the same reason — solid stock that wide would "
                "cup through a Maine spring",
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
                    "plywood, and there is no foot to level on a floor that "
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

    Framing lumber is the one stock in this project whose width is fixed by
    the mill, so length is the only thing left to choose and
    :func:`woodshop.cutlist.optimize_1d.optimize_1d` is the right optimiser —
    a 2x6 ledger and a 1x4 rail cannot come off the same stick, which is why
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
            f"storage totes ({tally}) — and the rack's ribs are what make the "
            f"bracket {mm_to_fractional_inch(bench.bracket_depth)} deep "
            f"instead of {mm_to_fractional_inch(bench.ledger_w)}. "
            f"{bench.spec.summary.capitalize()}."
        ),
        species=bench.frame_species,
        build=bench.build,
        check=bench.check,
        inventory=bench.inventory,
        notes=(
            "The storage is the structure: two 2x6 ledgers into the studs and "
            "plywood ribs spanning between them turn a shelf into a "
            "cantilever bracket, and the check report works the load path "
            "into pounds rather than asserting it. The totes decide the rest "
            "— a 26-7/8\" box is why the bench is 30-7/8\" deep, a 13-1/2\" "
            "one is why there are two tiers and no joists, and the mix of the "
            "two is what makes a fourth bay fit across 80\". The one "
            "assumption the model cannot verify is that the exposed studs are "
            "framing and not furring strips on masonry — set stud_nominal to "
            "what is actually there."
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
    parser.add_argument("--support", choices=sorted(SUPPORTS), default="shelf")
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
        help="leave this bay without shelves; repeatable",
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
                support=args.support,
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
