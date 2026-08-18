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
    AVO_PANEL_HEIGHTS_FT,
    AVO_POST_TABLE,
    AVO_STYLES,
    BOLTS_PER_HINGE,
    DESIGNS,
    HARDWARE_TIERS,
    HINGES_PER_LEAF,
    IN,
    MESH_THICKNESS_MM,
    POST_AND_RAIL_LENGTHS_FT,
    PROJECTS,
    STYLES,
    CedarFence,
    HardwarePlan,
    MeshPlan,
    PanelFence,
    StockChoice,
    catalogue,
    compare_designs,
    discount_note,
    hardware_stock,
    post_stone_cuyd,
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


def test_the_hardware_says_what_it_costs_and_where_buying_it_goes_wrong(report):
    """It used to say only that it was missing from every total. It is not now."""
    hardware = findings(report, "hardware")
    assert hardware
    assert any("hardware runs" in f.message for f in hardware)
    assert any(f.severity is Severity.WARN for f in hardware)


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


def test_the_mesh_runs_from_the_top_rail_to_the_ground(logs, log_parts):
    """A dog goes under a 2 in gap without breaking stride, so there isn't one."""
    mesh = next(p for p in log_parts if p.label == "mesh")
    assert mesh.width_mm == pytest.approx(48 * IN)
    assert logs.mesh_bottom == 0.0
    assert logs.mesh_height <= logs.mesh_roll_height_in * IN


def test_a_boarded_fence_keeps_its_ground_gap(logs):
    """The clearance is for boards that would wick water, not for mesh."""
    boards = CedarFence(style="picket")
    assert boards.mesh_bottom == pytest.approx(boards.ground_clearance_in * IN)


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
    """The logs are still unpriced, and a total that hid that would be worse."""
    summary = logs.cost_summary(log_parts)
    assert not summary.complete
    assert any("log" in label for label in summary.unpriced)
    assert "excludes unpriced" in summary.to_text()


def test_the_mesh_and_the_hardware_are_in_the_total_and_the_logs_are_not(
    logs, log_parts
):
    """Which is the point: the gap is named, and it is a smaller gap than it was."""
    summary = logs.cost_summary(log_parts)
    priced = " ".join(line.label for line in summary.lines)
    assert "mesh" in priced
    assert "tee hinge" in priced
    assert all("mesh" not in label for label in summary.unpriced)


def test_the_mesh_no_longer_warns_because_the_mesh_has_a_price(logs, log_parts):
    """The warning that said so was the point of the entry, and it is spent."""
    report = logs.check(logs.build(), log_parts)
    assert not [f for f in report.findings if f.code == "price"]


def test_but_it_comes_straight_back_if_the_price_goes_away(logs, log_parts):
    """The finding is gated on the price, not deleted along with the problem."""
    import copy

    bare = copy.deepcopy(logs)
    entry = bare.mesh_stock()
    object.__setattr__(entry, "price_per_unit", None)
    prices = [
        f for f in bare.check(bare.build(), log_parts).findings if f.code == "price"
    ]
    assert prices and prices[0].severity is Severity.WARN
    assert "nothing here has been invented" in prices[0].message


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


# ---------------------------------------------------------------------------
# The panels The Lumbery actually sells
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def panels() -> PanelFence:
    return PanelFence()


def test_the_catalogue_is_six_styles_in_three_heights():
    assert set(AVO_STYLES) == {
        "stockade", "privacy_board", "spaced_picket", "spaced_board",
        "universal", "chestnut_hill",
    }
    assert AVO_PANEL_HEIGHTS_FT == (4.0, 5.0, 6.0)


def test_the_two_board_sizes_are_theirs_not_a_nominal_lookup():
    """7/8 x 2-7/8 and 3/4 x 3-1/2 are milled sizes, not any table's answer."""
    assert AVO_STYLES["stockade"].board_t_in == 0.875
    assert AVO_STYLES["stockade"].board_w_in == 2.875
    assert AVO_STYLES["privacy_board"].board_t_in == 0.75
    assert AVO_STYLES["privacy_board"].board_w_in == 3.5


def test_the_rail_is_the_section_the_catalogue_publishes(panels):
    """2" x 3" S2S — a dressed 2x3 would be 1-1/2" x 2-1/2"."""
    assert panels.rail.thickness == pytest.approx(2 * IN)
    assert panels.rail.width == pytest.approx(3 * IN)
    rail = next(
        p for p in extract(panels.build()) if p.label.endswith("panel_rail")
    )
    assert rail.thickness_mm == pytest.approx(2 * IN)
    assert rail.stock_spec == "2x3 S2S dowelled Colonial rail"


def test_a_style_it_does_not_sell_is_refused():
    with pytest.raises(ValueError, match="style must be one of"):
        PanelFence(style="board_on_board")


def test_a_grade_that_style_is_not_offered_in_is_refused():
    """Spaced picket comes in Premium and #2; Economy is a privacy grade."""
    with pytest.raises(ValueError, match="is offered in"):
        PanelFence(style="spaced_picket", grade="Economy (#3)")


def test_the_default_grade_is_the_first_the_style_offers(panels):
    assert panels.grade == "Premium (#1)"


# ---------------------------------------------------------------------------
# The bay is the panel, so the run has to divide
# ---------------------------------------------------------------------------


def test_thirty_eight_feet_does_not_divide_into_eight_foot_panels(panels):
    assert len(panels.panels()) == 6
    odd = panels.odd_panels()
    assert len(odd) == 2
    assert all(s.length == pytest.approx(3 * 12 * IN) for s in odd)


def test_a_run_that_does_divide_gets_no_custom_panels():
    tidy = PanelFence(run_ft=32.0)
    assert not tidy.odd_panels()
    assert len(tidy.panels()) == 4


def test_the_odd_panel_is_flagged_with_what_would_fit(panels):
    layout = [
        f for f in panels.check(panels.build(), extract(panels.build())).findings
        if f.code == "layout"
    ]
    warn = next(f for f in layout if f.severity is Severity.WARN)
    assert "does not divide" in warn.message
    assert "16 ft or 24 ft" in warn.message


# ---------------------------------------------------------------------------
# Their post table, and where it disagrees with the frost line
# ---------------------------------------------------------------------------


def test_the_post_comes_from_their_sizing_table(panels):
    assert AVO_POST_TABLE[4.0] == (6.0, 2.0)
    assert panels.post_length_ft == 6.0


def test_hanging_the_panel_clear_of_grade_comes_out_of_the_hole(panels):
    """Their table says 2 ft down; the 2" gap under the panel takes 2" of it."""
    assert panels.above_grade == pytest.approx(50 * IN)
    assert panels.embedment == pytest.approx(22 * IN)


def test_their_own_sizing_is_flagged_against_the_frost_line(panels):
    frost = [
        f for f in panels.check(panels.build(), extract(panels.build())).findings
        if f.code == "frost"
    ]
    assert frost and frost[0].severity is Severity.WARN
    assert "catalogue's own sizing" in frost[0].message


def test_a_gate_post_is_one_length_up_and_all_of_it_goes_down(panels):
    posts = panels.posts()
    gate = next(p for p in posts if p.is_gate_post)
    line = next(p for p in posts if not p.is_gate_post)
    assert gate.length == pytest.approx(line.length + 24 * IN)
    assert gate.embedment == pytest.approx(line.embedment + 24 * IN)


# ---------------------------------------------------------------------------
# An order, not a cut list
# ---------------------------------------------------------------------------


def test_the_order_counts_panels_posts_and_caps(panels):
    order = panels.order()
    kinds = {
        what.split(",")[0]: (count, unit)
        for what, count, unit in order.lines
        if "CUSTOM" not in what
    }
    assert kinds["Stockade panel"][0] == 4
    assert kinds["4x4 end post"] == (2, "post")
    assert kinds["4x4 line post"] == (3, "post")
    assert kinds["6x6 gate post"] == (4, "post")
    assert kinds["post cap"] == (9, "each")


def test_every_custom_panel_is_its_own_line(panels):
    customs = [line for line in panels.order().lines if "CUSTOM" in line[0]]
    assert len(customs) == 2
    assert all(count == 1 for _what, count, _unit in customs)


def test_the_gates_are_quoted_rather_than_ordered(panels):
    order = panels.order()
    assert order.quoted and "gate leaves" in order.quoted[0]
    assert not any("gate leaf" in what for what, _c, _u in order.lines)


def test_nothing_in_the_catalogue_carries_a_published_price(panels):
    """Not one panel, post or cap. The only priced line is the stone under it."""
    order = panels.order()
    assert order.unpriced
    summary = order.cost_summary
    assert not summary.complete
    assert [line.label for line in summary.lines] == [
        stock.stock_label
        for stock in [hardware_stock(panels.inventory, '3/4" crushed, bulk')]
    ]


def test_the_order_reads_as_the_email_you_would_send(panels):
    text = panels.order().to_text()
    assert "Stockade panel" in text
    assert "CUSTOM" in text
    assert "quotes it by email" in text


# ---------------------------------------------------------------------------
# What is drawn, and what is admitted
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("style", sorted(AVO_STYLES))
def test_every_catalogue_style_builds_and_checks_clean(style: str):
    fence = PanelFence(style=style)
    assembly = fence.build()
    parts = extract(assembly)
    report = fence.check(assembly, parts)
    assert parts
    assert report.ok


def test_the_unpublished_numbers_are_flagged_as_assumed(panels):
    assumed = [
        f for f in panels.check(panels.build(), extract(panels.build())).findings
        if f.code == "assumed"
    ]
    assert assumed and all(f.severity is Severity.WARN for f in assumed)
    assert any("rails are drawn" in f.message for f in assumed)


def test_a_spaced_style_admits_the_gap_is_not_published():
    spaced = PanelFence(style="spaced_picket")
    assumed = [
        f for f in spaced.check(spaced.build(), extract(spaced.build())).findings
        if f.code == "assumed"
    ]
    assert any("gap between boards" in f.message for f in assumed)


def test_the_universal_panel_has_a_frame_and_no_backing_rails():
    universal = PanelFence(style="universal")
    labels = {p.label for p in extract(universal.build())}
    assert "frame_stile" in labels and "frame_rail" in labels
    assert "panel_rail" not in labels


def test_chestnut_hill_sandwiches_its_balusters(panels):
    hill = PanelFence(style="chestnut_hill")
    parts = extract(hill.build())
    rails = [p for p in parts if "chestnut" in p.label]
    balusters = [p for p in parts if p.label.endswith("baluster")]
    assert balusters
    # Two rails per position, one each side, so four rail rows in a panel.
    assert sum(p.qty for p in rails) == 4 * len(hill.panels())


def test_the_parts_list_says_it_is_not_an_order(panels):
    ordering = [
        f for f in panels.check(panels.build(), extract(panels.build())).findings
        if f.code == "ordering"
    ]
    assert any("nothing in this design is cut" in f.message for f in ordering)
    assert any("bored on the faces" in f.message for f in ordering)


# ---------------------------------------------------------------------------
# Three designs, because The Lumbery sells three systems
# ---------------------------------------------------------------------------


def test_there_are_exactly_three_designs():
    """One per system in the catalogue, and no fourth that only differs a bit.

    The styles below the designs still exist — they are how the catalogue is
    priced and how a panel is benchmarked against sticks — but a style is a
    row in a price guide and a design is something somebody can buy.
    """
    assert list(DESIGNS) == ["privacy", "chestnut", "rails"]
    assert [p.slug for p in PROJECTS] == [
        "cedar-fence-privacy",
        "cedar-fence-chestnut",
        "cedar-fence-rails",
    ]


def test_two_are_panels_and_one_is_sticks():
    """Which is the catalogue's own division, not a modelling convenience."""
    kinds = {key: type(factory()) for key, (_n, factory, _s) in DESIGNS.items()}
    assert kinds["privacy"] is PanelFence
    assert kinds["chestnut"] is PanelFence
    assert kinds["rails"] is CedarFence


def test_every_design_carries_its_own_summary_and_they_differ():
    summaries = [summary for _n, _f, summary in DESIGNS.values()]
    assert len(set(summaries)) == 3
    assert all(len(s) > 80 for s in summaries)


def test_the_rail_design_is_laid_out_in_the_rails_they_sell():
    """A bay is a rail here, the same way a bay is a panel on the other side."""
    fence = DESIGNS["rails"][1]()
    assert fence.bay_ft == POST_AND_RAIL_LENGTHS_FT[0] == 8.0
    lengths = sorted(
        round(s.length / (12 * IN), 2)
        for s in fence.spans()
        if s.kind == "panel"
    )
    # The run is 38 ft in two halves either side of the gate sections, and each
    # half is two 8 ft rails and a 3 ft remainder that a rail can be cut to.
    assert lengths == [3.0, 3.0, 8.0, 8.0, 8.0, 8.0]


def test_the_rail_design_hangs_mesh_and_the_panels_do_not():
    parts = {
        key: {p.label for p in extract(factory().build())}
        for key, (_n, factory, _s) in DESIGNS.items()
    }
    assert "mesh" in parts["rails"]
    assert "mesh" not in parts["privacy"]
    assert "mesh" not in parts["chestnut"]


def test_a_short_bay_is_explained_rather_than_left_to_be_noticed():
    fence = DESIGNS["rails"][1]()
    layout = [
        f for f in fence.check(fence.build(), extract(fence.build())).findings
        if f.code == "layout"
    ]
    assert any("cut" in f.message for f in layout)


def test_the_comparison_names_all_three_and_prices_none_of_them():
    text = compare_designs()
    for name, _factory, _summary in DESIGNS.values():
        assert name in text
    # The catalogue prices none of the three; the money in the wood column is
    # the wood at the sawn guide's rates, and it is marked as a floor.
    assert "publishes no price for any of" in text
    assert text.count("+") >= 3
    assert "quoted by email" in text


# ---------------------------------------------------------------------------
# Hardware: the half of a fence that a cut list cannot describe
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def rails() -> CedarFence:
    """Return the post-and-rail design, the one that buys its own hardware."""
    return DESIGNS["rails"][1]()


@pytest.fixture(scope="module")
def rail_hardware(rails: CedarFence) -> HardwarePlan:
    return rails.hardware(extract(rails.build()))


def _line(plan: HardwarePlan, needle: str):
    return next(ln for ln in plan.lines if needle in ln.label)


def test_hardware_is_counted_from_the_fence_not_typed_in(rails, rail_hardware):
    """Every quantity is a consequence of the geometry above it."""
    leaves = len(rails.gate_openings) * rails.gate_leaves
    assert _line(rail_hardware, "tee hinge").qty == HINGES_PER_LEAF * leaves
    assert _line(rail_hardware, "post cap").qty == len(rails.posts())
    assert _line(rail_hardware, "gate latch").qty == len(rails.gate_openings)


def test_every_quantity_shows_the_arithmetic_behind_it(rail_hardware):
    """A hardware count is the easiest number in a project to get wrong by one."""
    assert all(len(line.why) > 20 for line in rail_hardware.lines)


def test_bolts_and_staples_are_bought_by_the_package_not_the_piece(rail_hardware):
    """You cannot buy 24 carriage bolts; you buy a box of 25 and have one left."""
    bolts = _line(rail_hardware, "carriage bolts")
    assert bolts.pieces == BOLTS_PER_HINGE * _line(rail_hardware, "tee hinge").qty
    assert bolts.qty == 1
    assert bolts.pieces > bolts.stock.count_per_unit - 5
    staples = _line(rail_hardware, "fence staples")
    assert staples.qty == staples.stock.packages_for(staples.pieces)


def test_the_keg_of_staples_is_stocked_so_the_design_can_advise_against_it(rails):
    """It is ten times the staples at six times the price of the right box."""
    keg = hardware_stock(rails.inventory, 'fence staples, 9 ga, 1-3/4", knurled')
    box = hardware_stock(rails.inventory, 'fence staples, 9 ga, 1-1/2", galvanised')
    assert keg.count_per_unit > 3000
    assert box.count_per_unit < 500
    findings = rails.check(rails.build(), extract(rails.build())).findings
    advice = [f for f in findings if f.code == "hardware"]
    assert any("not the bucket" in f.message for f in advice)
    assert any(f.severity is Severity.WARN for f in advice)


def test_the_stone_is_the_hole_less_the_post(rails):
    """Nine holes minus nine posts, which is a fifth of a yard here."""
    holes = post_stone_cuyd(rails.posts(), round_posts=True)
    naive = post_stone_cuyd(
        rails.posts()
    )  # square posts displace more, so less stone
    assert holes > naive
    assert 0.5 < holes < 1.0
    assert _line(rails.hardware([]), "crushed").qty == 1


def test_a_tier_is_a_bet_on_hinges(rails):
    """Nearly the whole swing between the two tiers is the hinges."""
    parts = extract(rails.build())
    totals = {
        tier: rails.hardware(parts, tier).cost_summary.total
        for tier in HARDWARE_TIERS
    }
    dear, cheap = totals["heavy duty"], totals["budget"]
    assert dear > cheap * 1.5
    hinges = {
        tier: _line(rails.hardware(parts, tier), "tee hinge").price_line.amount
        for tier in HARDWARE_TIERS
    }
    assert hinges["heavy duty"] - hinges["budget"] > 0.6 * (dear - cheap)


def test_an_unknown_tier_is_refused_rather_than_quietly_priced(rails):
    with pytest.raises(ValueError, match="tier must be one of"):
        rails.hardware([], "whatever is cheapest")


def test_hardware_is_in_the_total_now(rails):
    """It used to be a warning saying it was in no total, which is not the same."""
    parts = extract(rails.build())
    with_gear = rails.cost_summary(parts).total
    timber_and_mesh = rails.plan(parts).cost_summary + rails.mesh_plan(parts).cost_summary
    assert with_gear > timber_and_mesh.total
    assert with_gear - timber_and_mesh.total == pytest.approx(
        rails.hardware(parts).cost_summary.total
    )


def test_every_hardware_price_carries_the_day_it_was_true(rail_hardware):
    """Which is the whole reason these are in stock.yaml and not in the code."""
    summary = rail_hardware.cost_summary
    assert summary.complete
    assert summary.verified
    assert all(
        "relayed by the owner" in line.source or "owner's estimate" in line.source
        for line in summary.lines
    )


def test_a_panel_fence_buys_stone_and_almost_nothing_else():
    """Its gates arrive hung and its caps come with AVO's posts."""
    order = DESIGNS["privacy"][1]().order()
    assert len(order.priced) == 1
    assert "crushed" in order.priced[0].label
    assert order.cost_summary.total == pytest.approx(order.priced[0].amount)
    # Still incomplete — the panels themselves carry no published price.
    assert not order.cost_summary.complete


def test_the_comparison_prices_the_hardware_it_cannot_price_the_panels():
    text = compare_designs()
    assert "hardware" in text
    assert "–" in text  # the budget-to-heavy range on the post-and-rail row
