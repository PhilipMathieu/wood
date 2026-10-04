"""OCCT hidden-line projection: turn a solid assembly into 2-D polylines.

For the orthographic views, whole-compound hidden-line removal — OCCT's
``HLRBRep_Algo``, reached through :meth:`build123d.Shape.project_to_viewport`
— replaces the painter's-algorithm shading ``model3d.py`` used to draw those
views with.  It sees the *whole* assembly at once and works from the exact
B-rep, so occlusion between parts comes out right (a bug per-part projection
cannot fix: it never sees the other parts to be occluded by), and there is no
tessellation tolerance to pick.  The cost is a monochrome line drawing rather
than a rendering — material colour survives only in the isometric, which is
drawn separately by ``raster.py``.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from build123d import Vector

__all__ = ["hlr_polylines"]

#: Samples per edge when flattening an OCCT curve to a polyline.  A straight
#: board edge only ever needs 2, but a round tabletop or a turned leg's
#: profile is one continuous curved edge — sample it too coarsely and the
#: hidden-line drawing facets in exactly the place the exact B-rep was
#: supposed to avoid faceting at all.
_SAMPLES_PER_EDGE = 64


def hlr_polylines(
    shape: Any,
    direction: tuple[float, float, float],
    up: tuple[float, float, float],
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Project *shape* to a viewport and flatten every edge to a polyline.

    Parameters
    ----------
    shape : build123d.Shape
        The whole assembly, projected as one shape (never re-wrapped in a
        new ``Compound`` — that would reparent it, via anytree, out from
        under the caller) so inter-part occlusion is resolved rather than
        just occlusion within one part's own faces.
    direction : tuple of float
        Unit vector from *shape*'s bounding-box centre toward the camera —
        the ``d`` computed from a view's elevation/azimuth, shared with
        ``raster.py``'s camera basis.
    up : tuple of float
        Viewport "up" hint, passed straight through to
        :meth:`~build123d.topology.composite.Compound.project_to_viewport`.

    Returns
    -------
    visible : list of numpy.ndarray
        One ``(k, 2)`` array of viewport ``(x, y)`` per visible edge.
    hidden : list of numpy.ndarray
        Same, for edges OCCT determined lie behind other geometry.
    """
    bbox = shape.bounding_box()
    center = bbox.center()
    diagonal = math.dist(
        (bbox.min.X, bbox.min.Y, bbox.min.Z), (bbox.max.X, bbox.max.Y, bbox.max.Z)
    )
    # Placed far outside the assembly so the viewport origin is never inside
    # the geometry it is projecting; orthographic output does not depend on
    # exactly how far.
    origin = Vector(
        center.X + direction[0] * 2 * diagonal,
        center.Y + direction[1] * 2 * diagonal,
        center.Z + direction[2] * 2 * diagonal,
    )
    visible_edges, hidden_edges = shape.project_to_viewport(
        viewport_origin=origin, viewport_up=up, look_at=center
    )
    return (
        [_polyline(edge) for edge in visible_edges],
        [_polyline(edge) for edge in hidden_edges],
    )


def _polyline(edge: Any) -> np.ndarray:
    """Sample *edge* at evenly spaced parameters and return viewport ``(x, y)``.

    HLR flattens every edge into the viewport's own XY plane — Z is constant
    across the whole projection — so only X and Y are kept.
    """
    points = [
        edge.position_at(t / (_SAMPLES_PER_EDGE - 1)) for t in range(_SAMPLES_PER_EDGE)
    ]
    return np.array([(p.X, p.Y) for p in points])
