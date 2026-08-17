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
    "plywood_cherry": "#c47a54",
    "plywood_birch": "#e8d6b3",
    "plywood_baltic_birch": "#f0e2c4",
}

_FALLBACK_COLOR = "#9e9e9e"

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
    facecolors: list[tuple[float, float, float]] = []
    for part in parts:
        base = to_rgb(MATERIAL_COLORS.get(part.material, _FALLBACK_COLOR))
        vertices, triangles = part.tessellate(tolerance)
        for triangle in triangles:
            tri = [
                (vertices[i].X, vertices[i].Y, vertices[i].Z) for i in triangle
            ]
            faces.append(tri)
            facecolors.append(_shade(base, tri))

    bb = assembly.bounding_box()
    spans = (bb.size.X, bb.size.Y, bb.size.Z)

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

        ax.set_xlim(bb.min.X, bb.max.X)
        ax.set_ylim(bb.min.Y, bb.max.Y)
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
