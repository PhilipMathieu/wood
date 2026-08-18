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
        ``length``, ``width``, ``thickness`` — plus ``shape`` if any part is
        not rectangular, and ``stock`` if any part names the nominal size it
        is cut from.

    Notes
    -----
    The dimensions are the **blank**: what to cut from a board, not what the
    finished part measures.  For a rectangle those are the same thing.  For a
    round or turned part they are not, and the blank is the useful one — an
    18" disc is bought and cut as an 18-1/4" square, and nobody can hand you a
    board 1-1/2" tapering to 1".  The ``shape`` column says what to do with the
    blank once it is cut.

    The ``stock`` column says what to *buy*, which stops being obvious the
    moment a part is cut from dimensional lumber: a row reading 5-1/8" wide is
    a 1x6 tongue and groove board, and a shop given only the finished width
    would go looking for 5-1/8" stock that nobody sells.
    """
    columns = ["label", "material", "grain", "qty", "length", "width", "thickness"]
    # A column reading "rectangular" on every row of a bed teaches nobody
    # anything; on a nightstand with three turned legs it is the whole point.
    shaped = any(p.shape != "rectangular" for p in parts)
    if shaped:
        columns.append("shape")
    # Milled to size out of rough hardwood, there is no nominal size to name;
    # cut from dimensional lumber, the nominal size is what the order says.
    stocked = any(p.nominal for p in parts)
    if stocked:
        columns.append("stock")

    rows = []
    for p in parts:
        row = {
            "label": p.label,
            "material": p.material,
            "grain": p.grain_direction,
            "qty": p.qty,
            "length": mm_to_fractional_inch(p.length_mm),
            "width": mm_to_fractional_inch(p.width_mm),
            "thickness": mm_to_fractional_inch(p.thickness_mm),
        }
        if shaped:
            row["shape"] = p.profile or p.shape
        if stocked:
            row["stock"] = p.stock_spec
        rows.append(row)

    df = pd.DataFrame(rows, columns=columns)

    if output_csv is not None:
        df.to_csv(output_csv, index=False)

    if output_md is not None:
        Path(output_md).write_text(df.to_markdown(index=False), encoding="utf-8")

    return df
