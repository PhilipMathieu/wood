"""Mysa nightstand — the round, three-legged companion to the sleigh bed.

Source
------
https://www.chiltons.com/products/mysa-nightstand-cherry

Published specification, read 2026-08-16::

    18" round x 22"H
    Top    1-1/2" thick, edge slightly angled inward
    Legs   three, round turned, 1-1/2" tapering to 1"
    No drawers; solid wood, conversion varnish
    $535.50 sale / $595.00 regular in cherry

Why this piece and not another
------------------------------
It is the only modern nightstand Chilton sells — the rest of that collection is
Shaker — and it is in the same line as the sleigh bed.  It is also the piece
that breaks every assumption the bed validated: the bed is entirely
rectilinear, and nothing in it is round, turned, tapered, or three-legged.

What is inferred rather than published
--------------------------------------
The listing gives an envelope, a top thickness, and a leg taper.  Everything
else below is derived, and stated here so it can be argued with:

* **The edge is angled in to 17"** at the underside, over the full 1-1/2"
  thickness — about 18° off vertical.  "Slightly angled inward" is all the
  listing says; this is the amount that makes a 1-1/2" top read as thinner
  without turning it into a bevel.
* **Legs meet the top on an 11" circle** (5-1/2" radius) and splay 6° outward.
  Neither number is published.  The splay is capped by the envelope, not by
  taste: the feet plus their own radius have to stay inside the 18" the
  listing quotes, which puts a hard ceiling of about 8-1/2" on the foot
  radius.  See the stability finding, which is a consequence of that ceiling
  rather than of this particular choice.
* **The legs are joined with a 1"-diameter round tenon**, 1" long, into a
  blind hole in the underside of the top.  Nothing is published about the
  joinery.  This is the simplest joint that suits a turned leg, and it is the
  weakest of the plausible ones — a leg-to-top joint with no apron carries the
  whole racking load on three glue lines.
* **The taper runs the full length of the leg**, 1" at the foot to 1-1/2"
  where it meets the top.  The listing gives the two diameters but not where
  they fall.

Both the top and the legs come out of 8/4 cherry, which surfaces to 1-3/4":
enough for a 1-1/2" top, and exactly a 1-3/4" turning square.

Run it
------
::

    uv run python projects/mysa_nightstand.py
    uv run python projects/mysa_nightstand.py --variant plywood --outdir build
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
    check_envelope,
    check_material_suitability,
    check_price_provenance,
    check_sheet_fit,
    check_thickness_substitution,
    check_tip_resistance,
    estimate_mass_kg,
)
from woodshop.cutlist.extract import CutPart, extract
from woodshop.cutlist.hardwood import nest_hardwood
from woodshop.inventory import Inventory
from woodshop.parts import Disc, Turning, retag
from woodshop.project import ProjectSpec
from woodshop.render import (
    export_assembly,
    render_assembly,
    render_board_diagram,
    render_cut_list,
)

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


@dataclass
class MysaNightstand:
    """A parametric Mysa nightstand.

    Parameters
    ----------
    variant : str
        ``"solid"`` for cherry throughout, as sold.  ``"plywood"`` substitutes
        sheet goods for the top and the legs — which is not a design, it is a
        demonstration: see :func:`woodshop.checks.check_material_suitability`,
        which rejects it.
    species : str, optional
        Solid-wood species, default ``"cherry"``.
    top_diameter_in : float, optional
        Finished diameter of the top, default 18".
    top_thickness_in : float, optional
        Finished thickness of the top, default 1-1/2".
    top_bottom_diameter_in : float, optional
        Diameter at the underside, default 17" — the angled edge.
    overall_h_in : float, optional
        Published overall height, default 22".
    n_legs : int, optional
        Number of legs, default 3.
    leg_top_diameter_in, leg_foot_diameter_in : float, optional
        Published leg taper, default 1-1/2" down to 1".
    leg_circle_r_in : float, optional
        Radius of the circle the legs meet the top on, default 5-1/2".
    splay_deg : float, optional
        How far the legs lean out from vertical, default 6°.
    tenon_length_in, tenon_diameter_in : float, optional
        Round tenon into the underside of the top, default 1" x 1" dia.
    inventory : Inventory, optional
        Stock inventory.  Loaded from ``stock.yaml`` if not given.

    Raises
    ------
    ValueError
        If *variant* is unknown, or fewer than three legs are asked for.
    """

    variant: str = "solid"
    species: str = "cherry"

    top_diameter_in: float = 18.0
    top_thickness_in: float = 1.5
    top_bottom_diameter_in: float = 17.0
    overall_h_in: float = 22.0

    n_legs: int = 3
    leg_top_diameter_in: float = 1.5
    leg_foot_diameter_in: float = 1.0
    leg_circle_r_in: float = 5.5
    splay_deg: float = 6.0
    tenon_length_in: float = 1.0
    tenon_diameter_in: float = 1.0

    inventory: Inventory = field(default_factory=Inventory.load)

    def __post_init__(self) -> None:
        """Validate the variant and the leg count."""
        if self.variant not in ("solid", "plywood"):
            raise ValueError(
                f"variant must be 'solid' or 'plywood', got {self.variant!r}"
            )
        if self.n_legs < 3:
            raise ValueError(f"a nightstand needs at least 3 legs, got {self.n_legs}")

    # ------------------------------------------------------------------
    # Materials — the only thing the two variants disagree about
    # ------------------------------------------------------------------

    @property
    def top_material(self) -> str:
        """Material of the top."""
        return "plywood_cherry" if self.variant == "plywood" else self.species

    @property
    def leg_material(self) -> str:
        """Material of the legs."""
        return "plywood_baltic_birch" if self.variant == "plywood" else self.species

    @property
    def top_thickness_mm(self) -> float:
        """Top thickness, measured for sheet goods.

        A 3/4" sheet is nowhere near the published 1-1/2", so the plywood
        variant's top is two sheets laminated — which is the least of its
        problems.
        """
        if self.variant == "plywood":
            return 2 * self.inventory.sheet_for("plywood_cherry", "3/4").thickness_mm
        return inches(self.top_thickness_in)

    # ------------------------------------------------------------------
    # Derived geometry
    # ------------------------------------------------------------------

    @property
    def overall_h(self) -> float:
        """Published overall height in mm."""
        return inches(self.overall_h_in)

    @property
    def top_diameter(self) -> float:
        """Finished diameter of the top in mm."""
        return inches(self.top_diameter_in)

    @property
    def top_underside_z(self) -> float:
        """Height of the underside of the top off the floor, mm."""
        return self.overall_h - self.top_thickness_mm

    @property
    def leg_rise(self) -> float:
        """Vertical distance from the floor to the top of the tenon, mm."""
        return self.top_underside_z + inches(self.tenon_length_in)

    @property
    def splay_rad(self) -> float:
        """Splay angle in radians."""
        return math.radians(self.splay_deg)

    @property
    def leg_length(self) -> float:
        """Length of one leg along its own axis, tenon included, mm.

        Longer than the vertical rise, because the leg leans.
        """
        return self.leg_rise / math.cos(self.splay_rad)

    @property
    def foot_radius(self) -> float:
        """Distance from the centre line to the middle of a foot, mm."""
        return inches(self.leg_circle_r_in) + self.leg_rise * math.tan(self.splay_rad)

    @property
    def foot_spread(self) -> float:
        """Overall diameter across the outsides of the feet, mm."""
        return 2 * (self.foot_radius + inches(self.leg_foot_diameter_in) / 2)

    # ------------------------------------------------------------------
    # Assembly
    # ------------------------------------------------------------------

    def build(self) -> Compound:
        """Build the nightstand as a positioned build123d assembly.

        The assembly is centred on its own axis, +Z up from the floor.

        Returns
        -------
        build123d.Compound
            The top and every leg, positioned.
        """
        children: list[object] = [
            Pos(0.0, 0.0, self.top_underside_z + self.top_thickness_mm / 2)
            * self._top()
        ]

        r_top = inches(self.leg_circle_r_in)
        length = self.leg_length
        sin_s, cos_s = math.sin(self.splay_rad), math.cos(self.splay_rad)

        for i in range(self.n_legs):
            theta = 2 * math.pi * i / self.n_legs
            # Axis direction, foot to top: up and *inward*, because a splayed
            # leg reaches outward on the way down.
            dx = -sin_s * math.cos(theta)
            dy = -sin_s * math.sin(theta)
            dz = cos_s
            # The top of the leg — tenon and all — lands on the leg circle.
            cx = r_top * math.cos(theta) - dx * length / 2
            cy = r_top * math.sin(theta) - dy * length / 2
            cz = self.leg_rise - dz * length / 2
            leg = (
                Pos(cx, cy, cz)
                * Rotation(0, 0, math.degrees(theta))
                * Rotation(0, -self.splay_deg, 0)
                * self._leg()
            )
            children.append(self._level_foot(leg))

        return Compound(children=children, label=f"mysa_nightstand_{self.variant}")

    def _level_foot(self, leg):
        """Saw a splayed foot off flat where it meets the floor.

        A leg turned between centres ends square to its own axis.  Lean it 6°
        and that end is no longer level: the outside corner drops about 1/16"
        below the floor and the piece rocks.  Every splayed-leg piece is
        levelled after glue-up, and the model should show the leg that leaves
        the shop rather than the one that leaves the lathe.

        The cut is a boolean, which returns anonymous geometry — hence
        :func:`woodshop.parts.retag`, without which the legs would vanish from
        the cut list and nothing would say so.
        """
        span = self.top_diameter * 2
        below_the_floor = Pos(0.0, 0.0, -span / 2) * Box(span, span, span)
        return retag(
            leg - below_the_floor,
            like=leg,
            notes=f"{leg.notes}; foot sawn level after glue-up",
        )

    def _top(self) -> Disc:
        """Return the top as a :class:`woodshop.parts.Disc`."""
        note = (
            "glue-up, staves running one way; fix to the legs through slotted "
            "holes so it can move"
        )
        if self.variant == "plywood":
            note = (
                "two 3/4\" sheets laminated to reach 1-1/2\"; the edge shows "
                "every ply, twice"
            )
        return Disc(
            diameter_mm=self.top_diameter,
            thickness_mm=self.top_thickness_mm,
            bottom_diameter_mm=inches(self.top_bottom_diameter_in),
            material=self.top_material,
            label="top",
            grain_direction="length",
            notes=note,
        )

    def _leg(self) -> Turning:
        """Return one leg as a :class:`woodshop.parts.Turning`."""
        return Turning(
            length_mm=self.leg_length,
            diameter_mm=inches(self.leg_foot_diameter_in),
            end_diameter_mm=inches(self.leg_top_diameter_in),
            material=self.leg_material,
            label="leg",
            grain_direction="length",
            notes=(
                f'top {self.tenon_length_in:g}" turned down to a '
                f'{self.tenon_diameter_in:g}" round tenon, housed in the top; '
                f"blank is a square, turned between centres"
            ),
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
                published_l_mm=self.top_diameter,
                published_w_mm=self.top_diameter,
                published_h_mm=self.overall_h,
            )
        )

        # The check this piece exists to exercise: a material against the
        # operation that shapes it, which no dimension can catch.
        report.extend(check_material_suitability(parts, self.inventory))
        report.extend(check_sheet_fit(parts, self.inventory))
        report.extend(check_thickness_substitution(parts, self.inventory))

        mass_kg = estimate_mass_kg(parts)
        report.extend(
            check_tip_resistance(
                mass_kg=mass_kg,
                n_legs=self.n_legs,
                foot_radius_mm=self.foot_radius,
                overhang_radius_mm=self.top_diameter / 2,
            )
        )

        # The splay is not a free choice: the feet have to stay inside the
        # published envelope, so the stance can never be wider than the top.
        headroom = self.top_diameter - self.foot_spread
        report.findings.append(
            Finding(
                Severity.INFO,
                "stability",
                f"feet span {self.foot_spread / IN:.1f}\" inside an "
                f"{self.top_diameter_in:g}\" top — {headroom / IN:.1f}\" of "
                f"envelope left, so the splay could go to about "
                f"{self._max_splay_deg():.0f}° before the feet show",
            )
        )
        if headroom < 0:
            report.findings.append(
                Finding(
                    Severity.ERROR,
                    "stability",
                    f"the feet span {self.foot_spread / IN:.1f}\", wider than the "
                    f"published {self.top_diameter_in:g}\" envelope",
                )
            )
        return report

    def _max_splay_deg(self) -> float:
        """Return the splay at which the feet reach the edge of the top."""
        limit = (
            self.top_diameter / 2
            - inches(self.leg_foot_diameter_in) / 2
            - inches(self.leg_circle_r_in)
        )
        return math.degrees(math.atan(limit / self.leg_rise))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def run(variant: str, outdir: Path) -> CheckReport:
    """Build one nightstand, write its cut list and diagrams, print the report.

    Parameters
    ----------
    variant : str
        ``"solid"`` or ``"plywood"``.
    outdir : Path
        Directory for the generated CSV, Markdown, PDF, and CAD files.

    Returns
    -------
    CheckReport
        The design-check findings.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    stand = MysaNightstand(variant=variant)
    assembly = stand.build()
    parts = extract(assembly)

    stem = f"mysa_nightstand_{variant}"
    print(f"\n{'=' * 78}\n  Mysa nightstand — {variant}\n{'=' * 78}")

    df = render_cut_list(
        parts,
        output_csv=outdir / f"{stem}_cutlist.csv",
        output_md=outdir / f"{stem}_cutlist.md",
    )
    print(df.to_string(index=False))

    report = stand.check(assembly, parts)
    print(f"\n-- design checks {'-' * 61}")
    print(report.to_text())

    # Separate from the design checks: where the money came from is a question
    # about the quote, not about whether the piece stands up.
    print(f"\n-- prices {'-' * 68}")
    print(
        CheckReport().extend(check_price_provenance(stand.inventory, parts)).to_text()
    )

    sheet_materials = {s.material for s in stand.inventory.sheet_goods}
    solid = [p for p in parts if p.material not in sheet_materials]
    if solid:
        print(f"\n-- {stand.species} to buy {'-' * 55}")
        plan = nest_hardwood(solid, stand.inventory, stand.species)
        print(plan.to_text())
        render_board_diagram(plan, output_pdf=outdir / f"{stem}_boards.pdf")

    render_assembly(
        assembly,
        output_png=outdir / f"{stem}.png",
        title=f"Mysa nightstand — {variant}",
    )
    export_assembly(
        assembly,
        output_step=outdir / f"{stem}.step",
        output_stl=outdir / f"{stem}.stl",
    )

    print(f"\nWrote cut list, diagrams, views and CAD export to {outdir}/")
    return report


def _spec() -> ProjectSpec:
    """Return the gallery entry for the solid-cherry nightstand."""
    stand = MysaNightstand()
    return ProjectSpec(
        slug="mysa-nightstand",
        name="Mysa nightstand",
        summary=(
            '18" round cherry top, 1-1/2" thick with the edge angled inward, '
            "on three turned legs tapering 1-1/2\" to 1\"."
        ),
        species="cherry",
        source_url="https://www.chiltons.com/products/mysa-nightstand-cherry",
        build=stand.build,
        check=stand.check,
        inventory=stand.inventory,
        notes=(
            "The piece that made the toolkit learn the difference between a "
            "blank and a finished part: you cannot buy a circle."
        ),
    )


#: Projects this module contributes to the gallery.
PROJECTS: list[ProjectSpec] = [_spec()]


def main() -> None:
    """Parse arguments and build the requested nightstand."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--variant", choices=["solid", "plywood", "both"], default="solid"
    )
    parser.add_argument("--outdir", type=Path, default=Path("build"))
    args = parser.parse_args()

    variants = ["solid", "plywood"] if args.variant == "both" else [args.variant]
    for variant in variants:
        run(variant, args.outdir)


if __name__ == "__main__":
    main()
