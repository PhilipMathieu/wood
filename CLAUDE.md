# Woodshop

Parametric furniture models in build123d, with cut lists, stock nesting,
design checks, and a generated gallery. `NOTES.md` is the working log —
significant modelling sessions get an addendum there.

## Commands

- Tests: `uv run pytest tests/ -q`
- One project: `uv run python projects/<name>.py` (see each module's docstring)
- Gallery: `uv run python scripts/build_gallery.py` (writes `gallery/`,
  gitignored; `--only <slug>` for a single project)

## Pull request conventions

- **Always include the gallery preview for any design a PR modifies.**
  Build it with `scripts/build_gallery.py --only <slug>`, commit each
  project's `hero.png` to `docs/previews/<slug>.png` on the PR branch, and
  embed those images in the PR body (raw.githubusercontent URL for the
  branch). One image per modified gallery project.
