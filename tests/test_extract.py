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
