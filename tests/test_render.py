"""Tests for woodshop.render — diagrams, 3-D views, and CAD export."""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "projects"))

from mysa_bed import SIZES, MysaBed  # noqa: E402

from woodshop.cutlist.extract import CutPart, extract  # noqa: E402
from woodshop.cutlist.hardwood import nest_hardwood  # noqa: E402
from woodshop.cutlist.optimize_2d import optimize_2d  # noqa: E402
from woodshop.inventory import Inventory  # noqa: E402
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


def _ground_polys(fig):
    """Return the ground quads drawn on the first axes of *fig*, if any."""
    from woodshop.render.model3d import GROUND_ALPHA

    out = []
    for ax in fig.axes:
        for collection in ax.collections:
            for colour in collection._facecolor3d:
                if abs(float(colour[3]) - GROUND_ALPHA) < 1e-6:
                    out.append(colour)
    return out


def test_a_model_that_goes_below_grade_gets_a_ground_plane():
    """A post four feet down is otherwise a stick hanging in space."""
    from build123d import Compound, Pos

    from woodshop.parts import Board

    post = Pos(0, 0, 0) * Board(
        length_mm=2438.4, nominal="4x4", material="white_cedar", label="post",
        rotation=(0, 90, 0),
    )
    buried = Compound(children=[post], label="post")
    assert buried.bounding_box().min.Z < 0
    fig = render_assembly(buried, views=(STANDARD_VIEWS[0],), close=False)
    try:
        assert _ground_polys(fig)
    finally:
        plt.close(fig)


def test_furniture_gets_no_slab_through_its_feet(bed):
    fig = render_assembly(bed.build(), views=(STANDARD_VIEWS[0],), close=False)
    try:
        assert not _ground_polys(fig)
    finally:
        plt.close(fig)


def test_the_ground_can_be_asked_for_or_refused(bed):
    on = render_assembly(
        bed.build(), views=(STANDARD_VIEWS[0],), ground=True, close=False
    )
    try:
        assert _ground_polys(on)
    finally:
        plt.close(on)


def test_the_ground_is_transparent_and_split_for_depth_sorting():
    from woodshop.render.model3d import GROUND_ALPHA, GROUND_GRID, _ground_faces

    class _BB:
        min = type("p", (), {"X": 0.0, "Y": 0.0, "Z": -1219.2})()
        max = type("p", (), {"X": 17678.4, "Y": 203.2, "Z": 1219.2})()
        size = type("s", (), {"X": 17678.4, "Y": 203.2, "Z": 2438.4})()

    faces, colours = _ground_faces(_BB())
    # Two triangles per quad, and enough quads that the painter's algorithm
    # sorts the ground locally rather than all at once.
    assert len(faces) == 2 * GROUND_GRID**2
    assert all(abs(c[3] - GROUND_ALPHA) < 1e-9 for c in colours)
    # It lies flat at grade, and reaches past a long thin fence on both sides.
    assert all(z == 0.0 for face in faces for _x, _y, z in face)
    ys = [y for face in faces for _x, y, _z in face]
    assert max(ys) - min(ys) > _BB.size.Y * 2
