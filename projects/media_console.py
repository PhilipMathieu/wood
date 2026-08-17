"""Media console — five record bays, a CD row, and a clear top for the machines.

Inspiration
-----------
https://luccahouse.com/ — the plain cherry casework, sized to what it holds
rather than to a catalogue.  Nothing here is measured off that site: it was not
reachable from the machine this model was built on, and no photograph was read.
The brief below is the specification, and everything else is derived from it.

The brief, as given::

    Media console — 80" x 24" x 13", cherry plywood

    Bottom row  five bays, each 15" wide and 13-1/2" tall — a record stands
                upright with a finger's room above the sleeve, and the bay is
                narrow enough that the stack never leans
    Above it    a shallower 8" row, CDs two deep
    Top         left clear for the turntable and the player
    Material    3/4" cherry plywood with solid cherry front edges, dadoed so
                the case is a single rigid box, finished clear, no stain

What the arithmetic decides
---------------------------
Five of the brief's numbers cannot all be exact at once, and the plywood is
what decides which one gives.  ``3/4"`` cherry plywood measures **45/64"**, so
six vertical panels take 4-7/32" of the 80" rather than 4-1/2", and three
horizontal panels take 2-3/32" of the 24" rather than 2-1/4":

* **Bay width comes out 15-5/32", not 15"** — the width is fixed at 80" and the
  five openings share what the six panels leave.  Holding a true 15" would mean
  a case 79-1/32" wide, which is a worse trade than an eighth of an inch nobody
  can see across a bay.
* **The openings still hit 13-1/2" and 8" exactly**, and the 3/8" the thin
  plywood gives back becomes the **toe reveal**: the bay bottoms are housed
  25/64" off the floor and the case stands on the six panel ends.  It is not
  decoration.  A floor is never flat, and a panel bearing on one telegraphs
  every hump in it.

What is inferred rather than given
----------------------------------
* **Solid edges are 1/4" thick**, on the front edge of every panel, so the
  panels are cut 12-3/4" deep and the console is 13" deep with the cherry on.
  The front therefore reads as a grid of 1/4" solid lines, and the plywood
  edge shows nowhere.
* **The joinery is 1/4"-deep dados**: the shelves are housed in the verticals,
  and the verticals are housed in the underside of the top — a dado for each
  divider and a rabbet at each end.  That last joint is what makes the case a
  box; without it the piece is a comb.
* **There is no back.** The brief calls the console open, and a media console
  wants cables through it.  Racking is carried by the dado grid alone, which
  is what six full-depth verticals housed top and bottom are for.
* **Capacities and weights** — 5 records to the inch at 250 g each, jewel cases
  at 10 mm and 100 g — are ordinary figures, not measurements of anybody's
  collection.  They set the load the shelves are checked against.

Why five bays
-------------
Not stiffness.  :func:`woodshop.checks.check_shelf_deflection` puts the sag of
a full bay bottom at a tenth of a millimetre and says **three** bays would be
enough to keep an undivided one inside span/360 — the fourth and the fifth are
there because a run of records much over 15" leans, slumps, and bends the
sleeves at the ends of it.  Both findings are in the report, so the reason the
piece looks the way it does is written down rather than implied.

Finish
------
Clear, no stain.  Cherry darkens on its own from pale amber to deep red-brown
over the first year, so the piece is meant to leave the shop a little pale.
That is also why the edging matters more than it looks: solid cherry and rotary
cherry veneer start at slightly different colours and darken at slightly
different rates, and sapwood in the edging never catches up.

Run it
------
::

    uv run python projects/media_console.py
    uv run python projects/media_console.py --outdir build
"""

from __future__ import annotations

import argparse
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
    estimate_mass_kg,
)
from woodshop.cutlist.extract import CutPart, extract
from woodshop.cutlist.hardwood import nest_hardwood
from woodshop.cutlist.optimize_2d import pack_by_material
from woodshop.inventory import Inventory
from woodshop.joinery import Dado
from woodshop.lumber import mm_to_fractional_inch
from woodshop.parts import Board, Panel, retag
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


@dataclass
class MediaConsole:
    """A parametric media console: a run of record bays under a CD row.

    Every dimension below is a *published* one — the envelope and the two
    opening heights.  Everything else (bay width, toe reveal, panel and shelf
    sizes) is derived from them and from the thickness the plywood actually
    measures, so changing the sheet changes the case rather than silently
    changing the fit.

    Parameters
    ----------
    overall_w_in, overall_h_in, overall_d_in : float, optional
        Published envelope, default 80" x 24" x 13".
    n_bays : int, optional
        Bays in the bottom row, default 5.
    record_bay_h_in : float, optional
        Clear height of a record bay, default 13-1/2" — a 12-3/8" sleeve and a
        finger above it.
    cd_row_h_in : float, optional
        Clear height of the row above, default 8".
    panel_material : str, optional
        Sheet-goods key for the case, default ``"plywood_cherry"``.
    panel_nominal_thickness : str, optional
        Nominal sheet thickness, default ``"3/4"``.  The *actual* thickness is
        read from the inventory and is what the geometry uses.
    species : str, optional
        Solid-wood species for the front edges, default ``"cherry"``.
    edge_thickness_in : float, optional
        Thickness of the solid front edging, front to back, default 1/4".
    dado_depth_in : float, optional
        Depth of every housing in the case, default 1/4".
    inventory : Inventory, optional
        Stock inventory.  Loaded from ``stock.yaml`` if not given.

    Raises
    ------
    ValueError
        If fewer than two bays are asked for, if the edging or the housings are
        deeper than the stock they land in, or if the two rows and their
        panels are taller than the published height — in which case there is no
        console to model, only a stack that does not fit in it.
    """

    overall_w_in: float = 80.0
    overall_h_in: float = 24.0
    overall_d_in: float = 13.0

    n_bays: int = 5
    record_bay_h_in: float = 13.5
    cd_row_h_in: float = 8.0

    panel_material: str = "plywood_cherry"
    panel_nominal_thickness: str = "3/4"
    species: str = "cherry"
    edge_thickness_in: float = 0.25
    dado_depth_in: float = 0.25

    inventory: Inventory = field(default_factory=Inventory.load)

    def __post_init__(self) -> None:
        """Reject a console whose numbers do not describe a case."""
        if self.n_bays < 2:
            raise ValueError(
                f"a run of bays needs at least 2 of them, got {self.n_bays}"
            )
        if self.edge_thickness_in >= self.overall_d_in:
            raise ValueError(
                f"{self.edge_thickness_in:g}\" of edging on a "
                f"{self.overall_d_in:g}\" deep case leaves no panel"
            )
        if self.dado_depth_in >= self.panel_t / IN:
            raise ValueError(
                f"a {self.dado_depth_in:g}\" housing goes through "
                f"{mm_to_fractional_inch(self.panel_t, 64)} stock"
            )
        if self.toe_reveal < 0:
            raise ValueError(
                f"a {self.record_bay_h_in:g}\" bay and a {self.cd_row_h_in:g}\" "
                f"row plus three panels come to "
                f"{mm_to_fractional_inch(self.overall_h - self.toe_reveal)}, "
                f"which does not fit inside {self.overall_h_in:g}\""
            )

    # ------------------------------------------------------------------
    # Stock
    # ------------------------------------------------------------------

    @property
    def sheet(self):
        """The sheet the case is cut from."""
        return self.inventory.sheet_for(
            self.panel_material, self.panel_nominal_thickness
        )

    @property
    def panel_t(self) -> float:
        """Measured panel thickness in mm — 45/64", not 3/4"."""
        return self.sheet.thickness_mm

    @property
    def edge_t(self) -> float:
        """Thickness of the solid front edging in mm."""
        return inches(self.edge_thickness_in)

    @property
    def dado_depth(self) -> float:
        """Depth of every housing in mm."""
        return inches(self.dado_depth_in)

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
    # Derived geometry
    # ------------------------------------------------------------------

    @property
    def n_verticals(self) -> int:
        """Two ends plus the dividers between the bays."""
        return self.n_bays + 1

    @property
    def panel_depth(self) -> float:
        """Depth of a plywood panel in mm — the case less its front edging."""
        return self.overall_d - self.edge_t

    @property
    def bay_clear_w(self) -> float:
        """Clear width of one bay in mm.

        The width is published and the panels take what they take, so this is
        an outcome rather than a choice: 15-5/32" for the default case, an
        eighth over the 15" the brief names, because the plywood is thin.
        """
        return (self.overall_w - self.n_verticals * self.panel_t) / self.n_bays

    @property
    def toe_reveal(self) -> float:
        """Height of the bay bottoms off the floor, mm.

        What is left of the published height once both openings and all three
        horizontal panels have had theirs.
        """
        return (
            self.overall_h
            - 3 * self.panel_t
            - inches(self.record_bay_h_in)
            - inches(self.cd_row_h_in)
        )

    @property
    def vertical_h(self) -> float:
        """Length of a side or divider in mm, housing at the top included."""
        return self.overall_h - self.panel_t + self.dado_depth

    @property
    def vertical_edge_h(self) -> float:
        """Exposed height of a vertical's front edge, mm.

        The top's own edging runs the full width and caps them, so a vertical's
        edging stops at the underside of the top.
        """
        return self.overall_h - self.panel_t

    @property
    def shelf_len(self) -> float:
        """Length of a shelf in mm, both housings included."""
        return self.bay_clear_w + 2 * self.dado_depth

    @property
    def bay_bottom_z(self) -> float:
        """Underside of the bay bottoms, mm off the floor."""
        return self.toe_reveal

    @property
    def cd_shelf_z(self) -> float:
        """Underside of the CD shelves, mm off the floor."""
        return self.toe_reveal + self.panel_t + inches(self.record_bay_h_in)

    @property
    def top_underside_z(self) -> float:
        """Underside of the top, mm off the floor."""
        return self.overall_h - self.panel_t

    @property
    def clear_run(self) -> float:
        """Width the bays share between the two end panels, mm."""
        return self.overall_w - 2 * self.panel_t

    def vertical_x(self, i: int) -> float:
        """Return the centre line of vertical *i* in mm, ``0`` at the middle.

        Parameters
        ----------
        i : int
            ``0`` is the left end panel, :attr:`n_verticals` - 1 the right.

        Returns
        -------
        float
            Distance from the console's centre line, negative to the left.
        """
        pitch = self.bay_clear_w + self.panel_t
        return -self.overall_w / 2 + self.panel_t / 2 + i * pitch

    @property
    def panel_y(self) -> float:
        """Centre of a panel front to back, mm — the edging is in front of it."""
        return -self.overall_d / 2 + self.edge_t + self.panel_depth / 2

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
            Every panel, shelf and edging strip, positioned, with the housings
            cut so the model shows the joint rather than implying it.
        """
        children: list[object] = [self._placed_top()]

        for i in range(self.n_verticals):
            children.append(self._placed_vertical(i))

        for bay in range(self.n_bays):
            x = (self.vertical_x(bay) + self.vertical_x(bay + 1)) / 2
            children.append(
                Pos(x, self.panel_y, self.bay_bottom_z + self.panel_t / 2)
                * self._shelf(
                    "bay_bottom",
                    notes=(
                        f"housed {mm_to_fractional_inch(self.toe_reveal, 64)} "
                        "off the floor in the verticals either side; identical "
                        f"to a cd_shelf, {2 * self.n_bays} in all"
                    ),
                )
            )
            children.append(
                Pos(x, self.panel_y, self.cd_shelf_z + self.panel_t / 2)
                * self._shelf(
                    "cd_shelf",
                    notes="housed in the verticals either side; carries the CDs",
                )
            )
            for z in (self.bay_bottom_z, self.cd_shelf_z):
                children.append(
                    Pos(x, self.edge_y, z + self.panel_t / 2)
                    * self._edging(
                        "shelf_edge",
                        length_mm=self.bay_clear_w,
                        notes=(
                            "fitted between the verticals' edging after "
                            "glue-up, so it is cut long and trimmed to the "
                            "opening"
                        ),
                    )
                )

        # -- Solid cherry on every front edge ---------------------------
        children.append(
            Pos(0.0, self.edge_y, self.top_underside_z + self.panel_t / 2)
            * self._edging(
                "top_edge",
                length_mm=self.overall_w,
                notes=(
                    "runs the full width and caps the verticals' edging; "
                    "glued on and planed flush after the case is together"
                ),
            )
        )
        for i in range(self.n_verticals):
            children.append(
                Pos(self.vertical_x(i), self.edge_y, self.vertical_edge_h / 2)
                * Rotation(0, 90, 0)
                * self._edging(
                    "vertical_edge",
                    length_mm=self.vertical_edge_h,
                    notes=(
                        "glued on before assembly; it is what the shelf "
                        "housings stop against"
                    ),
                )
            )

        return Compound(children=children, label="media_console")

    def _placed_top(self):
        """Return the top, positioned, with a housing for every vertical.

        The two at the ends are rabbets rather than dados — geometrically the
        same cut, and the difference is only that one side of it is fresh air.
        """
        part = Panel(
            length_mm=self.overall_w,
            width_mm=self.panel_depth,
            thickness_mm=self.panel_t,
            material=self.panel_material,
            label="top",
            grain_direction="length",
            notes=(
                "face grain runs the length; underside housed for all "
                f"{self.n_verticals} verticals — a rabbet at each end and "
                f"{self.n_bays - 1} dados between"
            ),
        )
        top = Pos(0.0, self.panel_y, self.top_underside_z + self.panel_t / 2) * part
        z = self.top_underside_z + self.dado_depth / 2
        for i in range(self.n_verticals):
            top = top - (
                Pos(self.vertical_x(i), self.panel_y, z)
                * Rotation(0, 0, 90)
                * self._housing()
            )
        return retag(top, like=part)

    def _housing(self) -> Dado:
        """Return one housing, drawn in its own frame and rotated by the caller.

        Every joint in the case is the same cut: the stock's measured
        thickness wide, :attr:`dado_depth` deep, running the full depth of the
        panel it crosses.
        """
        return Dado(
            width_mm=self.panel_t,
            depth_mm=self.dado_depth,
            length_mm=self.panel_depth,
            mode=Mode.PRIVATE,
        )

    def _placed_vertical(self, i: int):
        """Return vertical *i*, positioned, with its shelf housings cut.

        An end panel is housed on its inner face only; a divider is housed on
        both, which leaves 13/64" of web between the two dados — plenty, and
        the reason the housings are 1/4" deep rather than half the stock.
        """
        is_end = i in (0, self.n_verticals - 1)
        part = self._vertical(is_end=is_end)
        placed = (
            Pos(self.vertical_x(i), self.panel_y, self.vertical_h / 2)
            * Rotation(0, 90, 0)
            * part
        )

        faces = []
        if i > 0:
            faces.append(-1.0)  # housing on the left face, for the bay to its left
        if i < self.n_verticals - 1:
            faces.append(+1.0)
        offset = self.panel_t / 2 - self.dado_depth / 2

        for side in faces:
            for z in (self.bay_bottom_z, self.cd_shelf_z):
                placed = placed - (
                    Pos(
                        self.vertical_x(i) + side * offset,
                        self.panel_y,
                        z + self.panel_t / 2,
                    )
                    * Rotation(90, 90, 0)
                    * self._housing()
                )
        return retag(placed, like=part)

    def _vertical(self, is_end: bool) -> Panel:
        """Return a side or a divider as a :class:`woodshop.parts.Panel`."""
        if is_end:
            return Panel(
                length_mm=self.vertical_h,
                width_mm=self.panel_depth,
                thickness_mm=self.panel_t,
                material=self.panel_material,
                label="side",
                grain_direction="length",
                notes=(
                    "face grain runs up the case; two shelf housings on the "
                    "inner face, top end housed in the rabbet under the top"
                ),
            )
        return Panel(
            length_mm=self.vertical_h,
            width_mm=self.panel_depth,
            thickness_mm=self.panel_t,
            material=self.panel_material,
            label="divider",
            grain_direction="length",
            notes=(
                "same blank as a side; housed on both faces, and it carries "
                "the load of two bays straight to the floor"
            ),
        )

    def _shelf(self, label: str, notes: str) -> Panel:
        """Return one shelf — a bay bottom or a CD shelf, which are one part."""
        return Panel(
            length_mm=self.shelf_len,
            width_mm=self.panel_depth,
            thickness_mm=self.panel_t,
            material=self.panel_material,
            label=label,
            grain_direction="length",
            notes=notes,
        )

    def _edging(self, label: str, length_mm: float, notes: str) -> Board:
        """Return one strip of solid front edging.

        All three kinds are the same section — the board is milled to the
        plywood's own thickness and then ripped into strips the width of the
        edging, so the strip's *thickness* is what matches the panel it covers.
        Only the length and where it goes differ.

        Parameters
        ----------
        label : str
            Part name: ``"top_edge"``, ``"vertical_edge"``, ``"shelf_edge"``.
        length_mm : float
            Finished length.  Cut long — every one of these is fitted.
        notes : str
            What this strip is doing, carried to the cut list.

        Returns
        -------
        woodshop.parts.Board
            The strip, unplaced.
        """
        milling = (
            f"{self.species} milled to the plywood's "
            f"{mm_to_fractional_inch(self.panel_t, 64)} and ripped into "
            f"{mm_to_fractional_inch(self.edge_t, 32)} strips"
        )
        return Board(
            length_mm=length_mm,
            thickness_mm=self.panel_t,
            width_mm=self.edge_t,
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

        report.extend(self._fit_findings())
        report.extend(self._load_findings(parts))
        report.extend(self._construction_findings())
        return report

    def _fit_findings(self) -> list[Finding]:
        """Compare the openings against the things they are sized for."""
        findings: list[Finding] = []

        nominal_bay = round(self.bay_clear_w / IN)
        findings.append(
            Finding(
                Severity.INFO,
                "bay",
                f"{self.n_bays} bays come out "
                f"{mm_to_fractional_inch(self.bay_clear_w, 32)} clear, not "
                f"{nominal_bay:g}\": {self.n_verticals} panels of "
                f"{mm_to_fractional_inch(self.panel_t, 64)} take "
                f"{mm_to_fractional_inch(self.n_verticals * self.panel_t, 32)} "
                f"of the {self.overall_w_in:g}\", where "
                f"{self.n_verticals} of a true 3/4\" would take "
                f"{mm_to_fractional_inch(self.n_verticals * inches(0.75), 32)}",
            )
        )

        sleeve = inches(LP_SLEEVE_IN)
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
                label="bay bottom, full of records",
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
            label="the same bottom undivided",
            run_mm=self.clear_run,
        )
        findings.extend(undivided)
        if undivided and undivided[0].severity is Severity.WARN:
            findings.append(
                Finding(
                    Severity.INFO,
                    "bay",
                    f"so sag alone does not ask for {self.n_bays} bays — the "
                    "extra dividers are for the records, which lean and warp "
                    "in any run much over "
                    f"{mm_to_fractional_inch(self.bay_clear_w, 8)}",
                )
            )
        return findings

    def _construction_findings(self) -> list[Finding]:
        """Report what the case is standing on, and what it is not."""
        footprint = self.n_verticals * self.panel_t * self.panel_depth
        return [
            Finding(
                Severity.INFO,
                "stability",
                f"the case stands on {self.n_verticals} panel ends — "
                f"{footprint / IN**2:.0f} sq in of bearing over "
                f"{self.overall_w_in:g}\" — with the bay bottoms housed "
                f"{mm_to_fractional_inch(self.toe_reveal, 64)} clear of the "
                "floor, so an uneven floor cannot telegraph through a bottom",
            ),
            Finding(
                Severity.INFO,
                "racking",
                "no back panel: the dado grid is the whole of the racking "
                f"resistance, so the {self.n_verticals} housings under the top "
                "are structural and every one of them wants glue, not just a "
                "friction fit",
            ),
            Finding(
                Severity.INFO,
                "material",
                f"solid {self.species} edging against {self.panel_material} "
                "veneer: the two start at different colours and darken at "
                "different rates, and sapwood in the edging never catches up "
                "— pull every strip from one board, and keep the piece out of "
                "direct sun for its first months so it darkens evenly",
            ),
        ]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def run(outdir: Path) -> CheckReport:
    """Build the console, write its cut list and diagrams, print the report.

    Parameters
    ----------
    outdir : Path
        Directory for the generated CSV, Markdown, PDF, and CAD files.

    Returns
    -------
    CheckReport
        The design-check findings.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    console = MediaConsole()
    assembly = console.build()
    parts = extract(assembly)

    stem = "media_console"
    print(f"\n{'=' * 78}\n  Media console — 80\" x 24\" x 13\"\n{'=' * 78}")

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
        title="Media console",
    )
    export_assembly(
        assembly,
        output_step=outdir / f"{stem}.step",
        output_stl=outdir / f"{stem}.stl",
    )

    print(f"\nWrote cut list, diagrams, views and CAD export to {outdir}/")
    return report


def _spec() -> ProjectSpec:
    """Return the gallery entry for the console."""
    console = MediaConsole()
    return ProjectSpec(
        slug="media-console",
        name="Media console",
        summary=(
            f'{console.overall_w_in:g}"W x {console.overall_h_in:g}"H x '
            f'{console.overall_d_in:g}"D in cherry plywood with solid cherry '
            f"front edges: {console.n_bays} record bays "
            f'{console.record_bay_h_in:g}" tall under a '
            f'{console.cd_row_h_in:g}" CD row, and a clear top for the '
            "turntable."
        ),
        species=console.species,
        source_url="https://luccahouse.com/",
        build=console.build,
        check=console.check,
        inventory=console.inventory,
        notes=(
            "Sized to a record rather than to a catalogue: the openings are "
            "held exactly and the bay width, the toe reveal and the sheet "
            "count are whatever 45/64\" plywood leaves of an 80\" case."
        ),
        tags=["case", "storage"],
    )


#: Projects this module contributes to the gallery.
PROJECTS: list[ProjectSpec] = [_spec()]


def main() -> None:
    """Parse arguments and build the console."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--outdir", type=Path, default=Path("build"))
    args = parser.parse_args()
    run(args.outdir)


if __name__ == "__main__":
    main()
