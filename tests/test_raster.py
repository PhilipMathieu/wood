"""Tests for the software z-buffer rasteriser, on synthetic geometry only.

No build123d import here on purpose — these pin the projection and occlusion
math (the part that replaced mplot3d's painter's algorithm) independently of
CAD geometry, so a failure points at the raster itself.
"""

from __future__ import annotations

import numpy as np

from woodshop.render.raster import Camera, Screen, _wire_cover, rasterize

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


def test_wire_cover_is_exact_for_a_box_filter():
    # A pixel two pitches wide covers exactly two wires' worth, wherever it sits.
    s = np.linspace(0.0, 10.0, 41)
    cover = _wire_cover(s, np.full_like(s, 20.0), pitch=10.0, wire=1.0)
    assert np.allclose(cover, 0.1)
    # A narrow pixel on a wire is wholly covered; one midway between is clear.
    assert np.isclose(_wire_cover(np.array([0.0]), np.array([0.2]), 10.0, 1.0)[0], 1.0)
    assert np.isclose(_wire_cover(np.array([5.0]), np.array([0.2]), 10.0, 1.0)[0], 0.0)


def test_a_screen_shows_what_is_behind_it_between_its_wires():
    behind = _quad(half_size=10.0, z=0.0)
    mesh = _quad(half_size=10.0, z=5.0)
    triangles = np.concatenate([behind, mesh])
    colors = np.array([RED, RED, BLUE, BLUE])
    screen = Screen(
        origin=(-10.0, -10.0, 5.0), axis_a=(1.0, 0.0, 0.0), pitch_a=5.0,
        axis_b=(0.0, 1.0, 0.0), pitch_b=5.0, wire=0.5,
    )

    image, projection = rasterize(
        triangles, colors, _CAMERA, size=400, supersample=1,
        screen_ids=np.array([-1, -1, 0, 0]), screens=[screen],
    )

    # Midway between wires the red face behind shows through untouched...
    assert np.allclose(_pixel_color(image, projection, (2.5, 2.5, 5.0)), RED)
    # ...and where two wires cross, the mesh is drawn.
    assert np.allclose(_pixel_color(image, projection, (0.0, 0.0, 5.0)), BLUE)


def test_bounds_draw_a_close_up_window():
    triangles = np.concatenate([_quad(half_size=10.0, z=0.0)])
    image, projection = rasterize(
        triangles, np.array([RED, RED]), _CAMERA, size=200,
        bounds=(-2.0, 2.0, -1.0, 1.0),
    )
    assert image.shape[:2] == (100, 200)
    assert np.allclose(image, RED)  # the window is wholly inside the face
    assert np.isclose(projection.scale, 50.0)
