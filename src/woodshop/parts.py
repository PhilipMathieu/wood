"""Board and Panel — build123d solids that carry cut-list metadata.

Every part in an assembly is a :class:`Board` (dimensional / milled solid stock)
or a :class:`Panel` (sheet goods).  Both are ordinary build123d part objects, so
they can be positioned, unioned, and cut like any other solid — but they also
record the information a cut list needs and that geometry alone cannot recover:
the species, the grain direction, and the *stock* size before joinery removes
material.

Local part frame convention
---------------------------
A part is created with

* **length** along +X — always along the grain for ``grain_direction="length"``
* **width** along +Y
* **thickness** along +Z

Once the part is rotated into place in an assembly its bounding box no longer
reports those three numbers in that order, which is why the cut dimensions are
stored as attributes rather than measured back off the solid.

Example
-------
>>> from woodshop.parts import Board, Panel
>>> post = Board(length_mm=1016.0, nominal="2x2", material="cherry", label="head_post")
>>> post.thickness_mm, post.width_mm
(38.1, 38.1)
>>> shelf = Panel(length_mm=600.0, width_mm=300.0, nominal_thickness="3/4",
...               material="plywood_birch", label="shelf")
>>> round(shelf.thickness_mm, 3)
18.256
"""

from __future__ import annotations

from typing import Any, Iterable

from build123d import Align, Box, Mode, RotationLike

from woodshop.lumber import actual_dimensions_mm, plywood_thickness_mm

__all__ = ["Board", "Panel", "StockPart"]

#: Grain directions a part may declare.
GRAIN_DIRECTIONS: frozenset[str] = frozenset({"length", "width", "none"})


class StockPart(Box):
    """Base class for parts that appear on a cut list.

    Not usually instantiated directly — use :class:`Board` or :class:`Panel`.

    Parameters
    ----------
    length_mm : float
        Finished length along +X (along the grain when ``grain_direction`` is
        ``"length"``).
    width_mm : float
        Finished width along +Y.
    thickness_mm : float
        Finished thickness along +Z.
    material : str
        Species or sheet-goods material key, e.g. ``"cherry"``,
        ``"plywood_baltic_birch"``.
    label : str
        Human-readable part name.  Identical parts should share a label so the
        cut list can consolidate them into a single row with a quantity.
    grain_direction : str, optional
        ``"length"`` (default), ``"width"``, or ``"none"``.
    qty : int, optional
        How many identical parts this object stands for.  Use this when the
        assembly only models one representative of a repeated part; leave it at
        ``1`` when every copy is placed in the model.
    stock_length_mm : float, optional
        Length of stock to cut before joinery.  Defaults to
        ``length_mm + trim_allowance_mm``.
    trim_allowance_mm : float, optional
        Extra length added to the cut, e.g. for squaring ends or snipe.
        Default ``0.0``.
    notes : str, optional
        Free-text note carried through to the cut list.
    rotation : RotationLike, optional
        Passed through to :class:`build123d.Box`.
    align : Align or tuple, optional
        Passed through to :class:`build123d.Box`.  Defaults to centred.
    mode : build123d.Mode, optional
        Passed through to :class:`build123d.Box`, default ``Mode.ADD``.

    Raises
    ------
    ValueError
        If any dimension is non-positive, ``qty`` is below 1, or
        ``grain_direction`` is not one of :data:`GRAIN_DIRECTIONS`.
    """

    def __init__(
        self,
        length_mm: float,
        width_mm: float,
        thickness_mm: float,
        *,
        material: str,
        label: str,
        grain_direction: str = "length",
        qty: int = 1,
        stock_length_mm: float | None = None,
        trim_allowance_mm: float = 0.0,
        notes: str = "",
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] = (
            Align.CENTER,
            Align.CENTER,
            Align.CENTER,
        ),
        mode: Mode = Mode.ADD,
    ) -> None:
        for name, value in (
            ("length_mm", length_mm),
            ("width_mm", width_mm),
            ("thickness_mm", thickness_mm),
        ):
            if value <= 0:
                raise ValueError(f"{label!r}: {name} must be positive, got {value!r}")
        if qty < 1:
            raise ValueError(f"{label!r}: qty must be at least 1, got {qty!r}")
        if grain_direction not in GRAIN_DIRECTIONS:
            raise ValueError(
                f"{label!r}: grain_direction must be one of "
                f"{sorted(GRAIN_DIRECTIONS)}, got {grain_direction!r}"
            )

        super().__init__(
            length=length_mm,
            width=width_mm,
            height=thickness_mm,
            rotation=rotation,
            align=align,
            mode=mode,
        )

        self.label = label
        self.material = material
        self.grain_direction = grain_direction
        self.qty = qty
        self.length_mm = float(length_mm)
        self.width_mm = float(width_mm)
        self.thickness_mm = float(thickness_mm)
        self.trim_allowance_mm = float(trim_allowance_mm)
        self.stock_length_mm = (
            float(stock_length_mm)
            if stock_length_mm is not None
            else float(length_mm) + float(trim_allowance_mm)
        )
        self.notes = notes

    # ------------------------------------------------------------------
    # Derived quantities
    # ------------------------------------------------------------------

    @property
    def board_feet(self) -> float:
        """Board feet of stock for all ``qty`` copies (1 bd ft = 144 in³)."""
        mm3 = self.stock_length_mm * self.width_mm * self.thickness_mm * self.qty
        return mm3 / (25.4**3) / 144.0

    @property
    def area_m2(self) -> float:
        """Face area in square metres for all ``qty`` copies."""
        return self.stock_length_mm * self.width_mm * self.qty / 1_000_000.0

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        """Return a short description including the cut dimensions."""
        return (
            f"{type(self).__name__}({self.label!r}, {self.material}, "
            f"{self.stock_length_mm:.1f}x{self.width_mm:.1f}x"
            f"{self.thickness_mm:.1f}mm, qty={self.qty})"
        )


class Board(StockPart):
    """A part cut from solid (dimensional or milled) stock.

    Either give a ``nominal`` size such as ``"2x4"`` — thickness and width are
    then looked up in :mod:`woodshop.lumber` — or give ``thickness_mm`` and
    ``width_mm`` explicitly for milled-to-size hardwood.

    Parameters
    ----------
    length_mm : float
        Finished length along the grain.
    material : str
        Species, e.g. ``"cherry"``.
    label : str
        Part name.
    nominal : str, optional
        Nominal lumber size, e.g. ``"1x6"``.  Mutually exclusive with
        ``thickness_mm`` / ``width_mm``.
    thickness_mm : float, optional
        Finished thickness.  Required when ``nominal`` is not given.
    width_mm : float, optional
        Finished width.  Required when ``nominal`` is not given.
    **kwargs
        Forwarded to :class:`StockPart` (``qty``, ``grain_direction``,
        ``trim_allowance_mm``, ``rotation``, ``align``, ``mode``, ``notes``).

    Raises
    ------
    ValueError
        If ``nominal`` is combined with explicit dimensions, or if neither is
        supplied.

    Examples
    --------
    >>> rail = Board(length_mm=2000.0, nominal="1x6", material="pine", label="rail")
    >>> rail.width_mm
    139.7
    """

    def __init__(
        self,
        length_mm: float,
        *,
        material: str,
        label: str,
        nominal: str | None = None,
        thickness_mm: float | None = None,
        width_mm: float | None = None,
        **kwargs: Any,
    ) -> None:
        if nominal is not None:
            if thickness_mm is not None or width_mm is not None:
                raise ValueError(
                    f"{label!r}: pass either nominal= or thickness_mm=/width_mm=, "
                    "not both"
                )
            thickness_q, width_q = actual_dimensions_mm(nominal)
            thickness_mm = float(thickness_q.magnitude)
            width_mm = float(width_q.magnitude)
        elif thickness_mm is None or width_mm is None:
            raise ValueError(
                f"{label!r}: give nominal=, or both thickness_mm= and width_mm="
            )

        super().__init__(
            length_mm=length_mm,
            width_mm=width_mm,
            thickness_mm=thickness_mm,
            material=material,
            label=label,
            **kwargs,
        )
        self.nominal = nominal


class Panel(StockPart):
    """A part cut from sheet goods.

    Parameters
    ----------
    length_mm : float
        Finished length along +X (along the face grain when
        ``grain_direction`` is ``"length"``).
    width_mm : float
        Finished width along +Y.
    material : str
        Sheet-goods material key, e.g. ``"plywood_cherry"``.
    label : str
        Part name.
    nominal_thickness : str, optional
        Nominal thickness such as ``"3/4"``, looked up in
        :mod:`woodshop.lumber`.  Mutually exclusive with ``thickness_mm``.
    thickness_mm : float, optional
        Actual thickness.  Use this for metric sheet goods such as Baltic
        birch, whose 18 mm is *not* 3/4".
    **kwargs
        Forwarded to :class:`StockPart`.

    Raises
    ------
    ValueError
        If both or neither of ``nominal_thickness`` and ``thickness_mm`` are
        given.

    Notes
    -----
    ``grain_direction="length"`` means the face grain runs along ``length_mm``
    and the nesting optimiser may not rotate the part 90°.  Use ``"none"`` for
    parts where face-grain direction does not matter (most Baltic birch
    utility parts).
    """

    def __init__(
        self,
        length_mm: float,
        width_mm: float,
        *,
        material: str,
        label: str,
        nominal_thickness: str | None = None,
        thickness_mm: float | None = None,
        **kwargs: Any,
    ) -> None:
        if (nominal_thickness is None) == (thickness_mm is None):
            raise ValueError(
                f"{label!r}: give exactly one of nominal_thickness= or thickness_mm="
            )
        if nominal_thickness is not None:
            thickness_mm = float(plywood_thickness_mm(nominal_thickness).magnitude)

        super().__init__(
            length_mm=length_mm,
            width_mm=width_mm,
            thickness_mm=thickness_mm,
            material=material,
            label=label,
            **kwargs,
        )
        self.nominal_thickness = nominal_thickness


def total_board_feet(parts: Iterable[StockPart]) -> float:
    """Sum :attr:`StockPart.board_feet` over *parts*.

    Parameters
    ----------
    parts : iterable of StockPart
        Parts to total.

    Returns
    -------
    float
        Total board feet, quantities included.
    """
    return sum(p.board_feet for p in parts)
