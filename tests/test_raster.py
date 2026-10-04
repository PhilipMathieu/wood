"""Tests for the software z-buffer rasteriser, on synthetic geometry only.

No build123d import here on purpose — these pin the projection and occlusion
math (the part that replaced mplot3d's painter's algorithm) independently of
CAD geometry, so a failure points at the raster itself.
"""

from __future__ import annotations

import numpy as np

from woodshop.render.raster import Camera, rasterize

RED = (1.0, 0.0, 0.0)
BLUE = (0.0, 0.0, 1.0)
GREEN = (0.0, 1.0, 0.0)

#: Looking down -Z: X right, Y up, and "nearer the eye" is larger Z, matching
#: raster.py's convention that ``forward`` points from the scene to the eye.
_CAMERA = Camera(center=(0.0, 0.0, 0.0), right=(1.0, 0.0, 0.0), up=(0.0, 1.0, 0.0),
                  forward=(0.0, 0.0, 1.0))


def _quad(half_size: float, z: float) -> np.ndarray:
    """Return two CCW (facing +Z) triangles forming a square at height *z*."""
    v0 = (-half_size, -half_size, z)
    v1 = (half_size, -half_size, z)
    v2 = (half_size, half_size, z)
    v3 = (-half_size, half_size, z)
    return np.array([[v0, v1, v2], [v0, v2, v3]], dtype=float)


def _pixel_color(image: np.ndarray, projection, point) -> np.ndarray:
    col, row = projection.to_pixel(point)
    return image[int(round(row)), int(round(col))]


def test_a_near_box_occludes_a_far_box():
    """The regression this module exists for: no whole-triangle depth sort."""
    far = _quad(half_size=10.0, z=0.0)
    near = _quad(half_size=4.0, z=10.0)
    triangles = np.concatenate([far, near])
    colors = np.array([RED, RED, BLUE, BLUE])

    image, projection = rasterize(triangles, colors, _CAMERA, size=200)

    assert np.allclose(_pixel_color(image, projection, (0.0, 0.0, 0.0)), BLUE)
    assert np.allclose(_pixel_color(image, projection, (8.0, 0.0, 0.0)), RED)


def test_coplanar_triangles_do_not_speckle():
    """Two exactly-overlapping flush faces (a half-lap) must pick one winner."""
    triangles = np.concatenate([_quad(half_size=5.0, z=0.0), _quad(half_size=5.0, z=0.0)])
    colors = np.array([RED, RED, GREEN, GREEN])

    image, projection = rasterize(triangles, colors, _CAMERA, size=200, supersample=1)

    col, row = (int(round(v)) for v in projection.to_pixel((0.0, 0.0, 0.0)))
    region = image[row - 20 : row + 20, col - 20 : col + 20].reshape(-1, 3)
    unique_colors = {tuple(np.round(c, 6)) for c in region}
    assert unique_colors == {RED}, "the first-drawn part should win uniformly, with no speckle"


def test_an_edge_hidden_behind_a_face_does_not_draw():
    # supersample=1: the antialiasing blend a higher factor introduces would
    # otherwise dilute pure GREEN into a red/green mix and defeat the check.
    face = _quad(half_size=10.0, z=0.0)
    hidden_edge = [np.array([(-8.0, -8.0, -50.0), (8.0, 8.0, -50.0)])]
    visible_edge = [np.array([(-8.0, -8.0, 0.0), (8.0, 8.0, 0.0)])]

    image_hidden, _ = rasterize(
        face, np.array([RED, RED]), _CAMERA,
        edges=hidden_edge, edge_colors=[GREEN], size=200, supersample=1,
    )
    image_visible, _ = rasterize(
        face, np.array([RED, RED]), _CAMERA,
        edges=visible_edge, edge_colors=[GREEN], size=200, supersample=1,
    )

    hidden_region = image_hidden.reshape(-1, 3)
    visible_region = image_visible.reshape(-1, 3)
    assert not np.any(np.all(np.isclose(hidden_region, GREEN), axis=1))
    assert np.any(np.all(np.isclose(visible_region, GREEN), axis=1))


def test_world_to_pixel_mapping_round_trips_onto_its_own_geometry():
    """Locating a triangle's own centroid must land back inside that triangle."""
    triangle = np.array([[(-6.0, -6.0, 0.0), (6.0, -6.0, 0.0), (0.0, 6.0, 0.0)]])
    image, projection = rasterize(triangle, np.array([BLUE]), _CAMERA, size=300)

    centroid = triangle[0].mean(axis=0)
    assert np.allclose(_pixel_color(image, projection, centroid), BLUE)

    # A point well outside the triangle must not land on it either.
    outside = (100.0, 100.0, 0.0)
    col, row = projection.to_pixel(outside)
    assert not (0 <= row < projection.height and 0 <= col < projection.width)
