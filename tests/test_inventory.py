"""Tests for woodshop.inventory — loading stock.yaml and sheet-fit logic."""

from __future__ import annotations

import pytest

from woodshop.inventory import Inventory, SheetStock


@pytest.fixture(scope="module")
def inv() -> Inventory:
    return Inventory.load()


def test_stock_yaml_loads(inv):
    assert inv.dimensional and inv.hardwood and inv.sheet_goods


def test_baltic_birch_is_five_by_five_not_four_by_eight(inv):
    sheet = inv.sheet_for("plywood_baltic_birch", "3/4")
    assert sheet.width_mm == pytest.approx(1524.0)
    assert sheet.height_mm == pytest.approx(1524.0)


def test_baltic_birch_three_quarter_is_eighteen_millimetres(inv):
    sheet = inv.sheet_for("plywood_baltic_birch", "3/4")
    assert sheet.thickness_mm == pytest.approx(18.0, abs=0.02)


def test_sheet_for_unknown_material_lists_alternatives(inv):
    with pytest.raises(KeyError, match="stock.yaml has"):
        inv.sheet_for("plywood_unobtanium", "3/4")


def test_stock_lengths_spans_dimensional_and_hardwood(inv):
    assert inv.stock_lengths_mm("cherry") == [2438.4, 3048.0]
    assert inv.stock_lengths_mm("unobtanium") == []


def test_hardwood_surfaced_thickness(inv):
    assert inv.hardwood_for("cherry", "8/4").surfaced_thickness_mm == pytest.approx(44.45)


# ---------------------------------------------------------------------------
# fits(): the sheet's face grain runs along its height
# ---------------------------------------------------------------------------

_GRAINED = SheetStock(
    material="plywood_cherry", nominal_thickness="3/4", actual_thickness_in=0.703,
    sheet_width_in=48, sheet_height_in=96, grain="length",
)
_UNGRAINED = SheetStock(
    material="plywood_baltic_birch", nominal_thickness="3/4",
    actual_thickness_in=0.7087, sheet_width_in=60, sheet_height_in=60, grain="none",
)

_IN = 25.4


def test_long_grained_part_fits_along_the_sheet_grain():
    """Regression: a 61" part fits a 4x8 sheet by running along the 96" axis."""
    assert _GRAINED.fits(61.25 * _IN, 11.5 * _IN, "length")


def test_grained_part_cannot_be_turned_to_fit():
    # 60" along the grain is fine; 60" across a 48" sheet is not.
    assert _GRAINED.fits(60 * _IN, 10 * _IN, "length")
    assert not _GRAINED.fits(10 * _IN, 60 * _IN, "length")
    # With no grain requirement the same part can be turned.
    assert _GRAINED.fits(10 * _IN, 60 * _IN, "none")


def test_oversize_part_fits_no_orientation():
    """A queen slat is 62-1/2"; Baltic birch sheets are 60"."""
    assert not _UNGRAINED.fits(62.5 * _IN, 2.5 * _IN, "none")
    assert _UNGRAINED.fits(31.25 * _IN, 2.5 * _IN, "none")
