"""Render cut lists as pandas DataFrames, CSV, Markdown, and matplotlib diagrams.

Typical usage::

    from woodshop.cutlist.extract import extract
    from woodshop.cutlist.render import render_cut_list, render_sheet_diagram

    parts = extract(assembly)
    df = render_cut_list(parts, output_csv="cut_list.csv", output_md="cut_list.md")
    render_sheet_diagram(result_2d, sheet_w_mm=1219.2, sheet_h_mm=2438.4,
                         output_pdf="sheets.pdf")
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import pandas as pd

from woodshop.cutlist.extract import CutPart
from woodshop.lumber import mm_to_fractional_inch

if TYPE_CHECKING:
    from woodshop.cutlist.optimize_2d import Cut2DResult


def render_cut_list(
    parts: list[CutPart],
    output_csv: str | Path | None = None,
    output_md: str | Path | None = None,
) -> pd.DataFrame:
    """Build a cut-list DataFrame and optionally write CSV / Markdown outputs.

    Parameters
    ----------
    parts : list[CutPart]
        Parts extracted from an assembly.
    output_csv : str or Path, optional
        If given, write the DataFrame to this CSV file.
    output_md : str or Path, optional
        If given, write the DataFrame as a Markdown table to this file.

    Returns
    -------
    pandas.DataFrame
        Columns: ``label``, ``material``, ``grain``, ``qty``,
        ``length``, ``width``, ``thickness``.
    """
    rows = [
        {
            "label": p.label,
            "material": p.material,
            "grain": p.grain_direction,
            "qty": p.qty,
            "length": mm_to_fractional_inch(p.length_mm),
            "width": mm_to_fractional_inch(p.width_mm),
            "thickness": mm_to_fractional_inch(p.thickness_mm),
        }
        for p in parts
    ]

    df = pd.DataFrame(rows, columns=["label", "material", "grain", "qty",
                                     "length", "width", "thickness"])

    if output_csv is not None:
        df.to_csv(output_csv, index=False)

    if output_md is not None:
        Path(output_md).write_text(df.to_markdown(index=False), encoding="utf-8")

    return df


def render_sheet_diagram(
    result: "Cut2DResult",
    sheet_w_mm: float,
    sheet_h_mm: float,
    output_pdf: str | Path | None = None,
) -> list[plt.Figure]:
    """Render one matplotlib figure per sheet in *result*.

    Parameters
    ----------
    result : Cut2DResult
        Result from :func:`woodshop.cutlist.optimize_2d.optimize_2d`.
    sheet_w_mm : float
        Sheet width in mm.
    sheet_h_mm : float
        Sheet height in mm.
    output_pdf : str or Path, optional
        If given, save all sheets as a multi-page PDF.

    Returns
    -------
    list[matplotlib.figure.Figure]
        One figure per sheet.
    """
    from matplotlib.backends.backend_pdf import PdfPages

    n_sheets = result.sheets_used
    figs: list[plt.Figure] = []

    def _render_sheets(pdf: PdfPages | None) -> list[plt.Figure]:
        for sheet_idx in range(n_sheets):
            fig, ax = plt.subplots(figsize=(8, 16))
            ax.set_xlim(0, sheet_w_mm)
            ax.set_ylim(0, sheet_h_mm)
            ax.set_aspect("equal")
            ax.set_title(f"Sheet {sheet_idx + 1}")
            ax.set_xlabel(f"Width  ({mm_to_fractional_inch(sheet_w_mm)})")
            ax.set_ylabel(f"Height ({mm_to_fractional_inch(sheet_h_mm)})")

            cmap = plt.get_cmap("tab20")
            placements = [p for p in result.placements if p.sheet_index == sheet_idx]

            for i, pl in enumerate(placements):
                color = cmap(i % 20)
                rect = mpatches.Rectangle(
                    (pl.x_mm, pl.y_mm), pl.width_mm, pl.height_mm,
                    linewidth=1, edgecolor="black", facecolor=color, alpha=0.6,
                )
                ax.add_patch(rect)
                ax.text(
                    pl.x_mm + pl.width_mm / 2,
                    pl.y_mm + pl.height_mm / 2,
                    pl.label,
                    ha="center", va="center", fontsize=7, wrap=True,
                )

            figs.append(fig)
            if pdf is not None:
                pdf.savefig(fig)

        return figs

    if output_pdf is not None:
        with PdfPages(output_pdf) as pdf:
            _render_sheets(pdf)
    else:
        _render_sheets(None)

    return figs
