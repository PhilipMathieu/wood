"""Cut real volume overlaps out of the mesh before the shaded raster sees them.

``raster.py``'s z-buffer is exact wherever two meshes merely *touch* — a
half-lap's flush faces are a coincidence-of-depth problem, and the module's
own tie epsilon resolves it with no speckle. It has no answer for two solids
that genuinely *interpenetrate*: a housed joint modelled without the boolean
cut that would actually remove the housed member's silhouette from the part
it sits in. There, two independently-tessellated meshes cross along a true
3-D curve that lines up with neither mesh's own triangulation, and the
z-buffer's ordinary (non-tied) depth comparison flips winners at whatever
resolution the tessellation happens to facet that curve at — a jagged seam,
not a clean one.

This module finds any such pair and performs the cut the model itself never
did, using the exact OCCT boolean already available through build123d — the
same kernel :mod:`woodshop.render.hlr` already trusts for hidden-line removal
on this same geometry. The result is render-time only: it never mutates or
replaces the parts the caller passed in, so cut lists, checks, and every
other consumer of the real assembly are unaffected.

The one part of this that is a judgement call rather than a derivation is
*which* part of an interpenetrating pair loses the shared volume — see
:func:`trim_interpenetrations`'s docstring.
"""

from __future__ import annotations

from typing import Any, Sequence

__all__ = ["trim_interpenetrations"]


def _boxes_overlap(a: Any, b: Any, tolerance_mm: float) -> bool:
    """Return whether bounding boxes *a* and *b* overlap by more than *tolerance_mm*.

    The same three-axis test :func:`~tests.test_render.test_only_joinery_\
parts_interpenetrate` pins independently — a cheap prefilter, not proof of a
    real overlap, since two boxes can clash while the solids inside them
    only touch or miss entirely.
    """
    return (
        min(a.max.X, b.max.X) - max(a.min.X, b.min.X) > tolerance_mm
        and min(a.max.Y, b.max.Y) - max(a.min.Y, b.min.Y) > tolerance_mm
        and min(a.max.Z, b.max.Z) - max(a.min.Z, b.min.Z) > tolerance_mm
    )


def trim_interpenetrations(
    parts: Sequence[Any],
    bbox_tolerance_mm: float = 0.01,
    volume_tolerance_mm3: float = 1e-3,
) -> list[Any]:
    """Return *parts* with any genuine volume overlap cut out of the smaller part.

    Parts that only touch — a half-lap's flush faces, anything
    :meth:`~build123d.topology.shape_core.Shape.intersect` reports as
    ``None`` rather than a solid of positive volume — are left in the
    returned list untouched and unchanged (same object, not a copy); this
    function is a no-op wherever there is nothing to cut, which today is
    every joint in this repository but one.

    Where two parts really do interpenetrate, the **smaller of the two by
    volume has the intersection subtracted from it**; the larger part is
    returned as-is. There is no rule that gets this right for every possible
    joint — a shelf let into the side of a bookcase would want the opposite
    (the larger case side is the one that should show a housing) — so this
    is a stated default, not a law: a broad, thin member spanning a
    narrower one (a headboard panel over a stile, a case top over a leg) is
    conventionally read as the continuous part, with the narrower member
    relieved to let it pass, and "smaller volume yields" recovers that
    reading without hard-coding which labels are involved. A future joint
    where this default is wrong belongs fixed in the model — a real
    ``A - B`` cut at the call site, the same two-line fix
    :mod:`woodshop.parts` already recommends for exactly this reason — not
    patched further here.

    Parameters
    ----------
    parts : sequence
        Leaf parts, e.g. from :func:`woodshop.render.model3d._iter_leaf_parts`.
        Never mutated: every returned entry is either the original object
        (nothing to cut) or a new solid produced by subtraction.
    bbox_tolerance_mm : float, optional
        How far two bounding boxes must overlap on every axis before the
        expensive exact boolean check runs at all, default 0.01 mm.
    volume_tolerance_mm3 : float, optional
        Minimum intersection volume to treat as a real overlap rather than
        floating-point noise on an intended-flush joint, default 1e-3 mm³.

    Returns
    -------
    list
        *parts*, in the same order, with any genuinely overlapping member
        replaced by its trimmed copy.
    """
    parts = list(parts)
    boxes = [part.bounding_box() for part in parts]

    # Cuts accumulate per loser, keyed by index, and are only ever computed
    # against the ORIGINAL geometry (parts[i], parts[j] — never an
    # already-trimmed copy). A part can lose volume to more than one
    # neighbour (the bed's panel overlaps both stiles), and checking the
    # pristine solids avoids the order-dependence a running trim would
    # introduce: whichever pair happened to be resolved first would
    # otherwise change what a later pair sees.
    losers: dict[int, list[Any]] = {}
    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            if not _boxes_overlap(boxes[i], boxes[j], bbox_tolerance_mm):
                continue
            intersection = parts[i].intersect(parts[j])
            if intersection is None:
                continue
            solids = list(intersection)
            volume = sum(solid.volume for solid in solids)
            if volume <= volume_tolerance_mm3:
                continue
            # Strict "<" so an exact tie favours the earlier index, matching
            # raster.py's own "earlier part wins" convention for coincident
            # geometry.
            loser = i if parts[i].volume < parts[j].volume else j
            losers.setdefault(loser, []).extend(solids)

    if not losers:
        return parts

    trimmed = list(parts)
    for idx, cut_solids in losers.items():
        original = parts[idx]
        result = original
        for solid in cut_solids:
            result = result - solid
        result.material = original.material
        trimmed[idx] = result
    return trimmed
