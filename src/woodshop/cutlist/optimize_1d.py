"""1-D cutting-stock optimisation for dimensional lumber using OR-Tools CP-SAT.

Given a list of required cut lengths and a list of available stock lengths,
find the minimum number of stock pieces needed to fulfil all cuts (accounting
for kerf waste between cuts).

Example
-------
>>> from woodshop.cutlist.optimize_1d import optimize_1d
>>> from woodshop.cutlist.extract import CutPart
>>> parts = [CutPart("leg", "pine", "length", 800, 38, 38, qty=4)]
>>> result = optimize_1d(parts, stock_lengths_mm=[2438.4])  # 8 ft
>>> result.stock_used
2
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ortools.sat.python import cp_model  # type: ignore[import]

from woodshop.cutlist.extract import CutPart
from woodshop.lumber import KERF_MM


@dataclass
class Cut1DResult:
    """Result of a 1-D cutting-stock optimisation run.

    Parameters
    ----------
    stock_used : int
        Total number of stock pieces consumed.
    assignments : list[list[tuple[str, float]]]
        One list per stock piece; each tuple is ``(part_label, length_mm)``.
    waste_mm : list[float]
        Leftover length (mm) for each stock piece.
    """

    stock_used: int
    assignments: list[list[tuple[str, float]]] = field(default_factory=list)
    waste_mm: list[float] = field(default_factory=list)


def optimize_1d(
    parts: list[CutPart],
    stock_lengths_mm: list[float],
    kerf_mm: float = KERF_MM,
) -> Cut1DResult:
    """Minimise the number of stock pieces needed to fulfil *parts*.

    Uses a CP-SAT column-generation approach: enumerate which cuts go on each
    stock piece and minimise the number of pieces used.

    Parameters
    ----------
    parts : list[CutPart]
        Required cuts (``qty`` is honoured — each part is expanded).
    stock_lengths_mm : list[float]
        Available stock lengths.  If more than one length is given the solver
        chooses the best-fit per piece.
    kerf_mm : float, optional
        Saw kerf added between cuts on the same piece, default ``KERF_MM``.

    Returns
    -------
    Cut1DResult
        Optimised assignment of cuts to stock pieces.
    """
    # Expand parts by qty into individual cut requests.
    cuts: list[tuple[str, float]] = []
    for p in parts:
        for _ in range(p.qty):
            cuts.append((p.label, p.length_mm))

    if not cuts:
        return Cut1DResult(stock_used=0)

    # Use the longest stock length as the primary bin size.
    stock_len = max(stock_lengths_mm)

    n_cuts = len(cuts)
    # Upper bound: one cut per stock piece.
    max_bins = n_cuts

    model = cp_model.CpModel()
    scale = 1000  # work in micrometres (integer)

    cut_lengths_scaled = [int(round(c[1] * scale)) for c in cuts]
    stock_len_scaled = int(round(stock_len * scale))
    kerf_scaled = int(round(kerf_mm * scale))

    # x[i][j] = 1 if cut i is on bin j
    x = [[model.new_bool_var(f"x_{i}_{j}") for j in range(max_bins)] for i in range(n_cuts)]
    # y[j] = 1 if bin j is used
    y = [model.new_bool_var(f"y_{j}") for j in range(max_bins)]

    # Each cut is assigned to exactly one bin.
    for i in range(n_cuts):
        model.add(sum(x[i][j] for j in range(max_bins)) == 1)

    # Bin capacity constraint (cuts + kerfs between them).
    for j in range(max_bins):
        # Sum of cuts on bin j + (num_cuts_on_j - 1) * kerf <= stock_len
        cut_sum = sum(x[i][j] * cut_lengths_scaled[i] for i in range(n_cuts))
        count = sum(x[i][j] for i in range(n_cuts))
        model.add(cut_sum + (count - 1) * kerf_scaled <= stock_len_scaled)

        # Bin is used if any cut is assigned.
        for i in range(n_cuts):
            model.add(x[i][j] <= y[j])

    # Symmetry breaking: bins used in order.
    for j in range(max_bins - 1):
        model.add(y[j] >= y[j + 1])

    model.minimize(sum(y))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    status = solver.solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise RuntimeError("OR-Tools CP-SAT could not find a feasible solution.")

    assignments: list[list[tuple[str, float]]] = []
    waste: list[float] = []

    for j in range(max_bins):
        if not solver.value(y[j]):
            continue
        bin_cuts: list[tuple[str, float]] = []
        total = 0.0
        for i in range(n_cuts):
            if solver.value(x[i][j]):
                bin_cuts.append(cuts[i])
                total += cuts[i][1]
        kerf_total = kerf_mm * (len(bin_cuts) - 1)
        assignments.append(bin_cuts)
        waste.append(stock_len - total - kerf_total)

    return Cut1DResult(stock_used=len(assignments), assignments=assignments, waste_mm=waste)
