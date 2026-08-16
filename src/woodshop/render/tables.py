"""Render a cut list as a pandas DataFrame, CSV, or Markdown table.

Typical usage::

    from woodshop.cutlist.extract import extract
    from woodshop.render import render_cut_list

    parts = extract(assembly)
    df = render_cut_list(parts, output_csv="cut_list.csv", output_md="cut_list.md")
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from woodshop.cutlist.extract import CutPart
from woodshop.lumber import mm_to_fractional_inch


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
