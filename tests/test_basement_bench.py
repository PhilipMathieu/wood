"""Tests for the basement wall bench — the piece whose storage is its bracket."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "projects"))

from basement_bench import IN, BasementBench, lag_withdrawal_lb_per_in  # noqa: E402

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
# The envelope, and what the hung build means by it
# ---------------------------------------------------------------------------


def test_the_bench_is_the_published_size(bench):
    bb = bench.build().bounding_box()
    assert bb.size.X == pytest.approx(80 * IN, abs=0.1)
    assert bb.size.Y == pytest.approx(24 * IN, abs=0.1)
    assert bb.max.Z == pytest.approx(36 * IN, abs=0.1)


def test_nothing_in_the_hung_build_touches_the_floor(bench):
    """The whole argument for hanging it: the slab stays clear.

    The lowest part is the bottom tier's runners, and a broom has to get under
    them.
    """
    bb = bench.build().bounding_box()
    assert bb.min.Z == pytest.approx(bench.rack_bottom_z, abs=0.1)
    assert bb.min.Z > 3 * IN


def test_the_legged_build_reaches_the_floor_and_nothing_else_moves(bench, legged):
    """Same bench, same top, same rack — the ribs just grow down onto rails."""
    assert legged.build().bounding_box().min.Z == pytest.approx(0.0, abs=0.1)
    assert legged.top_height == bench.top_height
    assert legged.rack_bottom_z == pytest.approx(bench.rack_bottom_z)
    assert legged.derived_n_bays == bench.derived_n_bays


def test_the_back_of_the_bench_is_the_face_of_the_studs(bench):
    """Y = 0 is the face of the studs.

    A part at negative y would be inside the masonry, and a gap at y = 0 would
    mean the ledger is not touching.
    """
    assert bench.build().bounding_box().min.Y == pytest.approx(0.0, abs=0.01)


# ---------------------------------------------------------------------------
# The wall
# ---------------------------------------------------------------------------


def test_eighty_inches_is_five_studs_with_a_real_end_distance(bench):
    """The brief's "roughly 80 inches" is also a correct lag layout.

    Five studs at 16" o.c. with 7" of ledger past each end lag.
    """
    studs = bench.stud_positions
    assert len(studs) == 5
    left = studs[0] - bench.frame_x0
    right = bench.frame_x0 + bench.frame_w - studs[-1]
    assert left == pytest.approx(7 * IN)
    assert right == pytest.approx(7 * IN)
    assert left > 4 * bench.lag_diameter_in * IN


def test_twenty_four_inch_studs_lose_two_fixings_and_say_so(bench):
    wide = BasementBench(stud_spacing_in=24.0)
    assert len(wide.stud_positions) < len(bench.stud_positions)
    assert any(
        f.severity is Severity.WARN and "o.c. studs give" in f.message
        for f in wide._stud_findings()
    )


def test_furring_strips_are_an_error_not_a_warning():
    """The one assumption the model cannot check.

    A 1x3 strapping run and a 2x4 stud wall look identical with the drywall
    off, and every wall number in the report is worthless on the first one.
    """
    furred = BasementBench(stud_nominal="1x3")
    assert furred.studs_are_furring
    findings = furred._stud_findings()
    assert any(f.severity is Severity.ERROR for f in findings)
    assert any("concrete anchors" in f.message for f in findings)


def test_a_wall_with_no_studs_under_the_ledger_is_an_error():
    homeless = BasementBench(first_stud_offset_in=500.0)
    assert homeless.stud_positions == []
    findings = homeless._stud_findings()
    assert [f.severity for f in findings] == [Severity.ERROR]


def test_a_lag_landing_under_a_rib_is_told_to_counterbore():
    """A lag head under a rib is a clash only the model would catch.

    The rib's notch bears on the ledger's front face, so a proud lag head there
    stops the rib seating.
    """
    bench = BasementBench()
    clash = BasementBench(first_stud_offset_in=bench.rib_x(1) / IN - 1.0)
    findings = clash._stud_findings()
    assert any("counterbore" in f.message for f in findings)


# ---------------------------------------------------------------------------
# The rack is the bracket
# ---------------------------------------------------------------------------


def test_the_bracket_is_the_rack_and_not_the_ledger(bench):
    """The whole design argument, as a number.

    Running the ribs down past a second ledger buys a lever arm several times
    the ledger's own depth.
    """
    assert bench.bracket_depth > 20 * IN
    assert bench.bracket_depth > 3.5 * bench.ledger_w


def test_a_deeper_bracket_is_a_lighter_pull_on_the_same_lags(bench, parts):
    """Tension at the top ledger is moment over lever arm.

    Hold the moment still and the lever arm is the only thing left: the same
    bench on one ledger alone would pull its lags several times harder, which
    is the second finding the bracket section of the report prints.
    """
    moment = bench.overturning_moment_nmm(parts)
    assert moment / bench.bracket_depth < moment / bench.ledger_w / 3.0


def test_fewer_tiers_make_a_shallower_bracket(bench):
    """The rack's height and the bracket's lever arm are the same number.

    Two tiers of bins is a shorter rack, a lower bottom ledger position and
    therefore a shorter arm, even though it also holds less.
    """
    shallow = BasementBench(n_tiers=2)
    assert shallow.bracket_depth < bench.bracket_depth
    assert shallow.n_bins < bench.n_bins


def test_the_lags_are_not_the_limit_and_shear_is_tighter_than_pull_out(bench, parts):
    """Reference design values, both sides allowable.

    If this ever inverts, lags_per_stud is being defended by the wrong
    argument.
    """
    n_lags = len(bench.stud_positions) * bench.lags_per_stud
    pull_lb = (
        bench.overturning_moment_nmm(parts) / bench.bracket_depth / 4.4482216 / n_lags
    )
    capacity_lb = lag_withdrawal_lb_per_in() * bench.lag_penetration / IN
    assert capacity_lb / pull_lb > 4.0

    from basement_bench import LAG_SHEAR_LB, pounds_force

    shear_lb = pounds_force(bench.total_load_n(parts)) / n_lags
    assert LAG_SHEAR_LB / shear_lb < capacity_lb / pull_lb


def test_one_lag_per_stud_runs_a_margin_this_bench_should_not(parts):
    """Why lags_per_stud defaults to 2.

    One passes, and passing at 1.5x is not the same as being fine.
    """
    thin = BasementBench(lags_per_stud=1)
    findings = thin._wall_findings(extract(thin.build()))
    shear = next(f for f in findings if f.message.startswith("shear:"))
    assert shear.severity is Severity.WARN
    assert "lags_per_stud=2" in shear.message


def test_the_leaning_load_is_the_one_that_sizes_the_wall(bench, parts):
    """The smallest load has the longest lever arm.

    So it must not be possible to drop it and get the same answer.
    """
    cases = dict((name, (kg, arm)) for name, kg, arm in bench._load_cases(parts))
    leaning = "somebody leaning on the front edge"
    assert cases[leaning][1] == bench.overall_d
    assert cases[leaning][1] == max(arm for _, arm in cases.values())


# ---------------------------------------------------------------------------
# The rack, and the bin that sized it
# ---------------------------------------------------------------------------


def test_five_bays_not_six_because_of_the_runners(bench):
    """Six bays would leave a channel an 11" bin does not enter.

    The bay count is an outcome of the bin, which is why it is derived.
    """
    assert bench.derived_n_bays == 5
    assert bench.bin_channel_w > 11 * IN
    six = BasementBench(n_bays=6)
    assert six.bin_channel_w < 11 * IN


def test_a_smaller_bin_buys_more_bays():
    small = BasementBench(bin_w_in=8.25, bin_l_in=13.625, bin_h_in=5.0)
    assert small.derived_n_bays > BasementBench().derived_n_bays


def test_the_rack_holds_what_it_says_and_open_bays_cost_bins(bench):
    assert bench.n_bins == bench.derived_n_bays * bench.n_tiers
    opened = BasementBench(open_bays=(2,))
    assert opened.n_bins == bench.n_bins - bench.n_tiers
    assert opened.rack_load_kg < bench.rack_load_kg


def test_an_open_bay_takes_its_runners_out_of_the_model(bench):
    opened = BasementBench(open_bays=(2,))
    runners = next(p for p in extract(opened.build()) if p.label == "runner")
    every_bay = next(p for p in extract(bench.build()) if p.label == "runner")
    assert runners.qty == every_bay.qty - 2 * bench.n_tiers


def test_a_bin_never_reaches_the_ledgers_behind_it(bench):
    """The dead space behind a bin is the space the structure needs.

    If they stop being the same space, a bin stops going all the way in.
    """
    assert bench.frame_d - bench.bin_l_in * IN > bench.ledger_t


def test_the_front_rail_stops_where_the_rack_starts(bench):
    """A 2x6 front rail would hang 2" into the top tier and the top row of bins could not come out.

    The rail's underside is the rack's ceiling.
    """
    assert bench.joist_bottom_z == pytest.approx(bench.rack_top_z)
    top_bin_top = bench.rack_top_z - bench.bin_head_clearance_in * IN
    assert top_bin_top < bench.joist_bottom_z


def test_a_fourth_tier_does_not_fit_and_is_refused():
    with pytest.raises(ValueError, match="below the slab"):
        BasementBench(n_tiers=4)


def test_a_bin_too_wide_for_the_bench_is_refused():
    with pytest.raises(ValueError, match="fewer than two"):
        BasementBench(bin_w_in=40.0)


# ---------------------------------------------------------------------------
# The cut list
# ---------------------------------------------------------------------------


def test_the_kit_is_eight_kinds_of_part(parts):
    assert {p.label for p in parts} == {
        "top_skin",
        "top_surface",
        "top_ledger",
        "rack_ledger",
        "joist",
        "front_rail",
        "rib",
        "runner",
    }


def test_the_legged_build_adds_foot_rails_and_taller_ribs(bench, legged):
    labels = {p.label for p in extract(legged.build())}
    assert "foot_rail" in labels
    assert legged.rib_h > bench.rib_h


def test_there_is_one_rib_and_one_joist_per_bay_boundary(bench, parts):
    by_label = {p.label: p for p in parts}
    assert by_label["rib"].qty == bench.n_ribs
    assert by_label["joist"].qty == bench.n_ribs
    assert by_label["runner"].qty == 2 * bench.n_tiers * bench.derived_n_bays


def test_the_top_is_two_glued_layers_under_one_screwed_one(bench, parts):
    by_label = {p.label: p for p in parts}
    assert by_label["top_skin"].qty == 2
    assert by_label["top_surface"].qty == 1
    assert by_label["top_surface"].material != by_label["top_skin"].material
    assert bench.structural_top_t < bench.top_t


def test_the_notches_survive_into_the_rib_geometry(bench):
    """Two 1-1/2" x 5-1/2" notches out of a 22" x 27" panel.

    A regression here means the booleans quietly stopped cutting and the rib
    would foul both ledgers.
    """
    rib = next(
        c for c in bench.build().children if getattr(c, "label", "") == "rib"
    )
    rectangle = bench.frame_d * bench.rib_h * bench.panel_t
    notches = 2 * bench.ledger_t * bench.ledger_w * bench.panel_t
    assert rib.volume == pytest.approx(rectangle - notches, rel=1e-3)


def test_the_joist_dado_is_cut_to_the_sheet_and_not_to_its_label(bench):
    """23/32", not 3/4".

    A dado cut to the label is 0.8 mm loose and the rib it locates is no longer
    located.
    """
    joist = next(
        c for c in bench.build().children if getattr(c, "label", "") == "joist"
    )
    solid = bench.joist_len * bench.joist_w * bench.joist_t
    assert joist.volume < solid
    assert bench.panel_t == pytest.approx(0.71875 * IN, abs=0.01)


def test_the_ribs_are_free_to_turn_on_the_sheet_and_the_runners_are_not(parts):
    """Worth a sheet of plywood.

    A 27"-deep web does not care which way its face grain runs, and a 1-1/2"
    strip does.
    """
    by_label = {p.label: p for p in parts}
    assert by_label["rib"].grain_direction == "none"
    assert by_label["runner"].grain_direction == "length"
    assert by_label["top_skin"].grain_direction == "length"


# ---------------------------------------------------------------------------
# The report as a whole
# ---------------------------------------------------------------------------


def test_the_shipped_bench_has_no_errors(bench, parts):
    report = bench.check(bench.build(), parts)
    assert report.ok


def test_the_shipped_bench_warns_about_exactly_what_it_should(bench, parts):
    """Four WARN categories by design, and no more.

    No bay left open, the wall joint is the thing that moves, and nobody knows
    what is in those stud bays. The plywood-thickness WARNs come from the
    sheet, not from the design.
    """
    report = bench.check(bench.build(), parts)
    categories = sorted(
        {f.code for f in report.findings if f.severity is Severity.WARN}
    )
    assert categories == ["deflection", "rack", "site", "thickness"]


def test_opening_a_bay_answers_the_rack_warning(bench, parts):
    opened = BasementBench(open_bays=(2,))
    report = opened.check(opened.build(), extract(opened.build()))
    assert not any(
        f.severity is Severity.WARN and f.code == "rack" for f in report.findings
    )


def test_the_legged_build_swaps_a_floor_warning_for_the_hung_ones(legged):
    parts = extract(legged.build())
    messages = [f.message for f in legged.check(legged.build(), parts).findings]
    assert any("slab that wicks" in m for m in messages)
    assert not any("nothing touches the slab" in m for m in messages)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_both_builds_are_in_the_gallery():
    from woodshop.project import discover_projects

    slugs = {s.slug for s in discover_projects()}
    assert {"basement-bench-hung", "basement-bench-legged"} <= slugs
