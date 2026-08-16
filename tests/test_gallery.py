"""Tests for woodshop.render.gallery — the static site built from the models."""

from __future__ import annotations

import matplotlib
import pytest

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from woodshop.checks import CheckReport, Finding, Severity  # noqa: E402
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
