"""Tests for woodshop.parts — Board, Panel, and metadata survival."""

from __future__ import annotations

import pytest
from build123d import Compound, Rotation

from woodshop.cutlist.extract import extract
from woodshop.parts import Board, Panel, total_board_feet


def test_board_from_nominal():
    b = Board(length_mm=1000.0, nominal="2x4", material="pine", label="stud")
    assert b.thickness_mm == pytest.approx(38.1)
    assert b.width_mm == pytest.approx(88.9)
    assert b.stock_length_mm == pytest.approx(1000.0)


def test_board_explicit_dimensions():
    b = Board(
        length_mm=500.0, thickness_mm=25.4, width_mm=101.6,
        material="cherry", label="rail",
    )
    assert b.bounding_box().size.X == pytest.approx(500.0)


def test_board_rejects_nominal_and_explicit():
    with pytest.raises(ValueError, match="not both"):
        Board(
            length_mm=500.0, nominal="2x4", thickness_mm=25.4,
            material="pine", label="bad",
        )


def test_board_requires_some_dimensions():
    with pytest.raises(ValueError, match="give nominal"):
        Board(length_mm=500.0, material="pine", label="bad")


def test_panel_requires_exactly_one_thickness():
    with pytest.raises(ValueError, match="exactly one"):
        Panel(
            length_mm=600.0, width_mm=300.0, nominal_thickness="3/4",
            thickness_mm=18.0, material="plywood_birch", label="bad",
        )


def test_panel_metric_thickness_is_kept_exactly():
    p = Panel(
        length_mm=600.0, width_mm=300.0, thickness_mm=18.0,
        material="plywood_baltic_birch", label="slat",
    )
    assert p.thickness_mm == pytest.approx(18.0)


def test_trim_allowance_extends_stock_length():
    b = Board(
        length_mm=1000.0, nominal="1x4", material="pine", label="x",
        trim_allowance_mm=25.4,
    )
    assert b.stock_length_mm == pytest.approx(1025.4)


@pytest.mark.parametrize(
    "kwargs, match",
    [
        ({"length_mm": -1.0}, "must be positive"),
        ({"qty": 0}, "at least 1"),
        ({"grain_direction": "diagonal"}, "grain_direction"),
    ],
)
def test_invalid_arguments_rejected(kwargs, match):
    base = dict(
        length_mm=100.0, thickness_mm=10.0, width_mm=20.0,
        material="pine", label="x",
    )
    base.update(kwargs)
    with pytest.raises(ValueError, match=match):
        Board(**base)


def test_cut_dimensions_survive_rotation_into_an_assembly():
    """Regression: dimensions must come from the part, not its placed bbox."""
    flat = Board(
        length_mm=1000.0, thickness_mm=25.4, width_mm=101.6,
        material="cherry", label="rail",
    )
    on_edge = Rotation(0, 90, 90) * Board(
        length_mm=1000.0, thickness_mm=25.4, width_mm=101.6,
        material="cherry", label="rail",
    )
    parts = extract(Compound(children=[flat, on_edge]))

    assert len(parts) == 1, "identical parts should consolidate"
    assert parts[0].qty == 2
    assert parts[0].width_mm == pytest.approx(101.6)
    assert parts[0].thickness_mm == pytest.approx(25.4)


def test_board_feet_counts_quantity():
    # 1" x 12" x 12" = 1 board foot.
    b = Board(
        length_mm=304.8, thickness_mm=25.4, width_mm=304.8,
        material="cherry", label="x", qty=3,
    )
    assert b.board_feet == pytest.approx(3.0)
    assert total_board_feet([b]) == pytest.approx(3.0)
