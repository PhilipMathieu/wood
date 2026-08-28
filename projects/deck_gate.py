"""Deck stair gate — a railing section that lost two of its posts.

A gate for the stairs off the deck, so the dog can be let out without an
escort.  The deck railing it has to disappear into: 4x4 posts, horizontal
2x4 rails, vertical 1x1 slats with a 45° miter on either end, and a dressed
cedar 1x6 laid flat as a cap.  The gate is that railing section rebuilt as a
swinging frame, after the Young House Love "DeckGate" pattern: a 2x4
perimeter frame, the slat field screwed to its deck-side face at the same
pitch as the railing, and the cap on top.

Source
------
https://www.younghouselove.com/deckgate/ — the pattern, not the dimensions.
Their gate is 2x3s and 2x2 balusters; this one is 2x4s and 1x1 slats because
that is what the railing it matches is made of.

The bracing question
--------------------
A gate sags by racking: the frame parallelograms and the latch corner
drops.  Whether it needs a diagonal (wood brace or cable turnbuckle) is not
a matter of taste — it is the corner joints' moment capacity against the
racking moment, and both sides of that comparison are computable, so
:func:`check_racking` computes them.  The short version:

* The racking moment is the gate's own weight acting at its centre of
  gravity, plus the dog — modelled as a chosen mass landing paws on the
  latch corner with a dynamic factor, because that corner is exactly where
  a dog greets a gate.
* Each rail-to-stile corner resists as a force couple across the rail's
  3-1/2" depth.  A **glued half-lap** puts ~12 in² of long-grain glue face
  at every corner and resists that couple through the glue line; even at a
  wet-service allowable of 200 psi its capacity is an order of magnitude
  past the demand at stair-opening widths.  **Pocket screws into end
  grain** resist it through two screw shanks, and cyclic wet-dry loading
  is exactly what backs screws out of end grain.

So the model defaults to ``corner_joinery="half_lap"`` and ``brace="none"``,
and the check *shows* the margin rather than asserting it.  Build it with
pocket screws instead and the same check tells you to add the cable.

Placeholder dimensions
----------------------
The opening has not been measured yet.  ``opening_width_in=36`` and
``gate_height_in=36`` are stand-ins typical of a deck stair opening; every
derived number (slat count, weights, margins, prices) moves when the real
tape-measure numbers arrive.

Run it
------
::

    uv run python projects/deck_gate.py
    uv run python projects/deck_gate.py --opening-width 38.5 --height 34
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, field
from pathlib import Path

from build123d import Compound, Polyline, Pos, Rotation, extrude, make_face

from woodshop.checks import (
    CheckReport,
    Finding,
    Severity,
    check_envelope,
    check_material_suitability,
    check_price_provenance,
    estimate_mass_kg,
)
from woodshop.cutlist.extract import CutPart, extract
from woodshop.inventory import Inventory
from woodshop.parts import Board, retag
from woodshop.project import ProjectSpec
from woodshop.render import export_assembly, render_assembly, render_cut_list

IN = 25.4
G_M_S2 = 9.81

#: Rotations that stand a part up in the gate's frame: X across the opening,
#: Z up, Y through the gate's thickness.  A Board is born length-along-X,
#: width-along-Y, thickness-along-Z.
_ON_EDGE = Rotation(90, 0, 0)  # length X, width up, thickness through
_UPRIGHT = Rotation(0, 0, -90) * Rotation(0, -90, 0)  # length up, width across


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
class DeckStairGate:
    """A parametric gate matching a slatted 2x4-and-cedar deck railing.

    Parameters
    ----------
    opening_width_in : float, optional
        Clear width between the 4x4 posts, default 36" — a placeholder
        until the opening is measured.
    gate_height_in : float, optional
        Overall gate height, cap included, default 36".
    hinge_clearance_in, latch_clearance_in : float, optional
        Gaps left at the posts, default 1/4" hinge side and 5/8" latch
        side.  The latch side is bigger because seasonal movement and a
        settling post both close it.
    max_slat_gap_in : float, optional
        Largest clear gap allowed between slats, default 3-1/2".  Match
        the railing's pitch when it is known; whatever the value, the IRC
        4"-sphere rule is enforced by :func:`check_slat_gap`.
    species : str, optional
        Frame and slat species, default ``"white_cedar"`` — the cap has to
        be cedar to match the railing, and a cedar frame keeps the gate
        light, which is its own sag protection.
    corner_joinery : str, optional
        ``"half_lap"`` (glued and screwed, the default) or
        ``"pocket_screw"``.  Decides the corner capacity used by
        :func:`check_racking`.
    brace : str, optional
        ``"none"`` (default) or ``"cable"`` — a diagonal turnbuckle from
        the top hinge corner to the bottom latch corner, hardware rather
        than lumber, so it changes the checks and the notes but not the
        cut list.
    dog_mass_lb : float, optional
        The dog the racking check designs for, default 60 lb.
    inventory : Inventory, optional
        Stock inventory.  Loaded from ``stock.yaml`` if not given.

    Raises
    ------
    ValueError
        If *corner_joinery* or *brace* is unknown, or the opening is too
        narrow to hold a frame at all.
    """

    opening_width_in: float = 36.0
    gate_height_in: float = 36.0
    hinge_clearance_in: float = 0.25
    latch_clearance_in: float = 0.625
    max_slat_gap_in: float = 3.5
    species: str = "white_cedar"
    corner_joinery: str = "half_lap"
    brace: str = "none"
    dog_mass_lb: float = 60.0

    inventory: Inventory = field(default_factory=Inventory.load)

    #: Nominal sizes fixed by the railing being matched.
    frame_nominal: str = "2x4"
    cap_nominal: str = "1x6"
    #: A dressed "1x1" slat: 3/4" x 3/4", like the railing's.
    slat_side_in: float = 0.75

    def __post_init__(self) -> None:
        """Validate the choices that change structure, not just size."""
        if self.corner_joinery not in ("half_lap", "pocket_screw"):
            raise ValueError(
                f"corner_joinery must be 'half_lap' or 'pocket_screw', "
                f"got {self.corner_joinery!r}"
            )
        if self.brace not in ("none", "cable"):
            raise ValueError(f"brace must be 'none' or 'cable', got {self.brace!r}")
        if self.slat_span <= 0:
            raise ValueError(
                f"opening {self.opening_width_in:g}\" leaves no room between "
                f"the stiles"
            )

    # ------------------------------------------------------------------
    # Derived geometry
    # ------------------------------------------------------------------

    @property
    def gate_width(self) -> float:
        """Gate width in mm: the opening less the two hinge-and-latch gaps."""
        return inches(
            self.opening_width_in - self.hinge_clearance_in - self.latch_clearance_in
        )

    @property
    def cap_thickness(self) -> float:
        """Dressed thickness of the 1x6 cap, mm."""
        return inches(0.75)

    @property
    def frame_height(self) -> float:
        """Height of the 2x4 frame, mm — the gate less the cap on top."""
        return inches(self.gate_height_in) - self.cap_thickness

    @property
    def frame_depth(self) -> float:
        """Depth of a 2x4 on edge, mm: 3-1/2"."""
        return inches(3.5)

    @property
    def frame_thickness(self) -> float:
        """Thickness of the frame, mm: a 2x4's 1-1/2"."""
        return inches(1.5)

    @property
    def slat_side(self) -> float:
        """Side of a dressed 1x1 slat, mm."""
        return inches(self.slat_side_in)

    @property
    def slat_span(self) -> float:
        """Clear width between the stiles, mm — what the slats must fill."""
        return self.gate_width - 2 * self.frame_depth

    @property
    def slat_length(self) -> float:
        """Length of a slat, mm.

        The slats lie on the deck-side face and overlap both rails, like
        the railing's; they stop 1" shy of the frame's top and bottom so
        the mitered ends read against the rail faces.
        """
        return self.frame_height - 2 * inches(1.0)

    @property
    def n_slats(self) -> int:
        """Slat count: the fewest that keep every gap at or under the max."""
        gap = inches(self.max_slat_gap_in)
        return max(1, math.ceil((self.slat_span - gap) / (self.slat_side + gap)))

    @property
    def slat_gap(self) -> float:
        """Actual clear gap between slats (and stile to first slat), mm."""
        n = self.n_slats
        return (self.slat_span - n * self.slat_side) / (n + 1)

    # ------------------------------------------------------------------
    # Assembly
    # ------------------------------------------------------------------

    def build(self) -> Compound:
        """Build the gate as a positioned build123d assembly.

        The gate is centred on X, its hinge stile at -X; z = 0 is the
        bottom of the frame and +Y is the deck side, where the slats are.

        Returns
        -------
        build123d.Compound
            Frame, slats, and cap, positioned.
        """
        children: list[object] = []

        stile_x = self.gate_width / 2 - self.frame_depth / 2
        for side, x in (("hinge", -stile_x), ("latch", stile_x)):
            children.append(
                Pos(x, 0.0, self.frame_height / 2)
                * _UPRIGHT
                * self._stile(side)
            )

        rail_len = self.gate_width - 2 * self.frame_depth
        for name, z in (
            ("bottom", self.frame_depth / 2),
            ("top", self.frame_height - self.frame_depth / 2),
        ):
            children.append(Pos(0.0, 0.0, z) * _ON_EDGE * self._rail(name, rail_len))

        slat_y = self.frame_thickness / 2 + self.slat_side / 2
        pitch = self.slat_side + self.slat_gap
        first_x = -self.slat_span / 2 + self.slat_gap + self.slat_side / 2
        for i in range(self.n_slats):
            children.append(
                Pos(first_x + i * pitch, slat_y, self.frame_height / 2)
                * _UPRIGHT
                * self._slat()
            )

        children.append(
            Pos(0.0, 0.0, self.frame_height + self.cap_thickness / 2) * self._cap()
        )

        return Compound(children=children, label="deck_stair_gate")

    def _stile(self, side: str) -> Board:
        """Return one vertical frame member."""
        joint = (
            "half-lapped, glued (Titebond III) and screwed"
            if self.corner_joinery == "half_lap"
            else "pocket-screwed to the rails"
        )
        return Board(
            length_mm=self.frame_height,
            nominal=self.frame_nominal,
            material=self.species,
            label=f"{side}_stile",
            notes=f"{joint}; {side} side of the gate",
        )

    def _rail(self, name: str, length_mm: float) -> Board:
        """Return one horizontal frame member."""
        return Board(
            length_mm=length_mm,
            nominal=self.frame_nominal,
            material=self.species,
            label=f"{name}_rail",
            notes="on edge between the stiles",
        )

    def _slat(self):
        """Return one slat, both ends mitered 45° like the railing's.

        The miters are parallel — the face is a parallelogram — so every
        slat is one saw setup and goes on either way up.  A miter takes no
        extra stock, so the part is a plain 1x1 stick on the cut list, long
        point to long point, with the corners sawn off the solid: a boolean
        returns anonymous geometry, hence :func:`woodshop.parts.retag`.
        """
        length, side = self.slat_length, self.slat_side
        stick = Board(
            length_mm=length,
            thickness_mm=side,
            width_mm=side,
            material=self.species,
            label="slat",
        )
        # Corner triangles off opposite corners of the face, through the
        # full thickness, leaving the two 45° cuts parallel.
        wedges = []
        for sx, sy in ((-1.0, -1.0), (1.0, 1.0)):
            tri = make_face(
                Polyline(
                    (sx * length / 2, sy * side / 2),
                    (sx * (length / 2 - side), sy * side / 2),
                    (sx * length / 2, -sy * side / 2),
                    close=True,
                )
            )
            wedges.append(extrude(tri, amount=side, both=True))
        return retag(
            stick - wedges[0] - wedges[1],
            like=stick,
            notes=(
                "screwed to the deck-side face of both rails, one screw per "
                "crossing; ends mitered 45°, parallel, long point to long "
                "point"
            ),
        )

    def _cap(self) -> Board:
        """Return the cedar cap, laid flat over the frame."""
        return Board(
            length_mm=self.gate_width,
            nominal=self.cap_nominal,
            material="white_cedar",
            label="cap",
            notes=(
                "matches the railing cap; ease the ends so they clear the "
                "posts and the railing cap through the swing"
            ),
        )

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def check(self, assembly: Compound, parts: list[CutPart]) -> CheckReport:
        """Run every design check against a built gate.

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
                published_l_mm=self.gate_width,
                # The cap, not the frame, is the deepest thing on the gate.
                published_w_mm=inches(5.5),
                published_h_mm=inches(self.gate_height_in),
            )
        )
        report.extend(check_material_suitability(parts, self.inventory))
        report.extend(self.check_slat_gap())
        report.extend(self.check_racking(parts))
        report.extend(self.check_hinge_load(parts))
        return report

    def check_slat_gap(self) -> list[Finding]:
        """Hold the slat field to the guard rule the railing already meets.

        IRC R312.1.3: no opening in a guard may pass a 4" sphere.  A gate in
        a guard is part of the guard, and a dog-containment gate has its own
        reason to care.

        Returns
        -------
        list[Finding]
            An ``INFO`` stating the pitch, or an ``ERROR`` if a gap passes
            the sphere.
        """
        gap_in = self.slat_gap / IN
        if self.slat_gap >= inches(4.0):
            return [
                Finding(
                    Severity.ERROR,
                    "guard",
                    f'slat gaps are {gap_in:.2f}" — a 4" sphere passes; '
                    f"add a slat or tighten max_slat_gap_in",
                )
            ]
        return [
            Finding(
                Severity.INFO,
                "guard",
                f'{self.n_slats} slats at {gap_in:.2f}" gaps across a '
                f'{self.slat_span / IN:.1f}" field — match the railing pitch '
                f"when it is measured",
            )
        ]

    def check_racking(self, parts: list[CutPart]) -> list[Finding]:
        """Decide whether this gate needs a diagonal, with numbers.

        The racking moment about the hinge stile is the gate's weight at
        its centre of gravity plus the design dog landing on the latch
        corner with a dynamic factor of 1.5.  Each of the four rail-stile
        corners resists half the moment (two rails share it) as a force
        couple across the rail's depth.

        Corner capacity, stated conservatively so the margin means
        something:

        * ``half_lap`` — the couple loads a 3-1/2" x 3-1/2" long-grain glue
          face in shear.  At a wet-service allowable of 1.4 MPa (~200 psi,
          a tenth of dry Titebond III shear figures) the face carries
          ~11 kN; call the usable couple force 4.4 kN after eccentricity.
        * ``pocket_screw`` — two #8 screws in end grain at ~450 N
          (~100 lb) allowable lateral load each, before wet-dry cycling
          works on them.

        A cable brace changes the load path entirely — the latch corner
        hangs off the top hinge corner in tension — so with one fitted the
        corners are no longer the governing part and the check reports the
        cable instead.

        Parameters
        ----------
        parts : list[CutPart]
            The cut list, for the gate's own mass.

        Returns
        -------
        list[Finding]
            ``INFO`` with the demand and margin; ``WARN`` when the chosen
            corners cannot carry the dog.
        """
        mass_kg = estimate_mass_kg(parts)
        # Static: the gate's weight at mid-width, about the hinge line.
        static_nm = mass_kg * G_M_S2 * (self.gate_width / 2) / 1000.0
        # Dynamic: the dog, paws on the latch corner, 1.5x for the landing.
        dog_n = 1.5 * (self.dog_mass_lb * 0.4536) * G_M_S2
        dog_nm = dog_n * self.gate_width / 1000.0
        demand_nm = static_nm + dog_nm

        # Two rails share the moment; each corner turns its half into a
        # couple across the rail depth.
        couple_n = (demand_nm / 2) / (self.frame_depth / 1000.0)
        capacity_n = {"half_lap": 4400.0, "pocket_screw": 900.0}[self.corner_joinery]
        margin = capacity_n / couple_n

        if self.brace == "cable":
            return [
                Finding(
                    Severity.INFO,
                    "racking",
                    f"cable brace carries the latch corner in tension — "
                    f"~{demand_nm / (self.frame_height / 1000.0):.0f} N in the "
                    f"cable at full racking moment; corners are no longer "
                    f"governing",
                )
            ]

        summary = (
            f"racking demand {demand_nm:.0f} N·m "
            f"({static_nm:.0f} gate + {dog_nm:.0f} dog at {self.dog_mass_lb:g} lb) "
            f"→ {couple_n:.0f} N per corner couple against "
            f"{capacity_n:.0f} N for {self.corner_joinery} corners "
            f"({margin:.1f}x margin)"
        )
        if margin < 1.5:
            return [
                Finding(
                    Severity.WARN,
                    "racking",
                    f"{summary} — add a cable turnbuckle brace (brace='cable') "
                    f"or glue half-laps (corner_joinery='half_lap')",
                )
            ]
        return [
            Finding(
                Severity.INFO,
                "racking",
                f"{summary} — no diagonal needed; the slat field, screwed at "
                f"{2 * self.n_slats} rail crossings, is redundancy on top",
            )
        ]

    def check_hinge_load(self, parts: list[CutPart]) -> list[Finding]:
        """Report what the top hinge asks of its screws.

        The gate's weight at mid-width pries the top hinge away from the
        post; the pull is the weight scaled by the ratio of that lever to
        the hinge spacing.  It is never the governing number on a gate this
        size — which is worth a line, because oversizing hinges is how
        gates end up heavier than they need to be.

        Parameters
        ----------
        parts : list[CutPart]
            The cut list, for the gate's own mass.

        Returns
        -------
        list[Finding]
            One ``INFO``.
        """
        mass_kg = estimate_mass_kg(parts)
        # Hinges at the rail centre lines — as far apart as the frame allows.
        spacing = self.frame_height - self.frame_depth
        pull_n = mass_kg * G_M_S2 * (self.gate_width / 2) / spacing
        return [
            Finding(
                Severity.INFO,
                "hinges",
                f"gate is ~{mass_kg:.1f} kg ({mass_kg * 2.205:.0f} lb); top "
                f"hinge pulls ~{pull_n:.0f} N ({pull_n / 4.448:.0f} lb) — two "
                f'self-closing hinges on 2-1/2" structural screws into the '
                f"4x4 are plenty",
            )
        ]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def run(gate: DeckStairGate, outdir: Path) -> CheckReport:
    """Build one gate, write its cut list and views, print the report.

    Parameters
    ----------
    gate : DeckStairGate
        The gate to build.
    outdir : Path
        Directory for the generated CSV, Markdown, PNG, and CAD files.

    Returns
    -------
    CheckReport
        The design-check findings.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    assembly = gate.build()
    parts = extract(assembly)

    stem = "deck_gate"
    print(f"\n{'=' * 78}\n  Deck stair gate\n{'=' * 78}")

    df = render_cut_list(
        parts,
        output_csv=outdir / f"{stem}_cutlist.csv",
        output_md=outdir / f"{stem}_cutlist.md",
    )
    print(df.to_string(index=False))

    report = gate.check(assembly, parts)
    print(f"\n-- design checks {'-' * 61}")
    print(report.to_text())

    print(f"\n-- prices {'-' * 68}")
    print(
        CheckReport().extend(check_price_provenance(gate.inventory, parts)).to_text()
    )

    render_assembly(
        assembly,
        output_png=outdir / f"{stem}.png",
        title="Deck stair gate",
    )
    export_assembly(
        assembly,
        output_step=outdir / f"{stem}.step",
        output_stl=outdir / f"{stem}.stl",
    )

    print(f"\nWrote cut list, views and CAD export to {outdir}/")
    return report


def _spec() -> ProjectSpec:
    """Return the gallery entry for the gate."""
    gate = DeckStairGate()
    return ProjectSpec(
        slug="deck-stair-gate",
        name="Deck stair gate",
        summary=(
            "A gate for the deck stairs matching the railing: 2x4 frame, "
            "mitered 1x1 slats, cedar 1x6 cap.  Half-lapped corners instead "
            "of a diagonal brace, and a check that proves the margin."
        ),
        species="white_cedar",
        source_url="https://www.younghouselove.com/deckgate/",
        build=gate.build,
        check=gate.check,
        inventory=gate.inventory,
        notes=(
            "Placeholder 36\" x 36\" opening until the stairs are measured; "
            "every derived number moves with the tape measure."
        ),
        tags=["outdoor", "gate"],
    )


#: Projects this module contributes to the gallery.
PROJECTS: list[ProjectSpec] = [_spec()]


def main() -> None:
    """Parse arguments and build the gate."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--opening-width", type=float, default=36.0)
    parser.add_argument("--height", type=float, default=36.0)
    parser.add_argument(
        "--corner-joinery", choices=["half_lap", "pocket_screw"], default="half_lap"
    )
    parser.add_argument("--brace", choices=["none", "cable"], default="none")
    parser.add_argument("--outdir", type=Path, default=Path("build"))
    args = parser.parse_args()

    gate = DeckStairGate(
        opening_width_in=args.opening_width,
        gate_height_in=args.height,
        corner_joinery=args.corner_joinery,
        brace=args.brace,
    )
    run(gate, args.outdir)


if __name__ == "__main__":
    main()
