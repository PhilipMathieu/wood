"""1-D cutting-stock optimisation for solid stock using OR-Tools CP-SAT.

Given a list of required cut lengths and a list of available stock lengths,
choose how many pieces of which length to buy and which cuts to take from each,
accounting for kerf waste between cuts.

Two rules the solver enforces that are easy to get wrong by hand:

* **Cuts are grouped by cross-section.** A 2x4 cut and a 1x6 cut cannot come
  off the same board, so each ``(material, thickness, width)`` group is solved
  as an independent cutting-stock problem.
* **Stock length is chosen per board.** When both 8 ft and 10 ft stock is
  available, using a 10 ft board for three 900 mm rails beats using an 8 ft
  board and starting a second one.  The default objective minimises total
  length purchased rather than the number of boards, because that is what you
  pay for.

Example
-------
>>> from woodshop.cutlist.optimize_1d import optimize_1d
>>> from woodshop.cutlist.extract import CutPart
>>> parts = [CutPart("leg", "pine", "length", 800, 38, 38, qty=4)]
>>> result = optimize_1d(parts, stock_lengths_mm=[2438.4])
>>> result.stock_used
2
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ortools.sat.python import cp_model  # type: ignore[import]

from woodshop.cutlist.extract import CutPart
from woodshop.lumber import KERF_MM, mm_to_fractional_inch

__all__ = ["Cut1DResult", "StockPiece", "optimize_1d", "section_key"]


def section_key(part: CutPart) -> str:
    """Return the cross-section key a part must be cut from.

    Parts sharing a key can come off the same board; parts with different keys
    cannot.

    Parameters
    ----------
    part : CutPart
        The part to key.

    Returns
    -------
    str
        A human-readable key, e.g. ``'cherry 1-3/4" x 1-3/4"'``.
    """
    return (
        f"{part.material} "
        f"{mm_to_fractional_inch(part.thickness_mm)} x "
        f"{mm_to_fractional_inch(part.width_mm)}"
    )


@dataclass
class StockPiece:
    """One piece of stock and the cuts taken from it.

    Parameters
    ----------
    section : str
        Cross-section key — see :func:`section_key`.
    stock_length_mm : float
        Length of the piece purchased.
    cuts : list[tuple[str, float]]
        ``(part_label, length_mm)`` for each cut on this piece, in the order
        the solver assigned them.
    waste_mm : float
        Length left over after all cuts and kerfs.
    """

    section: str
    stock_length_mm: float
    cuts: list[tuple[str, float]] = field(default_factory=list)
    waste_mm: float = 0.0


@dataclass
class Cut1DResult:
    """Result of a 1-D cutting-stock optimisation run.

    Parameters
    ----------
    stock_used : int
        Total number of stock pieces consumed across all cross-sections.
    assignments : list[list[tuple[str, float]]]
        One list per stock piece; each tuple is ``(part_label, length_mm)``.
    waste_mm : list[float]
        Leftover length (mm) for each stock piece, in the same order.
    pieces : list[StockPiece]
        Richer per-piece detail, including which cross-section and which stock
        length each piece is.
    """

    stock_used: int
    assignments: list[list[tuple[str, float]]] = field(default_factory=list)
    waste_mm: list[float] = field(default_factory=list)
    pieces: list[StockPiece] = field(default_factory=list)

    @property
    def total_length_mm(self) -> float:
        """Total length of stock purchased, in mm."""
        return sum(p.stock_length_mm for p in self.pieces)

    @property
    def total_waste_mm(self) -> float:
        """Total offcut length, in mm."""
        return sum(p.waste_mm for p in self.pieces)

    @property
    def yield_fraction(self) -> float:
        """Fraction of purchased length that ends up in parts (0-1)."""
        total = self.total_length_mm
        return 0.0 if total == 0 else 1.0 - self.total_waste_mm / total


def optimize_1d(
    parts: list[CutPart],
    stock_lengths_mm: list[float],
    kerf_mm: float = KERF_MM,
    objective: str = "length",
    max_time_s: float = 30.0,
    group_by_section: bool = True,
) -> Cut1DResult:
    """Choose stock and assign cuts to minimise purchased material.

    Parameters
    ----------
    parts : list[CutPart]
        Required cuts (``qty`` is honoured — each part is expanded).
    stock_lengths_mm : list[float]
        Stock lengths available to buy.  Every length is a candidate for every
        board; the solver picks per board.
    kerf_mm : float, optional
        Saw kerf added between cuts on the same piece, default ``KERF_MM``.
    objective : str, optional
        ``"length"`` (default) minimises total length purchased;
        ``"pieces"`` minimises the number of boards.
    max_time_s : float, optional
        Solver time limit per cross-section group, default 30 s.
    group_by_section : bool, optional
        Solve each ``(material, thickness, width)`` group separately, default
        ``True``.  Set ``False`` only if every part really does come from the
        same stock.

    Returns
    -------
    Cut1DResult
        Optimised assignment of cuts to stock pieces.

    Raises
    ------
    ValueError
        If ``stock_lengths_mm`` is empty, ``objective`` is unknown, or a
        required cut is longer than the longest available stock.
    RuntimeError
        If CP-SAT finds no feasible solution within the time limit.
    """
    if objective not in ("length", "pieces"):
        raise ValueError(f"objective must be 'length' or 'pieces', got {objective!r}")
    if not parts:
        return Cut1DResult(stock_used=0)
    if not stock_lengths_mm:
        raise ValueError("stock_lengths_mm is empty — nothing to cut from")

    groups: dict[str, list[CutPart]] = {}
    for p in parts:
        key = section_key(p) if group_by_section else "all"
        groups.setdefault(key, []).append(p)

    pieces: list[StockPiece] = []
    for key in groups:
        pieces.extend(
            _solve_group(
                groups[key], key, stock_lengths_mm, kerf_mm, objective, max_time_s
            )
        )

    return Cut1DResult(
        stock_used=len(pieces),
        assignments=[p.cuts for p in pieces],
        waste_mm=[p.waste_mm for p in pieces],
        pieces=pieces,
    )


def _solve_group(
    parts: list[CutPart],
    section: str,
    stock_lengths_mm: list[float],
    kerf_mm: float,
    objective: str,
    max_time_s: float,
) -> list[StockPiece]:
    """Solve the cutting-stock problem for one cross-section group."""
    cuts: list[tuple[str, float]] = []
    for p in parts:
        cuts.extend((p.label, p.length_mm) for _ in range(p.qty))
    if not cuts:
        return []

    lengths = sorted(set(stock_lengths_mm))
    longest = lengths[-1]
    too_long = {label for label, length in cuts if length > longest}
    if too_long:
        raise ValueError(
            f"{section}: parts {sorted(too_long)} are longer than the longest "
            f"stock available ({longest:.1f} mm)"
        )

    n_cuts = len(cuts)
    # One bin per cut is the only sound bound when the objective is purchased
    # length.  A greedy first-fit-decreasing pass bounds the *bin count*, but
    # the cheapest plan may use more bins than that: with cuts of 2900 and ten
    # of 999 against 1000 mm and 3000 mm stock, the optimum is one 3000 plus
    # ten 1000s — eleven bins, where greedy on the only length long enough for
    # the 2900 cut finds six and hides the answer.
    max_bins = n_cuts

    model = cp_model.CpModel()
    scale = 1000  # work in micrometres (integer)
    cut_scaled = [int(round(c[1] * scale)) for c in cuts]
    len_scaled = [int(round(length * scale)) for length in lengths]
    kerf_scaled = int(round(kerf_mm * scale))

    # x[i][j] = 1 if cut i is on board j
    x = [[model.new_bool_var(f"x_{i}_{j}") for j in range(max_bins)] for i in range(n_cuts)]
    # y[j] = 1 if board j is used
    y = [model.new_bool_var(f"y_{j}") for j in range(max_bins)]
    # u[j][k] = 1 if board j is cut from stock length k
    u = [
        [model.new_bool_var(f"u_{j}_{k}") for k in range(len(lengths))]
        for j in range(max_bins)
    ]

    for i in range(n_cuts):
        model.add_exactly_one(x[i][j] for j in range(max_bins))

    for j in range(max_bins):
        # A used board is exactly one stock length; an unused board is none.
        model.add(sum(u[j][k] for k in range(len(lengths))) == y[j])

        capacity = sum(u[j][k] * len_scaled[k] for k in range(len(lengths)))
        cut_sum = sum(x[i][j] * cut_scaled[i] for i in range(n_cuts))
        count = sum(x[i][j] for i in range(n_cuts))
        # Cuts plus the kerf between each adjacent pair must fit the board.
        model.add(cut_sum + (count - 1) * kerf_scaled <= capacity)

        for i in range(n_cuts):
            model.add(x[i][j] <= y[j])

    # Symmetry breaking: boards are used in order.
    for j in range(max_bins - 1):
        model.add(y[j] >= y[j + 1])

    total_length = sum(
        u[j][k] * len_scaled[k] for j in range(max_bins) for k in range(len(lengths))
    )
    if objective == "length":
        # Minimise purchased length, then break ties toward fewer boards
        # (fewer boards means fewer setups for the same material cost).
        model.minimize(total_length * 1000 + sum(y))
    else:
        model.minimize(sum(y) * len_scaled[-1] * 1000 + total_length)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_time_s
    status = solver.solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError(
            f"{section}: OR-Tools CP-SAT found no feasible solution "
            f"(status {solver.status_name(status)})"
        )

    pieces: list[StockPiece] = []
    for j in range(max_bins):
        if not solver.value(y[j]):
            continue
        board_cuts = [cuts[i] for i in range(n_cuts) if solver.value(x[i][j])]
        stock_len = next(
            lengths[k] for k in range(len(lengths)) if solver.value(u[j][k])
        )
        used = sum(length for _, length in board_cuts)
        used += kerf_mm * (len(board_cuts) - 1)
        pieces.append(
            StockPiece(
                section=section,
                stock_length_mm=stock_len,
                cuts=board_cuts,
                waste_mm=stock_len - used,
            )
        )

    return pieces
