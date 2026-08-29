"""Tests for the deck stair gate — the piece that is mostly a question about sag."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "projects"))

from deck_gate import IN, DeckStairGate  # noqa: E402

from woodshop.checks import Severity  # noqa: E402
from woodshop.cutlist.extract import extract  # noqa: E402


@pytest.fixture(scope="module")
def gate() -> DeckStairGate:
    return DeckStairGate()


@pytest.fixture(scope="module")
def parts(gate) -> list:
    return extract(gate.build())


# ---------------------------------------------------------------------------
# Envelope and fit
# ---------------------------------------------------------------------------


def test_the_gate_fits_the_measured_opening_with_its_clearances(gate):
    bb = gate.build().bounding_box()
    assert bb.size.X < 36.5 * IN
    assert bb.size.X == pytest.approx(gate.gate_width, abs=0.1)


def test_the_gate_lands_on_the_railings_own_lines(gate):
    """Frame from 3-3/4" up to the 41-1/2" rail top, cap on top: hung at the
    measured bottom gap, the cap tops out at 42-1/4" like the railing's."""
    assert gate.frame_height == pytest.approx((41.5 - 3.75) * IN)
    assert gate.build().bounding_box().size.Z == pytest.approx(38.5 * IN, abs=0.1)


def test_the_cap_is_the_deepest_thing_on_the_gate(gate):
    """The 1x6 overhangs a 1-1/2" frame by 2" a side — that is the swing
    envelope, and what has to clear the posts."""
    assert gate.build().bounding_box().size.Y == pytest.approx(5.5 * IN, abs=0.1)


# ---------------------------------------------------------------------------
# The cut list
# ---------------------------------------------------------------------------


def test_the_cut_list_is_five_kinds_of_part(parts):
    by_label = {p.label: p for p in parts}
    assert set(by_label) == {
        "hinge_stile",
        "latch_stile",
        "top_rail",
        "bottom_rail",
        "slat",
        "cap",
    }
    assert by_label["slat"].qty == gate_n_slats_expected()


def gate_n_slats_expected() -> int:
    return DeckStairGate().n_slats


def test_a_beveled_slat_is_still_a_1x1_stick_on_the_cut_list(parts):
    """The 45° bevels take no extra stock; the blank is the bought baluster."""
    slat = next(p for p in parts if p.label == "slat")
    assert slat.width_mm == pytest.approx(0.75 * IN)
    assert slat.thickness_mm == pytest.approx(0.75 * IN)
    assert slat.length_mm == pytest.approx(DeckStairGate().slat_length)


def test_the_bevels_survive_into_the_geometry(gate):
    """A beveled slat has less volume than its stick; a regression here means
    the boolean quietly stopped cutting."""
    slat = next(
        c for c in gate.build().children if getattr(c, "label", "") == "slat"
    )
    stick_mm3 = gate.slat_length * gate.slat_side**2
    assert slat.volume < stick_mm3 * 0.999
    assert slat.volume > stick_mm3 * 0.9


# ---------------------------------------------------------------------------
# The guard rule
# ---------------------------------------------------------------------------


def test_no_gap_passes_a_four_inch_sphere(gate):
    assert gate.slat_gap < 4 * IN


def test_a_lazy_slat_count_is_an_error():
    lazy = DeckStairGate(max_slat_gap_in=6.0)
    findings = lazy.check_slat_gap()
    assert any(f.severity is Severity.ERROR for f in findings)


def test_matching_the_railings_five_inch_pitch_is_honest_about_the_sphere():
    """The railing runs 5" centres — 4-1/4" gaps, wider than the 4" rule.
    The gate can copy it, and the check refuses to look away."""
    copied = DeckStairGate(match_railing_pitch=True)
    assert copied.n_slats == 5
    assert copied.slat_gap > 4 * IN
    findings = copied.check_slat_gap()
    assert any(f.severity is Severity.ERROR for f in findings)


# ---------------------------------------------------------------------------
# The swing
# ---------------------------------------------------------------------------


def test_the_cap_is_held_back_from_the_hinge_end(gate, parts):
    """The gate and railing caps share a height; the setback keeps every cap
    point's swing radius clear of the railing cap."""
    cap = next(p for p in parts if p.label == "cap")
    assert cap.length_mm == pytest.approx(gate.gate_width - 2.5 * IN)
    findings = gate.check_swing_clearance()
    assert all(f.severity is Severity.INFO for f in findings)


def test_a_full_length_cap_is_told_it_will_hit_the_railing():
    proud = DeckStairGate(cap_hinge_setback_in=0.0)
    findings = proud.check_swing_clearance()
    assert any(f.severity is Severity.WARN for f in findings)


def test_a_baluster_too_short_to_reach_both_rails_is_refused():
    with pytest.raises(ValueError):
        DeckStairGate(slat_length_in=30.0)


# ---------------------------------------------------------------------------
# The bracing question
# ---------------------------------------------------------------------------


def test_glued_half_laps_need_no_diagonal(gate, parts):
    findings = gate.check_racking(parts)
    assert all(f.severity is Severity.INFO for f in findings)
    assert "no diagonal needed" in findings[0].message


def test_pocket_screwed_corners_are_told_to_add_the_cable():
    flimsy = DeckStairGate(corner_joinery="pocket_screw")
    parts = extract(flimsy.build())
    findings = flimsy.check_racking(parts)
    assert any(f.severity is Severity.WARN for f in findings)
    assert "cable" in findings[0].message


def test_a_cable_brace_takes_the_corners_out_of_the_argument():
    braced = DeckStairGate(corner_joinery="pocket_screw", brace="cable")
    parts = extract(braced.build())
    findings = braced.check_racking(parts)
    assert all(f.severity is Severity.INFO for f in findings)


def test_the_full_report_is_clean_by_default(gate, parts):
    report = gate.check(gate.build(), parts)
    assert report.ok
    assert not any(f.severity is Severity.WARN for f in report.findings)


# ---------------------------------------------------------------------------
# Cedar is light, and the model knows it
# ---------------------------------------------------------------------------


def test_the_gate_is_a_one_hand_gate(parts):
    """A cedar gate this size is ~11 lb.  If this creeps toward 10 kg the
    density table has lost white_cedar and fallen back to the default."""
    from woodshop.checks import estimate_mass_kg

    assert estimate_mass_kg(parts) < 7.0
