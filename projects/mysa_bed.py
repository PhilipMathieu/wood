"""Mysa sleigh bed — a reproduction of the Chilton Furniture design, and a variant.

Source
------
https://www.chiltons.com/products/mysa-sleigh-bed-cherry

Published specification, reproduced here as the design targets::

    Twin            81"L x 44"W x 40"H      Full   81"L x 59"W x 40"H
    Queen           87"L x 64"W x 40"H      King   87"L x 83"W x 40"H
    California King 91"L x 79"W x 40"H

    Headboard gap to platform  9-3/4"
    Slats                      16, 2-1/2" wide x 3/4" thick, spaced 2" apart,
                               14" off floor
    Centre rail lengthwise; metal hardware secures rails to posts
    Recommended mattress height 10"

Where the geometry comes from
-----------------------------
The first version of this model was built from the listing's prose alone, and
it was wrong in almost every respect that prose does not cover: it had square
posts, a frame-and-panel headboard, and a footboard.  The bed has none of
those.

The product page carries a **Cylindo 360 viewer** (customer 6989, product code
``MYSABED``), which serves an orthographic-ish frame every 11.25°.  Frames 1,
9 and 17 are the foot, side and head elevations.  Measured against the
published 87" x 64" x 40" envelope on 2026-08-17, they give:

===========================  =========================================
Head stiles                  2" thick across the bed, outer faces flush
                             with the overall width.  Seen from the
                             side they are *shaped*: the back edge is
                             straight and vertical at the head end, and
                             the front edge is a curve — 3-3/8" deep at
                             the floor, swelling to 6" at rail height,
                             tapering to about 3-1/4" at a rounded top.
Headboard panel              One slab, not a frame and panel.  Bottom
                             edge 23-5/8" off the floor, top just below
                             the stile tops, **raked back about 10°**.
Footboard                    There isn't one.  The foot is the rail.
Rails                        Top 15" off the floor, about 5-1/2" deep.
Foot legs                    1-3/4" thick across the bed, at the
                             corners with their outer faces flush.
                             Shaped: outer edge vertical, inner edge
                             sweeping from 5-5/8" deep at the rail to
                             2-3/4" at the floor.
===========================  =========================================

The published 9-3/4" headboard gap and 14" slat height both check out
against those frames, so they are still used to *derive* the panel's bottom
edge rather than being hard-coded from the photograph.

What is still inferred
----------------------
* **Thicknesses of the panel and rails** (1"): the elevations give outlines,
  not sections, and 1" is what the listing quotes for the rails.
* **How the panel is held** — housed in a shallow rebate in the stiles' front
  faces here.  The joint is not visible in any frame.
* **The ledger and centre rail.** The slats plainly sit on something; a ledger
  strip inside each rail and a centre rail down the middle is the ordinary way
  to do it, and the centre rail is mentioned in the listing.
* **Spacers** between slat ends, to hold the published 2" spacing.

Two variants are modelled:

``faithful``
    Solid cherry throughout, as sold.

``plywood``
    Headboard panel in cherry plywood, slats in Baltic birch.  Both
    substitutions change more than the material name — see
    :func:`woodshop.checks.check_thickness_substitution`,
    :func:`woodshop.checks.check_sheet_fit` and
    :func:`woodshop.checks.check_material_suitability`, which this script runs.

Run it
------
::

    uv run python projects/mysa_bed.py --size queen --variant faithful
    uv run python projects/mysa_bed.py --size queen --variant both --outdir build
"""

from __future__ import annotations

import argparse
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from build123d import Compound, Pos, Rotation

from woodshop.checks import (
    CheckReport,
    Finding,
    Severity,
    alternative_sheets,
    check_clearance,
    check_envelope,
    check_material_suitability,
    check_price_provenance,
    check_sheet_fit,
    check_slat_deflection,
    check_thickness_substitution,
)
from woodshop.cutlist.extract import CutPart, extract
from woodshop.cutlist.hardwood import nest_hardwood
from woodshop.cutlist.optimize_2d import pack_by_material
from woodshop.inventory import Inventory
from woodshop.parts import Board, Panel, ShapedBoard
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

#: Turns a profile drawn in (up the part, into the bed) into the bed's frame.
#:
#: :class:`woodshop.parts.ShapedBoard` draws its profile in X-Y and extrudes
#: along Z, and takes profile-X as the part's *length* — which for a stile or
#: a leg is its height, because that is the way the grain runs.  So the
#: profiles here are drawn with X up the part, and this rotation stands them
#: on end with their thickness across the bed.
PROFILE_TO_BED = Rotation(0, -90, 0)


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


def _profile_mm(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Convert a profile given in inches to millimetres."""
    return [(x * IN, y * IN) for x, y in points]


# ---------------------------------------------------------------------------
# Published sizes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BedSize:
    """A mattress size and the published envelope of the bed built around it.

    Parameters
    ----------
    name : str
        Size name, e.g. ``"queen"``.
    mattress_l_in, mattress_w_in : float
        Nominal mattress length and width in inches.
    overall_l_in, overall_w_in, overall_h_in : float
        Published overall envelope in inches.
    """

    name: str
    mattress_l_in: float
    mattress_w_in: float
    overall_l_in: float
    overall_w_in: float
    overall_h_in: float = 40.0


SIZES: dict[str, BedSize] = {
    "twin": BedSize("twin", 75, 38, 81, 44),
    "full": BedSize("full", 75, 54, 81, 59),
    "queen": BedSize("queen", 80, 60, 87, 64),
    "king": BedSize("king", 80, 76, 87, 83),
    "calking": BedSize("calking", 84, 72, 91, 79),
}


# ---------------------------------------------------------------------------
# The bed
# ---------------------------------------------------------------------------


@dataclass
class MysaBed:
    """A parametric Mysa sleigh bed.

    Dimensions are held in inches because that is how the source specifies
    them, and converted to mm at the point of use.

    Parameters
    ----------
    size : BedSize
        Which bed size to build.
    variant : str
        ``"faithful"`` for solid cherry throughout, or ``"plywood"`` for the
        cherry-plywood headboard panel and Baltic birch slats.
    species : str, optional
        Solid-wood species, default ``"cherry"``.
    stile_thickness_in : float, optional
        Head stile thickness across the bed, default 2" (measured).
    stile_depth_foot_in, stile_depth_max_in, stile_depth_top_in : float, optional
        The stile's shaped front edge: depth from the head end at the floor,
        at its widest, and at the top.  Default 3-3/8", 6", 3-1/4".
    stile_widest_at_in : float, optional
        Height at which the stile is deepest, default 16".
    rail_top_in, rail_height_in, rail_thickness_in : float, optional
        Rail section and height, default top at 15", 5-1/2" deep, 1" thick.
    leg_thickness_in : float, optional
        Foot leg thickness across the bed, default 1-3/4".
    leg_depth_top_in, leg_depth_foot_in : float, optional
        Foot leg depth at the rail and at the floor, default 5-5/8" and
        2-3/4".
    slat_top_in, slat_width_in, slat_thickness_in, slat_gap_in : float, optional
        Published slat deck, default 14" off the floor, 2-1/2" x 3/4" at 2".
    n_slats : int, optional
        Number of slats, default 16.
    headboard_gap_in : float, optional
        Published clear gap between the slat tops and the panel's lower edge,
        default 9-3/4".
    panel_thickness_in, panel_rake_deg, panel_reveal_in : float, optional
        Headboard panel thickness, its backward lean, and how far the stile
        tops stand above it.  Default 1", 10°, 3/4".
    panel_housing_in : float, optional
        How deep the panel is housed into each stile, default 3/8".
    ledger_w_in, ledger_t_in : float, optional
        Ledger strip inside each rail that carries the slats, default
        1-1/2" x 3/4".
    centre_rail_h_in, centre_rail_t_in : float, optional
        Centre support rail section, default 3-1/2" x 1".
    inventory : Inventory, optional
        Stock inventory used for real sheet thicknesses.  Loaded from
        ``stock.yaml`` if not given.
    """

    size: BedSize
    variant: str = "faithful"
    species: str = "cherry"

    # Head stiles — measured from the 360.
    stile_thickness_in: float = 2.0
    stile_depth_foot_in: float = 3.375
    stile_depth_max_in: float = 6.0
    stile_depth_top_in: float = 3.25
    stile_widest_at_in: float = 16.0

    # Rails.
    rail_top_in: float = 15.0
    rail_height_in: float = 5.5
    rail_thickness_in: float = 1.0

    # Foot legs — measured from the 360.
    leg_thickness_in: float = 1.75
    leg_depth_top_in: float = 5.625
    leg_depth_foot_in: float = 2.75

    # Slat deck — published.
    slat_top_in: float = 14.0
    slat_width_in: float = 2.5
    slat_thickness_in: float = 0.75
    slat_gap_in: float = 2.0
    n_slats: int = 16
    ledger_w_in: float = 1.5
    ledger_t_in: float = 0.75

    # Headboard.
    headboard_gap_in: float = 9.75
    panel_thickness_in: float = 1.0
    panel_rake_deg: float = 10.0
    panel_reveal_in: float = 0.75
    panel_housing_in: float = 0.375

    centre_rail_h_in: float = 3.5
    centre_rail_t_in: float = 1.0
    centre_rail_cap_in: float = 3.0
    cap_thickness_in: float = 0.75

    split_slats: bool | None = None

    inventory: Inventory = field(default_factory=Inventory.load)

    def __post_init__(self) -> None:
        """Validate the variant, and decide whether slats must be split."""
        if self.variant not in ("faithful", "plywood"):
            raise ValueError(
                f"variant must be 'faithful' or 'plywood', got {self.variant!r}"
            )
        if self.split_slats is None:
            self.split_slats = not self._slat_fits_stock()

    def _slat_sheet(self):
        """Return the Baltic birch sheet a full-width slat would come from.

        Baltic birch is stocked in two sizes and only one of them is long
        enough for a queen slat, so the sheet is chosen by the part rather
        than by thickness.
        """
        return self.inventory.best_sheet_for(
            "plywood_baltic_birch",
            length_mm=self.slat_length,
            width_mm=inches(self.slat_width_in),
            part_grain="none",
            nominal_thickness="3/4",
        )

    def _slat_fits_stock(self) -> bool:
        """Return whether a full-width slat can be got out of the slat stock.

        Solid stock is long enough by definition.  Sheet goods are not: a
        queen slat is 62", which clears a 4x8 sheet but not a 5x5 one.
        """
        if self.variant != "plywood":
            return True
        sheet = self._slat_sheet()
        return sheet.fits(self.slat_length, inches(self.slat_width_in), "none")

    # ------------------------------------------------------------------
    # Material choices — the only thing the two variants disagree about
    # ------------------------------------------------------------------

    @property
    def panel_material(self) -> str:
        """Material of the headboard panel."""
        return "plywood_cherry" if self.variant == "plywood" else self.species

    @property
    def slat_material(self) -> str:
        """Material of the slats."""
        return "plywood_baltic_birch" if self.variant == "plywood" else self.species

    @property
    def panel_thickness_mm(self) -> float:
        """Headboard panel thickness, measured for sheet goods."""
        if self.variant == "plywood":
            return self.inventory.sheet_for("plywood_cherry", "3/4").thickness_mm
        return inches(self.panel_thickness_in)

    @property
    def slat_thickness_mm(self) -> float:
        """Slat thickness, measured for sheet goods."""
        if self.variant == "plywood":
            return self._slat_sheet().thickness_mm
        return inches(self.slat_thickness_in)

    # ------------------------------------------------------------------
    # Derived geometry
    # ------------------------------------------------------------------

    @property
    def overall_l(self) -> float:
        """Published overall length in mm."""
        return inches(self.size.overall_l_in)

    @property
    def overall_w(self) -> float:
        """Published overall width in mm."""
        return inches(self.size.overall_w_in)

    @property
    def overall_h(self) -> float:
        """Published overall height in mm."""
        return inches(self.size.overall_h_in)

    @property
    def deck_length(self) -> float:
        """Clear mattress length, stile face to foot rail, mm.

        The head stile is deep and runs the full height, so it eats into the
        deck.  The foot legs do not: they stop at the underside of the rails,
        and only the 1" foot rail intrudes at mattress level.  For a queen
        that leaves exactly the 80" a queen mattress needs, which is a good
        sign the measured stile depth is right.
        """
        return self.overall_l - inches(
            self.stile_depth_max_in + self.rail_thickness_in
        )

    @property
    def deck_width(self) -> float:
        """Clear width of the mattress opening, rail face to rail face, mm."""
        return self.overall_w - 2 * inches(self.rail_thickness_in)

    @property
    def slat_length(self) -> float:
        """Slat length: the full deck width, resting on a ledger at each end."""
        return self.deck_width

    @property
    def slat_bearing_z(self) -> float:
        """Height of the ledger top the slats rest on, mm."""
        return inches(self.slat_top_in) - self.slat_thickness_mm

    @property
    def rail_top_z(self) -> float:
        """Height of the top edge of the rails, mm."""
        return inches(self.rail_top_in)

    @property
    def rail_bottom_z(self) -> float:
        """Height of the bottom edge of the rails, mm."""
        return self.rail_top_z - inches(self.rail_height_in)

    @property
    def side_rail_length(self) -> float:
        """Side rail length, stile face to the foot end of the bed, mm.

        Longer than :attr:`deck_length`, because the rail runs right out to
        the foot end and wraps the corner with the foot rail; the mattress
        stops one rail thickness short of that.
        """
        return self.overall_l - inches(self.stile_depth_max_in)

    @property
    def deck_centre_y(self) -> float:
        """Mid-length of the mattress deck, mm.

        Between the stile's front face and the foot rail's inner face, which
        are not symmetric about the middle of the bed.
        """
        return (inches(self.rail_thickness_in) - inches(self.stile_depth_max_in)) / 2

    @property
    def rail_centre_y(self) -> float:
        """Mid-length of the side rails, mm.

        The rails are not centred on the bed: the head stile eats into the
        length at one end only.
        """
        return -inches(self.stile_depth_max_in) / 2

    @property
    def end_rail_length(self) -> float:
        """Foot rail length across the bed, between the side rails, mm."""
        return self.deck_width

    @property
    def headboard_panel_bottom_z(self) -> float:
        """Height of the lower edge of the headboard panel, mm.

        Derived from the two published numbers rather than measured: the slat
        tops at 14" and the 9-3/4" gap above them.
        """
        return inches(self.slat_top_in) + inches(self.headboard_gap_in)

    @property
    def headboard_panel_top_z(self) -> float:
        """Height of the top edge of the headboard panel, mm."""
        return self.overall_h - inches(self.panel_reveal_in)

    @property
    def headboard_panel_height(self) -> float:
        """Headboard panel height measured on its own face, mm.

        The panel leans, so the board is longer than the vertical distance it
        covers — cutting it to the vertical figure would leave the gap above
        the slats wider than the published 9-3/4".
        """
        rise = self.headboard_panel_top_z - self.headboard_panel_bottom_z
        return rise / math.cos(math.radians(self.panel_rake_deg))

    @property
    def headboard_panel_width(self) -> float:
        """Headboard panel width, housings in both stiles included, mm."""
        return (
            self.overall_w
            - 2 * inches(self.stile_thickness_in)
            + 2 * inches(self.panel_housing_in)
        )

    @property
    def slat_run(self) -> float:
        """Total length occupied by the slats and the gaps between them, mm."""
        return (
            self.n_slats * inches(self.slat_width_in)
            + (self.n_slats - 1) * inches(self.slat_gap_in)
        )

    @property
    def centre_rail_bearing(self) -> float:
        """Width of the surface the slats land on at the centre of the bed, mm."""
        if self.split_slats:
            return inches(self.centre_rail_cap_in)
        return inches(self.centre_rail_t_in)

    @property
    def centre_rail_span(self) -> float:
        """Clear slat span between a side rail and the centre support, mm."""
        return (self.deck_width - self.centre_rail_bearing) / 2.0

    @property
    def half_slat_length(self) -> float:
        """Length of one half-slat: ledger to the centre of the cap, mm."""
        return self.centre_rail_span + self.centre_rail_bearing / 2.0

    @property
    def slat_cut_length(self) -> float:
        """Length each slat is actually cut to, mm."""
        return self.half_slat_length if self.split_slats else self.slat_length

    # ------------------------------------------------------------------
    # Shaped profiles, measured off the 360
    # ------------------------------------------------------------------

    def stile_profile(self) -> list[tuple[float, float]]:
        """Return the head stile's outline, in mm, as (height, -depth).

        The origin is the head end of the bed at floor level.  Height runs
        along the part, because that is the way the grain runs and the way the
        cut list should read it; depth is negative because the bed's head is
        at +Y and the stile reaches back from it.

        The back edge is straight and vertical; the front edge is the measured
        curve — narrow at the floor, deepest at rail height, tapering to a
        rounded top.

        Returns
        -------
        list[tuple[float, float]]
            A closed polygon, first point not repeated.
        """
        h = self.size.overall_h_in
        widest = self.stile_widest_at_in
        foot, deep, top = (
            self.stile_depth_foot_in,
            self.stile_depth_max_in,
            self.stile_depth_top_in,
        )
        nose = 1.5
        shoulder = h - nose
        # Sampled rather than splined: a polygon's area is exact, and the
        # yield figures are computed from it.
        profile: list[tuple[float, float]] = [(0.0, 0.0), (0.0, -foot)]
        # Front edge, floor up to the widest point: a quick sweep out.
        for i in range(1, 9):
            f = i / 8
            profile.append((widest * f, -(foot + (deep - foot) * f**0.7)))
        # Front edge, widest point up to the nose: a long slow taper back.
        for i in range(1, 13):
            f = i / 12
            profile.append(
                (widest + (shoulder - widest) * f, -(deep + (top - deep) * f**1.3))
            )
        # The nose itself, a half ellipse from the front edge over to the back.
        for i in range(1, 13):
            angle = math.pi * i / 12
            profile.append(
                (shoulder + nose * math.sin(angle), -top / 2 * (1 + math.cos(angle)))
            )
        return _profile_mm(profile)

    def leg_profile(self) -> list[tuple[float, float]]:
        """Return a foot leg's outline, in mm, as (height, into the bed).

        The origin is the foot end of the bed at floor level.  The outer edge
        is vertical and the inner edge sweeps, so the leg is deep where it
        meets the rail and narrow at the floor.

        Returns
        -------
        list[tuple[float, float]]
            A closed polygon, first point not repeated.
        """
        top = self.rail_top_in - self.rail_height_in
        deep, foot = self.leg_depth_top_in, self.leg_depth_foot_in
        profile = [(0.0, 0.0), (top, 0.0), (top, deep)]
        for i in range(1, 9):
            f = i / 8
            profile.append(
                (top * (1 - f), deep + (foot - deep) * f**0.8)
            )
        return _profile_mm(profile)

    # ------------------------------------------------------------------
    # Assembly
    # ------------------------------------------------------------------

    def build(self) -> Compound:
        """Build the bed as a positioned build123d assembly.

        The assembly is laid out with +X across the bed, +Y toward the
        headboard, and +Z up from the floor, all centred on the bed's
        footprint.

        Returns
        -------
        build123d.Compound
            Every part of the bed, positioned.
        """
        rail_t = inches(self.rail_thickness_in)
        children: list[object] = []

        y_head = self.overall_l / 2
        y_foot = -y_head

        # -- Head stiles ------------------------------------------------
        # The profile is drawn from the head end going into the bed, so it is
        # mirrored about Y and placed with its back face on the head end.
        stile_t = inches(self.stile_thickness_in)
        x_stile = self.overall_w / 2 - stile_t / 2
        stile_depth = inches(self.stile_depth_max_in)
        for sign in (-1, 1):
            children.append(
                Pos(sign * x_stile, y_head - stile_depth / 2, self.overall_h / 2)
                * PROFILE_TO_BED
                * ShapedBoard(
                    profile=self.stile_profile(),
                    thickness_mm=stile_t,
                    material=self.species,
                    label="head_stile",
                    notes=(
                        "bandsawn to the profile and cleaned up on a spindle "
                        "sander; 10/4 stock, grain running up the stile"
                    ),
                )
            )

        # -- Foot legs --------------------------------------------------
        leg_t = inches(self.leg_thickness_in)
        x_leg = self.overall_w / 2 - leg_t / 2
        leg_depth = inches(self.leg_depth_top_in)
        for sign in (-1, 1):
            children.append(
                Pos(sign * x_leg, y_foot + leg_depth / 2, self.rail_bottom_z / 2)
                * PROFILE_TO_BED
                * ShapedBoard(
                    profile=self.leg_profile(),
                    thickness_mm=leg_t,
                    material=self.species,
                    label="foot_leg",
                    notes=(
                        "bandsawn; outer faces flush with the rails, top under "
                        "the rail rather than beside it"
                    ),
                )
            )

        # -- Rails ------------------------------------------------------
        rail_z = self.rail_top_z - inches(self.rail_height_in) / 2
        for sign in (-1, 1):
            children.append(
                Pos(sign * (self.overall_w / 2 - rail_t / 2), self.rail_centre_y, rail_z)
                * Rotation(0, 90, 90)
                * Board(
                    length_mm=self.side_rail_length,
                    thickness_mm=rail_t,
                    width_mm=inches(self.rail_height_in),
                    material=self.species,
                    label="side_rail",
                    notes=(
                        "metal bed-rail brackets into the stile and the leg; "
                        f"ledger screwed to the inner face, its top "
                        f"{self.slat_bearing_z / IN:.2f}\" off the floor"
                    ),
                )
            )
        children.append(
            Pos(0.0, y_foot + rail_t / 2, rail_z)
            * Rotation(90, 0, 0)
            * Board(
                length_mm=self.end_rail_length,
                thickness_mm=rail_t,
                width_mm=inches(self.rail_height_in),
                material=self.species,
                label="foot_rail",
                notes="the foot of the bed is this rail and nothing above it",
            )
        )

        # -- Ledgers ----------------------------------------------------
        ledger_w = inches(self.ledger_w_in)
        ledger_t = inches(self.ledger_t_in)
        ledger_x = self.overall_w / 2 - rail_t - ledger_w / 2
        for sign in (-1, 1):
            children.append(
                Pos(
                    sign * ledger_x,
                    self.deck_centre_y,
                    self.slat_bearing_z - ledger_t / 2,
                )
                * Rotation(0, 0, 90)
                * Board(
                    length_mm=self.deck_length,
                    thickness_mm=ledger_t,
                    width_mm=ledger_w,
                    material=self.species,
                    label="slat_ledger",
                    notes="screwed to the inner face of the rail; carries the deck",
                )
            )

        # -- Headboard panel --------------------------------------------
        children.append(self._placed_panel())

        # -- Slats and spacers -----------------------------------------
        y0 = self.deck_centre_y + self.slat_run / 2 - inches(self.slat_width_in) / 2
        pitch = inches(self.slat_width_in) + inches(self.slat_gap_in)
        slat_z = inches(self.slat_top_in) - self.slat_thickness_mm / 2
        for i in range(self.n_slats):
            y = y0 - i * pitch
            if self.split_slats:
                for sign in (-1, 1):
                    children.append(
                        Pos(sign * self.half_slat_length / 2, y, slat_z) * self._slat()
                    )
            else:
                children.append(Pos(0.0, y, slat_z) * self._slat())

        spacer_x = self.deck_width / 2 - ledger_w / 2
        for i in range(self.n_slats - 1):
            y = y0 - i * pitch - pitch / 2
            for sign in (-1, 1):
                children.append(
                    Pos(sign * spacer_x, y, slat_z)
                    * Rotation(0, 0, 90)
                    * Board(
                        length_mm=inches(self.slat_gap_in),
                        thickness_mm=self.slat_thickness_mm,
                        width_mm=ledger_w,
                        material=self.species,
                        label="slat_spacer",
                        grain_direction="length",
                        notes=(
                            "a block of slat stock dropped on the ledger between "
                            "slat ends; sets the published 2\" spacing"
                        ),
                    )
                )

        # -- Centre rail, bearing cap, and legs -------------------------
        cr_h = inches(self.centre_rail_h_in)
        cr_t = inches(self.centre_rail_t_in)
        cap_t = inches(self.cap_thickness_in) if self.split_slats else 0.0

        if self.split_slats:
            children.append(
                Pos(0.0, self.deck_centre_y, self.slat_bearing_z - cap_t / 2)
                * Rotation(0, 0, 90)
                * Board(
                    length_mm=self.deck_length,
                    thickness_mm=cap_t,
                    width_mm=inches(self.centre_rail_cap_in),
                    material=self.species,
                    label="centre_rail_cap",
                    notes=(
                        "screwed to the centre rail; gives each half-slat "
                        f"{self.centre_rail_cap_in / 2:g}\" of bearing"
                    ),
                )
            )

        children.append(
            Pos(0.0, self.deck_centre_y, self.slat_bearing_z - cap_t - cr_h / 2)
            * Rotation(0, 90, 90)
            * Board(
                length_mm=self.deck_length,
                thickness_mm=cr_t,
                width_mm=cr_h,
                material=self.species,
                label="centre_rail",
                notes="halves the slat span; carries the deck load to the floor",
            )
        )
        leg_h = self.slat_bearing_z - cap_t - cr_h
        n_legs = 2 if self.deck_length > inches(60) else 1
        for i in range(n_legs):
            y = self.deck_centre_y + (
                0.0
                if n_legs == 1
                else (-1 if i == 0 else 1) * self.deck_length / 4
            )
            children.append(
                Pos(0.0, y, leg_h / 2)
                * Rotation(0, 90, 0)
                * Board(
                    length_mm=leg_h,
                    thickness_mm=cr_t,
                    width_mm=inches(self.leg_thickness_in),
                    material=self.species,
                    label="centre_rail_leg",
                )
            )

        return Compound(children=children, label=f"mysa_{self.size.name}_{self.variant}")

    def _placed_panel(self):
        """Return the headboard panel, raked back and positioned."""
        panel = self._headboard_panel()
        z_mid = (self.headboard_panel_bottom_z + self.headboard_panel_top_z) / 2
        # The panel leans back, so its face sits against the stiles' front
        # edge at mid height; the stile is deepest lower down, which is what
        # gives the headboard its rake.
        y_mid = self.overall_l / 2 - inches(self.stile_depth_max_in) * 0.72
        return (
            Pos(0.0, y_mid, z_mid)
            * Rotation(90 - self.panel_rake_deg, 0, 0)
            * panel
        )

    def _headboard_panel(self):
        """Return the headboard panel as a :class:`Board` or :class:`Panel`."""
        if self.variant == "plywood":
            return Panel(
                length_mm=self.headboard_panel_width,
                width_mm=self.headboard_panel_height,
                thickness_mm=self.panel_thickness_mm,
                material="plywood_cherry",
                label="headboard_panel",
                grain_direction="length",
                notes=(
                    "face grain runs across the bed; glue into the housing — "
                    "plywood does not move seasonally"
                ),
            )
        return Board(
            length_mm=self.headboard_panel_width,
            width_mm=self.headboard_panel_height,
            thickness_mm=self.panel_thickness_mm,
            material=self.species,
            label="headboard_panel",
            grain_direction="length",
            notes=(
                "glue-up; housed in the stiles, fixed at the centre only so it "
                "can move across its width"
            ),
        )

    def _slat(self):
        """Return one slat as a :class:`Board` or :class:`Panel`."""
        label = "half_slat" if self.split_slats else "slat"
        if self.variant == "plywood":
            return Panel(
                length_mm=self.slat_cut_length,
                width_mm=inches(self.slat_width_in),
                thickness_mm=self.slat_thickness_mm,
                material="plywood_baltic_birch",
                label=label,
                grain_direction="none",
                notes=(
                    "face grain along the span where the sheet allows; "
                    "butts over the centre cap"
                    if self.split_slats
                    else "face grain along the span where the sheet allows"
                ),
            )
        return Board(
            length_mm=self.slat_cut_length,
            width_mm=inches(self.slat_width_in),
            thickness_mm=self.slat_thickness_mm,
            material=self.species,
            label=label,
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
                actual_l_mm=bb.size.Y,
                actual_w_mm=bb.size.X,
                actual_h_mm=bb.size.Z,
                published_l_mm=self.overall_l,
                published_w_mm=self.overall_w,
                published_h_mm=self.overall_h,
            )
        )

        side = (self.deck_width - inches(self.size.mattress_w_in)) / 2
        end = (self.deck_length - inches(self.size.mattress_l_in)) / 2
        report.extend(
            check_clearance(
                "mattress side clearance",
                side,
                3.0,
                19.0,
                tight_note="mattress may bind",
                loose_note="mattress will slide and expose the rail",
            )
        )
        report.extend(
            check_clearance(
                "mattress end clearance",
                end,
                0.0,
                25.0,
                tight_note="mattress may bind",
                loose_note="mattress will slide and expose the rail",
            )
        )

        report.extend(check_material_suitability(parts, self.inventory))
        report.extend(check_sheet_fit(parts, self.inventory))
        report.extend(check_thickness_substitution(parts, self.inventory))

        report.extend(
            check_slat_deflection(
                material=self.slat_material,
                span_mm=self.centre_rail_span,
                slat_width_mm=inches(self.slat_width_in),
                slat_thickness_mm=self.slat_thickness_mm,
                n_slats=self.n_slats,
            )
        )

        report.findings.append(
            Finding(
                Severity.INFO,
                "headboard",
                f"the headboard rakes back {self.panel_rake_deg:g}°; its lower "
                f"edge is {self.headboard_panel_bottom_z / IN:.2f}\" off the "
                f"floor, the published {self.headboard_gap_in:g}\" above the "
                "slat tops",
            )
        )

        if self.split_slats:
            report.extend(self._split_slat_findings())

        slack = self.deck_length - self.slat_run
        report.findings.append(
            Finding(
                Severity.INFO,
                "slats",
                f"{self.n_slats} slats at {self.slat_gap_in:g}\" spacing occupy "
                f"{self.slat_run / IN:.1f}\" of the {self.deck_length / IN:.1f}\" "
                f"deck — {slack / IN / 2:.1f}\" bare at the head and foot",
            )
        )
        if slack < 0:
            report.findings.append(
                Finding(
                    Severity.ERROR,
                    "slats",
                    f"{self.n_slats} slats do not fit the {self.deck_length / IN:.1f}\" "
                    "deck at this spacing",
                )
            )
        return report

    def _split_slat_findings(self) -> list[Finding]:
        """Return the findings that explain a split slat deck."""
        findings: list[Finding] = []
        split_geometry = (
            f"slats are split into {self.n_slats * 2} halves of "
            f"{self.half_slat_length / IN:.2f}\" butting over a "
            f"{self.centre_rail_cap_in:g}\" centre cap"
        )
        # The split is only *forced* when no stocked sheet takes a full-width
        # slat.  Setting split_slats by hand, or splitting a solid-wood bed,
        # is a choice — and reporting it as a stock limitation would name a
        # sheet that has nothing to do with it.
        if self._slat_fits_stock():
            sheet_note = ""
            if self.variant == "plywood":
                sheet = self._slat_sheet()
                sheet_note = (
                    f" — a {self.slat_length / IN:.1f}\" slat fits the stocked "
                    f"{sheet.material} {sheet.size_label} sheet whole"
                )
            findings.append(
                Finding(
                    Severity.WARN,
                    "slats",
                    f"slats are split by request, not by necessity"
                    f"{sheet_note}. {split_geometry}",
                )
            )
            return findings

        sheet = self._slat_sheet()
        findings.append(
            Finding(
                Severity.WARN,
                "slats",
                f"a full-width slat is {self.slat_length / IN:.1f}\" but the "
                f"largest stocked {sheet.material} sheet is "
                f"{sheet.size_label} — {split_geometry}",
            )
        )
        others = alternative_sheets(
            self.inventory,
            self.slat_length,
            inches(self.slat_width_in),
            grain_direction="none",
            exclude_material=sheet.material,
            reference_thickness_mm=sheet.thickness_mm,
        )
        if others:
            findings.append(
                Finding(
                    Severity.INFO,
                    "slats",
                    "full-length slats would come whole out of: " + "; ".join(others),
                )
            )
        return findings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def run(size_name: str, variant: str, outdir: Path) -> CheckReport:
    """Build one bed, write its cut list and diagrams, and print the report.

    Parameters
    ----------
    size_name : str
        Key into :data:`SIZES`.
    variant : str
        ``"faithful"`` or ``"plywood"``.
    outdir : Path
        Directory for the generated CSV, Markdown, and PDF files.

    Returns
    -------
    CheckReport
        The design-check findings.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    bed = MysaBed(size=SIZES[size_name], variant=variant)
    assembly = bed.build()
    parts = extract(assembly)

    stem = f"mysa_{size_name}_{variant}"
    print(f"\n{'=' * 78}\n  Mysa sleigh bed — {size_name}, {variant}\n{'=' * 78}")

    df = render_cut_list(
        parts,
        output_csv=outdir / f"{stem}_cutlist.csv",
        output_md=outdir / f"{stem}_cutlist.md",
    )
    print(df.to_string(index=False))

    report = bed.check(assembly, parts)
    print(f"\n-- design checks {'-' * 61}")
    print(report.to_text())

    # Kept out of the design report on purpose: an undated price is a problem
    # with the quote, not with the joinery, and it should not make a buildable
    # bed report an error.
    print(f"\n-- prices {'-' * 68}")
    print(CheckReport().extend(check_price_provenance(bed.inventory, parts)).to_text())

    sheet_materials = {s.material for s in bed.inventory.sheet_goods}
    solid = [p for p in parts if p.material not in sheet_materials]
    sheet = [p for p in parts if p.material in sheet_materials]

    if solid:
        print(f"\n-- {bed.species} to buy {'-' * 55}")
        plan = nest_hardwood(solid, bed.inventory, bed.species)
        print(plan.to_text())
        render_board_diagram(plan, output_pdf=outdir / f"{stem}_boards.pdf")

    if sheet:
        print(f"\n-- sheet goods {'-' * 63}")
        packed = pack_by_material(sheet, bed.inventory)
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
        summary = sheet_cost_summary(packed, bed.inventory)
        print(f"  {'total':<28s} {summary.to_text()}")

    render_assembly(
        assembly,
        output_png=outdir / f"{stem}.png",
        title=f"Mysa sleigh bed — {size_name}, {variant}",
    )
    export_assembly(
        assembly,
        output_step=outdir / f"{stem}.step",
        output_stl=outdir / f"{stem}.stl",
    )

    print(f"\nWrote cut list, diagrams, views and CAD export to {outdir}/")
    return report


def _spec(size_name: str, variant: str) -> ProjectSpec:
    """Return the gallery entry for one size and variant.

    Only the queen is registered.  Five sizes times two variants is ten pages
    that differ in nothing but their numbers, and a gallery of near-identical
    cards teaches less than two that differ in something real.
    """
    bed = MysaBed(size=SIZES[size_name], variant=variant)
    material = (
        "Solid cherry throughout, as sold."
        if variant == "faithful"
        else "Cherry-plywood headboard panel and Baltic birch slats."
    )
    return ProjectSpec(
        slug=f"mysa-bed-{size_name}-{variant}",
        name=f"Mysa sleigh bed — {size_name}, {variant}",
        summary=(
            f"{bed.size.overall_l_in:g}\"L x {bed.size.overall_w_in:g}\"W x "
            f"{bed.size.overall_h_in:g}\"H platform bed: bandsawn stiles, a "
            f"raked slab headboard, no footboard. {material}"
        ),
        species=bed.species,
        source_url="https://www.chiltons.com/products/mysa-sleigh-bed-cherry",
        build=bed.build,
        check=bed.check,
        inventory=bed.inventory,
        notes=(
            "Geometry measured off the manufacturer's 360 viewer, not inferred "
            "from the listing's prose — which got it wrong."
        ),
        tags=["bed", variant],
    )


#: Projects this module contributes to the gallery.
PROJECTS: list[ProjectSpec] = [
    _spec("queen", "faithful"),
    _spec("queen", "plywood"),
]


def main() -> None:
    """Parse arguments and build the requested bed or beds."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--size", choices=sorted(SIZES), default="queen")
    parser.add_argument(
        "--variant", choices=["faithful", "plywood", "both"], default="faithful"
    )
    parser.add_argument("--outdir", type=Path, default=Path("build"))
    args = parser.parse_args()

    variants = ["faithful", "plywood"] if args.variant == "both" else [args.variant]
    for variant in variants:
        run(args.size, variant, args.outdir)


if __name__ == "__main__":
    main()
