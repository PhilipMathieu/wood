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
#
# These are *dressed* dimensions. Rough sawn stock is close to its nominal
# size — a rough 1x6 cedar board is about a full 1" x 6" — so an entry whose
# `profile` says "rough sawn" is not described by this table. See
# `rough_dimensions_mm`, which is the one a rough-sawn fence is laid out with.
_NOMINAL_TO_ACTUAL_IN: dict[str, tuple[float, float]] = {
    # fmt: off
    "1x2":  (0.75,  1.5),
    "1x3":  (0.75,  2.5),
    "1x4":  (0.75,  3.5),
    "1x6":  (0.75,  5.5),
    "1x8":  (0.75,  7.25),
    "1x10": (0.75,  9.25),
    "1x12": (0.75, 11.25),
    # 5/4 stock dresses to a full inch, which is why decking is sold in it.
    "5/4x3": (1.0,  2.5),
    "5/4x4": (1.0,  3.5),
    "5/4x6": (1.0,  5.5),
    "2x2":  (1.5,   1.5),
    "2x3":  (1.5,   2.5),
    "2x4":  (1.5,   3.5),
    "2x6":  (1.5,   5.5),
    "2x8":  (1.5,   7.25),
    "2x10": (1.5,   9.25),
    "2x12": (1.5,  11.25),
    "4x4":  (3.5,   3.5),
    "4x6":  (3.5,   5.5),
    "6x6":  (5.5,   5.5),
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


def rough_dimensions_mm(nominal: str) -> tuple[Q_, Q_]:
    """Return (thickness, width) in mm for *rough sawn* stock of a nominal size.

    Rough sawn lumber comes off the saw at very close to its nominal size and
    is sold that way: a rough 1x6 is about a full 1" x 6", where the dressed
    board of the same name measures 3/4" x 5-1/2".  Half of Lumbery's cedar
    list is rough sawn, and a fence laid out from the dressed table would be
    3/8" short in every bay and 1/4" thin in every board.

    Parameters
    ----------
    nominal : str
        Nominal size string, e.g. ``"1x6"``, ``"5/4x6"``, ``"4x4"``.  A
        quarter thickness before the ``x`` is read as a fraction, so ``5/4x6``
        is 1-1/4" x 6".

    Returns
    -------
    tuple[pint.Quantity, pint.Quantity]
        Thickness and width in mm.

    Raises
    ------
    ValueError
        If *nominal* is not two dimensions separated by an ``x``.

    Notes
    -----
    "Close to full dimension" is not "full dimension": a rough board varies
    across its length and between mills, and the thickness is the number that
    varies most.  These are the sizes to *design* to — a rail that has to
    land between two posts wants the width measured on the pile before
    anything is cut.

    Examples
    --------
    >>> t, w = rough_dimensions_mm("1x6")
    >>> round(t.magnitude, 1), round(w.magnitude, 1)
    (25.4, 152.4)
    >>> t, w = rough_dimensions_mm("5/4x6")
    >>> round(t.magnitude, 2)
    31.75
    """
    parts = nominal.lower().split("x")
    if len(parts) != 2:
        raise ValueError(
            f"{nominal!r} is not a nominal size of the form '1x6' or '5/4x6'"
        )
    return tuple(Q_(_parse_nominal_dimension(p, nominal), "inch").to("mm") for p in parts)


def _parse_nominal_dimension(text: str, nominal: str) -> float:
    """Parse one side of a nominal size, e.g. ``'5/4'`` or ``'6'``, in inches."""
    text = text.strip()
    try:
        if "/" in text:
            num, den = text.split("/")
            return float(num) / float(den)
        return float(text)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{nominal!r} is not a nominal size of the form '1x6' or '5/4x6'"
        ) from exc


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
