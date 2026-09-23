"""Tests for the basement wall bench — braced 2x4 side frames, rim-hung totes."""

from __future__ import annotations

import itertools
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from build123d import Box, Pos

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "projects"))

import basement_bench  # noqa: E402
from basement_bench import (  # noqa: E402
    BIN_TYPES,
    IN,
    LAG_SHEAR_LB,
    BasementBench,
    inches,
    lag_withdrawal_lb_per_in,
    pounds_force,
)

from woodshop.checks import Severity  # noqa: E402
from woodshop.cutlist.extract import extract  # noqa: E402


@pytest.fixture(scope="module")
def bench() -> BasementBench:
    return BasementBench()


@pytest.fixture(scope="module")
def built(bench):
    return bench.build()


@pytest.fixture(scope="module")
def parts(built) -> list:
    return extract(built)


@pytest.fixture(scope="module")
def legged() -> BasementBench:
    return BasementBench(mount="legged")


def _members(assembly, label):
    return [c for c in assembly.leaves if getattr(c, "label", "") == label]


def _qty(parts, label):
    return sum(p.qty for p in parts if p.label == label)


def _tote_path(bench, bay, tier):
    """Return the space one tote sweeps from its seat out past the front.

    Its rim, full width, from the lid down to the underside of the lip; its
    body, narrower by the lip each side, below that.
    """
    bin_ = bench.bay_bins[bay]
    z0, z1 = bench.tote_z(bay, tier)
    lip_z = z1 - inches(bin_.lip_drop_in)
    back = -(bench.wall_cleat_t + inches(bench.bin_back_clearance_in))
    front = -(bench.overall_d + 500.0)
    cx = bench.bay_centre_x(bay)
    cy = (back + front) / 2
    rim = Pos(cx, cy, (lip_z + z1) / 2) * Box(
        inches(bin_.width_in), back - front, z1 - lip_z
    )
    body = Pos(cx, cy, (z0 + lip_z) / 2) * Box(
        inches(bin_.body_w_in), back - front, lip_z - z0
    )
    return [rim, body]


# ---------------------------------------------------------------------------
# The totes
# ---------------------------------------------------------------------------


def test_the_16gal_tote_is_the_wide_long_one_and_the_17gal_the_tall_one(bench):
    assert bench.tallest.key == "17gal"
    assert bench.widest.key == "16gal"
    assert bench.longest.key == "16gal"


def test_every_published_tote_dimension_carries_a_source_and_a_date():
    for bin_ in BIN_TYPES.values():
        assert bin_.source
        assert bin_.lip_source
        assert bin_.read_on.startswith("2026-")


def test_the_lip_is_flagged_as_not_measured_and_the_report_says_so(bench):
    assert not any(b.lip_measured for b in BIN_TYPES.values())
    assert any("put a tape on it" in f.message for f in bench._rack_findings())


def test_a_totes_body_is_narrower_than_its_rim_by_the_lip(bench):
    for bin_ in BIN_TYPES.values():
        assert bin_.body_w_in == pytest.approx(bin_.width_in - 2 * bin_.lip_in)


# ---------------------------------------------------------------------------
# The envelope
# ---------------------------------------------------------------------------


def test_the_bench_is_the_published_size(bench, built):
    bb = built.bounding_box()
    assert bb.size.X == pytest.approx(90 * IN, abs=0.1)
    assert bb.size.Y == pytest.approx(bench.overall_d, abs=0.1)
    assert bb.max.Z == pytest.approx(40 * IN, abs=0.1)


def test_the_depth_is_derived_from_the_longest_tote(bench):
    assert bench.overall_d_in is None
    assert bench.overall_d == pytest.approx(
        bench.wall_cleat_t
        + (
            bench.bin_back_clearance_in
            + bench.longest.length_in
            + bench.top_overhang_front_in
        )
        * IN
        + bench.apron_t
    )
    assert bench.tote_run >= bench.longest.length_in * IN


def test_a_shallow_bench_will_not_take_the_longest_tote():
    with pytest.raises(ValueError, match="long and the rack is only"):
        BasementBench(overall_d_in=24.0)


def test_a_depth_that_was_given_rather_than_derived_is_flagged():
    deep = BasementBench(overall_d_in=40.0)
    assert any(
        f.severity is Severity.WARN and "rather than derived" in f.message
        for f in deep._depth_findings()
    )


def test_the_wall_is_at_y_zero_and_the_room_is_minus_y(bench, built):
    """The repo's convention, which the gallery's Front camera looks along.

    The last version had it backwards, so every view showed the bench from
    inside the wall and the bottom cleat read as a kickboard.
    """
    bb = built.bounding_box()
    assert bb.max.Y == pytest.approx(0.0, abs=0.01)
    apron = _members(built, "front_apron")[0].bounding_box()
    cleat = _members(built, "bottom_cleat")[0].bounding_box()
    assert apron.max.Y < -bench.frame_d + bench.apron_t + 0.01
    assert cleat.max.Y == pytest.approx(0.0, abs=0.01)


def test_nothing_in_the_hung_build_touches_the_floor(bench, built):
    bb = built.bounding_box()
    assert bb.min.Z == pytest.approx(bench.rack_bottom_z, abs=0.1)
    assert bb.min.Z > 3 * IN


def test_the_legged_build_reaches_the_floor_and_nothing_else_moves(bench, legged):
    assert legged.build().bounding_box().min.Z == pytest.approx(0.0, abs=0.1)
    assert legged.top_height == bench.top_height
    assert legged.rack_bottom_z == pytest.approx(bench.rack_bottom_z)
    assert [b.key for b in legged.bay_bins] == [b.key for b in bench.bay_bins]


def test_a_deep_bench_admits_it_is_past_a_comfortable_reach(bench):
    assert bench.reach_over > 0
    assert any(
        f.code == "ergonomics" and f.severity is Severity.WARN
        for f in bench._depth_findings()
    )


# ---------------------------------------------------------------------------
# Getting a tote in and out
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mount", ["hung", "legged"])
def test_every_tote_slides_in_from_the_front_without_touching_anything(mount):
    """The kickboard, and the tier ties before it.

    The last version hung a 3/4" tie across the front of every tier into a
    1/2" head clearance, and each tote below it hit the tie 1/4" deep.  Here
    the tote's own profile is swept from its seat out past the front of the
    top, against every part of the bench.
    """
    b = BasementBench(mount=mount)
    leaves = list(b.build().leaves)
    for bay, bin_ in enumerate(b.bay_bins):
        for tier in range(b.tiers_for(bin_)):
            for path in _tote_path(b, bay, tier):
                for leaf in leaves:
                    assert (path & leaf).volume < 1.0, (bay, tier, leaf.label)


def test_nothing_spans_a_bay_below_the_top_except_the_apron(bench, built):
    across = [
        c
        for c in built.leaves
        if c.bounding_box().size.X > bench.bay_clear_w(0)
        and c.bounding_box().max.Z < bench.top_underside_z + 0.01
    ]
    labels = {c.label for c in across}
    assert labels == {"top_cleat", "bottom_cleat", "front_apron"}
    for c in across:
        if c.label != "front_apron":
            assert c.bounding_box().min.Y > -bench.wall_cleat_t - 0.01
    apron = _members(built, "front_apron")[0].bounding_box()
    assert apron.min.Z == pytest.approx(bench.rack_top_z, abs=0.01)


@pytest.mark.parametrize("mount", ["hung", "legged"])
def test_no_two_parts_occupy_the_same_wood(mount):
    leaves = list(BasementBench(mount=mount).build().leaves)
    for a, c in itertools.combinations(leaves, 2):
        ba, bc = a.bounding_box(), c.bounding_box()
        if (
            ba.min.X >= bc.max.X
            or bc.min.X >= ba.max.X
            or ba.min.Y >= bc.max.Y
            or bc.min.Y >= ba.max.Y
            or ba.min.Z >= bc.max.Z
            or bc.min.Z >= ba.max.Z
        ):
            continue
        assert (a & c).volume < 1.0, (a.label, c.label)


def test_a_runner_costs_no_height_per_tier(bench):
    for bin_ in dict.fromkeys(bench.bay_bins):
        assert bench._tight_tier_pitch(bin_) == pytest.approx(
            (bin_.height_in + bench.bin_head_clearance_in) * IN
        )
    assert bench.rack_h == pytest.approx(30.0 * IN)


def test_the_runner_top_is_the_underside_of_the_lip(bench):
    for bay, bin_ in enumerate(bench.bay_bins):
        for tier in range(bench.tiers_for(bin_)):
            lid = bench.tote_z(bay, tier)[1]
            assert bench.runner_z(bay, tier)[1] == pytest.approx(
                lid - bin_.lip_drop_in * IN
            )


def test_the_lip_bears_on_the_runners_and_the_body_clears_them(bench):
    for bin_ in dict.fromkeys(bench.bay_bins):
        assert bench.lip_bearing(bin_) == pytest.approx(0.375 * IN)
        assert bench.body_clearance(bin_) == pytest.approx(0.875 * IN)


def test_bays_are_sized_exactly_and_the_slack_goes_to_the_overhang():
    """Slack spread into a bay would come straight off the lip's bearing."""
    roomy = BasementBench(bins=("16gal",), bay_layout=None, n_bays=2)
    assert roomy.end_overhang > 10 * IN
    for bay, bin_ in enumerate(roomy.bay_bins):
        assert roomy.bay_clear_w(bay) == pytest.approx(roomy.bay_cell(bin_))
    assert any(
        f.severity is Severity.WARN and "overhangs each end" in f.message
        for f in roomy._depth_findings()
    )


def test_too_much_side_clearance_drops_the_tote_between_the_runners():
    with pytest.raises(ValueError, match="falls between the runners"):
        BasementBench(bin_side_clearance_in=0.75, overall_w_in=100.0)


def test_a_lip_too_small_for_the_runners_binds_the_body(monkeypatch):
    stubby = {k: replace(b, lip_in=0.25) for k, b in BIN_TYPES.items()}
    monkeypatch.setattr(basement_bench, "BIN_TYPES", stubby)
    with pytest.raises(ValueError, match="binds on the runners"):
        BasementBench()


def test_the_non_driving_tote_rides_with_extra_headroom(bench):
    driver = bench._driving_bin
    other = next(b for b in dict.fromkeys(bench.bay_bins) if b is not driver)
    assert driver.key == "16gal"
    assert bench.head_clearance(driver) == pytest.approx(
        bench.bin_head_clearance_in * IN
    )
    assert bench.head_clearance(other) > bench.head_clearance(driver)


def test_the_report_says_neither_tote_fits_the_others_bay(bench):
    """What the last version claimed the opposite of."""
    messages = [f.message for f in bench._rack_findings()]
    assert any("only goes in a bay of its own kind" in m for m in messages)
    assert not any("any tote go in any slot" in m for m in messages)
    sixteen, seventeen = BIN_TYPES["16gal"], BIN_TYPES["17gal"]
    assert bench.tier_pitch_for(sixteen) < seventeen.height_in * IN
    assert bench.bay_cell(seventeen) < sixteen.width_in * IN


def test_the_rack_holds_what_it_says_and_open_bays_cost_totes(bench):
    assert bench.n_bins == sum(bench.tiers_for(b) for b in bench.bay_bins)
    opened = BasementBench(open_bays=(1,))
    assert opened.n_bins == bench.n_bins - bench.tiers_for(bench.bay_bins[1])


def test_an_open_bay_takes_its_runners_out_of_the_model(bench, parts):
    opened = extract(BasementBench(open_bays=(1,)).build())
    lost = 2 * bench.tiers_for(bench.bay_bins[1])
    assert _qty(opened, "runner") == _qty(parts, "runner") - lost


def test_a_fourth_sixteen_gallon_tier_does_not_fit_and_is_refused():
    with pytest.raises(ValueError, match="below the slab"):
        BasementBench(tier_counts={"16gal": 4, "17gal": 2})


# ---------------------------------------------------------------------------
# Bays and the packer
# ---------------------------------------------------------------------------


def test_the_default_layout_is_two_dedicated_bays_each(bench):
    assert bench.derived_n_bays == 4
    assert [b.key for b in bench.bay_bins] == ["16gal", "16gal", "17gal", "17gal"]


def test_a_bay_layout_naming_too_few_bays_is_refused():
    with pytest.raises(ValueError, match="fewer than two bays"):
        BasementBench(bay_layout=("16gal",))


def test_the_report_says_bay_layout_overrode_the_packer(bench):
    assert any(
        "bay_layout reserves" in f.message and "16 gal" in f.message
        for f in bench._rack_findings()
    )


def test_the_packer_alone_gives_the_brief_no_17gal_bay_at_all():
    auto = BasementBench(overall_w_in=80.0, bay_layout=None)
    assert {b.key for b in auto.bay_bins} == {"16gal"}


def test_whether_the_packer_mixes_them_depends_on_width_not_intent():
    widths = {
        w: {b.key for b in BasementBench(overall_w_in=w, bay_layout=None).bay_bins}
        for w in (80, 88, 96)
    }
    assert len({frozenset(keys) for keys in widths.values()}) > 1


def test_a_dedicated_layout_that_does_not_fit_says_how_wide_to_go():
    with pytest.raises(ValueError, match="widen to at least 8"):
        BasementBench(overall_w_in=80.0)


def test_forcing_a_bin_type_alone_still_gives_a_valid_layout():
    only_17 = BasementBench(bins=("17gal",), bay_layout=None)
    assert only_17.derived_n_bays >= 2
    assert {b.key for b in only_17.bay_bins} == {"17gal"}


def test_a_bay_layout_naming_an_unavailable_bin_is_refused():
    with pytest.raises(ValueError, match="not in bins"):
        BasementBench(bins=("16gal",), bay_layout=("17gal", "17gal"))


def test_a_bay_too_narrow_for_any_tote_is_refused():
    with pytest.raises(ValueError, match="fewer than two"):
        BasementBench(bins=("16gal",), bay_layout=None, bin_side_clearance_in=30.0)


# ---------------------------------------------------------------------------
# The frames, the cleats and the top
# ---------------------------------------------------------------------------


def test_every_frame_has_an_arm_from_the_studs_to_the_apron(bench, built):
    """The top's substructure: without the top, every frame still stands."""
    arms = _members(built, "arm")
    assert len(arms) == bench.n_frames
    for arm in arms:
        bb = arm.bounding_box()
        assert bb.max.Y == pytest.approx(0.0, abs=0.01)
        assert bb.min.Y == pytest.approx(-(bench.frame_d - bench.apron_t), abs=0.01)
        assert bb.max.Z == pytest.approx(bench.top_underside_z, abs=0.01)


def test_the_top_is_screwed_to_the_frame_and_glued_to_nothing_below_it(built):
    for label in ("top_skin", "top_surface"):
        assert "never glued" in _members(built, label)[0].notes


def test_the_top_is_two_glued_layers_under_one_screwed_one(bench, parts):
    assert _qty(parts, "top_skin") == 2
    assert _qty(parts, "top_surface") == 1
    assert bench.structural_top_t < bench.top_t


def test_the_back_stile_hangs_on_the_top_cleat(bench, built):
    """The notch is closed above the cleat, so the stile hooks over it.

    The last version's notch opened through the top of the divider, and
    nothing held the rack up but screws into its end grain.
    """
    z_top = bench.top_cleat_z[1]
    for i, stile in enumerate(_members(built, "back_stile")):
        x = bench.frame_x(i)
        above = Pos(x, -bench.wall_cleat_t / 2, z_top + 10.0) * Box(
            bench.stile_t, bench.wall_cleat_t, 20.0
        )
        assert (above & stile).volume > 0.0
        inside = Pos(x, -bench.wall_cleat_t / 2, z_top - 10.0) * Box(
            bench.stile_t, bench.wall_cleat_t, 20.0
        )
        assert (inside & stile).volume == pytest.approx(0.0, abs=1.0)


def test_both_cleats_sit_flat_on_the_studs_across_the_whole_frame(bench, built):
    for label in ("top_cleat", "bottom_cleat"):
        bb = _members(built, label)[0].bounding_box()
        assert bb.max.Y == pytest.approx(0.0, abs=0.01)
        assert bb.size.Y == pytest.approx(bench.wall_cleat_t, abs=0.01)
        assert bb.size.X == pytest.approx(bench.frame_w, abs=0.01)


def test_a_back_stile_is_two_cleat_notches_and_a_half_lap(bench, built):
    stile = _members(built, "back_stile")[0]
    blank = bench.stile_h * bench.stile_w * bench.stile_t
    notches = 2 * bench.wall_cleat_w * bench.wall_cleat_t * bench.stile_t
    lap = bench.stile_w * bench.stile_w * bench.stile_t / 2
    assert stile.volume == pytest.approx(blank - notches - lap, rel=1e-3)


def test_each_runner_is_lapped_onto_both_stiles(bench, built):
    fs0, fs1 = bench.front_stile_d
    for runner in _members(built, "runner"):
        bb = runner.bounding_box()
        assert -bb.max.Y < bench.stile_w
        assert -bb.min.Y == pytest.approx(fs1, abs=0.01)
        assert runner.volume == pytest.approx(
            bench.runner_len * bench.runner_h * bench.runner_t, rel=1e-3
        )


def test_the_hung_build_braces_every_frame_and_the_legged_one_does_not(
    bench, parts, legged
):
    assert _qty(parts, "brace") == bench.n_frames
    assert _qty(extract(legged.build()), "brace") == 0


def test_a_brace_stays_inside_its_frame(bench, built):
    for i, brace in enumerate(_members(built, "brace")):
        bb = brace.bounding_box()
        assert bb.size.X == pytest.approx(bench.stile_t, abs=0.01)
        assert bb.min.X == pytest.approx(bench.frame_x(i) - bench.stile_t / 2, abs=0.01)
        assert -bb.max.Y == pytest.approx(bench.stile_w, abs=0.01)
        assert -bb.min.Y == pytest.approx(bench.front_stile_d[0], abs=0.01)
        assert bb.min.Z == pytest.approx(bench.frame_bottom_z, abs=0.01)
        assert bb.max.Z == pytest.approx(bench.arm_bottom_z, abs=0.01)


def test_the_kit(parts):
    assert {p.label for p in parts} == {
        "top_skin",
        "top_surface",
        "top_cleat",
        "bottom_cleat",
        "back_stile",
        "front_stile",
        "arm",
        "brace",
        "runner",
        "front_apron",
    }


def test_one_frame_per_bay_boundary_and_two_runners_per_bay_per_tier(bench, parts):
    tiers = sum(bench.tiers_for(b) for b in bench.bay_bins)
    for label in ("back_stile", "front_stile", "arm"):
        assert _qty(parts, label) == bench.n_frames
    assert _qty(parts, "runner") == 2 * tiers


def test_the_legged_build_adds_foot_rails(parts, legged):
    assert _qty(extract(legged.build()), "foot_rail") == 2
    assert _qty(parts, "foot_rail") == 0


def test_no_plywood_below_the_top(parts):
    for p in parts:
        if p.label not in {"top_skin", "top_surface"}:
            assert p.material == "pine"


# ---------------------------------------------------------------------------
# The wall and the bracket
# ---------------------------------------------------------------------------


def test_ninety_inches_is_six_studs_with_a_real_end_distance(bench):
    studs = bench.stud_positions
    assert len(studs) == 6
    left = studs[0] - bench.frame_x0
    right = bench.frame_x0 + bench.frame_w - studs[-1]
    assert left == pytest.approx(right)
    assert left > 4 * bench.lag_diameter_in * IN


def test_furring_strips_are_an_error_not_a_warning():
    furred = BasementBench(stud_nominal="1x3")
    assert furred.studs_are_furring
    findings = furred._stud_findings()
    assert any(f.severity is Severity.ERROR for f in findings)
    assert any("concrete anchors" in f.message for f in findings)


def test_a_wall_with_no_studs_behind_the_cleat_is_an_error():
    homeless = BasementBench(first_stud_offset_in=500.0)
    assert homeless.stud_positions == []
    assert [f.severity for f in homeless._stud_findings()] == [Severity.ERROR]


def test_a_lag_landing_behind_a_stile_is_told_to_counterbore(bench):
    clash = BasementBench(
        first_stud_offset_in=(bench.frame_x(1) - bench.frame_x0) / IN
    )
    assert any("counterbore" in f.message for f in clash._stud_findings())


def test_the_bracket_depth_is_centroid_to_centroid_of_the_cleats(bench):
    cleats = sum(bench.top_cleat_z) / 2 - sum(bench.bottom_cleat_z) / 2
    assert bench.bracket_depth == pytest.approx(cleats)
    assert bench.bracket_depth > 4.0 * bench.wall_cleat_w


def test_a_deeper_bracket_is_a_lighter_pull_on_the_same_lags(bench, parts):
    moment = bench.overturning_moment_nmm(parts)
    assert moment / bench.bracket_depth < moment / bench.wall_cleat_w / 4.0


def test_the_lags_are_not_the_limit_and_shear_is_tighter_than_pull_out(bench, parts):
    n_lags = len(bench.stud_positions) * bench.lags_per_stud
    pull_lb = pounds_force(
        bench.overturning_moment_nmm(parts) / bench.bracket_depth
    ) / n_lags
    capacity_lb = (
        lag_withdrawal_lb_per_in(diameter_in=bench.lag_diameter_in)
        * bench.lag_penetration
        / IN
    )
    assert capacity_lb / pull_lb > 4.0
    shear_lb = pounds_force(bench.total_load_n(parts)) / n_lags
    shear_ratio = LAG_SHEAR_LB[bench.lag_diameter_in] / shear_lb
    assert 1.0 < shear_ratio < capacity_lb / pull_lb


def test_one_lag_per_stud_runs_a_margin_this_bench_should_not():
    thin = BasementBench(lags_per_stud=1)
    findings = thin._wall_findings(extract(thin.build()))
    shear = next(f for f in findings if f.message.startswith("shear:"))
    assert shear.severity is Severity.WARN
    assert "lags_per_stud=2" in shear.message


def test_an_untabulated_lag_is_not_checked_rather_than_interpolated():
    odd = BasementBench(lag_diameter_in=0.625)
    assert 0.625 not in LAG_SHEAR_LB
    findings = odd._wall_findings(extract(odd.build()))
    assert any("not checked" in f.message for f in findings)


def test_the_stile_screws_are_the_tension_connection_and_have_margin(bench, parts):
    joint = next(
        f
        for f in bench._wall_findings(parts)
        if f.message.startswith("the back stiles into the top cleat")
    )
    assert joint.severity is Severity.INFO
    few = BasementBench(stile_screws_per_cleat=1)
    weak = next(
        f
        for f in few._wall_findings(extract(few.build()))
        if f.message.startswith("the back stiles into the top cleat")
    )
    assert weak.severity is not Severity.INFO
    assert "stile_screws_per_cleat=3" in weak.message


def test_the_brace_is_checked_in_the_hung_build_only(bench, parts, legged):
    marker = "the busiest frame's brace"
    hung = [f for f in bench._wall_findings(parts) if f.message.startswith(marker)]
    assert len(hung) == 1 and hung[0].severity is Severity.INFO
    assert not any(
        f.message.startswith(marker)
        for f in legged._wall_findings(extract(legged.build()))
    )


def test_the_leaning_load_is_the_one_that_sizes_the_wall(bench, parts):
    cases = {name: (kg, arm) for name, kg, arm in bench._load_cases(parts)}
    leaning = "somebody leaning on the front edge"
    assert cases[leaning][1] == bench.overall_d
    assert cases[leaning][1] == max(arm for _, arm in cases.values())


def test_a_runner_is_checked_as_the_span_it_really_is(bench):
    """Between its two stiles — both of them real supports.

    The last version checked a rail as simply supported because it was
    tied to its twin at the front, which by symmetry supports nothing.
    """
    runner = [f for f in bench._stiffness_findings() if "a runner" in f.message]
    assert len(runner) == 1
    assert runner[0].severity is Severity.INFO
    assert bench.brace_run == pytest.approx(
        bench.front_stile_d[0] - bench.stile_w
    )


# ---------------------------------------------------------------------------
# The report as a whole
# ---------------------------------------------------------------------------


def test_the_shipped_bench_has_no_errors(bench, built, parts):
    assert bench.check(built, parts).ok


def test_the_shipped_bench_warns_about_exactly_what_it_should(bench, built, parts):
    """Every WARN by design, and no more.

    No bay left open, a deep bench reaches past a comfortable distance, a
    lag at this width lands behind a stile's notch, the wall joint is what
    moves under real use, the plywood is thinner than sold, and nobody
    knows what is in those stud bays.
    """
    report = bench.check(built, parts)
    codes = sorted({f.code for f in report.findings if f.severity is Severity.WARN})
    assert codes == ["deflection", "ergonomics", "rack", "site", "thickness", "wall"]


def test_opening_a_bay_answers_the_no_knee_space_warning():
    opened = BasementBench(open_bays=(1,))
    assembly = opened.build()
    report = opened.check(assembly, extract(assembly))
    assert not any(
        f.severity is Severity.WARN and f.code == "rack" for f in report.findings
    )


def test_the_legged_build_swaps_a_floor_warning_for_the_hung_ones(legged):
    assembly = legged.build()
    messages = [f.message for f in legged.check(assembly, extract(assembly)).findings]
    assert any("slab that wicks" in m for m in messages)
    assert not any("nothing touches the slab" in m for m in messages)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_both_builds_are_in_the_gallery():
    from woodshop.project import discover_projects

    slugs = {s.slug for s in discover_projects()}
    assert {"basement-bench-hung", "basement-bench-legged"} <= slugs
