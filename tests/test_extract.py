"""Tests for woodshop.cutlist.extract — CutPart and mm_to_fractional_inch."""

from __future__ import annotations

from woodshop.cutlist.extract import CutPart


def test_cut_part_fractional_properties() -> None:
    part = CutPart(
        label="test_leg",
        material="pine",
        grain_direction="length",
        length_mm=812.8,   # 32 inches
        width_mm=88.9,     # 3.5 inches
        thickness_mm=38.1, # 1.5 inches
    )
    assert part.length_in == '32"'
    assert part.width_in == '3-1/2"'
    assert part.thickness_in == '1-1/2"'


def test_cut_part_defaults() -> None:
    part = CutPart(
        label="shelf",
        material="plywood_birch",
        grain_direction="length",
        length_mm=600.0,
        width_mm=300.0,
        thickness_mm=18.25,
    )
    assert part.qty == 1


def test_shape_defaults_to_rectangular() -> None:
    part = CutPart("rail", "cherry", "length", 600.0, 100.0, 25.0)
    assert part.shape == "rectangular"
    assert part.finished_area_mm2 == part.blank_area_mm2


def test_finished_area_counts_quantity() -> None:
    part = CutPart(
        "leg", "cherry", "length", 600.0, 44.0, 44.0, qty=3,
        shape="turned", finished_area_each_mm2=1000.0,
    )
    assert part.finished_area_mm2 == 3000.0


def test_parts_of_different_shape_do_not_consolidate() -> None:
    """A square blank and a disc blank of the same size are not the same row."""
    from woodshop.cutlist.extract import consolidate

    square = CutPart("blank", "cherry", "length", 400.0, 400.0, 25.0)
    disc = CutPart(
        "blank", "cherry", "length", 400.0, 400.0, 25.0,
        shape="round", finished_area_each_mm2=125_664.0,
    )
    merged = consolidate([square, disc])
    assert len(merged) == 2
    assert {p.shape for p in merged} == {"rectangular", "round"}
