"""Tests for the media console — the piece that is nothing but a dado grid."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "projects"))

from media_console import (  # noqa: E402
    CD_CASE_D_IN,
    CD_CASE_H_IN,
    IN,
    LP_SLEEVE_IN,
    MediaConsole,
)

from woodshop.checks import Severity  # noqa: E402
from woodshop.cutlist.extract import extract  # noqa: E402
from woodshop.cutlist.hardwood import nest_hardwood  # noqa: E402
from woodshop.cutlist.optimize_2d import pack_by_material  # noqa: E402
from woodshop.render.model3d import _iter_leaf_parts  # noqa: E402


@pytest.fixture(scope="module")
def console() -> MediaConsole:
    return MediaConsole()


@pytest.fixture(scope="module")
def assembly(console):
    return console.build()


@pytest.fixture(scope="module")
def parts(assembly):
    return extract(assembly)


def _boxes(assembly) -> dict[str, list]:
    """Return every placed part's bounding box, grouped by label."""
    out: dict[str, list] = {}
    for part in _iter_leaf_parts(assembly):
        out.setdefault(part.label, []).append(part.bounding_box())
    return out


# ---------------------------------------------------------------------------
# The published envelope, and the openings it has to contain
# ---------------------------------------------------------------------------


def test_it_is_eighty_by_twenty_four_by_thirteen(assembly):
    bb = assembly.bounding_box()
    assert bb.size.X == pytest.approx(80 * IN, abs=0.1)
    assert bb.size.Y == pytest.approx(13 * IN, abs=0.1)
    assert bb.size.Z == pytest.approx(24 * IN, abs=0.1)


def test_the_openings_measure_what_the_brief_asked_for(console, assembly):
    """The two heights are held exactly; the plywood pays for it elsewhere."""
    boxes = _boxes(assembly)
    bay_bottom_top = boxes["bay_bottom"][0].max.Z
    cd_shelf = boxes["cd_shelf"][0]
    top_underside = boxes["top"][0].min.Z

    assert cd_shelf.min.Z - bay_bottom_top == pytest.approx(13.5 * IN, abs=0.05)
    assert top_underside - cd_shelf.max.Z == pytest.approx(8.0 * IN, abs=0.05)


def test_the_bays_come_out_wider_than_fifteen_because_the_plywood_is_thin(console):
    """45/64" stock leaves 5/32" more opening than a true 3/4" would."""
    assert console.panel_t == pytest.approx(45 / 64 * IN)
    assert console.bay_clear_w == pytest.approx(
        (console.overall_w - 6 * console.panel_t) / 5
    )
    assert 15 * IN < console.bay_clear_w < 15.25 * IN


def test_the_leftover_height_becomes_a_toe_reveal(console, assembly):
    """Three panels of 45/64" give back 3/8" of the 24"; it goes to the floor."""
    boxes = _boxes(assembly)
    assert console.toe_reveal == pytest.approx(0.390625 * IN, abs=0.01)
    assert boxes["bay_bottom"][0].min.Z == pytest.approx(console.toe_reveal, abs=0.05)
    # The case stands on the verticals, not on a bottom panel.
    assert min(b.min.Z for b in boxes["side"]) == pytest.approx(0.0, abs=0.01)
    assert min(b.min.Z for b in boxes["divider"]) == pytest.approx(0.0, abs=0.01)


def test_a_record_sits_inside_the_bay_in_all_three_directions(console):
    sleeve = LP_SLEEVE_IN * IN
    assert console.bay_clear_w > sleeve
    assert console.record_bay_h_in * IN > sleeve
    assert console.overall_d > sleeve


def test_the_cd_row_takes_jewel_cases_two_deep(console):
    assert console.cd_ranks == 2
    assert 2 * CD_CASE_D_IN * IN < console.overall_d
    assert console.cd_row_h_in * IN > CD_CASE_H_IN * IN


# ---------------------------------------------------------------------------
# The joinery is cut, not implied
# ---------------------------------------------------------------------------


def test_only_housed_parts_overlap(assembly):
    """Every overlap in the model is a joint somebody has to cut.

    Bounding boxes, so a shelf housed in a divider counts as an overlap even
    though the solids do not touch — which is the point: these six pairs are
    the housings, and anything else in the set would be a part buried in
    another one.
    """
    boxes = [(p.label, p.bounding_box()) for p in _iter_leaf_parts(assembly)]
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

    assert clashes == {
        ("bay_bottom", "divider"),
        ("bay_bottom", "side"),
        ("cd_shelf", "divider"),
        ("cd_shelf", "side"),
        ("divider", "top"),
        ("side", "top"),
    }


def test_the_housings_are_really_cut_away(assembly):
    """A shelf occupies its dado; if the dado were only a note, it would not.

    Without the boolean the shelf ends would be inside solid plywood, which no
    dimension check would notice and every glue-up would.
    """
    parts = {p.label: p for p in _iter_leaf_parts(assembly)}
    divider, shelf = parts["divider"], parts["bay_bottom"]
    assert (divider & shelf).volume == pytest.approx(0.0, abs=1.0)
    assert (parts["top"] & parts["side"]).volume == pytest.approx(0.0, abs=1.0)


def test_a_divider_loses_four_housings_and_a_side_only_two(console, assembly):
    """A divider is housed on both faces; an end panel on its inner one."""
    parts = {}
    for p in _iter_leaf_parts(assembly):
        parts.setdefault(p.label, p)
    one_housing = console.panel_t * console.dado_depth * console.panel_depth
    blank = console.vertical_h * console.panel_depth * console.panel_t

    assert blank - parts["divider"].volume == pytest.approx(4 * one_housing, rel=0.02)
    assert blank - parts["side"].volume == pytest.approx(2 * one_housing, rel=0.02)


# ---------------------------------------------------------------------------
# The cut list, and what it buys
# ---------------------------------------------------------------------------


def test_the_ten_shelves_are_one_part_made_twice(parts):
    by_label = {p.label: p for p in parts}
    bottom, shelf = by_label["bay_bottom"], by_label["cd_shelf"]
    assert bottom.qty == shelf.qty == 5
    assert bottom.length_mm == pytest.approx(shelf.length_mm)
    assert bottom.width_mm == pytest.approx(shelf.width_mm)


def test_every_panel_is_cut_to_the_sheet_not_to_the_nominal(console, parts):
    panels = [p for p in parts if p.material == "plywood_cherry"]
    assert panels
    for p in panels:
        assert p.thickness_mm == pytest.approx(console.panel_t)
        assert p.thickness_mm < 0.75 * IN


def test_a_shelf_is_cut_long_enough_to_reach_into_both_housings(console, parts):
    shelf = {p.label: p for p in parts}["cd_shelf"]
    assert shelf.length_mm == pytest.approx(
        console.bay_clear_w + 2 * console.dado_depth
    )


def test_the_case_comes_off_two_sheets(console, parts):
    sheet_parts = [p for p in parts if p.material == "plywood_cherry"]
    packed = pack_by_material(sheet_parts, console.inventory)
    (result,) = packed.values()
    assert not result.unpacked
    assert result.sheets_used == 2


def test_the_front_edges_come_off_four_quarter_cherry(console, parts):
    solid = [p for p in parts if p.material == "cherry"]
    assert {p.label for p in solid} == {"top_edge", "vertical_edge", "shelf_edge"}
    plan = nest_hardwood(solid, console.inventory, "cherry")
    assert [g.stock.thickness_quarter for g in plan.groups] == ["4/4"]


def test_the_edging_is_milled_to_the_plywood_it_covers(console, parts):
    strip = {p.label: p for p in parts}["vertical_edge"]
    assert strip.thickness_mm == pytest.approx(console.panel_t)
    assert strip.width_mm == pytest.approx(console.edge_t)


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def test_the_console_can_be_built(console, assembly, parts):
    report = console.check(assembly, parts)
    assert report.ok, report.to_text()


def test_the_thin_plywood_is_reported_where_it_matters(console, assembly, parts):
    """Every housing in this piece is cut to the sheet, so say so once a part."""
    report = console.check(assembly, parts)
    thickness = [f for f in report.findings if f.code == "thickness"]
    assert thickness
    assert all(f.severity is Severity.WARN for f in thickness)
    assert "cut the groove to fit the sheet" in thickness[0].message


def test_a_loaded_bay_bottom_does_not_sag(console, assembly, parts):
    report = console.check(assembly, parts)
    sag = [
        f for f in report.findings
        if f.code == "deflection" and "bay bottom" in f.message
    ]
    assert [f.severity for f in sag] == [Severity.INFO]


def test_the_same_bottom_undivided_would_sag_four_inches(console, assembly, parts):
    report = console.check(assembly, parts)
    undivided = [
        f for f in report.findings
        if f.code == "deflection" and "undivided" in f.message
    ]
    assert [f.severity for f in undivided] == [Severity.WARN]
    assert "bays across" in undivided[0].message


def test_the_fifth_bay_is_for_the_records_not_for_the_plywood(console, assembly, parts):
    """Sag asks for three bays.  The other two are about how records stand."""
    report = console.check(assembly, parts)
    assert any(
        f.code == "bay" and "lean and warp" in f.message for f in report.findings
    )


def test_the_bay_width_finding_shows_its_working(console, assembly, parts):
    report = console.check(assembly, parts)
    bay = [f for f in report.findings if f.code == "bay" and "clear" in f.message]
    assert bay and "45/64" in bay[0].message


# ---------------------------------------------------------------------------
# The numbers that must not be silently impossible
# ---------------------------------------------------------------------------


def test_one_bay_is_not_a_run_of_bays():
    with pytest.raises(ValueError, match="at least 2"):
        MediaConsole(n_bays=1)


def test_openings_taller_than_the_case_are_rejected():
    with pytest.raises(ValueError, match="does not fit inside"):
        MediaConsole(record_bay_h_in=18.0)


def test_a_housing_deeper_than_the_stock_is_rejected():
    with pytest.raises(ValueError, match="goes through"):
        MediaConsole(dado_depth_in=0.75)


def test_edging_thicker_than_the_case_is_rejected():
    with pytest.raises(ValueError, match="leaves no panel"):
        MediaConsole(edge_thickness_in=13.0)


def test_more_bays_are_narrower_ones_inside_the_same_envelope():
    six = MediaConsole(n_bays=6)
    assert six.bay_clear_w < MediaConsole().bay_clear_w
    bb = six.build().bounding_box()
    assert bb.size.X == pytest.approx(80 * IN, abs=0.1)
    assert bb.size.Z == pytest.approx(24 * IN, abs=0.1)
