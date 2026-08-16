"""Draw nesting layouts for sheet goods and for hardwood boards.

Both are the same picture with different stock behind it: rectangles packed
into a larger rectangle by the shelf packer.  Sheets are 4x8 or 5x5 plywood;
boards are random-width hardwood, where parts are ripped across the width as
well as cut along the length.

Two things the earlier renderer left out and a person at the saw needs:

* **Grain.** Parts are hatched along their grain, so "why is this one sideways?"
  is answered by the drawing rather than by re-reading the code.
* **Cut order.** Shelf layouts are guillotine-cuttable by construction, which
  is worth cashing in: :func:`cut_sequence` reads the strips back out as an
  ordered list of crosscuts and rips.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt

from woodshop.lumber import mm_to_fractional_inch

if TYPE_CHECKING:
    from woodshop.cutlist.hardwood import HardwoodPlan
    from woodshop.cutlist.optimize_2d import Cut2DResult, Placement

__all__ = ["render_sheet_diagram", "render_board_diagram", "cut_sequence"]

_IN = 25.4


def _grain_hatch(placement: "Placement") -> str | None:
    """Return a hatch pattern showing which way the grain runs, if it matters.

    ``'|'`` means the grain runs up the page (along the stock's length),
    ``'-'`` means across it.  Parts with no grain requirement get no hatch.
    """
    grain = getattr(placement, "grain_direction", "none")
    if grain == "none":
        return None
    if grain == "length":
        return "|" if placement.rotated else "-"
    return "-" if placement.rotated else "|"


def _inch_ticks(set_ticks, set_labels, extent_mm: float, step_in: float) -> None:
    """Place axis ticks at whole-inch intervals and label them in inches.

    The model is in mm throughout, but a layout drawing is read next to a tape
    measure — mm gridlines under an inch-labelled axis invite the wrong cut.
    """
    step = step_in * _IN
    n = int(extent_mm // step)
    ticks = [i * step for i in range(n + 1)]
    set_ticks(ticks)
    set_labels([f'{t / _IN:.0f}"' for t in ticks], fontsize=7)


def _render_layout(
    placements: list["Placement"],
    n_panels: int,
    panel_w_mm: float,
    panel_h_mm: float,
    panel_label: str,
    subtitle: str,
    close: bool,
) -> list[plt.Figure]:
    """Draw one figure per sheet or board."""
    figs: list[plt.Figure] = []
    cmap = plt.get_cmap("tab20")

    for index in range(n_panels):
        # Keep the drawing a sensible shape whatever the stock's aspect ratio.
        aspect = panel_h_mm / panel_w_mm if panel_w_mm else 1.0
        height = max(5.0, min(16.0, 7.0 * aspect))
        fig, ax = plt.subplots(figsize=(7.0, height))
        ax.set_xlim(0, panel_w_mm)
        ax.set_ylim(0, panel_h_mm)
        ax.set_aspect("equal")
        ax.set_title(f"{panel_label} {index + 1} of {n_panels}\n{subtitle}", fontsize=10)
        ax.set_xlabel(f"width  {mm_to_fractional_inch(panel_w_mm)}")
        ax.set_ylabel(f"length  {mm_to_fractional_inch(panel_h_mm)}  (face grain ↕)")
        # Geometry is in mm, but nobody at the saw is measuring this in mm.
        _inch_ticks(ax.set_xticks, ax.set_xticklabels, panel_w_mm, 6.0)
        _inch_ticks(ax.set_yticks, ax.set_yticklabels, panel_h_mm, 12.0)

        on_panel = [p for p in placements if p.sheet_index == index]
        for i, pl in enumerate(on_panel):
            ax.add_patch(
                mpatches.Rectangle(
                    (pl.x_mm, pl.y_mm), pl.width_mm, pl.height_mm,
                    linewidth=1, edgecolor="black",
                    facecolor=cmap(i % 20), alpha=0.55,
                    hatch=_grain_hatch(pl),
                )
            )
            long_side = max(pl.width_mm, pl.height_mm)
            ax.text(
                pl.x_mm + pl.width_mm / 2,
                pl.y_mm + pl.height_mm / 2,
                f"{pl.label}\n{mm_to_fractional_inch(long_side)}",
                ha="center", va="center", fontsize=6,
                rotation=90 if pl.height_mm > pl.width_mm * 1.5 else 0,
            )

        figs.append(fig)
        if close:
            plt.close(fig)

    return figs


def render_sheet_diagram(
    result: "Cut2DResult",
    sheet_w_mm: float | None = None,
    sheet_h_mm: float | None = None,
    output_pdf: str | Path | None = None,
    close: bool = True,
) -> list[plt.Figure]:
    """Render one figure per sheet in *result*.

    Parameters
    ----------
    result : Cut2DResult
        Result from :func:`woodshop.cutlist.optimize_2d.optimize_2d`.
    sheet_w_mm, sheet_h_mm : float, optional
        Sheet size.  Defaults to the size recorded on *result*.
    output_pdf : str or Path, optional
        If given, save all sheets as a multi-page PDF.
    close : bool, optional
        Close each figure after drawing, default ``True``.  The figures are
        still returned, but a closed figure cannot be re-saved — pass ``False``
        if you want to keep working with them, and close them yourself.

    Returns
    -------
    list[matplotlib.figure.Figure]
        One figure per sheet.

    Notes
    -----
    Figures are closed by default because generating every size and variant of
    a project opens far more than matplotlib's twenty-figure warning threshold.
    """
    w = sheet_w_mm if sheet_w_mm is not None else result.sheet_w_mm
    h = sheet_h_mm if sheet_h_mm is not None else result.sheet_h_mm
    materials = sorted({p.material for p in result.placements if p.material})
    subtitle = (
        f"{', '.join(materials) or 'sheet goods'} · "
        f"{result.yield_fraction * 100:.0f}% yield"
    )
    figs = _render_layout(
        result.placements, result.sheets_used, w, h, "Sheet", subtitle,
        close=output_pdf is None and close,
    )
    if output_pdf is not None:
        _save_pdf(figs, output_pdf, close)
    return figs


def render_board_diagram(
    plan: "HardwoodPlan",
    output_pdf: str | Path | None = None,
    close: bool = True,
) -> list[plt.Figure]:
    """Render the boards in a hardwood plan, one figure per board.

    This is where most of the cost of a solid-wood project sits, and until now
    it was the one layout with no picture at all.

    Parameters
    ----------
    plan : HardwoodPlan
        Result from :func:`woodshop.cutlist.hardwood.nest_hardwood`.
    output_pdf : str or Path, optional
        If given, save every board as a multi-page PDF.
    close : bool, optional
        Close each figure after drawing, default ``True``.

    Returns
    -------
    list[matplotlib.figure.Figure]
        One figure per board, across every thickness group.
    """
    figs: list[plt.Figure] = []
    for group in plan.groups:
        subtitle = (
            f"{group.label} · {group.stock.typical_width_in:g}\" x "
            f"{group.board_length_mm / 304.8:.0f} ft · "
            f"{group.board_feet:.1f} bd ft"
        )
        figs.extend(
            _render_layout(
                group.nesting.placements,
                group.nesting.sheets_used,
                group.stock.typical_width_in * _IN,
                group.board_length_mm,
                f"{group.label} board",
                subtitle,
                close=output_pdf is None and close,
            )
        )
    if output_pdf is not None:
        _save_pdf(figs, output_pdf, close)
    return figs


def _save_pdf(figs: list[plt.Figure], output_pdf: str | Path, close: bool) -> None:
    """Write *figs* to a multi-page PDF, closing them unless asked not to."""
    from matplotlib.backends.backend_pdf import PdfPages

    with PdfPages(output_pdf) as pdf:
        for fig in figs:
            pdf.savefig(fig)
    if close:
        for fig in figs:
            plt.close(fig)


def cut_sequence(result: "Cut2DResult") -> list[str]:
    """Read a shelf layout back out as an ordered list of saw cuts.

    Shelf layouts are guillotine-cuttable by construction: each shelf is a
    full-width strip, so the stock is crosscut into strips and each strip is
    then ripped into parts.  This turns that property into instructions.

    Parameters
    ----------
    result : Cut2DResult
        A layout produced by the ``"shelf"`` strategy.  Passing a
        ``"maxrects"`` layout will produce nonsense, because those layouts are
        not guillotine-cuttable in the first place.

    Returns
    -------
    list[str]
        Human-readable steps, in order.
    """
    steps: list[str] = []
    for index in range(result.sheets_used):
        on_sheet = [p for p in result.placements if p.sheet_index == index]
        if not on_sheet:
            continue
        steps.append(f"Sheet {index + 1}:")
        shelves: dict[float, list] = {}
        for p in on_sheet:
            shelves.setdefault(round(p.y_mm, 2), []).append(p)
        for y in sorted(shelves):
            row = sorted(shelves[y], key=lambda p: p.x_mm)
            strip_h = max(p.height_mm for p in row)
            steps.append(
                f"  crosscut a {mm_to_fractional_inch(strip_h)} strip "
                f"at {mm_to_fractional_inch(y)} from the edge"
            )
            parts = ", ".join(
                f"{p.label} {mm_to_fractional_inch(p.width_mm)}" for p in row
            )
            steps.append(f"    rip that strip into: {parts}")
    return steps
