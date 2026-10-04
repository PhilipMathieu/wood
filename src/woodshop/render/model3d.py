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
from woodshop.render.raster import Camera, Screen, rasterize
from woodshop.render.trim import trim_interpenetrations

__all__ = [
    "View",
    "STANDARD_VIEWS",
    "MATERIAL_COLORS",
    "GROUND_COLOR",
    "GROUND_ALPHA",
    "SCREEN_MATERIALS",
    "render_assembly",
    "render_configurations",
    "wants_ground",
]


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
    window_mm : tuple of float, optional
        ``(width, height)`` of a close-up: draw only this much of the model,
        in mm across the image, centred on a focus point the caller gives
        (:func:`render_configurations`) or on the model's centre.  Default
        ``None`` draws the whole model.  Shaded views only.
    """

    name: str
    elev: float
    azim: float
    style: str = "auto"
    window_mm: tuple[float, float] | None = None


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
    # Fresh northern white cedar is pale straw; left outside it silvers within
    # a season or two, which is why nobody stains a fence twice.
    "white_cedar": "#ddc49a",
    "syp_pt": "#b9b183",
    # Rough sawn hemlock: a redder, darker tan than the cedar beside it.
    "hemlock": "#c49a74",
    # Black PVC over galvanised wire: near-black, and not quite, because a
    # true black reads as a hole in a shaded render.
    "steel_mesh_black": "#2f3234",
    "steel_mesh_black_2x3": "#2f3234",
    # White vinyl, a shade off white so the shading still reads.
    "vinyl_pvc": "#ecebe6",
    "plywood_cherry": "#c47a54",
    "plywood_birch": "#e8d6b3",
    "plywood_baltic_birch": "#f0e2c4",
}

_FALLBACK_COLOR = "#9e9e9e"

#: Materials drawn as a see-through grid of wires instead of a solid, keyed
#: by material: ``(horizontal pitch, vertical pitch, wire)`` in mm.
#:
#: Welded mesh is modelled as a thin sheet (a wire per solid would be
#: hundreds of solids a bay), and drawn as a sheet it is an opaque black
#: board that hides the rails and posts behind it.  The shaded views draw
#: the sheet as the wire grid it stands for.  2" x 4" mesh is vertical wires
#: every 2" and horizontal wires every 4"; 14 ga is 2.0 mm of steel, about
#: 2.5 mm with its PVC coat.
SCREEN_MATERIALS: dict[str, tuple[float, float, float]] = {
    "steel_mesh_black": (50.8, 101.6, 2.5),
    # 2" x 3" garden fencing, about 16 ga: 1.6 mm wire, 2 mm coated.
    "steel_mesh_black_2x3": (50.8, 76.2, 2.0),
}

#: Colour of the ground plane: a muted moss-grey that reads as ground without
#: competing with the cedar in front of it.
GROUND_COLOR: str = "#6f7d72"

#: How strongly the ground colour is laid over the white page.  The raster
#: has a z-buffer and no transparency, so the ground is drawn opaque at this
#: blend, and what is below grade is clipped away in the shaded view, as it
#: is in the yard.  The hidden-line views still draw every post to its foot.
GROUND_ALPHA: float = 0.34

#: How far the ground reaches past the model, as a fraction of its footprint.
GROUND_MARGIN: float = 0.05

#: How far it reaches across the *narrow* axis, as a fraction of the long one.
#:
#: A fence is 58 ft long and 8 inches deep, so a plane that only cleared the
#: model would be a ribbon rather than ground.  Giving the short axis a share
#: of the long one puts some earth in front of the fence and some behind it,
#: which is what makes it read as the ground the posts are in.
GROUND_ASPECT: float = 0.08

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
        if view.window_mm is not None:
            return "shaded"
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


def _screen_for(part: Any, spec: tuple[float, float, float]) -> Screen:
    """Return the wire grid a flat *part* stands for.

    The sheet's plane is the two axes its bounding box is widest along.
    Where one of them is vertical, the wires spaced along it get the
    vertical pitch; the grid starts at the sheet's corner, as a roll cut to
    length does.
    """
    pitch_h, pitch_v, wire = spec
    bb = part.bounding_box()
    extents = (bb.max.X - bb.min.X, bb.max.Y - bb.min.Y, bb.max.Z - bb.min.Z)
    thin = int(np.argmin(extents))
    in_plane = [axis for axis in range(3) if axis != thin]
    vertical = 2 if 2 in in_plane else in_plane[1]
    horizontal = in_plane[0] if in_plane[0] != vertical else in_plane[1]
    unit = np.eye(3)
    return Screen(
        origin=(bb.min.X, bb.min.Y, bb.min.Z),
        axis_a=unit[horizontal],
        pitch_a=pitch_h,
        axis_b=unit[vertical],
        pitch_b=pitch_v,
        wire=wire,
    )


def _tessellate_scene(parts: list[Any], tolerance: float) -> tuple:
    """Tessellate *parts* as :func:`_tessellate` does, with mesh as screens.

    Returns
    -------
    tuple
        ``(triangles, colors, edges, edge_colors, screen_ids, screens)``:
        :func:`_tessellate`'s four, then one :func:`~woodshop.render.raster.\
rasterize` screen index per triangle (``-1`` for an opaque face) and the
        screens those indices name — one per part in :data:`SCREEN_MATERIALS`.
    """
    solid = [part for part in parts if part.material not in SCREEN_MATERIALS]
    mesh = [part for part in parts if part.material in SCREEN_MATERIALS]
    triangles, colors, edges, edge_colors = _tessellate(solid, tolerance)
    tri_chunks, color_chunks = [triangles], [colors]
    id_chunks = [np.full(len(triangles), -1, dtype=int)]
    screens: list[Screen] = []
    for part in mesh:
        m_tris, m_cols, m_edges, m_edge_cols = _tessellate([part], tolerance)
        id_chunks.append(np.full(len(m_tris), len(screens), dtype=int))
        screens.append(_screen_for(part, SCREEN_MATERIALS[part.material]))
        tri_chunks.append(m_tris)
        color_chunks.append(m_cols)
        edges += m_edges
        edge_colors += m_edge_cols
    return (
        np.concatenate(tri_chunks),
        np.concatenate(color_chunks),
        edges,
        edge_colors,
        np.concatenate(id_chunks),
        screens,
    )


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


def _ground_triangles(
    bb: Any, margin: float = GROUND_MARGIN
) -> tuple[np.ndarray, np.ndarray]:
    """Return two triangles covering the ground at ``z = 0``, and their colour.

    Grade is ``z = 0`` in every outdoor model here, so the plane needs no
    argument beyond the model's own footprint.

    Parameters
    ----------
    bb : build123d.BoundBox
        The assembly's bounding box.
    margin : float, optional
        Overhang past the model as a fraction of its footprint, default
        :data:`GROUND_MARGIN`.

    Returns
    -------
    triangles : numpy.ndarray
        ``(2, 3, 3)`` world-space triangles.
    colors : numpy.ndarray
        ``(2, 3)`` RGB: :data:`GROUND_COLOR` laid over white at
        :data:`GROUND_ALPHA`.
    """
    footprint = max(bb.size.X, bb.size.Y)
    pad_x = max(bb.size.X * margin, footprint * GROUND_ASPECT, 25.0)
    pad_y = max(bb.size.Y * margin, footprint * GROUND_ASPECT, 25.0)
    x0, x1 = bb.min.X - pad_x, bb.max.X + pad_x
    y0, y1 = bb.min.Y - pad_y, bb.max.Y + pad_y
    a, b, c, d = (x0, y0, 0.0), (x1, y0, 0.0), (x1, y1, 0.0), (x0, y1, 0.0)
    triangles = np.array([[a, b, c], [a, c, d]], dtype=float)
    ground = np.array(to_rgb(GROUND_COLOR))
    colour = GROUND_ALPHA * ground + (1.0 - GROUND_ALPHA) * np.ones(3)
    return triangles, np.array([colour, colour])


def _clip_below_grade(parts: list[Any], bb: Any, tolerance: float) -> list[Any]:
    """Return *parts* with everything below ``z = 0`` cut away, render-only.

    Never mutates the caller's parts: anything that does not reach below
    grade is returned as the same object, and anything that does is replaced
    by a new solid carrying the same material.
    """
    from build123d import Box, Pos

    pad = 1000.0
    below = Pos(
        bb.center().X, bb.center().Y, (bb.min.Z - pad) / 2
    ) * Box(bb.size.X + 2 * pad, bb.size.Y + 2 * pad, -bb.min.Z + pad)
    out: list[Any] = []
    for part in parts:
        if part.bounding_box().min.Z >= -tolerance:
            out.append(part)
            continue
        if part.bounding_box().max.Z <= tolerance:
            continue  # wholly underground: nothing of it shows
        clipped = part - below
        clipped.material = part.material
        out.append(clipped)
    return out


def _with_ground(geometry: tuple, bb: Any) -> tuple:
    """Return :func:`_tessellate_scene` *geometry* with the ground added.

    The ground is two opaque triangles and no edges.
    """
    triangles, colors, edges, edge_colors, screen_ids, screens = geometry
    g_tris, g_cols = _ground_triangles(bb)
    return (
        np.concatenate([triangles, g_tris]),
        np.concatenate([colors, g_cols]),
        edges,
        edge_colors,
        np.concatenate([screen_ids, np.full(len(g_tris), -1, dtype=int)]),
        screens,
    )


def _draw_shaded(
    ax: plt.Axes,
    geometry: tuple,
    direction: tuple[float, float, float],
    center: Any,
    window: tuple[float, float] | None = None,
    focus: tuple[float, float, float] | None = None,
) -> None:
    """Draw one shaded, z-buffered raster view of pre-tessellated *geometry*.

    With *window* — ``(width, height)`` in mm — draw only that much of the
    scene, centred on *focus* (default *center*).
    """
    triangles, colors, edges, edge_colors, screen_ids, screens = geometry
    _, right, up = _camera_basis(direction)
    origin = np.array((center.X, center.Y, center.Z))
    camera = Camera(center=origin, right=right, up=up, forward=direction)
    bounds = None
    if window is not None:
        target = origin if focus is None else np.asarray(focus, dtype=float)
        u = float((target - origin) @ np.asarray(right))
        v = float((target - origin) @ np.asarray(up))
        width, height = window
        bounds = (u - width / 2, u + width / 2, v - height / 2, v + height / 2)
    image, _ = rasterize(
        triangles,
        colors,
        camera,
        edges=edges,
        edge_colors=edge_colors,
        size=_RASTER_LONG_SIDE,
        supersample=_RASTER_SUPERSAMPLE,
        screen_ids=screen_ids,
        screens=screens,
        bounds=bounds,
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
    ground: bool | None = None,
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
    ground : bool or None, optional
        Draw the ground at ``z = 0`` in the shaded views.  ``None`` (default)
        draws it when the model goes below zero, which is the same thing as
        saying "when part of this is in the ground": a fence post four feet
        down is otherwise a stick hanging in space, and a nightstand does not
        want a slab through its feet.
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

    prepared = _prepare(assembly, parts, views, tolerance, ground)

    n = len(views)
    cols = 2 if n > 1 else 1
    rows = (n + cols - 1) // cols
    fig = plt.figure(figsize=figsize)
    if title:
        fig.suptitle(title, fontsize=14)

    for index, view in enumerate(views):
        ax = fig.add_subplot(rows, cols, index + 1)
        _draw_view(ax, assembly, index, prepared, view)
        ax.set_title(view.name, fontsize=10)
        ax.set_axis_off()

    fig.tight_layout()
    _save(fig, output_png, output_pdf)
    if close:
        plt.close(fig)
    return fig


def _prepare(
    assembly: Any,
    parts: list[Any],
    views: tuple[View, ...],
    tolerance: float,
    ground: bool | None,
) -> tuple[list[Any], list[str], Any, Any]:
    """Resolve each view's direction and style, and tessellate if any shades.

    Returns
    -------
    tuple
        ``(directions, styles, geometry, center)``; *geometry* and *center*
        are ``None`` when every view is a hidden-line drawing.
    """
    directions = [_direction(view.elev, view.azim) for view in views]
    styles = [_resolve_style(view, d) for view, d in zip(views, directions)]

    # Tessellation is the expensive step; skip it entirely when every
    # resolved view is a hidden-line drawing (the exact-B-rep path needs no
    # mesh at all).
    geometry = None
    center = None
    if any(style == "shaded" for style in styles):
        # A part that genuinely interpenetrates another (a housed joint
        # modelled without the boolean cut that would remove it) crosses
        # that neighbour's mesh along a curve neither triangulation lands
        # on — the z-buffer's tie epsilon only covers the *flush*, zero-
        # overlap case, so an uncut overlap reads as a jagged seam instead
        # of a clean one. Trimming it out here, before tessellation, is
        # render-only: it never touches the parts the caller passed in.
        bb = assembly.bounding_box()
        center = bb.center()
        shaded_parts = trim_interpenetrations(parts)
        if wants_ground(bb, ground, tolerance):
            # What is in the ground is not drawn in the shaded view, as it is
            # not seen in the yard; the hidden-line views still draw every
            # post to its foot, which is where its depth is read.
            shaded_parts = _clip_below_grade(shaded_parts, bb, tolerance)
            geometry = _with_ground(_tessellate_scene(shaded_parts, tolerance), bb)
        else:
            geometry = _tessellate_scene(shaded_parts, tolerance)
    return directions, styles, geometry, center


def _draw_view(
    ax: plt.Axes,
    assembly: Any,
    index: int,
    prepared: tuple[list[Any], list[str], Any, Any],
    view: View | None = None,
    focus: tuple[float, float, float] | None = None,
) -> None:
    """Draw view number *index* of a :func:`_prepare` result onto *ax*.

    A *view* with a ``window_mm`` is drawn as a close-up on *focus*.
    """
    directions, styles, geometry, center = prepared
    if styles[index] == "hlr":
        _draw_hlr(ax, assembly, directions[index])
    else:
        window = view.window_mm if view is not None else None
        _draw_shaded(ax, geometry, directions[index], center, window, focus)


def render_configurations(
    configurations: list[tuple],
    output_png: str | Path | None = None,
    output_pdf: str | Path | None = None,
    views: tuple[View, ...] = (STANDARD_VIEWS[0], STANDARD_VIEWS[1]),
    tolerance: float = 0.5,
    title: str = "",
    figsize: tuple[float, float] | None = None,
    ground: bool | None = None,
    close: bool = True,
) -> plt.Figure:
    """Draw several assemblies of one design, one row each, on one figure.

    The same design built to different layouts — a short run tied into a
    wall, a gate, a long straight run — reads better side by side than as
    one long model, because each is drawn at its own scale.

    Parameters
    ----------
    configurations : list of tuple
        ``(caption, assembly)`` or ``(caption, assembly, focus)`` for each
        row, top to bottom.  *focus* is the world point, mm, a close-up view
        (one with ``window_mm``) is centred on; default the model's centre.
    output_png, output_pdf : str or Path, optional
        Where to save.
    views : tuple of View, optional
        The columns, default isometric and front.
    tolerance : float, optional
        Tessellation tolerance for the shaded views, mm.
    title : str, optional
        Figure title.
    figsize : tuple, optional
        Figure size in inches; default scales with rows and columns.
    ground : bool or None, optional
        As :func:`render_assembly`.
    close : bool, optional
        Close the figure after saving, default ``True``.

    Returns
    -------
    matplotlib.figure.Figure
        The figure, closed unless *close* is ``False``.

    Raises
    ------
    ValueError
        If *configurations* is empty or any assembly has no parts.
    """
    if not configurations:
        raise ValueError("nothing to draw: no configurations given")
    rows, cols = len(configurations), len(views)
    fig = plt.figure(figsize=figsize or (6.0 * cols, 3.2 * rows))
    if title:
        fig.suptitle(title, fontsize=14)
    for row, (caption, assembly, *rest) in enumerate(configurations):
        focus = rest[0] if rest else None
        parts = list(_iter_leaf_parts(assembly))
        if not parts:
            raise ValueError(f"configuration {caption!r} has no parts to draw")
        prepared = _prepare(assembly, parts, views, tolerance, ground)
        for col, view in enumerate(views):
            ax = fig.add_subplot(rows, cols, row * cols + col + 1)
            _draw_view(ax, assembly, col, prepared, view, focus)
            label = caption if not view.name else f"{caption} — {view.name.lower()}"
            ax.set_title(label, fontsize=10)
            ax.set_axis_off()
    fig.tight_layout()
    _save(fig, output_png, output_pdf)
    if close:
        plt.close(fig)
    return fig


def wants_ground(bb: Any, ground: bool | None, tolerance: float = 0.5) -> bool:
    """Return whether a model with bounding box *bb* gets a ground plane.

    Parameters
    ----------
    bb : build123d.BoundBox
        The model's bounding box.
    ground : bool or None
        An explicit answer, or ``None`` to decide from the model: anything
        reaching more than *tolerance* below ``z = 0`` is in the ground.
    tolerance : float, optional
        Slack in mm, default 0.5.
    """
    if ground is not None:
        return ground
    return bb.min.Z < -tolerance


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
