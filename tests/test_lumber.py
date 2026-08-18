"""Tests for woodshop.lumber — unit conversion and fractional-inch formatting."""

from __future__ import annotations

import pytest

from woodshop.lumber import (
    KERF_MM,
    actual_dimensions_mm,
    mm_to_fractional_inch,
    plywood_thickness_mm,
    rough_dimensions_mm,
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


class TestRoughDimensions:
    """Tests for rough_dimensions_mm — the table dressed stock is not in."""

    def test_a_rough_1x6_is_a_full_inch_by_six(self) -> None:
        t, w = rough_dimensions_mm("1x6")
        assert float(t.to("inch").magnitude) == pytest.approx(1.0)
        assert float(w.to("inch").magnitude) == pytest.approx(6.0)

    def test_it_disagrees_with_the_dressed_table_on_purpose(self) -> None:
        rough_t, rough_w = rough_dimensions_mm("1x6")
        dressed_t, dressed_w = actual_dimensions_mm("1x6")
        assert rough_t.magnitude > dressed_t.magnitude
        assert rough_w.magnitude - dressed_w.magnitude == pytest.approx(12.7)

    def test_a_quarter_thickness_is_read_as_a_fraction(self) -> None:
        t, w = rough_dimensions_mm("5/4x6")
        assert float(t.to("inch").magnitude) == pytest.approx(1.25)
        assert float(w.to("inch").magnitude) == pytest.approx(6.0)

    def test_a_post_is_square(self) -> None:
        t, w = rough_dimensions_mm("6x6")
        assert t.magnitude == pytest.approx(w.magnitude)
        assert float(w.to("inch").magnitude) == pytest.approx(6.0)

    def test_it_needs_no_table_entry(self) -> None:
        """Unlike the dressed table, which is a lookup and can miss."""
        with pytest.raises(KeyError):
            actual_dimensions_mm("3x5")
        t, w = rough_dimensions_mm("3x5")
        assert float(t.to("inch").magnitude) == pytest.approx(3.0)
        assert float(w.to("inch").magnitude) == pytest.approx(5.0)

    @pytest.mark.parametrize("bad", ["", "1x6x2", "sixbysix", "1x"])
    def test_nonsense_raises(self, bad: str) -> None:
        with pytest.raises(ValueError, match="nominal size"):
            rough_dimensions_mm(bad)


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
