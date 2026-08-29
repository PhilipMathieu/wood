"""Design checks that run against a model before any stock is cut.

A cut list will happily tell you to cut a 62-1/2" slat from a 60" sheet, or to
plough a 3/4" groove for a panel that is really 45/64" thick.  The checks here
catch that class of mistake — the ones that come from a number being *nearly*
right — and report them as :class:`Finding` objects rather than exceptions, so
a design can be evaluated as a whole.

Example
-------
>>> from woodshop.checks import Finding, Severity
>>> f = Finding(Severity.WARN, "clearance", "1 in. per side is loose")
>>> f.severity is Severity.WARN
True
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import TYPE_CHECKING, Iterable

from woodshop.cutlist.extract import CutPart
from woodshop.lumber import mm_to_fractional_inch

if TYPE_CHECKING:
    from woodshop.inventory import Inventory, PricedStock

__all__ = [
    "Severity",
    "Finding",
    "CheckReport",
    "ELASTIC_MODULUS_MPA",
    "DENSITY_KG_M3",
    "STALE_AFTER_DAYS",
    "check_envelope",
    "check_sheet_fit",
    "check_thickness_substitution",
    "check_slat_deflection",
    "check_shelf_deflection",
    "check_material_suitability",
    "check_wood_movement",
    "check_price_provenance",
    "check_tip_resistance",
    "estimate_mass_kg",
]

_MM_PER_IN = 25.4


class Severity(str, Enum):
    """How much a finding matters."""

    INFO = "info"
    WARN = "warn"
    ERROR = "error"


@dataclass
class Finding:
    """A single design observation.

    Parameters
    ----------
    severity : Severity
        ``INFO`` for something worth knowing, ``WARN`` for something to decide
        about, ``ERROR`` for something that cannot be built as drawn.
    code : str
        Short machine-readable category, e.g. ``"sheet_fit"``.
    message : str
        Human-readable description, written for someone standing at the saw.
    """

    severity: Severity
    code: str
    message: str

    def __str__(self) -> str:
        """Return a one-line ``SEVERITY [code] message`` rendering."""
        return f"{self.severity.value.upper():5s} [{self.code}] {self.message}"


@dataclass
class CheckReport:
    """A collection of findings.

    Parameters
    ----------
    findings : list[Finding]
        All findings, in the order they were produced.
    """

    findings: list[Finding] = field(default_factory=list)

    def extend(self, findings: Iterable[Finding]) -> "CheckReport":
        """Append *findings* and return self, for chaining."""
        self.findings.extend(findings)
        return self

    @property
    def errors(self) -> list[Finding]:
        """Findings with ``ERROR`` severity."""
        return [f for f in self.findings if f.severity is Severity.ERROR]

    @property
    def ok(self) -> bool:
        """``True`` if nothing is an ``ERROR``."""
        return not self.errors

    def to_text(self) -> str:
        """Render the report as plain text, one finding per line."""
        if not self.findings:
            return "No findings."
        return "\n".join(str(f) for f in self.findings)


# Flatwise modulus of elasticity, MPa.  Solid-wood values are USDA Wood
# Handbook averages at 12% MC; plywood values are flatwise panel averages,
# which are well below the solid-wood figure for the same species because the
# cross plies contribute little along the span.
ELASTIC_MODULUS_MPA: dict[str, float] = {
    "cherry": 10_300.0,
    "maple": 12_600.0,
    "walnut": 11_600.0,
    "white_oak": 12_300.0,
    "pine": 8_500.0,
    "poplar": 10_900.0,
    "plywood_birch": 6_900.0,
    "plywood_cherry": 6_200.0,
    "plywood_baltic_birch": 6_500.0,
}


def check_envelope(
    actual_l_mm: float,
    actual_w_mm: float,
    actual_h_mm: float,
    published_l_mm: float,
    published_w_mm: float,
    published_h_mm: float,
    tolerance_mm: float = 1.6,
) -> list[Finding]:
    """Compare a model's overall envelope against a published specification.

    Parameters
    ----------
    actual_l_mm, actual_w_mm, actual_h_mm : float
        Envelope measured from the model.
    published_l_mm, published_w_mm, published_h_mm : float
        Envelope the design is supposed to hit.
    tolerance_mm : float, optional
        Allowed deviation, default 1.6 mm (1/16").

    Returns
    -------
    list[Finding]
        One ``INFO`` per matching dimension, one ``WARN`` per deviation.
    """
    findings: list[Finding] = []
    for name, actual, published in (
        ("length", actual_l_mm, published_l_mm),
        ("width", actual_w_mm, published_w_mm),
        ("height", actual_h_mm, published_h_mm),
    ):
        delta = actual - published
        if abs(delta) <= tolerance_mm:
            findings.append(
                Finding(
                    Severity.INFO,
                    "envelope",
                    f"overall {name} {mm_to_fractional_inch(actual)} matches published",
                )
            )
        else:
            findings.append(
                Finding(
                    Severity.WARN,
                    "envelope",
                    f"overall {name} {mm_to_fractional_inch(actual)} vs published "
                    f"{mm_to_fractional_inch(published)} "
                    f"({delta / _MM_PER_IN:+.3f} in.)",
                )
            )
    return findings


def check_clearance(
    name: str,
    clearance_mm: float,
    min_mm: float,
    max_mm: float,
    tight_note: str = "",
    loose_note: str = "",
) -> list[Finding]:
    """Flag a clearance that falls outside a comfortable band.

    Parameters
    ----------
    name : str
        What the clearance is, e.g. ``"mattress side clearance"``.
    clearance_mm : float
        The measured clearance.
    min_mm, max_mm : float
        Acceptable range.
    tight_note, loose_note : str, optional
        What being under or over the band costs, in the caller's own terms —
        a mattress binds, a record sleeve will not come out with one hand.
        The band alone cannot say which, and a check that guesses says
        "mattress" to a bookcase.

    Returns
    -------
    list[Finding]
        A single finding: ``INFO`` inside the band, ``WARN`` outside it.
    """
    text = f"{name} is {mm_to_fractional_inch(clearance_mm)}"
    if clearance_mm < min_mm:
        note = f", {tight_note}" if tight_note else ""
        return [Finding(Severity.WARN, "clearance", f"{text} — tight{note}")]
    if clearance_mm > max_mm:
        note = f", {loose_note}" if loose_note else ""
        return [Finding(Severity.WARN, "clearance", f"{text} — loose{note}")]
    return [Finding(Severity.INFO, "clearance", text)]


def check_sheet_fit(parts: list[CutPart], inventory: "Inventory") -> list[Finding]:
    """Check that every sheet-goods part fits on a sheet of its own material.

    Grain direction is honoured: a part with ``grain_direction="length"`` on a
    grained sheet cannot be turned 90° to make it fit.

    Parameters
    ----------
    parts : list[CutPart]
        Parts to check.  Materials with no sheet entry in *inventory* are
        assumed to be solid stock and skipped.
    inventory : Inventory
        Stock inventory supplying sheet sizes.

    Returns
    -------
    list[Finding]
        ``ERROR`` for any part that fits no sheet, ``INFO`` otherwise.
    """
    findings: list[Finding] = []
    sheet_materials = {s.material for s in inventory.sheet_goods}

    for p in parts:
        if p.material not in sheet_materials:
            continue
        findings.extend(_check_sheet_thickness(p, inventory))
        # Where a material comes in several sizes, ask for the smallest that
        # actually yields this part rather than guessing from thickness.
        sheet = inventory.best_sheet_for(
            p.material,
            length_mm=p.length_mm,
            width_mm=p.width_mm,
            part_grain=p.grain_direction,
            thickness_mm=p.thickness_mm,
        )
        rotatable = sheet.grain == "none" or p.grain_direction == "none"
        if sheet.fits(p.length_mm, p.width_mm, p.grain_direction):
            findings.append(
                Finding(
                    Severity.INFO,
                    "sheet_fit",
                    f"{p.label} ({mm_to_fractional_inch(p.length_mm)} x "
                    f"{mm_to_fractional_inch(p.width_mm)}) fits "
                    f"{p.material} {sheet.size_label}",
                )
            )
        else:
            grain_note = (
                "" if rotatable else " (face grain must run along its length, so it "
                "cannot be turned to fit)"
            )
            findings.append(
                Finding(
                    Severity.ERROR,
                    "sheet_fit",
                    f"{p.label} is {mm_to_fractional_inch(p.length_mm)} x "
                    f"{mm_to_fractional_inch(p.width_mm)} but the largest "
                    f"{p.material} sheet stocked is {sheet.size_label}"
                    f"{grain_note} — it cannot be cut from one piece",
                )
            )
    return findings


def _check_sheet_thickness(
    part: CutPart,
    inventory: "Inventory",
    tolerance_mm: float = 0.5,
) -> list[Finding]:
    """Report a sheet part thicker than anything the material comes in.

    Sheet fit used to be a question about length and width only, which let a
    1-3/4" turning blank "fit" a 3/4" sheet.  A part thicker than the stock is
    either a lamination — say so, with the layer count — or a mistake.
    """
    candidates = inventory.sheets_for(part.material)
    if not candidates:
        return []
    thickest = max(s.thickness_mm for s in candidates)
    if part.thickness_mm <= thickest + tolerance_mm:
        return []

    layers = round(part.thickness_mm / thickest)
    if layers >= 2 and abs(part.thickness_mm - layers * thickest) <= tolerance_mm:
        return [
            Finding(
                Severity.INFO,
                "sheet_fit",
                f"{part.label} at {mm_to_fractional_inch(part.thickness_mm)} is "
                f"{layers} layers of "
                f"{mm_to_fractional_inch(thickest, 64)} {part.material} "
                "laminated — no sheet is stocked that thick",
            )
        ]
    return [
        Finding(
            Severity.ERROR,
            "sheet_fit",
            f"{part.label} is {mm_to_fractional_inch(part.thickness_mm)} thick "
            f"but the thickest {part.material} stocked is "
            f"{mm_to_fractional_inch(thickest, 64)}, and it is not a whole "
            "number of layers",
        )
    ]


def check_thickness_substitution(
    parts: list[CutPart],
    inventory: "Inventory",
    joint_tolerance_mm: float = 0.4,
) -> list[Finding]:
    """Flag sheet parts whose real thickness differs from their nominal label.

    This is the check that catches "3/4" plywood is not 3/4"".  It matters
    wherever a part lands in a groove, dado, or rabbet sized off the nominal
    number.

    Parameters
    ----------
    parts : list[CutPart]
        Parts to check.
    inventory : Inventory
        Stock inventory supplying real thicknesses.
    joint_tolerance_mm : float, optional
        How much slop a glued joint tolerates, default 0.4 mm (about 1/64").

    Returns
    -------
    list[Finding]
        ``WARN`` where the gap exceeds *joint_tolerance_mm*.
    """
    findings: list[Finding] = []
    sheet_materials = {s.material for s in inventory.sheet_goods}
    seen: set[str] = set()

    for p in parts:
        if p.material not in sheet_materials or p.label in seen:
            continue
        seen.add(p.label)
        candidates = [s for s in inventory.sheet_goods if s.material == p.material]
        sheet = min(candidates, key=lambda s: abs(s.thickness_mm - p.thickness_mm))
        nominal_mm = _nominal_to_mm(sheet.nominal_thickness)
        gap = nominal_mm - sheet.thickness_mm
        if abs(gap) > joint_tolerance_mm:
            findings.append(
                Finding(
                    Severity.WARN,
                    "thickness",
                    f"{p.label}: {p.material} sold as "
                    f'{sheet.nominal_thickness}" measures '
                    f"{mm_to_fractional_inch(sheet.thickness_mm, 64)} "
                    f"({sheet.thickness_mm:.2f} mm) — a groove cut to "
                    f'{sheet.nominal_thickness}" would be '
                    f"{gap:.2f} mm loose; cut the groove to fit the sheet",
                )
            )
    return findings


def _nominal_to_mm(nominal: str) -> float:
    """Convert a nominal thickness label such as ``'3/4'`` to mm."""
    if "/" in nominal:
        num, den = nominal.split("/")
        return float(num) / float(den) * _MM_PER_IN
    return float(nominal) * _MM_PER_IN


def _udl_deflection_mm(
    span_mm: float,
    width_mm: float,
    thickness_mm: float,
    load_kg: float,
    e_mpa: float,
) -> float:
    """Return midspan sag of a simply-supported rectangular beam under a UDL.

    The one piece of beam theory this module needs, written once: a slat and a
    shelf are the same problem seen from different furniture.

    Parameters
    ----------
    span_mm : float
        Clear span between supports.
    width_mm : float
        Dimension across the span — a slat's width, a shelf's depth.
    thickness_mm : float
        Dimension the beam bends about.  It enters cubed, which is why an
        eighth of an inch of thickness beats a great deal of anything else.
    load_kg : float
        Total load on this one beam, spread evenly along it.
    e_mpa : float
        Modulus of elasticity in MPa.

    Returns
    -------
    float
        Midspan deflection in mm.
    """
    w = load_kg * 9.80665 / span_mm
    # Second moment of area of a rectangle bending about its weak axis.
    i_mm4 = width_mm * thickness_mm**3 / 12.0
    return 5.0 * w * span_mm**4 / (384.0 * e_mpa * i_mm4)


def check_slat_deflection(
    material: str,
    span_mm: float,
    slat_width_mm: float,
    slat_thickness_mm: float,
    n_slats: int,
    design_load_kg: float = 250.0,
    limit_ratio: float = 240.0,
) -> list[Finding]:
    """Estimate midspan deflection of a slat deck under load.

    Each slat is treated as a simply-supported beam over *span_mm* carrying an
    equal share of *design_load_kg* as a uniformly distributed load.  For a
    deck with a centre rail, pass the clear span *between* supports — halving
    the span cuts deflection by a factor of sixteen, which is usually the whole
    argument for having a centre rail.

    Parameters
    ----------
    material : str
        Material key, looked up in :data:`ELASTIC_MODULUS_MPA`.
    span_mm : float
        Clear span between supports.
    slat_width_mm, slat_thickness_mm : float
        Slat cross-section.
    n_slats : int
        Number of slats sharing the load.
    design_load_kg : float, optional
        Total deck load — mattress plus occupants — default 250 kg.
    limit_ratio : float, optional
        Deflection limit as span / ratio, default 240.

    Returns
    -------
    list[Finding]
        One finding with the computed deflection, ``WARN`` if it exceeds the
        limit, plus an ``INFO`` if the material's stiffness is unknown.

    Notes
    -----
    This is a serviceability estimate for comparing options, not a structural
    certification.  It ignores load sharing through the mattress, which makes
    it conservative, and it assumes the load is evenly spread, which a single
    person sitting on the edge is not.
    """
    e_mpa = ELASTIC_MODULUS_MPA.get(material)
    if e_mpa is None:
        return [
            Finding(
                Severity.INFO,
                "deflection",
                f"no stiffness figure for {material!r}; deflection not estimated",
            )
        ]

    deflection_mm = _udl_deflection_mm(
        span_mm=span_mm,
        width_mm=slat_width_mm,
        thickness_mm=slat_thickness_mm,
        load_kg=design_load_kg / n_slats,
        e_mpa=e_mpa,
    )
    limit_mm = span_mm / limit_ratio
    ratio = span_mm / deflection_mm if deflection_mm > 0 else float("inf")

    message = (
        f"{material} slat, {mm_to_fractional_inch(span_mm)} span: "
        f"{deflection_mm:.1f} mm midspan deflection under "
        f"{design_load_kg:.0f} kg over {n_slats} slats "
        f"(span/{ratio:.0f}; limit span/{limit_ratio:.0f} = {limit_mm:.1f} mm)"
    )
    if deflection_mm <= limit_mm:
        return [Finding(Severity.INFO, "deflection", message)]

    # Deflection per slat scales as 1/n, so the remedy is a slat count.
    needed = int(-(-n_slats * deflection_mm // limit_mm))
    # ...and as 1/t^3, so a thickness works too.
    thicker_mm = slat_thickness_mm * (deflection_mm / limit_mm) ** (1 / 3)
    return [
        Finding(
            Severity.WARN,
            "deflection",
            f"{message} — {needed} slats, or "
            f"{mm_to_fractional_inch(thicker_mm, 32)} stock, would meet it",
        )
    ]


def check_shelf_deflection(
    material: str,
    span_mm: float,
    depth_mm: float,
    thickness_mm: float,
    load_kg: float,
    label: str = "shelf",
    limit_ratio: float = 360.0,
    run_mm: float | None = None,
) -> list[Finding]:
    """Estimate midspan sag of a loaded shelf, and say what would fix it.

    Same beam as :func:`check_slat_deflection`, asked a different question.  A
    slat is one of many under a load that is fixed however many there are; a
    shelf is on its own, and its load *comes with its length* — twice the shelf
    holds twice the records.  So deflection here grows as the fourth power of
    the span, and the remedy that actually works is a divider rather than a
    thicker board.

    Parameters
    ----------
    material : str
        Material key, looked up in :data:`ELASTIC_MODULUS_MPA`.
    span_mm : float
        Clear span between supports.
    depth_mm : float
        Shelf depth, front to back.
    thickness_mm : float
        Shelf thickness.
    load_kg : float
        Total load on this one shelf when it is full.
    label : str, optional
        What the shelf is, for the message, default ``"shelf"``.
    limit_ratio : float, optional
        Sag limit as span / ratio, default 360 — the point at which a straight
        edge above a shelf stops looking straight.  Deflection this side of
        collapse is an appearance problem, and appearance is stricter than the
        span/240 a floor or a bed deck is held to.
    run_mm : float, optional
        The whole run the shelf divides up.  Given one, a failing shelf is told
        how many bays that run needs rather than only how short each may be.

    Returns
    -------
    list[Finding]
        One finding: ``INFO`` within the limit, ``WARN`` beyond it with both
        remedies costed.  ``INFO`` if the material's stiffness is unknown.

    Notes
    -----
    A serviceability estimate, not a structural one.  It ignores the stiffening
    a glued-on solid front edge contributes, which makes it conservative, and
    it assumes the load is spread evenly, which a full shelf of records nearly
    is and a single amplifier is not.
    """
    e_mpa = ELASTIC_MODULUS_MPA.get(material)
    if e_mpa is None:
        return [
            Finding(
                Severity.INFO,
                "deflection",
                f"no stiffness figure for {material!r}; {label} sag not estimated",
            )
        ]

    deflection_mm = _udl_deflection_mm(
        span_mm=span_mm,
        width_mm=depth_mm,
        thickness_mm=thickness_mm,
        load_kg=load_kg,
        e_mpa=e_mpa,
    )
    limit_mm = span_mm / limit_ratio
    ratio = span_mm / deflection_mm if deflection_mm > 0 else float("inf")

    message = (
        f"{label} in {material}, {mm_to_fractional_inch(span_mm)} span carrying "
        f"{load_kg:.1f} kg: {deflection_mm:.1f} mm midspan sag "
        f"(span/{ratio:.0f}; limit span/{limit_ratio:.0f} = {limit_mm:.1f} mm)"
    )
    if deflection_mm <= limit_mm:
        return [Finding(Severity.INFO, "deflection", message)]

    # Load per unit length is what the contents set, so sag goes as span^4 and
    # as 1/thickness^3.  Both remedies below hold the load per foot constant.
    max_span_mm = span_mm * (limit_mm / deflection_mm) ** 0.25
    thicker_mm = thickness_mm * (deflection_mm / limit_mm) ** (1 / 3)
    remedy = (
        f" — {mm_to_fractional_inch(max_span_mm)} is the longest span that "
        f"meets it, or {mm_to_fractional_inch(thicker_mm, 32)} stock at this "
        "span"
    )
    if run_mm is not None and max_span_mm > 0:
        bays = int(-(-run_mm // max_span_mm))
        remedy += f"; {bays} bays across a {mm_to_fractional_inch(run_mm)} run"
    return [Finding(Severity.WARN, "deflection", message + remedy)]


# Oven-dry-ish density at 8-12% MC, kg/m³.  Solid-wood figures are USDA Wood
# Handbook averages; plywood figures are panel averages, which run higher than
# the parent species because of the glue lines.
DENSITY_KG_M3: dict[str, float] = {
    "cherry": 560.0,
    "maple": 705.0,
    "walnut": 610.0,
    "white_oak": 755.0,
    "pine": 420.0,
    "poplar": 455.0,
    "white_cedar": 320.0,
    # As bought: ground-contact treatment leaves SYP saturated.  It dries
    # toward ~570 in service, so figures built on this run heavy — the safe
    # direction for racking and hinge loads.
    "syp_pt": 750.0,
    "plywood_birch": 680.0,
    "plywood_cherry": 590.0,
    "plywood_baltic_birch": 690.0,
}

_DEFAULT_DENSITY_KG_M3 = 600.0


def estimate_mass_kg(
    parts: Iterable[CutPart],
    default_density_kg_m3: float = _DEFAULT_DENSITY_KG_M3,
) -> float:
    """Estimate a piece's finished mass from its cut list.

    Blanks are what you buy; mass is what you end up carrying, so the estimate
    uses each part's *finished* face area rather than its blank.

    Parameters
    ----------
    parts : iterable of CutPart
        The cut list.
    default_density_kg_m3 : float, optional
        Density used for materials not in :data:`DENSITY_KG_M3`.

    Returns
    -------
    float
        Estimated mass in kilograms.

    Notes
    -----
    Joinery removes material this does not know about — mortises, grooves, and
    the hollow inside a frame and panel — so the figure runs a little high.
    That is the safe direction for a tipping calculation, where a heavier piece
    looks more stable than it is.
    """
    total_kg = 0.0
    for p in parts:
        density = DENSITY_KG_M3.get(p.material, default_density_kg_m3)
        volume_m3 = p.finished_area_mm2 * p.thickness_mm / 1e9
        total_kg += volume_m3 * density
    return total_kg


def check_material_suitability(
    parts: Iterable[CutPart],
    inventory: "Inventory | None" = None,
) -> list[Finding]:
    """Flag parts whose material cannot survive the operation that shapes them.

    Every other check in this module compares a number against a number.  This
    one compares a *material* against an *operation*, which is the question a
    cut list cannot ask on its own: a 3/4" Baltic birch slat and a 3/4" Baltic
    birch turned leg have identical rows, and only one of them is possible.

    Parameters
    ----------
    parts : iterable of CutPart
        Parts to check.
    inventory : Inventory, optional
        Used to recognise which materials are sheet goods.  When omitted, the
        material name is used instead — anything starting ``plywood``, ``mdf``,
        or ``particle``.

    Returns
    -------
    list[Finding]
        ``ERROR`` where the part cannot be made at all, ``WARN`` where it can
        be made but will not behave, ``INFO`` for a consequence worth knowing.
    """
    sheet_materials: set[str] = set()
    if inventory is not None:
        sheet_materials = {s.material for s in inventory.sheet_goods}

    def is_sheet(material: str) -> bool:
        if material in sheet_materials:
            return True
        return material.startswith(("plywood", "mdf", "particle"))

    findings: list[Finding] = []
    seen: set[tuple[str, str]] = set()
    for p in parts:
        key = (p.label, p.material)
        if p.shape == "rectangular" or key in seen:
            continue
        seen.add(key)

        if p.shape == "turned" and is_sheet(p.material):
            findings.append(
                Finding(
                    Severity.ERROR,
                    "material",
                    f"{p.label} is turned but specified in {p.material}: sheet "
                    "goods have no long grain running the length of a spindle, "
                    "so the alternating plies tear out at the skew and the "
                    "piece snaps at the first catch — turn it from solid stock",
                )
            )
        elif p.shape == "round" and is_sheet(p.material):
            findings.append(
                Finding(
                    Severity.WARN,
                    "material",
                    f"{p.label} is round and specified in {p.material}: the cut "
                    "exposes edge plies round the whole circumference, which "
                    "no edge banding follows cleanly — plan on a solid lipping "
                    "or accept a striped edge",
                )
            )
        elif p.shape == "shaped" and not is_sheet(p.material):
            findings.append(
                Finding(
                    Severity.INFO,
                    "material",
                    f"{p.label} is sawn to a curve in solid {p.material}: "
                    "wherever the curve runs across the grain the part is left "
                    "on short grain, which is where a leg breaks — lay the "
                    "blank out so the grain follows the sweep",
                )
            )
        elif p.shape == "round":
            findings.append(
                Finding(
                    Severity.INFO,
                    "material",
                    f"{p.label} ({p.profile or 'round'}) in solid "
                    f"{p.material}: it will move across the grain and not "
                    "along it, so it goes out of round with the seasons — "
                    "fix it down through slotted holes or buttons, never with "
                    "glue right across",
                )
            )
    return findings


# Tangential shrinkage, green to oven-dry, as a percentage of green width.
# USDA Wood Handbook table 4-3.  Tangential rather than radial because a
# flat-sawn board is what a glue-up is normally made of, and it is the larger
# of the two — the safe one to design to.
TANGENTIAL_SHRINKAGE_PCT: dict[str, float] = {
    "cherry": 7.1,
    "maple": 9.9,
    "walnut": 7.8,
    "white_oak": 10.5,
    "red_oak": 10.8,
    "pine": 7.4,
    "poplar": 8.2,
    "white_cedar": 4.9,
}

#: Moisture content at which wood starts to move, in percent.
#:
#: Above the fibre saturation point the cell walls are already full and only
#: the free water changes, so nothing moves.  Below it, movement is close
#: enough to linear for a shop estimate.
FIBRE_SATURATION_PCT: float = 30.0

#: Seasonal swing in moisture content to design to, in percentage points.
#:
#: Six points — roughly 6% in a heated winter to 12% in a damp summer — is the
#: usual figure for an interior piece in a temperate climate.  A house with no
#: humidity control swings further; a museum swings less.
DEFAULT_MC_SWING_PCT: float = 6.0


def check_wood_movement(
    species: str,
    width_mm: float,
    label: str = "panel",
    mc_swing_pct: float = DEFAULT_MC_SWING_PCT,
    allowance_mm: float | None = None,
) -> list[Finding]:
    """Estimate how far a solid panel moves across the grain, and against what.

    Sheet goods do not do this and solid wood always does, so the check exists
    for the moment a design mixes them: a plywood case does not move and a
    solid top on it moves every year of its life.  The number is what decides
    whether a joint has to allow for it or merely has to survive it.

    Parameters
    ----------
    species : str
        Species key, looked up in :data:`TANGENTIAL_SHRINKAGE_PCT`.
    width_mm : float
        Dimension **across the grain** — a top's depth, a panel's width.
        Movement along the grain is negligible and is not estimated.
    label : str, optional
        What the part is, for the message, default ``"panel"``.
    mc_swing_pct : float, optional
        Seasonal moisture-content swing in percentage points, default
        :data:`DEFAULT_MC_SWING_PCT`.
    allowance_mm : float, optional
        How much movement the construction actually permits.  Omit when the
        part is free to move — the finding is then the number and the rule that
        keeps it free.  Pass ``0.0`` to ask what a part glued or screwed across
        the grain is being asked to survive.

    Returns
    -------
    list[Finding]
        One finding: ``INFO`` when the part is free or the allowance covers the
        movement, ``WARN`` when it does not.  ``INFO`` if the species has no
        shrinkage figure.

    Notes
    -----
    A shop estimate, not a moisture model.  It assumes flat-sawn stock, linear
    movement below the fibre saturation point, and a species-average
    coefficient; real boards vary by a third either way.  It is meant to answer
    "is this a sixteenth or half an inch?", which is the question the joinery
    turns on.
    """
    shrinkage = TANGENTIAL_SHRINKAGE_PCT.get(species)
    if shrinkage is None:
        return [
            Finding(
                Severity.INFO,
                "movement",
                f"no shrinkage figure for {species!r}; {label} movement not "
                "estimated",
            )
        ]

    movement_mm = width_mm * (shrinkage / 100.0) * (mc_swing_pct / FIBRE_SATURATION_PCT)
    across = (
        f"{label}: {mm_to_fractional_inch(width_mm)} of {species} across the "
        f"grain moves about {mm_to_fractional_inch(movement_mm, 32)} "
        f"({movement_mm:.1f} mm) over a {mc_swing_pct:g}-point moisture swing"
    )

    if allowance_mm is None:
        return [
            Finding(
                Severity.INFO,
                "movement",
                f"{across} — it has to be held so that it can, which means no "
                "glue and no fixing across its width",
            )
        ]
    if movement_mm <= allowance_mm:
        return [
            Finding(
                Severity.INFO,
                "movement",
                f"{across}, inside the "
                f"{mm_to_fractional_inch(allowance_mm, 32)} the joint allows",
            )
        ]
    return [
        Finding(
            Severity.WARN,
            "movement",
            f"{across}, and the joint allows "
            f"{mm_to_fractional_inch(allowance_mm, 32)} — the difference does "
            "not disappear, it comes out as a split, a lifted joint, or a "
            "drawer that only opens in August",
        )
    ]


#: How long a price is treated as current, in days.
#:
#: Six months is a starting point rather than a considered figure.  Hardwood
#: moves faster than sheet goods, and the threshold probably wants to be
#: per-material once there is any real price history to judge it against.
STALE_AFTER_DAYS = 180


def check_price_provenance(
    inventory: "Inventory",
    parts: Iterable[CutPart] | None = None,
    today: date | None = None,
    stale_after_days: int = STALE_AFTER_DAYS,
) -> list[Finding]:
    """Report where each price used by a design came from, and when.

    Every other check in this module asks whether a design can be built.  This
    one asks whether its *cost* can be believed, which is a different question
    with the same failure mode: a number that is nearly right, printed in the
    same font as numbers that are exactly right.  Board feet are measured;
    dollars are quoted, and a quote has a date.

    Parameters
    ----------
    inventory : Inventory
        Stock inventory holding the prices and their provenance.
    parts : iterable of CutPart, optional
        The cut list, used to work out which stock the design actually buys.
        When omitted, every entry in the inventory is audited.
    today : datetime.date, optional
        The date to measure staleness against, default today.
    stale_after_days : int, optional
        How old a price may be before it is flagged, default
        :data:`STALE_AFTER_DAYS`.

    Returns
    -------
    list[Finding]
        ``ERROR`` for a price with no ``price_as_of`` — an unverified number
        that will otherwise be multiplied into a total that reads like a quote.
        ``WARN`` for a price older than *stale_after_days*, for a sale price
        whose ``price_valid_until`` has passed, and for a material the design
        uses that carries no price at all.  ``INFO`` for a price that is
        current, quoting its date, its source, and its sale end date if it has
        one.

    Notes
    -----
    Absence is reported as a ``WARN`` rather than an ``ERROR`` because an
    unpriced material makes a total incomplete, which the total says out loud;
    an undated price makes a total *wrong* while looking complete, which it
    cannot say on its own.
    """
    when = today or date.today()
    findings: list[Finding] = []

    for stock in _stock_used_by(inventory, parts):
        label = stock.stock_label
        if stock.price is None:
            findings.append(
                Finding(
                    Severity.WARN,
                    "price",
                    f"{label} has no price in stock.yaml — any total that "
                    "includes it is a total with a hole in it",
                )
            )
            continue

        source = stock.price_source or "no source recorded"
        if stock.price_as_of is None:
            findings.append(
                Finding(
                    Severity.ERROR,
                    "price",
                    f"{label} is priced per {stock.price_unit} but carries no "
                    f"price_as_of ({source}): treat it as invented until it is "
                    "replaced by a quote with a date on it",
                )
            )
            continue

        age = stock.price_age_days(when)
        quoted = f"quoted {stock.price_as_of.isoformat()}"
        if stock.price_has_expired(when):
            findings.append(
                Finding(
                    Severity.WARN,
                    "price",
                    f"{label} was a sale price that ended "
                    f"{stock.price_valid_until.isoformat()} ({source}): the "
                    "shelf price is not recorded, so this total is a total at "
                    "last month's discount",
                )
            )
        elif stock.price_is_a_special:
            findings.append(
                Finding(
                    Severity.INFO,
                    "price",
                    f"{label} priced per {stock.price_unit}, {quoted} — a sale "
                    f"price good to {stock.price_valid_until.isoformat()} "
                    f"({source}), not the shelf price",
                )
            )
        elif age is not None and age > stale_after_days:
            findings.append(
                Finding(
                    Severity.WARN,
                    "price",
                    f"{label} was {quoted} — {age} days ago, past the "
                    f"{stale_after_days}-day mark ({source}); lumber moves, so "
                    "re-quote before ordering",
                )
            )
        else:
            findings.append(
                Finding(
                    Severity.INFO,
                    "price",
                    f"{label} priced per {stock.price_unit}, {quoted} "
                    f"({source})",
                )
            )
    return findings


def _stock_used_by(
    inventory: "Inventory",
    parts: Iterable[CutPart] | None,
) -> list["PricedStock"]:
    """Return the inventory entries a cut list buys from, without duplicates.

    Pricing a design means pricing the stock it *lands on*, which is not the
    same as every entry of that material: a 3/4" part comes off 4/4 boards and
    a 62-1/2" slat comes off the 4x8 sheet, and the entries it does not touch
    have nothing to say about its cost.

    Entries come back in label order rather than cut-list order, so the report
    reads as a list of materials rather than as a trace of the parts loop.
    """
    if parts is None:
        return list(inventory.all_stock())

    sheet_materials = {s.material for s in inventory.sheet_goods}
    hardwood_species = {h.species for h in inventory.hardwood}
    seen: list["PricedStock"] = []

    def remember(entry: "PricedStock") -> None:
        if not any(entry is other for other in seen):
            seen.append(entry)

    for p in parts:
        if p.material in sheet_materials:
            remember(
                inventory.best_sheet_for(
                    p.material,
                    length_mm=p.length_mm,
                    width_mm=p.width_mm,
                    part_grain=p.grain_direction,
                    thickness_mm=p.thickness_mm,
                )
            )
            continue
        if p.material in hardwood_species:
            board = _hardwood_for_part(inventory, p)
            if board is not None:
                remember(board)
            continue
        # Dimensional stock is not thickness-matched: a pine part could be cut
        # from any nominal size the shop stocks, so every entry in the species
        # is in scope.
        for d in inventory.dimensional:
            if d.species == p.material:
                remember(d)
    return sorted(seen, key=lambda entry: entry.stock_label)


def _hardwood_for_part(inventory: "Inventory", part: CutPart) -> "PricedStock | None":
    """Return the thinnest stocked quarter that surfaces to *part*'s thickness.

    Mirrors the rule :func:`woodshop.cutlist.hardwood.nest_hardwood` buys by,
    so the price checked is the price charged.  ``None`` when the part is
    thicker than anything stocked — the cut list reports that on its own.
    """
    usable = [
        h
        for h in inventory.hardwood
        if h.species == part.material
        and h.surfaced_thickness_mm >= part.thickness_mm - 0.1
    ]
    if not usable:
        return None
    return min(usable, key=lambda h: h.surfaced_thickness_mm)


def check_tip_resistance(
    mass_kg: float,
    n_legs: int,
    foot_radius_mm: float,
    overhang_radius_mm: float,
    min_tip_load_kg: float = 10.0,
) -> list[Finding]:
    """Estimate the load at the rim that tips a piece on splayed legs over.

    A table on ``n`` equally spaced legs stands on a polygon, not a circle.
    The nearest edge of that polygon is at ``foot_radius * cos(pi / n)`` from
    the centre — for a tripod that is only *half* the foot radius, which is why
    three legs are so much tippier than four for the same footprint.

    Parameters
    ----------
    mass_kg : float
        Mass of the piece.  :func:`estimate_mass_kg` will produce one from a
        cut list.
    n_legs : int
        Number of legs, equally spaced.
    foot_radius_mm : float
        Distance from the centre line to the middle of a foot.
    overhang_radius_mm : float
        Distance from the centre line to where a load might be put — normally
        the rim of the top.
    min_tip_load_kg : float, optional
        Load the piece should carry at the rim without going over, default
        10 kg (22 lb) — roughly someone leaning a hand on the edge.

    Returns
    -------
    list[Finding]
        One finding: ``INFO`` if it holds, ``WARN`` with the tipping load if
        it does not.

    Raises
    ------
    ValueError
        If *n_legs* is below 3, which is not a thing that stands up.

    Notes
    -----
    Static, and it assumes the centre of mass is on the axis and the feet do
    not slide.  It compares moments about the tipping edge, so the answer is
    the *vertical* load at the rim; a sideways shove tips it sooner.
    """
    if n_legs < 3:
        raise ValueError(f"a piece needs at least 3 legs to stand, got {n_legs}")

    tipping_radius = foot_radius_mm * math.cos(math.pi / n_legs)
    if overhang_radius_mm <= tipping_radius:
        return [
            Finding(
                Severity.INFO,
                "stability",
                f"the top does not overhang the {n_legs}-leg stance "
                f"({mm_to_fractional_inch(overhang_radius_mm)} rim vs "
                f"{mm_to_fractional_inch(tipping_radius)} to the tipping edge)"
                " — a load anywhere on it cannot tip the piece",
            )
        ]

    lever = overhang_radius_mm - tipping_radius
    tip_load_kg = mass_kg * tipping_radius / lever
    message = (
        f"{mass_kg:.1f} kg on {n_legs} legs: a load of {tip_load_kg:.1f} kg "
        f"({tip_load_kg * 2.2046:.0f} lb) on the rim between two legs tips it "
        f"(rim {mm_to_fractional_inch(overhang_radius_mm)}, tipping edge "
        f"{mm_to_fractional_inch(tipping_radius)} from centre)"
    )
    if tip_load_kg >= min_tip_load_kg:
        return [Finding(Severity.INFO, "stability", message)]
    return [
        Finding(
            Severity.WARN,
            "stability",
            f"{message} — under the {min_tip_load_kg:g} kg it should hold. "
            "Splaying the legs further is the only fix that does not change "
            "the top",
        )
    ]


def alternative_sheets(
    inventory: "Inventory",
    length_mm: float,
    width_mm: float,
    grain_direction: str = "none",
    exclude_material: str | None = None,
    max_thickness_delta_mm: float = 1.6,
    reference_thickness_mm: float | None = None,
) -> list[str]:
    """Return stocked sheet materials that would take a part whole.

    Useful when a part does not fit the material it was specified in: the shop
    may already stock something the same thickness in a bigger sheet.

    Parameters
    ----------
    inventory : Inventory
        Stock inventory to search.
    length_mm, width_mm : float
        Part dimensions.
    grain_direction : str, optional
        The part's grain direction, default ``"none"``.
    exclude_material : str, optional
        Material to leave out — normally the one that did not fit.
    max_thickness_delta_mm : float, optional
        How far from *reference_thickness_mm* a substitute may be, default
        1.6 mm (1/16").
    reference_thickness_mm : float, optional
        Thickness to match.  If omitted, thickness is not considered.

    Returns
    -------
    list[str]
        Descriptions such as ``'plywood_birch 3/4" (48" x 96")'``.
    """
    out: list[str] = []
    for s in inventory.sheet_goods:
        if s.material == exclude_material:
            continue
        if reference_thickness_mm is not None:
            if abs(s.thickness_mm - reference_thickness_mm) > max_thickness_delta_mm:
                continue
        if s.fits(length_mm, width_mm, grain_direction):
            out.append(
                f'{s.material} {s.nominal_thickness}" '
                f'({s.sheet_width_in:g}" x {s.sheet_height_in:g}")'
            )
    return out
