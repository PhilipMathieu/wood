"""Parts that carry cut-list metadata: Board, Panel, Disc, and Turning.

Every part in an assembly is an ordinary build123d solid — it can be
positioned, unioned, and cut like any other — but it also records the
information a cut list needs and that geometry alone cannot recover: the
species, the grain direction, and the *stock* size before the saw and the
lathe take material away.

Five kinds of part, because they are bought and cut in genuinely different
ways:

``Board``
    Solid stock, rectangular.  Dimensional (``nominal="2x4"``) or milled to
    size from rough hardwood.

``Panel``
    Sheet goods, rectangular.

``Disc``
    A round part faceplate-turned or bandsawn out of a square blank — a table
    top, a seat, a lid.  Optionally a frustum, for an edge angled inward.

``Turning``
    A spindle turned between centres out of a square blank — a leg, a stretcher,
    a knob.  Optionally tapered.

``ShapedBoard``
    A flat part sawn to a profile rather than to a rectangle — a bandsawn leg,
    a curved rail, a crested headboard.

``Pole``
    Round stock that is *bought* round — a peeled cedar fence post, a rail, a
    dowel.  The distinction from :class:`Turning` is the whole point: a spindle
    is a square you turn most of away, and a log is a log.

Stock size versus finished size
-------------------------------
A round part is the clearest case of a distinction that applies to everything:
you cannot buy an 18" circle, you buy an 18-1/4" square and turn most of it
into shavings.  Every part therefore carries both

* ``length_mm`` / ``width_mm`` / ``thickness_mm`` — the **finished** part, and
* ``stock_length_mm`` / ``stock_width_mm`` / ``stock_thickness_mm`` — the
  **blank** you cut from a board.

For a rectangular part the two coincide apart from any trim allowance.  For a
:class:`Disc` or a :class:`Turning` they differ, and it is the blank that goes
on the cut list, because the blank is what you buy.

Local part frame convention
---------------------------
A rectangular part is created with

* **length** along +X — always along the grain for ``grain_direction="length"``
* **width** along +Y
* **thickness** along +Z

A round part is created about the **lathe axis, which runs along +Z**.  A
:class:`Disc` therefore lies flat, thickness along +Z, exactly as a Board does;
a :class:`Turning` stands upright on its axis, which is what a leg does anyway.
A :class:`ShapedBoard` carries its profile in the X-Y plane and its thickness
along +Z, so it lies flat like a Board too.

Once a part is rotated into place in an assembly its bounding box no longer
reports those numbers in that order, which is why the cut dimensions are stored
as attributes rather than measured back off the solid.

Example
-------
>>> from woodshop.parts import Board, Disc, Panel, Turning
>>> post = Board(length_mm=1016.0, nominal="2x2", material="cherry", label="head_post")
>>> round(post.thickness_mm, 3), round(post.width_mm, 3)
(38.1, 38.1)
>>> shelf = Panel(length_mm=600.0, width_mm=300.0, nominal_thickness="3/4",
...               material="plywood_birch", label="shelf")
>>> round(shelf.thickness_mm, 3)
18.256
>>> top = Disc(diameter_mm=457.2, thickness_mm=38.1, material="cherry", label="top")
>>> round(top.stock_length_mm, 2)          # an 18" disc needs an 18-1/4" square
463.55
"""

from __future__ import annotations

import math
from typing import Any, Iterable, Sequence

from build123d import (
    Align,
    BasePartObject,
    Box,
    BuildPart,
    Mode,
    Polyline,
    RotationLike,
    Solid,
    extrude,
    make_face,
    tuplify,
    validate_inputs,
)

from woodshop.lumber import (
    actual_dimensions_mm,
    mm_to_fractional_inch,
    plywood_thickness_mm,
    rough_dimensions_mm,
)

__all__ = [
    "Board",
    "Panel",
    "Disc",
    "Turning",
    "Pole",
    "StockPart",
    "ShapedPart",
    "ShapedBoard",
    "retag",
    "total_board_feet",
]

#: Grain directions a part may declare.
GRAIN_DIRECTIONS: frozenset[str] = frozenset({"length", "width", "none"})

#: Shapes a part may take.  Drives blank sizing, yield, and material checks.
#:
#: ``"pole"`` is round stock bought round, as against ``"turned"``, which is
#: round stock made by removing a square's corners.  They look identical in a
#: drawing and could not be less alike on an order: one is a line item in
#: lineal feet, the other is a blank and a lathe.
SHAPES: frozenset[str] = frozenset(
    {"rectangular", "round", "turned", "shaped", "pole"}
)

#: Extra width and length left round a round blank, in mm (1/4" total).
#:
#: A disc is centred on its blank by eye or by a compass, and the bandsaw
#: cut wanders.  Cutting the blank exactly to the finished diameter leaves no
#: room for either.
ROUND_BLANK_MARGIN_MM: float = 6.35

#: Extra length on a spindle blank, in mm (1" total).
#:
#: A spindle is driven between centres, and the few inches at each end that
#: the drive centre and the tailstock occupy are turned away or parted off.
TURNING_WASTE_MM: float = 25.4


class _StockMeta:
    """Cut-list metadata shared by every part, whatever shape it is.

    Mixed in ahead of the build123d solid class so that ``Board`` and ``Disc``
    answer the same questions despite being a box and a cone.  It deliberately
    defines no ``__init__``: the concrete part class builds its solid through
    ``super().__init__`` and then calls :meth:`_record`.
    """

    #: One of :data:`SHAPES`.  Overridden by shaped subclasses.
    shape: str = "rectangular"

    #: Nominal size the part is cut from, e.g. ``"1x6"``.  Empty for stock
    #: milled to size out of rough hardwood, which has no nominal size.
    nominal: str = ""

    #: Grade as the supplier names it, e.g. ``"STK"``.  Empty when the design
    #: does not care which grade it lands on.
    grade: str = ""

    #: How the stock is worked — ``"rough sawn"``, ``"dressed"``.  With
    #: :attr:`grade`, this is what tells two inventory entries of the same
    #: nominal size and very different prices apart.
    stock_profile: str = ""

    #: What the stock measures across its face.  Differs from the part's
    #: width only for milled stock, where part of the face is a tongue hidden
    #: in the next board.  ``0.0`` until a part sets it.
    face_width_mm: float = 0.0

    def _record(
        self,
        *,
        label: str,
        material: str,
        grain_direction: str,
        qty: int,
        notes: str,
        length_mm: float,
        width_mm: float,
        thickness_mm: float,
        stock_length_mm: float,
        stock_width_mm: float,
        stock_thickness_mm: float,
        finished_area_mm2: float,
        profile: str = "",
        trim_allowance_mm: float = 0.0,
    ) -> None:
        """Attach cut-list metadata to a freshly built solid."""
        if qty < 1:
            raise ValueError(f"{label!r}: qty must be at least 1, got {qty!r}")
        if grain_direction not in GRAIN_DIRECTIONS:
            raise ValueError(
                f"{label!r}: grain_direction must be one of "
                f"{sorted(GRAIN_DIRECTIONS)}, got {grain_direction!r}"
            )
        self.label = label
        self.material = material
        self.grain_direction = grain_direction
        self.qty = qty
        self.notes = notes
        self.length_mm = float(length_mm)
        self.width_mm = float(width_mm)
        self.thickness_mm = float(thickness_mm)
        self.stock_length_mm = float(stock_length_mm)
        self.stock_width_mm = float(stock_width_mm)
        self.stock_thickness_mm = float(stock_thickness_mm)
        self.finished_area_mm2 = float(finished_area_mm2)
        self.profile = profile
        self.trim_allowance_mm = float(trim_allowance_mm)

    # ------------------------------------------------------------------
    # Derived quantities
    # ------------------------------------------------------------------

    @property
    def board_feet(self) -> float:
        """Board feet of *stock* for all ``qty`` copies (1 bd ft = 144 in³).

        Blank dimensions, not finished ones — a round top is billed as the
        square it was cut from.
        """
        mm3 = (
            self.stock_length_mm
            * self.stock_width_mm
            * self.stock_thickness_mm
            * self.qty
        )
        return mm3 / (25.4**3) / 144.0

    @property
    def area_m2(self) -> float:
        """Blank face area in square metres for all ``qty`` copies."""
        return self.stock_length_mm * self.stock_width_mm * self.qty / 1_000_000.0

    @property
    def shape_yield(self) -> float:
        """Fraction of the blank's face area the finished part occupies (0-1).

        ``1.0`` for a rectangle; about ``0.79`` for a disc, which is the price
        of a circle.
        """
        blank = self.stock_length_mm * self.stock_width_mm
        return 0.0 if blank == 0 else self.finished_area_mm2 / blank

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        """Return a short description including the blank dimensions."""
        return (
            f"{type(self).__name__}({self.label!r}, {self.material}, "
            f"blank {self.stock_length_mm:.1f}x{self.stock_width_mm:.1f}x"
            f"{self.stock_thickness_mm:.1f}mm, qty={self.qty})"
        )


class StockPart(_StockMeta, Box):
    """Base class for rectangular parts that appear on a cut list.

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

    shape = "rectangular"

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

        super().__init__(
            length=length_mm,
            width=width_mm,
            height=thickness_mm,
            rotation=rotation,
            align=align,
            mode=mode,
        )

        blank_length = (
            float(stock_length_mm)
            if stock_length_mm is not None
            else float(length_mm) + float(trim_allowance_mm)
        )
        self._record(
            label=label,
            material=material,
            grain_direction=grain_direction,
            qty=qty,
            notes=notes,
            length_mm=length_mm,
            width_mm=width_mm,
            thickness_mm=thickness_mm,
            stock_length_mm=blank_length,
            stock_width_mm=width_mm,
            stock_thickness_mm=thickness_mm,
            finished_area_mm2=float(length_mm) * float(width_mm),
            trim_allowance_mm=trim_allowance_mm,
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
    rough : bool, optional
        Size the part from the *rough sawn* table rather than the dressed one:
        a rough 1x6 is about a full 1" x 6" where the dressed board of that
        name is 3/4" x 5-1/2".  Only meaningful with ``nominal``.
    covers_mm : float, optional
        What one board *covers* when it is butted to its neighbour, for milled
        stock where that is less than what it measures.  A 1x6 tongue and
        groove board is 5-1/2" wide and shows about 5-1/8": the rest is the
        tongue, and it lives inside the next board.  The part is modelled and
        laid out at the covering width — a solid drawn at the full face would
        interpenetrate its neighbour — while ``face_width_mm`` records what it
        measures and ``nominal`` records what to buy.  Requires ``nominal``.
    grade : str, optional
        Grade the part is specified in, as the supplier names it, e.g.
        ``"STK"``.
    stock_profile : str, optional
        How the stock is worked — ``"rough sawn"``, ``"dressed"``.  Set
        automatically to ``"rough sawn"`` when ``rough=True`` and nothing else
        is given.
    **kwargs
        Forwarded to :class:`StockPart` (``qty``, ``grain_direction``,
        ``trim_allowance_mm``, ``rotation``, ``align``, ``mode``, ``notes``).

    Raises
    ------
    ValueError
        If ``nominal`` is combined with explicit dimensions, if neither is
        supplied, if ``rough`` is set without a ``nominal`` to look up, or if
        ``covers_mm`` is not a positive width no greater than the face.

    Notes
    -----
    ``grade`` and ``stock_profile`` buy nothing geometrically and everything
    commercially: rough sawn 1x6 cedar is $2.30/LF in STK and $1.30 in low
    grade, and a design that does not say which one it means cannot be priced
    to better than 77%.  They travel to the cut list, where
    :func:`woodshop.cutlist.dimensional.plan_dimensional` matches the part to
    the inventory entry it actually buys.

    Examples
    --------
    >>> rail = Board(length_mm=2000.0, nominal="1x6", material="pine", label="rail")
    >>> rail.width_mm
    139.7
    >>> picket = Board(length_mm=1219.2, nominal="1x6", rough=True,
    ...                material="white_cedar", label="picket")
    >>> round(picket.width_mm, 1), round(picket.thickness_mm, 1)
    (152.4, 25.4)
    >>> tg = Board(length_mm=1219.2, nominal="1x6", covers_mm=130.2,
    ...            material="white_cedar", label="board")
    >>> round(tg.width_mm, 1), round(tg.face_width_mm, 1)
    (130.2, 139.7)
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
        rough: bool = False,
        covers_mm: float | None = None,
        grade: str = "",
        stock_profile: str = "",
        **kwargs: Any,
    ) -> None:
        if nominal is not None:
            if thickness_mm is not None or width_mm is not None:
                raise ValueError(
                    f"{label!r}: pass either nominal= or thickness_mm=/width_mm=, "
                    "not both"
                )
            sizes = rough_dimensions_mm if rough else actual_dimensions_mm
            thickness_q, width_q = sizes(nominal)
            thickness_mm = float(thickness_q.magnitude)
            width_mm = float(width_q.magnitude)
        elif thickness_mm is None or width_mm is None:
            raise ValueError(
                f"{label!r}: give nominal=, or both thickness_mm= and width_mm="
            )
        elif rough:
            raise ValueError(
                f"{label!r}: rough= sizes a part from its nominal size, so it "
                "needs nominal= rather than explicit dimensions"
            )

        face_width_mm = width_mm
        if covers_mm is not None:
            if nominal is None:
                raise ValueError(
                    f"{label!r}: covers_mm describes a milled nominal size, so "
                    "it needs nominal= rather than explicit dimensions"
                )
            if covers_mm <= 0 or covers_mm > width_mm + 1e-9:
                raise ValueError(
                    f"{label!r}: covers_mm must be positive and no wider than "
                    f"the {width_mm:.1f} mm face, got {covers_mm!r}"
                )
            width_mm = float(covers_mm)

        super().__init__(
            length_mm=length_mm,
            width_mm=width_mm,
            thickness_mm=thickness_mm,
            material=material,
            label=label,
            **kwargs,
        )
        self.nominal = nominal or ""
        self.grade = grade
        self.stock_profile = stock_profile or ("rough sawn" if rough else "")
        #: What the board measures across its face, which is what it is sold
        #: as.  Equal to ``width_mm`` unless the stock is milled to interlock.
        self.face_width_mm = float(face_width_mm)


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


class ShapedPart(_StockMeta, BasePartObject):
    """Base class for parts turned about an axis, which runs along +Z.

    Both shapes this project needs are surfaces of revolution: a cylinder when
    the two ends are the same diameter, a frustum when they are not.  Open
    Cascade will not build a cone from two identical radii, so the class picks
    the primitive rather than making the caller do it.

    Not instantiated directly — use :class:`Disc` or :class:`Turning`.
    """

    _applies_to = [BuildPart._tag]

    def _build_solid(
        self,
        *,
        bottom_diameter_mm: float,
        top_diameter_mm: float,
        height_mm: float,
        rotation: RotationLike,
        align: Align | tuple[Align, Align, Align],
        mode: Mode,
        label: str,
    ) -> None:
        """Construct the underlying solid, validating the dimensions first."""
        for name, value in (
            ("bottom diameter", bottom_diameter_mm),
            ("top diameter", top_diameter_mm),
        ):
            if value < 0:
                raise ValueError(
                    f"{label!r}: {name} must not be negative, got {value!r}"
                )
        if height_mm <= 0:
            raise ValueError(f"{label!r}: length must be positive, got {height_mm!r}")
        if max(bottom_diameter_mm, top_diameter_mm) <= 0:
            raise ValueError(f"{label!r}: at least one diameter must be positive")

        context = BuildPart._get_context(self)
        validate_inputs(context, self)

        if bottom_diameter_mm == top_diameter_mm:
            solid = Solid.make_cylinder(bottom_diameter_mm / 2.0, height_mm)
        else:
            solid = Solid.make_cone(
                bottom_diameter_mm / 2.0, top_diameter_mm / 2.0, height_mm
            )

        super().__init__(
            part=solid, rotation=rotation, align=tuplify(align, 3), mode=mode
        )


class Disc(ShapedPart):
    """A round part cut and turned from a square blank.

    A table top, a seat, a lid.  The finished part is a circle of
    ``diameter_mm``; the blank on the cut list is the square you actually buy,
    which is larger by :data:`ROUND_BLANK_MARGIN_MM`.

    Give ``bottom_diameter_mm`` to angle the edge inward, which is how a thick
    top is made to look thinner than it is.

    Parameters
    ----------
    diameter_mm : float
        Finished diameter at the top face — the widest point, and the one the
        envelope is measured across.
    thickness_mm : float
        Finished thickness, along +Z.
    material : str
        Species or sheet-goods material key.
    label : str
        Part name.
    bottom_diameter_mm : float, optional
        Diameter at the underside.  Defaults to ``diameter_mm`` (a straight
        edge).  Smaller values angle the edge inward.
    blank_margin_mm : float, optional
        Extra on each side of the square blank, default
        :data:`ROUND_BLANK_MARGIN_MM`.
    grain_direction : str, optional
        Default ``"length"``.  A solid disc is normally a glue-up whose staves
        all run one way, and that direction is the one it moves across.
    qty, notes, rotation, align, mode
        As :class:`StockPart`.

    Raises
    ------
    ValueError
        If a dimension is non-positive.

    Examples
    --------
    >>> top = Disc(diameter_mm=457.2, thickness_mm=38.1,
    ...            material="cherry", label="top")
    >>> round(top.shape_yield, 3)               # a circle in a square, plus margin
    0.764
    """

    shape = "round"

    def __init__(
        self,
        diameter_mm: float,
        thickness_mm: float,
        *,
        material: str,
        label: str,
        bottom_diameter_mm: float | None = None,
        blank_margin_mm: float = ROUND_BLANK_MARGIN_MM,
        grain_direction: str = "length",
        qty: int = 1,
        notes: str = "",
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] = (
            Align.CENTER,
            Align.CENTER,
            Align.CENTER,
        ),
        mode: Mode = Mode.ADD,
    ) -> None:
        bottom = diameter_mm if bottom_diameter_mm is None else bottom_diameter_mm
        self._build_solid(
            bottom_diameter_mm=bottom,
            top_diameter_mm=diameter_mm,
            height_mm=thickness_mm,
            rotation=rotation,
            align=align,
            mode=mode,
            label=label,
        )

        blank = float(diameter_mm) + float(blank_margin_mm)
        profile = f"{mm_to_fractional_inch(diameter_mm)} dia. round"
        if bottom != diameter_mm:
            profile += f" tapering to {mm_to_fractional_inch(bottom)} at the underside"
        self._record(
            label=label,
            material=material,
            grain_direction=grain_direction,
            qty=qty,
            notes=notes,
            length_mm=diameter_mm,
            width_mm=diameter_mm,
            thickness_mm=thickness_mm,
            stock_length_mm=blank,
            stock_width_mm=blank,
            stock_thickness_mm=thickness_mm,
            finished_area_mm2=math.pi * float(diameter_mm) ** 2 / 4.0,
            profile=profile,
        )
        self.diameter_mm = float(diameter_mm)
        self.bottom_diameter_mm = float(bottom)


class Turning(ShapedPart):
    """A spindle turned between centres from a square blank.

    A leg, a stretcher, a knob.  The cut list calls for the blank — a square
    of the largest diameter plus :data:`ROUND_BLANK_MARGIN_MM`, long enough to
    lose :data:`TURNING_WASTE_MM` to the centres — because "1-1/2" tapering to
    1"" is not something anybody can buy.

    The axis runs along +Z, ``diameter_mm`` at the -Z end and
    ``end_diameter_mm`` at the +Z end.

    Parameters
    ----------
    length_mm : float
        Finished length along the axis, including any tenon.
    diameter_mm : float
        Diameter at the -Z end.
    material : str
        Species.
    label : str
        Part name.
    end_diameter_mm : float, optional
        Diameter at the +Z end.  Defaults to ``diameter_mm`` (a cylinder).
    blank_margin_mm : float, optional
        Extra on each side of the square blank, default
        :data:`ROUND_BLANK_MARGIN_MM`.
    turning_waste_mm : float, optional
        Extra blank length for the centres, default :data:`TURNING_WASTE_MM`.
    grain_direction : str, optional
        Default ``"length"``.  A spindle must be long-grain along its axis —
        there is no other way to turn one that will not snap.
    qty, notes, rotation, align, mode
        As :class:`StockPart`.

    Raises
    ------
    ValueError
        If a dimension is non-positive.

    Examples
    --------
    >>> leg = Turning(length_mm=546.1, diameter_mm=25.4, end_diameter_mm=38.1,
    ...               material="cherry", label="leg")
    >>> leg.stock_width_mm, round(leg.stock_length_mm, 1)
    (44.45, 571.5)
    """

    shape = "turned"

    def __init__(
        self,
        length_mm: float,
        diameter_mm: float,
        *,
        material: str,
        label: str,
        end_diameter_mm: float | None = None,
        blank_margin_mm: float = ROUND_BLANK_MARGIN_MM,
        turning_waste_mm: float = TURNING_WASTE_MM,
        grain_direction: str = "length",
        qty: int = 1,
        notes: str = "",
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] = (
            Align.CENTER,
            Align.CENTER,
            Align.CENTER,
        ),
        mode: Mode = Mode.ADD,
    ) -> None:
        end = diameter_mm if end_diameter_mm is None else end_diameter_mm
        self._build_solid(
            bottom_diameter_mm=diameter_mm,
            top_diameter_mm=end,
            height_mm=length_mm,
            rotation=rotation,
            align=align,
            mode=mode,
            label=label,
        )

        largest = max(float(diameter_mm), float(end))
        blank_side = largest + float(blank_margin_mm)
        smallest = min(float(diameter_mm), float(end))
        profile = f"turned, {mm_to_fractional_inch(largest)} dia."
        if smallest != largest:
            profile = (
                f"turned, {mm_to_fractional_inch(largest)} tapering to "
                f"{mm_to_fractional_inch(smallest)}"
            )
        self._record(
            label=label,
            material=material,
            grain_direction=grain_direction,
            qty=qty,
            notes=notes,
            length_mm=length_mm,
            width_mm=largest,
            thickness_mm=largest,
            stock_length_mm=float(length_mm) + float(turning_waste_mm),
            stock_width_mm=blank_side,
            stock_thickness_mm=blank_side,
            # Silhouette of the finished spindle: a trapezium, seen edge-on in
            # the plane the blank is nested in.
            finished_area_mm2=float(length_mm) * (largest + smallest) / 2.0,
            profile=profile,
        )
        self.diameter_mm = float(diameter_mm)
        self.end_diameter_mm = float(end)
        self.max_diameter_mm = largest


class Pole(ShapedPart):
    """Round stock bought round: a peeled log post, a log rail, a dowel.

    :class:`Turning` describes a spindle, and prices it as the square blank it
    is cut from, because nobody sells a tapered cylinder.  A log is the other
    case entirely — you buy the round thing, by the foot, and the only work
    done to it is a saw cut at each end.  Sizing it as a square blank would
    overstate what it costs by a third and describe an operation nobody
    performs.

    The axis runs along +Z, matching :class:`Turning`.  The stock dimensions
    are the round stock itself: ``stock_width_mm`` and ``stock_thickness_mm``
    are both the diameter, so anything measuring the part in a rectangular
    world gets the circumscribing square, which is the right answer for
    clearances and the wrong one for cost — hence the lineal-foot buying plan
    in :mod:`woodshop.cutlist.dimensional`.

    Parameters
    ----------
    length_mm : float
        Length along the axis.
    diameter_mm : float
        Diameter.  Round stock is graded in ranges — a "4 to 5 inch" post — so
        this is the size to design to and not a promise about any one stick.
    material : str
        Species.
    label : str
        Part name.
    end_diameter_mm : float, optional
        Diameter at the +Z end, for stock with noticeable taper.  Defaults to
        ``diameter_mm``.
    trim_allowance_mm : float, optional
        Extra length on the cut, default ``0.0``.
    grain_direction : str, optional
        Default ``"length"``: a pole is long grain along its axis, and there
        is no other kind.
    qty, notes, rotation, align, mode
        As :class:`StockPart`.

    Raises
    ------
    ValueError
        If a dimension is non-positive.

    Examples
    --------
    >>> post = Pole(length_mm=2438.4, diameter_mm=127.0, material="white_cedar",
    ...             label="log_post")
    >>> post.stock_width_mm, post.stock_length_mm
    (127.0, 2438.4)
    >>> post.shape
    'pole'
    """

    shape = "pole"

    def __init__(
        self,
        length_mm: float,
        diameter_mm: float,
        *,
        material: str,
        label: str,
        end_diameter_mm: float | None = None,
        trim_allowance_mm: float = 0.0,
        grain_direction: str = "length",
        qty: int = 1,
        notes: str = "",
        nominal: str = "",
        grade: str = "",
        stock_profile: str = "",
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] = (
            Align.CENTER,
            Align.CENTER,
            Align.CENTER,
        ),
        mode: Mode = Mode.ADD,
    ) -> None:
        end = diameter_mm if end_diameter_mm is None else end_diameter_mm
        self._build_solid(
            bottom_diameter_mm=diameter_mm,
            top_diameter_mm=end,
            height_mm=length_mm,
            rotation=rotation,
            align=align,
            mode=mode,
            label=label,
        )

        largest = max(float(diameter_mm), float(end))
        smallest = min(float(diameter_mm), float(end))
        profile = f"round, {mm_to_fractional_inch(largest)} dia."
        if smallest != largest:
            profile = (
                f"round, {mm_to_fractional_inch(largest)} tapering to "
                f"{mm_to_fractional_inch(smallest)}"
            )
        self._record(
            label=label,
            material=material,
            grain_direction=grain_direction,
            qty=qty,
            notes=notes,
            length_mm=length_mm,
            width_mm=largest,
            thickness_mm=largest,
            stock_length_mm=float(length_mm) + float(trim_allowance_mm),
            # The stock *is* the round thing: no blank, no margin, nothing to
            # saw off the corners.
            stock_width_mm=largest,
            stock_thickness_mm=largest,
            # Seen from the side, which is the only way a pole is ever drawn
            # flat: a rectangle if it is parallel, a trapezium if it tapers.
            finished_area_mm2=float(length_mm) * (largest + smallest) / 2.0,
            profile=profile,
            trim_allowance_mm=trim_allowance_mm,
        )
        self.diameter_mm = float(diameter_mm)
        self.end_diameter_mm = float(end)
        self.max_diameter_mm = largest
        self.nominal = nominal
        self.grade = grade
        self.stock_profile = stock_profile
        self.face_width_mm = largest


class ShapedBoard(_StockMeta, BasePartObject):
    """A flat part sawn to a shaped outline, rather than to a rectangle.

    A bandsawn leg, a curved rail, a crested headboard — anything whose face
    is a profile rather than four square corners.  The profile lies in the
    X-Y plane and is extruded along +Z, so the local frame matches
    :class:`Board`: the face is X-Y, the thickness is Z.

    The blank on the cut list is the **bounding rectangle** of that profile
    plus a margin, because that is what you buy and what you clamp to the saw.
    The finished area is the polygon's own area, so the waste between the two
    lands in ``finished_yield_fraction`` rather than disappearing.

    Parameters
    ----------
    profile : sequence of (float, float)
        Closed outline in mm, in order, as ``(x, y)`` pairs.  The closing
        segment is implied — do not repeat the first point.  Curves are
        polylines: sample them as finely as the shape deserves.
    thickness_mm : float
        Finished thickness, along +Z.
    material : str
        Species or sheet-goods material key.
    label : str
        Part name.
    blank_margin_mm : float, optional
        Added to each side of the bounding rectangle, default
        :data:`ROUND_BLANK_MARGIN_MM`.
    grain_direction : str, optional
        Default ``"length"``, meaning along the profile's longer axis.
    qty, notes, rotation, align, mode
        As :class:`StockPart`.

    Raises
    ------
    ValueError
        If fewer than three points are given, the thickness is non-positive,
        or the profile encloses no area.

    Examples
    --------
    >>> leg = ShapedBoard(
    ...     profile=[(0, 0), (140, 0), (140, 500), (60, 500)],
    ...     thickness_mm=44.45, material="cherry", label="foot_leg",
    ... )
    >>> round(leg.stock_length_mm, 2), round(leg.stock_width_mm, 2)
    (146.35, 506.35)
    >>> round(leg.shape_yield, 3)          # a trapezium in its bounding box
    0.742
    """

    shape = "shaped"

    _applies_to = [BuildPart._tag]

    def __init__(
        self,
        profile: Sequence[tuple[float, float]],
        thickness_mm: float,
        *,
        material: str,
        label: str,
        blank_margin_mm: float = ROUND_BLANK_MARGIN_MM,
        grain_direction: str = "length",
        qty: int = 1,
        notes: str = "",
        rotation: RotationLike = (0, 0, 0),
        align: Align | tuple[Align, Align, Align] = (
            Align.CENTER,
            Align.CENTER,
            Align.CENTER,
        ),
        mode: Mode = Mode.ADD,
    ) -> None:
        pts = [(float(x), float(y)) for x, y in profile]
        if len(pts) < 3:
            raise ValueError(
                f"{label!r}: a profile needs at least 3 points, got {len(pts)}"
            )
        if thickness_mm <= 0:
            raise ValueError(
                f"{label!r}: thickness_mm must be positive, got {thickness_mm!r}"
            )
        area = abs(_polygon_area(pts))
        if area <= 0:
            raise ValueError(f"{label!r}: the profile encloses no area")

        context = BuildPart._get_context(self)
        validate_inputs(context, self)
        solid = extrude(make_face(Polyline(*pts, close=True)), amount=thickness_mm)
        super().__init__(
            part=solid, rotation=rotation, align=tuplify(align, 3), mode=mode
        )

        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        length = max(xs) - min(xs)
        width = max(ys) - min(ys)
        self._record(
            label=label,
            material=material,
            grain_direction=grain_direction,
            qty=qty,
            notes=notes,
            length_mm=length,
            width_mm=width,
            thickness_mm=thickness_mm,
            stock_length_mm=length + blank_margin_mm,
            stock_width_mm=width + blank_margin_mm,
            stock_thickness_mm=thickness_mm,
            finished_area_mm2=area,
            profile=(
                f"sawn to a profile, {mm_to_fractional_inch(length)} x "
                f"{mm_to_fractional_inch(width)} blank"
            ),
        )
        self.profile_points = pts


def _polygon_area(points: Sequence[tuple[float, float]]) -> float:
    """Return the signed area of a closed polygon by the shoelace formula."""
    total = 0.0
    for i, (x0, y0) in enumerate(points):
        x1, y1 = points[(i + 1) % len(points)]
        total += x0 * y1 - x1 * y0
    return total / 2.0


#: Attributes that make a solid recognisable to the cut list.
_METADATA_ATTRS: tuple[str, ...] = (
    "label",
    "material",
    "grain_direction",
    "qty",
    "notes",
    "length_mm",
    "width_mm",
    "thickness_mm",
    "stock_length_mm",
    "stock_width_mm",
    "stock_thickness_mm",
    "finished_area_mm2",
    "profile",
    "trim_allowance_mm",
    "shape",
    "nominal",
    "grade",
    "stock_profile",
    "face_width_mm",
)


def retag(solid: Any, like: Any, **overrides: Any) -> Any:
    """Copy cut-list metadata from one part onto another solid.

    A boolean operation returns a plain build123d solid: subtract a mortise
    from a rail, or saw a splayed foot off flat, and the result is geometry
    with no idea what it used to be.  The cut list then loses the part
    entirely, silently, and the only symptom is a missing row.

    This is the two-line fix at the call site.  It does not merge parts or
    recompute anything — the blank you buy is unchanged by a mortise, which is
    exactly why the metadata should survive the cut.

    Parameters
    ----------
    solid : build123d.Shape
        The result of the operation.
    like : StockPart or ShapedPart
        The part it was made from.
    **overrides
        Metadata to change rather than copy, e.g. ``notes=...``.

    Returns
    -------
    build123d.Shape
        *solid*, with the metadata attached.  Returned for chaining; the
        object is modified in place.

    Examples
    --------
    >>> from build123d import Pos, Box
    >>> from woodshop.parts import Board, retag
    >>> rail = Board(length_mm=600.0, thickness_mm=25.0, width_mm=100.0,
    ...              material="cherry", label="rail")
    >>> mortised = retag(rail - Pos(0, 0, 0) * Box(20, 20, 30), like=rail)
    >>> mortised.label, round(mortised.stock_length_mm, 1)
    ('rail', 600.0)
    """
    for attr in _METADATA_ATTRS:
        if hasattr(like, attr):
            setattr(solid, attr, getattr(like, attr))
    for attr, value in overrides.items():
        setattr(solid, attr, value)
    return solid


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
