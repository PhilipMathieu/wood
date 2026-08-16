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

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Iterable

from woodshop.cutlist.extract import CutPart
from woodshop.lumber import mm_to_fractional_inch

if TYPE_CHECKING:
    from woodshop.inventory import Inventory

__all__ = [
    "Severity",
    "Finding",
    "CheckReport",
    "ELASTIC_MODULUS_MPA",
    "check_envelope",
    "check_sheet_fit",
    "check_thickness_substitution",
    "check_slat_deflection",
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

    Returns
    -------
    list[Finding]
        A single finding: ``INFO`` inside the band, ``WARN`` outside it.
    """
    text = f"{name} is {mm_to_fractional_inch(clearance_mm)}"
    if clearance_mm < min_mm:
        return [Finding(Severity.WARN, "clearance", f"{text} — tight, mattress may bind")]
    if clearance_mm > max_mm:
        return [
            Finding(
                Severity.WARN,
                "clearance",
                f"{text} — loose, mattress will slide and expose the rail",
            )
        ]
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
        candidates = [s for s in inventory.sheet_goods if s.material == p.material]
        sheet = min(candidates, key=lambda s: abs(s.thickness_mm - p.thickness_mm))
        rotatable = sheet.grain == "none" or p.grain_direction == "none"
        if sheet.fits(p.length_mm, p.width_mm, p.grain_direction):
            findings.append(
                Finding(
                    Severity.INFO,
                    "sheet_fit",
                    f"{p.label} ({mm_to_fractional_inch(p.length_mm)} x "
                    f"{mm_to_fractional_inch(p.width_mm)}) fits "
                    f"{p.material} {sheet.sheet_width_in:g}x{sheet.sheet_height_in:g}",
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
                    f"{mm_to_fractional_inch(p.width_mm)} but {p.material} comes in "
                    f"{sheet.sheet_width_in:g}\" x {sheet.sheet_height_in:g}\" sheets"
                    f"{grain_note} — it cannot be cut from one piece",
                )
            )
    return findings


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

    # Uniformly distributed load per slat, N/mm.
    load_n = design_load_kg * 9.80665 / n_slats
    w = load_n / span_mm
    # Second moment of area of a rectangle bending about its weak axis.
    i_mm4 = slat_width_mm * slat_thickness_mm**3 / 12.0
    # Midspan deflection of a simply-supported beam under a UDL.
    deflection_mm = 5.0 * w * span_mm**4 / (384.0 * e_mpa * i_mm4)
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
