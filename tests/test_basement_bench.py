"""Tests for the basement wall bench — the piece whose storage is its bracket."""

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
# The totes, which decide almost everything
# ---------------------------------------------------------------------------


def test_each_tote_governs_the_dimension_the_brief_said_it_would(bench):
    """The brief called them the slightly taller and the slightly wider one.

    That is exactly how they divide the work: the 16 gallon sets the tier
    pitch, the 17 gallon sets the bay width and the depth of the whole bench.
    """
    assert bench.tallest.key == "16gal"
    assert bench.widest.key == "17gal"
    assert bench.longest.key == "17gal"


def test_the_depth_is_derived_from_the_longest_tote(bench):
    """A 26-7/8" box does not go into a 24" bench in any orientation."""
    longest = bench.longest
    assert bench.overall_d_in is None
    assert bench.overall_d == pytest.approx(
        (longest.length_in + bench.bin_back_clearance_in + bench.top_overhang_front_in)
        * IN
        + bench.ledger_t
    )
    assert bench.shelf_depth >= longest.length_in * IN


def test_a_twenty_four_inch_bench_will_not_take_these_totes():
    with pytest.raises(ValueError, match="long and the rack is only"):
        BasementBench(overall_d_in=24.0)


def test_a_depth_that_was_given_rather_than_derived_is_flagged():
    deep = BasementBench(overall_d_in=34.0)
    assert any(
        f.severity is Severity.WARN and "rather than derived" in f.message
        for f in deep._depth_findings()
    )


def test_every_published_tote_dimension_carries_its_source():
    """The same rule the prices live under.

    A number with no date behind it is a number somebody remembered.
    """
    for bin_ in BIN_TYPES.values():
        assert bin_.source and bin_.source_url.startswith("https://")
        assert bin_.read_on.startswith("2026-")


def test_a_totes_base_is_much_narrower_than_its_rim():
    """The taper is the whole reason the tiers are shelves.

    A published interior width is measured at the bottom of the box, so it is
    the number a pair of runners would have to catch.
    """
    for bin_ in BIN_TYPES.values():
        assert bin_.base_w_in < bin_.width_in - 2.0


# ---------------------------------------------------------------------------
# The envelope, and what the hung build means by it
# ---------------------------------------------------------------------------


def test_the_bench_is_the_published_size(bench):
    bb = bench.build().bounding_box()
    assert bb.size.X == pytest.approx(80 * IN, abs=0.1)
    assert bb.size.Y == pytest.approx(bench.overall_d, abs=0.1)
    assert bb.max.Z == pytest.approx(36 * IN, abs=0.1)


def test_nothing_in_the_hung_build_touches_the_floor(bench):
    """The whole argument for hanging it: the slab stays clear.

    The lowest part is the bottom shelf, and a broom has to get under it.
    """
    bb = bench.build().bounding_box()
    assert bb.min.Z == pytest.approx(bench.rack_bottom_z, abs=0.1)
    assert bb.min.Z > 3 * IN


def test_the_legged_build_reaches_the_floor_and_nothing_else_moves(bench, legged):
    """Same bench, same top, same rack — the ribs just grow down onto rails."""
    assert legged.build().bounding_box().min.Z == pytest.approx(0.0, abs=0.1)
    assert legged.top_height == bench.top_height
    assert legged.rack_bottom_z == pytest.approx(bench.rack_bottom_z)
    assert [b.key for b in legged.bay_bins] == [b.key for b in bench.bay_bins]


def test_the_back_of_the_bench_is_the_face_of_the_studs(bench):
    """Y = 0 is the wall.

    A part at negative y would be inside the masonry, and a gap at y = 0 would
    mean the ledger is not touching.
    """
    assert bench.build().bounding_box().min.Y == pytest.approx(0.0, abs=0.01)


def test_a_bench_this_deep_admits_it_is_past_a_comfortable_reach(bench):
    assert bench.reach_over > 0
    assert any(
        f.code == "ergonomics" and f.severity is Severity.WARN
        for f in bench._depth_findings()
    )


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
    """A clash nobody finds on paper.

    The rib's notch bears on the ledger's front face, so a proud lag head
    there stops the rib seating.
    """
    bench = BasementBench()
    clash = BasementBench(first_stud_offset_in=bench.rib_x(1) / IN - 1.0)
    assert any("counterbore" in f.message for f in clash._stud_findings())


# ---------------------------------------------------------------------------
# The rack is the bracket
# ---------------------------------------------------------------------------


def test_the_bracket_is_the_rack_and_not_the_ledger(bench):
    """The design argument, as a number.

    Running the ribs down past a second ledger buys a lever arm several times
    the ledger's own depth.
    """
    assert bench.bracket_depth > 24 * IN
    assert bench.bracket_depth > 4.0 * bench.ledger_w


def test_a_deeper_bracket_is_a_lighter_pull_on_the_same_lags(bench, parts):
    """Tension at the top ledger is moment over lever arm.

    Hold the moment still and the lever arm is the only thing left: the same
    bench on one ledger alone would pull its lags several times harder, which
    is the second finding the bracket section of the report prints.
    """
    moment = bench.overturning_moment_nmm(parts)
    assert moment / bench.bracket_depth < moment / bench.ledger_w / 4.0


def test_deleting_the_joists_deepened_the_bracket(bench):
    """The ribs carry the top directly, so the rack starts 3-1/2" higher.

    The lower ledger went down with it, which is a part removed for one reason
    paying off in another.
    """
    assert bench.rib_top_z == pytest.approx(bench.top_underside_z)
    assert "joist" not in {p.label for p in extract(bench.build())}


def test_the_lags_are_not_the_limit_and_shear_is_tighter_than_pull_out(bench, parts):
    """Reference design values, both sides allowable.

    If this ever inverts, the lag size is being defended by the wrong
    argument: eight full totes make holding the weight up the binding case,
    not pulling off the wall.
    """
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
    """Why lags_per_stud is 2.

    One passes, and passing at 1.5x under 900 lb is not the same as being
    fine.
    """
    thin = BasementBench(lags_per_stud=1)
    findings = thin._wall_findings(extract(thin.build()))
    shear = next(f for f in findings if f.message.startswith("shear:"))
    assert shear.severity is Severity.WARN
    assert "lags_per_stud=2" in shear.message


def test_an_untabulated_lag_is_not_checked_rather_than_interpolated(parts):
    odd = BasementBench(lag_diameter_in=0.625)
    assert 0.625 not in LAG_SHEAR_LB
    findings = odd._wall_findings(extract(odd.build()))
    assert any("not checked" in f.message for f in findings)


def test_the_leaning_load_is_the_one_that_sizes_the_wall(bench, parts):
    """The smallest load has the longest lever arm.

    So it must not be possible to drop it and get the same answer.
    """
    cases = {name: (kg, arm) for name, kg, arm in bench._load_cases(parts)}
    leaning = "somebody leaning on the front edge"
    assert cases[leaning][1] == bench.overall_d
    assert cases[leaning][1] == max(arm for _, arm in cases.values())


# ---------------------------------------------------------------------------
# The mix, and what it buys
# ---------------------------------------------------------------------------


def test_the_mix_is_what_makes_the_fourth_bay_fit(bench):
    """Not a preference — arithmetic.

    Four bays of the wide tote want more bench than there is; four of the
    narrow one waste most of a bay. Three and one fits exactly.
    """
    keys = [b.key for b in bench.bay_bins]
    assert keys == ["17gal", "17gal", "17gal", "16gal"]

    all_wide = BasementBench(bins=("17gal",))
    assert all_wide.derived_n_bays == 3
    all_narrow = BasementBench(bins=("16gal",))
    assert all_narrow.derived_n_bays == 4


def test_the_bays_are_not_all_the_same_width_and_the_clearance_is(bench):
    """Each bay is cut to its own tote, so the slack lands evenly."""
    widths = [bench.bay_clear_w(b) for b in range(bench.derived_n_bays)]
    assert len(set(round(w, 3) for w in widths)) == 2
    clearances = [
        bench.bin_side_clearance(b) for b in range(bench.derived_n_bays)
    ]
    assert max(clearances) - min(clearances) < 0.01
    assert clearances[0] > 0.375 * IN


def test_the_bays_add_up_to_the_frame(bench):
    total = sum(
        bench.bay_clear_w(b) for b in range(bench.derived_n_bays)
    ) + bench.n_ribs * bench.panel_t
    assert total == pytest.approx(bench.frame_w)


def test_uniform_tiers_let_any_tote_go_in_any_slot(bench):
    """The shorter tote rides with the difference as extra headroom.

    Worth more in a shop than the inch it costs, and the report says so.
    """
    short = BIN_TYPES["17gal"]
    assert bench.head_clearance(short) > bench.head_clearance(bench.tallest)
    assert bench.head_clearance(bench.tallest) == pytest.approx(
        bench.bin_head_clearance_in * IN
    )


def test_the_rack_holds_what_it_says_and_open_bays_cost_totes(bench):
    assert bench.n_bins == bench.derived_n_bays * bench.n_tiers == 8
    assert sum(bench.bin_tally.values()) == bench.n_bins
    opened = BasementBench(open_bays=(2,))
    assert opened.n_bins == bench.n_bins - bench.n_tiers


def test_an_open_bay_takes_its_shelves_and_its_dadoes_out_of_the_model(bench):
    opened = BasementBench(open_bays=(2,))
    shelves = [p for p in extract(opened.build()) if p.label == "shelf"]
    every_bay = [p for p in extract(bench.build()) if p.label == "shelf"]
    assert sum(p.qty for p in shelves) == sum(p.qty for p in every_bay) - bench.n_tiers


def test_a_third_tier_does_not_fit_and_is_refused():
    with pytest.raises(ValueError, match="below the slab"):
        BasementBench(n_tiers=3)


def test_a_tote_too_wide_for_the_bench_is_refused():
    with pytest.raises(ValueError, match="fewer than two"):
        BasementBench(bins=("17gal",), bin_side_clearance_in=12.0)


# ---------------------------------------------------------------------------
# Shelves, not runners
# ---------------------------------------------------------------------------


def test_runners_cannot_hold_a_tapered_tote_and_the_check_says_so():
    """The check that changed this design.

    A tote's base is nowhere near as wide as its rim, so a pair of runners at
    the bay's edges has nothing to catch.
    """
    runners = BasementBench(support="runners")
    report = runners.check(runners.build(), extract(runners.build()))
    assert not report.ok
    support = [f for f in report.findings if f.code == "support"]
    assert all(
        f.severity is Severity.ERROR
        for f in support
        if "drops between them" in f.message
    )
    assert any("drops between them" in f.message for f in support)


def test_runners_also_price_the_wider_tote_out_of_the_bench():
    """A runner stands proud of its rib, so it is bay width as well as sag."""
    runners = BasementBench(support="runners")
    assert {b.key for b in runners.bay_bins} == {"16gal"}
    assert any(
        f.severity is Severity.WARN and "gets no bay" in f.message
        for f in runners._rack_findings()
    )


def test_runners_also_cost_an_inch_and_a_half_of_floor_clearance(bench):
    runners = BasementBench(support="runners")
    assert runners.tier_pitch > bench.tier_pitch
    assert runners.rack_bottom_z < bench.rack_bottom_z


def test_the_shipped_build_holds_every_tote_it_claims_to(bench):
    findings = bench._support_findings()
    assert findings
    assert all(f.severity is Severity.INFO for f in findings)


# ---------------------------------------------------------------------------
# The cut list
# ---------------------------------------------------------------------------


def test_the_kit_is_seven_kinds_of_part(parts):
    assert {p.label for p in parts} == {
        "top_skin",
        "top_surface",
        "top_ledger",
        "rack_ledger",
        "front_rail",
        "rib",
        "shelf",
    }


def test_the_legged_build_adds_foot_rails_and_taller_ribs(bench, legged):
    labels = {p.label for p in extract(legged.build())}
    assert "foot_rail" in labels
    assert legged.rib_h > bench.rib_h


def test_there_is_one_rib_per_bay_boundary_and_a_shelf_per_bay_per_tier(
    bench, parts
):
    by_label: dict[str, int] = {}
    for p in parts:
        by_label[p.label] = by_label.get(p.label, 0) + p.qty
    assert by_label["rib"] == bench.n_ribs
    assert by_label["shelf"] == bench.derived_n_bays * bench.n_tiers


def test_two_shelf_sizes_because_two_bay_widths(parts):
    shelves = [p for p in parts if p.label == "shelf"]
    assert len(shelves) == 2
    assert {p.qty for p in shelves} == {2, 6}


def test_the_top_is_two_glued_layers_under_one_screwed_one(bench, parts):
    by_label = {p.label: p for p in parts}
    assert by_label["top_skin"].qty == 2
    assert by_label["top_surface"].qty == 1
    assert by_label["top_surface"].material != by_label["top_skin"].material
    assert bench.structural_top_t < bench.top_t


def test_the_notches_survive_into_the_rib_geometry():
    """Two ledger notches and the front rail's rebate, out of a rectangle.

    Checked on the runners build, whose ribs carry no shelf dadoes, so the
    arithmetic is exact rather than a bound.
    """
    bench = BasementBench(support="runners")
    rib = next(
        c for c in bench.build().children if getattr(c, "label", "") == "rib"
    )
    blank = bench.frame_d * bench.rib_h * bench.panel_t
    notches = 2 * bench.ledger_t * bench.ledger_w * bench.panel_t
    rebate = bench.rail_w * bench.rail_t * bench.panel_t
    assert rib.volume == pytest.approx(blank - notches - rebate, rel=1e-3)


def test_an_end_rib_is_dadoed_on_one_face_and_an_inner_rib_on_two(bench):
    ribs = [c for c in bench.build().children if getattr(c, "label", "") == "rib"]
    assert len(ribs) == bench.n_ribs
    end, inner = ribs[0], ribs[1]
    assert end.volume > inner.volume
    one_face = bench.n_tiers * (
        bench.shelf_depth * bench.panel_t * (0.25 * IN)
    )
    assert end.volume - inner.volume == pytest.approx(one_face, rel=0.02)


def test_the_dadoes_are_cut_to_the_sheet_and_not_to_its_label(bench):
    """23/32", not 3/4".

    A dado cut to the label is 0.8 mm loose and the shelf it houses rattles.
    """
    assert bench.panel_t == pytest.approx(0.71875 * IN, abs=0.01)


def test_the_ribs_and_shelves_are_free_to_turn_on_the_sheet_and_the_top_is_not(
    parts,
):
    """Worth a sheet of plywood.

    Neither a 30"-deep web nor a shelf that sags a tenth of a millimetre cares
    which way its face grain runs; the top is the face you look at.
    """
    by_label = {p.label: p for p in parts}
    assert by_label["rib"].grain_direction == "none"
    assert by_label["shelf"].grain_direction == "none"
    assert by_label["top_skin"].grain_direction == "length"


# ---------------------------------------------------------------------------
# The report as a whole
# ---------------------------------------------------------------------------


def test_the_shipped_bench_has_no_errors(bench, parts):
    report = bench.check(bench.build(), parts)
    assert report.ok


def test_the_shipped_bench_warns_about_exactly_what_it_should(bench, parts):
    """Five WARN categories by design, and no more.

    No bay left open, the back of a deep bench is past a reach, the wall joint
    is the thing that moves, and nobody knows what is in those stud bays. The
    plywood-thickness WARNs come from the sheet, not from the design.
    """
    report = bench.check(bench.build(), parts)
    codes = sorted({f.code for f in report.findings if f.severity is Severity.WARN})
    assert codes == ["deflection", "ergonomics", "rack", "site", "thickness"]


def test_opening_a_bay_answers_the_rack_warning():
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
