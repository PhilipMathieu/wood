"""Tests for buying dimensional stock by the lineal foot.

The question this module answers is the one a published price list leaves
open: the guide quotes cedar per lineal foot and lists no lengths, so a design
can be *bought* and cannot be *cut* from it.  These tests pin both halves —
the footage is real, and the silence about lengths stays visible.
"""

from __future__ import annotations

import datetime

import pytest

from woodshop.cutlist.dimensional import (
    OFFCUT_ALLOWANCE,
    LinealPlan,
    StockGroup,
    plan_dimensional,
)
from woodshop.cutlist.extract import CutPart
from woodshop.inventory import DimensionalStock, Inventory


@pytest.fixture(scope="module")
def inv() -> Inventory:
    return Inventory.load()


def picket(qty: int = 60, **kwargs) -> CutPart:
    """Return a rough sawn cedar board, 46" long, as the fence cuts them."""
    defaults = dict(
        nominal="1x6", grade="STK", stock_profile="rough sawn"
    )
    defaults.update(kwargs)
    return CutPart(
        "picket", "white_cedar", "length", 1168.4, 152.4, 25.4, qty=qty, **defaults
    )


# ---------------------------------------------------------------------------
# Matching a part to the entry it actually buys
# ---------------------------------------------------------------------------


def test_a_part_that_names_its_grade_lands_on_that_entry(inv):
    plan = plan_dimensional([picket()], inv)
    assert [g.label for g in plan.groups] == ["white_cedar 1x6 rough sawn (STK)"]
    assert plan.groups[0].stock.price == pytest.approx(2.30)


def test_the_same_board_in_low_grade_is_a_different_price(inv):
    stk = plan_dimensional([picket()], inv).cost
    low = plan_dimensional([picket(grade="low")], inv).cost
    assert low < stk
    # The gap between two entries under one nominal size is most of what a
    # fence costs, which is why grade is part of the match and not a comment.
    assert stk / low == pytest.approx(2.30 / 1.30, rel=1e-6)


def test_a_part_with_no_grade_is_unmatched_rather_than_guessed(inv):
    plan = plan_dimensional([picket(grade="", stock_profile="")], inv)
    assert not plan.groups
    assert len(plan.unmatched) == 1
    part, reason = plan.unmatched[0]
    assert part.label == "picket"
    assert "ambiguous" in reason


def test_a_part_with_no_nominal_size_is_unmatched(inv):
    milled = CutPart("rail", "white_cedar", "length", 1000.0, 100.0, 25.0)
    plan = plan_dimensional([milled], inv)
    assert plan.groups == []
    assert "nominal size" in plan.unmatched[0][1]


def test_a_species_that_is_not_stocked_is_named_not_dropped(inv):
    part = picket()
    part.material = "ipe"
    plan = plan_dimensional([part], inv)
    assert plan.groups == []
    assert "ipe" in plan.unmatched[0][1]


def test_parts_of_the_same_stock_share_a_group(inv):
    plan = plan_dimensional([picket(qty=10), picket(qty=5)], inv)
    assert len(plan.groups) == 1
    assert plan.groups[0].measured_ft == pytest.approx(15 * 46 / 12, rel=1e-6)


# ---------------------------------------------------------------------------
# Footage and money
# ---------------------------------------------------------------------------


def test_footage_is_the_cut_length_plus_a_stated_allowance(inv):
    plan = plan_dimensional([picket(qty=12)], inv)
    group = plan.groups[0]
    assert group.measured_ft == pytest.approx(12 * 46 / 12, rel=1e-6)
    assert group.lineal_ft == pytest.approx(group.measured_ft * (1 + OFFCUT_ALLOWANCE))
    assert group.allowance == OFFCUT_ALLOWANCE


def test_the_allowance_can_be_turned_off(inv):
    plan = plan_dimensional([picket(qty=12)], inv, allowance=0.0)
    assert plan.groups[0].lineal_ft == pytest.approx(plan.groups[0].measured_ft)


def test_a_negative_allowance_is_refused(inv):
    with pytest.raises(ValueError, match="non-negative"):
        plan_dimensional([picket()], inv, allowance=-0.1)


def test_the_total_carries_the_date_its_rates_were_true(inv):
    summary = plan_dimensional([picket(qty=60)], inv).cost_summary
    assert summary.verified
    assert summary.oldest_as_of == datetime.date(2026, 8, 17)
    assert "as of 2026-08-17" in summary.to_text()


def test_the_cost_is_feet_times_the_published_rate(inv):
    plan = plan_dimensional([picket(qty=12)], inv)
    assert plan.cost == pytest.approx(plan.lineal_ft * 2.30)


def test_an_unpriced_entry_is_named_rather_than_costed_at_zero():
    stock = DimensionalStock(
        species="white_cedar", nominal="1x6", lengths_ft=[], grade="STK",
        profile="rough sawn",
    )
    plan = LinealPlan(groups=[StockGroup(stock=stock, parts=[picket()])])
    assert plan.groups[0].price_line is None
    assert plan.cost is None
    assert "unpriced" in plan.cost_summary.to_text()
    assert "not free" in plan.to_text()


def test_stock_used_names_only_what_the_design_buys(inv):
    plan = plan_dimensional([picket()], inv)
    labels = [s.stock_label for s in plan.stock_used]
    assert labels == ["white_cedar 1x6 rough sawn (STK)"]
    # There are far more cedar entries than the one this design touches.
    assert len([d for d in inv.dimensional if d.species == "white_cedar"]) > 20


# ---------------------------------------------------------------------------
# Per-piece pricing, which is a different unit and not a converted one
# ---------------------------------------------------------------------------


def test_stock_priced_by_the_piece_is_bought_in_pieces():
    stock = DimensionalStock(
        species="white_cedar", nominal="1x4", lengths_ft=[2], grade="STK",
        profile="dressed cutoff", price_per_piece=1.00, price_length_ft=2,
        price_as_of=datetime.date(2026, 8, 17),
    )
    part = CutPart(
        "block", "white_cedar", "length", 304.8, 88.9, 19.05, qty=9,
        nominal="1x4", grade="STK", stock_profile="dressed cutoff",
    )
    group = StockGroup(stock=stock, parts=[part], allowance=0.0)
    # Nine one-foot blocks is 9 LF, and a 2 ft cutoff yields two of them.
    assert group.lineal_ft == pytest.approx(9.0)
    assert group.pieces == 5
    assert group.quantity == 5
    assert group.price_line.amount == pytest.approx(5.0)


def test_stock_priced_by_the_foot_reports_no_piece_count(inv):
    group = plan_dimensional([picket()], inv).groups[0]
    assert group.pieces is None
    assert group.quantity == pytest.approx(group.lineal_ft)


# ---------------------------------------------------------------------------
# What the plan says out loud
# ---------------------------------------------------------------------------


def test_the_text_names_the_entry_the_footage_and_the_provenance(inv):
    text = plan_dimensional([picket(qty=60)], inv).to_text()
    assert "white_cedar 1x6 rough sawn (STK)" in text
    assert "LF" in text
    assert "offcuts" in text
    assert "as of 2026-08-17" in text


def test_unmatched_parts_appear_in_the_text(inv):
    text = plan_dimensional([picket(grade="", stock_profile="")], inv).to_text()
    assert "(!) picket" in text


def test_board_feet_is_available_for_comparison_with_hardwood(inv):
    # One 46" x 6" x 1" board is 46 * 6 * 1 / 144 board feet.
    plan = plan_dimensional([picket(qty=1)], inv)
    assert plan.board_feet == pytest.approx(46 * 6 / 144, rel=1e-3)
