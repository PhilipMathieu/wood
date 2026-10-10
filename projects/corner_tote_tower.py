"""Corner tote tower — four 17-gallon totes hung by their rims in a stud corner.

The brief, as it ended up::

    Buy a medium-width steel bench and add a single column of storage for
    the taller totes, four high, in the basement corner where both walls are
    exposed studs at 16" on centre from the corner.  All new material, and
    no plywood over the wall.  A scrap of pressure-treated lumber where the
    leg meets the concrete.

The corner does most of the work
--------------------------------
A freestanding column of totes needs two side frames, a back to stop it
racking, and an anchor to stop it tipping.  In a corner, the walls already
do two of those jobs, and the side wall's studs do a third:

* **Wall side.**  Each runner — a 1x4 the tote's lip rides on, exactly as in
  ``basement_bench.py`` — is screwed straight to the faces of the side-wall
  studs it crosses: the corner stud and the one at 16".  Past that it
  overhangs to the front, which a 1x4 on edge does without noticing;
  :meth:`CornerToteTower._overhang_findings` works the number for a tote
  pulled out until its whole side load hangs on the tip.
* **Open side.**  One **front leg** on the slab, and a **back stile** that
  stops short of the floor and hangs on two 2x4 **blocks** fitted *between*
  the back-wall studs, flush with their faces.  Blocking rather than a cleat
  across the stud faces, because a cleat would stand in the wall plane right
  where the back of a tote ends up.  A **top rail** ties the leg's head back
  to the stile.
* **Top.**  A 1x4 **ledger** on the side-wall studs and the top rail carry
  four 1x6 **slats** — a shelf, and the tie that stops the leg leaning out.
* **Foot.**  An offcut of ground-contact pressure-treated 2x4 under the leg,
  so no untreated end grain stands on a slab that wicks.

Coordinates follow the rest of the repo: ``x`` along the back wall from the
face of the side-wall studs, ``y`` from the room toward the back wall (``y =
0`` is the face of the back-wall studs, the room is ``-y``), ``z`` up from the
slab.  The side wall is on the left; for a right-hand corner, build it the
mirror way round.

Run it
------
::

    uv run python projects/corner_tote_tower.py
    uv run python projects/corner_tote_tower.py --tiers 3 --outdir build
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

from build123d import Box, Compound, Pos, Rotation

sys.path.insert(0, str(Path(__file__).resolve().parent))

from basement_bench import BIN_DESIGN_MASS_KG, BIN_TYPES, IN, Bin, inches  # noqa: E402

from woodshop.checks import (  # noqa: E402
    ELASTIC_MODULUS_MPA,
    CheckReport,
    Finding,
    Severity,
    check_clearance,
    check_price_provenance,
)
from woodshop.cutlist.extract import CutPart, extract  # noqa: E402
from woodshop.cutlist.optimize_1d import optimize_1d  # noqa: E402
from woodshop.inventory import Inventory  # noqa: E402
from woodshop.lumber import actual_dimensions_mm, mm_to_fractional_inch  # noqa: E402
from woodshop.parts import Board  # noqa: E402
from woodshop.project import ProjectSpec  # noqa: E402
from woodshop.render import (  # noqa: E402
    export_assembly,
    render_assembly,
    render_cut_list,
)

#: length along +Y, width up (+Z), thickness across (+X) — a runner, the
#: ledger, a stile seen side-on: a board on edge running front to back.
_FRONT_TO_BACK = Rotation(0, 90, 90)

#: thickness across (+X), width through (+Y), length up (+Z) — a stile.
_UPRIGHT = Rotation(0, 90, 0)

#: length along +X, width up (+Z), thickness through (+Y) — a block fitted
#: flat between two back-wall studs, its face in the wall plane.
_FLAT_IN_WALL = Rotation(90, 0, 0)

#: Lateral design value assumed for one #8 screw through 3/4" pine into a
#: stud, lb.  An assumption rounded well down, not a tabulated figure: the
#: demand it is compared against is a few tens of pounds, so the check is
#: about order of magnitude, not the third significant figure.
_RUNNER_SCREW_SHEAR_LB: float = 60.0

#: Screws per runner at each stud or stile it lands on.
_SCREWS_PER_LANDING: int = 2

#: Newtons per pound-force.
_N_PER_LBF: float = 4.4482216

#: How tall to draw the existing studs, inches — context only.
_WALL_DRAWN_H_IN: float = 66.0


@dataclass
class CornerToteTower:
    """A column of rim-hung totes in a stud corner, with one leg.

    Parameters
    ----------
    bin_key : str, optional
        Key in :data:`basement_bench.BIN_TYPES`, default ``"17gal"``.
    tiers : int, optional
        Totes stacked in the column, default 4.
    stud_spacing_in : float, optional
        Stud spacing on centre on both walls, default 16".
    corner_stud : bool, optional
        Whether each wall has a stud at the corner itself, its face in the
        wall plane and its centre 3/4" from the other wall, default ``True``
        — corner framing almost always has one.  The next studs are then at
        ``stud_spacing_in`` and its multiples from the corner.
    bin_side_clearance_in : float, optional
        Clear space between the rim and the face it slides past each side,
        default 3/8".  With a 3/4" runner it also sets the lip's bearing.
    bin_head_clearance_in : float, optional
        Clear space above each lid, default 1/2".
    bin_back_clearance_in : float, optional
        Clear space behind each tote, in front of the back wall, default 1/2".
    floor_clearance_in : float, optional
        Underside of the bottom tote off the slab, default 2".
    bin_mass_kg : float, optional
        Mass of one full tote, default
        :data:`basement_bench.BIN_DESIGN_MASS_KG`.
    frame_species, frame_nominal : str, optional
        Leg, stile, top rail and blocking, default pine 2x4.
    runner_nominal : str, optional
        Runners and the top ledger, default 1x4.
    slat_nominal : str, optional
        Top slats, default 1x6.
    n_slats : int, optional
        Top slats, default 4.
    foot_species, foot_nominal : str, optional
        The pad under the leg, default ground-contact PT (``"syp_pt"``) 2x4.
    inventory : Inventory, optional
        Stock inventory.  Loaded from ``stock.yaml`` if not given.

    Raises
    ------
    ValueError
        If the tote key is unknown, if fewer than one tier is asked for, if
        the lip misses the runners or the body binds on them, if the runner
        above comes down on a lid, or if a wall-side runner crosses fewer than
        two studs.
    """

    bin_key: str = "17gal"
    tiers: int = 4
    stud_spacing_in: float = 16.0
    corner_stud: bool = True
    bin_side_clearance_in: float = 0.375
    bin_head_clearance_in: float = 0.5
    bin_back_clearance_in: float = 0.5
    floor_clearance_in: float = 2.0
    bin_mass_kg: float = BIN_DESIGN_MASS_KG

    frame_species: str = "pine"
    frame_nominal: str = "2x4"
    runner_nominal: str = "1x4"
    slat_nominal: str = "1x6"
    n_slats: int = 4
    foot_species: str = "syp_pt"
    foot_nominal: str = "2x4"

    inventory: Inventory = field(default_factory=Inventory.load)

    def __post_init__(self) -> None:
        """Reject a tower whose numbers do not describe one."""
        if self.bin_key not in BIN_TYPES:
            raise ValueError(
                f"unknown bin {self.bin_key!r}; known: {sorted(BIN_TYPES)}"
            )
        if self.tiers < 1:
            raise ValueError(f"a tower needs at least one tier, got {self.tiers}")
        if self.lip_bearing <= 0.0:
            raise ValueError(
                f"the {self.bin.label} tote's rim falls between the runners: "
                f"bin_side_clearance_in={self.bin_side_clearance_in:g} is as "
                f"much as a {self.runner_nominal} reaches out"
            )
        if self.body_clearance <= 0.0:
            raise ValueError(
                f"the {self.bin.label} tote's body binds on the runners"
            )
        stack = (
            inches(self.bin.lip_drop_in)
            + self.runner_h
            + inches(self.bin_head_clearance_in)
        )
        if self.pitch < stack:
            raise ValueError(
                "the runner above each tote comes down onto its lid"
            )
        if len(self.side_studs_under_runner) < 2:
            raise ValueError(
                f"a {mm_to_fractional_inch(self.depth)} runner crosses only "
                f"{len(self.side_studs_under_runner)} side-wall stud(s) — it "
                "needs two to stay level"
            )

    # ------------------------------------------------------------------
    # The tote and the stock
    # ------------------------------------------------------------------

    @property
    def bin(self) -> Bin:
        """The tote the column holds."""
        return BIN_TYPES[self.bin_key]

    @staticmethod
    def _dims(nominal: str) -> tuple[float, float]:
        """Return the (thickness, width) of a nominal size, mm."""
        t, w = actual_dimensions_mm(nominal)
        return float(t.magnitude), float(w.magnitude)

    @property
    def stile_t(self) -> float:
        """Thickness of the 2x4 frame members, mm."""
        return self._dims(self.frame_nominal)[0]

    @property
    def stile_w(self) -> float:
        """Face width of the 2x4 frame members, mm."""
        return self._dims(self.frame_nominal)[1]

    @property
    def runner_t(self) -> float:
        """How far a runner stands out from what it is screwed to, mm."""
        return self._dims(self.runner_nominal)[0]

    @property
    def runner_h(self) -> float:
        """Height of a runner, mm."""
        return self._dims(self.runner_nominal)[1]

    @property
    def slat_t(self) -> float:
        """Thickness of a top slat, mm."""
        return self._dims(self.slat_nominal)[0]

    @property
    def slat_w(self) -> float:
        """Width of a top slat, mm."""
        return self._dims(self.slat_nominal)[1]

    @property
    def foot_t(self) -> float:
        """Thickness of the PT pad under the leg, mm."""
        return self._dims(self.foot_nominal)[0]

    @property
    def foot_w(self) -> float:
        """Width of the PT pad — and its length, cut square, mm."""
        return self._dims(self.foot_nominal)[1]

    # ------------------------------------------------------------------
    # Plan: across (x, from the side-wall studs) and deep (d, from the back)
    # ------------------------------------------------------------------

    @property
    def bay_w(self) -> float:
        """Clear width from the side-wall stud faces to the open frame, mm."""
        return inches(self.bin.width_in) + 2 * inches(self.bin_side_clearance_in)

    @property
    def open_x(self) -> tuple[float, float]:
        """(inner face, outer face) of the open side's leg and stile, mm."""
        return (self.bay_w, self.bay_w + self.stile_t)

    @property
    def width(self) -> float:
        """Overall width, side-wall stud faces to the outside of the leg, mm."""
        return self.open_x[1]

    @property
    def depth(self) -> float:
        """Overall depth from the back-wall stud faces, mm.

        The gap behind the tote and the tote: its front is flush with the
        runners' ends and the leg's face.
        """
        return inches(self.bin_back_clearance_in) + inches(self.bin.length_in)

    @property
    def leg_d(self) -> tuple[float, float]:
        """(back face, front face) of the leg, mm from the back wall."""
        return (self.depth - self.stile_w, self.depth)

    @property
    def lip_bearing(self) -> float:
        """How far a runner reaches under the tote's lip, per side, mm."""
        return self.runner_t - inches(self.bin_side_clearance_in)

    @property
    def body_clearance(self) -> float:
        """Clear space between the tote's body and each runner, mm."""
        return inches(self.bin.lip_in) - self.lip_bearing

    def _stud_centres(self, length: float) -> list[float]:
        """Return stud centres along a wall, mm from the corner.

        Parameters
        ----------
        length : float
            How far along the wall to list them.

        Returns
        -------
        list of float
            The corner stud (if any) and every one at the spacing after it.
        """
        spacing = inches(self.stud_spacing_in)
        centres = [self.stile_t / 2] if self.corner_stud else []
        k = 1
        while k * spacing - self.stile_t / 2 < length:
            centres.append(k * spacing)
            k += 1
        return centres

    @property
    def side_studs_under_runner(self) -> list[float]:
        """Centres of the side-wall studs a wall-side runner lands on, mm."""
        half = self.stile_t / 2
        return [
            c
            for c in self._stud_centres(self.depth)
            if c - half >= 0.0 and c + half <= self.depth
        ]

    @property
    def wall_overhang(self) -> float:
        """How far a wall-side runner runs past its front stud, mm."""
        return self.depth - (self.side_studs_under_runner[-1] + self.stile_t / 2)

    @property
    def wall_back_span(self) -> float:
        """Centre to centre of a wall-side runner's back and front studs, mm."""
        studs = self.side_studs_under_runner
        return studs[-1] - studs[0]

    @property
    def back_studs(self) -> list[float]:
        """Back-wall stud centres out past the open side, mm from the corner."""
        return self._stud_centres(self.width + inches(self.stud_spacing_in))

    @property
    def stile_bay(self) -> tuple[float, float] | None:
        """(left, right) faces of the back-wall stud bay the back stile hangs in.

        ``None`` when the stile lands on a stud instead, and screws straight
        to it with no blocking at all.
        """
        x0, x1 = self.open_x
        half = self.stile_t / 2
        studs = self.back_studs
        for c in studs:
            if c - half < x1 and c + half > x0:
                return None
        left = max(c + half for c in studs if c + half <= x0)
        right = min(c - half for c in studs if c - half >= x1)
        return (left, right)

    # ------------------------------------------------------------------
    # Heights off the slab
    # ------------------------------------------------------------------

    @property
    def pitch(self) -> float:
        """Tote to tote, mm — the tote and its head clearance, no runner."""
        return inches(self.bin.height_in) + inches(self.bin_head_clearance_in)

    def tote_z(self, tier: int) -> tuple[float, float]:
        """Return the (base, lid) of one tote, mm off the slab, tier 0 lowest.

        Parameters
        ----------
        tier : int
            Tier index.

        Returns
        -------
        tuple of float
            Underside of the tote and top of its lid.
        """
        base = inches(self.floor_clearance_in) + tier * self.pitch
        return (base, base + inches(self.bin.height_in))

    def runner_z(self, tier: int) -> tuple[float, float]:
        """Return the (bottom, top) of the runners one tote hangs on, mm.

        Parameters
        ----------
        tier : int
            Tier index.

        Returns
        -------
        tuple of float
            The runner's top is the underside of the lip.
        """
        top = self.tote_z(tier)[1] - inches(self.bin.lip_drop_in)
        return (top - self.runner_h, top)

    @property
    def frame_top_z(self) -> float:
        """Top of the leg and back stile, mm — the top tote's lid plus clearance."""
        return self.tote_z(self.tiers - 1)[1] + inches(self.bin_head_clearance_in)

    @property
    def slat_z(self) -> float:
        """Underside of the slats, mm — on top of the rail and ledger."""
        return self.frame_top_z + self.stile_w

    @property
    def height(self) -> float:
        """Overall height of the tower, mm."""
        return self.slat_z + self.slat_t

    @property
    def stile_bottom_z(self) -> float:
        """Foot of the back stile, mm — level with the lowest runner."""
        return self.runner_z(0)[0]

    @property
    def block_zs(self) -> list[tuple[float, float]]:
        """(bottom, top) of each block between the back-wall studs, mm."""
        return [
            (self.stile_bottom_z, self.stile_bottom_z + self.stile_w),
            (self.frame_top_z - self.stile_w, self.frame_top_z),
        ]

    # ------------------------------------------------------------------
    # Assembly
    # ------------------------------------------------------------------

    def build(self, show_wall: bool = False) -> Compound:
        """Build the tower as a positioned build123d assembly.

        Parameters
        ----------
        show_wall : bool, optional
            Also draw the existing studs the tower is fixed to, default
            ``False``.  They are context, not parts: leave this off for
            anything that reads the cut list.

        Returns
        -------
        build123d.Compound
            Every part, positioned.
        """
        children: list[object] = []
        x_wall = self.runner_t / 2
        x_open = self.open_x[0] - self.runner_t / 2
        x_stile = sum(self.open_x) / 2
        run_cy = -self.depth / 2

        for tier in range(self.tiers):
            z0, z1 = self.runner_z(tier)
            for x, label in ((x_wall, "wall_runner"), (x_open, "open_runner")):
                children.append(
                    Pos(x, run_cy, (z0 + z1) / 2)
                    * _FRONT_TO_BACK
                    * self._board(label, self.depth, self.runner_nominal)
                )

        leg_h = self.frame_top_z - self.foot_t
        children.append(
            Pos(x_stile, -sum(self.leg_d) / 2, self.foot_t + leg_h / 2)
            * _UPRIGHT
            * self._board("front_leg", leg_h, self.frame_nominal)
        )
        stile_h = self.frame_top_z - self.stile_bottom_z
        children.append(
            Pos(x_stile, -self.stile_w / 2, self.stile_bottom_z + stile_h / 2)
            * _UPRIGHT
            * self._board("back_stile", stile_h, self.frame_nominal)
        )
        children.append(
            Pos(x_stile, run_cy, self.frame_top_z + self.stile_w / 2)
            * _FRONT_TO_BACK
            * self._board("top_rail", self.depth, self.frame_nominal)
        )
        children.append(
            Pos(x_wall, run_cy, self.frame_top_z + self.runner_h / 2)
            * _FRONT_TO_BACK
            * self._board("top_ledger", self.depth, self.runner_nominal)
        )

        gap = (self.depth - self.n_slats * self.slat_w) / max(1, self.n_slats - 1)
        for i in range(self.n_slats):
            d = self.slat_w / 2 + i * (self.slat_w + gap)
            children.append(
                Pos(self.width / 2, -d, self.slat_z + self.slat_t / 2)
                * self._board("top_slat", self.width, self.slat_nominal)
            )

        children.append(
            Pos(self.width - self.foot_w / 2, -sum(self.leg_d) / 2, self.foot_t / 2)
            * self._board(
                "leg_foot", self.foot_w, self.foot_nominal, self.foot_species
            )
        )

        bay = self.stile_bay
        if bay is not None:
            length = bay[1] - bay[0]
            for z0, z1 in self.block_zs:
                children.append(
                    Pos((bay[0] + bay[1]) / 2, self.stile_t / 2, (z0 + z1) / 2)
                    * _FLAT_IN_WALL
                    * self._board("blocking", length, self.frame_nominal)
                )

        if show_wall:
            children.extend(self._existing_studs())
        return Compound(children=children, label="corner_tote_tower")

    def _existing_studs(self) -> list[object]:
        """Return the studs already in both walls, for drawings only."""
        h = inches(_WALL_DRAWN_H_IN)
        studs: list[object] = []
        half = self.stile_t / 2
        for c in self._stud_centres(self.depth + inches(self.stud_spacing_in)):
            studs.append(_box(-self.stile_w, 0.0, -c - half, -c + half, 0.0, h))
        for c in self.back_studs:
            studs.append(
                _box(c - self.stile_t / 2, c + self.stile_t / 2, 0.0, self.stile_w, 0.0, h)
            )
        for solid in studs:
            solid.label = "existing_stud"
            solid.material = "existing wall"
            solid.stock_length_mm = h
        return studs

    def _board(
        self, label: str, length_mm: float, nominal: str, species: str | None = None
    ) -> Board:
        """Return one part, with how it is fixed in its notes.

        Parameters
        ----------
        label : str
            Cut-list name.
        length_mm : float
            Length of the blank.
        nominal : str
            Nominal size.
        species : str, optional
            Defaults to ``frame_species``.

        Returns
        -------
        Board
            The part.
        """
        notes = {
            "wall_runner": (
                "on edge, flat face screwed to the side-wall studs it crosses, "
                f"{_SCREWS_PER_LANDING} #8 x 2-1/2\" per stud; shim behind it "
                "so all four are in one plumb plane. Wax the top edge"
            ),
            "open_runner": (
                "on edge, screwed to the inside faces of the back stile and "
                "the leg; level with its partner on the wall. Wax the top edge"
            ),
            "front_leg": (
                "the one leg: stands on the PT foot, carries the open side's "
                "front, top rail on its head"
            ),
            "back_stile": (
                "hangs on the two blocks, screwed through its face into each; "
                "stops short of the slab"
            ),
            "top_rail": "on edge across the heads of the leg and back stile",
            "top_ledger": (
                "on edge on the side-wall studs, level with the top rail; "
                "carries the slats' wall end"
            ),
            "top_slat": (
                "screwed down to the ledger and the top rail — the shelf, and "
                "the tie that keeps the leg from leaning out"
            ),
            "leg_foot": (
                "an offcut of ground-contact PT under the leg: brush "
                "preservative on the cut faces, screw it to the leg, and set "
                "it on the slab — no untreated end grain on concrete"
            ),
            "blocking": (
                "fitted flat between two back-wall studs, face flush with "
                "theirs, screwed through each stud into its ends"
            ),
        }[label]
        return Board(
            length_mm=length_mm,
            nominal=nominal,
            material=species or self.frame_species,
            label=label,
            notes=notes,
        )

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def check(self, assembly: Compound, parts: list[CutPart]) -> CheckReport:
        """Run every design check against a built tower.

        Parameters
        ----------
        assembly : build123d.Compound
            The built tower, without the wall.
        parts : list[CutPart]
            The consolidated cut list.

        Returns
        -------
        CheckReport
            Every finding.
        """
        report = CheckReport()
        report.extend(self._envelope_findings(assembly))
        report.extend(self._sweep_findings(assembly))
        report.extend(self._rack_findings())
        report.extend(self._overhang_findings())
        report.extend(self._fixing_findings())
        report.extend(self._site_findings())
        return report

    def _envelope_findings(self, assembly: Compound) -> list[Finding]:
        """Report the tower's size, and that the model agrees with it.

        Measured over the parts in the room: the blocking lives inside the
        back wall, between studs that run past the tower's open side.
        """
        boxes = [
            leaf.bounding_box() for leaf in assembly.leaves if leaf.label != "blocking"
        ]
        lo = [min(getattr(b.min, a) for b in boxes) for a in "XYZ"]
        hi = [max(getattr(b.max, a) for b in boxes) for a in "XYZ"]
        expected_lo = (0.0, -self.depth, 0.0)
        expected_hi = (self.width, 0.0, self.height)
        severity = (
            Severity.INFO
            if all(abs(a - b) < 0.1 for a, b in zip(lo + hi, expected_lo + expected_hi))
            else Severity.ERROR
        )
        return [
            Finding(
                severity,
                "envelope",
                f"{mm_to_fractional_inch(self.width)} wide from the side-wall "
                f"studs, {mm_to_fractional_inch(self.depth)} deep from the "
                f"back-wall studs, {mm_to_fractional_inch(self.height)} tall — "
                f"{self.tiers} x {self.bin.label} at "
                f"{mm_to_fractional_inch(self.pitch)} apart",
            )
        ]

    def tote_path(self, tier: int) -> list[Box]:
        """Return the space one tote sweeps from its seat out into the room.

        Parameters
        ----------
        tier : int
            Tier index.

        Returns
        -------
        list of build123d.Box
            The rim, full width, from the lid down to the underside of the
            lip, and the body, narrower by the lip each side, below it.
        """
        bin_ = self.bin
        z0, z1 = self.tote_z(tier)
        lip_z = z1 - inches(bin_.lip_drop_in)
        back = -inches(self.bin_back_clearance_in)
        front = -(self.depth + 500.0)
        cx = self.bay_w / 2
        cy = (back + front) / 2
        rim = Pos(cx, cy, (lip_z + z1) / 2) * Box(
            inches(bin_.width_in), back - front, z1 - lip_z
        )
        body = Pos(cx, cy, (z0 + lip_z) / 2) * Box(
            inches(bin_.body_w_in), back - front, lip_z - z0
        )
        return [rim, body]

    def _sweep_findings(self, assembly: Compound) -> list[Finding]:
        """Slide every tote out past the front and look for anything it hits."""
        hits = sorted(
            {
                (tier, leaf.label)
                for tier in range(self.tiers)
                for path in self.tote_path(tier)
                for leaf in assembly.leaves
                if (path & leaf).volume > 1.0
            }
        )
        if hits:
            return [
                Finding(
                    Severity.ERROR,
                    "clearance",
                    "totes hit the frame on their way out: "
                    + ", ".join(f"tier {t} on {label}" for t, label in hits),
                )
            ]
        return [
            Finding(
                Severity.INFO,
                "clearance",
                f"all {self.tiers} totes slide out past the front of the tower "
                "without touching any part of it",
            )
        ]

    def _rack_findings(self) -> list[Finding]:
        """Report the rim clearance, the lip bearing and the head room."""
        bin_ = self.bin
        message = (
            f"{self.runner_nominal} runners reach "
            f"{mm_to_fractional_inch(self.runner_t)} out, so the lip bears "
            f"{mm_to_fractional_inch(self.lip_bearing)} a side and the body "
            f"clears them by {mm_to_fractional_inch(self.body_clearance)}"
        )
        if not bin_.lip_measured:
            message += (
                f"; the {mm_to_fractional_inch(inches(bin_.lip_in))} lip is a "
                "published build's figure, not measured on this tote — put a "
                "tape on it before screwing a runner on"
            )
        findings = check_clearance(
            "each side of the tote's rim, to the stud faces and to the leg",
            inches(self.bin_side_clearance_in),
            inches(0.25),
            inches(0.5),
            tight_note="a tote goes in crooked; under a quarter inch it binds",
            loose_note="clearance past the runner comes off the lip's bearing",
        )
        findings.append(Finding(Severity.INFO, "rack", message))
        findings.append(
            Finding(
                Severity.INFO,
                "rack",
                f"{mm_to_fractional_inch(inches(self.bin_head_clearance_in))} "
                "over each lid, and the bottom tote "
                f"{mm_to_fractional_inch(inches(self.floor_clearance_in))} off "
                f"the slab — clear of the {mm_to_fractional_inch(self.foot_t)} "
                "PT foot",
            )
        )
        return findings

    def _overhang_findings(self) -> list[Finding]:
        """Work a wall-side runner's overhang, tote pulled out to the tip.

        The worst case for the overhang: a tote pulled forward until its back
        end is at the runner's tip, so half its weight hangs there as a point
        load.  An overhanging beam on two supports: tip deflection
        ``P a² (L + a) / 3EI``; the back stud is pulled *up* by ``P a / L``,
        the front stud pushed down by ``P (L + a) / L``.
        """
        a = self.wall_overhang
        span = self.wall_back_span
        p_n = self.bin_mass_kg * 9.80665 / 2
        e_mpa = ELASTIC_MODULUS_MPA[self.frame_species]
        i_mm4 = self.runner_t * self.runner_h**3 / 12.0
        tip = p_n * a**2 * (span + a) / (3 * e_mpa * i_mm4)
        limit = a / 180.0
        front_lb = p_n * (span + a) / span / _N_PER_LBF
        back_lb = p_n * a / span / _N_PER_LBF
        cap_lb = _SCREWS_PER_LANDING * _RUNNER_SCREW_SHEAR_LB
        return [
            Finding(
                Severity.INFO if tip <= limit else Severity.WARN,
                "deflection",
                f"a wall-side runner lands on studs "
                f"{mm_to_fractional_inch(span)} apart and overhangs the front "
                f"one by {mm_to_fractional_inch(a)}; with a tote pulled out to "
                f"the tip it dips {tip:.2f} mm (limit {limit:.1f} mm, "
                "overhang/180)",
            ),
            Finding(
                Severity.INFO if cap_lb / front_lb >= 2.5 else Severity.WARN,
                "joint",
                f"in that case the front stud's screws carry {front_lb:.0f} lb "
                f"and the back stud's {back_lb:.0f} lb (upward), against about "
                f"{cap_lb:.0f} lb for {_SCREWS_PER_LANDING} #8 screws in "
                f"shear — assumed, not tabulated — {cap_lb / front_lb:.1f}x",
            ),
        ]

    def _fixing_findings(self) -> list[Finding]:
        """Report how the open side is held: the blocking, the leg, the foot."""
        bay = self.stile_bay
        if bay is None:
            stile = Finding(
                Severity.INFO,
                "wall",
                "the back stile lands on a back-wall stud: screw it straight "
                "to the stud, no blocking needed",
            )
        else:
            stile = Finding(
                Severity.INFO,
                "wall",
                f"the back stile falls in the stud bay "
                f"{mm_to_fractional_inch(bay[0])}–"
                f"{mm_to_fractional_inch(bay[1])} from the corner, so it "
                f"hangs on two {mm_to_fractional_inch(bay[1] - bay[0])} blocks "
                "fitted between those studs, flush with their faces — a cleat "
                "across the stud faces would stand where the back of a tote "
                "goes. This assumes the bays are open behind the studs",
            )
        tote_kg = self.tiers * self.bin_mass_kg
        leg_lb = tote_kg / 4 * 9.80665 / _N_PER_LBF
        pad_in2 = (self.foot_w / IN) ** 2
        return [
            stile,
            Finding(
                Severity.INFO,
                "load",
                f"{self.tiers} full totes are {tote_kg:.0f} kg; the leg carries "
                f"about a quarter of it, {leg_lb:.0f} lb, onto a "
                f"{mm_to_fractional_inch(self.foot_w)} square PT pad — "
                f"{leg_lb / pad_in2:.0f} psi, which neither the pad nor the "
                "slab will notice",
            ),
        ]

    def _site_findings(self) -> list[Finding]:
        """Report what the model cannot see."""
        return [
            Finding(
                Severity.WARN,
                "site",
                "both walls get screws: find out what is in those stud bays "
                "first — wiring and water lines run there",
            ),
            Finding(
                Severity.WARN,
                "site",
                "exposed basement studs are rarely in one plumb plane, and "
                f"the lip only bears {mm_to_fractional_inch(self.lip_bearing)}: "
                "check the side-wall stud faces with a straightedge and shim "
                "each runner to match its partner on the leg",
            ),
            Finding(
                Severity.INFO,
                "site",
                "screwed to both walls, the tower cannot tip or rack; the "
                "slats tie the leg's head back to the side wall",
            ),
        ]


def _box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> Box:
    """Return an axis-aligned box spanning the given world ranges, mm."""
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(
        x1 - x0, y1 - y0, z1 - z0
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def run(tower: CornerToteTower, outdir: Path) -> CheckReport:
    """Build the tower, write its cut list and drawings, print the report.

    Parameters
    ----------
    tower : CornerToteTower
        The tower to build.
    outdir : Path
        Directory for the generated CSV, Markdown, PNG and CAD files.

    Returns
    -------
    CheckReport
        The design-check findings.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    assembly = tower.build()
    parts = extract(assembly)
    stem = "corner_tote_tower"
    print(f"\n{'=' * 78}\n  Corner tote tower\n{'=' * 78}")

    df = render_cut_list(
        parts,
        output_csv=outdir / f"{stem}_cutlist.csv",
        output_md=outdir / f"{stem}_cutlist.md",
    )
    print(df.to_string(index=False))

    report = tower.check(assembly, parts)
    print(f"\n-- design checks {'-' * 61}")
    print(report.to_text())

    print(f"\n-- prices {'-' * 68}")
    print(CheckReport().extend(check_price_provenance(tower.inventory, parts)).to_text())

    print(f"\n-- to buy {'-' * 68}")
    for species in dict.fromkeys(p.material for p in parts):
        group = [p for p in parts if p.material == species]
        lengths = tower.inventory.stock_lengths_mm(species)
        if not lengths:
            names = ", ".join(f"{p.label} {p.length_in}" for p in group)
            print(f"  {species}: {names} — from the offcut bin")
            continue
        for nominal in dict.fromkeys(_nominal(p, tower) for p in group):
            same = [p for p in group if _nominal(p, tower) == nominal]
            sized = [
                mm
                for d in tower.inventory.dimensional
                if d.species == species and d.nominal == nominal
                for mm in d.lengths_mm
            ]
            result = optimize_1d(same, stock_lengths_mm=sorted(sized) or lengths)
            print(f"  {species} {nominal}: {result.stock_used} board(s)")
            for piece, cuts in zip(result.pieces, result.assignments):
                labels = ", ".join(
                    f"{lbl} {mm_to_fractional_inch(mm)}" for lbl, mm in cuts
                )
                print(
                    f"    {piece.stock_length_mm / IN / 12:.0f} ft: {labels}  "
                    f"| offcut {mm_to_fractional_inch(piece.waste_mm)}"
                )

    render_assembly(
        tower.build(show_wall=True),
        output_png=outdir / f"{stem}.png",
        title="Corner tote tower — existing studs in grey",
    )
    export_assembly(
        assembly,
        output_step=outdir / f"{stem}.step",
        output_stl=outdir / f"{stem}.stl",
    )
    print(f"\nWrote cut list, drawings and CAD export to {outdir}/")
    return report


def _nominal(part: CutPart, tower: CornerToteTower) -> str:
    """Return the nominal size a cut part is cut from, e.g. ``"2x4"``."""
    for nominal in (tower.frame_nominal, tower.runner_nominal, tower.slat_nominal):
        t, w = tower._dims(nominal)
        if abs(part.thickness_mm - t) < 0.01 and abs(part.width_mm - w) < 0.01:
            return nominal
    return f"{part.thickness_in} x {part.width_in}"


def _spec() -> ProjectSpec:
    """Return the gallery entry."""
    tower = CornerToteTower()
    return ProjectSpec(
        slug="corner-tote-tower",
        name="Corner tote tower",
        summary=(
            f"{tower.tiers} x {tower.bin.label} totes hung by their rims in a "
            f"basement stud corner: {mm_to_fractional_inch(tower.width)} wide, "
            f"{mm_to_fractional_inch(tower.depth)} deep, "
            f"{mm_to_fractional_inch(tower.height)} tall, one leg."
        ),
        species=tower.frame_species,
        build=tower.build,
        check=tower.check,
        inventory=tower.inventory,
        notes=(
            "The side wall's studs carry the runners on that side directly; "
            "the open side is one leg on a PT foot and a back stile hung on "
            "blocking between the back-wall studs. No plywood, no back panel "
            "— the two walls stop it racking and tipping."
        ),
        tags=["shop", "storage", "wall-mounted"],
    )


#: Projects this module contributes to the gallery.
PROJECTS: list[ProjectSpec] = [_spec()]


def main() -> None:
    """Parse arguments and build the tower."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bin", default="17gal", choices=sorted(BIN_TYPES))
    parser.add_argument("--tiers", type=int, default=4)
    parser.add_argument("--stud-spacing", type=float, default=16.0)
    parser.add_argument(
        "--no-corner-stud",
        action="store_true",
        help="the first stud on each wall is at the spacing, not in the corner",
    )
    parser.add_argument("--outdir", type=Path, default=Path("build"))
    args = parser.parse_args()
    run(
        CornerToteTower(
            bin_key=args.bin,
            tiers=args.tiers,
            stud_spacing_in=args.stud_spacing,
            corner_stud=not args.no_corner_stud,
        ),
        args.outdir,
    )


if __name__ == "__main__":
    main()
