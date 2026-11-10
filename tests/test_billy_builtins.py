"""Tests for the BILLY built-ins — mostly a question of what fits under the ceiling."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "projects"))

from billy_builtins import BILLY, BILLY_EXT, IN, BillyBuiltIns  # noqa: E402

from woodshop.checks import Severity  # noqa: E402
from woodshop.cutlist.extract import extract, purchased_items  # noqa: E402
from woodshop.parts import Purchased  # noqa: E402


@pytest.fixture(scope="module")
def design() -> BillyBuiltIns:
    return BillyBuiltIns()


@pytest.fixture(scope="module")
def assembly(design):
    return design.build()


@pytest.fixture(scope="module")
def parts(assembly) -> list:
    return extract(assembly)


def _findings(report, category):
    return [f for f in report.findings if f.code == category]


# ---------------------------------------------------------------------------
# Purchased parts: drawn, never cut
# ---------------------------------------------------------------------------


def test_a_purchased_box_is_not_on_the_cut_list():
    box = Purchased(100.0, 50.0, 20.0, material="billy_white", label="case")
    assert extract(box) == []
    assert purchased_items(box) == {"case": 1}


def test_no_billy_panel_or_heat_pump_reaches_the_cut_list(parts):
    assert {p.material for p in parts} == {"poplar", "pine", "plywood_birch"}


def test_six_panels_of_a_bookcase_are_one_purchase(assembly):
    """Each BILLY is a dozen panels in the drawing and one line at the till."""
    bought = purchased_items(assembly)
    assert bought[BILLY] == 2
    assert bought[BILLY_EXT] == 1


# ---------------------------------------------------------------------------
# Fit across the alcoves
# ---------------------------------------------------------------------------


def test_the_sections_fill_their_measured_alcoves(design, assembly):
    bb = assembly.bounding_box()
    assert bb.size.X == pytest.approx((42 + 72 + 37.5) * IN, abs=0.1)
    assert bb.size.Z == pytest.approx(99 * IN, abs=0.1)


def test_the_right_billy_is_centred_with_matching_stiles(design, parts):
    by_label = {p.label: p for p in parts}
    centred = (37.5 * IN - 800) / 2 + 15
    assert by_label["right_wall_stile"].width_mm == pytest.approx(centred)
    assert by_label["right_window_stile"].width_mm == pytest.approx(centred)


def test_the_stiles_flanking_the_bay_are_a_pair(design, parts):
    by_label = {p.label: p for p in parts}
    assert by_label["left_window_stile"].width_mm == pytest.approx(
        by_label["right_window_stile"].width_mm
    )


def test_the_left_sections_extra_width_goes_to_its_wall_side(design):
    extra = (42 - 37.5) * IN
    assert design.wall_stile("left") == pytest.approx(design.wall_stile("right") + extra)


def test_without_the_closet_the_wall_side_is_a_stile(design):
    parts = extract(BillyBuiltIns(broom_closet=False).build())
    by_label = {p.label: p for p in parts}
    assert by_label["left_wall_stile"].width_mm == pytest.approx(design.wall_stile("left"))
    assert "broom_closet_door" not in by_label


def test_matching_the_window_stiles_centres_the_case_under_the_heat_pump(design):
    case_c = design.billy_x("left") + design.billy_width_mm / 2
    hp_c = (design.heat_pump_x0 + design.heat_pump_x1) / 2
    assert abs(case_c - hp_c) < 0.5 * IN
    centred = BillyBuiltIns(match_window_stiles=False)
    case_c = centred.billy_x("left") + centred.billy_width_mm / 2
    assert abs(case_c - hp_c) > 2 * IN


def test_unmatched_stiles_centre_each_billy_in_its_section():
    d = BillyBuiltIns(match_window_stiles=False)
    assert d.wall_stile("left") == pytest.approx(d.window_stile("left"))


def test_the_width_is_spent_on_nailers_billy_and_side_panel(design):
    for side in ("left", "right"):
        total = (
            design.wall_gap(side)
            + design.billy_width_mm
            + design.window_gap(side)
            + design.side_panel_mm
        )
        assert total == pytest.approx(design.width_of(side))


def test_the_right_shelves_sit_on_the_left_shelf_lines(design):
    left, right = design.shelf_heights("left"), design.shelf_heights("right")
    assert right[: len(left)] == pytest.approx(left)
    # ...and the next one is level with the left case's top.
    assert right[len(left)] == pytest.approx(design.left_case_top - 15.0, abs=1.0)


def test_shelf_alignment_can_be_turned_off():
    d = BillyBuiltIns(align_shelves=False)
    heights = d.shelf_heights("right")
    gaps = [b - a for a, b in zip(heights, heights[1:])]
    assert max(gaps) - min(gaps) < 1e-6
    assert len(heights) == 5


def _child(section, label):
    return next(c for c in section.children if getattr(c, "label", "") == label)


def test_each_section_has_a_side_panel_framing_the_bay(design, assembly):
    left, right = assembly.children[0], assembly.children[1]
    lp = _child(left, "left_side_panel")
    rp = _child(right, "right_side_panel")
    # On the bay side: the left section's right end, the right's left end.
    assert lp.bounding_box().max.X == pytest.approx(42 * IN, abs=0.01)
    assert rp.bounding_box().min.X == pytest.approx(design.right_x0, abs=0.01)
    assert lp.bounding_box().size.Y == pytest.approx(design.billy_depth_mm, abs=0.01)


def test_the_right_side_panel_reaches_the_ceiling_in_two_sheet_sized_pieces(
    design, assembly, parts
):
    """99" will not come out of a 4x8; the joint lands on the header line."""
    right = assembly.children[1]
    lower, upper = _child(right, "right_side_panel"), _child(right, "right_side_panel_top")
    assert upper.bounding_box().max.Z == pytest.approx(design.ceiling, abs=0.01)
    assert lower.bounding_box().max.Z == pytest.approx(
        design.ceiling - design.right_header_height, abs=0.01
    )
    panels = [p for p in parts if p.material == "plywood_birch"]
    assert all(p.length_mm <= 95 * IN for p in panels)


def test_the_left_side_panel_stops_at_the_cut_down_case(design, assembly):
    """The unit's right clearance reaches past the section edge."""
    assert not design.left_panel_to_ceiling
    lp = _child(assembly.children[0], "left_side_panel")
    assert lp.bounding_box().max.Z == pytest.approx(design.left_case_top, abs=0.01)


def test_nailers_fill_both_gaps_front_and_back(design, parts):
    by_label = {p.label: p for p in parts}
    for side, where in (("right", "wall"), ("right", "window"), ("left", "window")):
        nailer = by_label[f"{side}_{where}_nailer"]
        gap = design.wall_gap(side) if where == "wall" else design.window_gap(side)
        assert nailer.qty == 2
        assert nailer.width_mm == pytest.approx(gap)


def test_no_full_width_nailer_stands_beside_the_heat_pump(design, assembly):
    """Only a 1x2 nailer may rise past the left case top.

    A 5" nailer there would sit in the heat pump's side clearance.
    """
    left = assembly.children[0]
    for c in left.children:
        if "nailer" in getattr(c, "label", "") and c.label != "left_upper_wall_nailer":
            assert c.bounding_box().max.Z <= design.left_case_top + 0.01


def test_a_gap_too_narrow_for_a_nailer_is_flagged():
    findings = BillyBuiltIns(right_width_in=33.5).check_widths()
    assert any(f.severity is Severity.WARN and "nailer" in f.message for f in findings)


def test_an_alcove_narrower_than_a_billy_is_refused():
    with pytest.raises(ValueError, match="narrower than a BILLY"):
        BillyBuiltIns(right_width_in=32.0)


def test_the_symmetry_is_reported(design, assembly, parts):
    report = design.check(assembly, parts)
    lines = [f.message for f in _findings(report, "symmetry")]
    assert any("a pair either side of the bay" in m for m in lines)
    assert any("on the case's axis" in m for m in lines)


def test_the_bottom_shelf_lands_flush_with_the_baseboard_top(design):
    assert design.riser_height_mm + 3.25 * IN == pytest.approx(5.5 * IN)


# ---------------------------------------------------------------------------
# The extension under the ceiling
# ---------------------------------------------------------------------------


def test_the_extension_fits_comfortably_under_the_measured_ceiling(design):
    findings = design.check_extension_fit()
    assert all(f.severity is Severity.INFO for f in findings)
    assert design.ceiling - design.extension_top > 3 * IN


def test_an_eight_foot_ceiling_only_just_takes_the_extension():
    findings = BillyBuiltIns(ceiling_in=96.0).check_extension_fit()
    assert not [f for f in findings if f.severity is Severity.ERROR]
    assert any(f.severity is Severity.WARN for f in findings)


def test_a_lower_ceiling_will_not_take_the_extension():
    findings = BillyBuiltIns(ceiling_in=95.0).check_extension_fit()
    assert any(f.severity is Severity.ERROR for f in findings)


def test_the_right_header_closes_the_gap_to_the_ceiling(design):
    """At 99" the header is 4" and change — a 1x6 rip, not a 1x2."""
    assert design.right_header_height == pytest.approx(
        99 * IN - (design.extension_top - 15.0)
    )
    assert design.right_header_height > 4 * IN


# ---------------------------------------------------------------------------
# The heat pump, as installed
# ---------------------------------------------------------------------------


def test_the_installed_unit_sits_eight_inches_under_the_ceiling(design):
    assert design.ceiling - design.heat_pump_top == pytest.approx(8 * IN)
    assert design.heat_pump_bottom == pytest.approx(99 * IN - 8 * IN - 345.0)


def test_a_full_billy_would_run_into_the_unit(design):
    assert design.riser_height_mm + design.billy_height_mm > design.heat_pump_bottom


def test_the_left_billy_is_cut_down_to_leave_outlet_air(design):
    assert design.left_case_cut > 0
    assert design.heat_pump_bottom - design.left_case_top == pytest.approx(4 * IN)
    outlet = [f for f in design.check_heat_pump() if "cut the left BILLY" in f.message]
    assert outlet and outlet[0].severity is Severity.WARN


def test_the_cut_down_billy_keeps_shelves_at_about_the_full_pitch(design, assembly):
    shelves = [
        c for c in assembly.children[0].children if getattr(c, "label", "") == "billy_shelf"
    ]
    # 202 cm has five shelves in six openings; 71" of case keeps four in five.
    assert len(shelves) == 4


def test_a_lower_unit_that_leaves_room_needs_no_cut():
    design = BillyBuiltIns(ceiling_in=110.0)
    assert design.left_case_cut == 0
    outlet = [f for f in design.check_heat_pump() if "outlet" in f.message]
    assert outlet[0].severity is Severity.INFO


def test_a_unit_hung_too_low_for_a_bookcase_is_an_error():
    findings = BillyBuiltIns(heat_pump_bottom_in=26.0).check_heat_pump()
    assert any(f.severity is Severity.ERROR and "not a bookcase" in f.message for f in findings)


def test_the_wall_side_clearance_is_checked_against_the_offset():
    findings = BillyBuiltIns(heat_pump_left_offset_in=3.0).check_heat_pump()
    assert any(
        f.severity is Severity.ERROR and "left end" in f.message for f in findings
    )


def test_the_unit_is_too_wide_for_fascia_on_the_bay_side(design, parts):
    """39-5/16" + 4" + 4" is more than 42": no window upper stile."""
    labels = {p.label for p in parts}
    assert "left_window_upper_stile" not in labels
    assert "left_wall_upper_stile" in labels
    warn = [f for f in design.check_heat_pump() if "47-5/16" in f.message]
    assert warn and warn[0].severity is Severity.WARN


def test_a_wide_enough_section_frames_both_sides_to_the_ceiling():
    wide = BillyBuiltIns(left_width_in=48.5)
    assert wide.left_panel_to_ceiling
    labels = {p.label for p in extract(wide.build())}
    assert "left_window_upper_stile" in labels


def test_no_header_crosses_the_heat_pump_when_there_is_no_room(design, parts):
    assert design.left_header_height == 0.0
    assert "left_header" not in {p.label for p in parts}


def test_a_header_appears_above_the_clearance_when_there_is_room():
    design = BillyBuiltIns(heat_pump_bottom_in=72.0)
    assert design.left_header_height > 0
    header_bottom = design.ceiling - design.left_header_height
    assert header_bottom >= design.heat_pump_top + 8 * IN - 1e-6
    assert "left_header" in {p.label for p in extract(design.build())}


def test_the_upper_stile_frames_the_unit_without_covering_it(design):
    stile = [f for f in design.check_heat_pump() if "upper wall stile" in f.message]
    assert stile[0].severity is Severity.INFO


# ---------------------------------------------------------------------------
# Whole report
# ---------------------------------------------------------------------------


def test_the_default_design_has_no_errors(design, assembly, parts):
    report = design.check(assembly, parts)
    assert report.ok, report.to_text()


def test_the_shopping_list_is_in_the_report(design, assembly, parts):
    report = design.check(assembly, parts)
    purchases = _findings(report, "purchase")
    assert any(BILLY_EXT in f.message for f in purchases)


# ---------------------------------------------------------------------------
# The proposal render
# ---------------------------------------------------------------------------


def test_the_room_leaves_wall_behind_the_heat_pump(design):
    """The unit hangs on the wall, so the bay cannot open under its end."""
    from billy_builtins import BayRoom

    room = BayRoom(design)
    assert 42 * IN + room.pier > design.heat_pump_x1


def test_the_room_is_never_on_the_cut_list_or_shopping_list(design):
    from billy_builtins import BayRoom

    room = BayRoom(design).build()
    assert extract(room) == []


def test_the_proposal_sheet_is_written(design, tmp_path):
    from billy_builtins import render_proposal

    out = render_proposal(design, tmp_path / "proposal.png", size=400)
    assert out.exists() and out.stat().st_size > 10_000


# ---------------------------------------------------------------------------
# The broom closet
# ---------------------------------------------------------------------------


def test_the_closet_replaces_the_wall_stile_and_its_nailers(parts):
    labels = {p.label for p in parts}
    assert {"broom_closet_door", "broom_closet_lid", "broom_closet_kick"} <= labels
    assert "left_wall_stile" not in labels
    assert "left_wall_nailer" not in labels


def test_the_closed_door_reads_as_the_stile_it_replaced(design, assembly):
    door = _child(assembly.children[0], "broom_closet_door").bounding_box()
    assert door.size.X == pytest.approx(design.wall_stile("left") - 4.8, abs=0.1)
    assert door.min.Z == pytest.approx(5.5 * IN + 1.6, abs=0.1)
    assert door.max.Z == pytest.approx(design.left_case_top - 1.6, abs=0.1)


def test_the_closet_stops_at_the_case_top(design, assembly):
    """Above the case is the heat pump's side clearance."""
    for label in ("broom_closet_door", "broom_closet_lid"):
        bb = _child(assembly.children[0], label).bounding_box()
        assert bb.max.Z <= design.left_case_top + 0.01


def test_the_inside_is_the_wall_gap_by_the_case_depth(design):
    width, depth, height = design.closet_interior()
    assert width == pytest.approx(7.5 * IN, abs=0.5)
    assert depth == pytest.approx(design.billy_depth_mm)
    assert height > 70 * IN


def test_a_12_by_2_inch_head_does_not_fit_and_the_limit_is_reported(design):
    findings = design.check_broom_closet()
    head = findings[0]
    assert head.severity is Severity.WARN
    assert "11-9/16" in head.message


def test_an_11_and_a_half_inch_head_fits_on_the_diagonal():
    d = BillyBuiltIns(broom_head_in=11.5)
    head = d.check_broom_closet()[0]
    assert head.severity is Severity.INFO
    assert "diagonal" in head.message


def test_a_ten_inch_swiffer_fits_straight():
    d = BillyBuiltIns(broom_head_in=10.0, broom_head_thick_in=2.5)
    assert "straight" in d.check_broom_closet()[0].message


def test_the_broom_lifts_over_the_kick(design):
    lift = design.check_broom_closet()[1]
    assert lift.severity is Severity.INFO
    assert "lifts over" in lift.message


def test_a_long_handle_has_to_be_tilted_in():
    lift = BillyBuiltIns(broom_length_in=70.0).check_broom_closet()[1]
    assert lift.severity is Severity.WARN
