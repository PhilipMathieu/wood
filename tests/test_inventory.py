"""Tests for woodshop.inventory — loading stock.yaml and sheet-fit logic."""

from __future__ import annotations

import datetime

import pytest

from woodshop.inventory import DimensionalStock, Inventory, SheetStock


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


# ---------------------------------------------------------------------------
# Price provenance — issue #3
# ---------------------------------------------------------------------------


def test_a_price_in_stock_yaml_is_either_dated_or_labelled_a_placeholder(inv):
    """No third state: a number with neither a date nor a warning is the bug."""
    priced = [s for s in inv.all_stock() if s.price is not None]
    assert priced
    for stock in priced:
        if stock.price_is_verified:
            assert stock.price_source and "PLACEHOLDER" not in stock.price_source
        else:
            assert "PLACEHOLDER" in stock.price_source


def test_the_cherry_and_plywood_prices_are_still_undated_placeholders(inv):
    """O'Brien publishes no prices; these stay visibly invented until they do."""
    undated = [s for s in inv.all_stock() if s.price is not None
               and not s.price_is_verified]
    assert {s.stock_label.split()[0] for s in undated} == {
        "cherry", "plywood_cherry", "plywood_baltic_birch"
    }


def test_the_cedar_prices_are_real_dated_and_sourced(inv):
    """Lumbery publishes a full guide, so this is the one supplier we can cite."""
    cedar = [d for d in inv.dimensional if d.species == "white_cedar"]
    assert len(cedar) > 20
    for entry in cedar:
        assert entry.price_is_verified
        assert entry.price_as_of == datetime.date(2026, 8, 17)
        assert entry.price_source.startswith("Lumbery")
        assert entry.price_url.startswith("https://lumbery-me.com/")


def test_cedar_is_priced_by_the_lineal_foot_as_the_guide_quotes_it(inv):
    """The guide's unit, kept as published rather than converted."""
    board = next(
        d for d in inv.dimensional
        if d.species == "white_cedar" and d.nominal == "1x6"
        and d.profile == "rough sawn" and d.grade == "STK"
    )
    assert board.price_unit == "lineal ft"
    assert board.price == pytest.approx(2.30)
    # 12 boards of 6 ft: the rate multiplies feet, not sticks.
    assert board.price_line(72).amount == pytest.approx(165.60)


def test_grade_and_profile_separate_two_prices_for_the_same_size(inv):
    """A rough 1x6 in STK and in low grade are different products."""
    ones = [
        d for d in inv.dimensional
        if d.species == "white_cedar" and d.nominal == "1x6"
        and d.profile == "rough sawn"
    ]
    assert {d.grade for d in ones} == {"STK", "low"}
    assert len({d.stock_label for d in ones}) == 2
    assert "white_cedar 1x6 rough sawn (STK)" in {d.stock_label for d in ones}


def test_an_entry_cannot_be_priced_two_ways_at_once():
    with pytest.raises(ValueError, match="not both"):
        DimensionalStock(
            species="white_cedar", nominal="1x6", lengths_ft=[8],
            price_per_piece=18.40, price_per_lineal_ft=2.30,
        )


def test_an_iso_date_string_loads_as_a_date():
    inv = Inventory.from_dict(
        {
            "sheet_goods": [
                dict(
                    material="plywood_birch", nominal_thickness="3/4",
                    actual_thickness_in=0.71875, sheet_width_in=48,
                    sheet_height_in=96, price_per_sheet=90.0,
                    price_as_of="2026-08-16", price_source="Home Depot shelf tag",
                )
            ]
        }
    )
    sheet = inv.sheet_goods[0]
    assert sheet.price_as_of == datetime.date(2026, 8, 16)
    assert sheet.price_is_verified
    assert sheet.price_age_days(datetime.date(2026, 8, 26)) == 10
    assert sheet.price_note() == "Home Depot shelf tag, 2026-08-16"


def test_a_price_date_that_is_not_a_date_is_rejected():
    """A price dated "soon" would satisfy the check that looks for a date."""
    with pytest.raises(ValueError, match="ISO date"):
        Inventory.from_dict(
            {
                "hardwood": [
                    dict(
                        species="cherry", thickness_quarter="4/4",
                        rough_thickness_in=1.0, surfaced_thickness_in=0.75,
                        typical_width_in=7, lengths_ft=[8], price_per_bf=12.5,
                        price_as_of="soon",
                    )
                ]
            }
        )


def test_dimensional_stock_can_carry_a_price(inv):
    """It had no price field at all, so a softwood plan could never be costed."""
    stock = Inventory.from_dict(
        {
            "dimensional": [
                dict(
                    species="pine", nominal="2x4", lengths_ft=[8, 10, 12], qty=6,
                    price_per_piece=6.48, price_as_of=datetime.date(2026, 8, 16),
                    price_source="Hammond Lumber, shelf price",
                )
            ]
        }
    ).dimensional[0]
    assert stock.price == pytest.approx(6.48)
    # A price per piece means nothing without the length it buys.
    assert stock.price_unit == "8 ft piece"
    assert stock.price_line(3).amount == pytest.approx(19.44)


def test_an_unpriced_entry_refuses_to_be_multiplied(inv):
    with pytest.raises(ValueError, match="no price"):
        inv.sheet_for("plywood_birch", "3/4").price_line(2)


def test_stock_labels_distinguish_the_two_baltic_birch_sizes(inv):
    labels = {s.stock_label for s in inv.sheets_for("plywood_baltic_birch", "3/4")}
    assert labels == {
        'plywood_baltic_birch 3/4 (60" x 60")',
        'plywood_baltic_birch 3/4 (48" x 96")',
    }


# ---------------------------------------------------------------------------
# Finding the one dimensional entry a part buys
# ---------------------------------------------------------------------------


def test_dimensional_for_finds_the_entry_a_part_is_specified_in(inv):
    stock = inv.dimensional_for(
        "white_cedar", "1x6", grade="STK", profile="rough sawn"
    )
    assert stock.stock_label == "white_cedar 1x6 rough sawn (STK)"
    assert stock.price == pytest.approx(2.30)


def test_dimensional_for_refuses_to_pick_between_two_grades(inv):
    """Eight entries answer to "cedar 1x6" and they span $1.30 to $3.75."""
    with pytest.raises(KeyError, match="ambiguous"):
        inv.dimensional_for("white_cedar", "1x6")


def test_dimensional_for_names_what_is_stocked_when_nothing_matches(inv):
    with pytest.raises(KeyError) as excinfo:
        inv.dimensional_for("white_cedar", "1x6", grade="FAS", profile="rough sawn")
    message = str(excinfo.value)
    assert "no white_cedar 1x6" in message
    assert "white_cedar 1x6 rough sawn (STK)" in message


def test_dimensional_for_matches_a_size_with_only_one_entry(inv):
    """A grade is only needed where a grade distinguishes something."""
    stock = inv.dimensional_for("white_cedar", "6x6")
    assert stock.nominal == "6x6"
    assert stock.price == pytest.approx(9.45)
