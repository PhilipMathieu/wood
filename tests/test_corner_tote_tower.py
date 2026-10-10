"""Tests for the corner tote tower — rim-hung totes, one leg, two stud walls."""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "projects"))

from corner_tote_tower import IN, CornerToteTower  # noqa: E402

from woodshop.checks import Severity  # noqa: E402
from woodshop.cutlist.extract import extract  # noqa: E402


@pytest.fixture(scope="module")
def tower() -> CornerToteTower:
    return CornerToteTower()


@pytest.fixture(scope="module")
def built(tower):
    return tower.build()


@pytest.fixture(scope="module")
def parts(built):
    return extract(built)


def _qty(parts, label):
    return sum(p.qty for p in parts if p.label == label)


def _members(assembly, label):
    return [c for c in assembly.leaves if getattr(c, "label", "") == label]


def _overlaps(a, c) -> bool:
    ba, bc = a.bounding_box(), c.bounding_box()
    if (
        ba.min.X >= bc.max.X
        or bc.min.X >= ba.max.X
        or ba.min.Y >= bc.max.Y
        or bc.min.Y >= ba.max.Y
        or ba.min.Z >= bc.max.Z
        or bc.min.Z >= ba.max.Z
    ):
        return False
    return (a & c).volume > 1.0


def test_four_seventeen_gallon_totes_at_thirteen_inches(tower):
    assert tower.tiers == 4
    assert tower.bin.key == "17gal"
    assert tower.pitch == pytest.approx(13.0 * IN)


def test_the_tower_is_the_size_it_says(tower, built, parts):
    findings = tower._envelope_findings(built)
    assert [f.severity for f in findings] == [Severity.INFO]
    assert tower.width == pytest.approx(20.25 * IN)
    assert tower.depth == pytest.approx(27.375 * IN)


def test_every_tote_slides_out_without_touching_anything(tower, built):
    for tier in range(tower.tiers):
        for path in tower.tote_path(tier):
            for leaf in built.leaves:
                assert (path & leaf).volume < 1.0, (tier, leaf.label)
    assert tower._sweep_findings(built)[0].severity is Severity.INFO


def test_no_part_overlaps_another_or_the_existing_studs(tower):
    leaves = list(tower.build(show_wall=True).leaves)
    for a, c in itertools.combinations(leaves, 2):
        if a.label == c.label == "existing_stud":
            continue
        assert not _overlaps(a, c), (a.label, c.label)


def test_the_studs_are_drawn_but_never_cut(tower, parts):
    assert "existing_stud" not in {p.label for p in parts}
    drawn = tower.build(show_wall=True)
    assert len(_members(drawn, "existing_stud")) > 0


def test_only_the_pt_foot_touches_the_slab(built):
    on_floor = [c for c in built.leaves if c.bounding_box().min.Z < 0.01]
    assert [c.label for c in on_floor] == ["leg_foot"]
    assert on_floor[0].material == "syp_pt"


def test_the_leg_stands_on_the_foot_and_the_back_stile_does_not_reach_the_floor(
    tower, built
):
    foot = _members(built, "leg_foot")[0].bounding_box()
    leg = _members(built, "front_leg")[0].bounding_box()
    stile = _members(built, "back_stile")[0].bounding_box()
    assert leg.min.Z == pytest.approx(foot.max.Z, abs=0.01)
    assert foot.min.X <= leg.min.X and foot.max.X == pytest.approx(leg.max.X, abs=0.01)
    assert foot.min.Y <= leg.min.Y and foot.max.Y >= leg.max.Y
    assert stile.min.Z == pytest.approx(tower.runner_z(0)[0], abs=0.01)


def test_the_bottom_tote_clears_the_foot(tower):
    assert tower.tote_z(0)[0] > tower.foot_t


def test_each_wall_runner_lands_on_two_side_wall_studs(tower):
    assert len(tower.side_studs_under_runner) == 2
    assert tower.wall_overhang == pytest.approx((27.375 - 16.75) * IN)


def test_the_overhang_is_stiff_and_the_screws_are_not_the_limit(tower):
    findings = tower._overhang_findings()
    assert all(f.severity is Severity.INFO for f in findings)


def test_a_wall_with_studs_too_far_apart_is_refused():
    with pytest.raises(ValueError, match="needs two to stay level"):
        CornerToteTower(stud_spacing_in=30.0)


def test_the_back_stile_hangs_on_blocking_between_two_back_wall_studs(
    tower, built
):
    left, right = tower.stile_bay
    assert left == pytest.approx(16.75 * IN)
    assert right == pytest.approx(31.25 * IN)
    for block in _members(built, "blocking"):
        bb = block.bounding_box()
        assert bb.min.Y == pytest.approx(0.0, abs=0.01)
        assert bb.size.X == pytest.approx(right - left, abs=0.01)


def test_a_stile_that_lands_on_a_stud_needs_no_blocking():
    on_stud = CornerToteTower(stud_spacing_in=19.5)
    assert on_stud.stile_bay is None
    assert _qty(extract(on_stud.build()), "blocking") == 0
    assert any("no blocking" in f.message for f in on_stud._fixing_findings())


def test_the_runners_catch_the_lip_and_clear_the_body(tower):
    assert tower.lip_bearing == pytest.approx(0.375 * IN)
    assert tower.body_clearance == pytest.approx(0.875 * IN)


def test_the_top_clears_the_top_tote(tower, built):
    lid = tower.tote_z(tower.tiers - 1)[1]
    for label in ("top_rail", "top_ledger", "top_slat"):
        for part in _members(built, label):
            assert part.bounding_box().min.Z >= lid


def test_the_kit(tower, parts):
    assert {p.label: _qty(parts, p.label) for p in parts} == {
        "wall_runner": tower.tiers,
        "open_runner": tower.tiers,
        "front_leg": 1,
        "back_stile": 1,
        "top_rail": 1,
        "top_ledger": 1,
        "top_slat": tower.n_slats,
        "leg_foot": 1,
        "blocking": 2,
    }


def test_the_tower_has_no_errors_and_warns_only_about_the_site(tower, built, parts):
    report = tower.check(built, parts)
    assert report.ok
    warns = {f.code for f in report.findings if f.severity is Severity.WARN}
    assert warns == {"site"}


def test_three_tiers_is_a_shorter_tower(tower):
    short = CornerToteTower(tiers=3)
    assert tower.height - short.height == pytest.approx(tower.pitch)


def test_the_tower_is_in_the_gallery():
    from woodshop.project import discover_projects

    assert "corner-tote-tower" in {s.slug for s in discover_projects()}
