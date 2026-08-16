"""Tests for 2-D sheet-goods packing optimiser."""

from __future__ import annotations

from woodshop.cutlist.extract import CutPart
from woodshop.cutlist.optimize_2d import optimize_2d


SHEET_W = 1219.2   # 48"
SHEET_H = 2438.4   # 96"


def _panel(label: str, length: float, width: float, qty: int = 1) -> CutPart:
    return CutPart(label, "plywood_birch", "length", length, width, 18.25, qty=qty)


def test_small_panels_one_sheet() -> None:
    panels = [_panel("shelf", 300.0, 200.0, qty=4)]
    result = optimize_2d(panels, sheet_w_mm=SHEET_W, sheet_h_mm=SHEET_H)
    assert result.sheets_used == 1
    assert len(result.unpacked) == 0


def test_empty_parts() -> None:
    result = optimize_2d([], sheet_w_mm=SHEET_W, sheet_h_mm=SHEET_H)
    assert result.sheets_used == 0
    assert result.placements == []
