"""Software z-buffer rasteriser for the shaded isometric view.

mplot3d's ``Poly3DCollection`` has no depth buffer: it sorts whole triangles
by average depth (``zsort="average"``), which is wrong wherever surfaces are
coincident or interleaved — the exact case a half-lap joint creates.  This
module replaces it with an ordinary per-pixel z-buffer, in pure numpy so the
projection and occlusion math is unit-testable on synthetic geometry with no
build123d or matplotlib import at all.

``model3d.py`` supplies world-space triangles already lit by its own
directional shading (one flat colour per triangle — this module does no
shading of its own) and world-space edge polylines for the seam overlay, and
gets back an RGB image plus the affine that maps a world point into that
image's pixels.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

__all__ = ["Camera", "Projection", "rasterize"]

#: Fraction of the scene diagonal a triangle must be nearer by to win a
#: coplanar tie.  Without it, two exactly flush faces — a half-lap's whole
#: reason for existing — speckle between their colours pixel by pixel as
#: floating-point noise flips the winner; with it, whichever part was
#: tessellated first (a stable, caller-controlled order) wins everywhere,
#: and the joint's seam is left to the edge overlay instead.
_TIE_FRACTION = 1e-6

#: How far behind the visible surface a true edge may sit and still be drawn
#: (world units; capped in absolute mm and also scaled to the scene, so it
#: tracks whichever is smaller). Far below any real stock thickness, so an
#: edge on a part one board-thickness further back stays hidden while a
#: flush seam — zero thickness away — still draws.
_EDGE_BIAS_MM = 1.0
_EDGE_BIAS_FRACTION = 1e-3


@dataclass(frozen=True)
class Camera:
    """An orthographic camera basis.

    Parameters
    ----------
    center : array_like
        World point the view is centred on — typically the assembly's
        bounding-box centre.
    right : array_like
        Unit vector spanning the image's horizontal axis.
    up : array_like
        Unit vector spanning the image's vertical axis.
    forward : array_like
        Unit vector pointing from the scene toward the eye.  Used as the
        depth axis, so depth increases toward the viewer, and for backface
        culling (a triangle facing away from the eye has ``normal · forward
        < 0``).
    """

    center: np.ndarray
    right: np.ndarray
    up: np.ndarray
    forward: np.ndarray

    def __post_init__(self) -> None:
        """Coerce every field to a float ndarray, so tuples work as input."""
        for name in ("center", "right", "up", "forward"):
            object.__setattr__(self, name, np.asarray(getattr(self, name), dtype=float))


@dataclass(frozen=True)
class Projection:
    """The affine mapping this render used from world coordinates to pixels.

    Parameters
    ----------
    camera : Camera
        The basis :func:`rasterize` projected with.
    u_min, v_min : float
        World-plane coordinate (in *camera*'s ``right``/``up`` axes) that
        maps to the image's bottom-left corner.
    scale : float
        Output pixels per world unit.
    width, height : int
        Output image size in pixels — matches the array :func:`rasterize`
        returns.
    """

    camera: Camera
    u_min: float
    v_min: float
    scale: float
    width: int
    height: int

    def to_pixel(self, point: Sequence[float]) -> tuple[float, float]:
        """Return the ``(column, row)`` pixel — row 0 at the top — for *point*.

        Parameters
        ----------
        point : array_like
            A world-space ``(x, y, z)``.

        Returns
        -------
        tuple of float
            Fractional pixel coordinates in the image :func:`rasterize`
            returned alongside this projection.  Not rounded, so a caller
            comparing against a pixel grid should do so itself.
        """
        rel = np.asarray(point, dtype=float) - self.camera.center
        u = float(rel @ self.camera.right)
        v = float(rel @ self.camera.up)
        col = (u - self.u_min) * self.scale
        row = self.height - (v - self.v_min) * self.scale
        return (col, row)


def _round_up_to_multiple(value: float, multiple: int) -> int:
    """Return the smallest multiple of *multiple* at least *value*."""
    return max(multiple, int(np.ceil(value / multiple)) * multiple)


def _scene_diagonal(triangles: np.ndarray, edges: Sequence[np.ndarray]) -> float:
    """Return the world-space bounding-box diagonal of *triangles* and *edges*."""
    chunks = [triangles.reshape(-1, 3)] if triangles.size else []
    chunks += [np.asarray(edge, dtype=float) for edge in edges if len(edge)]
    if not chunks:
        return 1.0
    points = np.concatenate(chunks, axis=0)
    span = points.max(axis=0) - points.min(axis=0)
    return float(np.linalg.norm(span)) or 1.0


def _project(points: np.ndarray, camera: Camera) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return ``(u, v, depth)`` for world *points* (``(..., 3)``) under *camera*."""
    rel = points - camera.center
    return rel @ camera.right, rel @ camera.up, rel @ camera.forward


def _rasterize_triangles(
    tri_px: np.ndarray,
    tri_py: np.ndarray,
    tri_depth: np.ndarray,
    colors: np.ndarray,
    zbuf: np.ndarray,
    img: np.ndarray,
    tie_eps: float,
) -> None:
    """Fill *zbuf* and *img* in place, one triangle's pixel window at a time."""
    height, width = zbuf.shape
    for i in range(len(tri_px)):
        xs, ys, zs = tri_px[i], tri_py[i], tri_depth[i]
        x0 = max(int(np.floor(xs.min())), 0)
        x1 = min(int(np.ceil(xs.max())), width - 1)
        y0 = max(int(np.floor(ys.min())), 0)
        y1 = min(int(np.ceil(ys.max())), height - 1)
        if x0 > x1 or y0 > y1:
            continue

        px, py = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        denom = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if denom == 0:
            continue
        w0 = ((ys[1] - ys[2]) * (px - xs[2]) + (xs[2] - xs[1]) * (py - ys[2])) / denom
        w1 = ((ys[2] - ys[0]) * (px - xs[2]) + (xs[0] - xs[2]) * (py - ys[2])) / denom
        w2 = 1.0 - w0 - w1
        inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not inside.any():
            continue

        depth = w0 * zs[0] + w1 * zs[1] + w2 * zs[2]
        window_z = zbuf[y0 : y1 + 1, x0 : x1 + 1]
        window_img = img[y0 : y1 + 1, x0 : x1 + 1]
        write = inside & (depth > window_z + tie_eps)
        if write.any():
            window_z[write] = depth[write]
            window_img[write] = colors[i]


def _rasterize_edges(
    edges: Sequence[np.ndarray],
    edge_colors: Sequence[Sequence[float]],
    camera: Camera,
    u_min: float,
    v_min: float,
    scale: float,
    zbuf: np.ndarray,
    img: np.ndarray,
    edge_bias: float,
) -> None:
    """Draw each polyline in *edges* over *img* where it is not behind *zbuf*."""
    height, width = zbuf.shape
    for polyline, color in zip(edges, edge_colors):
        points = np.asarray(polyline, dtype=float)
        if len(points) < 2:
            continue
        u, v, depth = _project(points, camera)
        px = (u - u_min) * scale
        py = height - (v - v_min) * scale

        # Densify to ~1 px spacing along the polyline's own projected length,
        # so a long straight rail edge is sampled as finely as a short one.
        seg_px = np.hypot(np.diff(px), np.diff(py))
        samples = max(2, int(np.ceil(seg_px.sum())) + 1)
        t = np.linspace(0.0, len(points) - 1, samples)
        idx = np.clip(np.floor(t).astype(int), 0, len(points) - 2)
        frac = t - idx

        def _interp(values: np.ndarray) -> np.ndarray:
            return values[idx] * (1 - frac) + values[idx + 1] * frac

        cols = np.round(_interp(px)).astype(int)
        rows = np.round(_interp(py)).astype(int)
        sample_depth = _interp(depth)

        valid = (cols >= 0) & (cols < width) & (rows >= 0) & (rows < height)
        cols, rows, sample_depth = cols[valid], rows[valid], sample_depth[valid]
        if not len(cols):
            continue
        visible = sample_depth > zbuf[rows, cols] - edge_bias
        img[rows[visible], cols[visible]] = color


def _downsample(img: np.ndarray, factor: int) -> np.ndarray:
    """Mean-pool *img* by *factor* in both dimensions — cheap antialiasing."""
    if factor == 1:
        return img
    h, w, c = img.shape
    return img.reshape(h // factor, factor, w // factor, factor, c).mean(axis=(1, 3))


def rasterize(
    triangles: np.ndarray,
    colors: np.ndarray,
    camera: Camera,
    edges: Sequence[np.ndarray] = (),
    edge_colors: Sequence[Sequence[float]] = (),
    size: int = 1000,
    supersample: int = 2,
    background: tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> tuple[np.ndarray, Projection]:
    """Render shaded *triangles* with a software z-buffer.

    Parameters
    ----------
    triangles : numpy.ndarray
        ``(n, 3, 3)`` world-space triangle vertices.
    colors : numpy.ndarray
        ``(n, 3)`` RGB in ``[0, 1]``, one flat colour per triangle — the
        caller has already lit each one (see ``model3d._shade``); this
        function does no shading.
    camera : Camera
        The orthographic view to project through.
    edges : sequence of numpy.ndarray, optional
        World-space polylines (``(k, 3)`` each), drawn over the shaded faces
        wherever they are not hidden — the part boundaries flat shading
        alone would erase, including a half-lap's flush seam.
    edge_colors : sequence of RGB, optional
        One colour per polyline in *edges*, same length as *edges*.
    size : int, optional
        Long side of the output image in pixels, default 1000.
    supersample : int, optional
        Internal oversampling factor, default 2, mean-pooled away before
        returning — the antialiasing budget.
    background : tuple of float, optional
        RGB fill for pixels no triangle covers, default white.

    Returns
    -------
    image : numpy.ndarray
        ``(h, w, 3)`` RGB float image in ``[0, 1]``.
    projection : Projection
        The world → pixel mapping this render used, so a caller can find
        where a 3-D point landed in *image*.
    """
    triangles = np.asarray(triangles, dtype=float)
    colors = np.asarray(colors, dtype=float)
    edges = list(edges)
    edge_colors = list(edge_colors)

    if triangles.size:
        normals = np.cross(
            triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]
        )
        keep = normals @ camera.forward > 0
        triangles, colors = triangles[keep], colors[keep]

    diagonal = _scene_diagonal(triangles, edges)
    tie_eps = _TIE_FRACTION * diagonal
    edge_bias = min(_EDGE_BIAS_MM, _EDGE_BIAS_FRACTION * diagonal)

    if triangles.size:
        tri_u, tri_v, tri_depth = _project(triangles, camera)
    else:
        tri_u = tri_v = tri_depth = np.empty((0, 3))
    u_chunks = [tri_u.ravel()] if tri_u.size else []
    v_chunks = [tri_v.ravel()] if tri_v.size else []
    for polyline in edges:
        u, v, _ = _project(np.asarray(polyline, dtype=float), camera)
        u_chunks.append(u)
        v_chunks.append(v)
    u_all = np.concatenate(u_chunks) if u_chunks else np.array([0.0, 1.0])
    v_all = np.concatenate(v_chunks) if v_chunks else np.array([0.0, 1.0])

    u_min, u_max = float(u_all.min()), float(u_all.max())
    v_min, v_max = float(v_all.min()), float(v_all.max())
    u_span = max(u_max - u_min, 1e-9)
    v_span = max(v_max - v_min, 1e-9)
    margin = 0.04 * max(u_span, v_span)
    u_min, v_min = u_min - margin, v_min - margin
    u_span, v_span = u_span + 2 * margin, v_span + 2 * margin

    work_long = size * supersample
    if u_span >= v_span:
        work_w = work_long
        work_h = _round_up_to_multiple(work_long * v_span / u_span, supersample)
    else:
        work_h = work_long
        work_w = _round_up_to_multiple(work_long * u_span / v_span, supersample)
    scale = work_w / u_span

    zbuf = np.full((work_h, work_w), -np.inf)
    img = np.empty((work_h, work_w, 3))
    img[:] = background

    if triangles.size:
        tri_px = (tri_u - u_min) * scale
        tri_py = work_h - (tri_v - v_min) * scale
        _rasterize_triangles(tri_px, tri_py, tri_depth, colors, zbuf, img, tie_eps)

    if edges:
        _rasterize_edges(
            edges, edge_colors, camera, u_min, v_min, scale, zbuf, img, edge_bias
        )

    final = _downsample(img, supersample)
    projection = Projection(
        camera=camera,
        u_min=u_min,
        v_min=v_min,
        scale=scale / supersample,
        width=final.shape[1],
        height=final.shape[0],
    )
    return final, projection
