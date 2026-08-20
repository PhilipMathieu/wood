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

- **Always include the gallery preview for any design a PR modifies** — in
  the PR body, never committed with the change.  Build it with
  `scripts/build_gallery.py --only <slug>`, push each project's `hero.png`
  to the images-only `pr-previews` branch (an orphan branch that is never
  merged) under `<pr-branch-name>/<slug>.png`, and embed it in the PR body
  via its raw.githubusercontent URL.  One image per modified gallery
  project.
