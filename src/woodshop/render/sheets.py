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

__all__ = [
    "render_sheet_diagram",
    "render_board_diagram",
    "cut_sequence",
    "save_figures",
]

_IN = 25.4


def save_figures(
    figs: list[plt.Figure],
    outdir: str | Path,
    stem: str,
    ext: str = "png",
    dpi: int = 110,
    close: bool = True,
) -> list[Path]:
    """Write each figure to its own image file and return the paths.

    A multi-page PDF is the right thing to carry to the saw and the wrong
    thing to put on a web page, which cannot embed one.  This is the other
    output.

    Parameters
    ----------
    figs : list of matplotlib.figure.Figure
        Figures to write, in order.
    outdir : str or Path
        Directory to write into.  Created if it does not exist.
    stem : str
        Filename stem.  Files are named ``{stem}-1.{ext}``, ``{stem}-2.{ext}``,
        and so on — one-based, matching the "Sheet 1 of 3" in the titles.
    ext : str, optional
        Image extension, default ``"png"``.  ``"svg"`` also works and stays
        sharp at any zoom.
    dpi : int, optional
        Resolution for raster formats, default 110.
    close : bool, optional
        Close each figure after writing, default ``True``.

    Returns
    -------
    list[Path]
        The files written, in order.
    """
    directory = Path(outdir)
    directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for index, fig in enumerate(figs, start=1):
        path = directory / f"{stem}-{index}.{ext}"
        fig.savefig(path, dpi=dpi, bbox_inches="tight")
        written.append(path)
        if close:
            plt.close(fig)
    return written


#: Above this length-to-width ratio the stock is drawn lying down.
#:
#: A 4x8 sheet stands up fine at 2:1.  A 6" x 10 ft board at 20:1 becomes a
#: ribbon down a page four times taller than it is wide, unreadable at any
#: size a screen or a sheet of paper can hold.
LANDSCAPE_ASPECT: float = 3.0


def _xy(x: float, y: float, landscape: bool) -> tuple[float, float]:
    """Swap a coordinate or size pair when the stock is drawn lying down."""
    return (y, x) if landscape else (x, y)


def _grain_hatch(placement: "Placement", landscape: bool = False) -> str | None:
    """Return a hatch pattern showing which way the grain runs, if it matters.

    The hatch follows the part's grain *as drawn*, so it stays truthful when
    the stock is turned on its side.  Parts with no grain requirement get no
    hatch.
    """
    grain = getattr(placement, "grain_direction", "none")
    if grain == "none":
        return None
    if grain == "length":
        hatch = "|" if placement.rotated else "-"
    else:
        hatch = "-" if placement.rotated else "|"
    if landscape:
        hatch = "-" if hatch == "|" else "|"
    return hatch


def _draw_finished_outline(ax, placement: "Placement", landscape: bool) -> None:
    """Outline the finished part inside its blank, for non-rectangular parts.

    The blank is what the saw cuts and what the layout has to fit; the outline
    is what survives.  Drawing both is the difference between a diagram that
    says "an 18-1/4" square" and one that shows why you bought it.
    """
    shape = getattr(placement, "shape", "rectangular")
    if shape == "rectangular":
        return
    area = placement.yielded_area_mm2
    if area <= 0:
        return
    cx = placement.x_mm + placement.width_mm / 2
    cy = placement.y_mm + placement.height_mm / 2
    style = dict(fill=False, linestyle="--", linewidth=0.9, edgecolor="black")

    if shape == "round":
        # Exact: the finished area is a circle, so it fixes the diameter.
        radius = (area / 3.141592653589793) ** 0.5
        ax.add_patch(mpatches.Circle(_xy(cx, cy, landscape), radius, **style))
        return

    # A turning: a band down the middle of the blank at the mean diameter.
    # The real profile tapers, but mean diameter is what the area fixes, and
    # the point of the outline is "most of this square is shavings".
    along = max(placement.width_mm, placement.height_mm)
    mean_dia = area / along if along else 0.0
    if placement.height_mm >= placement.width_mm:
        x, y = cx - mean_dia / 2, placement.y_mm
        w, h = mean_dia, placement.height_mm
    else:
        x, y = placement.x_mm, cy - mean_dia / 2
        w, h = placement.width_mm, mean_dia
    ax.add_patch(
        mpatches.Rectangle(_xy(x, y, landscape), *_xy(w, h, landscape), **style)
    )


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
    landscape: bool | None = None,
) -> list[plt.Figure]:
    """Draw one figure per sheet or board.

    When *landscape* is ``None`` the orientation follows the stock's aspect
    ratio: long thin boards are turned on their side, sheets are left standing.
    The layout itself is unchanged — only which way up it is drawn.
    """
    figs: list[plt.Figure] = []
    cmap = plt.get_cmap("tab20")

    aspect = panel_h_mm / panel_w_mm if panel_w_mm else 1.0
    if landscape is None:
        landscape = aspect > LANDSCAPE_ASPECT

    width_label = f"width  {mm_to_fractional_inch(panel_w_mm)}"
    length_label = (
        f"length  {mm_to_fractional_inch(panel_h_mm)}  "
        f"(face grain {'↔' if landscape else '↕'})"
    )

    for index in range(n_panels):
        # Keep the drawing a sensible shape whatever the stock's aspect ratio.
        if landscape:
            figsize = (min(16.0, max(7.0, 3.0 * aspect)), 4.0)
        else:
            figsize = (7.0, max(5.0, min(16.0, 7.0 * aspect)))
        fig, ax = plt.subplots(figsize=figsize)
        ax.set_xlim(0, panel_h_mm if landscape else panel_w_mm)
        ax.set_ylim(0, panel_w_mm if landscape else panel_h_mm)
        ax.set_aspect("equal")
        ax.set_title(f"{panel_label} {index + 1} of {n_panels}\n{subtitle}", fontsize=10)
        ax.set_xlabel(length_label if landscape else width_label)
        ax.set_ylabel(width_label if landscape else length_label)
        # Geometry is in mm, but nobody at the saw is measuring this in mm.
        across_step, along_step = 6.0, 12.0
        _inch_ticks(
            ax.set_xticks, ax.set_xticklabels,
            *( (panel_h_mm, along_step) if landscape else (panel_w_mm, across_step) ),
        )
        _inch_ticks(
            ax.set_yticks, ax.set_yticklabels,
            *( (panel_w_mm, across_step) if landscape else (panel_h_mm, along_step) ),
        )

        on_panel = [p for p in placements if p.sheet_index == index]
        for i, pl in enumerate(on_panel):
            ax.add_patch(
                mpatches.Rectangle(
                    _xy(pl.x_mm, pl.y_mm, landscape),
                    *_xy(pl.width_mm, pl.height_mm, landscape),
                    linewidth=1, edgecolor="black",
                    facecolor=cmap(i % 20), alpha=0.55,
                    hatch=_grain_hatch(pl, landscape),
                )
            )
            _draw_finished_outline(ax, pl, landscape)
            long_side = max(pl.width_mm, pl.height_mm)
            drawn_w, drawn_h = _xy(pl.width_mm, pl.height_mm, landscape)
            ax.text(
                *_xy(pl.x_mm + pl.width_mm / 2, pl.y_mm + pl.height_mm / 2, landscape),
                f"{pl.label}\n{mm_to_fractional_inch(long_side)}",
                ha="center", va="center", fontsize=6,
                rotation=90 if drawn_h > drawn_w * 1.5 else 0,
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
    if abs(result.finished_yield_fraction - result.yield_fraction) > 0.005:
        subtitle += f" nested, {result.finished_yield_fraction * 100:.0f}% finished"
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
        # Yields are quoted against the width you *buy*, matching HardwoodPlan.
        # Measuring them against the narrower post-jointing width would put two
        # different numbers for the same quantity on the same page.
        subtitle = (
            f"{group.label} · {group.stock.typical_width_in:g}\" x "
            f"{group.board_length_mm / 304.8:.0f} ft · "
            f"{group.board_feet:.1f} bd ft · "
            f"{group.yield_fraction * 100:.0f}% nested"
        )
        if abs(group.finished_yield_fraction - group.yield_fraction) > 0.005:
            subtitle += f", {group.finished_yield_fraction * 100:.0f}% after the lathe"
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
