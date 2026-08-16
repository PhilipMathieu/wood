# wood

Code-assisted woodworking. Parametric furniture models in
[build123d](https://build123d.readthedocs.io/), with cut lists, stock
optimisation, and design checks that run before anything gets cut.

## Layout

```
src/woodshop/
  parts.py            Board, Panel, Disc, Turning — solids that carry cut-list metadata
  lumber.py           nominal -> actual dimension tables, kerf, fraction formatting
  inventory.py        loads stock.yaml: dimensional, hardwood, and sheet stock
  checks.py           design checks (envelope, fit, thickness, deflection, material, tipping)
  project.py          the registry that makes projects discoverable
  cutlist/
    extract.py        walk an assembly into a consolidated list of CutParts
    hardwood.py       nest parts on random-width boards, total board feet
    optimize_1d.py    cutting stock for fixed-width lumber (CP-SAT)
    optimize_2d.py    grain-aware, guillotine-safe sheet nesting
  render/
    tables.py         CSV / Markdown cut lists
    sheets.py         sheet and board nesting diagrams, cut order
    model3d.py        shaded 3-D views of an assembly
    export.py         STEP / STL export, ocp_vscode preview
    gallery.py        a static site built from every registered project
  joinery/            dado, rabbet, tenon, mortise, pocket hole
  hardware/           stocked fasteners
projects/
  mysa_bed.py         Chilton Mysa sleigh bed, faithful and plywood variants
  mysa_nightstand.py  Chilton Mysa nightstand — round top, three turned legs
  workbench.py        minimal example
scripts/
  build_gallery.py    one command to regenerate the gallery
stock.yaml            what the shop has on hand
NOTES.md              design journal from the first real project
```

## Getting started

```bash
uv sync
uv run pytest
uv run python projects/mysa_bed.py --size queen --variant both --outdir build
uv run python projects/mysa_nightstand.py --outdir build
```

That writes to `build/`:

| File | What it is |
| --- | --- |
| `*_cutlist.csv` / `.md` | the cut list |
| `*.png` | isometric, front, side and plan views |
| `*.step` / `*.stl` | CAD export, for a real viewer |
| `*_boards.pdf` | hardwood nesting, one page per board |
| `*_sheets.pdf` | sheet-goods nesting, one page per sheet |
| `*_cutorder.txt` | crosscut-then-rip sequence for each sheet |

and prints the design-check report.

Look at the PNG. Everything else in this project *measures* the model; the
views are the only step that would catch a part rotated about the wrong axis
or buried inside another one.

## The gallery

```bash
uv run python scripts/build_gallery.py --outdir gallery
open gallery/index.html
```

One command builds every registered project, renders it, nests its stock, runs
its checks, and writes a static site: an index of cards and a page per project
with the four views, the cut list, the nesting layouts, the check report styled
by severity, and the STEP/STL/CSV to download. The pages are self-contained —
no CDN, no external stylesheet — so they work from a file:// URL, from a USB
stick, or from GitHub Pages. `--single-file` inlines every image into one HTML
document you can mail to somebody.

Costs are **omitted by default**, because the prices in `stock.yaml` are
invented. `--with-costs` puts them back with that warning attached.

A project joins the gallery by publishing a module-level `PROJECTS` list:

```python
PROJECTS = [ProjectSpec(slug="mysa-nightstand", name="Mysa nightstand",
                        summary="…", build=stand.build, check=stand.check)]
```

`discover_projects()` finds it. Modules without one — `workbench.py` builds a
cut list and no geometry — are skipped rather than treated as an error.

## Modelling conventions

Parts are built in a local frame with **length along +X, width along +Y,
thickness along +Z**, then rotated and positioned into the assembly. Round
parts (`Disc`, `Turning`) are built about the **lathe axis, which runs along
+Z**. Cut dimensions are stored on the part rather than measured back off its
bounding box, so they survive being placed.

### Stock size versus finished size

Every part carries both. `length_mm`/`width_mm`/`thickness_mm` are the
**finished** part; `stock_length_mm`/`stock_width_mm`/`stock_thickness_mm` are
the **blank** you cut from a board. For a rectangle they coincide apart from a
trim allowance. For a round or turned part they do not, and it is the blank
that goes on the cut list — you cannot buy an 18" circle, you buy an 18-1/4"
square, and nobody can hand you a board 1-1/2" tapering to 1".

That distinction is also why there are two yield figures. `yield_fraction`
answers "how well did I nest?"; `finished_yield_fraction` answers "how much of
the board ends up in the furniture?". They are identical for a project made of
rectangles, and the gap between them is what the lathe and the bandsaw take.

A boolean cut — a mortise, a rabbet, a foot sawn level — returns anonymous
geometry and drops the part out of the cut list without saying so. `retag()`
puts the metadata back:

```python
leg = retag(leg - below_the_floor, like=leg, notes="foot sawn level")
```

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
ERROR [material]  leg is turned but specified in plywood_baltic_birch: sheet
                  goods have no long grain running the length of a spindle
WARN  [stability] 4.8 kg on 3 legs: a load of 3.6 kg (8 lb) on the rim between
                  two legs tips it
```

Most checks compare a number against a number. `check_material_suitability`
compares a **material against an operation**, which is the question a cut list
cannot ask on its own: a 3/4" Baltic birch slat and a 3/4" Baltic birch turned
leg have identical rows, and only one of them is possible.

`CheckReport.ok` is `True` when nothing is an `ERROR`.

A material can be stocked in more than one sheet size — Baltic birch is both
5'×5' and 4'×8' — so use `Inventory.best_sheet_for`, which picks the smallest
sheet a part actually fits on rather than guessing from thickness.

**Prices in `stock.yaml` are unverified placeholders.** Quantities, board feet,
and yields are real; dollar totals are not.

## Known limitation of the 3-D views

matplotlib has no depth buffer, so nearly-coincident surfaces sort
unreliably — in the plan view the centre rail appears to lie over the slats it
actually sits beneath. Use the STEP or STL export in a real viewer when that
matters. `test_centre_rail_sits_below_the_slats` pins the geometry so the
artifact cannot be mistaken for a model error.

See [NOTES.md](NOTES.md) for what these checks caught on the first real project,
and for the list of things still worth building.
