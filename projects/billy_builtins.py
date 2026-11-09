"""Billy built-ins — two IKEA BILLY bookcases made to look built in, either side of the bay.

The "Billy hack": buy the flat-pack carcasses, stand them on a riser, and
dress the front in paint-grade poplar — a face frame scribed to the walls,
baseboard across the bottom, and fascia up to the ceiling — so the room
reads one piece of joinery instead of two bookcases.  Everything that is
*cut* is on the cut list; the BILLYs and the heat pump are drawn, not cut
(:class:`woodshop.parts.Purchased`), and appear on the shopping list.

The two sections
----------------
* **Right**, 37-1/2" wall to wall: a BILLY 80x28x202 with the 80x28x35
  height-extension unit on top, and a header rail closing the last inch to
  the ceiling.
* **Left**, 42" wall to wall: a BILLY 80x28x202 on its own.  Above it hangs
  the mini-split head, and the fascia goes up to the ceiling *around* it —
  stiles either side, open in front, so the unit keeps the clearances its
  installation manual asks for.

Measured, assumed, and looked up
--------------------------------
Measured by the owner: the two widths, 37-1/2" and 42".

Looked up: BILLY 80x28x202 cm and the 80x28x35 cm height extension (237 cm
stacked, IKEA's own combination listing); the extension's dowels need about
7 mm of lift to drop on, so the ceiling must clear the stack by that much.
Mitsubishi MSZ-GS indoor unit, 31-7/16" x 11-5/8" x 9-1/8", whose
installation manual asks 2-1/8" to the ceiling (5-1/8" with left or
left-rear piping on the spacer), 3-7/8" to the left and 4-3/8" to the right.

**Assumed, and every one of them a parameter** — measure before cutting:

* ceiling height, 96" (the right stack has 7/16" to spare at 96");
* the heat pump is a GS-size head, hung as high as its ceiling clearance
  allows (``heat_pump_bottom_in`` takes the real height if it is up);
* BILLY panels 15 mm, kick plate 3-1/4" (bottom-shelf top above the base);
* 5-1/2" baseboard (poplar 1x6) — the riser makes up the difference so
  the bottom shelf lands flush with the baseboard top;
* 4" of open air below the heat pump's outlet louvre.  Not a manufacturer
  number — the GS manual says only "where airflow is not blocked" — but the
  louvre throws down and forward, and a case top inches under it deflects
  the discharge straight back along the wall.

The default ceiling is where this design is tightest, and the checks say
so: at 96" the outlet sits half an inch above the left BILLY.

Run it
------
::

    uv run python projects/billy_builtins.py
    uv run python projects/billy_builtins.py --ceiling 100 --heat-pump-bottom 84
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, field
from pathlib import Path

from build123d import Compound, Pos, Rotation

from woodshop.checks import (
    CheckReport,
    Finding,
    Severity,
    check_envelope,
    check_material_suitability,
    check_price_provenance,
    check_shelf_deflection,
)
from woodshop.cutlist.extract import CutPart, extract, purchased_items
from woodshop.inventory import Inventory
from woodshop.lumber import mm_to_fractional_inch
from woodshop.parts import Board, Purchased
from woodshop.project import ProjectSpec
from woodshop.render import export_assembly, render_assembly, render_cut_list

IN = 25.4

#: Rotations from a Board's birth frame (length X, width Y, thickness Z).
_ON_EDGE = Rotation(90, 0, 0)  # length X, width up, thickness along Y
_UPRIGHT = Rotation(0, 0, -90) * Rotation(0, -90, 0)  # length up, width X, thickness Y
_UPRIGHT_SIDEWAYS = Rotation(0, -90, 0)  # length up, width Y, thickness X
_ON_EDGE_DEEP = Rotation(0, 0, 90) * _ON_EDGE  # length Y, width up, thickness X

#: Dressed 1-by widths, for saying which board a rip comes out of.
_ONE_BY_WIDTHS_IN: tuple[tuple[str, float], ...] = (
    ("1x2", 1.5),
    ("1x3", 2.5),
    ("1x4", 3.5),
    ("1x6", 5.5),
    ("1x8", 7.25),
    ("1x10", 9.25),
    ("1x12", 11.25),
)

BILLY = "BILLY bookcase 80x28x202 cm, white"
BILLY_EXT = "BILLY height extension unit 80x28x35 cm, white"
HEAT_PUMP = "mini-split head (existing / by the HVAC installer)"


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


def rip_source(width_mm: float) -> str:
    """Name the narrowest dressed 1-by a part of *width_mm* can be ripped from.

    Parameters
    ----------
    width_mm : float
        Finished width.

    Returns
    -------
    str
        e.g. ``"1x4"``, or a glue-up note past a 1x12.
    """
    for nominal, width_in in _ONE_BY_WIDTHS_IN:
        if width_mm <= inches(width_in) + 0.01:
            return nominal
    return "glue-up (wider than a 1x12)"


def _box(
    x0: float, x1: float, y0: float, y1: float, z0: float, z1: float
) -> tuple[Pos, float, float, float]:
    """Return the centre and sizes of an axis-aligned span."""
    return (
        Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2),
        x1 - x0,
        y1 - y0,
        z1 - z0,
    )


@dataclass
class BillyBuiltIns:
    """Two BILLY bookcases built in either side of a bay window.

    World frame: X runs along the wall left to right as seen from the room,
    the wall face is ``y = 0`` with the room at -Y, and ``z = 0`` is the
    floor.  The left section's left wall is ``x = 0``.

    Parameters
    ----------
    left_width_in, right_width_in : float, optional
        Wall-to-wall width of each alcove, default the measured 42" and
        37-1/2".
    bay_opening_in : float, optional
        Width between the two sections, default 72" — a guess, used only to
        lay the drawing out.  Nothing is built there.
    ceiling_in : float, optional
        Floor to ceiling, default 96" (assumed).  The one number this design
        is most sensitive to: it decides whether the extension fits on the
        right and whether the heat pump breathes on the left.
    baseboard_in : float, optional
        Baseboard height, default 5-1/2" (a 1x6).  Match the room's.
    billy_kick_in : float, optional
        Height of the BILLY's bottom-shelf top above its own base, default
        3-1/4" (assumed; measure the assembled case).
    billy_panel_mm : float, optional
        BILLY side/top panel thickness, default 15 mm (assumed).
    heat_pump_width_in, heat_pump_height_in, heat_pump_depth_in : float, optional
        Indoor unit size, default a Mitsubishi MSZ-GS (31-7/16 x 11-5/8 x
        9-1/8).
    heat_pump_bottom_in : float or None, optional
        Underside of the indoor unit above the floor.  ``None`` (default)
        hangs it as high as ``heat_pump_ceiling_clearance_in`` allows.
    heat_pump_ceiling_clearance_in : float, optional
        Manufacturer's minimum to the ceiling, default 2-1/8" (MSZ-GS; 5-1/8"
        with left or left-rear piping on the spacer).
    heat_pump_left_clearance_in, heat_pump_right_clearance_in : float, optional
        Manufacturer's side minimums, default 3-7/8" and 4-3/8" (MSZ-GS),
        left and right *as seen facing the unit*.
    outlet_clearance_in : float, optional
        Open air required between the top of the left case and the unit's
        underside, default 4" — a judgement, not a manufacturer figure.
    upper_stile_in : float, optional
        Width of the left section's stiles above the BILLY, default 1-1/2".
        Narrower than the stiles below so they frame the heat pump rather
        than masking its ends.
    rail_in : float, optional
        Face-frame rail width (mid rail, left top rail, minimum header),
        default 1-1/2".
    shelf_load_kg : float, optional
        Books on one BILLY shelf for the sag check, default 15 kg — a shelf
        of hardbacks.  IKEA rates the shelf at 30 kg.
    inventory : Inventory, optional
        Stock inventory, loaded from ``stock.yaml`` if not given.

    Raises
    ------
    ValueError
        If an alcove is narrower than a BILLY, or the riser the baseboard
        asks for cannot be ripped out of a 2x4.
    """

    left_width_in: float = 42.0
    right_width_in: float = 37.5
    bay_opening_in: float = 72.0
    ceiling_in: float = 96.0
    baseboard_in: float = 5.5
    billy_kick_in: float = 3.25
    billy_panel_mm: float = 15.0
    heat_pump_width_in: float = 31.0 + 7 / 16
    heat_pump_height_in: float = 11.625
    heat_pump_depth_in: float = 9.125
    heat_pump_bottom_in: float | None = None
    heat_pump_ceiling_clearance_in: float = 2.125
    heat_pump_left_clearance_in: float = 3.875
    heat_pump_right_clearance_in: float = 4.375
    outlet_clearance_in: float = 4.0
    upper_stile_in: float = 1.5
    rail_in: float = 1.5
    shelf_load_kg: float = 15.0

    inventory: Inventory = field(default_factory=Inventory.load)

    #: BILLY, per IKEA: 80 x 28 x 202 cm, extension 35 cm tall.
    billy_width_mm: float = 800.0
    billy_depth_mm: float = 280.0
    billy_height_mm: float = 2020.0
    extension_height_mm: float = 350.0
    #: Lift the extension needs to drop onto its dowels (IKEA reviewers).
    extension_lift_mm: float = 7.0
    #: Paint-grade face frame and baseboard: dressed 3/4" poplar.
    trim_thickness_mm: float = 19.05

    def __post_init__(self) -> None:
        """Refuse an alcove a BILLY will not go into."""
        for side, width in (("left", self.left_width_in), ("right", self.right_width_in)):
            if inches(width) < self.billy_width_mm:
                raise ValueError(
                    f'{side} alcove is {width:g}" — narrower than a BILLY\'s '
                    f'{self.billy_width_mm / IN:.2f}"'
                )
        if self.riser_height_mm > inches(3.5):
            raise ValueError(
                f"a {self.riser_height_mm / IN:.2f}\" riser is more than a 2x4 "
                "on edge — use a taller riser stock or a lower baseboard"
            )

    # ------------------------------------------------------------------
    # Derived geometry
    # ------------------------------------------------------------------

    @property
    def ceiling(self) -> float:
        """Ceiling height, mm."""
        return inches(self.ceiling_in)

    @property
    def riser_height_mm(self) -> float:
        """Riser height, mm: lifts the bottom shelf flush with the baseboard top."""
        return max(0.0, inches(self.baseboard_in - self.billy_kick_in))

    @property
    def billy_top(self) -> float:
        """Top of either BILLY above the floor, mm."""
        return self.riser_height_mm + self.billy_height_mm

    @property
    def extension_top(self) -> float:
        """Top of the right section's extension unit above the floor, mm."""
        return self.billy_top + self.extension_height_mm

    @property
    def face_y(self) -> float:
        """Back face of the face frame (the BILLY front edges), mm."""
        return -self.billy_depth_mm

    def filler(self, width_in: float) -> float:
        """Gap from each side wall to a centred BILLY, mm."""
        return (inches(width_in) - self.billy_width_mm) / 2

    def stile_width(self, width_in: float) -> float:
        """Lower stile width, mm: the filler plus the BILLY side it laps."""
        return self.filler(width_in) + self.billy_panel_mm

    @property
    def right_header_height(self) -> float:
        """Right header, mm: from the extension's inside top to the ceiling."""
        return max(
            inches(self.rail_in),
            self.ceiling - (self.extension_top - self.billy_panel_mm),
        )

    @property
    def heat_pump_bottom(self) -> float:
        """Underside of the heat pump above the floor, mm."""
        if self.heat_pump_bottom_in is not None:
            return inches(self.heat_pump_bottom_in)
        return (
            self.ceiling
            - inches(self.heat_pump_ceiling_clearance_in)
            - inches(self.heat_pump_height_in)
        )

    @property
    def heat_pump_top(self) -> float:
        """Top of the heat pump above the floor, mm."""
        return self.heat_pump_bottom + inches(self.heat_pump_height_in)

    @property
    def left_header_height(self) -> float:
        """Left header, mm, or 0 when it would crowd the heat pump.

        The header runs across the front of the unit, so it may only occupy
        the band *above* the unit's ceiling clearance — anything lower sits
        in front of the intake grille on top and stops the front panel
        lifting for the filters.  Matches the right header when it can; a
        sliver under 3/4" is not worth nailing up and is left out.
        """
        room = self.ceiling - (
            self.heat_pump_top + inches(self.heat_pump_ceiling_clearance_in)
        )
        height = min(self.right_header_height, room)
        return height if height >= inches(0.75) else 0.0

    @property
    def right_x0(self) -> float:
        """Left wall of the right section, mm."""
        return inches(self.left_width_in + self.bay_opening_in)

    @property
    def heat_pump_x0(self) -> float:
        """Left end of the heat pump, mm — centred in the left section."""
        return (inches(self.left_width_in) - inches(self.heat_pump_width_in)) / 2

    # ------------------------------------------------------------------
    # Assembly
    # ------------------------------------------------------------------

    def build(self) -> Compound:
        """Build both sections, the BILLYs, and the heat pump, positioned.

        Returns
        -------
        build123d.Compound
            ``left`` and ``right`` sub-assemblies plus the heat pump.
        """
        left = self._section("left", 0.0, self.left_width_in, extension=False)
        right = self._section(
            "right", self.right_x0, self.right_width_in, extension=True
        )
        hp_pos, hx, hy, hz = _box(
            self.heat_pump_x0,
            self.heat_pump_x0 + inches(self.heat_pump_width_in),
            -inches(self.heat_pump_depth_in),
            0.0,
            self.heat_pump_bottom,
            self.heat_pump_top,
        )
        heat_pump = hp_pos * Purchased(
            hx, hy, hz, material="heat_pump", label="heat_pump", item=HEAT_PUMP
        )
        return Compound(children=[left, right, heat_pump], label="billy_builtins")

    def _section(
        self, side: str, x0: float, width_in: float, *, extension: bool
    ) -> Compound:
        """Build one alcove: riser, BILLY (and extension), face frame, trim."""
        width = inches(width_in)
        f = self.filler(width_in)
        s = self.stile_width(width_in)
        t = self.trim_thickness_mm
        fy0, fy1 = self.face_y - t, self.face_y  # face-frame plane
        children: list[object] = []

        children += self._riser(side, x0 + f)
        children += self._billy(side, x0 + f, self.riser_height_mm, extension)

        # Stiles: full height on the right; on the left they stop at the
        # case top and narrower uppers carry on to the ceiling.
        lower_top = self.ceiling if extension else self.billy_top
        for x_a, x_b in ((x0, x0 + s), (x0 + width - s, x0 + width)):
            children.append(
                self._trim(
                    f"{side}_stile",
                    x_a, x_b, fy0, fy1, 0.0, lower_top,
                    orient="upright",
                    notes=(
                        "scribed to the wall; glued and brad-nailed to the "
                        "BILLY side, which it laps by its panel thickness"
                    ),
                )
            )
        if not extension:
            u = inches(self.upper_stile_in)
            for x_a, x_b in ((x0, x0 + u), (x0 + width - u, x0 + width)):
                children.append(
                    self._trim(
                        f"{side}_upper_stile",
                        x_a, x_b, fy0, fy1, self.billy_top, self.ceiling,
                        orient="upright",
                        notes=(
                            "frames the heat pump; scribed to wall and "
                            "ceiling, nailed to the wall nailer"
                        ),
                    )
                )

        inner0, inner1 = x0 + s, x0 + width - s
        rail = inches(self.rail_in)
        children.append(
            self._trim(
                f"{side}_bottom_rail",
                inner0, inner1, fy0, fy1, 0.0, inches(self.baseboard_in),
                orient="rail",
                notes="backer for the baseboard; top flush with the bottom shelf",
            )
        )
        if extension:
            seam = self.billy_top
            children.append(
                self._trim(
                    f"{side}_mid_rail",
                    inner0, inner1, fy0, fy1, seam - rail / 2, seam + rail / 2,
                    orient="rail",
                    notes="covers the BILLY / extension seam",
                )
            )
            hh = self.right_header_height
            children.append(
                self._trim(
                    f"{side}_header",
                    inner0, inner1, fy0, fy1, self.ceiling - hh, self.ceiling,
                    orient="rail",
                    notes="fascia to the ceiling; scribed to it",
                )
            )
        else:
            children.append(
                self._trim(
                    f"{side}_top_rail",
                    inner0, inner1, fy0, fy1, self.billy_top - rail, self.billy_top,
                    orient="rail",
                    notes="top flush with the BILLY top — nothing proud under the outlet",
                )
            )
            hh = self.left_header_height
            if hh > 0:
                u = inches(self.upper_stile_in)
                children.append(
                    self._trim(
                        f"{side}_header",
                        x0 + u, x0 + width - u, fy0, fy1,
                        self.ceiling - hh, self.ceiling,
                        orient="rail",
                        notes="fascia above the heat pump's ceiling clearance",
                    )
                )

        # Baseboard across the front, over the face frame.
        children.append(
            self._trim(
                f"{side}_baseboard",
                x0, x0 + width, fy0 - t, fy0, 0.0, inches(self.baseboard_in),
                orient="rail",
                notes="over the face frame, wall to wall; coped or butted to the room's",
            )
        )

        # A nailer on each side wall behind the stile's scribed edge.
        nailer_w = inches(1.5)
        if f >= t:
            for xa in (x0, x0 + width - t):
                pos, *_ = _box(xa, xa + t, fy1, fy1 + nailer_w, 0.0, self.ceiling)
                children.append(
                    pos
                    * _UPRIGHT_SIDEWAYS
                    * Board(
                        length_mm=self.ceiling,
                        nominal="1x2",
                        material="pine",
                        label=f"{side}_wall_nailer",
                        notes="screwed to the side wall; the stile nails into its edge",
                    )
                )
        return Compound(children=children, label=f"{side}_section")

    def _trim(
        self,
        label: str,
        x0: float,
        x1: float,
        y0: float,
        y1: float,
        z0: float,
        z1: float,
        *,
        orient: str,
        notes: str,
    ):
        """Return one poplar trim piece filling an axis-aligned span."""
        pos, dx, dy, dz = _box(x0, x1, y0, y1, z0, z1)
        if orient == "upright":
            length, width, rot = dz, dx, _UPRIGHT
        else:
            length, width, rot = dx, dz, _ON_EDGE
        board = Board(
            length_mm=length,
            thickness_mm=dy,
            width_mm=width,
            material="poplar",
            label=label,
            notes=f"rip from {rip_source(width)}; {notes}",
        )
        return pos * rot * board

    def _riser(self, side: str, x0: float) -> list[object]:
        """Return the 2x4 ladder the BILLY stands on, ripped to height."""
        h = self.riser_height_mm
        if h <= 0:
            return []
        t = inches(1.5)
        d = self.billy_depth_mm
        out: list[object] = []
        for y_a in (-d, -t):
            pos, *_ = _box(x0, x0 + self.billy_width_mm, y_a, y_a + t, 0.0, h)
            out.append(
                pos
                * _ON_EDGE
                * Board(
                    length_mm=self.billy_width_mm,
                    thickness_mm=t,
                    width_mm=h,
                    material="pine",
                    label=f"{side}_riser_rail",
                    notes="2x4 ripped to height, on edge; shim level, screw to the floor",
                )
            )
        rung = d - 2 * t
        for x_c in (x0 + t / 2, x0 + self.billy_width_mm / 2, x0 + self.billy_width_mm - t / 2):
            out.append(
                Pos(x_c, -d / 2, h / 2)
                * _ON_EDGE_DEEP
                * Board(
                    length_mm=rung,
                    thickness_mm=t,
                    width_mm=h,
                    material="pine",
                    label=f"{side}_riser_rung",
                    notes="2x4 ripped to height; between the rails",
                )
            )
        return out

    def _billy(
        self, side: str, x0: float, z0: float, extension: bool
    ) -> list[object]:
        """Return a BILLY (and extension) as bought panels, for the drawing."""
        p = self.billy_panel_mm
        w, d = self.billy_width_mm, self.billy_depth_mm
        out: list[object] = []

        def panel(item, label, x_a, x_b, y_a, y_b, z_a, z_b):
            pos, dx, dy, dz = _box(x_a, x_b, y_a, y_b, z_a, z_b)
            part = Purchased(dx, dy, dz, material="billy_white", label=label, item=item)
            part.instance = f"{side}:{item}"
            out.append(pos * part)

        def carcass(item, z_a, z_b, bottom_at, shelves):
            for xa in (x0, x0 + w - p):
                panel(item, "billy_side", xa, xa + p, -d, 0.0, z_a, z_b)
            panel(item, "billy_top", x0 + p, x0 + w - p, -d, 0.0, z_b - p, z_b)
            panel(item, "billy_bottom", x0 + p, x0 + w - p, -d, 0.0, bottom_at - p, bottom_at)
            panel(item, "billy_back", x0, x0 + w, -3.0, 0.0, z_a, z_b)
            if bottom_at - p > z_a:
                panel(item, "billy_plinth", x0 + p, x0 + w - p, -d, -d + p, z_a, bottom_at - p)
            for z in shelves:
                panel(
                    item, "billy_shelf",
                    x0 + p + 3, x0 + w - p - 3, -d + 15, -3.0, z - p / 2, z + p / 2,
                )

        bottom = z0 + inches(self.billy_kick_in)
        top_inside = z0 + self.billy_height_mm - p
        pitch = (top_inside - bottom) / 6
        carcass(BILLY, z0, z0 + self.billy_height_mm, bottom,
                [bottom + i * pitch for i in range(1, 6)])
        if extension:
            ez = z0 + self.billy_height_mm
            carcass(BILLY_EXT, ez, ez + self.extension_height_mm, ez + p, [])
        return out

    # ------------------------------------------------------------------
    # Checks
    # ------------------------------------------------------------------

    def check(self, assembly: Compound, parts: list[CutPart]) -> CheckReport:
        """Run every design check against the built-ins.

        Parameters
        ----------
        assembly : build123d.Compound
            The result of :meth:`build`.
        parts : list[CutPart]
            The cut list extracted from *assembly*.

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
                published_l_mm=inches(
                    self.left_width_in + self.bay_opening_in + self.right_width_in
                ),
                published_w_mm=self.billy_depth_mm + 2 * self.trim_thickness_mm,
                published_h_mm=self.ceiling,
            )
        )
        report.extend(check_material_suitability(parts, self.inventory))
        report.extend(self.check_widths())
        report.extend(self.check_extension_fit())
        report.extend(self.check_heat_pump())
        report.extend(
            check_shelf_deflection(
                material="particleboard",
                span_mm=self.billy_width_mm - 2 * self.billy_panel_mm,
                depth_mm=self.billy_depth_mm - 20.0,
                thickness_mm=self.billy_panel_mm,
                load_kg=self.shelf_load_kg,
                label="BILLY shelf",
            )
        )
        report.findings.append(
            Finding(
                Severity.INFO,
                "deflection",
                "the face frame stiffens nothing that moves: a BILLY shelf "
                "that sags is fixed by gluing a 1x2 poplar nosing on edge to "
                "its front, not by the frame",
            )
        )
        report.extend(self.check_stock_lengths(parts))
        report.findings.append(
            Finding(
                Severity.INFO,
                "mounting",
                "pull the room's baseboard behind each case; set the risers "
                "level (shim, then screw down), stand the BILLYs on them and "
                "anchor each to a stud with IKEA's bracket before any trim "
                "goes on; prime the BILLY's foil edges with a bonding primer "
                "so the paint line across frame and case matches",
            )
        )
        report.extend(self.shopping_list(assembly))
        return report

    def check_widths(self) -> list[Finding]:
        """Report the filler each side of each BILLY and the stile it makes.

        Returns
        -------
        list[Finding]
            One ``INFO`` per section; a ``WARN`` where the filler is too
            narrow for a wall nailer behind the stile.
        """
        findings = []
        for side, width_in in (("left", self.left_width_in), ("right", self.right_width_in)):
            f = self.filler(width_in)
            s = self.stile_width(width_in)
            text = (
                f'{side}: {width_in:g}" alcove leaves {mm_to_fractional_inch(f)} '
                f"each side of the BILLY; stiles {mm_to_fractional_inch(s)} wide "
                f"(rip from {rip_source(s + inches(0.25))} — cut 1/4\" fat and "
                f"scribe to the wall)"
            )
            if f < self.trim_thickness_mm:
                findings.append(
                    Finding(Severity.WARN, "fit", text + " — no room for a wall nailer")
                )
            else:
                findings.append(Finding(Severity.INFO, "fit", text))
        return findings

    def check_extension_fit(self) -> list[Finding]:
        """Make sure the right stack goes in under the ceiling.

        Two different questions.  Standing the BILLY up off its back needs
        its diagonal under the ceiling.  The extension then has to be lifted
        onto its dowels, ~7 mm above where it ends up — and a ceiling is not
        flat, so less than half an inch of spare is worth a tape at the
        front *and* back of where the case stands.

        Returns
        -------
        list[Finding]
            ``ERROR`` if the extension cannot go on, ``WARN`` if it only
            just can, otherwise ``INFO``.
        """
        diag = math.hypot(self.billy_height_mm, self.billy_depth_mm)
        findings = [
            Finding(
                Severity.INFO if diag < self.ceiling else Severity.ERROR,
                "fit",
                f"a BILLY stands up through a {mm_to_fractional_inch(diag)} "
                f"diagonal against a {self.ceiling_in:g}\" ceiling; stand it "
                f"up on the floor, then lift it onto the riser",
            )
        ]
        spare = self.ceiling - self.extension_top
        need = self.extension_lift_mm
        msg = (
            f"right stack (riser {mm_to_fractional_inch(self.riser_height_mm)} "
            f"+ BILLY + extension) tops out at "
            f"{mm_to_fractional_inch(self.extension_top)}, "
            f"{mm_to_fractional_inch(spare)} under the ceiling; the extension "
            f"needs {need:.0f} mm of lift to drop onto its dowels"
        )
        if spare < need:
            max_riser = self.riser_height_mm - (need - spare)
            findings.append(
                Finding(
                    Severity.ERROR,
                    "fit",
                    f"{msg} — it will not go on.  The riser can be at most "
                    f"{mm_to_fractional_inch(max(max_riser, 0.0))}, which drops "
                    f"the bottom shelf below the baseboard top",
                )
            )
        elif spare < need + inches(0.25):
            findings.append(
                Finding(
                    Severity.WARN,
                    "fit",
                    f"{msg} — tight: measure the ceiling front and back where "
                    f"the case stands before ripping the riser",
                )
            )
        else:
            findings.append(Finding(Severity.INFO, "fit", msg))
        findings.append(
            Finding(
                Severity.INFO,
                "fit",
                f"right header {mm_to_fractional_inch(self.right_header_height)} "
                f"(rip from {rip_source(self.right_header_height)}) closes the "
                f"extension's top to the ceiling",
            )
        )
        return findings

    def check_heat_pump(self) -> list[Finding]:
        """Hold the left section to the heat pump's airflow clearances.

        Four zones around the indoor unit, each a different rule:

        * **Ceiling** — the manufacturer's minimum above the unit, where the
          intake grille is.
        * **Sides** — the manufacturer's minimums, to the alcove walls (the
          real obstruction beside the unit).  The upper stiles stand in the
          face plane, ahead of the unit's front, and must not cover its
          ends.
        * **Front** — open.  A header across the front may sit only above
          the ceiling clearance; lower, it is in front of the intake and
          stops the front panel lifting for the filters.
        * **Below** — the outlet louvre, which throws down and forward.  The
          case top under it is held ``outlet_clearance_in`` away.

        Returns
        -------
        list[Finding]
            ``ERROR`` for a manufacturer minimum broken, ``WARN`` for the
            outlet judgement, ``INFO`` for each zone that passes.
        """
        findings: list[Finding] = []
        fmt = mm_to_fractional_inch

        above = self.ceiling - self.heat_pump_top
        need_above = inches(self.heat_pump_ceiling_clearance_in)
        findings.append(
            Finding(
                Severity.INFO if above >= need_above - 0.5 else Severity.ERROR,
                "airflow",
                f"heat pump top {fmt(above)} below the ceiling (needs "
                f"{fmt(need_above)}; 5-1/8\" if the piping leaves left or "
                f"left-rear on the spacer)",
            )
        )

        width = inches(self.left_width_in)
        hp_w = inches(self.heat_pump_width_in)
        left_gap = self.heat_pump_x0
        right_gap = width - self.heat_pump_x0 - hp_w
        for name, gap, need in (
            ("left", left_gap, inches(self.heat_pump_left_clearance_in)),
            ("right", right_gap, inches(self.heat_pump_right_clearance_in)),
        ):
            findings.append(
                Finding(
                    Severity.INFO if gap >= need else Severity.ERROR,
                    "airflow",
                    f"heat pump {name} end {fmt(gap)} from the wall (needs {fmt(need)})",
                )
            )
        u = inches(self.upper_stile_in)
        reveal = min(left_gap, right_gap) - u
        findings.append(
            Finding(
                Severity.INFO if reveal >= 0 else Severity.WARN,
                "airflow",
                f"upper stiles {fmt(u)} wide leave {fmt(max(reveal, 0.0))} "
                f"between each stile and the unit's end in front view"
                + ("" if reveal >= 0 else " — they cover the unit's ends; narrow them"),
            )
        )

        if self.left_header_height > 0:
            findings.append(
                Finding(
                    Severity.INFO,
                    "airflow",
                    f"left header {fmt(self.left_header_height)} sits above the "
                    f"heat pump's ceiling clearance; the front stays open",
                )
            )
        else:
            findings.append(
                Finding(
                    Severity.INFO,
                    "airflow",
                    "no header across the heat pump: there is no band above "
                    "its ceiling clearance to put one in, so the fascia is the "
                    "two upper stiles, open to the ceiling — the header line "
                    "breaks here on purpose",
                )
            )

        gap = self.heat_pump_bottom - self.billy_top
        need = inches(self.outlet_clearance_in)
        msg = (
            f"heat pump outlet {fmt(max(gap, 0.0))} above the left BILLY top "
            f"(wants {fmt(need)})"
        )
        if gap < 0:
            findings.append(
                Finding(Severity.ERROR, "airflow", f"{msg} — the unit hits the case")
            )
        elif gap < need:
            short = need - gap
            ceiling_needed = (
                self.billy_top
                + need
                + inches(self.heat_pump_height_in)
                + need_above
            )
            findings.append(
                Finding(
                    Severity.WARN,
                    "airflow",
                    f"{msg} — the case top will turn the discharge back along "
                    f"the wall.  Needs a {fmt(ceiling_needed)} ceiling as "
                    f"drawn; or cut the left BILLY's sides down "
                    f"{fmt(short, 8)} and re-bore the top's cam holes; or "
                    f"drop the left riser and let the baseboard lap the "
                    f"bottom shelf",
                )
            )
        else:
            findings.append(Finding(Severity.INFO, "airflow", msg))
        return findings

    def check_stock_lengths(self, parts: list[CutPart]) -> list[Finding]:
        """Flag trim longer than an 8' board will give clean.

        Returns
        -------
        list[Finding]
            One ``WARN`` listing the long parts, or nothing.
        """
        long = sorted(
            {p.label for p in parts if p.length_mm > inches(95.0)}
        )
        if not long:
            return []
        return [
            Finding(
                Severity.WARN,
                "stock",
                f"{', '.join(long)} run past 95\" — an 8' board leaves no "
                f"room to square the ends; buy 10' stock for them",
            )
        ]

    def shopping_list(self, assembly: Compound) -> list[Finding]:
        """List what is bought whole rather than cut.

        Returns
        -------
        list[Finding]
            One ``INFO`` per purchased item.
        """
        return [
            Finding(Severity.INFO, "purchase", f"{qty} x {item}")
            for item, qty in purchased_items(assembly).items()
        ]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def run(builtins: BillyBuiltIns, outdir: Path) -> CheckReport:
    """Build the built-ins, write cut list and views, print the report.

    Parameters
    ----------
    builtins : BillyBuiltIns
        The design to build.
    outdir : Path
        Directory for the generated files.

    Returns
    -------
    CheckReport
        The design-check findings.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    assembly = builtins.build()
    parts = extract(assembly)

    stem = "billy_builtins"
    print(f"\n{'=' * 78}\n  Billy built-ins\n{'=' * 78}")
    df = render_cut_list(
        parts,
        output_csv=outdir / f"{stem}_cutlist.csv",
        output_md=outdir / f"{stem}_cutlist.md",
    )
    print(df.to_string(index=False))

    report = builtins.check(assembly, parts)
    print(f"\n-- design checks {'-' * 61}")
    print(report.to_text())
    print(f"\n-- prices {'-' * 68}")
    print(
        CheckReport()
        .extend(check_price_provenance(builtins.inventory, parts))
        .to_text()
    )

    render_assembly(assembly, output_png=outdir / f"{stem}.png", title="Billy built-ins")
    export_assembly(
        assembly, output_step=outdir / f"{stem}.step", output_stl=outdir / f"{stem}.stl"
    )
    print(f"\nWrote cut list, views and CAD export to {outdir}/")
    return report


def _spec() -> ProjectSpec:
    """Return the gallery entry."""
    design = BillyBuiltIns()
    return ProjectSpec(
        slug="billy-builtins",
        name="Billy built-ins",
        summary=(
            "Two IKEA BILLY bookcases built in either side of the bay: "
            "the right one extended to the ceiling, the left one stopping "
            "under the heat pump, with the poplar face frame, baseboard and "
            "fascia framing the unit's airflow clearances."
        ),
        species="poplar",
        build=design.build,
        check=design.check,
        inventory=design.inventory,
        notes=(
            'Measured: 42" (left) and 37-1/2" (right) wall to wall. Assumed '
            'until measured: 96" ceiling, a Mitsubishi GS-size head hung at '
            "its minimum ceiling clearance, 5-1/2\" baseboard."
        ),
        tags=["built-in", "ikea-hack", "paint-grade"],
    )


#: Projects this module contributes to the gallery.
PROJECTS: list[ProjectSpec] = [_spec()]


def main() -> None:
    """Parse arguments and build."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--left-width", type=float, default=42.0)
    parser.add_argument("--right-width", type=float, default=37.5)
    parser.add_argument("--ceiling", type=float, default=96.0)
    parser.add_argument("--baseboard", type=float, default=5.5)
    parser.add_argument("--heat-pump-bottom", type=float, default=None)
    parser.add_argument("--outdir", type=Path, default=Path("build"))
    args = parser.parse_args()
    run(
        BillyBuiltIns(
            left_width_in=args.left_width,
            right_width_in=args.right_width,
            ceiling_in=args.ceiling,
            baseboard_in=args.baseboard,
            heat_pump_bottom_in=args.heat_pump_bottom,
        ),
        args.outdir,
    )


if __name__ == "__main__":
    main()
