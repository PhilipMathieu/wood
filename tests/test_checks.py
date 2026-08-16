"""Tests for woodshop.checks — the design checks that run before cutting."""

from __future__ import annotations

import pytest

from woodshop.checks import (
    Severity,
    alternative_sheets,
    check_envelope,
    check_sheet_fit,
    check_slat_deflection,
    check_thickness_substitution,
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


def test_oversize_baltic_birch_slat_is_an_error(inv):
    slat = CutPart("slat", "plywood_baltic_birch", "none", 62.5 * _IN, 2.5 * _IN, 18.0)
    findings = check_sheet_fit([slat], inv)
    assert [f.severity for f in findings] == [Severity.ERROR]
    assert "60" in findings[0].message


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
