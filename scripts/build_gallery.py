"""Regenerate the project gallery from the models.

One command builds every registered project, renders it, nests its stock, runs
its checks, and writes a static site::

    uv run python scripts/build_gallery.py
    uv run python scripts/build_gallery.py --outdir docs --with-costs
    uv run python scripts/build_gallery.py --single-file --outdir build

Projects are found through :func:`woodshop.project.discover_projects`, which
reads the module-level ``PROJECTS`` list from each module in ``projects/``.  A
new design appears in the gallery by declaring one, and by doing nothing else.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

# Written to files, never shown, and the machine that builds this may have no
# display at all.
matplotlib.use("Agg")

from woodshop.project import discover_projects  # noqa: E402
from woodshop.render.gallery import build_gallery  # noqa: E402


def main() -> None:
    """Parse arguments and write the gallery."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--outdir", type=Path, default=Path("gallery"), help="where to write"
    )
    parser.add_argument(
        "--dpi", type=int, default=110, help="resolution of generated images"
    )
    parser.add_argument(
        "--with-costs",
        action="store_true",
        help=(
            "include cost figures. They are built on unverified placeholder "
            "prices (see issue #3) and are rendered with that warning attached."
        ),
    )
    parser.add_argument(
        "--single-file",
        action="store_true",
        help="write one self-contained HTML file with images inlined",
    )
    parser.add_argument(
        "--only",
        action="append",
        default=None,
        metavar="SLUG",
        help="build only this project; repeatable",
    )
    args = parser.parse_args()

    specs = discover_projects()
    if args.only:
        wanted = set(args.only)
        missing = wanted - {s.slug for s in specs}
        if missing:
            raise SystemExit(
                f"no such project: {sorted(missing)}. "
                f"Available: {sorted(s.slug for s in specs)}"
            )
        specs = [s for s in specs if s.slug in wanted]

    for spec in specs:
        print(f"  building {spec.slug} …")
    index = build_gallery(
        specs,
        outdir=args.outdir,
        dpi=args.dpi,
        show_costs=args.with_costs,
        single_file=args.single_file,
    )
    print(f"\nWrote {index}")
    if not args.with_costs:
        print("Costs omitted. Pass --with-costs to include them (see issue #3).")


if __name__ == "__main__":
    main()
