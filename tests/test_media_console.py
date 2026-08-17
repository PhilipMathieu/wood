"""Tests for the media console — the piece that slides together and comes apart."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import pytest
from build123d import Box, Pos

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "projects"))

from media_console import (  # noqa: E402
    CD_CASE_D_IN,
    CD_CASE_H_IN,
    IN,
    LP_SLEEVE_IN,
    VARIANTS,
    MediaConsole,
    Variant,
)

from woodshop.checks import Severity  # noqa: E402
from woodshop.cutlist.extract import extract  # noqa: E402
from woodshop.cutlist.hardwood import nest_hardwood  # noqa: E402
from woodshop.cutlist.optimize_2d import pack_by_material  # noqa: E402
from woodshop.render.model3d import _iter_leaf_parts  # noqa: E402


@pytest.fixture(scope="module")
def console() -> MediaConsole:
    return MediaConsole()


@pytest.fixture(scope="module")
def assembly(console):
    return console.build()


@pytest.fixture(scope="module")
def parts(assembly):
    return extract(assembly)


def _placed(assembly) -> dict[str, list]:
    """Return every placed part, grouped by label, in the order built."""
    out: dict[str, list] = {}
    for part in _iter_leaf_parts(assembly):
        out.setdefault(part.label, []).append(part)
    return out


# ---------------------------------------------------------------------------
# The published envelope, and the openings it has to contain
# ---------------------------------------------------------------------------


def test_it_is_eighty_by_twenty_four_by_thirteen(assembly):
    bb = assembly.bounding_box()
    assert bb.size.X == pytest.approx(80 * IN, abs=0.1)
    assert bb.size.Y == pytest.approx(13 * IN, abs=0.1)
    assert bb.size.Z == pytest.approx(24 * IN, abs=0.1)


def test_the_openings_measure_what_the_brief_asked_for(console, assembly):
    """The two heights are held exactly; the plywood pays for it elsewhere."""
    placed = _placed(assembly)
    shelves = sorted(
        (p.bounding_box() for p in placed["shelf"]), key=lambda b: b.min.Z
    )
    top_underside = placed["top"][0].bounding_box().min.Z

    assert shelves[1].min.Z - shelves[0].max.Z == pytest.approx(13.5 * IN, abs=0.05)
    assert top_underside - shelves[1].max.Z == pytest.approx(8.0 * IN, abs=0.05)


def test_the_bays_are_what_the_panels_and_the_ears_leave(console):
    """Two things eat the published width: six panels, and the two overruns."""
    assert console.panel_t == pytest.approx(45 / 64 * IN)
    assert console.bay_clear_w == pytest.approx(
        (console.upright_span - 6 * console.panel_t) / 5
    )
    assert console.upright_span == pytest.approx(
        console.case_w - 2 * console.end_overhang
    )
    # Flush ends would give the 15-5/32" the design had before the overrun.
    flush = MediaConsole(end_overhang_in=0.0)
    assert 15 * IN < flush.bay_clear_w < 15.25 * IN
    assert console.bay_clear_w < flush.bay_clear_w


def test_the_overrun_is_the_makers_own_proportion(console):
    """~4" on an 11-1/2" panel, measured off their parts drawings."""
    assert console.end_overhang == pytest.approx(0.35 * console.panel_depth)
    assert MediaConsole(end_overhang_in=2.0).end_overhang == pytest.approx(2 * IN)


def test_the_overrun_makes_every_crossing_interior(console, assembly):
    """The point of it: no joint at the end of a member, on either part."""
    placed = _placed(assembly)
    shelf = min(placed["shelf"], key=lambda p: p.bounding_box().min.Z)
    end_upright = placed["upright"][0].bounding_box()

    # The shelf carries on past the outermost upright, at both ends.
    shelf_bb = shelf.bounding_box()
    assert end_upright.min.X - shelf_bb.min.X == pytest.approx(
        console.end_overhang, abs=0.5
    )
    assert shelf_bb.max.X - placed["upright"][-1].bounding_box().max.X == (
        pytest.approx(console.end_overhang, abs=0.5)
    )
    # ...so there is stock on both sides of the slot: probe just outside it.
    z = console.shelf_z(0) + console.panel_t / 2
    outboard = Pos(
        end_upright.min.X - console.panel_t,
        console.panel_back_y - console.lap_depth / 2,
        z,
    ) * Box(console.panel_t * 0.6, console.lap_depth * 0.5, console.panel_t * 0.5)
    assert (shelf & outboard).volume > 0


def test_the_leftover_height_becomes_a_toe_reveal(console, assembly):
    """Three panels of 45/64" give back 3/8" of the 24"; it goes to the floor."""
    placed = _placed(assembly)
    assert console.toe_reveal == pytest.approx(0.390625 * IN, abs=0.01)

    lowest_shelf = min(p.bounding_box().min.Z for p in placed["shelf"])
    assert lowest_shelf == pytest.approx(console.toe_reveal, abs=0.05)
    # The kit stands on its uprights, not on a shelf.
    assert min(p.bounding_box().min.Z for p in placed["upright"]) == pytest.approx(
        0.0, abs=0.01
    )


def test_the_uprights_own_edging_covers_their_feet(console, assembly):
    """No rail at the toe: each upright is edged in one piece to the floor."""
    strips = [p.bounding_box() for p in _placed(assembly)["upright_edge"]]
    assert len(strips) == console.n_uprights, "one strip per upright, not per row"
    for strip in strips:
        assert strip.min.Z == pytest.approx(0.0, abs=0.01)
        assert strip.max.Z == pytest.approx(console.top_underside_z, abs=0.01)
    assert "base_rail" not in _placed(assembly)


def test_a_record_sits_inside_the_bay_in_all_three_directions(console):
    sleeve = LP_SLEEVE_IN * IN
    assert console.bay_clear_w > sleeve
    assert console.record_bay_h_in * IN > sleeve
    assert console.overall_d > sleeve


def test_the_cd_row_takes_jewel_cases_two_deep(console):
    assert console.cd_ranks == 2
    assert 2 * CD_CASE_D_IN * IN < console.overall_d
    assert console.cd_row_h_in * IN > CD_CASE_H_IN * IN


# ---------------------------------------------------------------------------
# The half-laps are cut, and they interlock
# ---------------------------------------------------------------------------


def test_at_a_crossing_each_part_has_only_its_own_half(console, assembly):
    """The whole design in one assertion.

    Where a shelf crosses an upright, the *upright* keeps the front half of the
    depth and the shelf keeps the back — so the two fill each other exactly,
    which is what lets them slide together with no glue, and the front of the
    case reads as an unbroken vertical.  This is the way round the maker's own
    photographs show; the first version of this model had it reversed.
    """
    placed = _placed(assembly)
    upright = placed["upright"][2]
    shelf = min(placed["shelf"], key=lambda p: p.bounding_box().min.Z)

    z = console.shelf_z(0) + console.panel_t / 2
    x = console.upright_x(2)

    def probe(y: float):
        # Narrower than the upright, so it can only see that one part's stock.
        return Pos(x, y, z) * Box(
            console.panel_t * 0.6, console.lap_depth * 0.8, console.panel_t * 0.5
        )

    front = probe(console.panel_front_y + console.lap_depth / 2)
    back = probe(console.panel_back_y - console.lap_depth / 2)

    assert (upright & front).volume > 0.0
    assert (upright & back).volume == pytest.approx(0.0, abs=1.0)
    assert (shelf & front).volume == pytest.approx(0.0, abs=1.0)
    assert (shelf & back).volume > 0.0


def test_no_two_parts_occupy_the_same_space(console, assembly):
    """Interlocking, not interpenetrating: every joint has zero overlap."""
    placed = _placed(assembly)
    upright, top = placed["upright"][2], placed["top"][0]
    for shelf in placed["shelf"]:
        assert (upright & shelf).volume == pytest.approx(0.0, abs=1.0)
    assert (top & upright).volume == pytest.approx(0.0, abs=1.0)


def test_only_interlocking_parts_share_a_bounding_box(assembly):
    """Bounding boxes overlap exactly where the kit interlocks and nowhere else."""
    boxes = [(p.label, p.bounding_box()) for p in _iter_leaf_parts(assembly)]
    tol = 0.01

    clashes = set()
    for i, (label_a, a) in enumerate(boxes):
        for label_b, b in boxes[i + 1:]:
            if (
                min(a.max.X, b.max.X) - max(a.min.X, b.min.X) > tol
                and min(a.max.Y, b.max.Y) - max(a.min.Y, b.min.Y) > tol
                and min(a.max.Z, b.max.Z) - max(a.min.Z, b.min.Z) > tol
            ):
                clashes.add(tuple(sorted((label_a, label_b))))

    assert clashes == {("shelf", "upright"), ("top", "upright")}


def test_every_part_loses_exactly_the_slots_it_is_meant_to():
    """Square-cornered, so the only thing missing from a blank is joinery."""
    console = MediaConsole(corner_radius_in=0.0)
    placed = _placed(console.build())
    one_slot = console.panel_t * console.panel_t * console.lap_depth
    one_housing = console.panel_t * console.dado_depth * console.panel_depth

    upright_blank = console.upright_h * console.panel_depth * console.panel_t
    shelf_blank = console.shelf_len * console.panel_depth * console.panel_t
    top_blank = console.overall_w * console.panel_depth * console.panel_t

    assert upright_blank - placed["upright"][0].volume == pytest.approx(
        console.n_shelves * one_slot, rel=0.02
    )
    assert shelf_blank - placed["shelf"][0].volume == pytest.approx(
        console.n_uprights * one_slot, rel=0.02
    )
    assert top_blank - placed["top"][0].volume == pytest.approx(
        console.n_uprights * one_housing, rel=0.02
    )


def test_a_slot_takes_half_the_depth_so_one_part_can_be_both_members(console):
    assert console.lap_depth == pytest.approx(console.panel_depth / 2)


# ---------------------------------------------------------------------------
# The kit: three parts, none of them handed
# ---------------------------------------------------------------------------


def test_the_case_is_three_panel_parts_and_nine_pieces(parts):
    panels = {p.label: p for p in parts if p.material == "plywood_cherry"}
    assert set(panels) == {"upright", "shelf", "top"}
    assert panels["upright"].qty == 6
    assert panels["shelf"].qty == 2
    assert panels["top"].qty == 1
    assert sum(p.qty for p in panels.values()) == 9


def test_the_uprights_are_one_part_ends_included(console, assembly):
    """A slot open at an edge is symmetrical, so no upright is handed."""
    placed = _placed(assembly)
    volumes = [p.volume for p in placed["upright"]]
    assert volumes[0] == pytest.approx(volumes[-1], rel=1e-6)
    assert all(v == pytest.approx(volumes[0], rel=1e-6) for v in volumes)


def test_the_two_shelves_are_one_part_too(assembly):
    a, b = _placed(assembly)["shelf"]
    assert a.volume == pytest.approx(b.volume, rel=1e-6)
    assert a.bounding_box().size.X == pytest.approx(b.bounding_box().size.X)


def test_a_shelf_runs_the_whole_width(console, parts):
    shelf = {p.label: p for p in parts}["shelf"]
    assert shelf.length_mm == pytest.approx(console.overall_w)


def test_every_panel_is_cut_to_the_sheet_not_to_the_nominal(console, parts):
    panels = [p for p in parts if p.material == "plywood_cherry"]
    assert panels
    for p in panels:
        assert p.thickness_mm == pytest.approx(console.panel_t)
        assert p.thickness_mm < 0.75 * IN


def test_the_case_comes_off_two_sheets(console, parts):
    sheet_parts = [p for p in parts if p.material == "plywood_cherry"]
    packed = pack_by_material(sheet_parts, console.inventory)
    (result,) = packed.values()
    assert not result.unpacked
    assert result.sheets_used == 2


def test_the_front_edges_come_off_four_quarter_cherry(console, parts):
    solid = [p for p in parts if p.material == "cherry"]
    assert {p.label for p in solid} == {
        "top_edge",
        "shelf_edge",
        "shelf_ear_edge",
        "upright_edge",
    }
    for strip in solid:
        assert strip.thickness_mm == pytest.approx(console.edge_t)
    plan = nest_hardwood(solid, console.inventory, "cherry")
    assert [g.stock.thickness_quarter for g in plan.groups] == ["4/4"]


def test_the_upright_edging_runs_unbroken_and_the_shelves_fill_between(console, parts):
    """The uprights cross the shelves at the front, so their edging is one piece."""
    by_label = {p.label: p for p in parts}
    assert by_label["upright_edge"].qty == console.n_uprights
    assert by_label["upright_edge"].length_mm >= console.upright_edge_h
    assert by_label["shelf_edge"].qty == console.n_bays * console.n_shelves
    assert by_label["shelf_edge"].length_mm < console.bay_clear_w + 25.4
    assert by_label["top_edge"].length_mm >= console.case_w


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def test_the_console_can_be_built(console, assembly, parts):
    report = console.check(assembly, parts)
    assert report.ok, report.to_text()


def test_the_kit_is_described_as_a_grid(console, assembly, parts):
    report = console.check(assembly, parts)
    kit = [f for f in report.findings if f.code == "kit"]
    assert any("5x2 grid" in f.message for f in kit)
    assert any("No part is handed" in f.message for f in kit)


def test_a_slack_slot_is_warned_about_because_nothing_takes_it_up(
    console, assembly, parts
):
    """In a glued case 1/32" is a glue line; with no glue it is the joint."""
    report = console.check(assembly, parts)
    slot = [
        f for f in report.findings
        if f.code == "kit" and f.severity is Severity.WARN
    ]
    assert slot and "45/64" in slot[0].message


def test_a_loaded_bay_does_not_sag(console, assembly, parts):
    report = console.check(assembly, parts)
    sag = [
        f for f in report.findings
        if f.code == "deflection" and "bay of records" in f.message
    ]
    assert [f.severity for f in sag] == [Severity.INFO]


def test_even_an_all_half_lap_shelf_would_hold(console, assembly, parts):
    """The upper bound on what the notches cost: still inside the limit."""
    report = console.check(assembly, parts)
    bound = [
        f for f in report.findings
        if f.code == "deflection" and "half-lap ran its whole length" in f.message
    ]
    assert [f.severity for f in bound] == [Severity.INFO]


def test_the_same_shelf_with_no_uprights_would_sag_four_inches(
    console, assembly, parts
):
    report = console.check(assembly, parts)
    undivided = [
        f for f in report.findings
        if f.code == "deflection" and "no uprights under it" in f.message
    ]
    assert [f.severity for f in undivided] == [Severity.WARN]
    assert "bays across" in undivided[0].message


def test_the_fifth_bay_is_for_the_records_not_for_the_plywood(console, assembly, parts):
    """Sag asks for three bays.  The other two are about how records stand."""
    report = console.check(assembly, parts)
    assert any(
        f.code == "bay" and "lean and warp" in f.message for f in report.findings
    )


def test_the_report_says_what_holds_a_glueless_case_together(console, assembly, parts):
    report = console.check(assembly, parts)
    racking = [f for f in report.findings if f.code == "racking"]
    assert any("no glue" in f.message for f in racking)
    assert any("friction" in f.message for f in racking)


# ---------------------------------------------------------------------------
# The painted build: a different sheet, no edging, and a top that moves
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def painted() -> MediaConsole:
    return MediaConsole(variant="painted")


@pytest.fixture(scope="module")
def painted_parts(painted):
    return extract(painted.build())


def test_the_painted_build_keeps_the_published_envelope(painted):
    bb = painted.build().bounding_box()
    assert bb.size.X == pytest.approx(80 * IN, abs=0.1)
    assert bb.size.Y == pytest.approx(13 * IN, abs=0.1)
    assert bb.size.Z == pytest.approx(24 * IN, abs=0.1)


def test_paint_grade_birch_is_thicker_than_cherry_ply_and_the_kit_follows(
    console, painted
):
    """Same design, different sheet: 23/32" against 45/64", and every slot moves."""
    assert painted.panel_t == pytest.approx(23 / 32 * IN)
    assert painted.panel_t > console.panel_t
    assert painted.toe_reveal < console.toe_reveal
    assert painted.upright_h != console.upright_h


def test_the_solid_tops_overhang_comes_out_of_the_case_not_the_room(
    console, painted
):
    """The console is 80" either way; the horizontals under the top run 79"."""
    assert painted.case_w == pytest.approx(79 * IN)
    assert painted.overall_w == console.overall_w
    # Flush-ended, the thicker birch would cost about an eighth of bay; the
    # top's own overhang hands most of it back.
    flush_cherry = MediaConsole(end_overhang_in=0.0)
    flush_painted = MediaConsole(variant="painted", end_overhang_in=0.0)
    assert abs(flush_painted.bay_clear_w - flush_cherry.bay_clear_w) < IN / 4


def test_the_painted_build_is_eight_pieces_of_plywood_and_one_board(painted_parts):
    plywood = [p for p in painted_parts if p.material == "plywood_birch"]
    solid = [p for p in painted_parts if p.material == "cherry"]
    assert {p.label for p in plywood} == {"upright", "shelf"}
    assert sum(p.qty for p in plywood) == 8
    assert [p.label for p in solid] == ["top"]


def test_there_is_no_edging_to_hide_a_painted_edge(painted, painted_parts):
    assert not painted.has_edging
    assert painted.edge_t == 0
    assert painted.panel_depth == pytest.approx(painted.overall_d)
    assert not [p for p in painted_parts if p.label.endswith("_edge")]


def test_the_solid_top_overhangs_the_case_at_each_end(painted):
    placed = _placed(painted.build())
    top = placed["top"][0].bounding_box()
    uprights = [p.bounding_box() for p in placed["upright"]]

    assert top.size.X == pytest.approx(80 * IN, abs=0.05)
    assert top.size.Y == pytest.approx(13 * IN, abs=0.05)
    assert top.min.X < min(b.min.X for b in uprights) - IN / 4
    assert top.max.X > max(b.max.X for b in uprights) + IN / 4


def test_the_solid_top_is_still_housed_on_every_upright():
    """Square-cornered: the radius takes its own bite, measured separately."""
    painted = MediaConsole(variant="painted", corner_radius_in=0.0)
    placed = _placed(painted.build())
    top = placed["top"][0]
    blank = painted.overall_w * painted.overall_d * painted.top_t
    one_housing = painted.panel_t * painted.dado_depth * painted.panel_depth
    assert blank - top.volume == pytest.approx(
        painted.n_uprights * one_housing, rel=0.02
    )
    for upright in placed["upright"]:
        assert (top & upright).volume == pytest.approx(0.0, abs=1.0)


def test_the_painted_build_can_be_built(painted, painted_parts):
    report = painted.check(painted.build(), painted_parts)
    assert report.ok, report.to_text()


def test_the_top_is_the_one_part_that_moves(painted, painted_parts):
    """A plywood case does not move; 13" of cherry across the grain does."""
    report = painted.check(painted.build(), painted_parts)
    movement = [f for f in report.findings if f.code == "movement"]
    assert movement, report.to_text()
    assert all(f.severity is Severity.INFO for f in movement)
    assert "3/16" in movement[0].message
    assert any("housings run front to back" in f.message for f in movement)


def test_the_cherry_build_has_nothing_wide_enough_to_move(console, assembly, parts):
    report = console.check(assembly, parts)
    assert not [f for f in report.findings if f.code == "movement"]


def test_a_bare_plywood_edge_is_reported_rather_than_assumed_fine(painted):
    report = painted.check(painted.build(), extract(painted.build()))
    assert any(
        f.code == "material" and "does not fill a void" in f.message
        for f in report.findings
    )


def test_the_painted_top_is_a_glue_up_of_solid_stock(painted, painted_parts):
    solid = [p for p in painted_parts if p.material == "cherry"]
    plan = nest_hardwood(solid, painted.inventory, "cherry")
    assert [label for label, _, _ in plan.glue_ups] == ["top"]
    assert [g.stock.thickness_quarter for g in plan.groups] == ["4/4"]


# ---------------------------------------------------------------------------
# Rounded corners, borrowed from the same system as the joinery
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def rounded(console) -> MediaConsole:
    """Return the shipped design — the radius is on by default now."""
    return console


def test_the_radius_is_the_makers_proportion_by_default(console):
    assert console.corner_radius == pytest.approx(0.07 * console.panel_depth)
    assert console.corner_radius == pytest.approx(console.reference_corner_radius)
    assert 0.85 * IN < console.corner_radius < 0.95 * IN
    assert MediaConsole(corner_radius_in=0.0).corner_radius == 0.0


def test_a_radius_does_not_move_the_envelope_or_the_openings(rounded):
    square = MediaConsole(corner_radius_in=0.0)
    bb = rounded.build().bounding_box()
    assert bb.size.X == pytest.approx(80 * IN, abs=0.1)
    assert bb.size.Y == pytest.approx(13 * IN, abs=0.1)
    assert bb.size.Z == pytest.approx(24 * IN, abs=0.1)
    assert rounded.bay_clear_w == pytest.approx(square.bay_clear_w)
    assert rounded.toe_reveal == pytest.approx(square.toe_reveal)


def test_a_radius_makes_the_panels_shaped_and_leaves_the_shelves_alone(rounded):
    """The cut list has to say a panel is sawn to a profile, not cut to size."""
    parts = {p.label: p for p in extract(rounded.build())}
    assert parts["upright"].shape == "shaped"
    assert parts["top"].shape == "shaped"
    assert parts["shelf"].shape == "rectangular"


def test_all_four_corners_of_an_upright_are_gone_and_the_edges_are_not(rounded):
    """Four corners, not "the bottom two" — which the first draft got upside down.

    The rotation that stands an upright on end reverses its length axis, so a
    profile rounded at its X origin comes out rounded at the ceiling.  Rounding
    every corner is both the look and the end of that trap.
    """
    upright = _placed(rounded.build())["upright"][0]
    bb = upright.bounding_box()
    x = (bb.min.X + bb.max.X) / 2
    # Sized off the radius so the whole probe stays outside the arc: its far
    # corner sits 1.1r from the arc centre.
    inset = 0.15 * rounded.corner_radius
    side = 0.15 * rounded.corner_radius

    def probe(y: float, z: float):
        return Pos(x, y, z) * Box(rounded.panel_t * 2, side, side)

    for y in (bb.min.Y + inset, bb.max.Y - inset):
        for z in (bb.min.Z + inset, bb.max.Z - inset):
            assert probe(y, z).volume > 0
            assert (upright & probe(y, z)).volume == pytest.approx(0.0, abs=1e-6)

    mid_y, mid_z = (bb.min.Y + bb.max.Y) / 2, (bb.min.Z + bb.max.Z) / 2
    assert (upright & probe(mid_y, bb.max.Z - inset)).volume > 0
    assert (upright & probe(bb.min.Y + inset, mid_z)).volume > 0


def test_the_rounded_top_still_houses_every_upright(rounded):
    """The radius eats the ends of the two outer housings, and only those."""
    placed = _placed(rounded.build())
    raw_top = (
        Pos(0.0, rounded.panel_y, rounded.top_underside_z + rounded.top_t / 2)
        * rounded._top()
    )
    slab = Pos(0.0, 0.0, rounded.top_underside_z + rounded.dado_depth / 2) * Box(
        3000.0, 900.0, rounded.dado_depth
    )
    middle = placed["upright"][2] & slab
    end = placed["upright"][0] & slab
    assert (middle & raw_top).volume == pytest.approx(middle.volume, rel=1e-6)
    assert (end & raw_top).volume > 0.95 * end.volume


def test_a_radius_too_big_for_the_panel_is_rejected():
    console = MediaConsole(corner_radius_in=10.0)
    with pytest.raises(ValueError, match="does not fit twice"):
        console.build()


# ---------------------------------------------------------------------------
# The numbers that must not be silently impossible
# ---------------------------------------------------------------------------


def test_one_bay_is_not_a_run_of_bays():
    with pytest.raises(ValueError, match="at least 2"):
        MediaConsole(n_bays=1)


def test_openings_taller_than_the_case_are_rejected():
    with pytest.raises(ValueError, match="does not fit inside"):
        MediaConsole(record_bay_h_in=18.0)


def test_a_housing_deeper_than_the_stock_is_rejected():
    with pytest.raises(ValueError, match="goes through"):
        MediaConsole(dado_depth_in=0.75)


def test_an_unknown_variant_is_rejected():
    with pytest.raises(ValueError, match="variant must be one of"):
        MediaConsole(variant="veneered")


def test_edging_deeper_than_the_case_is_rejected(monkeypatch):
    """Guards the variant table, which is now where such a number would land."""
    absurd = replace(VARIANTS["cherry"], name="absurd", edge_thickness_in=13.0)
    assert isinstance(absurd, Variant)
    monkeypatch.setitem(VARIANTS, "absurd", absurd)
    with pytest.raises(ValueError, match="leaves no panel"):
        MediaConsole(variant="absurd")


def test_a_column_costs_one_upright_and_longer_shelves():
    six = MediaConsole(n_bays=6)
    assert six.n_uprights == 7
    assert six.bay_clear_w < MediaConsole().bay_clear_w
    assert six.grid_label == "6x2"

    parts = {p.label: p for p in extract(six.build())}
    assert parts["upright"].qty == 7
    assert parts["shelf"].qty == 2
    bb = six.build().bounding_box()
    assert bb.size.X == pytest.approx(80 * IN, abs=0.1)
    assert bb.size.Z == pytest.approx(24 * IN, abs=0.1)
