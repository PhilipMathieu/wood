"""Render an assembly as shaded 3-D views.

Until something draws the model, every claim about it rests on
``bounding_box()`` and a cut list — and a part rotated about the wrong axis, or
buried inside another part, passes both without complaint.  These views are the
cheapest way to find that class of mistake: look at it.

Geometry comes from :meth:`build123d.Shape.tessellate`, so what is drawn is the
real solid rather than a stand-in built from part dimensions.  Parts are
coloured by material, which makes a substitution visible at a glance.

Example
-------
>>> from woodshop.render.model3d import render_assembly     # doctest: +SKIP
>>> render_assembly(bed, output_png="bed.png")              # doctest: +SKIP
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

__all__ = [
    "View",
    "STANDARD_VIEWS",
    "MATERIAL_COLORS",
    "GROUND_COLOR",
    "GROUND_ALPHA",
    "render_assembly",
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
    """

    name: str
    elev: float
    azim: float


#: Isometric plus the three orthographic views, in the order they are drawn.
STANDARD_VIEWS: tuple[View, ...] = (
    View("Isometric", 22.0, -55.0),
    View("Front", 2.0, -90.0),
    View("Side", 2.0, 0.0),
    View("Plan", 89.0, -90.0),
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
    "white_cedar": "#d8c9a3",
    # Black PVC over galvanised wire: near-black, and not quite, because a
    # true black reads as a hole in a shaded render.
    "steel_mesh_black": "#2f3234",
    "plywood_cherry": "#c47a54",
    "plywood_birch": "#e8d6b3",
    "plywood_baltic_birch": "#f0e2c4",
}

_FALLBACK_COLOR = "#9e9e9e"

#: Colour of the ground plane: a muted moss-grey that reads as ground without
#: competing with the cedar in front of it.
GROUND_COLOR: str = "#6f7d72"

#: How opaque the ground is.  Transparent on purpose — what is under it is a
#: third of the length of every post, and a solid plane would hide exactly the
#: part of the drawing nobody can inspect once the fence is built.
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

#: How many quads the ground is split into, per axis.
#:
#: One big quad would be one polygon with one depth, and matplotlib sorts whole
#: polygons: the ground would pass entirely in front of or entirely behind the
#: fence rather than in front of the near posts and behind the far ones.
#: Splitting it lets the sort be local, which is as close to a depth buffer as
#: this renderer gets.
GROUND_GRID: int = 12

#: Direction the fake light comes from, so faces at different angles separate.
_LIGHT = (0.35, -0.62, 0.70)


def _shade(
    base: tuple[float, float, float],
    triangle: list[tuple[float, float, float]],
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
    lit = abs(
        (nx * _LIGHT[0] + ny * _LIGHT[1] + nz * _LIGHT[2]) / norm
    )
    factor = 0.55 + 0.45 * lit
    return tuple(min(1.0, channel * factor) for channel in base)  # type: ignore[return-value]


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


def _ground_faces(
    bb: Any, grid: int = GROUND_GRID, margin: float = GROUND_MARGIN
) -> tuple[list[list[tuple[float, float, float]]], list[tuple[float, ...]]]:
    """Return the triangles and colours of a transparent plane at ``z = 0``.

    Grade is ``z = 0`` in every outdoor model here, so the plane needs no
    argument beyond the model's own footprint.

    Parameters
    ----------
    bb : build123d.BoundBox
        The assembly's bounding box.
    grid : int, optional
        Quads per axis, default :data:`GROUND_GRID`.
    margin : float, optional
        Overhang past the model as a fraction of its footprint, default
        :data:`GROUND_MARGIN`.

    Returns
    -------
    faces : list
        Triangles, two per quad.
    facecolors : list
        One RGBA colour per triangle.
    """
    footprint = max(bb.size.X, bb.size.Y)
    pad_x = max(bb.size.X * margin, footprint * GROUND_ASPECT, 25.0)
    pad_y = max(bb.size.Y * margin, footprint * GROUND_ASPECT, 25.0)
    x0, x1 = bb.min.X - pad_x, bb.max.X + pad_x
    y0, y1 = bb.min.Y - pad_y, bb.max.Y + pad_y

    faces: list[list[tuple[float, float, float]]] = []
    colour = (*to_rgb(GROUND_COLOR), GROUND_ALPHA)
    for i in range(grid):
        xa = x0 + (x1 - x0) * i / grid
        xb = x0 + (x1 - x0) * (i + 1) / grid
        for j in range(grid):
            ya = y0 + (y1 - y0) * j / grid
            yb = y0 + (y1 - y0) * (j + 1) / grid
            corners = [(xa, ya, 0.0), (xb, ya, 0.0), (xb, yb, 0.0), (xa, yb, 0.0)]
            faces.append([corners[0], corners[1], corners[2]])
            faces.append([corners[0], corners[2], corners[3]])
    return faces, [colour] * len(faces)


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
        The positioned assembly to draw.
    output_png : str or Path, optional
        If given, save a PNG here.
    output_pdf : str or Path, optional
        If given, save a PDF here.
    views : tuple of View, optional
        Camera angles, default :data:`STANDARD_VIEWS`.
    tolerance : float, optional
        Tessellation tolerance in mm, default 0.5.  Flat-sided parts look the
        same at any tolerance; a turned leg or a round top does not, and 0.5 mm
        is where the faceting stops showing at gallery sizes.
    title : str, optional
        Figure title.
    figsize : tuple, optional
        Figure size in inches.
    ground : bool or None, optional
        Draw a transparent plane at ``z = 0``.  ``None`` (default) draws one
        when the model goes below zero, which is the same thing as saying "when
        part of this is in the ground": a fence post four feet down is
        otherwise a stick hanging in space, and a nightstand does not want a
        slab through its feet.
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

    # Tessellate once; every view reuses the same triangles.  Faces from every
    # part go into one list so matplotlib depth-sorts the whole assembly
    # together — sorting per part draws the centre rail over the slats that
    # cover it.
    faces: list[list[tuple[float, float, float]]] = []
    facecolors: list[tuple[float, ...]] = []
    for part in parts:
        base = to_rgb(MATERIAL_COLORS.get(part.material, _FALLBACK_COLOR))
        vertices, triangles = part.tessellate(tolerance)
        for triangle in triangles:
            tri = [
                (vertices[i].X, vertices[i].Y, vertices[i].Z) for i in triangle
            ]
            faces.append(tri)
            # Opaque, and said so explicitly: a ragged mix of RGB and RGBA is
            # not something matplotlib will accept in one list.
            facecolors.append((*_shade(base, tri), 1.0))

    bb = assembly.bounding_box()
    spans = (bb.size.X, bb.size.Y, bb.size.Z)

    below_grade = bb.min.Z < -tolerance
    show_ground = below_grade if ground is None else ground
    x_lim = (bb.min.X, bb.max.X)
    y_lim = (bb.min.Y, bb.max.Y)
    if show_ground:
        ground_faces, ground_colors = _ground_faces(bb)
        faces.extend(ground_faces)
        facecolors.extend(ground_colors)
        xs = [x for face in ground_faces for x, _y, _z in face]
        ys = [y for face in ground_faces for _x, y, _z in face]
        x_lim = (min(xs), max(xs))
        y_lim = (min(ys), max(ys))
        spans = (x_lim[1] - x_lim[0], y_lim[1] - y_lim[0], bb.size.Z)

    n = len(views)
    cols = 2 if n > 1 else 1
    rows = (n + cols - 1) // cols
    fig = plt.figure(figsize=figsize)
    if title:
        fig.suptitle(title, fontsize=14)

    for index, view in enumerate(views):
        ax = fig.add_subplot(rows, cols, index + 1, projection="3d")
        # Edges are left off deliberately: the tessellation splits every
        # rectangular face into two triangles, so drawing edges puts an X
        # across every board.  Shading separates the faces instead.
        ax.add_collection3d(
            Poly3DCollection(
                faces, facecolors=facecolors, edgecolors="none", zsort="average"
            )
        )

        ax.set_xlim(*x_lim)
        ax.set_ylim(*y_lim)
        ax.set_zlim(bb.min.Z, bb.max.Z)
        ax.set_box_aspect(spans)
        ax.view_init(elev=view.elev, azim=view.azim)
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
