"""Tests for woodshop.pricing — a total may never appear without provenance."""

from __future__ import annotations

from datetime import date

import pytest

from woodshop.cutlist.extract import CutPart
from woodshop.cutlist.hardwood import nest_hardwood
from woodshop.cutlist.optimize_2d import pack_by_material
from woodshop.inventory import Inventory
from woodshop.pricing import (
    UNVERIFIED_MARKER,
    CostSummary,
    PriceLine,
    sheet_cost_summary,
    sheet_for_key,
)

_DATED = PriceLine(
    "cherry 4/4", 46.7, "bd ft", 12.50, as_of=date(2026, 8, 16),
    source="O'Brien Hardwoods, phone quote", source_url="https://obrienhardwoods.com/",
)
_UNDATED = PriceLine("cherry 8/4", 10.0, "bd ft", 15.00, source="PLACEHOLDER")


def _inventory(**overrides) -> Inventory:
    """Return an inventory with one priced and one unpriced entry of each kind."""
    hardwood = [
        dict(
            species="cherry", thickness_quarter="4/4", rough_thickness_in=1.0,
            surfaced_thickness_in=0.75, typical_width_in=7, lengths_ft=[8],
            price_per_bf=12.50, price_as_of=date(2026, 8, 16),
            price_source="O'Brien Hardwoods, phone quote",
        ),
        dict(
            species="cherry", thickness_quarter="8/4", rough_thickness_in=2.0,
            surfaced_thickness_in=1.75, typical_width_in=6, lengths_ft=[8],
        ),
    ]
    sheet_goods = [
        dict(
            material="plywood_birch", nominal_thickness="3/4",
            actual_thickness_in=0.71875, sheet_width_in=48, sheet_height_in=96,
            price_per_sheet=90.0, price_as_of=date(2026, 8, 16),
            price_source="Home Depot shelf tag",
        ),
        dict(
            material="plywood_cherry", nominal_thickness="3/4",
            actual_thickness_in=0.703125, sheet_width_in=48, sheet_height_in=96,
            grain="length",
        ),
    ]
    return Inventory.from_dict(
        {"hardwood": hardwood, "sheet_goods": sheet_goods, **overrides}
    )


# ---------------------------------------------------------------------------
# A line, and the amount it is allowed to print
# ---------------------------------------------------------------------------


def test_an_undated_line_says_so_every_time_it_is_rendered():
    assert _UNDATED.to_text() == "$150 (unverified)"
    assert "unverified" in _UNDATED.rate_text()
    assert not _UNDATED.verified


def test_a_dated_line_carries_its_date():
    assert _DATED.to_text() == "$584 (as of 2026-08-16)"
    assert _DATED.rate_text() == "$12.50/bd ft, as of 2026-08-16"
    assert _DATED.verified


# ---------------------------------------------------------------------------
# A summary: partial totals name what they leave out
# ---------------------------------------------------------------------------


def test_a_total_from_an_undated_price_is_marked_unverified():
    summary = CostSummary.of([_UNDATED])
    assert summary.total == pytest.approx(150.0)
    assert UNVERIFIED_MARKER in summary.to_text()
    assert not summary.verified


def test_a_total_from_dated_prices_quotes_the_oldest_date():
    older = PriceLine("cherry 8/4", 10.0, "bd ft", 15.0, as_of=date(2026, 1, 2))
    summary = CostSummary.of([_DATED, older])
    assert summary.verified
    assert summary.oldest_as_of == date(2026, 1, 2)
    assert "prices as of 2026-01-02" in summary.to_text()


def test_one_undated_price_taints_the_whole_total():
    """A total is only as verified as its worst ingredient."""
    summary = CostSummary.of([_DATED, _UNDATED])
    assert not summary.verified
    assert summary.oldest_as_of is None
    assert UNVERIFIED_MARKER in summary.to_text()


def test_a_partial_total_names_the_material_it_excludes():
    summary = CostSummary.of([_DATED], ["plywood_birch 3/4"])
    assert not summary.complete
    assert "excludes unpriced plywood_birch 3/4" in summary.to_text()
    assert ", partial" in summary.to_label()


def test_nothing_priced_is_an_explanation_rather_than_a_zero():
    summary = CostSummary.of([], ["plywood_birch 3/4"])
    assert summary.total is None
    assert summary.to_text() == "no priced stock — plywood_birch 3/4 unpriced"
    assert summary.to_label() == "unpriced"
    assert CostSummary().to_text() == "nothing to price"


def test_summaries_merge_keeping_every_line_and_every_gap():
    merged = CostSummary.of([_DATED], ["a"]) + CostSummary.of([_UNDATED], ["b"])
    assert merged.total == pytest.approx(_DATED.amount + _UNDATED.amount)
    assert merged.unpriced == ("a", "b")


# ---------------------------------------------------------------------------
# Plans price themselves through the same machinery
# ---------------------------------------------------------------------------


def test_a_hardwood_plan_totals_what_it_can_and_names_what_it_cannot():
    """Regression: a single unpriced group used to drop the cost to None."""
    inv = _inventory()
    parts = [
        CutPart("slat", "cherry", "length", 1000.0, 63.5, 19.05, qty=4),
        CutPart("post", "cherry", "length", 1000.0, 63.5, 44.45),
    ]
    plan = nest_hardwood(parts, inv, "cherry")
    summary = plan.cost_summary

    assert [line.label for line in summary.lines] == ["cherry 4/4"]
    assert summary.unpriced == ("cherry 8/4",)
    assert plan.cost == pytest.approx(summary.total)
    assert plan.cost is not None


def test_the_plan_text_never_prints_a_bare_total():
    inv = _inventory()
    parts = [CutPart("slat", "cherry", "length", 1000.0, 63.5, 19.05, qty=4)]
    text = nest_hardwood(parts, inv, "cherry").to_text()
    for line in text.splitlines():
        if "$" in line:
            assert "as of 2026-08-16" in line or UNVERIFIED_MARKER in line


def test_an_unpriced_group_is_called_out_in_the_plan_text():
    inv = _inventory()
    parts = [CutPart("post", "cherry", "length", 1000.0, 63.5, 44.45)]
    text = nest_hardwood(parts, inv, "cherry").to_text()
    assert "cherry 8/4 has no price" in text
    assert "not free" in text


def test_sheets_are_priced_by_the_sheet_and_keyed_as_the_packer_keys_them():
    inv = _inventory()
    parts = [
        CutPart("shelf", "plywood_birch", "length", 600.0, 300.0, 18.25, qty=3),
        CutPart("back", "plywood_cherry", "length", 600.0, 300.0, 17.86),
    ]
    results = pack_by_material(parts, inv)
    summary = sheet_cost_summary(results, inv)

    assert [line.unit for line in summary.lines] == ["sheet"]
    assert summary.lines[0].label.startswith("plywood_birch 3/4")
    assert summary.lines[0].amount == pytest.approx(90.0)
    assert any(u.startswith("plywood_cherry") for u in summary.unpriced)


def test_a_key_that_names_no_stocked_sheet_returns_nothing():
    assert sheet_for_key(_inventory(), 'plywood_unobtanium 3/4 (48" x 96")') is None
