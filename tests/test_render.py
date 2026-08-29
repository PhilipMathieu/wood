"""Tests for woodshop.render — diagrams, 3-D views, and CAD export."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import numpy as np
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "projects"))

from mysa_bed import SIZES, MysaBed  # noqa: E402

from woodshop.cutlist.extract import CutPart, extract  # noqa: E402
from woodshop.cutlist.hardwood import nest_hardwood  # noqa: E402
from woodshop.cutlist.optimize_2d import optimize_2d  # noqa: E402
from woodshop.inventory import Inventory  # noqa: E402
from woodshop.parts import Board  # noqa: E402
from woodshop.render import (  # noqa: E402
    export_assembly,
    render_assembly,
    render_board_diagram,
    render_sheet_diagram,
    save_figures,
)
from woodshop.render.sheets import cut_sequence  # noqa: E402

_IN = 25.4
SHEET_W, SHEET_H = 48 * _IN, 96 * _IN


@pytest.fixture(autouse=True)
def _no_leaked_figures():
    """Every renderer must clean up after itself."""
    plt.close("all")
    yield
    assert not plt.get_fignums(), "a renderer left figures open"


@pytest.fixture(scope="module")
def bed():
    return MysaBed(size=SIZES["queen"])


def _panels(qty=6):
    return [CutPart("shelf", "plywood_birch", "length", 600.0, 300.0, 18.25, qty=qty)]


# ---------------------------------------------------------------------------
# Figure hygiene — the bug that prompted this module
# ---------------------------------------------------------------------------


def test_sheet_diagram_closes_its_figures():
    """Regression: figures were never closed, tripping matplotlib's warning."""
    result = optimize_2d(_panels(40), sheet_w_mm=SHEET_W, sheet_h_mm=SHEET_H)
    render_sheet_diagram(result)
    assert not plt.get_fignums()


def test_sheet_diagram_closes_figures_when_writing_pdf(tmp_path):
    result = optimize_2d(_panels(), sheet_w_mm=SHEET_W, sheet_h_mm=SHEET_H)
    render_sheet_diagram(result, output_pdf=tmp_path / "s.pdf")
    assert (tmp_path / "s.pdf").stat().st_size > 0
    assert not plt.get_fignums()


def test_figures_can_be_kept_open_deliberately():
    result = optimize_2d(_panels(), sheet_w_mm=SHEET_W, sheet_h_mm=SHEET_H)
    figs = render_sheet_diagram(result, close=False)
    assert plt.get_fignums()
    for fig in figs:
        plt.close(fig)


# ---------------------------------------------------------------------------
# Layout diagrams
# ---------------------------------------------------------------------------


def test_sheet_diagram_draws_one_figure_per_sheet():
    result = optimize_2d(_panels(60), sheet_w_mm=SHEET_W, sheet_h_mm=SHEET_H)
    assert result.sheets_used > 1
    figs = render_sheet_diagram(result, close=False)
    assert len(figs) == result.sheets_used
    for fig in figs:
        plt.close(fig)


def test_sheet_diagram_defaults_to_the_size_on_the_result():
    result = optimize_2d(_panels(), sheet_w_mm=SHEET_W, sheet_h_mm=SHEET_H)
    figs = render_sheet_diagram(result, close=False)
    ax = figs[0].axes[0]
    assert ax.get_xlim() == (0, SHEET_W)
    plt.close(figs[0])


def test_board_diagram_draws_every_board(bed):
    """Regression: hardwood nesting had no renderer at all."""
    parts = extract(bed.build())
    sheet_materials = {s.material for s in bed.inventory.sheet_goods}
    solid = [p for p in parts if p.material not in sheet_materials]
    plan = nest_hardwood(solid, bed.inventory, "cherry")
    figs = render_board_diagram(plan, close=False)
    assert len(figs) == plan.boards_needed > 0
    for fig in figs:
        plt.close(fig)


def test_board_diagram_writes_a_pdf(tmp_path):
    parts = [CutPart("slat", "cherry", "length", 1587.5, 63.5, 19.05, qty=8)]
    plan = nest_hardwood(parts, Inventory.load(), "cherry")
    render_board_diagram(plan, output_pdf=tmp_path / "b.pdf")
    assert (tmp_path / "b.pdf").stat().st_size > 0


# ---------------------------------------------------------------------------
# Cut order
# ---------------------------------------------------------------------------


def test_cut_sequence_describes_crosscuts_then_rips():
    result = optimize_2d(_panels(4), sheet_w_mm=SHEET_W, sheet_h_mm=SHEET_H)
    steps = cut_sequence(result)
    assert any("crosscut" in s for s in steps)
    assert any("rip that strip into" in s for s in steps)


def test_cut_sequence_covers_every_placed_part():
    result = optimize_2d(_panels(7), sheet_w_mm=SHEET_W, sheet_h_mm=SHEET_H)
    text = "\n".join(cut_sequence(result))
    assert text.count("shelf") == len(result.placements)


def test_cut_sequence_of_an_empty_result_is_empty():
    assert cut_sequence(optimize_2d([], sheet_w_mm=SHEET_W, sheet_h_mm=SHEET_H)) == []


# ---------------------------------------------------------------------------
# 3-D views and export
# ---------------------------------------------------------------------------


def test_render_assembly_writes_a_png(bed, tmp_path):
    render_assembly(bed.build(), output_png=tmp_path / "bed.png")
    assert (tmp_path / "bed.png").stat().st_size > 0


def test_render_assembly_draws_one_axes_per_view(bed):
    from woodshop.render.model3d import STANDARD_VIEWS

    fig = render_assembly(bed.build(), close=False)
    assert len(fig.axes) == len(STANDARD_VIEWS)
    plt.close(fig)


def test_a_long_low_assembly_is_not_clipped(tmp_path):
    """Regression: the 80" console lost its right-hand end in the elevations.

    mplot3d honoured the ratio of a plot box's spans and not their size, so a
    long thin box ran off the axes and was clipped without a word. Both
    renderers now use plain 2-D axes, which autoscale to whatever they are
    given — encode that as a border-pixel check so it holds for the
    hidden-line views and the shaded raster alike.
    """
    board = Board(
        length_mm=2032.0, material="cherry", label="plank",
        thickness_mm=19.05, width_mm=330.2,
    )
    png = tmp_path / "long.png"
    render_assembly(board, output_png=png, figsize=(10.0, 3.0))

    image = matplotlib.image.imread(png)
    border = np.concatenate(
        [image[0, :, :3], image[-1, :, :3], image[:, 0, :3], image[:, -1, :3]]
    )
    assert np.all(border > 0.98), "a clipped drawing would touch the image border"


def test_render_assembly_rejects_an_empty_assembly():
    from build123d import Box, Compound

    with pytest.raises(ValueError, match="no Board/Panel parts"):
        render_assembly(Compound(children=[Box(1, 1, 1)]))


def test_export_writes_step_and_stl(bed, tmp_path):
    written = export_assembly(
        bed.build(), output_step=tmp_path / "b.step", output_stl=tmp_path / "b.stl"
    )
    assert len(written) == 2
    assert all(p.stat().st_size > 0 for p in written)


# ---------------------------------------------------------------------------
# What drawing the model actually caught
# ---------------------------------------------------------------------------


def test_only_joinery_parts_interpenetrate(bed):
    """Parts may overlap only where a joint says they should.

    Rendering the bed raised the question of whether anything was buried
    inside anything else.  It is not, and in this bed there is exactly one
    overlap that should exist: the headboard panel housed into the stiles.
    Everything else *meets* rather than interpenetrates — the slats sit on the
    ledgers, the rails sit on the foot legs, and the rails butt the stiles
    where the metal brackets go.
    """
    from woodshop.render.model3d import _iter_leaf_parts

    parts = list(_iter_leaf_parts(bed.build()))
    boxes = [(p.label, p.bounding_box()) for p in parts]
    tol = 0.01

    clashes = set()
    for i, (label_a, a) in enumerate(boxes):
        for label_b, b in boxes[i + 1:]:
            if (
                min(a.max.X, b.max.X) - max(a.min.X, b.min.X) > tol
                and min(a.max.Y, b.max.Y) - max(a.min.Y, b.min.Y) > tol
                and min(a.max.Z, b.max.Z) - max(a.min.Z, b.min.Z) > tol
            ):
                clashes.add(tuple(sorted((label_a, label_b))))

    assert clashes == {("head_stile", "headboard_panel")}


def test_plan_view_hides_what_the_slats_cover(bed):
    """HLR must dash the rail under the slats, not draw it over them.

    This is the bug issue #10 is named for: the painter's algorithm drew the
    centre rail's triangles over the slats that actually cover it, because it
    sorts by *triangle*, not by pixel. A visible-edge sample landing inside a
    slat's own footprint would mean something is drawing through the slat;
    the rail's edges belong in the hidden set there instead.
    """
    from woodshop.render.hlr import hlr_polylines
    from woodshop.render.model3d import _camera_basis, _direction, _iter_leaf_parts

    assembly = bed.build()
    direction = _direction(90.0, -90.0)
    up_hint, _, _ = _camera_basis(direction)
    visible, hidden = hlr_polylines(assembly, direction, up_hint)

    margin = 2.0  # mm — stay off each slat's own silhouette edge
    footprints = []
    for slat in _iter_leaf_parts(assembly):
        if slat.label != "slat":
            continue
        bb = slat.bounding_box()
        footprints.append(
            (bb.min.X + margin, bb.max.X - margin, bb.min.Y + margin, bb.max.Y - margin)
        )
    assert footprints, "the bed fixture should have slats to hide things under"

    def _covered(point: np.ndarray) -> bool:
        x, y = point
        return any(x0 < x < x1 and y0 < y < y1 for x0, x1, y0, y1 in footprints)

    assert not any(_covered(p) for edge in visible for p in edge)
    assert any(_covered(p) for edge in hidden for p in edge), (
        "the rail should be hidden under the slats, not simply missing"
    )


def test_iso_view_shows_slat_color_over_the_rail_crossing():
    """The z-buffer must paint the nearer slat, not the rail underneath it.

    The plywood variant is used rather than the shared ``bed`` fixture
    because the faithful variant builds the slats from the same species as
    the frame — nothing to tell apart by colour. (The console has the
    opposite problem: its shelves and uprights share one material too, which
    is why its interlock is checked with the raster unit tests instead.)
    """
    from matplotlib.colors import to_rgb

    from woodshop.render.model3d import (
        MATERIAL_COLORS,
        _camera_basis,
        _direction,
        _iter_leaf_parts,
        _tessellate,
    )
    from woodshop.render.raster import Camera, rasterize

    plywood_bed = MysaBed(size=SIZES["queen"], variant="plywood").build()
    parts = list(_iter_leaf_parts(plywood_bed))
    triangles, colors, edges, edge_colors = _tessellate(parts, tolerance=0.5)

    direction = _direction(22.0, -55.0)
    _, right, up = _camera_basis(direction)
    center = plywood_bed.bounding_box().center()
    camera = Camera(center=(center.X, center.Y, center.Z), right=right, up=up, forward=direction)
    image, projection = rasterize(
        triangles, colors, camera, edges=edges, edge_colors=edge_colors, size=1000
    )

    rail = next(p for p in parts if p.label == "centre_rail")
    slat = next(
        p
        for p in parts
        if p.label == "slat" and p.bounding_box().min.Y < rail.bounding_box().max.Y
    )
    rail_bb, slat_bb = rail.bounding_box(), slat.bounding_box()
    crossing = (0.0, (slat_bb.min.Y + slat_bb.max.Y) / 2, slat_bb.max.Z)
    assert rail_bb.min.X < crossing[0] < rail_bb.max.X, "sanity: the point sits over the rail"

    col, row = projection.to_pixel(crossing)
    pixel = image[int(round(row)), int(round(col))]
    birch = np.array(to_rgb(MATERIAL_COLORS["plywood_baltic_birch"]))
    cherry = np.array(to_rgb(MATERIAL_COLORS["cherry"]))
    assert np.linalg.norm(pixel - birch) < np.linalg.norm(pixel - cherry)


def test_front_view_has_visible_and_hidden_line_work(bed):
    """Both hidden-line collections carry geometry for an ordinary view."""
    from woodshop.render.hlr import hlr_polylines
    from woodshop.render.model3d import _camera_basis, _direction

    assembly = bed.build()
    direction = _direction(0.0, -90.0)
    up_hint, _, _ = _camera_basis(direction)
    visible, hidden = hlr_polylines(assembly, direction, up_hint)
    assert visible
    assert hidden


def test_hlr_of_two_stacked_boxes_shows_only_the_top_ones_outline():
    """A minimal, non-project regression for whole-compound occlusion.

    A small box sits entirely under a larger one; viewed from above, the
    larger box's footprint covers it completely, so the visible outline must
    be the top box's alone, with the bottom box's edges relegated to the
    hidden set rather than drawn (the exact bug: a per-part projection would
    draw both outlines, since it never sees the other part to be hidden by).
    """
    from build123d import Box, Compound, Location

    from woodshop.render.hlr import hlr_polylines

    bottom = Box(60.0, 60.0, 10.0)
    top = Box(100.0, 100.0, 20.0).located(Location((0, 0, 20.0)))
    assembly = Compound(children=[bottom, top])

    # Looking straight down (+Z toward the eye), Y as the viewport's "up".
    visible, hidden = hlr_polylines(assembly, direction=(0.0, 0.0, 1.0), up=(0.0, 1.0, 0.0))

    visible_points = np.concatenate(visible)
    assert visible_points[:, 0].min() == pytest.approx(-50.0, abs=0.5)
    assert visible_points[:, 0].max() == pytest.approx(50.0, abs=0.5)
    assert not any(-30.0 < x < 30.0 and -30.0 < y < 30.0 for x, y in visible_points)
    assert hidden


def test_centre_rail_sits_below_the_slats(bed):
    """The plan view suggests otherwise; that is a depth-sorting artifact."""
    from woodshop.render.model3d import _iter_leaf_parts

    tops = {
        p.label: p.bounding_box().max.Z
        for p in _iter_leaf_parts(bed.build())
    }
    assert tops["centre_rail"] <= tops["slat"] - 19.0


# ---------------------------------------------------------------------------
# Per-figure images, for anything that cannot embed a PDF
# ---------------------------------------------------------------------------


def test_save_figures_writes_one_image_per_sheet(tmp_path):
    result = optimize_2d(_panels(60), sheet_w_mm=SHEET_W, sheet_h_mm=SHEET_H)
    figs = render_sheet_diagram(result, close=False)
    written = save_figures(figs, tmp_path, "sheets")
    assert len(written) == result.sheets_used > 1
    assert [p.name for p in written][:2] == ["sheets-1.png", "sheets-2.png"]
    assert all(p.stat().st_size > 0 for p in written)
    assert not plt.get_fignums(), "save_figures closes what it writes"


def test_save_figures_can_write_svg(tmp_path):
    result = optimize_2d(_panels(), sheet_w_mm=SHEET_W, sheet_h_mm=SHEET_H)
    written = save_figures(
        render_sheet_diagram(result, close=False), tmp_path, "s", ext="svg"
    )
    assert written[0].read_text(encoding="utf-8").lstrip().startswith("<?xml")


def test_save_figures_creates_the_directory(tmp_path):
    result = optimize_2d(_panels(), sheet_w_mm=SHEET_W, sheet_h_mm=SHEET_H)
    out = tmp_path / "deep" / "nested"
    assert save_figures(render_sheet_diagram(result, close=False), out, "s")[0].is_file()


# ---------------------------------------------------------------------------
# Orientation
# ---------------------------------------------------------------------------


def test_a_long_thin_board_is_drawn_lying_down():
    """A 6" x 10 ft board standing up is a ribbon four pages tall."""
    parts = [CutPart("rail", "cherry", "length", 600.0, 85.0, 19.05, qty=8)]
    plan = nest_hardwood(parts, Inventory.load(), "cherry")
    figs = render_board_diagram(plan, close=False)
    ax = figs[0].axes[0]
    assert ax.get_xlim()[1] > ax.get_ylim()[1]
    assert "length" in ax.get_xlabel()
    for fig in figs:
        plt.close(fig)


def test_a_sheet_is_left_standing_up():
    result = optimize_2d(_panels(), sheet_w_mm=SHEET_W, sheet_h_mm=SHEET_H)
    ax = render_sheet_diagram(result, close=False)[0].axes[0]
    assert ax.get_xlim() == (0, SHEET_W)
    assert "width" in ax.get_xlabel()
    plt.close(ax.figure)


# ---------------------------------------------------------------------------
# Shaped parts in the layout
# ---------------------------------------------------------------------------


def _disc(diameter_mm=400.0):
    import math

    blank = diameter_mm + 6.35
    return CutPart(
        "top", "plywood_birch", "none", blank, blank, 18.25,
        shape="round", finished_area_each_mm2=math.pi * diameter_mm**2 / 4,
    )


def test_a_round_part_is_drawn_as_a_circle_inside_its_blank():
    import matplotlib.patches as mpatches

    result = optimize_2d([_disc()], sheet_w_mm=SHEET_W, sheet_h_mm=SHEET_H)
    ax = render_sheet_diagram(result, close=False)[0].axes[0]
    circles = [p for p in ax.patches if isinstance(p, mpatches.Circle)]
    assert len(circles) == 1
    assert circles[0].get_radius() == pytest.approx(200.0, abs=0.1)
    plt.close(ax.figure)


def test_a_rectangular_part_gets_no_outline():
    import matplotlib.patches as mpatches

    result = optimize_2d(_panels(1), sheet_w_mm=SHEET_W, sheet_h_mm=SHEET_H)
    ax = render_sheet_diagram(result, close=False)[0].axes[0]
    assert not [p for p in ax.patches if isinstance(p, mpatches.Circle)]
    plt.close(ax.figure)


def test_the_subtitle_admits_the_shavings():
    result = optimize_2d([_disc()], sheet_w_mm=SHEET_W, sheet_h_mm=SHEET_H)
    title = render_sheet_diagram(result, close=False)[0].axes[0].get_title()
    assert "finished" in title
    plt.close(plt.gcf())


# ---------------------------------------------------------------------------
# The cut-list table
# ---------------------------------------------------------------------------


def test_the_shape_column_appears_only_when_something_is_not_a_rectangle():
    from woodshop.render import render_cut_list

    rectangles = render_cut_list(_panels(2))
    assert "shape" not in rectangles.columns

    shaped = render_cut_list([_disc()])
    assert "shape" in shaped.columns
    assert "round" in shaped["shape"].iloc[0]
