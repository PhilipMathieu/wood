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
    STANDARD_VIEWS,
    export_assembly,
    render_assembly,
    render_board_diagram,
    render_cut_list,
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


def _bbox_clashes(parts, tol=0.01):
    """Return the set of label pairs whose bounding boxes overlap by more than *tol*."""
    from woodshop.render.trim import _boxes_overlap

    boxes = [(p.label, p.bounding_box()) for p in parts]
    clashes = set()
    for i, (label_a, a) in enumerate(boxes):
        for label_b, b in boxes[i + 1 :]:
            if _boxes_overlap(a, b, tol):
                clashes.add(tuple(sorted((label_a, label_b))))
    return clashes


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
    assert _bbox_clashes(parts) == {("head_stile", "headboard_panel")}


def test_trimming_removes_the_one_real_interpenetration(bed):
    """The render-time boolean trim leaves nothing volumetrically overlapping.

    This is the geometric ground truth behind the isometric's jagged seam at
    the headboard: two independently-tessellated meshes crossing along a real
    3-D curve, which is exactly what :func:`woodshop.render.trim.\
trim_interpenetrations` removes before the shaded raster ever tessellates the
    parts. A bounding-box check isn't enough here — cutting a corner off the
    stile doesn't necessarily shrink its *box* — so this checks the exact
    boolean :meth:`~build123d.topology.shape_core.Shape.intersect` the trim
    itself relies on. Once this passes, the raster's input geometry no longer
    volumetrically overlaps anywhere, and the z-buffer's existing coincident-
    face handling (`_TIE_FRACTION`) is the only case left for it to resolve.
    """
    from woodshop.render.model3d import _iter_leaf_parts
    from woodshop.render.trim import trim_interpenetrations

    parts = list(_iter_leaf_parts(bed.build()))
    stile = next(p for p in parts if p.label == "head_stile")
    panel = next(p for p in parts if p.label == "headboard_panel")
    assert stile.intersect(panel) is not None  # the bug this trim exists for

    trimmed = trim_interpenetrations(parts)
    trimmed_stiles = [p for p in trimmed if p.label == "head_stile"]
    trimmed_panel = next(p for p in trimmed if p.label == "headboard_panel")
    for trimmed_stile in trimmed_stiles:
        assert trimmed_stile.intersect(trimmed_panel) is None


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
    """Pin the geometry the plan view's hidden-line dashes now show correctly."""
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


def test_the_stock_column_appears_only_when_a_part_names_its_nominal_size():
    milled = CutPart(
        "picket", "white_cedar", "length", 1168.4, 130.2, 19.05, qty=60,
        nominal="1x6", grade="STK", stock_profile="tongue & groove, dressed",
    )
    plain = CutPart("slat", "cherry", "length", 1587.5, 63.5, 19.05, qty=16)

    assert "stock" not in render_cut_list([plain]).columns

    df = render_cut_list([milled])
    assert df["stock"].iloc[0] == "1x6 tongue & groove, dressed (STK)"
    # The width column is what it covers; the stock column is what to order,
    # and a shop given only the first would go looking for 5-1/8" boards.
    assert df["width"].iloc[0] == "5-1/8\""


# ---------------------------------------------------------------------------
# The ground, for the models that are in it
# ---------------------------------------------------------------------------


class _FenceBB:
    """A bounding box shaped like the fence: long, thin, and half underground."""

    min = type("p", (), {"X": 0.0, "Y": 0.0, "Z": -1219.2})()
    max = type("p", (), {"X": 17678.4, "Y": 203.2, "Z": 1219.2})()
    size = type("s", (), {"X": 17678.4, "Y": 203.2, "Z": 2438.4})()


def test_a_model_that_goes_below_grade_gets_a_ground_plane():
    """A post four feet down is otherwise a stick hanging in space."""
    from build123d import Compound, Pos

    from woodshop.parts import Board
    from woodshop.render.model3d import wants_ground

    post = Pos(0, 0, 0) * Board(
        length_mm=2438.4, nominal="4x4", material="white_cedar", label="post",
        rotation=(0, 90, 0),
    )
    buried = Compound(children=[post], label="post")
    assert buried.bounding_box().min.Z < 0
    assert wants_ground(buried.bounding_box(), None)
    # And it renders with one, in the shaded view.
    fig = render_assembly(buried, views=(STANDARD_VIEWS[0],), close=False)
    plt.close(fig)


def test_furniture_gets_no_slab_through_its_feet(bed):
    from woodshop.render.model3d import wants_ground

    assert not wants_ground(bed.build().bounding_box(), None)


def test_the_ground_can_be_asked_for_or_refused(bed):
    from woodshop.render.model3d import wants_ground

    bb = bed.build().bounding_box()
    assert wants_ground(bb, True)
    assert not wants_ground(_FenceBB(), False)


def test_the_ground_lies_at_grade_and_reaches_past_a_thin_fence():
    from matplotlib.colors import to_rgb

    from woodshop.render.model3d import GROUND_ALPHA, GROUND_COLOR, _ground_triangles

    triangles, colours = _ground_triangles(_FenceBB())
    assert triangles.shape == (2, 3, 3)
    assert (triangles[..., 2] == 0.0).all()
    ys = triangles[..., 1]
    assert ys.max() - ys.min() > _FenceBB.size.Y * 2
    # Opaque in the raster, so the colour is the ground laid over white.
    expected = GROUND_ALPHA * np.array(to_rgb(GROUND_COLOR)) + (1 - GROUND_ALPHA)
    assert np.allclose(colours[0], expected)


def test_configurations_draw_one_row_each(tmp_path):
    from build123d import Compound, Pos

    from woodshop.parts import Board
    from woodshop.render import render_configurations

    def post(height):
        return Compound(
            children=[
                Pos(0, 0, height / 2 - 600)
                * Board(
                    length_mm=height, nominal="4x4", material="white_cedar",
                    label="post", rotation=(0, 90, 0),
                )
            ],
            label="post",
        )

    out = tmp_path / "configs.png"
    fig = render_configurations(
        [("short", post(1500)), ("tall", post(2400))],
        output_png=out,
        views=(STANDARD_VIEWS[0], STANDARD_VIEWS[1]),
        close=False,
    )
    try:
        assert out.exists()
        assert len(fig.axes) == 4
        assert fig.axes[0].get_title() == "short — isometric"
        assert fig.axes[3].get_title() == "tall — front"
    finally:
        plt.close(fig)
    with pytest.raises(ValueError):
        render_configurations([])


def test_the_shaded_view_clips_what_is_below_grade():
    from build123d import Pos

    from woodshop.parts import Board
    from woodshop.render.model3d import _clip_below_grade

    buried = Pos(0, 0, 0) * Board(
        length_mm=2000, nominal="4x4", material="white_cedar", label="post",
        rotation=(0, 90, 0),
    )
    above = Pos(0, 0, 2000) * Board(
        length_mm=500, nominal="4x4", material="white_cedar", label="cap",
        rotation=(0, 90, 0),
    )
    bb = buried.bounding_box()
    clipped = _clip_below_grade([buried, above], bb, 0.5)
    assert clipped[1] is above  # untouched, the same object
    assert clipped[0].bounding_box().min.Z == pytest.approx(0.0, abs=1e-3)
    assert clipped[0].material == "white_cedar"
    assert buried.bounding_box().min.Z < 0  # the caller's part is not mutated
