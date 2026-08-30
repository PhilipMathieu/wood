"""Tests for the render-time boolean pre-trim, on plain build123d boxes.

Real leaf parts (:class:`woodshop.parts.StockPart` and friends) carry more
metadata than :func:`~woodshop.render.trim.trim_interpenetrations` needs —
it only ever reads ``bounding_box()``, ``intersect()``, ``volume``, and sets
``.material`` on a loser — so plain :class:`build123d.Box` solids with
``.material`` set by hand are enough to pin the logic.
"""

from __future__ import annotations

import pytest
from build123d import Box, Pos

from woodshop.render.trim import trim_interpenetrations


def _box(size: tuple[float, float, float], center: tuple[float, float, float], material: str):
    part = Pos(*center) * Box(*size)
    part.material = material
    return part


def test_disjoint_parts_are_returned_unchanged():
    a = _box((10, 10, 10), (0, 0, 0), "cherry")
    b = _box((10, 10, 10), (50, 0, 0), "walnut")

    result = trim_interpenetrations([a, b])

    assert result[0] is a
    assert result[1] is b


def test_flush_touching_faces_are_not_trimmed():
    a = _box((10, 10, 10), (0, 0, 0), "cherry")
    b = _box((10, 10, 10), (10, 0, 0), "walnut")  # shares the x=5 face exactly

    result = trim_interpenetrations([a, b])

    assert result[0] is a
    assert result[1] is b


def test_a_real_overlap_trims_the_smaller_part():
    large = _box((20, 20, 20), (0, 0, 0), "cherry")
    small = _box((6, 6, 6), (7, 0, 0), "walnut")  # overlaps large's +X face
    large_volume, small_volume = large.volume, small.volume

    result = trim_interpenetrations([large, small])

    assert result[0] is large
    assert result[0].volume == large_volume
    assert result[1] is not small
    overlap = large.intersect(small)
    overlap_volume = sum(s.volume for s in overlap)
    assert result[1].volume == pytest.approx(small_volume - overlap_volume)
    assert result[1].intersect(result[0]) is None
    # originals are untouched
    assert large.volume == large_volume
    assert small.volume == small_volume


def test_material_survives_onto_the_trimmed_part():
    large = _box((20, 20, 20), (0, 0, 0), "cherry")
    small = _box((6, 6, 6), (7, 0, 0), "walnut")

    result = trim_interpenetrations([large, small])

    assert result[1].material == "walnut"
    assert result[0].material == "cherry"


def test_a_part_can_lose_volume_to_two_separate_overlaps():
    small = _box((30, 3, 3), (0, 0, 0), "plywood_birch")  # thin, spans both boxes below
    left = _box((10, 10, 10), (-12, 0, 0), "cherry")
    right = _box((10, 10, 10), (12, 0, 0), "cherry")
    small_volume = small.volume
    left_overlap = sum(s.volume for s in small.intersect(left))
    right_overlap = sum(s.volume for s in small.intersect(right))

    result = trim_interpenetrations([small, left, right])

    assert result[1] is left
    assert result[2] is right
    assert result[0] is not small
    assert result[0].volume == pytest.approx(small_volume - left_overlap - right_overlap)


def test_equal_volume_ties_favour_the_earlier_part():
    a = _box((10, 10, 10), (0, 0, 0), "cherry")
    b = _box((10, 10, 10), (6, 0, 0), "walnut")  # identical volume, real overlap
    assert a.volume == b.volume

    result = trim_interpenetrations([a, b])

    assert result[0] is a
    assert result[1] is not b
