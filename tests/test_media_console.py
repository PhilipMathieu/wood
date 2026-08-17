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


def test_the_bays_come_out_wider_than_fifteen_because_the_plywood_is_thin(console):
    """45/64" stock leaves 5/32" more opening than a true 3/4" would."""
    assert console.panel_t == pytest.approx(45 / 64 * IN)
    assert console.bay_clear_w == pytest.approx(
        (console.overall_w - 6 * console.panel_t) / 5
    )
    assert 15 * IN < console.bay_clear_w < 15.25 * IN


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


def test_the_base_rail_covers_the_feet_but_does_not_stand_on_them(console, assembly):
    """The rail hides 25/64" of foot and stops a sixteenth short of the floor."""
    rail = _placed(assembly)["base_rail"][0].bounding_box()
    assert rail.min.Z == pytest.approx(0.0625 * IN, abs=0.01), (
        "only the uprights touch the floor"
    )
    assert rail.max.Z == pytest.approx(console.toe_reveal + console.panel_t, abs=0.01)
    assert rail.size.Z > console.panel_t, "it covers the feet as well as the shelf"


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

    Where a shelf crosses an upright, the upright has no material in the front
    half of the depth and the shelf none in the back half — so the two fill
    each other exactly, which is what lets them slide together with no glue.
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

    assert (upright & front).volume == pytest.approx(0.0, abs=1.0)
    assert (upright & back).volume > 0.0
    assert (shelf & front).volume > 0.0
    assert (shelf & back).volume == pytest.approx(0.0, abs=1.0)


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


def test_every_part_loses_exactly_the_slots_it_is_meant_to(console, assembly):
    placed = _placed(assembly)
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
        "upright_edge",
        "base_rail",
    }
    for strip in solid:
        assert strip.thickness_mm == pytest.approx(console.edge_t)
    plan = nest_hardwood(solid, console.inventory, "cherry")
    assert [g.stock.thickness_quarter for g in plan.groups] == ["4/4"]


def test_the_horizontal_edging_runs_unbroken(console, parts):
    """The shelves cross the uprights at the front, so their edging is one piece."""
    by_label = {p.label: p for p in parts}
    assert by_label["shelf_edge"].length_mm >= console.overall_w
    assert by_label["top_edge"].length_mm >= console.overall_w
    assert by_label["upright_edge"].length_mm < console.overall_h


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


def test_the_overhang_hands_the_bays_back_what_the_thicker_sheet_took(
    console, painted
):
    """The console is 80" either way; the case underneath is 79"."""
    assert painted.case_w == pytest.approx(79 * IN)
    assert painted.overall_w == console.overall_w
    assert abs(painted.bay_clear_w - 15 * IN) < abs(console.bay_clear_w - 15 * IN)
    assert abs(painted.bay_clear_w - 15 * IN) < IN / 16


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


def test_the_solid_top_is_still_housed_on_every_upright(painted):
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
