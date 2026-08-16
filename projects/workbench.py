"""Example project: simple workbench top with legs.

Run with:
    uv run python projects/workbench.py

For 3-D preview in VS Code run this file directly with ocp_vscode installed.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------
from woodshop.cutlist.optimize_1d import optimize_1d
from woodshop.cutlist.render import render_cut_list

# Nominal stock lengths available (mm).
STOCK_LENGTHS_MM = [2438.4, 3048.0]  # 8 ft, 10 ft


def build_workbench() -> list:  # type: ignore[type-arg]
    """Return a flat list of CutPart objects for a simple workbench.

    Returns
    -------
    list[CutPart]
        All parts required for the workbench.
    """
    # This example uses CutParts directly (no build123d geometry) to keep the
    # script runnable without the full Open Cascade installation.
    from woodshop.cutlist.extract import CutPart

    parts = [
        CutPart("top_board", "pine", "length", 1828.8, 139.7, 38.1, qty=5),  # 2x6 x 72"
        CutPart("leg", "pine", "length", 863.6, 88.9, 88.9, qty=4),           # 4x4 x 34"
        CutPart("apron_long", "pine", "length", 1651.0, 88.9, 38.1, qty=2),   # 2x4 x 65"
        CutPart("apron_short", "pine", "length", 558.8, 88.9, 38.1, qty=2),   # 2x4 x 22"
        CutPart("shelf", "pine", "length", 1651.0, 139.7, 38.1, qty=3),       # 2x6 x 65"
    ]
    return parts


def main() -> None:
    """Generate cut list and optimise stock usage for the workbench."""
    parts = build_workbench()
    df = render_cut_list(parts, output_csv="workbench_cut_list.csv",
                         output_md="workbench_cut_list.md")
    print(df.to_string(index=False))

    result_1d = optimize_1d(parts, stock_lengths_mm=STOCK_LENGTHS_MM)
    print(f"\nStock pieces needed: {result_1d.stock_used}")
    for i, assignment in enumerate(result_1d.assignments):
        labels = ", ".join(f"{lbl} ({length_mm:.0f} mm)" for lbl, length_mm in assignment)
        waste = result_1d.waste_mm[i]
        print(f"  Board {i + 1}: {labels}  | waste {waste:.0f} mm")


if __name__ == "__main__":
    main()
