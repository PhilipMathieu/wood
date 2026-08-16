"""Nominal-to-actual dimension tables for common lumber, backed by Pint units.

All internal geometry is in mm. Use the conversion helpers at module boundaries.
"""

from __future__ import annotations

from typing import Final

from pint import UnitRegistry

ureg: Final = UnitRegistry()
Q_ = ureg.Quantity

# ---------------------------------------------------------------------------
# Kerf
# ---------------------------------------------------------------------------

#: Default saw kerf in mm (1/8").
KERF_MM: Final[float] = 3.175

# ---------------------------------------------------------------------------
# Nominal → actual dimension tables
# ---------------------------------------------------------------------------

# Mapping of nominal size string → (thickness_in, width_in) as fractions of inches.
# Covers the most common dimensional lumber sizes.
_NOMINAL_TO_ACTUAL_IN: dict[str, tuple[float, float]] = {
    # fmt: off
    "1x2":  (0.75,  1.5),
    "1x3":  (0.75,  2.5),
    "1x4":  (0.75,  3.5),
    "1x6":  (0.75,  5.5),
    "1x8":  (0.75,  7.25),
    "1x10": (0.75,  9.25),
    "1x12": (0.75, 11.25),
    "2x2":  (1.5,   1.5),
    "2x3":  (1.5,   2.5),
    "2x4":  (1.5,   3.5),
    "2x6":  (1.5,   5.5),
    "2x8":  (1.5,   7.25),
    "2x10": (1.5,   9.25),
    "2x12": (1.5,  11.25),
    "4x4":  (3.5,   3.5),
    "4x6":  (3.5,   5.5),
    # fmt: on
}

# Plywood nominal thickness → actual thickness in inches.
_PLYWOOD_ACTUAL_IN: dict[str, float] = {
    "1/4":  0.234375,   # 15/64"
    "3/8":  0.359375,   # 23/64"
    "1/2":  0.46875,    # 15/32"
    "5/8":  0.59375,    # 19/32"
    "3/4":  0.71875,    # 23/32"
    "1":    0.96875,    # 31/32"
}


def actual_dimensions_mm(nominal: str) -> tuple[Q_, Q_]:
    """Return (thickness, width) as Pint quantities in mm for a nominal lumber size.

    Parameters
    ----------
    nominal : str
        Nominal size string, e.g. ``"2x4"``, ``"1x6"``.

    Returns
    -------
    thickness : pint.Quantity
        Actual thickness in mm.
    width : pint.Quantity
        Actual width in mm.

    Raises
    ------
    KeyError
        If *nominal* is not in the lookup table.
    """
    t_in, w_in = _NOMINAL_TO_ACTUAL_IN[nominal]
    return (
        Q_(t_in, "inch").to("mm"),
        Q_(w_in, "inch").to("mm"),
    )


def plywood_thickness_mm(nominal: str) -> Q_:
    """Return actual plywood thickness as a Pint quantity in mm.

    Parameters
    ----------
    nominal : str
        Nominal thickness string, e.g. ``"3/4"``, ``"1/2"``.

    Returns
    -------
    pint.Quantity
        Actual thickness in mm.

    Raises
    ------
    KeyError
        If *nominal* is not in the lookup table.
    """
    return Q_(_PLYWOOD_ACTUAL_IN[nominal], "inch").to("mm")


def mm_to_fractional_inch(value_mm: float, denominator: int = 16) -> str:
    """Convert a millimetre value to a fractional-inch string (nearest 1/16").

    Parameters
    ----------
    value_mm : float
        Length in millimetres.
    denominator : int, optional
        Fraction denominator, default 16.

    Returns
    -------
    str
        Human-readable fractional-inch string, e.g. ``'3-1/4"'``.
    """
    total_sixteenths = round(value_mm / 25.4 * denominator)
    whole = total_sixteenths // denominator
    remainder = total_sixteenths % denominator

    if remainder == 0:
        return f'{whole}"'

    # Simplify fraction
    from math import gcd

    g = gcd(remainder, denominator)
    num = remainder // g
    den = denominator // g

    if whole == 0:
        return f'{num}/{den}"'
    return f'{whole}-{num}/{den}"'
