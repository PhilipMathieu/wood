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

from cedar_fence import (  # noqa: E402
    ASSUMED_COVERAGE_IN,
    IN,
    MESH_THICKNESS_MM,
    STYLES,
    CedarFence,
    MeshPlan,
    StockChoice,
    catalogue,
    discount_note,
    price_variants,
    style_for,
    variants,
)

from woodshop.checks import Severity  # noqa: E402
from woodshop.cutlist.extract import extract  # noqa: E402
from woodshop.inventory import Inventory  # noqa: E402


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


# ---------------------------------------------------------------------------
# Choosing among everything Lumbery stocks
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def inv() -> Inventory:
    return Inventory.load()


def test_a_choice_sizes_itself_from_the_table_its_profile_lives_in():
    rough = StockChoice("1x6", "STK", "rough sawn")
    dressed = StockChoice("1x6", "STK", "dressed")
    assert rough.width == pytest.approx(6 * IN)
    assert dressed.width == pytest.approx(5.5 * IN)
    assert rough.rough and not dressed.rough


def test_a_square_edged_board_covers_what_it_measures():
    plain = StockChoice("1x6", "STK", "rough sawn")
    assert plain.covers == pytest.approx(plain.width)
    assert not plain.milled


def test_a_milled_board_covers_less_than_it_measures():
    tg = StockChoice("1x6", "STK", "tongue & groove, dressed")
    assert tg.milled
    assert tg.covers < tg.width
    assert tg.covers == pytest.approx(ASSUMED_COVERAGE_IN[("1x6", tg.profile)] * IN)


def test_every_choice_resolves_to_one_inventory_entry(inv):
    for variant in variants(inv)[0]:
        if variant.choice is None:      # the mesh, which is bought by the roll
            continue
        entry = variant.choice.entry(inv)
        assert entry is variant.stock


def test_every_lumbery_cedar_entry_is_either_usable_or_explained(inv):
    usable, unusable = variants(inv)
    accounted = {v.stock.stock_label for v in usable}
    accounted |= {label for label, _ in unusable}
    everything = {
        d.stock_label for d in inv.dimensional if d.species == "white_cedar"
    } | {u.stock_label for u in inv.unit_goods if u.species == "white_cedar"}
    assert everything <= accounted


def test_the_sawn_entries_are_priced_and_the_round_ones_are_not(inv):
    """Which is a fact about the guide, not about the fence."""
    for variant in variants(inv)[0]:
        if variant.choice is None:
            continue
        entry = variant.choice.entry(inv)
        if variant.requires_style == "log_and_mesh":
            assert entry.price is None
        else:
            assert entry.price_is_verified


def test_what_cannot_be_used_says_why(inv):
    reasons = dict(variants(inv)[1])
    assert "2 ft piece" in reasons["white_cedar 1x4 dressed cutoff (STK)"]
    assert "bundle" in reasons['white_cedar shakes 3/8" (clear)']
    assert "sheet" in reasons["white_cedar lattice, square grids 4x8"]


# ---------------------------------------------------------------------------
# Milled stock butts; it cannot be spaced or lapped
# ---------------------------------------------------------------------------


def test_tongue_and_groove_butts_and_rips_the_last_board():
    fence = CedarFence(
        style="picket", board=StockChoice("1x6", "STK", "tongue & groove, dressed")
    )
    group = fence.panel_groups()[0]
    _, cover = fence.cover_of(group)
    run = fence.board_run(cover, fence.target_gap)
    assert run.gap == 0.0
    assert run.last_width is not None and run.last_width < fence.board_w
    assert (
        run.full_boards * fence.board_w + run.last_width
    ) == pytest.approx(cover)


def test_the_ripped_board_reaches_the_cut_list_as_its_own_row():
    fence = CedarFence(
        style="picket", board=StockChoice("1x6", "STK", "tongue & groove, dressed")
    )
    parts = extract(fence.build())
    widths = {round(p.width_mm, 1) for p in parts if p.label == "board"}
    assert len(widths) > 1
    ripped = [p for p in parts if p.label == "board" and "ripped" in p._extra["notes"]]
    assert ripped


def test_milled_stock_is_still_bought_by_the_board_it_comes_from():
    fence = CedarFence(
        style="picket", board=StockChoice("1x6", "STK", "tongue & groove, dressed")
    )
    plan = fence.plan(extract(fence.build()))
    labels = [g.label for g in plan.groups]
    assert "white_cedar 1x6 tongue & groove, dressed (STK)" in labels


def test_the_assumed_coverage_is_flagged_every_time_it_is_used():
    fence = CedarFence(
        style="picket", board=StockChoice("1x6", "STK", "tongue & groove, dressed")
    )
    parts = extract(fence.build())
    coverage = [
        f for f in fence.check(fence.build(), parts).findings if f.code == "coverage"
    ]
    assert coverage and coverage[0].severity is Severity.WARN
    assert "ASSUMED" in coverage[0].message


def test_an_interlocking_board_cannot_be_laid_board_on_board():
    with pytest.raises(ValueError, match="interlocks"):
        CedarFence(
            style="board_on_board",
            board=StockChoice("1x6", "STK", "tongue & groove, dressed"),
        )


def test_the_catalogue_builds_it_as_a_picket_instead():
    milled = StockChoice("1x6", "STK", "tongue & groove, dressed")
    assert style_for(milled, "board_on_board") == "picket"
    assert style_for(milled, "horizontal") == "horizontal"
    assert style_for(StockChoice("1x6"), "board_on_board") == "board_on_board"


# ---------------------------------------------------------------------------
# Pricing every variant
# ---------------------------------------------------------------------------


def test_every_board_variant_builds_and_prices(inv):
    rows = price_variants("board", inv)
    assert len(rows) >= 20
    for row in rows:
        assert row.total is not None
        assert row.summary.verified
        assert row.complete
        assert not row.plan.unmatched


def test_low_grade_is_the_cheap_way_to_build_the_same_fence(inv):
    rows = {r.variant.choice.label: r.total for r in price_variants("board", inv)}
    assert rows["1x6 rough sawn (low)"] < rows["1x6 rough sawn (STK)"]


def test_rails_and_posts_are_priced_too(inv):
    assert {r.variant.choice.nominal for r in price_variants("rail", inv)} == {
        "2x4", "2x6", "log 4",
    }
    assert {r.variant.choice.nominal for r in price_variants("post", inv)} == {
        "4x4", "6x6", "log 5", "log 6",
    }


def test_a_partial_total_sorts_below_every_complete_one(inv):
    """$231 of a fence is not cheaper than $2,269 of one; it is less of a total."""
    rows = price_variants("post", inv)
    complete = [i for i, r in enumerate(rows) if r.complete]
    partial = [i for i, r in enumerate(rows) if not r.complete]
    assert complete and partial
    assert max(complete) < min(partial)
    logs = [r for r in rows if r.variant.requires_style == "log_and_mesh"]
    assert logs and all(
        "part" in r.total_text() or r.total_text() == "unpriced" for r in logs
    )


def test_the_catalogue_names_every_variant_and_what_it_costs(inv):
    text = catalogue(inv)
    assert "1x6 rough sawn (STK)" in text
    assert "1x6 tongue & groove, dressed (low)" in text
    assert "shakes" in text
    assert "$/LF" in text
    assert "2026-08-17" in text


# ---------------------------------------------------------------------------
# Terms that apply to the order rather than the board
# ---------------------------------------------------------------------------


def test_a_fence_this_size_misses_the_first_volume_tier(inv):
    note = discount_note(2_269, inv)
    assert "below" in note
    assert "$5,000" in note


def test_a_bigger_order_says_what_it_saves(inv):
    note = discount_note(8_000, inv)
    assert "10% tier" in note
    assert "$7,200" in note      # 8,000 less 10%
    assert "$10,000" in note     # and what the next tier would need


def test_a_yard_with_no_terms_says_so(inv):
    assert "no volume discount" in discount_note(9_999, inv, "O'Brien Hardwoods")


# ---------------------------------------------------------------------------
# Logs and mesh: round stock, and infill sold by the roll
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def logs() -> CedarFence:
    return CedarFence(style="log_and_mesh")


@pytest.fixture(scope="module")
def log_parts(logs: CedarFence) -> list:
    return extract(logs.build())


def test_the_log_style_brings_its_own_stock(logs):
    """A log fence is different materials, not a different arrangement."""
    assert logs.post.round and logs.rail.round and logs.gate_post.round
    assert logs.post.diameter_in == 5.0
    assert logs.rail.diameter_in == 4.0
    # The gate frame stays sawn in every style, because a round stile cannot
    # be half-lapped.
    assert not logs.gate_frame.round


def test_posts_and_rails_are_bought_round(log_parts):
    for label in ("line_post", "gate_post", "log_rail"):
        part = next(p for p in log_parts if p.label == label)
        assert part.shape == "pole"
        assert part.nominal.startswith("log")
        assert "dia." in part.profile


def test_a_pole_is_not_priced_as_a_square_blank(log_parts):
    """Which is the whole difference between a log and a turning."""
    post = next(p for p in log_parts if p.label == "line_post")
    assert post.width_mm == pytest.approx(5 * IN)
    assert post.thickness_mm == pytest.approx(5 * IN)
    assert post.length_mm == pytest.approx(96 * IN)


def test_a_rail_is_longer_than_the_gap_it_crosses(logs, log_parts):
    """Because both ends are tenoned into a hole bored in the post."""
    rails = [p for p in log_parts if p.label == "log_rail"]
    bay = next(s for s in logs.spans() if s.kind == "panel")
    clear = bay.length - logs.post_size / 2 - logs.gate_post_size / 2
    lengths = {round(p.length_mm, 1) for p in rails}
    assert any(
        abs(length - (clear + 2 * logs.tenon_in * IN)) < 0.5 for length in lengths
    )


def test_every_bay_gets_its_own_sheet_of_mesh(logs, log_parts):
    bays = len([s for s in logs.spans() if s.kind == "panel"])
    mesh = [p for p in log_parts if p.label == "mesh"]
    assert sum(p.qty for p in mesh) == bays
    assert all(p.thickness_mm == pytest.approx(MESH_THICKNESS_MM) for p in mesh)


def test_the_mesh_hangs_behind_the_logs(logs):
    """So the fence shows cedar from the front and mesh to the dog."""
    children = {c.label: c for c in logs.build().children}
    rail = children["log_rail"].bounding_box()
    mesh = children["mesh"].bounding_box()
    assert mesh.max.Y <= rail.min.Y + 1e-6


def test_the_mesh_stops_where_the_fence_does(logs, log_parts):
    mesh = next(p for p in log_parts if p.label == "mesh")
    assert mesh.width_mm == pytest.approx(46 * IN)   # 48" less the ground gap
    assert logs.mesh_height <= logs.mesh_roll_height_in * IN


def test_the_gates_are_sawn_frames_with_mesh_in_them(log_parts):
    assert not [p for p in log_parts if p.label == "gate_board"]
    stile = next(p for p in log_parts if p.label == "gate_stile")
    assert stile.stock_spec == "2x4 rough sawn (STK)"
    assert next(p for p in log_parts if p.label == "gate_mesh")


def test_at_least_two_rails_or_the_mesh_has_no_edge():
    with pytest.raises(ValueError, match="at least a top and a bottom"):
        CedarFence(style="log_and_mesh", log_rails=1)


def test_the_middle_rail_can_be_left_out():
    two = CedarFence(style="log_and_mesh", log_rails=2)
    heights = two._log_rail_heights()
    assert [name for _z, name in heights] == ["bottom", "top"]
    # The row count is the same — it is the rail *quantity* that drops.
    rails = next(p for p in extract(two.build()) if p.label == "log_rail")
    three = next(
        p for p in extract(CedarFence(style="log_and_mesh").build())
        if p.label == "log_rail"
    )
    assert rails.qty < three.qty


# ---------------------------------------------------------------------------
# Buying mesh, which is neither lumber nor sheet goods
# ---------------------------------------------------------------------------


def test_mesh_is_bought_by_the_roll_from_the_feet_of_fence(logs, log_parts):
    plan = logs.mesh_plan(log_parts)
    assert plan is not None
    assert plan.roll_length_ft == pytest.approx(100.0)
    assert plan.buy_ft == pytest.approx(plan.run_ft * 1.05)
    assert plan.rolls == 1


def test_a_longer_fence_needs_more_rolls(inv):
    long_fence = CedarFence(style="log_and_mesh", run_ft=300.0, inventory=inv)
    plan = long_fence.mesh_plan(extract(long_fence.build()))
    assert plan.rolls >= 3


def test_an_unstocked_roll_length_is_not_a_guessed_one():
    plan = MeshPlan(stock=None, run_ft=54.0, height=1168.4, roll_height=1219.2)
    assert plan.roll_length_ft is None
    assert plan.rolls is None
    assert "no mesh is stocked" in plan.to_text()


def test_the_timber_plan_leaves_the_mesh_alone(logs, log_parts):
    """Mesh is not lumber; a lineal-foot lumber plan has nothing to say to it."""
    plan = logs.plan(log_parts)
    assert not plan.unmatched
    assert all(g.stock.species == "white_cedar" for g in plan.groups)


def test_the_total_refuses_to_look_complete(logs, log_parts):
    summary = logs.cost_summary(log_parts)
    assert not summary.complete
    assert any("log" in label for label in summary.unpriced)
    assert any("mesh" in label for label in summary.unpriced)
    assert "excludes unpriced" in summary.to_text()


def test_the_unpriced_mesh_is_reported_as_a_gap_and_not_as_free(logs, log_parts):
    report = logs.check(logs.build(), log_parts)
    prices = [f for f in report.findings if f.code == "price"]
    assert prices and prices[0].severity is Severity.WARN
    assert "nothing was invented" in prices[0].message


# ---------------------------------------------------------------------------
# What the log-and-mesh checks catch
# ---------------------------------------------------------------------------


def test_mesh_taller_than_its_roll_is_an_error():
    tall = CedarFence(style="log_and_mesh", height_in=72.0, mesh_roll_height_in=48.0)
    parts = extract(tall.build())
    mesh = [f for f in tall.check(tall.build(), parts).findings if f.code == "mesh"]
    assert mesh[0].severity is Severity.ERROR
    assert "cannot be stretched" in mesh[0].message


def test_a_round_rail_is_not_the_square_it_fits_inside(logs, log_parts):
    deflection = [
        f for f in logs.check(logs.build(), log_parts).findings
        if f.code == "deflection"
    ]
    assert deflection and "59%" in deflection[0].message


def test_the_joint_is_a_bored_hole_and_it_has_to_be_bored_first(logs, log_parts):
    joinery = [
        f for f in logs.check(logs.build(), log_parts).findings
        if f.code == "joinery"
    ]
    assert joinery and "before the posts are set" in joinery[0].message


def test_a_peeled_post_is_flagged_for_what_its_skin_is(logs, log_parts):
    durability = [
        f for f in logs.check(logs.build(), log_parts).findings
        if f.code == "durability"
    ]
    assert any("sapwood band as its outer skin" in f.message for f in durability)


def test_cedar_and_plain_steel_are_flagged_in_every_style(fence, parts, logs,
                                                          log_parts):
    for design, cut in ((fence, parts), (logs, log_parts)):
        fasteners = [
            f for f in design.check(design.build(), cut).findings
            if f.code == "fasteners"
        ]
        assert fasteners and fasteners[0].severity is Severity.WARN
        assert "stain the wood black" in fasteners[0].message


def test_the_mesh_says_what_it_does_not_stop(logs, log_parts):
    mesh = [
        f for f in logs.check(logs.build(), log_parts).findings if f.code == "mesh"
    ]
    assert any("rabbit" in f.message for f in mesh)


def test_the_model_admits_it_drew_a_sheet_instead_of_wires(logs, log_parts):
    mesh = [
        f for f in logs.check(logs.build(), log_parts).findings if f.code == "mesh"
    ]
    assert any("not as wires" in f.message for f in mesh)
