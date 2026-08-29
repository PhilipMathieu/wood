"""Render an assembly as hidden-line and shaded views.

Until something draws the model, every claim about it rests on
``bounding_box()`` and a cut list — and a part rotated about the wrong axis, or
buried inside another part, passes both without complaint.  These views are the
cheapest way to find that class of mistake: look at it.

The three orthographic views (Front, Side, Plan) are OCCT hidden-line
drawings: :func:`woodshop.render.hlr.hlr_polylines` projects the *whole*
assembly at once through ``build123d``'s exact-B-rep HLR, so occlusion between
parts — not just between one part's own triangles — is resolved correctly, and
what is drawn is monochrome technical line work rather than a rendering. The
isometric is a shaded raster: :func:`woodshop.render.raster.rasterize` tessellates
the assembly (:meth:`build123d.Shape.tessellate`) and paints it through a pure-
numpy software z-buffer, so material colour survives and, unlike a whole-
triangle painter's algorithm, coincident or interleaved surfaces resolve pixel
by pixel instead of triangle by triangle.

Example
-------
>>> from woodshop.render.model3d import render_assembly     # doctest: +SKIP
>>> render_assembly(bed, output_png="bed.png")               # doctest: +SKIP
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.colors import to_rgb

from woodshop.render.hlr import hlr_polylines
from woodshop.render.raster import Camera, rasterize

__all__ = ["View", "STANDARD_VIEWS", "MATERIAL_COLORS", "render_assembly"]


@dataclass(frozen=True)
class View:
    """A named camera angle.

    Parameters
    ----------
    name : str
        Title shown above the view.
    elev : float
        Elevation angle in degrees.
    azim : float
        Azimuth angle in degrees.
    style : str, optional
        ``"auto"`` (default), ``"shaded"``, or ``"hlr"``. ``"auto"`` picks
        ``"hlr"`` when the view direction is axis-aligned — the three
        orthographic views — and ``"shaded"`` otherwise, so an isometric
        or any other oblique angle renders with material colour without the
        caller having to say so.
    """

    name: str
    elev: float
    azim: float
    style: str = "auto"


#: Isometric plus the three orthographic views, in the order they are drawn.
#: The orthographic angles are exact (mplot3d's old renderer needed a 1-2°
#: cheat off-axis to avoid a degenerate view box; HLR and the raster have no
#: such problem, so Front/Side/Plan look squarely along an axis).
STANDARD_VIEWS: tuple[View, ...] = (
    View("Isometric", 22.0, -55.0),
    View("Front", 0.0, -90.0),
    View("Side", 0.0, 0.0),
    View("Plan", 90.0, -90.0),
)

#: Approximate finished colours, so a material swap is obvious on sight.
MATERIAL_COLORS: dict[str, str] = {
    "cherry": "#8c4a2f",
    "walnut": "#4b3621",
    "maple": "#e0c9a6",
    "white_oak": "#c8ab7d",
    "pine": "#e8cf9f",
    "poplar": "#d6d2b0",
    "white_cedar": "#ddc49a",
    "syp_pt": "#b9b183",
    "plywood_cherry": "#c47a54",
    "plywood_birch": "#e8d6b3",
    "plywood_baltic_birch": "#f0e2c4",
}

_FALLBACK_COLOR = "#9e9e9e"

#: Direction the fake light comes from, so faces at different angles separate.
_LIGHT = (0.35, -0.62, 0.70)

#: Below this, a direction component counts as zero — the three orthographic
#: views hit their axes to double-precision, so this only has to reject the
#: isometric's genuinely oblique components, not filter out numerical noise.
_AXIS_SNAP = 1e-9

#: Edge samples per part edge in the shaded raster's overlay — matches
#: ``hlr.py``'s per-projected-edge sample count, though these stay in 3-D
#: world coordinates instead of being flattened to a viewport.  A curved edge
#: (a turned leg's profile) facets visibly at anything coarser.
_EDGE_SAMPLES = 64

#: Long side of the shaded raster, in pixels, before the 2x2 antialiasing
#: mean-pool; independent of ``figsize`` — matplotlib scales the finished
#: image into whatever axes box it is given.
_RASTER_LONG_SIDE = 1000
_RASTER_SUPERSAMPLE = 2

#: Hidden-line drawing style: a technical line drawing, not a rendering.
_HLR_VISIBLE_COLOR = "#37322c"
_HLR_HIDDEN_COLOR = "#b9b2a6"


def _shade(
    base: tuple[float, float, float],
    triangle: Any,
) -> tuple[float, float, float]:
    """Return *base* lightened or darkened according to the triangle's normal.

    A cheap directional light.  Without it every face of a board is the same
    flat colour and the solid reads as a silhouette.
    """
    (ax_, ay, az), (bx, by, bz), (cx, cy, cz) = triangle
    ux, uy, uz = bx - ax_, by - ay, bz - az
    vx, vy, vz = cx - ax_, cy - ay, cz - az
    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
    norm = (nx * nx + ny * ny + nz * nz) ** 0.5
    if norm == 0:
        return base
    lit = abs((nx * _LIGHT[0] + ny * _LIGHT[1] + nz * _LIGHT[2]) / norm)
    factor = 0.55 + 0.45 * lit
    return tuple(min(1.0, channel * factor) for channel in base)  # type: ignore[return-value]


def _direction(elev: float, azim: float) -> tuple[float, float, float]:
    """Return the unit vector from the assembly's centre toward the camera.

    Matches mplot3d's own elevation/azimuth convention exactly, so a
    ``View`` means the same thing it always has, regardless of which of the
    two renderers below ends up drawing it.
    """
    e = math.radians(elev)
    a = math.radians(azim)
    return (math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e))


def _is_axis_aligned(direction: tuple[float, float, float]) -> bool:
    """Return whether *direction* points along a single world axis.

    Two of its three components must vanish — an oblique angle like the
    isometric never satisfies this, however close its elevation gets to
    0 or 90.
    """
    return sum(abs(component) < _AXIS_SNAP for component in direction) >= 2


def _resolve_style(view: View, direction: tuple[float, float, float]) -> str:
    """Return ``"hlr"`` or ``"shaded"`` for *view*, expanding ``"auto"``."""
    if view.style == "auto":
        return "hlr" if _is_axis_aligned(direction) else "shaded"
    return view.style


def _camera_basis(
    direction: tuple[float, float, float],
) -> tuple[tuple[float, float, float], np.ndarray, np.ndarray]:
    """Return ``(up_hint, right, up)`` for a camera looking along *direction*.

    ``up_hint`` is the raw vector HLR's ``project_to_viewport`` expects (it
    orthogonalises internally); ``right``/``up`` are the exact orthonormal
    pair the software raster needs to build its own camera. Deriving both
    from the same ``up_hint`` keeps the two renderers agreeing pixel-for-
    pixel on which way is "up".
    """
    d = np.asarray(direction, dtype=float)
    up_hint = (0.0, 1.0, 0.0) if abs(d[2]) > 0.999 else (0.0, 0.0, 1.0)
    forward_into_scene = -d
    right = np.cross(forward_into_scene, up_hint)
    right = right / np.linalg.norm(right)
    up = np.cross(right, forward_into_scene)
    up = up / np.linalg.norm(up)
    return up_hint, right, up


def _iter_leaf_parts(node: Any) -> Iterator[Any]:
    """Yield every part leaf below *node*.

    A leaf is anything carrying the cut-list metadata that
    :class:`woodshop.parts.StockPart` sets.
    """
    if hasattr(node, "material") and hasattr(node, "stock_length_mm"):
        yield node
        return
    children: list[Any] = []
    if hasattr(node, "children"):
        children = list(node.children)
    elif hasattr(node, "part"):
        children = [node.part]
    for child in children:
        yield from _iter_leaf_parts(child)


def _tessellate(
    parts: list[Any], tolerance: float
) -> tuple[np.ndarray, np.ndarray, list[np.ndarray], list[tuple[float, float, float]]]:
    """Tessellate every part once, lit, plus a sampled polyline per edge.

    Parameters
    ----------
    parts : list
        Leaf parts from :func:`_iter_leaf_parts`.
    tolerance : float
        Passed straight to :meth:`build123d.Shape.tessellate`.

    Returns
    -------
    triangles : numpy.ndarray
        ``(n, 3, 3)`` world-space triangles from every part, in one array so
        the raster's z-buffer resolves occlusion across parts, not just
        within one part's own faces — the same reason the old painter's-
        algorithm renderer put every part into one collection.
    colors : numpy.ndarray
        ``(n, 3)`` lit RGB, one per triangle.
    edges : list of numpy.ndarray
        One ``(k, 3)`` world-space polyline per part edge — the seam a flat-
        shaded face would otherwise hide, e.g. a half-lap's interlock.
    edge_colors : list of tuple
        One RGB per polyline in *edges*, darkened from its part's colour.
    """
    triangles: list[np.ndarray] = []
    colors: list[tuple[float, float, float]] = []
    edges: list[np.ndarray] = []
    edge_colors: list[tuple[float, float, float]] = []
    for part in parts:
        base = to_rgb(MATERIAL_COLORS.get(part.material, _FALLBACK_COLOR))
        vertices, tris = part.tessellate(tolerance)
        verts = np.array([(v.X, v.Y, v.Z) for v in vertices])
        for tri in tris:
            triangle = verts[list(tri)]
            triangles.append(triangle)
            colors.append(_shade(base, triangle))
        edge_color = tuple(channel * 0.45 for channel in base)
        for edge in part.edges():
            points = [edge.position_at(t / (_EDGE_SAMPLES - 1)) for t in range(_EDGE_SAMPLES)]
            edges.append(np.array([(p.X, p.Y, p.Z) for p in points]))
            edge_colors.append(edge_color)
    tri_array = np.array(triangles) if triangles else np.empty((0, 3, 3))
    color_array = np.array(colors) if colors else np.empty((0, 3))
    return tri_array, color_array, edges, edge_colors


def _draw_hlr(ax: plt.Axes, assembly: Any, direction: tuple[float, float, float]) -> None:
    """Draw one orthographic view of *assembly* as an OCCT hidden-line drawing."""
    up_hint, _, _ = _camera_basis(direction)
    visible, hidden = hlr_polylines(assembly, direction, up_hint)
    if hidden:
        ax.add_collection(
            LineCollection(
                hidden, colors=_HLR_HIDDEN_COLOR, linewidths=0.6, linestyles=(0, (2, 2))
            )
        )
    if visible:
        ax.add_collection(LineCollection(visible, colors=_HLR_VISIBLE_COLOR, linewidths=1.1))
    ax.set_aspect("equal")
    ax.margins(0.04)
    ax.autoscale()


def _draw_shaded(
    ax: plt.Axes,
    geometry: tuple[np.ndarray, np.ndarray, list[np.ndarray], list[tuple[float, float, float]]],
    direction: tuple[float, float, float],
    center: Any,
) -> None:
    """Draw one shaded, z-buffered raster view of pre-tessellated *geometry*."""
    triangles, colors, edges, edge_colors = geometry
    _, right, up = _camera_basis(direction)
    camera = Camera(
        center=(center.X, center.Y, center.Z), right=right, up=up, forward=direction
    )
    image, _ = rasterize(
        triangles,
        colors,
        camera,
        edges=edges,
        edge_colors=edge_colors,
        size=_RASTER_LONG_SIDE,
        supersample=_RASTER_SUPERSAMPLE,
    )
    ax.imshow(image)


def render_assembly(
    assembly: Any,
    output_png: str | Path | None = None,
    output_pdf: str | Path | None = None,
    views: tuple[View, ...] = STANDARD_VIEWS,
    tolerance: float = 0.5,
    title: str = "",
    figsize: tuple[float, float] = (14.0, 12.0),
    close: bool = True,
) -> plt.Figure:
    """Draw *assembly* from several angles on one figure.

    Parameters
    ----------
    assembly : build123d.Compound
        The positioned assembly to draw.  Projected directly — never
        rewrapped in a new ``Compound`` — since :meth:`~build123d.topology.\
composite.Compound.project_to_viewport` reparents its argument via anytree,
        which would otherwise mutate the caller's own assembly.
    output_png : str or Path, optional
        If given, save a PNG here.
    output_pdf : str or Path, optional
        If given, save a PDF here.  The hidden-line views are true vector
        line work at any zoom; the isometric is the raster image.
    views : tuple of View, optional
        Camera angles, default :data:`STANDARD_VIEWS`.
    tolerance : float, optional
        Tessellation tolerance in mm for the shaded views only, default
        0.5 mm — where faceting stops showing at gallery sizes on a turned
        leg or round top. The hidden-line views come from the exact B-rep
        and ignore it entirely.
    title : str, optional
        Figure title.
    figsize : tuple, optional
        Figure size in inches.
    close : bool, optional
        Close the figure after saving, default ``True``.  Set ``False`` to keep
        it for interactive display — but then it is the caller's job to close
        it, or matplotlib will eventually complain about open figures.

    Returns
    -------
    matplotlib.figure.Figure
        The figure, closed unless *close* is ``False``.

    Raises
    ------
    ValueError
        If *assembly* contains no parts carrying cut-list metadata.
    """
    parts = list(_iter_leaf_parts(assembly))
    if not parts:
        raise ValueError(
            "assembly contains no Board/Panel parts — nothing to draw. "
            "Check that the parts carry material and stock_length_mm."
        )

    directions = [_direction(view.elev, view.azim) for view in views]
    styles = [_resolve_style(view, d) for view, d in zip(views, directions)]

    # Tessellation is the expensive step; skip it entirely when every
    # resolved view is a hidden-line drawing (the exact-B-rep path needs no
    # mesh at all).
    geometry = None
    center = None
    if any(style == "shaded" for style in styles):
        geometry = _tessellate(parts, tolerance)
        center = assembly.bounding_box().center()

    n = len(views)
    cols = 2 if n > 1 else 1
    rows = (n + cols - 1) // cols
    fig = plt.figure(figsize=figsize)
    if title:
        fig.suptitle(title, fontsize=14)

    for index, (view, direction, style) in enumerate(zip(views, directions, styles)):
        ax = fig.add_subplot(rows, cols, index + 1)
        if style == "hlr":
            _draw_hlr(ax, assembly, direction)
        else:
            _draw_shaded(ax, geometry, direction, center)
        ax.set_title(view.name, fontsize=10)
        ax.set_axis_off()

    fig.tight_layout()
    _save(fig, output_png, output_pdf)
    if close:
        plt.close(fig)
    return fig


def _save(
    fig: plt.Figure,
    output_png: str | Path | None,
    output_pdf: str | Path | None,
) -> None:
    """Write *fig* to the requested formats."""
    if output_png is not None:
        fig.savefig(output_png, dpi=140, bbox_inches="tight")
    if output_pdf is not None:
        fig.savefig(output_pdf, bbox_inches="tight")
