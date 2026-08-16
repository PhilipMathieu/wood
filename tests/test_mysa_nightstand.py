"""Tests for the Mysa nightstand — the piece that is not made of rectangles."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "projects"))

from mysa_nightstand import IN, MysaNightstand  # noqa: E402

from woodshop.checks import Severity  # noqa: E402
from woodshop.cutlist.extract import extract  # noqa: E402
from woodshop.cutlist.hardwood import nest_hardwood  # noqa: E402


@pytest.fixture(scope="module")
def stand() -> MysaNightstand:
    return MysaNightstand()


@pytest.fixture(scope="module")
def plywood() -> MysaNightstand:
    return MysaNightstand(variant="plywood")


# ---------------------------------------------------------------------------
# The published envelope
# ---------------------------------------------------------------------------


def test_it_is_eighteen_round_by_twenty_two_high(stand):
    bb = stand.build().bounding_box()
    assert bb.size.X == pytest.approx(18 * IN, abs=0.1)
    assert bb.size.Y == pytest.approx(18 * IN, abs=0.1)
    assert bb.size.Z == pytest.approx(22 * IN, abs=0.1)


def test_the_feet_are_sawn_level_so_it_does_not_rock(stand):
    """A leg turned square to its axis and then leant over dips below the floor.

    Regression: before the feet were cut flat the model was 22-1/16" tall and
    its lowest point was 1/16" underground.
    """
    assert stand.build().bounding_box().min.Z == pytest.approx(0.0, abs=0.01)


def test_the_feet_stay_inside_the_published_diameter(stand):
    """The envelope is what caps the splay, not taste."""
    assert stand.foot_spread < stand.top_diameter


def test_the_top_is_the_widest_thing_about_it(stand):
    top = [p for p in stand.build().children if getattr(p, "label", "") == "top"][0]
    assert top.bounding_box().size.X == pytest.approx(stand.top_diameter, abs=0.1)


def test_legs_lean_out_so_the_feet_are_wider_than_the_leg_circle(stand):
    assert stand.foot_radius > stand.leg_circle_r_in * IN
    expected = stand.leg_circle_r_in * IN + stand.leg_rise * math.tan(stand.splay_rad)
    assert stand.foot_radius == pytest.approx(expected)


def test_a_leaning_leg_is_longer_than_the_height_it_covers(stand):
    assert stand.leg_length > stand.leg_rise


# ---------------------------------------------------------------------------
# The cut list calls for blanks
# ---------------------------------------------------------------------------


def test_the_cut_list_asks_for_a_square_not_a_circle(stand):
    top = {p.label: p for p in extract(stand.build())}["top"]
    assert top.shape == "round"
    assert top.length_mm == pytest.approx(top.width_mm)
    assert top.length_mm > stand.top_diameter, "the blank is bigger than the disc"


def test_the_cut_list_asks_for_a_turning_square_not_a_taper(stand):
    leg = {p.label: p for p in extract(stand.build())}["leg"]
    assert leg.qty == 3
    assert leg.shape == "turned"
    # 8/4 cherry surfaces to 1-3/4", which is exactly a leg blank.
    assert leg.width_mm == pytest.approx(1.75 * IN, abs=0.01)
    assert leg.thickness_mm == pytest.approx(leg.width_mm)
    assert leg.length_mm > stand.leg_length, "blank allows for the centres"


def test_everything_comes_out_of_eight_quarter(stand):
    parts = extract(stand.build())
    plan = nest_hardwood(parts, stand.inventory, "cherry")
    assert [g.stock.thickness_quarter for g in plan.groups] == ["8/4"]


def test_the_top_is_a_glue_up(stand):
    plan = nest_hardwood(extract(stand.build()), stand.inventory, "cherry")
    assert [label for label, _, _ in plan.glue_ups] == ["top"]


def test_turning_and_sawing_cost_yield_that_nesting_does_not_see(stand):
    plan = nest_hardwood(extract(stand.build()), stand.inventory, "cherry")
    assert plan.finished_yield_fraction < plan.yield_fraction - 0.05


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def test_the_solid_nightstand_can_be_built(stand):
    assembly = stand.build()
    report = stand.check(assembly, extract(assembly))
    assert report.ok, report.to_text()


def test_a_round_solid_top_gets_a_wood_movement_note(stand):
    assembly = stand.build()
    report = stand.check(assembly, extract(assembly))
    materials = [f for f in report.findings if f.code == "material"]
    assert [f.severity for f in materials] == [Severity.INFO]
    assert "out of round" in materials[0].message


def test_an_eighteen_inch_tripod_tips_under_a_light_load(stand):
    """Not a modelling error: the envelope caps the stance at half the rim."""
    assembly = stand.build()
    report = stand.check(assembly, extract(assembly))
    tipping = [
        f for f in report.findings
        if f.code == "stability" and f.severity is Severity.WARN
    ]
    assert tipping, report.to_text()
    assert "on the rim between two legs" in tipping[0].message


def test_splaying_the_legs_further_makes_it_harder_to_tip():
    def tip_warning(splay_deg: float) -> bool:
        stand = MysaNightstand(splay_deg=splay_deg)
        assembly = stand.build()
        return any(
            f.code == "stability" and f.severity is Severity.WARN
            for f in stand.check(assembly, extract(assembly)).findings
        )

    assert tip_warning(2.0)
    # Far past what the envelope allows, but it proves the check responds.
    assert not tip_warning(20.0)


def test_legs_wider_than_the_top_are_an_error():
    stand = MysaNightstand(splay_deg=20.0)
    assembly = stand.build()
    report = stand.check(assembly, extract(assembly))
    assert not report.ok
    assert any("wider than the published" in f.message for f in report.errors)


# ---------------------------------------------------------------------------
# The plywood variant, which exists to be rejected
# ---------------------------------------------------------------------------


def test_plywood_legs_cannot_be_turned(plywood):
    assembly = plywood.build()
    report = plywood.check(assembly, extract(assembly))
    assert not report.ok
    assert any(
        f.code == "material" and "turned" in f.message for f in report.errors
    )


def test_a_plywood_top_is_only_a_warning(plywood):
    assembly = plywood.build()
    warns = [
        f for f in plywood.check(assembly, extract(assembly)).findings
        if f.code == "material" and f.severity is Severity.WARN
    ]
    assert any("edge plies" in f.message for f in warns)


def test_a_laminated_plywood_top_is_reported_as_layers(plywood):
    assembly = plywood.build()
    report = plywood.check(assembly, extract(assembly))
    assert any("2 layers" in f.message for f in report.findings)


def test_two_sheets_of_three_quarter_do_not_reach_an_inch_and_a_half(plywood):
    """45/64" twice is 1-13/32", not 1-1/2" — the trap the check exists for."""
    assert plywood.top_thickness_mm < 1.5 * IN
    assert plywood.top_thickness_mm == pytest.approx(2 * 17.859375, abs=0.01)


def test_invalid_variant_rejected():
    with pytest.raises(ValueError, match="variant"):
        MysaNightstand(variant="carbon_fibre")


def test_two_legs_rejected():
    with pytest.raises(ValueError, match="at least 3 legs"):
        MysaNightstand(n_legs=2)
