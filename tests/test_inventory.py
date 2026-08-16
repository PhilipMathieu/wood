"""Tests for woodshop.inventory — loading stock.yaml and sheet-fit logic."""

from __future__ import annotations

import pytest

from woodshop.inventory import Inventory, SheetStock


@pytest.fixture(scope="module")
def inv() -> Inventory:
    return Inventory.load()


def test_stock_yaml_loads(inv):
    assert inv.dimensional and inv.hardwood and inv.sheet_goods


def test_baltic_birch_is_stocked_in_two_sizes(inv):
    sizes = {
        (s.sheet_width_in, s.sheet_height_in)
        for s in inv.sheets_for("plywood_baltic_birch", "3/4")
    }
    assert sizes == {(60, 60), (48, 96)}


def test_sheet_for_returns_the_smallest_size(inv):
    sheet = inv.sheet_for("plywood_baltic_birch", "3/4")
    assert sheet.width_mm == pytest.approx(1524.0)
    assert sheet.height_mm == pytest.approx(1524.0)


def test_best_sheet_prefers_the_smallest_that_fits(inv):
    small = inv.best_sheet_for(
        "plywood_baltic_birch", length_mm=31.25 * _IN, width_mm=2.5 * _IN,
        nominal_thickness="3/4",
    )
    assert (small.sheet_width_in, small.sheet_height_in) == (60, 60)


def test_best_sheet_upgrades_when_the_part_is_too_long(inv):
    """Regression: a 62-1/2" slat must select the 4x8, not the 5x5."""
    big = inv.best_sheet_for(
        "plywood_baltic_birch", length_mm=62.5 * _IN, width_mm=2.5 * _IN,
        nominal_thickness="3/4",
    )
    assert (big.sheet_width_in, big.sheet_height_in) == (48, 96)


def test_best_sheet_falls_back_to_the_largest_when_nothing_fits(inv):
    huge = inv.best_sheet_for(
        "plywood_baltic_birch", length_mm=120 * _IN, width_mm=2.5 * _IN,
        nominal_thickness="3/4",
    )
    assert (huge.sheet_width_in, huge.sheet_height_in) == (48, 96)


def test_best_sheet_for_unknown_material_raises(inv):
    with pytest.raises(KeyError, match="no sheet stock"):
        inv.best_sheet_for("plywood_unobtanium", length_mm=100.0, width_mm=100.0)


def test_cherry_is_stocked_in_the_thicknesses_obrien_lists(inv):
    quarters = {h.thickness_quarter for h in inv.hardwood if h.species == "cherry"}
    assert {"4/4", "5/4", "6/4", "8/4", "10/4"} <= quarters


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

_IN = 25.4

_GRAINED = SheetStock(
    material="plywood_cherry", nominal_thickness="3/4", actual_thickness_in=0.703,
    sheet_width_in=48, sheet_height_in=96, grain="length",
)
_UNGRAINED = SheetStock(
    material="plywood_baltic_birch", nominal_thickness="3/4",
    actual_thickness_in=0.7087, sheet_width_in=60, sheet_height_in=60, grain="none",
)

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
