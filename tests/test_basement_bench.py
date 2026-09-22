"""Tests for the basement wall bench — 2x4 dividers and rails on a bracket."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "projects"))

from basement_bench import (  # noqa: E402
    BIN_TYPES,
    IN,
    LAG_SHEAR_LB,
    BasementBench,
    lag_withdrawal_lb_per_in,
    pounds_force,
)

from woodshop.checks import Severity  # noqa: E402
from woodshop.cutlist.extract import extract  # noqa: E402


@pytest.fixture(scope="module")
def bench() -> BasementBench:
    return BasementBench()


@pytest.fixture(scope="module")
def parts(bench) -> list:
    return extract(bench.build())


@pytest.fixture(scope="module")
def legged() -> BasementBench:
    return BasementBench(mount="legged")


# ---------------------------------------------------------------------------
# The totes
# ---------------------------------------------------------------------------


def test_each_tote_governs_the_dimension_it_wins_on(bench):
    """The 16-gallon tote is now both wider and longer than the 17-gallon.

    So it — not the 17-gallon — sets the bay width and the bench depth; the
    17-gallon, being taller, still sets the tier pitch.
    """
    assert bench.tallest.key == "17gal"
    assert bench.widest.key == "16gal"
    assert bench.longest.key == "16gal"


def test_the_depth_is_derived_from_the_longest_tote(bench):
    longest = bench.longest
    assert bench.overall_d_in is None
    assert bench.overall_d == pytest.approx(
        (longest.length_in + bench.bin_back_clearance_in + bench.top_overhang_front_in)
        * IN
        + bench.ledger_t
    )
    assert bench.rail_run >= longest.length_in * IN


def test_a_shallow_bench_will_not_take_the_longest_tote():
    with pytest.raises(ValueError, match="long and the rack is only"):
        BasementBench(overall_d_in=24.0)


def test_a_depth_that_was_given_rather_than_derived_is_flagged():
    deep = BasementBench(overall_d_in=40.0)
    assert any(
        f.severity is Severity.WARN and "rather than derived" in f.message
        for f in deep._depth_findings()
    )


def test_every_published_tote_dimension_carries_a_source_and_a_date():
    for bin_ in BIN_TYPES.values():
        assert bin_.source
        assert bin_.read_on.startswith("2026-")


def test_the_16gal_totes_base_is_estimated_not_measured():
    """The estimate is flagged so the report can say so.

    No interior figure is published for the 16-gallon tote.
    """
    assert BIN_TYPES["16gal"].interior_measured is False
    assert BIN_TYPES["17gal"].interior_measured is True


def test_a_totes_base_is_much_narrower_than_its_rim():
    for bin_ in BIN_TYPES.values():
        assert bin_.base_w_in < bin_.width_in - 2.0


# ---------------------------------------------------------------------------
# The envelope
# ---------------------------------------------------------------------------


def test_the_bench_is_the_published_size(bench):
    bb = bench.build().bounding_box()
    assert bb.size.X == pytest.approx(90 * IN, abs=0.1)
    assert bb.size.Y == pytest.approx(bench.overall_d, abs=0.1)
    assert bb.max.Z == pytest.approx(40 * IN, abs=0.1)


def test_nothing_in_the_hung_build_touches_the_floor(bench):
    bb = bench.build().bounding_box()
    assert bb.min.Z == pytest.approx(bench.lowest_point_z, abs=0.1)
    assert bb.min.Z > 0.0


def test_the_legged_build_reaches_the_floor_and_nothing_else_moves(bench, legged):
    assert legged.build().bounding_box().min.Z == pytest.approx(0.0, abs=0.1)
    assert legged.top_height == bench.top_height
    assert legged.rack_bottom_z == pytest.approx(bench.rack_bottom_z)
    assert [b.key for b in legged.bay_bins] == [b.key for b in bench.bay_bins]


def test_the_back_of_the_bench_is_the_face_of_the_studs(bench):
    assert bench.build().bounding_box().min.Y == pytest.approx(0.0, abs=0.01)


def test_a_deep_bench_admits_it_is_past_a_comfortable_reach(bench):
    assert bench.reach_over > 0
    assert any(
        f.code == "ergonomics" and f.severity is Severity.WARN
        for f in bench._depth_findings()
    )


# ---------------------------------------------------------------------------
# The wall and the bracket — unchanged by the switch to 2x4s
# ---------------------------------------------------------------------------


def test_ninety_inches_is_six_studs_with_a_real_end_distance(bench):
    studs = bench.stud_positions
    assert len(studs) == 6
    left = studs[0] - bench.frame_x0
    right = bench.frame_x0 + bench.frame_w - studs[-1]
    assert left == pytest.approx(4 * IN)
    assert right == pytest.approx(4 * IN)
    assert left > 4 * bench.lag_diameter_in * IN


def test_furring_strips_are_an_error_not_a_warning():
    furred = BasementBench(stud_nominal="1x3")
    assert furred.studs_are_furring
    findings = furred._stud_findings()
    assert any(f.severity is Severity.ERROR for f in findings)
    assert any("concrete anchors" in f.message for f in findings)


def test_a_wall_with_no_studs_under_the_ledger_is_an_error():
    homeless = BasementBench(first_stud_offset_in=500.0)
    assert homeless.stud_positions == []
    assert [f.severity for f in homeless._stud_findings()] == [Severity.ERROR]


def test_a_lag_landing_under_a_divider_is_told_to_counterbore():
    bench = BasementBench()
    clash = BasementBench(first_stud_offset_in=bench.divider_x(1) / IN - 1.0)
    assert any("counterbore" in f.message for f in clash._stud_findings())


def test_the_bracket_depth_does_not_depend_on_what_spans_between_the_ledgers(bench):
    """The whole point of the redesign.

    Swapping the plywood rack for 2x4s changes nothing about the lever arm,
    because it only depends on where the two ledgers sit.
    """
    only_ledgers = (
        sum(bench.top_ledger_z) / 2 - sum(bench.rack_ledger_z) / 2
    )
    assert bench.bracket_depth == pytest.approx(only_ledgers)
    assert bench.bracket_depth > 4.0 * bench.ledger_w


def test_a_deeper_bracket_is_a_lighter_pull_on_the_same_lags(bench, parts):
    moment = bench.overturning_moment_nmm(parts)
    assert moment / bench.bracket_depth < moment / bench.ledger_w / 4.0


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


def test_one_lag_per_stud_runs_a_margin_this_bench_should_not(parts):
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


def test_the_leaning_load_is_the_one_that_sizes_the_wall(bench, parts):
    cases = {name: (kg, arm) for name, kg, arm in bench._load_cases(parts)}
    leaning = "somebody leaning on the front edge"
    assert cases[leaning][1] == bench.overall_d
    assert cases[leaning][1] == max(arm for _, arm in cases.values())


# ---------------------------------------------------------------------------
# The rack: bays, rails, and the taper that decided the layout
# ---------------------------------------------------------------------------


def test_the_default_layout_is_two_dedicated_bays_each(bench):
    """The whole reason for the extra 10" of width.

    Left to the auto-packer, whether these two totes share a rack at all is
    an accident of width — see test_the_packer_alone_gives_the_brief_no_17gal
    _bay_at_all. bay_layout makes the mix explicit instead.
    """
    assert bench.derived_n_bays == 4
    assert [b.key for b in bench.bay_bins] == ["16gal", "16gal", "17gal", "17gal"]


def test_a_bay_layout_naming_too_few_bays_is_refused():
    with pytest.raises(ValueError, match="fewer than two bays"):
        BasementBench(bay_layout=("16gal",))


def test_the_report_says_bay_layout_overrode_the_packer(bench):
    findings = bench._rack_findings()
    assert any(
        "bay_layout reserves" in f.message and "16 gal" in f.message
        for f in findings
    )


def test_the_packer_alone_gives_the_brief_no_17gal_bay_at_all():
    """The fact bay_layout exists to work around.

    At the brief's own 80"-wide frame, the auto-packer fills every bay with
    the 16-gallon tote and never reaches for a 17-gallon one — a mix was
    never guaranteed, only ever a possible accident of the width.
    """
    auto = BasementBench(overall_w_in=80.0, bay_layout=None)
    assert {b.key for b in auto.bay_bins} == {"16gal"}


def test_whether_the_packer_mixes_them_depends_on_width_not_intent():
    """A few inches either way flips the packer's answer.

    Which is the point: it is arithmetic about remainders, not a decision
    about what the rack should hold, so it is not something to rely on.
    """
    widths = {w: {b.key for b in BasementBench(overall_w_in=w, bay_layout=None).bay_bins}
              for w in (80, 88, 96)}
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
        BasementBench(
            bins=("16gal",), bay_layout=None, bin_side_clearance_in=30.0
        )


def test_rails_are_spaced_to_the_base_not_the_rim(bench):
    """The mistake the plywood version's own runners made, corrected.

    The rails must end up narrower than the base, and clear of the divider.
    """
    for bay, bin_ in enumerate(bench.bay_bins):
        channel = bench.rail_channel(bay)
        base = bin_.base_w_in * IN
        assert channel < base
        assert bench.bay_clear_w(bay) > bin_.width_in * IN  # rim clears the bay


def test_rail_channel_is_the_same_for_every_bay_of_one_tote(bench):
    """Every bay of one tote type gets the same channel, whatever the mix.

    The default layout leaves almost no slack to test this against, so this
    checks it on a same-type, slack-heavy layout instead: two bays of one
    tote in a 90"-wide frame leaves 40" of slack, and the channel must not
    move with it.
    """
    slack_heavy = BasementBench(
        bins=("16gal",), bay_layout=None, n_bays=2, overall_w_in=90.0
    )
    assert slack_heavy.bay_slack > 30 * IN
    channels = {
        slack_heavy.rail_channel(b) for b in range(slack_heavy.derived_n_bays)
    }
    assert len(channels) == 1


def test_rail_gap_is_independent_of_bay_slack(bench):
    """The bug the first version of this rewrite had.

    A rail flush against the divider follows the bay's slack outward and can
    miss the base; spacing from the tote instead means the channel does not
    change even though bays end up wider than their tote strictly needs.
    Checked per tote type: the default layout mixes two different totes,
    which legitimately get two different channels.
    """
    assert bench.bay_slack > 0
    by_key: dict[str, set[float]] = {}
    for bay, bin_ in enumerate(bench.bay_bins):
        by_key.setdefault(bin_.key, set()).add(bench.rail_channel(bay))
    assert all(len(v) == 1 for v in by_key.values())


def test_zero_bearing_margin_is_refused():
    with pytest.raises(ValueError, match="no channel at all"):
        BasementBench(rail_bearing_margin_in=20.0)


def test_the_non_driving_tote_rides_with_extra_headroom(bench):
    """Whichever tote's tier count does not drive the shared rack height.

    gets the difference back as head room, rather than a cramped fit. Here
    that is the 17-gallon tote: three tiers of the 16-gallon tote need more
    rack height than two tiers of the 17-gallon, so the 16-gallon tiers get
    the bare minimum and the 17-gallon tiers get the surplus.
    """
    driver = max(
        set(bench.bay_bins),
        key=lambda b: bench.tiers_for(b) * bench._tight_tier_pitch(b),
    )
    other = next(b for b in set(bench.bay_bins) if b is not driver)
    assert bench.head_clearance(other) > bench.head_clearance(driver)
    assert bench.head_clearance(driver) == pytest.approx(
        bench.bin_head_clearance_in * IN
    )


def test_the_rack_holds_what_it_says_and_open_bays_cost_totes(bench):
    assert bench.n_bins == sum(bench.tiers_for(b) for b in bench.bay_bins)
    opened = BasementBench(open_bays=(1,))
    assert opened.n_bins == bench.n_bins - bench.tiers_for(bench.bay_bins[1])


def test_an_open_bay_takes_its_rails_out_of_the_model(bench):
    opened = BasementBench(open_bays=(1,))
    rails = [p for p in extract(opened.build()) if p.label == "rail"]
    every_bay = [p for p in extract(bench.build()) if p.label == "rail"]
    lost = 2 * bench.tiers_for(bench.bay_bins[1])
    assert sum(p.qty for p in rails) == sum(p.qty for p in every_bay) - lost


def test_a_fourth_sixteen_gallon_tier_does_not_fit_and_is_refused():
    with pytest.raises(ValueError, match="below the slab"):
        BasementBench(tier_counts={"16gal": 4, "17gal": 2})


# ---------------------------------------------------------------------------
# The cut list
# ---------------------------------------------------------------------------


def test_the_kit_is_eight_kinds_of_part(parts):
    assert {p.label for p in parts} == {
        "top_skin",
        "top_surface",
        "top_ledger",
        "rack_ledger",
        "front_rail",
        "divider",
        "rail",
        "tier_tie",
    }


def test_the_legged_build_adds_foot_rails(bench, legged):
    labels = {p.label for p in extract(legged.build())}
    assert "foot_rail" in labels
    assert "foot_rail" not in {p.label for p in extract(bench.build())}


def test_one_divider_per_bay_boundary_and_two_rails_per_bay_per_tier(bench, parts):
    by_label = {p.label: p for p in parts}
    tiers = sum(bench.tiers_for(b) for b in bench.bay_bins)
    tier_tie_qty = sum(p.qty for p in parts if p.label == "tier_tie")
    assert by_label["divider"].qty == bench.n_dividers
    assert by_label["rail"].qty == 2 * tiers
    assert tier_tie_qty == tiers


def test_the_top_is_two_glued_layers_under_one_screwed_one(bench, parts):
    by_label = {p.label: p for p in parts}
    assert by_label["top_skin"].qty == 2
    assert by_label["top_surface"].qty == 1
    assert by_label["top_surface"].material != by_label["top_skin"].material
    assert bench.structural_top_t < bench.top_t


def test_a_divider_is_notched_at_both_ends_not_dadoed(bench):
    """Two ledger notches out of a rectangle, nothing else.

    No shelf dado, no rebate — which is the whole point of the redesign.
    """
    divider = next(
        c for c in bench.build().children if getattr(c, "label", "") == "divider"
    )
    blank = bench.divider_h * bench.divider_w * bench.divider_t
    notches = 2 * bench.ledger_w * bench.ledger_t * bench.divider_t
    assert divider.volume == pytest.approx(blank - notches, rel=1e-3)


def test_a_rail_is_a_plain_uncut_board(bench):
    """No notch, no dado — just a length of 2x4.

    Which is the entire reason this rack has three kinds of part instead of
    six.
    """
    rail = next(
        c for c in bench.build().children if getattr(c, "label", "") == "rail"
    )
    blank = bench.rail_run * bench.divider_w * bench.divider_t
    assert rail.volume == pytest.approx(blank, rel=1e-3)


def test_no_plywood_below_the_top(parts):
    """The whole ask: everything under the benchtop is dimensional lumber."""
    frame_labels = {"top_ledger", "rack_ledger", "front_rail", "divider", "rail"}
    for p in parts:
        if p.label in frame_labels:
            assert p.material == "pine"


# ---------------------------------------------------------------------------
# The report as a whole
# ---------------------------------------------------------------------------


def test_the_shipped_bench_has_no_errors(bench, parts):
    report = bench.check(bench.build(), parts)
    assert report.ok


def test_the_shipped_bench_warns_about_exactly_what_it_should(bench, parts):
    """Every WARN by design, and no more.

    No bay left open, a deep bench reaches past a comfortable distance, the
    rack rides close to the floor (the cost of stiff-enough rails), a lag at
    this width happens to land under a divider's notch, the wall joint is
    what moves under real use, and nobody knows what is in those stud bays.
    """
    report = bench.check(bench.build(), parts)
    codes = sorted({f.code for f in report.findings if f.severity is Severity.WARN})
    assert codes == [
        "clearance",
        "deflection",
        "ergonomics",
        "rack",
        "site",
        "thickness",
        "wall",
    ]


def test_opening_a_bay_answers_the_no_knee_space_warning():
    opened = BasementBench(open_bays=(1,))
    report = opened.check(opened.build(), extract(opened.build()))
    assert not any(
        f.severity is Severity.WARN and f.code == "rack" for f in report.findings
    )


def test_the_legged_build_swaps_a_floor_warning_for_the_hung_ones(legged):
    parts = extract(legged.build())
    messages = [f.message for f in legged.check(legged.build(), parts).findings]
    assert any("slab that wicks" in m for m in messages)
    assert not any("nothing touches the slab" in m for m in messages)


def test_the_rail_check_passes_only_because_it_is_tied(bench, parts):
    """The number that decided the design.

    A flat rail, tied at the front into a simply-supported span, checked
    against span/240 under a full tote — one check for the whole rack, since
    every rail shares the same span, depth, and thickness.
    """
    findings = bench._stiffness_findings()
    rail_findings = [f for f in findings if "tied at the front" in f.message]
    assert len(rail_findings) == 1
    assert all(f.severity is Severity.INFO for f in rail_findings)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_both_builds_are_in_the_gallery():
    from woodshop.project import discover_projects

    slugs = {s.slug for s in discover_projects()}
    assert {"basement-bench-hung", "basement-bench-legged"} <= slugs
