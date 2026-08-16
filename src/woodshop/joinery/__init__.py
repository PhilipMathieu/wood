"""Joinery subtractive operations: Dado, Rabbet, Tenon, PocketHole.

Each class follows the bd_warehouse ``ClearanceHole`` idiom:
- ``mode=Mode.SUBTRACT`` by default
- context-aware (works inside a ``BuildPart`` context or standalone)
- registers ``stock_length`` / other metadata on the host part when applicable

Usage example::

    with BuildPart() as leg:
        Board("2x4", length_mm=800, label="leg")
        Mortise(width_mm=38, height_mm=19, depth_mm=38, label="top_rail_mortise")
"""

from __future__ import annotations

from build123d import Box, Mode


class Dado(Box):
    """A rectangular dado (trench) cut across the grain.

    Parameters
    ----------
    width_mm : float
        Width of the dado (perpendicular to grain), typically the mating part thickness.
    depth_mm : float
        Depth of the cut into the board.
    length_mm : float
        Length of the dado along the board face.
    mode : build123d.Mode, optional
        Default is ``Mode.SUBTRACT``.
    """

    def __init__(
        self,
        width_mm: float,
        depth_mm: float,
        length_mm: float,
        *,
        mode: Mode = Mode.SUBTRACT,
    ) -> None:
        super().__init__(length=length_mm, width=width_mm, height=depth_mm, mode=mode)


class Rabbet(Box):
    """A rabbet (rebate) cut along the edge of a board.

    Parameters
    ----------
    width_mm : float
        Width of the rabbet shoulder.
    depth_mm : float
        Depth of the rabbet cut.
    length_mm : float
        Length of the rabbet (typically the full board length).
    mode : build123d.Mode, optional
        Default is ``Mode.SUBTRACT``.
    """

    def __init__(
        self,
        width_mm: float,
        depth_mm: float,
        length_mm: float,
        *,
        mode: Mode = Mode.SUBTRACT,
    ) -> None:
        super().__init__(length=length_mm, width=width_mm, height=depth_mm, mode=mode)


class Tenon(Box):
    """A rectangular tenon that extends beyond the shoulder of a board.

    The tenon geometry is *additive* (it projects from the board end), but the
    corresponding mortise must be subtracted from the mating part separately.

    .. note::
       Call :py:func:`woodshop.joinery.Mortise` on the mating part to cut the pocket.

    Parameters
    ----------
    width_mm : float
        Tenon face width.
    height_mm : float
        Tenon thickness.
    length_mm : float
        Tenon projection beyond the shoulder (haunched length).
    mode : build123d.Mode, optional
        Default is ``Mode.ADD`` (the tenon adds material).
    """

    def __init__(
        self,
        width_mm: float,
        height_mm: float,
        length_mm: float,
        *,
        mode: Mode = Mode.ADD,
    ) -> None:
        super().__init__(length=length_mm, width=width_mm, height=height_mm, mode=mode)


class Mortise(Box):
    """A rectangular mortise pocket in a board.

    Parameters
    ----------
    width_mm : float
        Mortise width (matches tenon width + fit allowance).
    height_mm : float
        Mortise height (matches tenon height + fit allowance).
    depth_mm : float
        Mortise depth.
    mode : build123d.Mode, optional
        Default is ``Mode.SUBTRACT``.
    """

    def __init__(
        self,
        width_mm: float,
        height_mm: float,
        depth_mm: float,
        *,
        mode: Mode = Mode.SUBTRACT,
    ) -> None:
        super().__init__(length=depth_mm, width=width_mm, height=height_mm, mode=mode)


class PocketHole(Box):
    """A pocket-hole screw pocket (Kreg-style).

    Approximated as an angled rectangular slot. Depth and width are fixed to
    match common Kreg R3/K4 dimensions.

    Parameters
    ----------
    board_thickness_mm : float
        Thickness of the board being joined (determines pocket depth).
    mode : build123d.Mode, optional
        Default is ``Mode.SUBTRACT``.
    """

    # Typical Kreg pocket-hole dimensions
    _POCKET_WIDTH_MM: float = 9.525    # 3/8"
    _POCKET_HEIGHT_MM: float = 14.288  # ~9/16"

    def __init__(
        self,
        board_thickness_mm: float,
        *,
        mode: Mode = Mode.SUBTRACT,
    ) -> None:
        depth_mm = board_thickness_mm * 0.75
        super().__init__(
            length=depth_mm,
            width=self._POCKET_WIDTH_MM,
            height=self._POCKET_HEIGHT_MM,
            mode=mode,
        )
