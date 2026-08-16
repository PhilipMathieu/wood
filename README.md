# wood

Code-assisted woodworking. Parametric furniture models in
[build123d](https://build123d.readthedocs.io/), with cut lists, stock
optimisation, and design checks that run before anything gets cut.

## Layout

```
src/woodshop/
  parts.py            Board and Panel — solids that carry cut-list metadata
  lumber.py           nominal -> actual dimension tables, kerf, fraction formatting
  inventory.py        loads stock.yaml: dimensional, hardwood, and sheet stock
  checks.py           design checks (envelope, fit, thickness, deflection)
  cutlist/
    extract.py        walk an assembly into a consolidated list of CutParts
    hardwood.py       nest parts on random-width boards, total board feet
    optimize_1d.py    cutting stock for fixed-width lumber (CP-SAT)
    optimize_2d.py    grain-aware, guillotine-safe sheet nesting
    render.py         CSV / Markdown cut lists and sheet diagrams
  joinery/            dado, rabbet, tenon, mortise, pocket hole
  hardware/           stocked fasteners
projects/
  mysa_bed.py         Chilton Mysa sleigh bed, faithful and plywood variants
  workbench.py        minimal example
stock.yaml            what the shop has on hand
NOTES.md              design journal from the first real project
```

## Getting started

```bash
uv sync
uv run pytest
uv run python projects/mysa_bed.py --size queen --variant both --outdir build
```

That writes a cut list (CSV and Markdown) plus sheet-layout diagrams to
`build/`, and prints the design-check report.

## Modelling conventions

Parts are built in a local frame with **length along +X, width along +Y,
thickness along +Z**, then rotated and positioned into the assembly. Cut
dimensions are stored on the part rather than measured back off its bounding
box, so they survive being placed.

Grain matters twice. On a part, `grain_direction` says which dimension runs
along the grain. On a sheet or a board, the face grain runs along the **height**
(`sheet_h_mm`). A part whose grain runs along its length must lie along that
axis and will not be rotated to make it fit.

All internal geometry is in millimetres. Inches are a presentation format —
`mm_to_fractional_inch` renders them for the cut list.

## Choosing an optimiser

| Stock | Use | Why |
| --- | --- | --- |
| Dimensional lumber | `optimize_1d` | width is fixed, so only length is chosen |
| Hardwood | `nest_hardwood` | random widths; parts are ripped across the board too |
| Sheet goods | `pack_by_material` | per-material sheet sizes and grain |

`optimize_2d` defaults to a shelf packer, whose layouts are always
guillotine-cuttable — crosscut into strips, then rip. `strategy="maxrects"`
packs tighter but generally cannot be cut on a table saw; it is useful as a
lower bound.

## Design checks

`woodshop.checks` returns findings rather than raising, so a design can be
assessed as a whole:

```
INFO  [envelope]  overall width 64" matches published
WARN  [clearance] mattress side clearance is 1" — loose, mattress will slide
INFO  [sheet_fit] slat (62-1/2" x 2-1/2") fits plywood_baltic_birch 48" x 96"
WARN  [thickness] plywood_cherry sold as 3/4" measures 45/64" — a groove cut to
                  3/4" would be 1.19 mm loose
WARN  [deflection] plywood_baltic_birch slat, 30-1/2" span: 4.6 mm midspan
                  deflection (span/168; limit span/240) — 23 slats, or 13/16"
                  stock, would meet it
```

`CheckReport.ok` is `True` when nothing is an `ERROR`.

A material can be stocked in more than one sheet size — Baltic birch is both
5'×5' and 4'×8' — so use `Inventory.best_sheet_for`, which picks the smallest
sheet a part actually fits on rather than guessing from thickness.

**Prices in `stock.yaml` are unverified placeholders.** Quantities, board feet,
and yields are real; dollar totals are not.

See [NOTES.md](NOTES.md) for what these checks caught on the first real project,
and for the list of things still worth building.
