"""Tests for woodshop.cutlist.hardwood — nesting parts on random-width boards."""

from __future__ import annotations

import math

import pytest

from woodshop.cutlist.extract import CutPart
from woodshop.cutlist.hardwood import nest_hardwood, stave_wide_parts
from woodshop.inventory import Inventory

_IN = 25.4


@pytest.fixture(scope="module")
def inv() -> Inventory:
    return Inventory.load()


def test_slats_are_ripped_from_shared_boards(inv):
    """Regression: 1-D binning bought one 8 ft board per 2-1/2" slat."""
    slats = [
        CutPart("slat", "cherry", "length", 62.5 * _IN, 2.5 * _IN, 0.75 * _IN, qty=16)
    ]
    plan = nest_hardwood(slats, inv, "cherry")
    # A 7" board takes two slats side by side, and an 8 ft board takes one
    # 62-1/2" length, so 16 slats is 8 boards — not 16.
    assert plan.boards_needed == 8
    assert plan.board_feet == pytest.approx(37.3, abs=0.5)


def test_cost_uses_board_feet(inv):
    parts = [CutPart("x", "cherry", "length", 1000.0, 100.0, 19.05, qty=4)]
    plan = nest_hardwood(parts, inv, "cherry")
    assert plan.cost == pytest.approx(plan.board_feet * 12.50, rel=1e-6)


def test_parts_are_grouped_by_quarter_thickness(inv):
    parts = [
        CutPart("post", "cherry", "length", 1000.0, 44.45, 44.45),
        CutPart("rail", "cherry", "length", 1000.0, 100.0, 25.4),
        CutPart("slat", "cherry", "length", 1000.0, 63.5, 19.05),
    ]
    plan = nest_hardwood(parts, inv, "cherry")
    assert {g.stock.thickness_quarter for g in plan.groups} == {"4/4", "5/4", "8/4"}


def test_thinnest_usable_stock_is_chosen(inv):
    """A 3/4" part comes from 4/4, not from 8/4."""
    parts = [CutPart("slat", "cherry", "length", 1000.0, 63.5, 19.05)]
    plan = nest_hardwood(parts, inv, "cherry")
    assert [g.stock.thickness_quarter for g in plan.groups] == ["4/4"]


def test_part_thicker_than_any_stock_is_reported(inv):
    parts = [CutPart("beam", "cherry", "length", 1000.0, 100.0, 100.0)]
    plan = nest_hardwood(parts, inv, "cherry")
    assert [p.label for p in plan.unmatched] == ["beam"]


def test_other_species_are_ignored(inv):
    parts = [CutPart("stud", "pine", "length", 1000.0, 88.9, 38.1)]
    assert nest_hardwood(parts, inv, "cherry").boards_needed == 0


def test_unknown_species_raises(inv):
    with pytest.raises(KeyError, match="stock.yaml has"):
        nest_hardwood([], inv, "unobtanium")


# ---------------------------------------------------------------------------
# Glue-ups
# ---------------------------------------------------------------------------


def test_wide_panel_is_split_into_staves():
    panel = CutPart("panel", "cherry", "length", 1555.75, 292.1, 19.05)  # 61-1/4 x 11-1/2
    parts, glue_ups = stave_wide_parts([panel], 6.5 * _IN)
    assert [p.label for p in parts] == ["panel_stave"]
    assert parts[0].qty == 2
    assert parts[0].width_mm == pytest.approx(146.05)
    assert glue_ups == [("panel", 2, pytest.approx(146.05))]


def test_narrow_parts_are_left_alone():
    part = CutPart("slat", "cherry", "length", 1000.0, 63.5, 19.05)
    parts, glue_ups = stave_wide_parts([part], 6.5 * _IN)
    assert parts == [part]
    assert glue_ups == []


def test_glue_up_is_reported_rather_than_unpackable(inv):
    """Regression: an 11-1/2" panel used to fail to nest on a 7" board."""
    panel = CutPart("headboard_panel", "cherry", "length", 1555.75, 292.1, 19.05)
    plan = nest_hardwood([panel], inv, "cherry")
    assert plan.boards_needed >= 1
    assert not any(g.nesting.unpacked for g in plan.groups)
    assert plan.glue_ups[0][0] == "headboard_panel"


def test_nesting_respects_the_jointing_allowance(inv):
    """Regression: parts were nested across width the jointer removes.

    Both edges of a rough board must be jointed straight before anything is
    ripped from it, so the usable width is narrower than the width billed.
    """
    from woodshop.cutlist.hardwood import JOINTING_ALLOWANCE_MM

    parts = [CutPart("rail", "cherry", "length", 600.0, 85.0, 19.05, qty=8)]
    group = nest_hardwood(parts, inv, "cherry").groups[0]
    usable = group.stock.typical_width_in * _IN - JOINTING_ALLOWANCE_MM
    assert max(p.x_mm + p.width_mm for p in group.nesting.placements) <= usable


def test_board_feet_still_bill_the_full_width(inv):
    """Jointing narrows what you can use, not what you pay for."""
    parts = [CutPart("rail", "cherry", "length", 600.0, 85.0, 19.05, qty=8)]
    group = nest_hardwood(parts, inv, "cherry").groups[0]
    expected = (
        group.boards_needed
        * group.stock.typical_width_in
        * (group.board_length_mm / _IN)
        * group.stock.rough_thickness_in
        / 144.0
    )
    assert group.board_feet == pytest.approx(expected)


def test_stock_with_no_lengths_names_the_offending_row():
    inv = Inventory.from_dict(
        {
            "hardwood": [
                {
                    "species": "cherry", "thickness_quarter": "4/4",
                    "rough_thickness_in": 1.0, "surfaced_thickness_in": 0.75,
                    "typical_width_in": 7, "lengths_ft": [],
                }
            ]
        }
    )
    with pytest.raises(ValueError, match="cherry 4/4: no lengths_ft"):
        nest_hardwood([CutPart("x", "cherry", "length", 600.0, 50.0, 19.05)],
                      inv, "cherry")


# ---------------------------------------------------------------------------
# Round and turned parts
# ---------------------------------------------------------------------------


def test_a_round_part_nests_as_its_square_blank(inv):
    """Correct for buying. The circle only shows up in the yield."""
    top = CutPart(
        "top", "cherry", "length", 4.5 * _IN, 4.5 * _IN, 38.1,
        shape="round", finished_area_each_mm2=math.pi * (4.5 * _IN) ** 2 / 4,
    )
    plan = nest_hardwood([top], inv, "cherry")
    assert plan.boards_needed == 1
    assert plan.finished_yield_fraction < plan.yield_fraction
    assert plan.finished_yield_fraction / plan.yield_fraction == pytest.approx(
        math.pi / 4, abs=0.001
    )


def test_all_rectangles_means_the_two_yields_agree(inv):
    parts = [CutPart("rail", "cherry", "length", 600.0, 85.0, 19.05, qty=8)]
    plan = nest_hardwood(parts, inv, "cherry")
    assert plan.finished_yield_fraction == pytest.approx(plan.yield_fraction)


def test_a_staved_round_top_keeps_its_share_of_the_shavings(inv):
    """Regression: staving a disc turned it into rectangles and hid the waste."""
    finished = math.pi * (18 * _IN) ** 2 / 4
    top = CutPart(
        "top", "cherry", "length", 18.25 * _IN, 18.25 * _IN, 38.1,
        shape="round", finished_area_each_mm2=finished,
    )
    plan = nest_hardwood([top], inv, "cherry")
    assert plan.glue_ups and plan.glue_ups[0][0] == "top"
    total_finished = sum(g.nesting.finished_area_mm2 for g in plan.groups)
    assert total_finished == pytest.approx(finished, rel=1e-6)


def test_group_yields_are_billed_against_the_width_you_buy(inv):
    """Regression: two different yields for one board on one page.

    The nesting runs on the post-jointing width, so its own yield_fraction
    divides by a narrower board than the one you paid for.
    """
    parts = [CutPart("rail", "cherry", "length", 600.0, 85.0, 19.05, qty=8)]
    plan = nest_hardwood(parts, inv, "cherry")
    group = plan.groups[0]
    assert group.yield_fraction == pytest.approx(plan.yield_fraction)
    assert group.yield_fraction < group.nesting.yield_fraction
