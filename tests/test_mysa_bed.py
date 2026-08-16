"""Tests for the Mysa sleigh bed model, against the published specification."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "projects"))

from mysa_bed import IN, SIZES, MysaBed  # noqa: E402

from woodshop.checks import Severity  # noqa: E402
from woodshop.cutlist.extract import extract  # noqa: E402
from woodshop.inventory import Inventory  # noqa: E402


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
    assert parts["slat"].material == "plywood_baltic_birch"
    assert parts["side_rail"].material == "cherry"
    assert parts["head_post"].material == "cherry"


def test_plywood_thicknesses_are_measured_not_nominal(queen_plywood):
    # 3/4" cherry ply is 45/64"; 3/4" Baltic birch is 18 mm.
    assert queen_plywood.panel_thickness_mm == pytest.approx(17.86, abs=0.05)
    assert queen_plywood.slat_thickness_mm == pytest.approx(18.0, abs=0.05)


def test_queen_slats_are_whole_because_baltic_birch_comes_in_4x8(queen_plywood):
    """O'Brien stocks Baltic birch as 4x8 as well as 5x5, so 62-1/2" fits."""
    assert queen_plywood.split_slats is False
    parts = {p.label: p for p in extract(queen_plywood.build())}
    assert parts["slat"].qty == 16
    assert parts["slat"].length_mm == pytest.approx(62.5 * IN, abs=0.1)
    assert "centre_rail_cap" not in parts


def test_split_slats_meet_over_the_centre_cap():
    """The split machinery still works when a shop only has 5x5 sheets."""
    bed = MysaBed(size=SIZES["queen"], variant="plywood", split_slats=True)
    assert bed.half_slat_length * 2 == pytest.approx(bed.slat_length)
    parts = {p.label: p for p in extract(bed.build())}
    assert parts["half_slat"].qty == 32
    assert parts["half_slat"].length_mm == pytest.approx(31.25 * IN, abs=0.1)
    assert parts["centre_rail_cap"].qty == 1


def test_split_is_chosen_when_only_five_by_five_is_stocked():
    """Regression: the decision must follow the inventory, not a constant."""
    inv = Inventory.from_dict(
        {
            "hardwood": [
                {
                    "species": "cherry", "thickness_quarter": "4/4",
                    "rough_thickness_in": 1.0, "surfaced_thickness_in": 0.75,
                    "typical_width_in": 7, "lengths_ft": [8],
                }
            ],
            "sheet_goods": [
                {
                    "material": "plywood_cherry", "nominal_thickness": "3/4",
                    "actual_thickness_in": 0.703125,
                    "sheet_width_in": 48, "sheet_height_in": 96, "grain": "length",
                },
                {
                    "material": "plywood_baltic_birch", "nominal_thickness": "3/4",
                    "actual_thickness_in": 0.7087,
                    "sheet_width_in": 60, "sheet_height_in": 60, "grain": "none",
                },
            ],
        }
    )
    bed = MysaBed(size=SIZES["queen"], variant="plywood", inventory=inv)
    assert bed.split_slats is True


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
        ("full", False),     # 57-1/2"
        ("queen", False),    # 62-1/2" — fits the 96" side of a 4x8
        ("king", False),     # 81-1/2"
        ("calking", False),  # 77-1/2"
    ],
)
def test_no_size_needs_split_slats_with_4x8_stocked(size_name, expect_split):
    bed = MysaBed(size=SIZES[size_name], variant="plywood")
    assert bed.split_slats is expect_split
    assert bed.slat_length <= 96 * IN


def test_king_slat_exceeds_even_a_4x8_sheet():
    """An 81-1/2" slat still clears 96", but check the guard is live."""
    bed = MysaBed(size=SIZES["king"], variant="plywood")
    assembly = bed.build()
    report = bed.check(assembly, extract(assembly))
    assert report.ok, report.to_text()


def test_invalid_variant_rejected():
    with pytest.raises(ValueError, match="variant"):
        MysaBed(size=SIZES["queen"], variant="carbon_fibre")


def test_forced_split_is_reported_as_a_choice_not_a_stock_limit():
    """Regression: the message named the sheet that *would* fit them whole.

    With 4x8 Baltic birch stocked, a forced split is a decision — reporting
    "sheets are only 96 inches" blamed stock for something the flag did.
    """
    bed = MysaBed(size=SIZES["queen"], variant="plywood", split_slats=True)
    assembly = bed.build()
    slats = [
        f.message
        for f in bed.check(assembly, extract(assembly)).findings
        if f.code == "slats"
    ]
    assert any("by request, not by necessity" in m for m in slats)
    assert not any("would come whole out of" in m for m in slats)


def test_genuinely_forced_split_names_the_largest_stocked_sheet(monkeypatch):
    inv = Inventory.from_dict(
        {
            "hardwood": [
                {
                    "species": "cherry", "thickness_quarter": q,
                    "rough_thickness_in": r, "surfaced_thickness_in": s,
                    "typical_width_in": 7, "lengths_ft": [8],
                }
                for q, r, s in [("4/4", 1.0, 0.75), ("5/4", 1.25, 1.0),
                                ("8/4", 2.0, 1.75)]
            ],
            "sheet_goods": [
                {
                    "material": "plywood_cherry", "nominal_thickness": "3/4",
                    "actual_thickness_in": 0.703125, "sheet_width_in": 48,
                    "sheet_height_in": 96, "grain": "length",
                },
                {
                    "material": "plywood_baltic_birch", "nominal_thickness": "3/4",
                    "actual_thickness_in": 0.7087, "sheet_width_in": 60,
                    "sheet_height_in": 60, "grain": "none",
                },
            ],
        }
    )
    bed = MysaBed(size=SIZES["queen"], variant="plywood", inventory=inv)
    assert bed.split_slats is True
    assembly = bed.build()
    slats = [
        f.message
        for f in bed.check(assembly, extract(assembly)).findings
        if f.code == "slats"
    ]
    assert any('largest stocked plywood_baltic_birch sheet is 60" x 60"' in m
               for m in slats)


def test_forced_split_on_a_solid_bed_names_no_sheet():
    """A solid-cherry bed has no Baltic birch in it to blame."""
    bed = MysaBed(size=SIZES["queen"], split_slats=True)
    assembly = bed.build()
    slats = [
        f.message
        for f in bed.check(assembly, extract(assembly)).findings
        if f.code == "slats"
    ]
    assert any("by request" in m for m in slats)
    assert not any("plywood" in m for m in slats)
