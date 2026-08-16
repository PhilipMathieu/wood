"""Tests for the Mysa sleigh bed model, against the published specification."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "projects"))

from mysa_bed import IN, SIZES, MysaBed  # noqa: E402

from woodshop.checks import Severity  # noqa: E402
from woodshop.cutlist.extract import extract  # noqa: E402


@pytest.fixture(scope="module")
def queen() -> MysaBed:
    return MysaBed(size=SIZES["queen"])


@pytest.fixture(scope="module")
def queen_plywood() -> MysaBed:
    return MysaBed(size=SIZES["queen"], variant="plywood")


# ---------------------------------------------------------------------------
# The published envelope
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("size_name", sorted(SIZES))
@pytest.mark.parametrize("variant", ["faithful", "plywood"])
def test_assembly_matches_the_published_envelope(size_name, variant):
    bed = MysaBed(size=SIZES[size_name], variant=variant)
    bb = bed.build().bounding_box()
    assert bb.size.X == pytest.approx(bed.overall_w, abs=0.1)
    assert bb.size.Y == pytest.approx(bed.overall_l, abs=0.1)
    assert bb.size.Z == pytest.approx(bed.overall_h, abs=0.1)


@pytest.mark.parametrize("size_name", sorted(SIZES))
def test_bed_sits_on_the_floor(size_name):
    bb = MysaBed(size=SIZES[size_name]).build().bounding_box()
    assert bb.min.Z == pytest.approx(0.0, abs=0.1)


# ---------------------------------------------------------------------------
# Published detail dimensions
# ---------------------------------------------------------------------------


def test_slat_tops_are_fourteen_inches_off_the_floor(queen):
    assert queen.slat_bearing_z + queen.slat_thickness_mm == pytest.approx(14 * IN)


def test_headboard_gap_is_nine_and_three_quarter_inches(queen):
    gap = queen.headboard_panel_bottom_z - 14 * IN
    assert gap == pytest.approx(9.75 * IN)


def test_sixteen_slats_fit_the_deck(queen):
    assert queen.n_slats == 16
    assert queen.slat_run < queen.deck_length


def test_slat_length_reaches_into_both_rail_rabbets(queen):
    assert queen.slat_length == pytest.approx(queen.deck_width + 2 * 0.25 * IN)


def test_faithful_variant_uses_full_width_slats(queen):
    assert queen.split_slats is False
    assert queen.slat_cut_length == pytest.approx(queen.slat_length)


# ---------------------------------------------------------------------------
# The cut list
# ---------------------------------------------------------------------------


def test_faithful_bed_is_all_solid_cherry(queen):
    parts = extract(queen.build())
    assert {p.material for p in parts} == {"cherry"}


def test_expected_parts_and_counts(queen):
    parts = {p.label: p for p in extract(queen.build())}
    assert parts["head_post"].qty == 2
    assert parts["foot_post"].qty == 2
    assert parts["side_rail"].qty == 2
    assert parts["slat"].qty == 16
    assert parts["slat_spacer"].qty == 30  # 15 gaps, both sides
    assert "centre_rail_cap" not in parts  # only needed for split slats


def test_faithful_bed_passes_every_check(queen):
    assembly = queen.build()
    report = queen.check(assembly, extract(assembly))
    assert report.ok, report.to_text()


# ---------------------------------------------------------------------------
# The plywood variant
# ---------------------------------------------------------------------------


def test_plywood_variant_substitutes_only_panel_and_slats(queen_plywood):
    parts = {p.label: p for p in extract(queen_plywood.build())}
    assert parts["headboard_panel"].material == "plywood_cherry"
    assert parts["half_slat"].material == "plywood_baltic_birch"
    assert parts["side_rail"].material == "cherry"
    assert parts["head_post"].material == "cherry"


def test_plywood_thicknesses_are_measured_not_nominal(queen_plywood):
    # 3/4" cherry ply is 45/64"; 3/4" Baltic birch is 18 mm.
    assert queen_plywood.panel_thickness_mm == pytest.approx(17.86, abs=0.05)
    assert queen_plywood.slat_thickness_mm == pytest.approx(18.0, abs=0.05)


def test_queen_slats_are_split_because_baltic_birch_is_sixty_inches(queen_plywood):
    assert queen_plywood.split_slats is True
    parts = {p.label: p for p in extract(queen_plywood.build())}
    assert parts["half_slat"].qty == 32
    assert parts["half_slat"].length_mm == pytest.approx(31.25 * IN, abs=0.1)


def test_split_slats_meet_over_the_centre_cap(queen_plywood):
    assert queen_plywood.half_slat_length * 2 == pytest.approx(
        queen_plywood.slat_length
    )
    parts = {p.label: p for p in extract(queen_plywood.build())}
    assert parts["centre_rail_cap"].qty == 1


def test_spacers_follow_the_slat_thickness(queen_plywood):
    parts = {p.label: p for p in extract(queen_plywood.build())}
    assert parts["slat_spacer"].width_mm == pytest.approx(
        queen_plywood.slat_thickness_mm
    )


def test_plywood_variant_has_no_errors_but_warns_about_deflection(queen_plywood):
    assembly = queen_plywood.build()
    report = queen_plywood.check(assembly, extract(assembly))
    assert report.ok, report.to_text()
    codes = {f.code for f in report.findings if f.severity is Severity.WARN}
    assert "deflection" in codes
    assert "thickness" in codes


def test_narrow_beds_do_not_need_split_slats():
    """A twin slat is 42-1/2" and comes whole out of a 60" sheet."""
    twin = MysaBed(size=SIZES["twin"], variant="plywood")
    assert twin.split_slats is False
    assert twin.slat_cut_length == pytest.approx(twin.slat_length)


@pytest.mark.parametrize(
    "size_name, expect_split",
    [
        ("twin", False),     # 42-1/2" slat
        ("full", False),     # 57-1/2" slat — just inside a 60" sheet
        ("queen", True),     # 62-1/2"
        ("king", True),      # 81-1/2"
        ("calking", True),   # 77-1/2"
    ],
)
def test_split_is_decided_by_sheet_size_per_bed_size(size_name, expect_split):
    bed = MysaBed(size=SIZES[size_name], variant="plywood")
    assert bed.split_slats is expect_split
    if not expect_split:
        assert bed.slat_length <= 60 * IN


def test_split_can_be_forced_off():
    bed = MysaBed(size=SIZES["queen"], variant="plywood", split_slats=False)
    assembly = bed.build()
    report = bed.check(assembly, extract(assembly))
    assert not report.ok
    assert any(f.code == "sheet_fit" for f in report.errors)


def test_invalid_variant_rejected():
    with pytest.raises(ValueError, match="variant"):
        MysaBed(size=SIZES["queen"], variant="carbon_fibre")
