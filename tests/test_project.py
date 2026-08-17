"""Tests for woodshop.project — finding projects without special-casing them."""

from __future__ import annotations

import pytest

from woodshop.project import ProjectSpec, discover_projects


@pytest.fixture(scope="module")
def specs() -> list[ProjectSpec]:
    return discover_projects()


def test_the_repository_projects_are_found(specs):
    slugs = {s.slug for s in specs}
    assert {"mysa-bed-queen-faithful", "mysa-bed-queen-plywood", "mysa-nightstand"} <= (
        slugs
    )


def test_a_module_with_no_projects_list_is_skipped_not_an_error(specs):
    """workbench.py builds a cut list with no 3-D model. That is allowed."""
    assert not any(s.slug.startswith("workbench") for s in specs)


def test_every_spec_can_build_and_check(specs):
    for spec in specs:
        assembly = spec.build()
        assert assembly.bounding_box().size.Z > 0
        assert spec.check is not None


def test_specs_come_back_in_a_stable_order(specs):
    assert [s.slug for s in specs] == sorted(s.slug for s in specs)


def test_a_missing_directory_is_an_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="no project directory"):
        discover_projects(tmp_path / "nowhere")


def test_duplicate_slugs_are_refused(tmp_path):
    """Two projects with one slug would overwrite each other's output."""
    (tmp_path / "twins.py").write_text(
        "from woodshop.project import ProjectSpec\n"
        "PROJECTS = [\n"
        "    ProjectSpec(slug='x', name='A', summary='', build=lambda: None),\n"
        "    ProjectSpec(slug='x', name='B', summary='', build=lambda: None),\n"
        "]\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="two projects claim the slug"):
        discover_projects(tmp_path)


def test_private_modules_are_not_imported(tmp_path):
    (tmp_path / "_helper.py").write_text("raise RuntimeError('imported')\n", "utf-8")
    assert discover_projects(tmp_path) == []
