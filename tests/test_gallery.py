"""Tests for woodshop.render.gallery — the static site built from the models."""

from __future__ import annotations

import dataclasses
import datetime

import matplotlib
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from woodshop.checks import CheckReport, Finding, Severity  # noqa: E402
from woodshop.inventory import Inventory  # noqa: E402
from woodshop.project import ProjectSpec, discover_projects  # noqa: E402
from woodshop.render.gallery import (  # noqa: E402
    build_gallery,
    build_project,
    slugify,
)


@pytest.fixture(autouse=True)
def _no_leaked_figures():
    """Fail the test if the gallery leaves matplotlib figures open."""
    plt.close("all")
    yield
    assert not plt.get_fignums(), "the gallery left figures open"


@pytest.fixture(scope="module")
def nightstand() -> ProjectSpec:
    return next(s for s in discover_projects() if s.slug == "mysa-nightstand")


@pytest.fixture(scope="module")
def bed() -> ProjectSpec:
    return next(s for s in discover_projects() if s.slug == "mysa-bed-queen-plywood")


@pytest.fixture(scope="module")
def fence() -> ProjectSpec:
    """Return the one fence design built from sticks, not ordered as panels."""
    return next(s for s in discover_projects() if s.slug == "cedar-fence-rails")


# ---------------------------------------------------------------------------
# slugify
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected",
    [
        ('plywood_cherry 3/4 (48" x 96")', "plywood-cherry-3-4-48-x-96"),
        ("mysa-nightstand", "mysa-nightstand"),
        ("  spaces  ", "spaces"),
    ],
)
def test_slugify(text, expected):
    assert slugify(text) == expected


# ---------------------------------------------------------------------------
# Building one project
# ---------------------------------------------------------------------------


def test_build_project_derives_everything_from_the_two_callables(nightstand):
    built = build_project(nightstand)
    assert built.parts
    assert built.report.findings
    assert built.hardwood is not None and built.hardwood.boards_needed
    assert built.mass_kg > 0


def test_a_project_with_sheet_goods_gets_a_sheet_plan(bed):
    built = build_project(bed)
    assert built.sheets_used > 0


def test_findings_are_counted_by_severity(nightstand):
    counts = build_project(nightstand).counts()
    assert counts[Severity.INFO] > 0
    assert counts[Severity.ERROR] == 0


# ---------------------------------------------------------------------------
# The site
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def site(tmp_path_factory, nightstand):
    out = tmp_path_factory.mktemp("gallery")
    index = build_gallery([nightstand], outdir=out, dpi=60, generated="2026-01-01")
    plt.close("all")
    return index


def test_an_index_and_a_page_per_project_are_written(site):
    assert site.name == "index.html"
    assert (site.parent / "mysa-nightstand" / "index.html").is_file()


def test_the_index_links_to_the_project(site):
    assert 'href="mysa-nightstand/index.html"' in site.read_text(encoding="utf-8")


def test_pages_are_self_contained(site):
    """A strict host, an offline laptop: nothing may be fetched from elsewhere."""
    for page in site.parent.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        assert "http://" not in text
        assert "<link" not in text
        assert "cdn" not in text.lower()


def test_the_page_carries_the_renders_and_the_downloads(site):
    text = (site.parent / "mysa-nightstand" / "index.html").read_text(encoding="utf-8")
    for name in ("views.png", "boards-1.png", ".step", ".stl", "cutlist.csv"):
        assert name in text
    assert (site.parent / "mysa-nightstand" / "views.png").stat().st_size > 0


def test_the_hero_image_is_not_the_four_view_sheet(site):
    """A card wants one picture of the furniture, not a drawing sheet."""
    directory = site.parent / "mysa-nightstand"
    assert (directory / "hero.png").stat().st_size > 0
    assert 'src="mysa-nightstand/hero.png"' in site.read_text(encoding="utf-8")


def test_findings_are_styled_by_severity(site):
    text = (site.parent / "mysa-nightstand" / "index.html").read_text(encoding="utf-8")
    assert '<li class="info">' in text
    assert '<li class="warn">' in text


def test_the_cut_list_appears_as_a_table(site):
    text = (site.parent / "mysa-nightstand" / "index.html").read_text(encoding="utf-8")
    assert "<table" in text and "<th>shape</th>" in text


def test_the_generation_date_is_on_the_page(site):
    assert "2026-01-01" in site.read_text(encoding="utf-8")


def test_a_nesting_pdf_is_written_alongside_the_images(site):
    assert (site.parent / "mysa-nightstand" / "boards.pdf").stat().st_size > 0


# ---------------------------------------------------------------------------
# Costs — issue #3 says these numbers are invented
# ---------------------------------------------------------------------------


def test_no_dollar_figure_appears_by_default(site):
    for page in site.parent.rglob("*.html"):
        assert "$" not in page.read_text(encoding="utf-8")


def test_costs_come_with_the_caveat_attached(tmp_path, nightstand):
    index = build_gallery(
        [nightstand], outdir=tmp_path, dpi=60, show_costs=True, downloads=False
    )
    plt.close("all")
    text = (index.parent / "mysa-nightstand" / "index.html").read_text(encoding="utf-8")
    assert "$" in text
    assert "placeholder" in text
    assert "Costs on this page are not real" in index.read_text(encoding="utf-8")


def test_no_total_is_printed_without_a_date_or_an_unverified_marker(
    tmp_path, nightstand
):
    """Issue #3: a dollar figure with nothing attached reads as a quote."""
    index = build_gallery(
        [nightstand], outdir=tmp_path, dpi=60, show_costs=True, downloads=False
    )
    plt.close("all")
    for page in index.parent.rglob("*.html"):
        for fragment in page.read_text(encoding="utf-8").split("$")[1:]:
            head = fragment[:120]
            assert "unverified" in head.lower() or "as of" in head, head


def test_dated_prices_are_published_with_their_date_and_a_link(tmp_path, nightstand):
    """What the pages do the day somebody records a real quote."""
    inv = Inventory.load()
    inv.hardwood = [
        dataclasses.replace(
            h,
            price_as_of=datetime.date(2026, 8, 16),
            price_source="O'Brien Hardwoods, phone quote",
            price_url="https://obrienhardwoods.com/",
        )
        for h in inv.hardwood
    ]
    index = build_gallery(
        [nightstand], outdir=tmp_path, dpi=60, show_costs=True, downloads=False,
        inventory=inv,
    )
    plt.close("all")
    text = (index.parent / "mysa-nightstand" / "index.html").read_text(encoding="utf-8")

    assert "Prices are as of 2026-08-16" in text
    assert 'href="https://obrienhardwoods.com/"' in text
    assert "as of 2026-08-16" in text
    # The scare block is data-driven: dated prices have earned their way out.
    assert "Costs on this page are not real" not in text
    assert "UNVERIFIED" not in text


def test_price_provenance_is_published_even_when_costs_are_not(site):
    """The amounts are the embarrassing part; the provenance is the useful part."""
    text = (site.parent / "mysa-nightstand" / "index.html").read_text(encoding="utf-8")
    assert "<h3>Prices</h3>" in text
    assert "carries no price_as_of" in text
    assert "PLACEHOLDER" in text


def test_provenance_findings_do_not_redden_a_buildable_design(nightstand):
    """An undated price is a problem with the quote, not with the joinery."""
    built = build_project(nightstand)
    assert built.report.ok
    assert any(f.severity is Severity.ERROR for f in built.price_report.findings)
    assert built.cost_summary.total is not None
    assert not built.cost_summary.verified


# ---------------------------------------------------------------------------
# Single-file output
# ---------------------------------------------------------------------------


def test_a_single_file_gallery_inlines_its_images(tmp_path, nightstand):
    index = build_gallery(
        [nightstand], outdir=tmp_path, dpi=60, single_file=True,
        generated="2026-01-01",
    )
    plt.close("all")
    text = index.read_text(encoding="utf-8")
    assert "data:image/png;base64," in text
    assert 'src="views.png"' not in text
    # Nothing to link to: the file is meant to travel on its own.
    assert "download>" not in text
    assert not list(index.parent.glob("*/index.html"))


# ---------------------------------------------------------------------------
# Edges
# ---------------------------------------------------------------------------


def test_an_empty_gallery_is_a_bug_not_an_output(tmp_path):
    with pytest.raises(ValueError, match="no projects"):
        build_gallery([], outdir=tmp_path)


def test_a_project_with_no_checks_still_gets_a_page(tmp_path, nightstand):
    bare = ProjectSpec(
        slug="bare",
        name="Bare",
        summary="No checks at all.",
        build=nightstand.build,
        inventory=nightstand.inventory,
    )
    index = build_gallery([bare], outdir=tmp_path, dpi=60, downloads=False)
    plt.close("all")
    text = (index.parent / "bare" / "index.html").read_text(encoding="utf-8")
    assert "defines no checks" in text


def test_findings_are_escaped_not_injected(tmp_path, nightstand):
    def check(assembly, parts):
        return CheckReport([Finding(Severity.WARN, "x", "<script>alert(1)</script>")])

    spec = ProjectSpec(
        slug="escaped",
        name="Escaped",
        summary="",
        build=nightstand.build,
        check=check,
        inventory=nightstand.inventory,
    )
    index = build_gallery([spec], outdir=tmp_path, dpi=60, downloads=False)
    plt.close("all")
    text = (index.parent / "escaped" / "index.html").read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in text
    assert "&lt;script&gt;" in text


# ---------------------------------------------------------------------------
# Browsability
# ---------------------------------------------------------------------------


def test_the_index_is_a_masonry_column_layout(site):
    """A bed is a wide picture and a nightstand a tall one; rows would pad."""
    css = site.read_text(encoding="utf-8")
    assert ".cards { columns:" in css
    assert "break-inside: avoid" in css


def test_the_whole_card_is_the_link(site):
    """A card that looks clickable everywhere must be clickable everywhere."""
    text = site.read_text(encoding="utf-8")
    assert '<a class="card" href="mysa-nightstand/index.html">' in text
    # The title is inside that link rather than being a second, nested one.
    assert "<h3><a " not in text


def test_a_card_says_what_clicking_it_gets_you(site):
    assert "Cut list, stock layouts and checks" in site.read_text(encoding="utf-8")


def test_the_render_opens_full_size(site):
    text = (site.parent / "mysa-nightstand" / "index.html").read_text(encoding="utf-8")
    assert '<a href="views.png"><img src="views.png"' in text


def test_the_single_file_build_gets_the_same_cards(tmp_path, nightstand):
    index = build_gallery(
        [nightstand], outdir=tmp_path, dpi=60, single_file=True,
        generated="2026-01-01",
    )
    plt.close("all")
    text = index.read_text(encoding="utf-8")
    # Cards jump to the section rather than to a file that is not there.
    assert '<a class="card" href="#mysa-nightstand">' in text
    assert 'id="mysa-nightstand"' in text
    # And no card links to a page the single file does not carry.
    assert 'href="mysa-nightstand/index.html"' not in text


# ---------------------------------------------------------------------------
# A project bought by the lineal foot rather than the board foot
# ---------------------------------------------------------------------------


def test_a_dimensional_project_gets_a_lineal_plan_not_a_nesting(fence):
    """Nesting a fence post on a random-width board answers nobody's question."""
    built = build_project(fence)
    assert built.hardwood is None
    assert built.lineal is not None
    assert built.lineal_ft > 250


def test_the_mesh_is_unmatched_because_it_is_not_lumber(fence):
    """Wire off a roll has no nominal size, and saying so beats guessing one."""
    built = build_project(fence)
    assert {part.label for part, _reason in built.lineal.unmatched} == {
        "mesh",
        "gate_mesh",
    }
    assert all("roll" in reason for _part, reason in built.lineal.unmatched)


def test_its_total_is_real_and_dated(fence):
    summary = build_project(fence).cost_summary
    assert summary.verified
    assert summary.oldest_as_of == datetime.date(2026, 8, 17)


def test_its_price_report_names_the_entries_it_buys_not_the_whole_species(fence):
    built = build_project(fence)
    assert len(built.price_report.findings) == len(built.lineal.groups)
    # There are thirty-odd cedar entries in the guide; this design buys four,
    # and the report is about those four.
    assert 1 <= len(built.lineal.groups) <= 6
    assert all(
        f.severity in (Severity.INFO, Severity.WARN)
        for f in built.price_report.findings
    )


def test_the_page_publishes_the_footage_and_the_offcut_allowance(fence, tmp_path):
    build_gallery([fence], outdir=tmp_path, show_costs=True)
    page = (tmp_path / fence.slug / "index.html").read_text(encoding="utf-8")
    assert "lineal ft" in page
    assert "offcuts" in page
    assert "as of 2026-08-17" in page


# ---------------------------------------------------------------------------
# One file, and one file with no document shell
# ---------------------------------------------------------------------------


def test_single_file_is_a_whole_document(fence, tmp_path):
    index = build_gallery([fence], outdir=tmp_path, single_file=True)
    page = index.read_text(encoding="utf-8")
    assert page.startswith("<!doctype html>")
    assert "<body>" in page
    assert "data:image/png;base64," in page


def test_a_fragment_brings_its_style_and_leaves_the_shell_to_its_host(fence, tmp_path):
    index = build_gallery([fence], outdir=tmp_path, fragment=True)
    page = index.read_text(encoding="utf-8")
    for shell in ("<!doctype", "<html", "<head>", "<body>"):
        assert shell not in page.lower()
    assert page.startswith("<title>")
    assert "<style>" in page
    # Still self-contained: a fragment that pointed at sibling files could not
    # be pasted anywhere.
    assert "data:image/png;base64," in page
    assert 'src="views.png"' not in page


def test_a_fragment_needs_no_second_flag(fence, tmp_path):
    """`--fragment` implies `--single-file`; asking for both is not required."""
    index = build_gallery([fence], outdir=tmp_path, fragment=True)
    assert not (tmp_path / fence.slug / "index.html").exists()
    assert index.name == "index.html"


def test_the_theme_resolves_in_all_three_states(fence, tmp_path):
    """System-dark, explicitly dark, and explicitly light on a dark machine."""
    page = build_gallery([fence], outdir=tmp_path, fragment=True).read_text()
    assert '@media (prefers-color-scheme: dark)' in page
    assert ':root:not([data-theme="light"])' in page
    assert ':root[data-theme="dark"]' in page
    # And the body paints its own ground rather than borrowing the host's.
    assert "background: var(--bg)" in page


# ---------------------------------------------------------------------------
# A design that is ordered rather than cut
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def panels() -> ProjectSpec:
    return next(s for s in discover_projects() if s.slug == "cedar-fence-privacy")


def test_a_project_with_an_order_derives_no_buying_plan(panels):
    """A fence bought as panels is not bought in lineal feet."""
    built = build_project(panels)
    assert built.order is not None
    assert built.lineal is None
    assert built.hardwood is None


def test_its_total_names_what_the_catalogue_does_not_price(panels):
    """The one priced line is the stone; the panels above it are all named."""
    summary = build_project(panels).cost_summary
    assert not summary.complete
    assert any("panel" in label for label in summary.unpriced)
    assert [line.label for line in summary.lines] == ['stone 3/4" crushed, bulk']


def test_the_page_lists_pieces_and_says_nothing_is_cut(panels, tmp_path):
    build_gallery([panels], outdir=tmp_path, show_costs=True)
    page = (tmp_path / panels.slug / "index.html").read_text(encoding="utf-8")
    assert "4 panels:" in page or "4 panel" in page
    assert "Nothing in this design is cut" in page or "nothing in this design" in page.lower()
    assert "lineal ft" not in page


def test_a_supplier_unit_is_not_naively_pluralised(panels, tmp_path):
    """"9 eachs" is what a naive pluraliser does to a catalogue's own unit."""
    build_gallery([panels], outdir=tmp_path)
    page = (tmp_path / panels.slug / "index.html").read_text(encoding="utf-8")
    assert "eachs" not in page
    assert "9 each:" in page


def test_a_fence_is_bought_two_ways_at_once(fence):
    """By the foot for its cedar, and by the roll and the box for the rest."""
    built = build_project(fence)
    assert built.lineal is not None
    assert built.extras is not None
    bought = {what for what, _count, _unit in built.extras.lines}
    assert any("mesh" in what for what in bought)
    assert any("hinge" in what for what in bought)
    assert any("crushed" in what for what in bought)


def test_the_mesh_is_not_reported_as_a_gap_once_the_roll_is_in_the_total(fence):
    """The lineal plan is right to exclude it, and wrong to keep saying so."""
    built = build_project(fence)
    assert any("mesh" in label for label in built.lineal.cost_summary.unpriced)
    assert not any("mesh" in label for label in built.cost_summary.unpriced)
    assert built.cost_summary.total > 1000


def test_an_ordered_project_gets_no_extras_because_its_order_holds_them(panels):
    """A panel fence's stone is a line on its order, not a plan beside it."""
    built = build_project(panels)
    assert built.extras is None
    assert built.order is not None
