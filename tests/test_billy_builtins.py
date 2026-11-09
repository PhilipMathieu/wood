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
    assert bb.size.Z == pytest.approx(96 * IN, abs=0.1)


def test_each_stile_covers_the_filler_and_laps_the_billy_side(design, parts):
    by_label = {p.label: p for p in parts}
    # The BILLY stays centred: 42" less 80 cm, split, plus a 15 mm side.
    assert by_label["left_wall_stile"].width_mm == pytest.approx((42 * IN - 800) / 2 + 15)
    assert by_label["right_wall_stile"].width_mm == pytest.approx(
        (37.5 * IN - 800) / 2 + 15
    )


def test_both_stiles_of_a_section_are_the_same_width(parts):
    by_label = {p.label: p for p in parts}
    for side in ("left", "right"):
        assert by_label[f"{side}_window_stile"].width_mm == pytest.approx(
            by_label[f"{side}_wall_stile"].width_mm
        )


def test_the_width_is_spent_on_nailers_billy_and_side_panel(design):
    for width in (design.left_width_in, design.right_width_in):
        total = (
            design.wall_gap(width)
            + design.billy_width_mm
            + design.window_gap(width)
            + design.side_panel_mm
        )
        assert total == pytest.approx(width * IN)


def test_each_section_has_a_side_panel_framing_the_bay(design, assembly, parts):
    panels = {p.label: p for p in parts if p.material == "plywood_birch"}
    assert set(panels) == {"left_side_panel", "right_side_panel"}
    for p in panels.values():
        assert p.length_mm == pytest.approx(design.ceiling)
        assert p.width_mm == pytest.approx(design.billy_depth_mm)
    # The panels sit on the bay side: left section's right end, right's left.
    left, right = assembly.children[0], assembly.children[1]
    lp = next(c for c in left.children if getattr(c, "label", "") == "left_side_panel")
    rp = next(c for c in right.children if getattr(c, "label", "") == "right_side_panel")
    assert lp.bounding_box().max.X == pytest.approx(42 * IN, abs=0.01)
    assert rp.bounding_box().min.X == pytest.approx(design.right_x0, abs=0.01)


def test_nailers_fill_both_gaps_front_and_back(design, parts):
    by_label = {p.label: p for p in parts}
    for side, width in (("left", 42.0), ("right", 37.5)):
        wall, window = by_label[f"{side}_wall_nailer"], by_label[f"{side}_window_nailer"]
        assert wall.qty == window.qty == 2
        assert wall.width_mm == pytest.approx(design.wall_gap(width))
        assert window.width_mm == pytest.approx(design.window_gap(width))


def test_no_full_width_nailer_stands_beside_the_heat_pump(design, assembly):
    """Only a 1x2 nailer may rise past the left case top.

    A 5" nailer there would sit in the heat pump's side clearance.
    """
    left = assembly.children[0]
    for c in left.children:
        if "nailer" in getattr(c, "label", "") and c.label != "left_upper_wall_nailer":
            assert c.bounding_box().max.Z <= design.billy_top + 0.01


def test_a_gap_too_narrow_for_a_nailer_is_flagged():
    findings = BillyBuiltIns(right_width_in=33.5).check_widths()
    assert any(f.severity is Severity.WARN and "nailer" in f.message for f in findings)


def test_an_alcove_narrower_than_a_billy_is_refused():
    with pytest.raises(ValueError, match="narrower than a BILLY"):
        BillyBuiltIns(right_width_in=32.0)


def test_the_bottom_shelf_lands_flush_with_the_baseboard_top(design):
    assert design.riser_height_mm + 3.25 * IN == pytest.approx(5.5 * IN)


# ---------------------------------------------------------------------------
# The extension under the ceiling
# ---------------------------------------------------------------------------


def test_the_extension_just_fits_under_an_eight_foot_ceiling(design):
    findings = design.check_extension_fit()
    assert not [f for f in findings if f.severity is Severity.ERROR]
    assert any(f.severity is Severity.WARN for f in findings)


def test_a_lower_ceiling_will_not_take_the_extension():
    findings = BillyBuiltIns(ceiling_in=95.0).check_extension_fit()
    assert any(f.severity is Severity.ERROR for f in findings)


def test_a_taller_ceiling_grows_the_right_header():
    tall = BillyBuiltIns(ceiling_in=108.0)
    assert tall.right_header_height == pytest.approx(
        108 * IN - (tall.extension_top - 15.0)
    )


# ---------------------------------------------------------------------------
# The heat pump
# ---------------------------------------------------------------------------


def test_the_42_inch_alcove_meets_the_side_clearances(design):
    side = [
        f for f in design.check_heat_pump() if " end " in f.message and "needs" in f.message
    ]
    assert len(side) == 2
    assert all(f.severity is Severity.INFO for f in side)


def test_a_narrow_left_alcove_breaks_a_side_clearance():
    findings = BillyBuiltIns(left_width_in=38.0).check_heat_pump()
    assert any(
        f.severity is Severity.ERROR and "needs" in f.message
        for f in findings
    )


def test_the_right_clearance_is_measured_to_the_side_panel(design):
    right = [f for f in design.check_heat_pump() if "right end" in f.message]
    assert "side panel" in right[0].message


def test_a_ceiling_over_eight_feet_outgrows_a_4x8_side_panel():
    tall = BillyBuiltIns(ceiling_in=100.0)
    assert any("4x10" in f.message for f in tall.check_stock_lengths(extract(tall.build())))


def test_at_eight_feet_the_outlet_is_crowded_by_the_case_top(design):
    outlet = [f for f in design.check_heat_pump() if "outlet" in f.message]
    assert outlet[0].severity is Severity.WARN
    assert "ceiling" in outlet[0].message


def test_a_taller_ceiling_frees_the_outlet():
    outlet = [
        f for f in BillyBuiltIns(ceiling_in=100.0).check_heat_pump()
        if "outlet" in f.message
    ]
    assert outlet[0].severity is Severity.INFO


def test_no_header_crosses_the_heat_pump_when_there_is_no_room(design, parts):
    assert design.left_header_height == 0.0
    assert "left_header" not in {p.label for p in parts}


def test_a_header_appears_above_the_clearance_when_there_is_room():
    design = BillyBuiltIns(ceiling_in=100.0, heat_pump_bottom_in=84.0)
    assert design.left_header_height > 0
    header_bottom = design.ceiling - design.left_header_height
    assert header_bottom >= design.heat_pump_top + 2.125 * IN - 1e-6
    assert "left_header" in {p.label for p in extract(design.build())}


def test_the_upper_stiles_frame_the_unit_without_covering_it(design):
    stile = [f for f in design.check_heat_pump() if "upper stiles" in f.message]
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
