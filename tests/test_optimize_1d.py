"""Tests for 1-D cutting-stock optimiser."""

from __future__ import annotations

import pytest

from woodshop.cutlist.extract import CutPart
from woodshop.cutlist.optimize_1d import optimize_1d


def _make_parts(label: str, length_mm: float, qty: int = 1) -> list[CutPart]:
    return [CutPart(label, "pine", "length", length_mm, 38.1, 88.9, qty=qty)]


def test_single_cut_fits_one_stock() -> None:
    parts = _make_parts("leg", 800.0, qty=1)
    result = optimize_1d(parts, stock_lengths_mm=[2438.4])
    assert result.stock_used == 1


def test_four_legs_two_stocks() -> None:
    # Four 900 mm legs on 8-ft (2438.4 mm) stock: two fit per board.
    parts = _make_parts("leg", 900.0, qty=4)
    result = optimize_1d(parts, stock_lengths_mm=[2438.4])
    assert result.stock_used == 2


def test_empty_parts() -> None:
    result = optimize_1d([], stock_lengths_mm=[2438.4])
    assert result.stock_used == 0
    assert result.assignments == []


# ---------------------------------------------------------------------------
# Cross-section grouping and stock-length choice
# ---------------------------------------------------------------------------


def test_different_sections_never_share_a_board():
    """Regression: a 2x4 cut and a 1x6 cut used to be binned onto one board."""
    parts = [
        CutPart("stud", "pine", "length", 600.0, 88.9, 38.1),
        CutPart("shelf", "pine", "length", 600.0, 139.7, 19.05),
    ]
    result = optimize_1d(parts, stock_lengths_mm=[2438.4])
    assert result.stock_used == 2
    assert len({p.section for p in result.pieces}) == 2


def test_same_section_shares_a_board():
    parts = [CutPart("stud", "pine", "length", 600.0, 88.9, 38.1, qty=2)]
    assert optimize_1d(parts, stock_lengths_mm=[2438.4]).stock_used == 1


def test_shorter_stock_is_chosen_when_it_wastes_less():
    """Three 900 mm rails: two 6 ft boards beat two 8 ft boards."""
    parts = [CutPart("rail", "pine", "length", 900.0, 88.9, 38.1, qty=3)]
    result = optimize_1d(parts, stock_lengths_mm=[1828.8, 2438.4])
    assert result.total_length_mm == pytest.approx(2 * 1828.8)


def test_more_short_boards_can_beat_fewer_long_ones():
    """Regression: bounding bins on the longest stock cut this solution off.

    Four 900 mm legs: four 1000 mm boards waste 400 mm in total, while two
    2438.4 mm boards waste 876.8 mm.  Bounding the bin count by a greedy pass
    on the longest stock alone caps the search at two bins and hides it.
    """
    parts = [CutPart("leg", "pine", "length", 900.0, 88.9, 38.1, qty=4)]
    result = optimize_1d(parts, stock_lengths_mm=[1000.0, 2438.4])
    assert result.stock_used == 4
    assert result.total_length_mm == pytest.approx(4 * 1000.0)


def test_pieces_objective_minimises_board_count():
    parts = [CutPart("leg", "pine", "length", 900.0, 88.9, 38.1, qty=4)]
    result = optimize_1d(parts, stock_lengths_mm=[1000.0, 2438.4], objective="pieces")
    assert result.stock_used == 2


def test_kerf_is_charged_between_cuts():
    # Two cuts that sum to exactly the stock length cannot share a board once
    # the saw takes its 1/8".
    parts = [CutPart("x", "pine", "length", 1219.2, 88.9, 38.1, qty=2)]
    assert optimize_1d(parts, stock_lengths_mm=[2438.4]).stock_used == 2


def test_part_longer_than_stock_raises():
    parts = [CutPart("beam", "pine", "length", 3000.0, 88.9, 38.1)]
    with pytest.raises(ValueError, match="longer than the longest"):
        optimize_1d(parts, stock_lengths_mm=[2438.4])


def test_empty_stock_lengths_raises():
    parts = [CutPart("x", "pine", "length", 600.0, 88.9, 38.1)]
    with pytest.raises(ValueError, match="stock_lengths_mm is empty"):
        optimize_1d(parts, stock_lengths_mm=[])


def test_unknown_objective_raises():
    with pytest.raises(ValueError, match="objective"):
        optimize_1d(_make_parts("x", 600.0), stock_lengths_mm=[2438.4],
                    objective="cheapest")


def test_yield_and_waste_are_consistent():
    parts = [CutPart("x", "pine", "length", 600.0, 88.9, 38.1, qty=4)]
    result = optimize_1d(parts, stock_lengths_mm=[2438.4])
    assert result.total_waste_mm == pytest.approx(sum(result.waste_mm))
    assert 0.0 < result.yield_fraction < 1.0
