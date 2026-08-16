"""Mysa sleigh bed — a reproduction of the Chilton Furniture design, and a variant.

Source
------
https://www.chiltons.com/products/mysa-sleigh-bed-cherry

Published specification, reproduced here as the design targets::

    Twin            81"L x 44"W x 40"H      Full   81"L x 59"W x 40"H
    Queen           87"L x 64"W x 40"H      King   87"L x 83"W x 40"H
    California King 91"L x 79"W x 40"H

    Headboard gap to platform  9-3/4"
    Footboard height           15"
    Rails                      4-1/2"H x 1"D
    Slats                      16, 2-1/2" wide x 3/4" thick, spaced 2" apart
                               with wood spacers, 14" off floor, 1/4" deep on rail
    Centre rail lengthwise; metal hardware secures rails to posts
    Recommended mattress height 10"

Two variants are modelled:

``faithful``
    Solid cherry throughout, as sold.

``plywood``
    Headboard panel in 3/4" cherry plywood, slats in Baltic birch.  Both
    substitutions change more than the material name — see
    :func:`woodshop.checks.check_thickness_substitution` and
    :func:`woodshop.checks.check_sheet_fit`, which this script runs.

What is inferred rather than published
--------------------------------------
The listing gives an envelope and a handful of section sizes, not a cutting
list.  Everything below is derived from those numbers, and every derived
number is stated here so it can be argued with:

* **Posts are 1-3/4" square.** The envelope is measured across the posts.
  8/4 cherry surfaces to 1-3/4", so a true 2" post would need 10/4 stock or a
  lamination; 1-3/4" is the size that falls out of normal stock.
* **Side rails sit flush with the outside faces of the posts**, which makes
  the mattress opening ``overall_width - 2 x rail_thickness``.
* **Rail tops are level with the footboard at 15"**, so the 4-1/2" rail
  occupies 10-1/2" to 15" off the floor.  The 1/4"-deep slat ledge is a rabbet
  in the rail's inner face, its shoulder at 13-1/4" so the 3/4" slats land at
  the published 14".
* **The headboard is a frame and panel**: a 3" top rail flush with the post
  tops, a 2-1/2" bottom rail whose lower edge is the published 9-3/4" above
  the slats, and a panel between them housed 3/8" into grooves.
* **The footboard is the foot rail alone** at 15", matching both the published
  footboard height and the rail height. Nothing is published that would put
  anything above it.
* **Spacers** are short blocks of slat stock dropped into the rail rabbet
  between slat ends to hold the published 2" spacing.

Run it
------
::

    uv run python projects/mysa_bed.py --size queen --variant faithful
    uv run python projects/mysa_bed.py --size queen --variant plywood
    uv run python projects/mysa_bed.py --size queen --variant both --outdir build
"""

from __future__ import annotations

import argparse
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
    check_sheet_fit,
    check_slat_deflection,
    check_thickness_substitution,
)
from woodshop.cutlist.extract import CutPart, extract
from woodshop.cutlist.hardwood import nest_hardwood
from woodshop.cutlist.optimize_2d import pack_by_material
from woodshop.cutlist.render import render_cut_list, render_sheet_diagram
from woodshop.inventory import Inventory
from woodshop.parts import Board, Panel

IN = 25.4


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
    post_in : float, optional
        Post cross-section, square, default 1.75".
    rail_thickness_in, rail_height_in : float, optional
        Side- and footboard-rail section, default 1" x 4-1/2".
    footboard_height_in : float, optional
        Top of the footboard off the floor, default 15".
    slat_top_in : float, optional
        Top face of the slats off the floor, default 14".
    slat_width_in, slat_thickness_in : float, optional
        Slat section, default 2-1/2" x 3/4".
    slat_gap_in : float, optional
        Clear gap between slats, default 2".
    n_slats : int, optional
        Number of slats, default 16.
    ledge_depth_in : float, optional
        Depth of the rabbet the slat ends sit in, default 1/4".
    headboard_gap_in : float, optional
        Clear gap between the slat tops and the headboard's lower edge,
        default 9-3/4".
    hb_top_rail_in, hb_bottom_rail_in : float, optional
        Headboard frame rail widths, default 3" and 2-1/2".
    groove_depth_in : float, optional
        Depth the headboard panel is housed into the frame, default 3/8".
    panel_thickness_in : float, optional
        Solid headboard panel thickness, default 3/4".  Ignored in the
        ``plywood`` variant, which uses the real sheet thickness.
    tenon_in : float, optional
        Tenon length on the headboard and footboard rails, default 1".
    centre_rail_h_in, centre_rail_t_in : float, optional
        Centre support rail section, default 3-1/2" x 1".
    inventory : Inventory, optional
        Stock inventory used for real sheet thicknesses.  Loaded from
        ``stock.yaml`` if not given.
    """

    size: BedSize
    variant: str = "faithful"
    species: str = "cherry"

    post_in: float = 1.75
    rail_thickness_in: float = 1.0
    rail_height_in: float = 4.5
    footboard_height_in: float = 15.0

    slat_top_in: float = 14.0
    slat_width_in: float = 2.5
    slat_thickness_in: float = 0.75
    slat_gap_in: float = 2.0
    n_slats: int = 16
    ledge_depth_in: float = 0.25

    headboard_gap_in: float = 9.75
    hb_top_rail_in: float = 3.0
    hb_bottom_rail_in: float = 2.5
    groove_depth_in: float = 0.375
    panel_thickness_in: float = 0.75
    tenon_in: float = 1.0

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

    def _slat_fits_stock(self) -> bool:
        """Return whether a full-width slat can be got out of the slat stock.

        Solid stock is long enough by definition.  Sheet goods are not: Baltic
        birch comes in 60" x 60" sheets, and a queen slat is 62-1/2".
        """
        if self.variant != "plywood":
            return True
        sheet = self.inventory.sheet_for("plywood_baltic_birch", "3/4")
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
            return self.inventory.sheet_for("plywood_baltic_birch", "3/4").thickness_mm
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
        """Clear length of the mattress opening, post face to post face, mm."""
        return self.overall_l - 2 * inches(self.post_in)

    @property
    def deck_width(self) -> float:
        """Clear width of the mattress opening, rail face to rail face, mm."""
        return self.overall_w - 2 * inches(self.rail_thickness_in)

    @property
    def slat_length(self) -> float:
        """Slat length: the deck width plus the rabbet at each end, mm."""
        return self.deck_width + 2 * inches(self.ledge_depth_in)

    @property
    def slat_bearing_z(self) -> float:
        """Height of the rabbet shoulder the slats rest on, mm."""
        return inches(self.slat_top_in) - self.slat_thickness_mm

    @property
    def rail_top_z(self) -> float:
        """Height of the top edge of the side and footboard rails, mm."""
        return inches(self.footboard_height_in)

    @property
    def frame_rail_length(self) -> float:
        """Headboard and footboard rail length including tenons, mm."""
        return (
            self.overall_w - 2 * inches(self.post_in) + 2 * inches(self.tenon_in)
        )

    @property
    def headboard_panel_bottom_z(self) -> float:
        """Height of the lower edge of the headboard assembly, mm."""
        return inches(self.slat_top_in) + inches(self.headboard_gap_in)

    @property
    def headboard_panel_height(self) -> float:
        """Headboard panel height including the tongues in both grooves, mm."""
        clear = (
            self.overall_h
            - inches(self.hb_top_rail_in)
            - (self.headboard_panel_bottom_z + inches(self.hb_bottom_rail_in))
        )
        return clear + 2 * inches(self.groove_depth_in)

    @property
    def headboard_panel_width(self) -> float:
        """Headboard panel width including the tongues in both grooves, mm."""
        return (
            self.overall_w
            - 2 * inches(self.post_in)
            + 2 * inches(self.groove_depth_in)
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
        """Length of one half-slat: side rail rabbet to centre of the cap, mm."""
        return (
            self.centre_rail_span
            + inches(self.ledge_depth_in)
            + self.centre_rail_bearing / 2.0
        )

    @property
    def slat_cut_length(self) -> float:
        """Length each slat is actually cut to, mm."""
        return self.half_slat_length if self.split_slats else self.slat_length

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
        post = inches(self.post_in)
        rail_t = inches(self.rail_thickness_in)
        children: list[object] = []

        x_post = self.overall_w / 2 - post / 2
        y_head = self.overall_l / 2 - post / 2
        y_foot = -y_head

        # -- Posts -----------------------------------------------------
        # Rotation(0, 90, 0) stands a Board on end: local length -> +Z.
        for sign in (-1, 1):
            children.append(
                Pos(sign * x_post, y_head, self.overall_h / 2)
                * Rotation(0, 90, 0)
                * Board(
                    length_mm=self.overall_h,
                    thickness_mm=post,
                    width_mm=post,
                    material=self.species,
                    label="head_post",
                    notes="8/4 stock, milled square",
                )
            )
            children.append(
                Pos(sign * x_post, y_foot, inches(self.footboard_height_in) / 2)
                * Rotation(0, 90, 0)
                * Board(
                    length_mm=inches(self.footboard_height_in),
                    thickness_mm=post,
                    width_mm=post,
                    material=self.species,
                    label="foot_post",
                    notes="8/4 stock, milled square",
                )
            )

        # -- Side rails ------------------------------------------------
        # Rotation(0, 90, 90) lays a Board on edge running along +Y.
        rail_z = self.rail_top_z - inches(self.rail_height_in) / 2
        for sign in (-1, 1):
            children.append(
                Pos(sign * (self.overall_w / 2 - rail_t / 2), 0.0, rail_z)
                * Rotation(0, 90, 90)
                * Board(
                    length_mm=self.deck_length,
                    thickness_mm=rail_t,
                    width_mm=inches(self.rail_height_in),
                    material=self.species,
                    label="side_rail",
                    notes=(
                        f'rabbet {self.ledge_depth_in}" deep x '
                        f"{self.slat_thickness_mm / IN:.3f}\" tall on the inner "
                        "face, shoulder "
                        f"{self.slat_bearing_z / IN:.2f}\" off the floor"
                    ),
                )
            )

        # -- Footboard rail --------------------------------------------
        # Rotation(90, 0, 0) stands a Board on edge running along +X.
        children.append(
            Pos(0.0, y_foot, rail_z)
            * Rotation(90, 0, 0)
            * Board(
                length_mm=self.frame_rail_length,
                thickness_mm=rail_t,
                width_mm=inches(self.rail_height_in),
                material=self.species,
                label="footboard_rail",
                notes=f'{self.tenon_in}" tenon each end',
            )
        )

        # -- Headboard frame and panel ---------------------------------
        hb_top_z = self.overall_h - inches(self.hb_top_rail_in) / 2
        children.append(
            Pos(0.0, y_head, hb_top_z)
            * Rotation(90, 0, 0)
            * Board(
                length_mm=self.frame_rail_length,
                thickness_mm=rail_t,
                width_mm=inches(self.hb_top_rail_in),
                material=self.species,
                label="headboard_top_rail",
                notes=(
                    f'{self.tenon_in}" tenon each end; '
                    f'{self.groove_depth_in}" panel groove'
                ),
            )
        )
        hb_bottom_z = self.headboard_panel_bottom_z + inches(self.hb_bottom_rail_in) / 2
        children.append(
            Pos(0.0, y_head, hb_bottom_z)
            * Rotation(90, 0, 0)
            * Board(
                length_mm=self.frame_rail_length,
                thickness_mm=rail_t,
                width_mm=inches(self.hb_bottom_rail_in),
                material=self.species,
                label="headboard_bottom_rail",
                notes=(
                    f'{self.tenon_in}" tenon each end; '
                    f'{self.groove_depth_in}" panel groove'
                ),
            )
        )

        panel_z = (
            self.headboard_panel_bottom_z
            + inches(self.hb_bottom_rail_in)
            + (self.headboard_panel_height - 2 * inches(self.groove_depth_in)) / 2
        )
        children.append(
            Pos(0.0, y_head, panel_z)
            * Rotation(90, 0, 0)
            * self._headboard_panel()
        )

        # -- Slats and spacers -----------------------------------------
        y0 = self.slat_run / 2 - inches(self.slat_width_in) / 2
        pitch = inches(self.slat_width_in) + inches(self.slat_gap_in)
        slat_z = inches(self.slat_top_in) - self.slat_thickness_mm / 2
        for i in range(self.n_slats):
            y = y0 - i * pitch
            if self.split_slats:
                # Two half-slats meeting over the centre cap, which carries
                # the butt joint.
                for sign in (-1, 1):
                    children.append(
                        Pos(sign * self.half_slat_length / 2, y, slat_z) * self._slat()
                    )
            else:
                children.append(Pos(0.0, y, slat_z) * self._slat())

        # Spacers sit in the rail rabbet between slat ends, both sides.
        spacer_x = self.deck_width / 2 + inches(self.ledge_depth_in) / 2
        for i in range(self.n_slats - 1):
            y = y0 - i * pitch - pitch / 2
            for sign in (-1, 1):
                children.append(
                    Pos(sign * spacer_x, y, slat_z)
                    * Rotation(0, 90, 90)
                    * Board(
                        length_mm=inches(self.slat_gap_in),
                        thickness_mm=inches(self.ledge_depth_in),
                        width_mm=self.slat_thickness_mm,
                        material=self.species,
                        label="slat_spacer",
                        grain_direction="length",
                        notes="cut from offcuts; sets the 2\" slat spacing",
                    )
                )

        # -- Centre rail, bearing cap, and legs -------------------------
        cr_h = inches(self.centre_rail_h_in)
        cr_t = inches(self.centre_rail_t_in)
        cap_t = inches(self.cap_thickness_in) if self.split_slats else 0.0

        if self.split_slats:
            # Split slats butt over the centre of the bed, so the centre rail
            # needs a wider landing than its own 1" edge.
            children.append(
                Pos(0.0, 0.0, self.slat_bearing_z - cap_t / 2)
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
            Pos(0.0, 0.0, self.slat_bearing_z - cap_t - cr_h / 2)
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
            y = (
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
                    width_mm=inches(self.post_in),
                    material=self.species,
                    label="centre_rail_leg",
                )
            )

        return Compound(children=children, label=f"mysa_{self.size.name}_{self.variant}")

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
                    "face grain runs across the bed; glue into the groove — "
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
                "glue-up; float in the groove, glued at the centre only, so it "
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
        report.extend(check_clearance("mattress side clearance", side, 3.0, 19.0))
        report.extend(check_clearance("mattress end clearance", end, 3.0, 19.0))

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

        if self.split_slats:
            sheet = self.inventory.sheet_for("plywood_baltic_birch", "3/4")
            report.findings.append(
                Finding(
                    Severity.WARN,
                    "slats",
                    f"a full-width slat is {self.slat_length / IN:.1f}\" but "
                    f"{sheet.material} sheets are only "
                    f"{sheet.sheet_height_in:g}\" — slats are split into "
                    f"{self.n_slats * 2} halves of "
                    f"{self.half_slat_length / IN:.2f}\" butting over a "
                    f"{self.centre_rail_cap_in:g}\" centre cap",
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
                report.findings.append(
                    Finding(
                        Severity.INFO,
                        "slats",
                        "full-length slats would come whole out of: "
                        + "; ".join(others),
                    )
                )

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

    # Solid stock: group by cross-section and choose stock lengths.
    sheet_materials = {s.material for s in bed.inventory.sheet_goods}
    solid = [p for p in parts if p.material not in sheet_materials]
    sheet = [p for p in parts if p.material in sheet_materials]

    if solid:
        # Hardwood is nested in two dimensions — parts are ripped out of a
        # board's width as well as its length — and bought by the board foot.
        print(f"\n-- {bed.species} to buy {'-' * 55}")
        print(nest_hardwood(solid, bed.inventory, bed.species).to_text())

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
                # Thickness labels contain a slash ("3/4"), which is not a
                # filename.
                slug = key.replace(" ", "_").replace("/", "-")
                render_sheet_diagram(
                    res,
                    sheet_w_mm=res.sheet_w_mm,
                    sheet_h_mm=res.sheet_h_mm,
                    output_pdf=outdir / f"{stem}_{slug}_sheets.pdf",
                )

    print(f"\nWrote cut list and diagrams to {outdir}/")
    return report


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
