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
