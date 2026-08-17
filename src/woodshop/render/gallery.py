"""Turn every registered project into a static site you can actually look at.

Everything this repository produces — renders, nesting diagrams, cut lists,
check reports — lands in a gitignored ``build/`` and lives about as long as the
terminal scrollback.  There is no way to see what the models look like without
cloning the repository and running a script.

This module is the other end of that.  It walks the project registry, builds
each design, and writes a self-contained set of HTML pages: an index of cards,
and one page per project carrying the four views, the cut list, the nesting
diagrams, the check report styled by severity, and links to the STEP and STL.

What it deliberately does not do
--------------------------------
**Publish prices.**  Every price in ``stock.yaml`` is an invented placeholder,
and a dollar figure on a web page reads as researched however the YAML file
labels it.  Costs are omitted unless :func:`build_gallery` is called with
``show_costs=True``, and then every one of them sits inside a warning block.

Example
-------
>>> from woodshop.render.gallery import build_gallery   # doctest: +SKIP
>>> build_gallery(outdir="gallery")                     # doctest: +SKIP
"""

from __future__ import annotations

import base64
import html
import mimetypes
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from woodshop.checks import CheckReport, Severity, estimate_mass_kg
from woodshop.cutlist.extract import CutPart, extract
from woodshop.cutlist.hardwood import HardwoodPlan, nest_hardwood
from woodshop.cutlist.optimize_2d import Cut2DResult, pack_by_material
from woodshop.inventory import Inventory
from woodshop.lumber import mm_to_fractional_inch
from woodshop.project import ProjectSpec, discover_projects
from woodshop.render.export import export_assembly
from woodshop.render.model3d import STANDARD_VIEWS, View, render_assembly
from woodshop.render.sheets import (
    cut_sequence,
    render_board_diagram,
    render_sheet_diagram,
    save_figures,
)
from woodshop.render.tables import render_cut_list

__all__ = ["ProjectBuild", "build_project", "build_gallery", "slugify"]


#: Warning shown wherever a cost appears.  See issue #3.
COST_CAVEAT = (
    "Every price behind these figures is an unverified placeholder invented so "
    "the cost machinery has something to multiply. The quantities are real; "
    "the dollars are not. Do not quote them at anybody."
)

#: Note on the one rendering limitation a woodworker will spot immediately.
PLAN_VIEW_CAVEAT = (
    "Views are painter's-algorithm renders: matplotlib sorts whole triangles "
    "by depth with no depth buffer, so a part can occasionally draw over one "
    "that covers it. The model is right; the picture is approximate."
)


def slugify(text: str) -> str:
    """Reduce a string to something safe as a filename or URL fragment.

    Sheet-goods group keys look like ``plywood_cherry 3/4 (48" x 96")``, in
    which the slash, the quotes and the parentheses are each hostile to a
    filesystem in their own way.

    Parameters
    ----------
    text : str
        Any string.

    Returns
    -------
    str
        Lowercase, alphanumerics and single hyphens only.

    Examples
    --------
    >>> slugify('plywood_cherry 3/4 (48" x 96")')
    'plywood-cherry-3-4-48-x-96'
    """
    return re.sub(r"[^0-9a-zA-Z]+", "-", text).strip("-").lower()


@dataclass
class ProjectBuild:
    """Everything derived from one project, ready to be written out.

    Parameters
    ----------
    spec : ProjectSpec
        The project this came from.
    assembly : build123d.Compound
        The built model.
    parts : list[CutPart]
        The extracted cut list.
    report : CheckReport
        The design-check findings, empty if the project defines no checks.
    hardwood : HardwoodPlan or None
        Solid-stock buying plan, ``None`` if the project uses no solid stock.
    sheets : dict[str, Cut2DResult]
        Sheet-goods nesting, keyed as :func:`pack_by_material` keys them.
    mass_kg : float
        Estimated finished mass.
    """

    spec: ProjectSpec
    assembly: Any
    parts: list[CutPart]
    report: CheckReport
    hardwood: HardwoodPlan | None = None
    sheets: dict[str, Cut2DResult] = field(default_factory=dict)
    mass_kg: float = 0.0

    @property
    def board_feet(self) -> float:
        """Board feet of solid stock this project buys."""
        return 0.0 if self.hardwood is None else self.hardwood.board_feet

    @property
    def sheets_used(self) -> int:
        """Number of sheets this project buys."""
        return sum(r.sheets_used for r in self.sheets.values())

    @property
    def cost(self) -> float | None:
        """Total cost, or ``None`` if anything is unpriced.

        Placeholder prices — see :data:`COST_CAVEAT`.
        """
        total = 0.0 if self.hardwood is None else self.hardwood.cost
        if total is None:
            return None
        return total

    def counts(self) -> dict[Severity, int]:
        """Return the number of findings at each severity."""
        return {
            severity: sum(1 for f in self.report.findings if f.severity is severity)
            for severity in Severity
        }


def build_project(spec: ProjectSpec, inventory: Inventory | None = None) -> ProjectBuild:
    """Build one project and derive everything a page needs from it.

    Parameters
    ----------
    spec : ProjectSpec
        The project to build.
    inventory : Inventory, optional
        Stock inventory.  Falls back to the spec's own, then to ``stock.yaml``.

    Returns
    -------
    ProjectBuild
        Model, cut list, findings, buying plans, and mass.
    """
    inv = inventory or spec.inventory or Inventory.load()
    assembly = spec.build()
    parts = extract(assembly)
    report = spec.check(assembly, parts) if spec.check else CheckReport()

    sheet_materials = {s.material for s in inv.sheet_goods}
    solid = [p for p in parts if p.material not in sheet_materials]
    sheet = [p for p in parts if p.material in sheet_materials]

    hardwood = nest_hardwood(solid, inv, spec.species) if solid else None
    sheets = pack_by_material(sheet, inv) if sheet else {}

    return ProjectBuild(
        spec=spec,
        assembly=assembly,
        parts=parts,
        report=report,
        hardwood=hardwood,
        sheets=sheets,
        mass_kg=estimate_mass_kg(parts),
    )


def build_gallery(
    specs: Iterable[ProjectSpec] | None = None,
    outdir: str | Path = "gallery",
    inventory: Inventory | None = None,
    dpi: int = 110,
    show_costs: bool = False,
    single_file: bool = False,
    downloads: bool = True,
    generated: str | None = None,
) -> Path:
    """Build every project and write a static gallery.

    Parameters
    ----------
    specs : iterable of ProjectSpec, optional
        Projects to include.  Defaults to :func:`discover_projects`.
    outdir : str or Path, optional
        Directory to write into, default ``"gallery"``.  Created if missing.
    inventory : Inventory, optional
        Stock inventory used for every project, overriding their own.
    dpi : int, optional
        Resolution of the generated images, default 110.
    show_costs : bool, optional
        Include cost figures, default ``False``.  When ``True`` every cost is
        rendered inside a block carrying :data:`COST_CAVEAT`, because the
        underlying prices are invented.
    single_file : bool, optional
        Write one self-contained ``index.html`` with every image inlined as a
        ``data:`` URI and no per-project pages, default ``False``.  Useful for
        sending someone the whole thing as one file; large, and no downloads.
    downloads : bool, optional
        Write STEP, STL, and CSV alongside each page, default ``True``.
        Ignored when *single_file* is set.
    generated : str, optional
        Date stamp shown in the footer.  Defaults to today.  A gallery with no
        date is the same trap as a price with no date.

    Returns
    -------
    Path
        The written ``index.html``.

    Raises
    ------
    ValueError
        If no projects are found — an empty gallery is a bug, not an output.
    """
    project_specs = list(specs) if specs is not None else discover_projects()
    if not project_specs:
        raise ValueError(
            "no projects to put in a gallery; a project module must define a "
            "module-level PROJECTS list of ProjectSpec"
        )

    root = Path(outdir)
    root.mkdir(parents=True, exist_ok=True)
    stamp = generated or date.today().isoformat()

    pages: list[tuple[ProjectBuild, dict[str, Any]]] = []
    for spec in project_specs:
        built = build_project(spec, inventory)
        assets = _write_assets(
            built,
            root / spec.slug,
            dpi=dpi,
            downloads=downloads and not single_file,
        )
        pages.append((built, assets))

    if single_file:
        for _, assets in pages:
            _inline_images(assets, root)
        index = root / "index.html"
        index.write_text(
            _render_single_file(pages, show_costs, stamp), encoding="utf-8"
        )
        return index

    for built, assets in pages:
        page = root / built.spec.slug / "index.html"
        page.write_text(
            _render_project_page(built, assets, show_costs, stamp, prefix=""),
            encoding="utf-8",
        )

    index = root / "index.html"
    index.write_text(_render_index(pages, show_costs, stamp), encoding="utf-8")
    return index


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------


def _write_assets(
    built: ProjectBuild,
    directory: Path,
    dpi: int,
    downloads: bool,
) -> dict[str, Any]:
    """Render every image and file for one project; return relative paths."""
    directory.mkdir(parents=True, exist_ok=True)
    slug = built.spec.slug
    assets: dict[str, Any] = {"dir": directory, "boards": [], "sheets": []}

    render_assembly(
        built.assembly,
        output_png=directory / "views.png",
        title=built.spec.name,
        figsize=(12.0, 10.0),
    )
    assets["views"] = "views.png"

    # A card wants one picture of the furniture, not a four-up drawing sheet:
    # at card size the orthographic views are too small to read and only make
    # the card tall enough to push everything else off the screen.
    hero_view = STANDARD_VIEWS[0]
    render_assembly(
        built.assembly,
        output_png=directory / "hero.png",
        # Nameless: a card is already labelled with the project's name, and
        # "Isometric" over the top of it is a caption for nobody.
        views=(View("", hero_view.elev, hero_view.azim),),
        figsize=(6.0, 5.0),
    )
    assets["hero"] = "hero.png"

    if built.hardwood is not None and built.hardwood.boards_needed:
        # The PDF first, because it is the one you carry to the saw; the PNGs
        # exist only because a web page cannot embed a PDF.
        render_board_diagram(built.hardwood, output_pdf=directory / "boards.pdf")
        figs = render_board_diagram(built.hardwood, close=False)
        assets["boards"] = [
            p.name for p in save_figures(figs, directory, "boards", dpi=dpi)
        ]
        assets["boards_pdf"] = "boards.pdf"

    for key, result in built.sheets.items():
        if not result.sheets_used:
            continue
        stem = f"sheets-{slugify(key)}"
        render_sheet_diagram(result, output_pdf=directory / f"{stem}.pdf")
        figs = render_sheet_diagram(result, close=False)
        assets["sheets"].append(
            {
                "key": key,
                "images": [p.name for p in save_figures(figs, directory, stem, dpi=dpi)],
                "pdf": f"{stem}.pdf",
                "steps": cut_sequence(result),
                "result": result,
            }
        )

    render_cut_list(built.parts, output_csv=directory / f"{slug}-cutlist.csv")
    assets["csv"] = f"{slug}-cutlist.csv"

    if downloads:
        export_assembly(
            built.assembly,
            output_step=directory / f"{slug}.step",
            output_stl=directory / f"{slug}.stl",
        )
        assets["step"] = f"{slug}.step"
        assets["stl"] = f"{slug}.stl"
    return assets


def _inline_images(assets: dict[str, Any], root: Path) -> None:
    """Replace image filenames with ``data:`` URIs for the single-file build."""
    directory: Path = assets["dir"]
    assets["views"] = _data_uri(directory / assets["views"])
    assets["hero"] = _data_uri(directory / assets["hero"])
    assets["boards"] = [_data_uri(directory / name) for name in assets["boards"]]
    for group in assets["sheets"]:
        group["images"] = [_data_uri(directory / name) for name in group["images"]]
        group.pop("pdf", None)
    # A single file has nothing to link to: every other artefact still exists
    # on disk beside it, but a document meant to be mailed around should not
    # promise files that will not travel with it.
    for key in ("csv", "step", "stl", "boards_pdf"):
        assets.pop(key, None)


def _data_uri(path: Path) -> str:
    """Return *path* as a ``data:`` URI."""
    mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

_CSS = """
:root {
  --bg: #fbf8f4; --card: #fff; --ink: #241c16; --muted: #6b5d52;
  --rule: #e3d9cd; --accent: #8c4a2f;
  --info: #4a6b8a; --warn: #a8781a; --error: #a33b2a;
  --info-bg: #eef3f8; --warn-bg: #fbf3e0; --error-bg: #fbeceb;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #1a1613; --card: #241f1a; --ink: #ede5db; --muted: #a2948a;
    --rule: #3b332c; --accent: #d08a63;
    --info: #8fb3d4; --warn: #e0b661; --error: #e88a78;
    --info-bg: #1e2831; --warn-bg: #2e2617; --error-bg: #2f1d1a;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 0 1.25rem 4rem; background: var(--bg); color: var(--ink);
  font: 16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
        "Helvetica Neue", Arial, sans-serif;
}
.wrap { max-width: 62rem; margin: 0 auto; }
header { padding: 2.5rem 0 1.5rem; border-bottom: 1px solid var(--rule); }
h1 { margin: 0 0 .35rem; font-size: 1.9rem; letter-spacing: -.02em; }
h2 { margin: 2.5rem 0 .75rem; font-size: 1.25rem; letter-spacing: -.01em; }
h3 { margin: 1.5rem 0 .5rem; font-size: 1rem; }
a { color: var(--accent); }
p.lede, .muted { color: var(--muted); }
/* Masonry, not a grid. A bed is a wide picture and a nightstand is a tall one;
   a row-aligned grid pads every card to the tallest in its row and the page
   fills with empty card. CSS columns let each card take the height it needs. */
.cards { columns: 21rem auto; column-gap: 1.25rem; margin-top: 1.75rem; }
.card {
  background: var(--card); border: 1px solid var(--rule); border-radius: 10px;
  overflow: hidden; display: block; margin: 0 0 1.25rem;
  /* Without this a card is sliced in half across a column boundary. */
  break-inside: avoid; -webkit-column-break-inside: avoid;
  color: inherit; text-decoration: none;
  transition: border-color .15s ease, transform .15s ease;
}
/* The whole card is the link, not just the title — a card that looks
   clickable everywhere and is clickable only on six words is worse than one
   that does not look clickable at all. */
a.card:hover, a.card:focus-visible {
  border-color: var(--accent); transform: translateY(-2px);
}
a.card:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.card img { width: 100%; height: auto; display: block; background: #fff; }
.card .body { padding: .9rem 1rem 1.1rem; }
.card h3 { margin: 0 0 .3rem; color: var(--accent); }
.card p { margin: .25rem 0 .6rem; font-size: .92rem; color: var(--muted); }
.card .more { font-size: .82rem; color: var(--accent); display: block;
              margin-top: .55rem; }
@media (prefers-reduced-motion: reduce) {
  .card { transition: none; }
  a.card:hover, a.card:focus-visible { transform: none; }
}
.stats { display: flex; flex-wrap: wrap; gap: .4rem; font-size: .78rem; }
.stat {
  border: 1px solid var(--rule); border-radius: 999px; padding: .1rem .55rem;
  color: var(--muted); white-space: nowrap;
}
.badge {
  border-radius: 999px; padding: .1rem .55rem; font-size: .78rem;
  font-weight: 600; white-space: nowrap;
}
.badge.info  { background: var(--info-bg);  color: var(--info); }
.badge.warn  { background: var(--warn-bg);  color: var(--warn); }
.badge.error { background: var(--error-bg); color: var(--error); }
figure { margin: 1rem 0; }
figure img { width: 100%; height: auto; border: 1px solid var(--rule);
             border-radius: 8px; background: #fff; }
/* A 6" x 10 ft board is a very tall, very thin picture. Bound its height and
   let the width follow, or one board fills three screens. */
figure.layout img { width: auto; max-width: 100%; max-height: 34rem; }
figure.layout { text-align: center; }
figcaption { font-size: .82rem; color: var(--muted); margin-top: .4rem; }
.scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }
table { border-collapse: collapse; font-size: .9rem; min-width: 34rem; }
th, td { text-align: left; padding: .35rem .7rem; border-bottom: 1px solid var(--rule); }
th { font-weight: 600; white-space: nowrap; }
td:nth-child(4) { text-align: right; }
pre { background: var(--card); border: 1px solid var(--rule); border-radius: 8px;
      padding: .8rem 1rem; overflow-x: auto; font-size: .84rem; }
ul.findings { list-style: none; padding: 0; margin: .5rem 0; }
ul.findings li {
  border-left: 3px solid var(--rule); padding: .45rem .8rem; margin-bottom: .4rem;
  border-radius: 0 6px 6px 0; font-size: .92rem;
}
li.info  { border-left-color: var(--info);  background: var(--info-bg); }
li.warn  { border-left-color: var(--warn);  background: var(--warn-bg); }
li.error { border-left-color: var(--error); background: var(--error-bg); }
li .code { font-weight: 600; margin-right: .4rem; }
.caveat {
  border: 1px solid var(--warn); background: var(--warn-bg); color: var(--ink);
  border-radius: 8px; padding: .8rem 1rem; margin: 1rem 0; font-size: .9rem;
}
.downloads { display: flex; flex-wrap: wrap; gap: .6rem; margin: .75rem 0; }
.downloads a {
  border: 1px solid var(--rule); border-radius: 8px; padding: .35rem .8rem;
  text-decoration: none; font-size: .88rem;
}
footer { margin-top: 3rem; padding-top: 1.25rem; border-top: 1px solid var(--rule);
         font-size: .85rem; color: var(--muted); }
"""


def _page(title: str, body: str) -> str:
    """Wrap *body* in a complete, self-contained HTML document."""
    return (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(title)}</title>\n"
        f"<style>{_CSS}</style>\n</head>\n<body>\n"
        f'<div class="wrap">\n{body}\n</div>\n</body>\n</html>\n'
    )


def _footer(stamp: str) -> str:
    """Return the footer, which always carries the generation date."""
    return (
        f'<footer><p>Generated {html.escape(stamp)} by '
        "<code>uv run python scripts/build_gallery.py</code>. "
        "Every dimension comes from the models in this repository; nothing on "
        "these pages is typed in by hand.</p></footer>"
    )


def _severity_badges(built: ProjectBuild) -> str:
    """Return the ERROR/WARN badges for a card, or an all-clear."""
    counts = built.counts()
    out = []
    for severity, label in ((Severity.ERROR, "error"), (Severity.WARN, "warning")):
        n = counts[severity]
        if n:
            plural = "" if n == 1 else "s"
            out.append(
                f'<span class="badge {severity.value}">{n} {label}{plural}</span>'
            )
    if not out:
        out.append('<span class="badge info">checks clear</span>')
    return "".join(out)


def _card_stats(built: ProjectBuild, show_costs: bool) -> str:
    """Return the small pill statistics shown on a card."""
    stats = []
    if built.board_feet:
        stats.append(f"{built.board_feet:.0f} bd ft {built.spec.species}")
    if built.sheets_used:
        plural = "" if built.sheets_used == 1 else "s"
        stats.append(f"{built.sheets_used} sheet{plural}")
    stats.append(f"{len(built.parts)} distinct parts")
    stats.append(f"{built.mass_kg:.0f} kg")
    if show_costs and built.cost is not None:
        stats.append(f"${built.cost:,.0f} (placeholder)")
    return "".join(f'<span class="stat">{html.escape(s)}</span>' for s in stats)


def _render_index(
    pages: list[tuple[ProjectBuild, dict[str, Any]]],
    show_costs: bool,
    stamp: str,
) -> str:
    """Render the index page."""
    cards = [
        _card(built, f"{built.spec.slug}/index.html", f"{built.spec.slug}/", assets,
              show_costs)
        for built, assets in pages
    ]

    caveat = "" if show_costs else _no_cost_note()
    body = (
        "<header><h1>Woodshop</h1>"
        '<p class="lede">Parametric furniture, cut lists that describe what you '
        "buy, and design checks that run before anything is cut. Every page "
        "below is generated from the model — the pictures and the numbers "
        "cannot disagree. Pick a piece to see its cut list, stock layouts and "
        "design checks.</p></header>"
        f"{_cost_caveat() if show_costs else caveat}"
        f'<div class="cards">{"".join(cards)}</div>'
        f"{_footer(stamp)}"
    )
    return _page("Woodshop gallery", body)


def _card(
    built: ProjectBuild,
    href: str,
    image_prefix: str,
    assets: dict[str, Any],
    show_costs: bool,
) -> str:
    """Render one index card, clickable over its whole area.

    *image_prefix* is prepended to the hero filename, and is empty when the
    image is already an inlined ``data:`` URI.
    """
    hero = assets["hero"]
    src = hero if hero.startswith("data:") else f"{image_prefix}{hero}"
    return (
        f'<a class="card" href="{href}">'
        f'<img src="{src}" alt="{html.escape(built.spec.name)}" loading="lazy">'
        f'<div class="body"><h3>{html.escape(built.spec.name)}</h3>'
        f"<p>{html.escape(built.spec.summary)}</p>"
        f'<div class="stats">{_card_stats(built, show_costs)}'
        f"{_severity_badges(built)}</div>"
        f'<span class="more">Cut list, stock layouts and checks &rarr;</span>'
        f"</div></a>"
    )


def _render_single_file(
    pages: list[tuple[ProjectBuild, dict[str, Any]]],
    show_costs: bool,
    stamp: str,
) -> str:
    """Render every project into one self-contained document."""
    # Even in one document the cards earn their place: they are the contents
    # page, and each jumps to its section instead of to another file.
    cards = [
        _card(built, f"#{built.spec.slug}", "", assets, show_costs)
        for built, assets in pages
    ]
    sections = [
        _render_project_body(built, assets, show_costs, heading_level=2)
        for built, assets in pages
    ]
    body = (
        "<header><h1>Woodshop</h1>"
        '<p class="lede">Every registered project, in one file: renders, cut '
        "lists, nesting layouts and design checks, all generated from the "
        "models.</p></header>"
        f"{_cost_caveat() if show_costs else _no_cost_note()}"
        f'<div class="cards">{"".join(cards)}</div>'
        f"{''.join(sections)}"
        f"{_footer(stamp)}"
    )
    return _page("Woodshop gallery", body)


def _render_project_page(
    built: ProjectBuild,
    assets: dict[str, Any],
    show_costs: bool,
    stamp: str,
    prefix: str,
) -> str:
    """Render one project's own page."""
    body = (
        f'<header><p class="muted"><a href="{prefix}../index.html">'
        "&larr; all projects</a></p>"
        f"<h1>{html.escape(built.spec.name)}</h1>"
        f'<p class="lede">{html.escape(built.spec.summary)}</p></header>'
        f"{_render_project_body(built, assets, show_costs, heading_level=2, show_heading=False)}"
        f"{_footer(stamp)}"
    )
    return _page(built.spec.name, body)


def _render_project_body(
    built: ProjectBuild,
    assets: dict[str, Any],
    show_costs: bool,
    heading_level: int,
    max_shown: int = 4,
    show_heading: bool = True,
) -> str:
    """Render the shared body of a project, at a given heading level."""
    h = f"h{heading_level}"
    sub = f"h{heading_level + 1}"
    spec = built.spec
    out: list[str] = []

    if show_heading:
        out.append(f"<{h} id=\"{spec.slug}\">{html.escape(spec.name)}</{h}>")

    if spec.source_url:
        out.append(
            f'<p class="muted">Reproduction of <a href="{html.escape(spec.source_url)}"'
            f">{html.escape(spec.source_url)}</a></p>"
        )
    if spec.notes:
        out.append(f'<p class="muted">{html.escape(spec.notes)}</p>')

    views = assets["views"]
    img = (
        f'<img src="{views}" alt="{html.escape(spec.name)} — four views" '
        f'loading="lazy">'
    )
    # Click the drawing to see it at full size — unless it is already inlined,
    # in which case there is no separate file to open.
    if not views.startswith("data:"):
        img = f'<a href="{views}">{img}</a>'
    out.append(
        f"<figure>{img}"
        f"<figcaption>{html.escape(PLAN_VIEW_CAVEAT)}</figcaption></figure>"
    )

    out.append(_downloads(assets))
    out.append(f"<{sub}>Design checks</{sub}>")
    out.append(_render_findings(built.report))

    out.append(f"<{sub}>Cut list</{sub}>")
    out.append(
        '<p class="muted">Dimensions are the blank to cut from a board, not '
        "the finished part. For a rectangle those are the same thing; for "
        "anything round or turned they are not, and the blank is the one you "
        "can buy.</p>"
    )
    out.append(_render_cut_table(built.parts))

    out.append(f"<{sub}>Materials</{sub}>")
    out.append(_render_materials(built, show_costs))

    if built.hardwood is not None and assets["boards"]:
        out.append(f"<{sub}>Board layout</{sub}>")
        out.append(_layout_figures(assets["boards"], "board nesting",
                                   assets.get("boards_pdf"), max_shown))

    for group in assets["sheets"]:
        out.append(f"<{sub}>Sheet layout — {html.escape(group['key'])}</{sub}>")
        out.append(_layout_figures(group["images"], "sheet nesting",
                                   group.get("pdf"), max_shown))
        if group["steps"]:
            steps = html.escape("\n".join(group["steps"]))
            out.append(f"<pre>{steps}</pre>")

    return "".join(out)


def _layout_figures(
    sources: list[str],
    alt: str,
    pdf: str | None,
    max_shown: int,
) -> str:
    """Render nesting diagrams, saying plainly how many were left out.

    Sixteen near-identical boards down one page is not information.  Showing a
    few and linking the rest is — but a silent truncation would read as "this
    is all of it", which is exactly the wrong impression when the number of
    boards is the cost of the project.
    """
    shown = sources[:max_shown]
    out = [
        f'<figure class="layout"><img src="{src}" alt="{alt}" loading="lazy">'
        "</figure>"
        for src in shown
    ]
    dropped = len(sources) - len(shown)
    if dropped:
        rest = (
            f' <a href="{pdf}" download>All {len(sources)} as a PDF</a>.'
            if pdf
            else ""
        )
        out.append(
            f'<p class="muted">Showing {len(shown)} of {len(sources)} — the '
            f"rest are the same layout again.{rest}</p>"
        )
    return "".join(out)


def _downloads(assets: dict[str, Any]) -> str:
    """Return the download links, or nothing if none were written."""
    links = [
        (assets.get("step"), "STEP"),
        (assets.get("stl"), "STL"),
        (assets.get("csv"), "Cut list (CSV)"),
    ]
    present = [
        f'<a href="{href}" download>{label}</a>' for href, label in links if href
    ]
    if not present:
        return ""
    return f'<div class="downloads">{"".join(present)}</div>'


def _render_findings(report: CheckReport) -> str:
    """Render a check report as a severity-styled list."""
    if not report.findings:
        return '<p class="muted">This project defines no checks.</p>'
    items = [
        f'<li class="{f.severity.value}"><span class="code">[{html.escape(f.code)}]'
        f"</span>{html.escape(f.message)}</li>"
        for f in report.findings
    ]
    return f'<ul class="findings">{"".join(items)}</ul>'


def _render_cut_table(parts: list[CutPart]) -> str:
    """Render the cut list as an HTML table that scrolls rather than squashes."""
    df = render_cut_list(parts)
    table = df.to_html(index=False, border=0, escape=True)
    return f'<div class="scroll">{table}</div>'


def _render_materials(built: ProjectBuild, show_costs: bool) -> str:
    """Render the buying summary: board feet by thickness, sheets by size."""
    rows: list[str] = []
    if built.hardwood is not None:
        for group in built.hardwood.groups:
            cost = ""
            if show_costs and group.cost is not None:
                cost = f" — ${group.cost:,.0f} at placeholder rates"
            rows.append(
                f"<li>{html.escape(group.label)}: {group.boards_needed} board(s) of "
                f'{group.stock.typical_width_in:g}" x '
                f"{group.board_length_mm / 304.8:.0f} ft, "
                f"{group.board_feet:.1f} bd ft{html.escape(cost)}</li>"
            )
        for label, n, stave_w in built.hardwood.glue_ups:
            rows.append(
                f"<li>{html.escape(label)}: edge-glued from {n} staves of "
                f"{html.escape(mm_to_fractional_inch(stave_w))}</li>"
            )
    for key, result in built.sheets.items():
        if result.sheets_used:
            rows.append(
                f"<li>{html.escape(key)}: {result.sheets_used} sheet(s), "
                f"{result.yield_fraction * 100:.0f}% nested</li>"
            )

    yields = ""
    if built.hardwood is not None and built.hardwood.boards_needed:
        plan = built.hardwood
        yields = (
            f'<p class="muted">Nesting claims {plan.yield_fraction * 100:.0f}% of '
            f"the boards bought; {plan.finished_yield_fraction * 100:.0f}% of "
            "them ends up in a finished part. The gap between those two numbers "
            "is what the lathe and the bandsaw take.</p>"
        )
    if not rows:
        return '<p class="muted">Nothing to buy.</p>'
    return f'<ul>{"".join(rows)}</ul>{yields}'


def _cost_caveat() -> str:
    """Return the block that must accompany any published cost."""
    return (
        f'<div class="caveat"><strong>Costs on this page are not real.</strong> '
        f"{html.escape(COST_CAVEAT)}</div>"
    )


def _no_cost_note() -> str:
    """Return the note explaining why no costs appear."""
    return (
        '<p class="muted">Quantities are shown; costs are not. The prices in '
        "<code>stock.yaml</code> are placeholders nobody has verified, and a "
        "dollar figure on a web page reads as researched however the source "
        "file labels it.</p>"
    )
