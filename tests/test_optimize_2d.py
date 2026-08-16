"""Tests for 2-D sheet-goods packing optimiser."""

from __future__ import annotations

import pytest

from woodshop.cutlist.extract import CutPart
from woodshop.cutlist.optimize_2d import optimize_2d, pack_by_material
from woodshop.inventory import Inventory

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


# ---------------------------------------------------------------------------
# Grain locking
# ---------------------------------------------------------------------------

_IN = 25.4


def test_grained_part_is_laid_along_the_sheet_grain():
    """A part whose grain runs along its length must run along the 96" axis."""
    panel = CutPart("panel", "plywood_cherry", "length", 61.25 * _IN, 11.5 * _IN, 17.86)
    result = optimize_2d(panel_list := [panel], sheet_w_mm=SHEET_W, sheet_h_mm=SHEET_H)
    assert result.unpacked == []
    placed = result.placements[0]
    # Placed height (along the grain) is the part's length, not its width.
    assert placed.height_mm == pytest.approx(61.25 * _IN, abs=0.1)
    assert placed.rotated is True
    assert len(panel_list) == 1


def test_grain_lock_can_make_a_part_unpackable():
    # 60" across a 48"-wide sheet only works if the part may be turned.
    part = CutPart("wide", "plywood_cherry", "width", 60 * _IN, 10 * _IN, 17.86)
    locked = optimize_2d([part], sheet_w_mm=SHEET_W, sheet_h_mm=SHEET_H)
    assert locked.unpacked == ["wide"]

    free = optimize_2d(
        [part], sheet_w_mm=SHEET_W, sheet_h_mm=SHEET_H, respect_grain=False
    )
    assert free.unpacked == []


def test_ungrained_sheet_allows_either_orientation():
    part = CutPart("slat", "plywood_baltic_birch", "none", 55 * _IN, 2.5 * _IN, 18.0)
    result = optimize_2d(
        [part], sheet_w_mm=60 * _IN, sheet_h_mm=60 * _IN, sheet_grain="none"
    )
    assert result.unpacked == []


def test_part_larger_than_the_sheet_is_reported():
    part = CutPart("slat", "plywood_baltic_birch", "none", 62.5 * _IN, 2.5 * _IN, 18.0)
    result = optimize_2d(
        [part], sheet_w_mm=60 * _IN, sheet_h_mm=60 * _IN, sheet_grain="none"
    )
    assert result.unpacked == ["slat"]
    assert result.sheets_used == 0


def test_shelf_layout_is_guillotine_cuttable():
    """Every part in a shelf must share the shelf's bottom edge."""
    parts = [_panel(f"p{i}", 300.0 + 40 * i, 200.0, qty=3) for i in range(5)]
    result = optimize_2d(parts, sheet_w_mm=SHEET_W, sheet_h_mm=SHEET_H)
    by_row: dict[tuple[int, float], list] = {}
    for p in result.placements:
        by_row.setdefault((p.sheet_index, round(p.y_mm, 3)), []).append(p)
    # Parts sharing a y are a strip; strips must not overlap in y.
    for sheet_index in {p.sheet_index for p in result.placements}:
        rows = sorted(
            (y, max(p.y_mm + p.height_mm for p in ps))
            for (s, y), ps in by_row.items()
            if s == sheet_index
        )
        for (_, top), (next_y, _) in zip(rows, rows[1:]):
            assert top <= next_y + 1e-6


def test_yield_fraction_is_sane():
    result = optimize_2d([_panel("p", 600.0, 300.0, qty=4)],
                         sheet_w_mm=SHEET_W, sheet_h_mm=SHEET_H)
    assert 0.0 < result.yield_fraction < 1.0


def test_unknown_strategy_rejected():
    with pytest.raises(ValueError, match="strategy"):
        optimize_2d([_panel("p", 100.0, 100.0)], sheet_w_mm=SHEET_W,
                    sheet_h_mm=SHEET_H, strategy="magic")


def test_pack_by_material_uses_each_material_own_sheet_size():
    inv = Inventory.load()
    parts = [
        CutPart("panel", "plywood_cherry", "length", 61.25 * _IN, 11.5 * _IN, 17.86),
        CutPart("slat", "plywood_baltic_birch", "none", 31.25 * _IN, 2.5 * _IN, 18.0,
                qty=32),
    ]
    results = pack_by_material(parts, inv)
    keys = {k.split(" (")[0]: v for k, v in results.items()}
    assert keys["plywood_cherry 3/4"].sheet_h_mm == pytest.approx(96 * _IN)
    # Short half-slats fit the smaller 5x5 sheet, so that is what gets bought.
    assert keys["plywood_baltic_birch 3/4"].sheet_h_mm == pytest.approx(60 * _IN)


def test_pack_by_material_upgrades_to_the_larger_sheet_when_needed():
    """A 62-1/2" slat forces the 4x8 Baltic birch rather than the 5x5."""
    inv = Inventory.load()
    parts = [
        CutPart("slat", "plywood_baltic_birch", "none", 62.5 * _IN, 2.5 * _IN, 18.0,
                qty=16),
    ]
    result = next(iter(pack_by_material(parts, inv).values()))
    assert result.sheet_h_mm == pytest.approx(96 * _IN)
    assert result.unpacked == []
