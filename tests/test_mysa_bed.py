"""Tests for the Mysa sleigh bed.

The published listing gives an envelope and a handful of numbers.  Everything
else in this model is measured off the manufacturer's Cylindo 360 viewer — see
the module docstring in ``projects/mysa_bed.py``.  These tests pin both: the
published numbers because they are the contract, and the measured ones because
the first version of this model inferred them from prose and got a different
bed.
"""

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


@pytest.fixture(scope="module")
def queen_parts(queen):
    return {p.label: p for p in extract(queen.build())}


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
# What the 360 shows, and the prose did not
# ---------------------------------------------------------------------------


def test_there_is_no_footboard(queen_parts):
    """Regression: the first model invented a 15" footboard rail.

    The foot of this bed is the rail and nothing above it.
    """
    assert "footboard_rail" not in queen_parts
    assert "foot_rail" in queen_parts


def test_the_headboard_is_a_slab_not_a_frame_and_panel(queen_parts):
    """Regression: the first model invented top and bottom headboard rails."""
    assert "headboard_top_rail" not in queen_parts
    assert "headboard_bottom_rail" not in queen_parts
    assert queen_parts["headboard_panel"].qty == 1


def test_the_head_stiles_are_sawn_to_a_profile_not_square(queen_parts):
    """Regression: the first model used 1-3/4" square posts."""
    stile = queen_parts["head_stile"]
    assert stile.qty == 2
    assert stile.shape == "shaped"
    assert stile.length_mm > stile.width_mm, "the grain runs up the stile"


def test_the_foot_legs_are_sawn_to_a_profile(queen_parts):
    leg = queen_parts["foot_leg"]
    assert leg.qty == 2
    assert leg.shape == "shaped"


def test_a_shaped_part_wastes_stock_a_rectangle_would_not(queen):
    """The blank is the bounding rectangle; the curve is what the saw removes."""
    parts = {p.label: p for p in extract(queen.build())}
    stile = parts["head_stile"]
    assert stile.finished_area_mm2 < stile.blank_area_mm2 * 0.95


def test_the_stile_is_deepest_around_rail_height(queen):
    """The measured curve: narrow at the floor, widest at the rail, tapered up."""
    profile = queen.stile_profile()
    def depth_at(height_in):
        target = height_in * IN
        return max(
            -y for x, y in profile if abs(x - target) < 3.0 * IN
        )
    assert depth_at(0.5) < depth_at(16.0)
    assert depth_at(38.0) < depth_at(16.0)
    assert depth_at(16.0) == pytest.approx(queen.stile_depth_max_in * IN, rel=0.02)


def test_the_stile_back_edge_is_straight_and_on_the_head_end(queen):
    profile = queen.stile_profile()
    assert min(-y for _, y in profile) == pytest.approx(0.0, abs=1e-6)


def test_the_foot_leg_is_narrower_at_the_floor_than_at_the_rail(queen):
    profile = queen.leg_profile()
    at_floor = max(y for x, y in profile if x < 1.0)
    at_rail = max(y for x, y in profile if x > queen.rail_bottom_z - 1.0)
    assert at_floor < at_rail
    assert at_floor == pytest.approx(queen.leg_depth_foot_in * IN, rel=0.02)


def test_the_foot_legs_form_the_corners(queen):
    """Regression: the first measuring pass stopped the legs under the rails.

    The 360 shows the legs running up past the rail — the rails butt into
    them — with a rounded runner tip standing proud of the rail top.
    """
    from woodshop.render.model3d import _iter_leaf_parts

    tops = {
        p.label: p.bounding_box().max.Z for p in _iter_leaf_parts(queen.build())
    }
    assert tops["foot_leg"] == pytest.approx(
        queen.rail_top_z + queen.leg_tip_above_rail_in * IN, abs=0.1
    )
    assert tops["side_rail"] == pytest.approx(queen.rail_top_z, abs=0.1)


def test_the_headboard_rakes_back(queen):
    """The panel leans away from the bed; its top is nearer the head end."""
    from woodshop.render.model3d import _iter_leaf_parts

    panel = [
        p for p in _iter_leaf_parts(queen.build())
        if p.label == "headboard_panel"
    ][0]
    bb = panel.bounding_box()
    # A vertical panel 1" thick would occupy 1" of length; a raked one occupies
    # its own thickness plus the run of the lean.
    assert bb.size.Y > queen.panel_thickness_mm * 2


def test_the_stiles_stand_proud_of_the_panel(queen):
    from woodshop.render.model3d import _iter_leaf_parts

    tops = {p.label: p.bounding_box().max.Z for p in _iter_leaf_parts(queen.build())}
    assert tops["head_stile"] > tops["headboard_panel"]
    assert tops["head_stile"] == pytest.approx(queen.overall_h, abs=0.1)


# ---------------------------------------------------------------------------
# Published detail dimensions
# ---------------------------------------------------------------------------


def test_slat_tops_are_fourteen_inches_off_the_floor(queen):
    assert queen.slat_bearing_z + queen.slat_thickness_mm == pytest.approx(14 * IN)


def test_headboard_gap_is_nine_and_three_quarter_inches(queen):
    gap = queen.headboard_panel_bottom_z - 14 * IN
    assert gap == pytest.approx(9.75 * IN)


def test_the_measured_stile_depth_leaves_room_for_a_queen_mattress(queen):
    """87 - 5-3/4 - 1 = 80-1/4: an 80" mattress with a whisker of clearance."""
    assert queen.deck_length == pytest.approx(80.25 * IN)
    assert queen.deck_length >= SIZES["queen"].mattress_l_in * IN


def test_sixteen_slats_fit_the_deck(queen):
    assert queen.n_slats == 16
    assert queen.slat_run < queen.deck_length


def test_slats_span_the_deck_and_rest_on_the_ledgers(queen):
    assert queen.slat_length == pytest.approx(queen.deck_width)
    assert queen.split_slats is False
    assert queen.slat_cut_length == pytest.approx(queen.slat_length)


# ---------------------------------------------------------------------------
# The cut list
# ---------------------------------------------------------------------------


def test_faithful_bed_is_all_solid_cherry(queen):
    assert {p.material for p in extract(queen.build())} == {"cherry"}


def test_expected_parts_and_counts(queen_parts):
    assert queen_parts["head_stile"].qty == 2
    assert queen_parts["foot_leg"].qty == 2
    assert queen_parts["side_rail"].qty == 2
    assert queen_parts["foot_rail"].qty == 1
    assert queen_parts["head_rail"].qty == 1
    assert queen_parts["slat_ledger"].qty == 2
    assert queen_parts["slat"].qty == 16
    assert queen_parts["slat_spacer"].qty == 30  # 15 gaps, both sides
    assert "centre_rail_cap" not in queen_parts  # only needed for split slats


def test_the_spacers_are_slat_stock(queen_parts, queen):
    """They fill the gap between slat ends, so they match the slats."""
    assert queen_parts["slat_spacer"].thickness_mm == pytest.approx(
        queen.slat_thickness_mm
    )


def test_faithful_bed_passes_every_check(queen):
    assembly = queen.build()
    report = queen.check(assembly, extract(assembly))
    assert report.ok, report.to_text()


def test_the_stiles_come_out_of_eight_quarter_stock(queen):
    """A 1-3/4" finished stile is exactly what 8/4 surfaces to.

    Regression: the first measuring pass called the stiles 2" — an artifact
    of scaling the Cal King render against the queen envelope — and 2" needs
    10/4.  The corrected 1-3/4" saves a whole thickness class.
    """
    from woodshop.cutlist.hardwood import nest_hardwood

    plan = nest_hardwood(extract(queen.build()), queen.inventory, "cherry")
    quarters = {
        g.stock.thickness_quarter
        for g in plan.groups
        for p in g.parts
        if p.label.startswith("head_stile")
    }
    assert quarters == {"8/4"}


# ---------------------------------------------------------------------------
# The plywood variant
# ---------------------------------------------------------------------------


def test_plywood_variant_substitutes_only_panel_and_slats(queen_plywood):
    parts = {p.label: p for p in extract(queen_plywood.build())}
    assert parts["headboard_panel"].material == "plywood_cherry"
    assert parts["slat"].material == "plywood_baltic_birch"
    assert parts["side_rail"].material == "cherry"
    assert parts["head_stile"].material == "cherry"


def test_plywood_thicknesses_are_measured_not_nominal(queen_plywood):
    # 3/4" cherry ply is 45/64"; 3/4" Baltic birch is 18 mm.
    assert queen_plywood.panel_thickness_mm == pytest.approx(17.86, abs=0.05)
    assert queen_plywood.slat_thickness_mm == pytest.approx(18.0, abs=0.05)


def test_queen_slats_are_whole_because_baltic_birch_comes_in_4x8(queen_plywood):
    """O'Brien stocks Baltic birch as 4x8 as well as 5x5, so 62" fits."""
    assert queen_plywood.split_slats is False
    parts = {p.label: p for p in extract(queen_plywood.build())}
    assert parts["slat"].qty == 16
    assert parts["slat"].length_mm == pytest.approx(62 * IN, abs=0.1)
    assert "centre_rail_cap" not in parts


def test_split_slats_meet_over_the_centre_cap():
    """The split machinery still works when a shop only has 5x5 sheets."""
    bed = MysaBed(size=SIZES["queen"], variant="plywood", split_slats=True)
    assert bed.half_slat_length * 2 == pytest.approx(bed.slat_length)
    parts = {p.label: p for p in extract(bed.build())}
    assert parts["half_slat"].qty == 32
    assert parts["centre_rail_cap"].qty == 1


def test_split_is_chosen_when_only_five_by_five_is_stocked():
    """Regression: the decision must follow the inventory, not a constant."""
    inv = Inventory.from_dict(
        {
            "hardwood": [
                {
                    "species": "cherry", "thickness_quarter": q,
                    "rough_thickness_in": r, "surfaced_thickness_in": s,
                    "typical_width_in": 7, "lengths_ft": [8],
                }
                for q, r, s in [("4/4", 1.0, 0.75), ("5/4", 1.25, 1.0),
                                ("8/4", 2.0, 1.75), ("10/4", 2.5, 2.25)]
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


def test_plywood_variant_has_no_errors_but_warns_about_deflection(queen_plywood):
    assembly = queen_plywood.build()
    report = queen_plywood.check(assembly, extract(assembly))
    assert report.ok, report.to_text()
    codes = {f.code for f in report.findings if f.severity is Severity.WARN}
    assert "deflection" in codes
    assert "thickness" in codes


def test_narrow_beds_do_not_need_split_slats():
    """A twin slat is 42" and comes whole out of a 60" sheet."""
    twin = MysaBed(size=SIZES["twin"], variant="plywood")
    assert twin.split_slats is False
    assert twin.slat_cut_length == pytest.approx(twin.slat_length)


@pytest.mark.parametrize("size_name", sorted(SIZES))
def test_no_size_needs_split_slats_with_4x8_stocked(size_name):
    bed = MysaBed(size=SIZES[size_name], variant="plywood")
    assert bed.split_slats is False
    assert bed.slat_length <= 96 * IN


def test_invalid_variant_rejected():
    with pytest.raises(ValueError, match="variant"):
        MysaBed(size=SIZES["queen"], variant="carbon_fibre")


def test_forced_split_is_reported_as_a_choice_not_a_stock_limit():
    """Regression: the message named the sheet that *would* fit them whole."""
    bed = MysaBed(size=SIZES["queen"], variant="plywood", split_slats=True)
    assembly = bed.build()
    slats = [
        f.message
        for f in bed.check(assembly, extract(assembly)).findings
        if f.code == "slats"
    ]
    assert any("by request, not by necessity" in m for m in slats)
    assert not any("would come whole out of" in m for m in slats)


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
