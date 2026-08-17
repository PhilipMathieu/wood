"""Tests for woodshop.checks — the design checks that run before cutting."""

from __future__ import annotations

import math
from datetime import date, timedelta

import pytest

from woodshop.checks import (
    Severity,
    alternative_sheets,
    check_envelope,
    check_material_suitability,
    check_price_provenance,
    check_sheet_fit,
    check_slat_deflection,
    check_thickness_substitution,
    check_tip_resistance,
    estimate_mass_kg,
)
from woodshop.cutlist.extract import CutPart
from woodshop.inventory import Inventory

_IN = 25.4


@pytest.fixture(scope="module")
def inv() -> Inventory:
    return Inventory.load()


def test_envelope_match_is_info():
    findings = check_envelope(100.0, 200.0, 300.0, 100.0, 200.0, 300.0)
    assert all(f.severity is Severity.INFO for f in findings)


def test_envelope_deviation_is_warned_with_the_delta():
    findings = check_envelope(125.4, 200.0, 300.0, 100.0, 200.0, 300.0)
    warn = [f for f in findings if f.severity is Severity.WARN]
    assert len(warn) == 1
    assert "+1.000 in." in warn[0].message


def test_queen_slat_fits_the_4x8_baltic_birch_sheet(inv):
    """Regression: 62-1/2" clears a 4x8, though not the 5x5."""
    slat = CutPart("slat", "plywood_baltic_birch", "none", 62.5 * _IN, 2.5 * _IN, 18.0)
    findings = check_sheet_fit([slat], inv)
    assert [f.severity for f in findings] == [Severity.INFO]
    assert '48" x 96"' in findings[0].message


def test_part_longer_than_every_stocked_sheet_is_an_error(inv):
    slat = CutPart("slat", "plywood_baltic_birch", "none", 120 * _IN, 2.5 * _IN, 18.0)
    findings = check_sheet_fit([slat], inv)
    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "largest" in findings[0].message


def test_half_slat_fits(inv):
    slat = CutPart("slat", "plywood_baltic_birch", "none", 31.25 * _IN, 2.5 * _IN, 18.0)
    assert check_sheet_fit([slat], inv)[0].severity is Severity.INFO


def test_grained_cherry_panel_fits_a_four_by_eight(inv):
    """Regression: this was wrongly reported as an error."""
    panel = CutPart(
        "headboard_panel", "plywood_cherry", "length", 61.25 * _IN, 11.5 * _IN, 17.86
    )
    assert check_sheet_fit([panel], inv)[0].severity is Severity.INFO


def test_solid_stock_is_not_sheet_checked(inv):
    board = CutPart("rail", "cherry", "length", 3000.0, 114.3, 25.4)
    assert check_sheet_fit([board], inv) == []


def test_nominal_three_quarter_ply_is_flagged_as_undersize(inv):
    panel = CutPart("panel", "plywood_cherry", "length", 1000.0, 300.0, 17.86)
    findings = check_thickness_substitution([panel], inv)
    assert len(findings) == 1
    assert findings[0].severity is Severity.WARN
    assert "loose" in findings[0].message


def test_deflection_within_limit_is_info():
    findings = check_slat_deflection(
        "cherry", span_mm=775.0, slat_width_mm=63.5, slat_thickness_mm=19.05,
        n_slats=16,
    )
    assert findings[0].severity is Severity.INFO


def test_baltic_birch_is_floppier_than_cherry_and_a_remedy_is_given():
    args = dict(span_mm=775.0, slat_width_mm=63.5, slat_thickness_mm=18.0, n_slats=16)
    cherry = check_slat_deflection("cherry", **args)[0]
    birch = check_slat_deflection("plywood_baltic_birch", **args)[0]
    assert cherry.severity is Severity.INFO
    assert birch.severity is Severity.WARN
    assert "would meet it" in birch.message


def test_unknown_material_does_not_raise():
    findings = check_slat_deflection(
        "unobtanium", span_mm=775.0, slat_width_mm=63.5, slat_thickness_mm=19.05,
        n_slats=16,
    )
    assert findings[0].severity is Severity.INFO


def test_alternative_sheets_finds_a_bigger_sheet(inv):
    others = alternative_sheets(
        inv, 62.5 * _IN, 2.5 * _IN,
        grain_direction="none",
        exclude_material="plywood_baltic_birch",
        reference_thickness_mm=18.0,
    )
    assert any("plywood_birch" in o for o in others)
    assert not any("plywood_baltic_birch" in o for o in others)


# ---------------------------------------------------------------------------
# Material versus operation
# ---------------------------------------------------------------------------


def _turned(material: str) -> CutPart:
    return CutPart(
        "leg", material, "length", 575.0, 44.45, 44.45, qty=3,
        shape="turned", profile='turned, 1-1/2" tapering to 1"',
    )


def _round(material: str) -> CutPart:
    return CutPart(
        "top", material, "length", 463.6, 463.6, 38.1,
        shape="round", finished_area_each_mm2=164_000.0, profile='18" dia. round',
    )


def test_plywood_cannot_be_turned(inv):
    findings = check_material_suitability([_turned("plywood_baltic_birch")], inv)
    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "long grain" in findings[0].message


def test_a_round_plywood_part_is_a_warning_not_an_error(inv):
    findings = check_material_suitability([_round("plywood_cherry")], inv)
    assert [f.severity for f in findings] == [Severity.WARN]
    assert "edge plies" in findings[0].message


def test_a_round_solid_part_gets_a_wood_movement_note(inv):
    findings = check_material_suitability([_round("cherry")], inv)
    assert [f.severity for f in findings] == [Severity.INFO]
    assert "out of round" in findings[0].message


def test_rectangular_parts_say_nothing(inv):
    board = CutPart("rail", "plywood_cherry", "length", 1000.0, 100.0, 18.0)
    assert check_material_suitability([board], inv) == []


def test_sheet_materials_are_recognised_without_an_inventory():
    """The check must still work for a material stock.yaml has never heard of."""
    findings = check_material_suitability([_turned("plywood_unobtanium")])
    assert [f.severity for f in findings] == [Severity.ERROR]


def test_each_part_is_reported_once_however_many_copies(inv):
    findings = check_material_suitability([_turned("cherry"), _turned("cherry")], inv)
    assert findings == []


# ---------------------------------------------------------------------------
# Sheet thickness
# ---------------------------------------------------------------------------


def test_a_sheet_part_two_layers_thick_is_reported_as_a_lamination(inv):
    thickness = 2 * inv.sheet_for("plywood_cherry", "3/4").thickness_mm
    part = CutPart("top", "plywood_cherry", "length", 463.6, 463.6, thickness)
    findings = [f for f in check_sheet_fit([part], inv) if "layers" in f.message]
    assert [f.severity for f in findings] == [Severity.INFO]
    assert "2 layers" in findings[0].message


def test_a_sheet_part_thicker_than_any_whole_number_of_layers_is_an_error(inv):
    part = CutPart("leg", "plywood_baltic_birch", "none", 575.0, 44.45, 44.45)
    errors = [f for f in check_sheet_fit([part], inv) if f.severity is Severity.ERROR]
    assert errors and "thickest" in errors[0].message


def test_a_normal_sheet_part_gets_no_thickness_complaint(inv):
    part = CutPart("panel", "plywood_cherry", "length", 1000.0, 300.0, 17.86)
    assert not any("thickest" in f.message for f in check_sheet_fit([part], inv))


# ---------------------------------------------------------------------------
# Mass and tipping
# ---------------------------------------------------------------------------


def test_mass_uses_the_finished_area_not_the_blank():
    """A round top weighs what the circle weighs, not what the square did."""
    square = CutPart("t", "cherry", "length", 400.0, 400.0, 25.0)
    disc = CutPart(
        "t", "cherry", "length", 400.0, 400.0, 25.0,
        shape="round", finished_area_each_mm2=math.pi * 400.0**2 / 4,
    )
    assert estimate_mass_kg([disc]) < estimate_mass_kg([square])
    assert estimate_mass_kg([disc]) / estimate_mass_kg([square]) == pytest.approx(
        math.pi / 4, abs=0.001
    )


def test_unknown_material_falls_back_to_a_default_density():
    part = CutPart("x", "unobtanium", "length", 1000.0, 100.0, 20.0)
    assert estimate_mass_kg([part]) > 0


def test_a_top_inside_the_stance_cannot_be_tipped():
    findings = check_tip_resistance(
        mass_kg=5.0, n_legs=4, foot_radius_mm=300.0, overhang_radius_mm=150.0
    )
    assert [f.severity for f in findings] == [Severity.INFO]
    assert "cannot tip" in findings[0].message


def test_three_legs_tip_sooner_than_four_for_the_same_footprint():
    """cos(pi/3) is 1/2; cos(pi/4) is 0.71. That is the whole difference."""
    args = dict(mass_kg=10.0, foot_radius_mm=200.0, overhang_radius_mm=230.0)
    three = check_tip_resistance(n_legs=3, **args)[0]
    four = check_tip_resistance(n_legs=4, **args)[0]
    assert three.severity is Severity.WARN
    assert four.severity is Severity.INFO


def test_the_tipping_load_is_reported_in_both_units():
    finding = check_tip_resistance(
        mass_kg=5.0, n_legs=3, foot_radius_mm=200.0, overhang_radius_mm=230.0
    )[0]
    assert "kg" in finding.message and "lb" in finding.message


def test_two_legs_is_not_a_thing_that_stands_up():
    with pytest.raises(ValueError, match="at least 3 legs"):
        check_tip_resistance(
            mass_kg=5.0, n_legs=2, foot_radius_mm=200.0, overhang_radius_mm=230.0
        )


def test_a_bandsawn_solid_part_gets_a_short_grain_note(inv):
    """Where the curve crosses the grain is where a leg breaks."""
    leg = CutPart(
        "foot_leg", "cherry", "length", 241.3, 142.9, 44.45, qty=2,
        shape="shaped", finished_area_each_mm2=25_000.0,
    )
    findings = check_material_suitability([leg], inv)
    assert [f.severity for f in findings] == [Severity.INFO]
    assert "short grain" in findings[0].message


def test_a_bandsawn_sheet_part_gets_no_grain_lecture(inv):
    """Plywood has no grain to run short; cutting a curve in it is routine."""
    part = CutPart(
        "bracket", "plywood_birch", "none", 300.0, 200.0, 18.0,
        shape="shaped", finished_area_each_mm2=40_000.0,
    )
    assert check_material_suitability([part], inv) == []


# ---------------------------------------------------------------------------
# Price provenance — issue #3
# ---------------------------------------------------------------------------

_TODAY = date(2026, 8, 17)


def _priced(**overrides) -> Inventory:
    """One cherry entry, priced however the test needs it."""
    entry = dict(
        species="cherry", thickness_quarter="4/4", rough_thickness_in=1.0,
        surfaced_thickness_in=0.75, typical_width_in=7, lengths_ft=[8],
        price_per_bf=12.50,
    )
    entry.update(overrides)
    return Inventory.from_dict({"hardwood": [entry]})


def _cherry_slat() -> CutPart:
    return CutPart("slat", "cherry", "length", 1000.0, 63.5, 19.05)


def test_a_price_with_no_date_is_an_error():
    """Every price in stock.yaml today: a number nobody has verified."""
    findings = check_price_provenance(_priced(), [_cherry_slat()], today=_TODAY)
    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "price_as_of" in findings[0].message


def test_a_price_older_than_the_threshold_is_stale():
    stock = _priced(
        price_as_of=_TODAY - timedelta(days=200),
        price_source="O'Brien Hardwoods, phone quote",
    )
    findings = check_price_provenance(stock, [_cherry_slat()], today=_TODAY)
    assert [f.severity for f in findings] == [Severity.WARN]
    assert "200 days ago" in findings[0].message
    assert "O'Brien" in findings[0].message


def test_a_current_price_is_reported_with_its_date_and_source():
    stock = _priced(
        price_as_of=date(2026, 8, 1), price_source="O'Brien Hardwoods, phone quote"
    )
    findings = check_price_provenance(stock, [_cherry_slat()], today=_TODAY)
    assert [f.severity for f in findings] == [Severity.INFO]
    assert "quoted 2026-08-01" in findings[0].message


def test_the_staleness_threshold_is_adjustable():
    stock = _priced(price_as_of=_TODAY - timedelta(days=30))
    assert check_price_provenance(
        stock, [_cherry_slat()], today=_TODAY, stale_after_days=14
    )[0].severity is Severity.WARN
    assert check_price_provenance(
        stock, [_cherry_slat()], today=_TODAY, stale_after_days=60
    )[0].severity is Severity.INFO


def test_a_material_with_no_price_at_all_is_warned_about():
    stock = _priced(price_per_bf=None)
    findings = check_price_provenance(stock, [_cherry_slat()], today=_TODAY)
    assert [f.severity for f in findings] == [Severity.WARN]
    assert "no price" in findings[0].message


def test_only_the_stock_a_design_actually_buys_is_audited(inv):
    """A 3/4" slat comes off 4/4 boards, so 10/4 has nothing to say about it."""
    findings = check_price_provenance(inv, [_cherry_slat()], today=_TODAY)
    assert len(findings) == 1
    assert findings[0].message.startswith("cherry 4/4")


def test_a_sheet_part_is_audited_against_the_sheet_it_fits(inv):
    """A 62-1/2" slat is bought on the 4x8, so that is the price that matters."""
    slat = CutPart("slat", "plywood_baltic_birch", "none", 62.5 * _IN, 2.5 * _IN, 18.0)
    findings = check_price_provenance(inv, [slat], today=_TODAY)
    assert len(findings) == 1
    assert '48" x 96"' in findings[0].message


def test_with_no_parts_the_whole_inventory_is_audited(inv):
    findings = check_price_provenance(inv, today=_TODAY)
    assert len(findings) == len(inv.all_stock())


def test_the_shipped_stock_file_is_honest_about_its_prices(inv):
    """Nothing in stock.yaml is dated yet, so nothing in it may look researched."""
    findings = check_price_provenance(inv, today=_TODAY)
    assert not any(f.severity is Severity.INFO for f in findings)
    assert all(
        f.severity is Severity.ERROR
        for f in findings
        if "carries no price_as_of" in f.message
    )
