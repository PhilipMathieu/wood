"""Tests for woodshop.parts — Board, Panel, and metadata survival."""

from __future__ import annotations

import math

import pytest
from build123d import Compound, Rotation

from woodshop.cutlist.extract import extract
from woodshop.parts import (
    ROUND_BLANK_MARGIN_MM,
    TURNING_WASTE_MM,
    Board,
    Disc,
    Panel,
    Turning,
    retag,
    total_board_feet,
)


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


# ---------------------------------------------------------------------------
# Round and turned parts — blank versus finished
# ---------------------------------------------------------------------------


def test_disc_blank_is_a_square_larger_than_the_circle():
    top = Disc(
        diameter_mm=18 * 25.4, thickness_mm=1.5 * 25.4,
        material="cherry", label="top",
    )
    assert top.length_mm == pytest.approx(18 * 25.4)
    assert top.stock_length_mm == pytest.approx(18 * 25.4 + ROUND_BLANK_MARGIN_MM)
    assert top.stock_width_mm == top.stock_length_mm
    assert top.stock_thickness_mm == pytest.approx(1.5 * 25.4)


def test_disc_shape_yield_is_pi_over_four_less_the_margin():
    top = Disc(diameter_mm=400.0, thickness_mm=25.0, material="cherry", label="t")
    # A circle in its own bounding square is pi/4; the blank is bigger still.
    assert top.shape_yield < math.pi / 4
    assert top.shape_yield == pytest.approx(0.76, abs=0.01)


def test_disc_edge_can_be_angled_inward():
    top = Disc(
        diameter_mm=457.2, thickness_mm=38.1, bottom_diameter_mm=431.8,
        material="cherry", label="top",
    )
    bb = top.bounding_box()
    assert bb.size.X == pytest.approx(457.2)
    assert bb.size.Z == pytest.approx(38.1)
    assert "tapering to 17\"" in top.profile


def test_a_straight_edged_disc_is_a_cylinder_not_a_degenerate_cone():
    """Open Cascade refuses a cone with two equal radii; the class must not."""
    top = Disc(diameter_mm=400.0, thickness_mm=25.0, material="cherry", label="t")
    assert top.bounding_box().size.X == pytest.approx(400.0)


def test_turning_blank_is_square_and_longer_than_the_spindle():
    leg = Turning(
        length_mm=546.1, diameter_mm=25.4, end_diameter_mm=38.1,
        material="cherry", label="leg",
    )
    assert leg.stock_width_mm == pytest.approx(38.1 + ROUND_BLANK_MARGIN_MM)
    assert leg.stock_thickness_mm == leg.stock_width_mm
    assert leg.stock_length_mm == pytest.approx(546.1 + TURNING_WASTE_MM)


def test_turning_profile_names_both_diameters():
    leg = Turning(
        length_mm=500.0, diameter_mm=25.4, end_diameter_mm=38.1,
        material="cherry", label="leg",
    )
    assert leg.profile == 'turned, 1-1/2" tapering to 1"'


def test_a_parallel_turning_is_described_as_one_diameter():
    knob = Turning(length_mm=50.0, diameter_mm=25.4, material="cherry", label="knob")
    assert knob.profile == 'turned, 1" dia.'


def test_shaped_parts_reject_a_zero_length():
    with pytest.raises(ValueError, match="length must be positive"):
        Turning(length_mm=0.0, diameter_mm=25.4, material="cherry", label="bad")


def test_board_feet_bill_the_blank_not_the_finished_part():
    """You buy the square, not the circle."""
    top = Disc(diameter_mm=304.8, thickness_mm=25.4, material="cherry", label="t")
    blank_side = 304.8 + ROUND_BLANK_MARGIN_MM
    assert top.board_feet == pytest.approx(blank_side**2 * 25.4 / 25.4**3 / 144.0)


def test_extract_reports_the_blank_for_shaped_parts():
    top = Disc(
        diameter_mm=18 * 25.4, thickness_mm=1.5 * 25.4,
        material="cherry", label="top",
    )
    part = extract(Compound(children=[top]))[0]
    assert part.shape == "round"
    assert part.length_mm == pytest.approx(18 * 25.4 + ROUND_BLANK_MARGIN_MM)
    assert part.finished_area_mm2 < part.blank_area_mm2
    assert "round" in part.profile


# ---------------------------------------------------------------------------
# retag — metadata across a boolean
# ---------------------------------------------------------------------------


def test_a_boolean_cut_loses_the_cut_list_without_retag():
    """The bug retag exists for: the part silently leaves the cut list."""
    from build123d import Box, Pos

    rail = Board(
        length_mm=600.0, thickness_mm=25.0, width_mm=100.0,
        material="cherry", label="rail",
    )
    mortised = rail - Pos(0, 0, 0) * Box(20, 20, 40)
    assert extract(Compound(children=[mortised])) == []


def test_retag_puts_the_part_back_on_the_cut_list():
    from build123d import Box, Pos

    rail = Board(
        length_mm=600.0, thickness_mm=25.0, width_mm=100.0,
        material="cherry", label="rail",
    )
    mortised = retag(rail - Pos(0, 0, 0) * Box(20, 20, 40), like=rail)
    part = extract(Compound(children=[mortised]))[0]
    assert part.label == "rail"
    assert part.length_mm == pytest.approx(600.0)
    assert part.width_mm == pytest.approx(100.0)


def test_retag_can_override_a_field():
    rail = Board(
        length_mm=600.0, thickness_mm=25.0, width_mm=100.0,
        material="cherry", label="rail",
    )
    other = Board(
        length_mm=10.0, thickness_mm=10.0, width_mm=10.0,
        material="pine", label="scrap",
    )
    retag(other, like=rail, notes="mortised")
    assert other.label == "rail"
    assert other.notes == "mortised"
