"""Tests for the cedar fence — the project that is bought by the foot.

Everything else in this repository is furniture: measured to a sixteenth,
priced by the board foot, and cut from stock whose lengths somebody publishes.
A fence is none of those things, and these tests pin the places where that
difference shows.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "projects"))

from cedar_fence import IN, STYLES, CedarFence  # noqa: E402

from woodshop.checks import Severity  # noqa: E402
from woodshop.cutlist.extract import extract  # noqa: E402


@pytest.fixture(scope="module")
def fence() -> CedarFence:
    return CedarFence()


@pytest.fixture(scope="module")
def parts(fence: CedarFence) -> list:
    return extract(fence.build())


@pytest.fixture(scope="module")
def report(fence: CedarFence, parts: list):
    return fence.check(fence.build(), parts)


def findings(report, code: str) -> list:
    return [f for f in report.findings if f.code == code]


# ---------------------------------------------------------------------------
# The brief: 38 ft at 4 ft, plus two 10 ft gate sections
# ---------------------------------------------------------------------------


def test_it_is_thirty_eight_feet_of_fence_and_two_ten_foot_gate_sections(fence):
    panels = [s for s in fence.spans() if s.kind == "panel"]
    gates = [s for s in fence.spans() if s.kind == "gate"]
    assert sum(s.length for s in panels) == pytest.approx(38 * 12 * IN)
    assert len(gates) == 2
    assert all(s.length == pytest.approx(10 * 12 * IN) for s in gates)


def test_the_fence_stands_four_feet_above_grade(fence):
    bb = fence.build().bounding_box()
    assert bb.max.Z == pytest.approx(48 * IN, abs=0.1)


def test_the_posts_go_below_grade_and_the_boards_do_not(fence):
    bb = fence.build().bounding_box()
    assert bb.min.Z == pytest.approx(-fence.gate_post_length + 48 * IN, abs=0.1)
    boards = [
        child for child in fence.build().children if child.label == "under_board"
    ]
    assert min(b.bounding_box().min.Z for b in boards) == pytest.approx(
        2 * IN, abs=0.1
    )


def test_a_line_post_is_exactly_an_eight_foot_stick(fence):
    """4 ft in the ground and 4 ft in the air, which is why 8 ft is the size."""
    assert fence.post_length == pytest.approx(96 * IN)
    assert fence.embedment_in == 48.0


def test_gate_posts_are_bigger_and_deeper(fence):
    posts = fence.posts()
    gate = [p for p in posts if p.is_gate_post]
    line = [p for p in posts if not p.is_gate_post]
    assert len(gate) == 4
    assert all(p.size > line[0].size for p in gate)
    assert all(p.embedment > line[0].embedment for p in gate)


def test_only_the_posts_a_gate_touches_are_six_by_six(fence):
    gate_x = {s.x0 for s in fence.gate_openings} | {
        s.x1 for s in fence.gate_openings
    }
    for post in fence.posts():
        assert post.is_gate_post == any(
            abs(post.x - x) < 1e-6 for x in gate_x
        )


# ---------------------------------------------------------------------------
# Rough sawn is not dressed, and the whole layout depends on which
# ---------------------------------------------------------------------------


def test_the_boards_are_rough_sawn_and_therefore_full_size(fence, parts):
    board = next(p for p in parts if p.label == "under_board")
    assert board.width_mm == pytest.approx(152.4)      # a full 6"
    assert board.thickness_mm == pytest.approx(25.4)   # a full 1"
    assert board.stock_profile == "rough sawn"


def test_every_part_names_the_grade_it_is_priced_in(parts):
    assert {p.grade for p in parts} == {"STK"}
    assert all(p.nominal for p in parts)


# ---------------------------------------------------------------------------
# Board layout: the gap absorbs the remainder
# ---------------------------------------------------------------------------


def test_a_row_of_boards_fills_its_cover_exactly(fence):
    for group in fence.panel_groups():
        _, cover = fence.cover_of(group)
        run = fence.board_run(cover, fence.target_gap)
        assert (
            run.count * fence.board_w + (run.count - 1) * run.gap
        ) == pytest.approx(cover)


def test_the_fitted_gap_stays_near_the_one_asked_for(fence):
    for group in fence.panel_groups():
        _, cover = fence.cover_of(group)
        run = fence.board_run(cover, fence.target_gap)
        assert abs(run.gap - fence.target_gap) < fence.board_w / 2


def test_boards_run_past_a_line_post_and_stop_at_a_gate_post(fence):
    """Otherwise every second post gets a sliver against it."""
    first = fence.panel_groups()[0]
    x_start, cover = fence.cover_of(first)
    # The run starts half a post outside the first post...
    assert x_start == pytest.approx(-fence.post_size / 2)
    # ...and stops at the near face of the gate post, not at its centre.
    gate_post_x = fence.gate_openings[0].x0
    assert x_start + cover == pytest.approx(gate_post_x - fence.gate_post_size / 2)


def test_the_over_course_laps_its_neighbours(fence):
    """A board-on-board fence that does not lap is a fence with slots in it."""
    for group in fence.panel_groups():
        _, cover = fence.cover_of(group)
        run = fence.board_run(cover, fence.target_gap)
        lap = (fence.board_w - run.gap) / 2
        assert lap >= 0.75 * IN


def test_the_two_courses_sit_in_front_of_each_other(fence):
    children = {c.label: c for c in fence.build().children if "board" in c.label}
    under = children["under_board"].bounding_box()
    over = children["over_board"].bounding_box()
    assert over.min.Y == pytest.approx(under.max.Y, abs=0.01)


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------


def test_a_ten_foot_section_is_a_nine_foot_six_opening(fence):
    span = fence.gate_openings[0]
    assert fence.clear_opening(span) == pytest.approx(114 * IN)


def test_two_leaves_and_their_gaps_fill_the_opening(fence):
    span = fence.gate_openings[0]
    width = fence.leaf_width(span)
    gaps = 2 * fence.hinge_gap_in * IN + fence.leaf_gap_in * IN
    assert 2 * width + gaps == pytest.approx(fence.clear_opening(span))


def test_a_leaf_hangs_clear_of_the_ground_and_flush_with_the_fence(fence):
    stiles = [c for c in fence.build().children if c.label == "gate_stile"]
    bb = stiles[0].bounding_box()
    assert bb.min.Z == pytest.approx(3 * IN, abs=0.1)
    assert bb.max.Z == pytest.approx(48 * IN, abs=0.1)


def test_the_brace_rises_from_the_hinge_side(fence):
    """A brace running the other way holds the gate up in tension, and sags."""
    braces = sorted(
        (c for c in fence.build().children if c.label == "gate_brace"),
        key=lambda b: b.bounding_box().min.X,
    )
    assert len(braces) == 4  # two leaves in each of two gates
    for i, brace in enumerate(braces[:2]):
        vertices = [tuple(v) for v in brace.vertices()]
        foot = min(vertices, key=lambda v: v[2])
        head = max(vertices, key=lambda v: v[2])
        # The left-hand leaf hinges on the left, so its brace rises to the
        # right; the right-hand leaf hinges on the right and mirrors it.
        assert (foot[0] < head[0]) is (i == 0)


def test_a_single_walk_gate_gets_a_panel_beside_it():
    walk = CedarFence(style="picket", gate_leaves=1)
    spans = walk.spans()
    gates = [s for s in spans if s.kind == "gate"]
    assert all(s.length == pytest.approx(48 * IN) for s in gates)
    # The rest of the 10 ft section is fence, so the run gains two posts.
    assert len(walk.posts()) == len(CedarFence(style="picket").posts()) + 2
    assert walk.clear_opening(gates[0]) == pytest.approx(42 * IN)


def test_a_walk_gate_wider_than_its_section_is_refused():
    with pytest.raises(ValueError, match="does not fit"):
        CedarFence(gate_leaves=1, walk_gate_in=132.0)


def test_an_unknown_style_is_refused():
    with pytest.raises(ValueError, match="style must be"):
        CedarFence(style="basketweave")


# ---------------------------------------------------------------------------
# The three styles
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("style", STYLES)
def test_every_style_builds_and_checks_clean(style: str):
    fence = CedarFence(style=style)
    assembly = fence.build()
    parts = extract(assembly)
    report = fence.check(assembly, parts)
    assert parts
    assert report.ok  # nothing an ERROR, whatever else it says


def test_the_horizontal_style_shortens_the_bays_and_drops_the_rails():
    flat = CedarFence(style="horizontal")
    parts = extract(flat.build())
    assert not [p for p in parts if p.label == "rail"]
    panels = [s for s in flat.spans() if s.kind == "panel"]
    assert max(s.length for s in panels) <= 6 * 12 * IN + 1e-6


def test_privacy_costs_more_than_pickets():
    """Twice the boards, and the check that says so is the price line."""
    picket = CedarFence(style="picket")
    privacy = CedarFence(style="board_on_board")
    cheap = picket.plan(extract(picket.build())).cost
    dear = privacy.plan(extract(privacy.build())).cost
    assert dear > cheap


# ---------------------------------------------------------------------------
# Buying it
# ---------------------------------------------------------------------------


def test_the_plan_buys_four_entries_and_names_all_of_them(fence, parts):
    plan = fence.plan(parts)
    assert [g.label for g in plan.groups] == [
        "white_cedar 1x6 rough sawn (STK)",
        "white_cedar 2x4 rough sawn (STK)",
        "white_cedar 4x4 rough sawn (STK)",
        "white_cedar 6x6 rough sawn (STK)",
    ]
    assert not plan.unmatched


def test_every_price_behind_the_total_is_dated(fence, parts):
    summary = fence.plan(parts).cost_summary
    assert summary.verified
    assert summary.complete
    assert "unverified" not in summary.to_text().lower()


def test_the_price_report_names_only_the_stock_this_fence_buys(fence, parts):
    plan = fence.plan(parts)
    report = fence.check_prices(plan)
    assert len(report.findings) == 4
    assert all(f.severity is Severity.INFO for f in report.findings)


def test_no_published_lengths_means_no_cut_plan(fence, parts):
    """The honest headline: a rate per foot is not a list of sticks."""
    plan = fence.plan(parts)
    warnings = fence.check_stock_lengths(plan)
    assert len(warnings) == 4
    assert all(f.severity is Severity.WARN for f in warnings)
    assert all("not a cut list" in f.message for f in warnings)


# ---------------------------------------------------------------------------
# What the checks catch
# ---------------------------------------------------------------------------


def test_the_layout_finding_counts_the_bays_and_the_posts(report):
    message = findings(report, "layout")[0].message
    assert "6 bays" in message
    assert "9 posts" in message


def test_a_post_short_of_the_frost_line_is_a_warning():
    shallow = CedarFence(embedment_in=30.0)
    parts = extract(shallow.build())
    frost = [f for f in shallow.check(shallow.build(), parts).findings
             if f.code == "frost"]
    assert frost[0].severity is Severity.WARN
    assert "jacked" in frost[0].message


def test_a_post_below_the_frost_line_is_not(report):
    assert findings(report, "frost")[0].severity is Severity.INFO


def test_the_rot_risk_is_reported_even_though_it_is_cedar(report):
    durability = findings(report, "durability")
    assert any(f.severity is Severity.WARN for f in durability)
    assert any("sapwood" in f.message for f in durability)


def test_the_hardware_is_named_as_missing_from_the_total(report):
    hardware = findings(report, "hardware")
    assert hardware and hardware[0].severity is Severity.WARN


def test_a_gate_spacing_that_fights_the_fence_is_flagged():
    """The picket gate cannot match the fence's rhythm, and says so."""
    picket = CedarFence(style="picket")
    parts = extract(picket.build())
    rhythm = [
        f for f in picket.check(picket.build(), parts).findings
        if "rhythm" in f.message
    ]
    assert rhythm and rhythm[0].severity is Severity.WARN


def test_the_rail_deflection_is_reported_against_a_limit(report):
    message = findings(report, "deflection")[0].message
    assert "limit span/240" in message


def test_a_bay_too_long_for_the_style_is_a_warning():
    stretched = CedarFence(style="picket", max_bay_ft=20.0)
    parts = extract(stretched.build())
    layout = [f for f in stretched.check(stretched.build(), parts).findings
              if f.code == "layout"]
    assert any(f.severity is Severity.WARN for f in layout)
