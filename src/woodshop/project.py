"""A registry so projects can be found and run without being special-cased.

Every script in ``projects/`` used to be an island: its own ``main()``, its own
argparse, its own idea of what to write where.  That is fine when a human runs
one at a time and hopeless for anything that wants to run *all* of them — a
gallery, a regression sweep, a cost comparison.

A project therefore publishes a module-level ``PROJECTS`` list of
:class:`ProjectSpec`, and :func:`discover_projects` finds them.  A spec is
deliberately thin: a name, a slug, and the two callables that matter — build
the model, and check it.  Everything else (cut lists, nesting, renders,
exports) is derived from those two by machinery that already exists, so a new
project gets all of it by declaring four lines.

Example
-------
>>> from woodshop.project import discover_projects
>>> slugs = sorted(spec.slug for spec in discover_projects())
>>> "mysa-nightstand" in slugs
True
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

__all__ = ["ProjectSpec", "discover_projects", "PROJECTS_DIR"]

#: ``projects/`` at the repository root.
PROJECTS_DIR: Path = Path(__file__).resolve().parents[2] / "projects"


@dataclass(frozen=True)
class ProjectSpec:
    """One buildable design, described well enough to run unattended.

    Parameters
    ----------
    slug : str
        URL- and filename-safe identifier, e.g. ``"mysa-bed-queen-faithful"``.
        Also the directory name in a generated gallery, so it must be unique.
    name : str
        Display name.
    summary : str
        One or two sentences describing the piece.
    build : callable
        Takes no arguments, returns a positioned ``build123d.Compound``.
    check : callable, optional
        Takes ``(assembly, parts)`` and returns a
        :class:`woodshop.checks.CheckReport`.  ``None`` if the project has no
        checks of its own.
    species : str, optional
        Primary solid-wood species, used to plan hardwood purchases.
    source_url : str, optional
        Where the design came from, if it is a reproduction.
    inventory : Inventory, optional
        Stock inventory the project was designed against.  ``None`` loads the
        default ``stock.yaml``.
    notes : str, optional
        Free text shown alongside the project.
    tags : list[str], optional
        Free-form labels, e.g. ``["bed", "reproduction"]``.
    """

    slug: str
    name: str
    summary: str
    build: Callable[[], Any]
    check: Callable[[Any, list], Any] | None = None
    species: str = "cherry"
    source_url: str = ""
    inventory: Any = None
    notes: str = ""
    tags: list[str] = field(default_factory=list)


def discover_projects(directory: str | Path | None = None) -> list[ProjectSpec]:
    """Import every module in *directory* and collect the specs they publish.

    A module contributes by defining a module-level ``PROJECTS`` list.  Modules
    without one are skipped rather than treated as an error: ``workbench.py``
    builds a cut list with no 3-D model at all, and there is nothing wrong with
    that — it simply has nothing to show.

    Parameters
    ----------
    directory : str or Path, optional
        Directory of project modules, default :data:`PROJECTS_DIR`.

    Returns
    -------
    list[ProjectSpec]
        Every spec found, sorted by slug so the order does not depend on the
        filesystem.

    Raises
    ------
    FileNotFoundError
        If *directory* does not exist.
    ValueError
        If two projects claim the same slug — they would overwrite each
        other's output.
    """
    root = Path(directory) if directory is not None else PROJECTS_DIR
    if not root.is_dir():
        raise FileNotFoundError(f"no project directory at {root}")

    specs: list[ProjectSpec] = []
    for path in sorted(root.glob("*.py")):
        if path.name.startswith("_"):
            continue
        module = _import_module(path)
        specs.extend(getattr(module, "PROJECTS", []))

    seen: dict[str, str] = {}
    for spec in specs:
        if spec.slug in seen:
            raise ValueError(
                f"two projects claim the slug {spec.slug!r}: "
                f"{seen[spec.slug]} and {spec.name}"
            )
        seen[spec.slug] = spec.name
    return sorted(specs, key=lambda s: s.slug)


def _import_module(path: Path) -> Any:
    """Import a project module by path, without requiring it to be a package.

    ``projects/`` is a directory of scripts, not an installed package, so it is
    loaded from its file location.  The module is registered in
    :data:`sys.modules` under its stem so that repeated discovery — a gallery
    build followed by a test run — reuses the same objects.
    """
    name = path.stem
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError(f"cannot import a project module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module
