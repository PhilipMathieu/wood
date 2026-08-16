"""Tests for woodshop.lumber — unit conversion and fractional-inch formatting."""

from __future__ import annotations

import pytest

from woodshop.lumber import (
    KERF_MM,
    actual_dimensions_mm,
    mm_to_fractional_inch,
    plywood_thickness_mm,
)


class TestActualDimensions:
    """Tests for actual_dimensions_mm."""

    def test_2x4(self) -> None:
        t, w = actual_dimensions_mm("2x4")
        assert abs(float(t.to("inch").magnitude) - 1.5) < 0.001
        assert abs(float(w.to("inch").magnitude) - 3.5) < 0.001

    def test_1x6(self) -> None:
        t, w = actual_dimensions_mm("1x6")
        assert abs(float(t.to("inch").magnitude) - 0.75) < 0.001
        assert abs(float(w.to("inch").magnitude) - 5.5) < 0.001

    def test_unknown_raises(self) -> None:
        with pytest.raises(KeyError):
            actual_dimensions_mm("3x5")


class TestPlywoodThickness:
    """Tests for plywood_thickness_mm."""

    def test_three_quarter(self) -> None:
        q = plywood_thickness_mm("3/4")
        assert abs(float(q.to("inch").magnitude) - 0.71875) < 0.001

    def test_half(self) -> None:
        q = plywood_thickness_mm("1/2")
        assert abs(float(q.to("inch").magnitude) - 0.46875) < 0.001


class TestMmToFractionalInch:
    """Tests for mm_to_fractional_inch."""

    def test_whole_inch(self) -> None:
        assert mm_to_fractional_inch(25.4) == '1"'

    def test_quarter_inch(self) -> None:
        assert mm_to_fractional_inch(25.4 * 0.25) == '1/4"'

    def test_compound(self) -> None:
        # 3.25 inches = 82.55 mm
        result = mm_to_fractional_inch(25.4 * 3.25)
        assert result == '3-1/4"'

    def test_zero(self) -> None:
        assert mm_to_fractional_inch(0.0) == '0"'


def test_kerf_constant() -> None:
    """Kerf should be 1/8 inch = 3.175 mm."""
    assert abs(KERF_MM - 3.175) < 0.001
