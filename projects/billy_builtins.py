"""Billy built-ins — two IKEA BILLY bookcases made to look built in, either side of the bay.

The "Billy hack": buy the flat-pack carcasses, stand them on a riser, and
dress the front in paint-grade poplar — a face frame scribed to the walls,
baseboard across the bottom, and fascia up to the ceiling — so the room
reads one piece of joinery instead of two bookcases.  Everything that is
*cut* is on the cut list; the BILLYs and the heat pump are drawn, not cut
(:class:`woodshop.parts.Purchased`), and appear on the shopping list.

The two sections
----------------
* **Right**, 37-1/2" from its wall to the window: a BILLY 80x28x202 with
  the 80x28x35 height-extension unit on top, and a header rail closing the
  last inch to the ceiling.
* **Left**, 42" from its wall to the window: a BILLY 80x28x202 *cut down*
  to fit under the installed heat pump.  The fascia goes up to the ceiling
  around the unit — the wall-side stile, open in front — so the unit keeps
  the clearances its installation manual asks for.

Each section has a wall on one side and the bay on the other.  The window
side gets a finished **side panel** — 3/4" birch ply, floor to ceiling, full
depth — which frames the bay and is what the room sees there; the baseboard
returns along it.  The measured width runs to the panel's outside face.

The width that is not BILLY or side panel is split evenly either side of
the case and filled with **nailers**: 2x stock ripped to the gap, front and
back, floor to case top, screwed to the wall (or glued and screwed to the
side panel).  The BILLY screws through its sides into them, and the stiles
nail to their front edges.  Splitting evenly keeps the two stiles the same
width — the wall stile covers gap + BILLY side, the window stile covers
side panel + gap + BILLY side — so the opening sits centred in the frame.

Measured, assumed, and looked up
--------------------------------
Measured by the owner: the two widths, 42" and 37-1/2"; the ceiling, 8' 3"
(99"); and the heat pump — an LG KNUAB181A, installed with its top the 8"
below the ceiling LG asks for.

Looked up: BILLY 80x28x202 cm and the 80x28x35 cm height extension (237 cm
stacked); the extension's dowels need about 7 mm of lift to drop on.  The
KNUAB181A is 998 x 345 mm face-on (LG Canada; 39-5/16" x 13-9/16"), and
9.281" deep by US listings (LG Canada says 210 mm; the deeper figure is
used).  LG's standard wall-mount manual: 8" to the ceiling for 18k units,
more than 4" to "any wall or enclosure" either side, 6.5' to the floor.

What that does to the left side
-------------------------------
Hung 8" below a 99" ceiling, the unit's underside is at about 77-7/16".  A
202 cm BILLY on its riser tops out at 81-3/4" — 4-3/8" *into* the unit.
So the left case is cut down to leave ``outlet_clearance_in`` of open air
under the outlet louvre (4", a judgement — LG gives no figure below the
unit): about 8-3/8" off the sides, new cam holes for the top.

And the unit is wide.  39-5/16" plus 4" a side needs 47-5/16" between
obstructions, and the section is 42".  With its left end 4" off the wall
(assumed — measure it), the unit overhangs the section by 1-5/16", so the
left side panel cannot rise past the case: it stops at the case top and
the bay side above it stays open.

**Still assumed, each a parameter**: the unit's left offset (4"), BILLY
panels 15 mm, kick plate 3-1/4", a 5-1/2" baseboard, and the 4" outlet air.

Run it
------
::

    uv run python projects/billy_builtins.py
    uv run python projects/billy_builtins.py --heat-pump-left-offset 5 --heat-pump-bottom 77.5
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
    check_sheet_fit,
    check_shelf_deflection,
)
from woodshop.cutlist.extract import CutPart, extract, purchased_items
from woodshop.inventory import Inventory
from woodshop.lumber import mm_to_fractional_inch
from woodshop.parts import Board, Panel, Purchased
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
HEAT_PUMP = "LG KNUAB181A wall head (installed)"


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
        Width of each section from its wall to the outside face of its
        window-side panel, default the measured 42" and 37-1/2".
    bay_opening_in : float, optional
        Width between the two sections, default 72" — a guess, used only to
        lay the drawing out.  Nothing is built there.
    ceiling_in : float, optional
        Floor to ceiling, default the measured 8' 3" (99").
    baseboard_in : float, optional
        Baseboard height, default 5-1/2" (a 1x6).  Match the room's.
    billy_kick_in : float, optional
        Height of the BILLY's bottom-shelf top above its own base, default
        3-1/4" (assumed; measure the assembled case).
    billy_panel_mm : float, optional
        BILLY side/top panel thickness, default 15 mm (assumed).
    heat_pump_width_in, heat_pump_height_in, heat_pump_depth_in : float, optional
        Indoor unit size, default the installed LG KNUAB181A: 998 x 345 mm
        (LG's metric spec) and 9.281" deep (US listings; LG Canada says
        210 mm — the larger is used).
    heat_pump_bottom_in : float or None, optional
        Underside of the indoor unit above the floor.  ``None`` (default)
        puts its top ``heat_pump_ceiling_clearance_in`` below the ceiling,
        which is how it was installed.
    heat_pump_left_offset_in : float, optional
        The unit's left end from the left section's wall, default 4" —
        assumed: LG's minimum, which an installer working to the manual
        would not have exceeded by much.  Measure it.
    heat_pump_ceiling_clearance_in : float, optional
        Manufacturer's minimum to the ceiling, default 8" (LG standard wall
        mount, 18k).
    heat_pump_left_clearance_in, heat_pump_right_clearance_in : float, optional
        Manufacturer's side minimums to "any wall or enclosure", default
        4" each (LG), left and right *as seen facing the unit*.
    outlet_clearance_in : float, optional
        Open air required between the top of the left case and the unit's
        underside, default 4" — a judgement, not a manufacturer figure.  The
        left BILLY is cut down to leave it.
    upper_stile_in : float, optional
        Width of the left section's stiles above the BILLY, default 1-1/2".
        Narrower than the stiles below so they frame the heat pump rather
        than masking its ends.
    match_window_stiles : bool, optional
        Default ``True``: the left section's window-side stile matches the
        right's, so the two stiles flanking the bay are a pair, and the left
        section's 4-1/2" of extra width all goes to its wall stile.  It also
        happens to centre the left case under the heat pump.  ``False``
        centres each BILLY in its own section.
    align_shelves : bool, optional
        Default ``True``: the right BILLY's adjustable shelves are set on the
        left case's shelf lines, so the horizontals read straight across the
        bay, and its top line lands on the left case top.  ``False`` spaces
        them evenly.
    min_nailer_in : float, optional
        Narrowest gap worth a nailer, default 3/4" — narrower and the BILLY
        side should go straight to the wall with shims.
    side_panel_max_in : float, optional
        Longest side panel cut in one piece, default 95" — a 4x8 sheet
        less room to square and scribe.  Taller panels are made in two.
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
    ceiling_in: float = 99.0
    baseboard_in: float = 5.5
    billy_kick_in: float = 3.25
    billy_panel_mm: float = 15.0
    heat_pump_width_in: float = 998.0 / IN
    heat_pump_height_in: float = 345.0 / IN
    heat_pump_depth_in: float = 9.281
    heat_pump_bottom_in: float | None = None
    heat_pump_left_offset_in: float = 4.0
    heat_pump_ceiling_clearance_in: float = 8.0
    heat_pump_left_clearance_in: float = 4.0
    heat_pump_right_clearance_in: float = 4.0
    outlet_clearance_in: float = 4.0
    upper_stile_in: float = 1.5
    rail_in: float = 1.5
    min_nailer_in: float = 0.75
    match_window_stiles: bool = True
    align_shelves: bool = True
    side_panel_max_in: float = 95.0
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
    #: Window-side panels: 3/4" birch ply, which is 23/32".
    side_panel_nominal: str = "3/4"
    #: Nailers are 2x stock ripped to the gap: 1-1/2" front to back.
    nailer_depth_mm: float = 38.1

    def __post_init__(self) -> None:
        """Refuse an alcove a BILLY will not go into."""
        for side, width in (("left", self.left_width_in), ("right", self.right_width_in)):
            if min(self.window_gap(side), self.wall_gap(side)) < 0:
                raise ValueError(
                    f'{side} section is {width:g}" — narrower than a BILLY\'s '
                    f'{self.billy_width_mm / IN:.2f}" plus its side panel'
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

    @property
    def side_panel_mm(self) -> float:
        """Thickness of the window-side panel, mm (3/4" ply is 23/32")."""
        return float(Panel(10.0, 10.0, material="plywood_birch", label="probe",
                           nominal_thickness=self.side_panel_nominal).thickness_mm)

    def width_of(self, side: str) -> float:
        """Width of the ``"left"`` or ``"right"`` section, mm."""
        return inches(self.left_width_in if side == "left" else self.right_width_in)

    def _centred_window_gap(self, side: str) -> float:
        """Window-side nailer gap with the BILLY centred in *side*, mm.

        Centred, the side panel comes out of the window-side gap and the
        two stiles of the section come out the same width.
        """
        return (self.width_of(side) - self.billy_width_mm) / 2 - self.side_panel_mm

    def window_gap(self, side: str) -> float:
        """Nailer gap between the BILLY and the side panel, mm.

        The right section is centred.  With :attr:`match_window_stiles` the
        left takes the right's window gap, so the two stiles either side of
        the bay match, and its extra width all goes to the wall side.
        """
        if side == "left" and self.match_window_stiles:
            return self._centred_window_gap("right")
        return self._centred_window_gap(side)

    def wall_gap(self, side: str) -> float:
        """Nailer gap between the wall and the BILLY, mm: whatever is left."""
        return (
            self.width_of(side)
            - self.billy_width_mm
            - self.side_panel_mm
            - self.window_gap(side)
        )

    def wall_stile(self, side: str) -> float:
        """Wall-side stile width, mm: the wall gap plus the BILLY side it laps."""
        return self.wall_gap(side) + self.billy_panel_mm

    def window_stile(self, side: str) -> float:
        """Window-side stile width, mm: side panel, window gap, BILLY side."""
        return self.side_panel_mm + self.window_gap(side) + self.billy_panel_mm

    def billy_x(self, side: str) -> float:
        """Return the BILLY's left edge, mm, from its section's left end."""
        if side == "left":  # wall on its left
            return self.wall_gap(side)
        return self.side_panel_mm + self.window_gap(side)

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
        """Left end of the heat pump, mm, from the left section's wall."""
        return inches(self.heat_pump_left_offset_in)

    @property
    def heat_pump_x1(self) -> float:
        """Right end of the heat pump, mm."""
        return self.heat_pump_x0 + inches(self.heat_pump_width_in)

    @property
    def left_case_height(self) -> float:
        """Height of the left BILLY, mm — cut down to clear the heat pump.

        A 202 cm BILLY unless that would bring its top within
        ``outlet_clearance_in`` of the unit's underside; then the sides are
        cut down to leave exactly that.
        """
        room = (
            self.heat_pump_bottom
            - inches(self.outlet_clearance_in)
            - self.riser_height_mm
        )
        return min(self.billy_height_mm, room)

    @property
    def left_case_cut(self) -> float:
        """How much comes off the left BILLY's sides, mm (0 if none)."""
        return self.billy_height_mm - self.left_case_height

    @property
    def left_case_top(self) -> float:
        """Top of the left BILLY above the floor, mm."""
        return self.riser_height_mm + self.left_case_height

    @property
    def left_panel_to_ceiling(self) -> bool:
        """Whether the left side panel can rise past the case to the ceiling.

        Only if its inside face stands at least the unit's right clearance
        clear of the unit's right end — otherwise it is an "enclosure"
        inside the clearance (or runs straight through the unit), and stops
        at the case top.
        """
        inside = inches(self.left_width_in) - self.side_panel_mm
        return inside >= self.heat_pump_x1 + inches(self.heat_pump_right_clearance_in)

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
        left = self._section(
            "left", 0.0, self.left_width_in, extension=False, window="right"
        )
        right = self._section(
            "right", self.right_x0, self.right_width_in, extension=True, window="left"
        )
        hp_pos, hx, hy, hz = _box(
            self.heat_pump_x0,
            self.heat_pump_x1,
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
        self, side: str, x0: float, width_in: float, *, extension: bool, window: str
    ) -> Compound:
        """Build one section: riser, BILLY, nailers, side panel, face frame, trim.

        *window* says which end faces the bay (``"left"`` or ``"right"``);
        the wall is at the other end.
        """
        width = inches(width_in)
        x1 = x0 + width
        sp = self.side_panel_mm
        t = self.trim_thickness_mm
        fy0, fy1 = self.face_y - t, self.face_y  # face-frame plane
        billy_x = x0 + self.billy_x(side)
        s_wall, s_win = self.wall_stile(side), self.window_stile(side)
        # Top of the BILLY itself (the left one may be cut down), and of the
        # whole stack.
        top = self.billy_top if extension else self.left_case_top
        case_top = self.extension_top if extension else top
        panel_top = self.ceiling if (extension or self.left_panel_to_ceiling) else top
        children: list[object] = []

        children += self._riser(side, billy_x)
        children += self._billy(
            side, billy_x, self.riser_height_mm, extension, height=top - self.riser_height_mm
        )

        # The side panel framing the bay: full depth, floor to ceiling —
        # unless the heat pump's clearance reaches past it, when it stops at
        # the case top.
        px0 = x1 - sp if window == "right" else x0
        # A panel taller than a 4x8 sheet allows is made in two, joined on
        # the header line, where the front already has a horizontal joint.
        split = (
            self.ceiling - self.right_header_height
            if extension
            else inches(self.side_panel_max_in)
        )
        pieces = (
            [(0.0, panel_top, f"{side}_side_panel")]
            if panel_top <= inches(self.side_panel_max_in)
            else [
                (0.0, split, f"{side}_side_panel"),
                (split, panel_top, f"{side}_side_panel_top"),
            ]
        )
        for za, zb, label in pieces:
            pos, *_ = _box(px0, px0 + sp, self.face_y, 0.0, za, zb)
            children.append(
                pos
                * _UPRIGHT_SIDEWAYS
                * Panel(
                    length_mm=zb - za,
                    width_mm=self.billy_depth_mm,
                    nominal_thickness=self.side_panel_nominal,
                    material="plywood_birch",
                    label=label,
                    notes=(
                        "frames the bay; scribed to wall"
                        + (" and ceiling" if zb == self.ceiling
                           else "; stops at the case top, below the heat pump"
                           if zb == top else "")
                        + (f"; splined to the {'upper' if za == 0 else 'lower'} "
                           "piece on the header line, filled and painted"
                           if len(pieces) > 1 else "")
                        + "; front edge under the window stile, glued and "
                        "screwed to its nailers"
                    ),
                )
            )

        # Nailers: 2x ripped to each gap, front and back, floor to case top.
        wall_x = (x0, billy_x) if window == "right" else (billy_x + self.billy_width_mm, x1)
        win_x = (
            (billy_x + self.billy_width_mm, px0) if window == "right" else (px0 + sp, billy_x)
        )
        nd = self.nailer_depth_mm
        for where, (xa, xb), fixing in (
            ("wall", wall_x, "screwed to the wall studs or plugs"),
            ("window", win_x, "glued and screwed to the side panel"),
        ):
            gap = xb - xa
            if gap < inches(self.min_nailer_in):
                continue
            for ya, yb, face in ((self.face_y, self.face_y + nd, "front"), (-nd, 0.0, "back")):
                pos, *_ = _box(xa, xb, ya, yb, 0.0, case_top)
                children.append(
                    pos
                    * _UPRIGHT
                    * Board(
                        length_mm=case_top,
                        thickness_mm=nd,
                        width_mm=gap,
                        material="pine",
                        label=f"{side}_{where}_nailer",
                        notes=(
                            f"2x ripped to {mm_to_fractional_inch(gap)}; {fixing}; "
                            "the BILLY screws through its side into it"
                            + ("; the stile nails to its edge" if face == "front" else "")
                        ),
                    )
                )

        # Stiles: full height on the right; on the left they stop at the
        # case top and narrower uppers carry on to the ceiling.
        lower_top = self.ceiling if extension else top
        stiles = {
            "wall": (x0, x0 + s_wall) if window == "right" else (x1 - s_wall, x1),
            "window": (x1 - s_win, x1) if window == "right" else (x0, x0 + s_win),
        }
        for where, (x_a, x_b) in stiles.items():
            children.append(
                self._trim(
                    f"{side}_{where}_stile",
                    x_a, x_b, fy0, fy1, 0.0, lower_top,
                    orient="upright",
                    notes=(
                        "scribed to the wall" if where == "wall"
                        else "outside edge flush with the side panel's face"
                    )
                    + "; glued and brad-nailed to the nailer and the BILLY side it laps",
                )
            )
        if not extension:
            u = inches(self.upper_stile_in)
            uppers = {
                "wall": (x0, x0 + u) if window == "right" else (x1 - u, x1),
                "window": (x1 - u, x1) if window == "right" else (x0, x0 + u),
            }
            if not self.left_panel_to_ceiling:
                # Nothing to frame that side with inside the clearance.
                del uppers["window"]
            for where, (x_a, x_b) in uppers.items():
                children.append(
                    self._trim(
                        f"{side}_{where}_upper_stile",
                        x_a, x_b, fy0, fy1, top, self.ceiling,
                        orient="upright",
                        notes=(
                            "frames the heat pump; nailed to the "
                            + ("upper wall nailer" if where == "wall" else "side panel's edge")
                        ),
                    )
                )
            # Above the case only the stile needs fixing — a full-width
            # nailer would stand in the heat pump's side clearance.
            wx = x0 if window == "right" else x1 - t
            pos, *_ = _box(wx, wx + t, self.face_y, self.face_y + inches(1.5),
                           top, self.ceiling)
            children.append(
                pos
                * _UPRIGHT_SIDEWAYS
                * Board(
                    length_mm=self.ceiling - top,
                    nominal="1x2",
                    material="pine",
                    label=f"{side}_upper_wall_nailer",
                    notes="screwed to the wall above the case; carries the upper stile",
                )
            )

        # The opening between the stiles: the BILLY's inside faces.
        inner0 = billy_x + self.billy_panel_mm
        inner1 = billy_x + self.billy_width_mm - self.billy_panel_mm
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
                    inner0, inner1, fy0, fy1, top - rail, top,
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
                        x0 + u, x1 - u, fy0, fy1,
                        self.ceiling - hh, self.ceiling,
                        orient="rail",
                        notes="fascia above the heat pump's ceiling clearance",
                    )
                )

        # Baseboard across the front, over the face frame, mitered into a
        # return that runs back along the side panel to the wall.
        bh = inches(self.baseboard_in)
        bx0, bx1 = (x0, x1 + t) if window == "right" else (x0 - t, x1)
        children.append(
            self._trim(
                f"{side}_baseboard",
                bx0, bx1, fy0 - t, fy0, 0.0, bh,
                orient="rail",
                notes="over the face frame; mitered to the return at the bay, "
                "coped or butted to the room's at the wall",
            )
        )
        rx0 = x1 if window == "right" else x0 - t
        children.append(
            self._trim(
                f"{side}_baseboard_return",
                rx0, rx0 + t, fy0 - t, 0.0, 0.0, bh,
                orient="return",
                notes="along the side panel's bay face, wall to the miter",
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
            length, width, thick, rot = dz, dx, dy, _UPRIGHT
        elif orient == "return":
            length, width, thick, rot = dy, dz, dx, _ON_EDGE_DEEP
        else:
            length, width, thick, rot = dx, dz, dy, _ON_EDGE
        board = Board(
            length_mm=length,
            thickness_mm=thick,
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
        self, side: str, x0: float, z0: float, extension: bool, *, height: float
    ) -> list[object]:
        """Return a BILLY (and extension) as bought panels, for the drawing.

        *height* is the case as installed — under 202 cm when the sides
        have been cut down — and sets how many shelves it keeps, at the
        uncut case's pitch.
        """
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
        shelves = self.shelf_heights("right" if extension else "left")
        carcass(BILLY, z0, z0 + height, bottom, shelves)
        if extension:
            ez = z0 + height
            carcass(BILLY_EXT, ez, ez + self.extension_height_mm, ez + p, [])
        return out

    def _even_shelves(self, height: float) -> tuple[list[float], float]:
        """Shelf centres for a BILLY of *height*, evenly spaced, and the pitch.

        As many openings as fit at about the uncut case's pitch (202 cm has
        six), so a cut-down case loses shelves rather than squashing them.
        """
        p = self.billy_panel_mm
        bottom = self.riser_height_mm + inches(self.billy_kick_in)
        full_pitch = (self.billy_height_mm - p - inches(self.billy_kick_in)) / 6
        top_inside = self.riser_height_mm + height - p
        openings = max(1, round((top_inside - bottom) / full_pitch))
        pitch = (top_inside - bottom) / openings
        return [bottom + i * pitch for i in range(1, openings)], pitch

    def shelf_heights(self, side: str) -> list[float]:
        """Shelf centre heights above the floor for one side's BILLY, mm.

        The left case's are even.  With :attr:`align_shelves` the right
        case's sit on the left's lines — carried on at the same pitch, so
        the left case *top* becomes a shelf line on the right too — as far
        as leaves a 6" opening under the right BILLY's own top.
        """
        if side == "left":
            return self._even_shelves(self.left_case_height)[0]
        if not self.align_shelves:
            return self._even_shelves(self.billy_height_mm)[0]
        _, pitch = self._even_shelves(self.left_case_height)
        bottom = self.riser_height_mm + inches(self.billy_kick_in)
        limit = self.billy_top - self.billy_panel_mm - inches(6.0)
        heights, z = [], bottom + pitch
        while z <= limit:
            heights.append(z)
            z += pitch
        return heights

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
                # The baseboard returns face the bay, inside this extent.
                published_l_mm=inches(
                    self.left_width_in + self.bay_opening_in + self.right_width_in
                ),
                published_w_mm=self.billy_depth_mm + 2 * self.trim_thickness_mm,
                published_h_mm=self.ceiling,
            )
        )
        report.extend(check_material_suitability(parts, self.inventory))
        report.extend(check_sheet_fit(parts, self.inventory))
        report.extend(self.check_widths())
        report.extend(self.check_extension_fit())
        report.extend(self.check_heat_pump())
        report.extend(self.check_symmetry())
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
        """Report how each section's width is spent, nailers included.

        Wall | wall gap | BILLY | window gap | side panel.  The gaps are
        what the nailers fill, so each must be wide enough to be worth one;
        under :attr:`min_nailer_in` the BILLY side goes to the wall (or
        panel) on shims instead, and the stile has nothing behind its edge.

        Returns
        -------
        list[Finding]
            One ``INFO`` per section; a ``WARN`` per gap too narrow for a
            nailer.
        """
        fmt = mm_to_fractional_inch
        findings = []
        for side, width_in in (("left", self.left_width_in), ("right", self.right_width_in)):
            wall, win = self.wall_gap(side), self.window_gap(side)
            sw, sn = self.wall_stile(side), self.window_stile(side)
            stiles = (
                f"both stiles {fmt(sw)} (rip from {rip_source(sw + inches(0.25))})"
                if abs(sw - sn) < 0.5
                else f"wall stile {fmt(sw)} (rip from {rip_source(sw + inches(0.25))}), "
                f"window stile {fmt(sn)} (rip from {rip_source(sn)})"
            )
            findings.append(
                Finding(
                    Severity.INFO,
                    "fit",
                    f'{side}: {width_in:g}" = {fmt(wall)} wall nailer + '
                    f'{fmt(self.billy_width_mm)} BILLY + {fmt(win)} window nailer + '
                    f"{fmt(self.side_panel_mm, 32)} side panel; {stiles} — cut "
                    f'the wall stile 1/4" fat and scribe it',
                )
            )
            for where, gap in (("wall", wall), ("window", win)):
                if gap < inches(self.min_nailer_in):
                    findings.append(
                        Finding(
                            Severity.WARN,
                            "fit",
                            f"{side} {where} gap is {fmt(gap)} — too narrow for a "
                            f"nailer; shim the BILLY side tight instead and glue "
                            f"the stile to it",
                        )
                    )
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
        """Hold the left section to the installed heat pump's clearances.

        The unit is already on the wall, so the cabinetry answers to it,
        never the other way round.  Four zones, each its own rule:

        * **Ceiling** — the manufacturer's minimum above the unit, where the
          intake grille is.  The installer's job; reported, not designed.
        * **Sides** — the manufacturer's minimum to "any wall or enclosure".
          On the wall side that is the installer's offset.  On the bay side
          it decides whether the side panel and an upper stile may rise
          past the case: only if they stand clear of the unit's right end
          by the full clearance.
        * **Front** — open.  A header across the front may sit only above
          the ceiling clearance.
        * **Below** — the outlet louvre.  The left BILLY is cut down to
          leave ``outlet_clearance_in`` under it, and the cut is reported,
          because it is work: new cam and dowel holes for the top.

        Returns
        -------
        list[Finding]
            ``ERROR`` for a manufacturer minimum broken, ``WARN`` for work
            the clearances force, ``INFO`` for each zone that passes.
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
                f"{fmt(need_above)}); underside at {fmt(self.heat_pump_bottom)} "
                f"— LG also asks 6.5' to the floor, so measure the real "
                f"underside before cutting the case",
            )
        )

        left_need = inches(self.heat_pump_left_clearance_in)
        findings.append(
            Finding(
                Severity.INFO if self.heat_pump_x0 >= left_need else Severity.ERROR,
                "airflow",
                f"heat pump left end {fmt(self.heat_pump_x0)} from the wall "
                f"(needs {fmt(left_need)}) — assumed; measure it",
            )
        )

        width = inches(self.left_width_in)
        right_need = inches(self.heat_pump_right_clearance_in)
        clear_line = self.heat_pump_x1 + right_need
        if self.left_panel_to_ceiling:
            gap = width - self.side_panel_mm - self.heat_pump_x1
            findings.append(
                Finding(
                    Severity.INFO,
                    "airflow",
                    f"heat pump right end {fmt(gap)} from the side panel "
                    f"(needs {fmt(right_need)}); panel and upper stile run to "
                    f"the ceiling",
                )
            )
        else:
            over = self.heat_pump_x1 - width
            where = (
                f"overhangs the {self.left_width_in:g}\" section by {fmt(over)}"
                if over > 0
                else f"ends {fmt(-over)} short of the section's edge"
            )
            findings.append(
                Finding(
                    Severity.WARN,
                    "airflow",
                    f"the {fmt(inches(self.heat_pump_width_in))} unit {where}, "
                    f"and its right clearance runs to {fmt(clear_line)} from "
                    f"the wall — so the side panel stops at the case top and "
                    f"the bay side above it stays open.  Any fascia framing "
                    f"that side must stand at least {fmt(clear_line)} from "
                    f"the wall, out over the bay",
                )
            )

        u = inches(self.upper_stile_in)
        reveal = self.heat_pump_x0 - u
        findings.append(
            Finding(
                Severity.INFO if reveal >= 0 else Severity.WARN,
                "airflow",
                f"upper wall stile {fmt(u)} wide leaves {fmt(max(reveal, 0.0))} "
                f"to the unit's end in front view"
                + ("" if reveal >= 0 else " — it covers the unit's end; narrow it"),
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
                    "no header across the heat pump: its ceiling clearance "
                    "takes the whole band above it, so the front stays open "
                    "to the ceiling — the header line breaks here on purpose",
                )
            )

        gap = self.heat_pump_bottom - self.left_case_top
        need = inches(self.outlet_clearance_in)
        if self.left_case_height < inches(20.0):
            findings.append(
                Finding(
                    Severity.ERROR,
                    "airflow",
                    f"only {fmt(max(self.left_case_height, 0.0))} of case fits "
                    f"under the heat pump with {fmt(need)} of outlet air — not "
                    f"a bookcase",
                )
            )
        elif self.left_case_cut > 0:
            uncut_top = self.riser_height_mm + self.billy_height_mm
            findings.append(
                Finding(
                    Severity.WARN,
                    "airflow",
                    f"a full BILLY would top out at {fmt(uncut_top)}, "
                    f"{fmt(uncut_top - self.heat_pump_bottom)} into the heat "
                    f"pump; cut the left BILLY's sides and back down "
                    f"{fmt(self.left_case_cut, 8)} to "
                    f"{fmt(self.left_case_height, 8)}, re-bore the top's cam "
                    f"and dowel holes, and it keeps {fmt(gap)} of air under "
                    f"the outlet.  Uncut alternative: BILLY 80x28x106 plus "
                    f"the 35 cm extension (141 cm), a lower case with more air",
                )
            )
        else:
            findings.append(
                Finding(
                    Severity.INFO,
                    "airflow",
                    f"heat pump outlet {fmt(gap)} above the left BILLY top "
                    f"(wants {fmt(need)})",
                )
            )
        return findings

    def check_symmetry(self) -> list[Finding]:
        """Say what reads as a pair across the bay, and where the difference went.

        The two sections cannot match — 4-1/2" apart in width, one tall and
        one under a heat pump — so the design matches what the eye compares
        (the two stiles flanking the window, the openings, the shelf lines)
        and puts the difference where it reads as wall: the left wall stile.

        Returns
        -------
        list[Finding]
            ``INFO`` lines describing the composition.
        """
        fmt = mm_to_fractional_inch
        findings = []
        lw, rw = self.window_stile("left"), self.window_stile("right")
        findings.append(
            Finding(
                Severity.INFO,
                "symmetry",
                f"window stiles {fmt(lw)} left, {fmt(rw)} right"
                + (" — a pair either side of the bay" if abs(lw - rw) < 0.5 else "")
                + f"; openings both {fmt(self.billy_width_mm - 2 * self.billy_panel_mm)}; "
                f"the left section's extra width is in its "
                f"{fmt(self.wall_stile('left'))} wall stile",
            )
        )
        case_c = self.billy_x("left") + self.billy_width_mm / 2
        hp_c = (self.heat_pump_x0 + self.heat_pump_x1) / 2
        findings.append(
            Finding(
                Severity.INFO,
                "symmetry",
                f"left case centre {fmt(abs(hp_c - case_c))} "
                f"{'left' if case_c < hp_c else 'right'} of the heat pump's "
                f"centre — the unit reads as sitting on the case's axis"
                if abs(hp_c - case_c) < inches(1.0)
                else f"left case centre is {fmt(abs(hp_c - case_c))} off the heat "
                f"pump's centre",
            )
        )
        if self.align_shelves:
            findings.append(
                Finding(
                    Severity.INFO,
                    "symmetry",
                    f"right shelves set on the left's lines, "
                    f"{fmt(self.shelf_heights('right')[1] - self.shelf_heights('right')[0])} "
                    f"apart, the top one level with the left case top — set "
                    f"each to the nearest pin hole",
                )
            )
        return findings

    def check_stock_lengths(self, parts: list[CutPart]) -> list[Finding]:
        """Flag trim longer than an 8' board will give clean.

        Returns
        -------
        list[Finding]
            One ``WARN`` listing the long parts, or nothing.
        """
        sheet = {s.material for s in self.inventory.sheet_goods}
        too_long = [p for p in parts if p.length_mm > inches(95.0)]
        boards = sorted({p.label for p in too_long if p.material not in sheet})
        panels = sorted({p.label for p in too_long if p.material in sheet})
        findings = []
        if boards:
            findings.append(
                Finding(
                    Severity.WARN,
                    "stock",
                    f"{', '.join(boards)} run past 95\" — an 8' board leaves "
                    f"no room to square the ends; buy 10' stock for them",
                )
            )
        if panels:
            findings.append(
                Finding(
                    Severity.WARN,
                    "stock",
                    f"{', '.join(panels)} run past 95\" — a 4x8 sheet leaves "
                    f"nothing to scribe to the ceiling; order 4x10 birch ply "
                    f'(or 49x97 MDF), or let the panel stop under a 1x '
                    f"crown-line rail",
                )
            )
        return findings

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
            "the right one extended to the ceiling, the left one cut down "
            "under the installed heat pump, with a poplar face frame, ply "
            "side panels at the bay, and fascia that keeps the unit's "
            "airflow clearances."
        ),
        species="poplar",
        build=design.build,
        check=design.check,
        inventory=design.inventory,
        notes=(
            'Measured: 42" (left) and 37-1/2" (right), wall to bay; 99" '
            "ceiling; LG KNUAB181A head installed 8\" below it. Assumed until "
            'measured: the head 4" off the left wall, 5-1/2" baseboard.'
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
    parser.add_argument("--ceiling", type=float, default=99.0)
    parser.add_argument("--baseboard", type=float, default=5.5)
    parser.add_argument("--heat-pump-bottom", type=float, default=None)
    parser.add_argument("--heat-pump-left-offset", type=float, default=4.0)
    parser.add_argument("--outdir", type=Path, default=Path("build"))
    args = parser.parse_args()
    run(
        BillyBuiltIns(
            left_width_in=args.left_width,
            right_width_in=args.right_width,
            ceiling_in=args.ceiling,
            baseboard_in=args.baseboard,
            heat_pump_bottom_in=args.heat_pump_bottom,
            heat_pump_left_offset_in=args.heat_pump_left_offset,
        ),
        args.outdir,
    )


if __name__ == "__main__":
    main()
