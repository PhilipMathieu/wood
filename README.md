# wood

Code-assisted woodworking. Parametric furniture models in
[build123d](https://build123d.readthedocs.io/), with cut lists, stock
optimisation, and design checks that run before anything gets cut.

## Layout

```
src/woodshop/
  parts.py            Board, Panel, Disc, Turning, Pole, ShapedBoard — solids
                      that carry cut-list metadata
  lumber.py           nominal -> actual dimension tables, kerf, fraction formatting
  inventory.py        loads stock.yaml: dimensional, hardwood, and sheet stock,
                      each price carrying the date and source behind it
  pricing.py          PriceLine and CostSummary — a total that cannot print
                      without saying how old its rates are
  checks.py           design checks (envelope, fit, thickness, deflection,
                      material, tipping, price provenance)
  project.py          the registry that makes projects discoverable
  cutlist/
    extract.py        walk an assembly into a consolidated list of CutParts
    hardwood.py       nest parts on random-width boards, total board feet
    dimensional.py    buy nominal-size stock by the lineal foot, when the
                      supplier prices it and publishes no lengths
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
  mysa_bed.py         Chilton Mysa sleigh bed — geometry measured off the
                      manufacturer's 360 viewer; faithful and plywood variants
  mysa_nightstand.py  Chilton Mysa nightstand — round top, three turned legs
  cedar_fence.py      38 ft of white cedar fence at 4 ft, in four styles —
                      picket, board-on-board, horizontal, and peeled logs with
                      black coated mesh — plus two 10 ft gated sections
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
uv run python projects/cedar_fence.py --style all --outdir build
uv run python projects/cedar_fence.py --compare     # the three styles, priced
uv run python projects/cedar_fence.py --variants    # every cedar Lumbery stocks
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
invented. `--with-costs` puts them back — each amount tagged with the date its
rate was quoted, or marked unverified when there is no date to tag it with.
Provenance is published either way: every project page carries a *Prices*
section naming each material it buys and where that material's price came
from, which stays useful after somebody records a real one.

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
+Z**. A `ShapedBoard` carries a closed 2-D profile in X–Y and extrudes it along
+Z — and takes profile-X as the part's *length*, so a leg's profile is drawn
with its **height** along X, because that is the way the grain runs. Cut dimensions are stored on the part rather than measured back off its
bounding box, so they survive being placed.

### Round stock: bought round, or made round

`Turning` is a spindle: a square blank with most of it turned away, priced as
the square. `Pole` is a log: you buy the round thing by the foot, and the only
work done to it is a cut at each end. They draw identically and could not be
less alike on an order, so they are different classes and different `shape`
values — and `estimate_mass_kg` knows a solid of revolution is π/4 of the box
it sits in, which is 27% of a fence post.

### Rough sawn versus dressed, and what a board covers

`NOMINAL_TO_ACTUAL` holds *dressed* sizes: a 1x6 is 3/4" x 5-1/2". Rough sawn
stock is close to full dimension, and half of Lumbery's cedar list is rough
sawn, so `rough_dimensions_mm` is the table that describes it — a rough 1x6 is
about a full 1" x 6". `Board(..., rough=True)` sizes a part from it. Laid out
from the dressed table a fence is 3/8" short in every bay and 1/4" thin in
every board.

Milled stock adds a third width. A 1x6 tongue-and-groove board is 5-1/2" across
the face and shows about 5-1/8": the rest is the tongue, and it lives inside the
next board. `Board(..., covers_mm=...)` models the part at what it **covers**,
records what it **measures** as `face_width_mm`, and keeps buying it by its
**nominal** size — three different numbers for one board, and a layout that uses
the wrong one is out by a board in forty. What a profile covers is not published
by anybody, so the assumption lives in the project that makes it
(`cedar_fence.ASSUMED_COVERAGE_IN`) and every design that uses it gets a `WARN`
naming the number.

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
| Dimensional lumber, lengths known | `optimize_1d` | width is fixed, so only length is chosen |
| Dimensional lumber, lengths unpublished | `plan_dimensional` | a rate per lineal foot buys material; it does not buy sticks |
| Hardwood | `nest_hardwood` | random widths; parts are ripped across the board too |
| Sheet goods | `pack_by_material` | per-material sheet sizes and grain |
| Sold by the roll or the bundle | neither | it is not lumber; `plan_dimensional` names it and hands it back |

`plan_dimensional` is the answer to a supplier who prices twenty-eight cedar
profiles and lists no lengths at all. It groups the cut list by the *entry each
part actually buys* — which is why a `Board` carries `grade` and
`stock_profile` as well as a nominal size, since rough sawn 1x6 is $2.30/LF in
STK and $1.30 in low grade — totals the lineal feet, adds a stated offcut
allowance, and prices it in the unit the supplier printed. What it deliberately
does not do is invent an 8 ft stick so that a cutting-stock solver has
something to chew on: `uv run python projects/cedar_fence.py --assume-lengths
8,10,12` will do that, and labels every number it produces as resting on your
assumption.

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
ERROR [price]     cherry 4/4 is priced per bd ft but carries no price_as_of:
                  treat it as invented until it is replaced by a quote with a
                  date on it
WARN  [price]     plywood_birch 3/4 (48" x 96") has no price in stock.yaml —
                  any total that includes it is a total with a hole in it
```

Most checks compare a number against a number. `check_material_suitability`
compares a **material against an operation**, which is the question a cut list
cannot ask on its own: a 3/4" Baltic birch slat and a 3/4" Baltic birch turned
leg have identical rows, and only one of them is possible.
`check_price_provenance` compares a **price against a date**, which is the
question a price list cannot ask on its own: board feet are measured and stay
true, dollars are quoted and go off.

`CheckReport.ok` is `True` when nothing is an `ERROR`.

A material can be stocked in more than one sheet size — Baltic birch is both
5'×5' and 4'×8' — so use `Inventory.best_sheet_for`, which picks the smallest
sheet a part actually fits on rather than guessing from thickness.

## Prices

Every price in `stock.yaml` carries its own provenance:

```yaml
- species: white_cedar
  nominal: "1x6"
  grade: STK
  profile: rough sawn
  price_per_lineal_ft: 2.30
  price_as_of: 2026-08-17              # ISO date, required whenever a price is set
  price_source: "Lumbery, White Cedar Lumber Pricing Guide"
  price_url: "https://lumbery-me.com/pricing-guide-featuring-cedar-shiplap-siding/"
```

Softwood is quoted per piece by some yards and per lineal foot by others, so
an entry carries `price_per_piece` (with `price_length_ft`, because a price
per stick means nothing without the length) **or** `price_per_lineal_ft` —
whichever the supplier printed, never both. `grade` and `profile` are what
separate two entries of the same nominal size at very different prices: a
rough sawn 1x6 in STK is $2.30/LF and the same board in low grade is $1.30.

A price with no `price_as_of` is *unverified*, not trusted:
`check_price_provenance` reports it as an `ERROR`, and every total built from
it prints `UNVERIFIED — placeholder prices`. That is why the placeholders can
stay in the file — they are visibly placeholders — rather than having to be
deleted before anything else can be built.

`woodshop.pricing` is what makes that stick. A price never travels as a bare
float: it is a `PriceLine` (quantity × rate, plus where the rate came from and
when), and `CostSummary` refuses to render a total without the date behind it.
A summary totals what it can and *names* what it cannot, so one unpriced
material no longer drops the whole cost line:

```
cherry 4/4     8 boards of 7" x 8 ft  (37.3 bd ft, $467 (unverified))
(!) plywood_birch 3/4 (48" x 96") has no price in stock.yaml — it is missing
    from the total below, not free
total          8 boards, 37.3 bd ft, $467 (UNVERIFIED — placeholder prices;
               excludes unpriced plywood_birch 3/4 (48" x 96")), 47% yield
```

### Which prices are real

| Stock | Prices | Source |
| --- | --- | --- |
| white cedar — all 34 lines of the guide: 30 board profiles/grades, 3 shake grades, lattice | **real** shelf prices, per lineal foot, per piece, per bundle and per sheet | [Lumbery's pricing guide](https://lumbery-me.com/pricing-guide-featuring-cedar-shiplap-siding/), read 2026-08-17 |
| cherry 6/4, red oak 4/4, white oak 5/4 and 8/4, 6 mm Baltic birch | **real** but on **sale** to 2026-08-31 | [O'Brien Hardwoods August specials](https://obrienhardwoods.com/specials) |
| walnut 4/4 shorts | **real**, a standing special | [Atlantic Hardwoods specials](https://www.atlantichardwoods.com/specials) |
| cherry 4/4, 5/4, 8/4, 10/4 | placeholder, undated | neither yard publishes a full list — needs a call |
| cherry and Baltic birch plywood | placeholder, undated | as above |
| birch plywood, pine, poplar | no price | — |

Three kinds of entry, because a price sheet has more than one kind of unit.
`dimensional` holds anything sold by the foot or the stick; `unit_goods` holds
what is sold by the item — a bundle of shakes, a lattice panel — where the
supplier prices the thing and publishes no geometry for it, and those entries
record the missing coverage and thickness *as missing*. `suppliers` holds what
applies to the order rather than to any board in it: the yard's phone number and
its volume-discount tiers, which change every line at once or none of them.

```
uv run python projects/cedar_fence.py --variants
```

prices the same 58 ft of fence in every cedar variant Lumbery stocks — $1,708 in
low-grade rough 1x6 up to $3,540 in 5/4x4 decking — and lists what the guide
sells that a fence cannot use, with the reason.

Two materials in that table have **no price at all**, and the file says so
rather than filling them in: peeled round cedar, which Lumbery's guide does not
cover because the guide is sawn stock only, and the black coated welded wire the
log fence is built around, whose retail price is published on pages this
environment's egress proxy blocks. Both are recorded with sizes, sources and a
plain statement of what is missing, so every total that touches them prints as
partial and names what it left out.

`projects/cedar_fence.py` is the project built entirely on the real ones: every
line of its total is dated, and the same guide that prices the stock publishes
no lengths for it, which is why that project buys by the foot and says so.

Three states, and the file distinguishes all three. A **shelf price** is good
until it goes stale. A **sale price** carries `price_valid_until`, so the check
reports it as a special while it lasts and warns the day it lapses — a total
built on last month's discount is wrong in a way that looks perfectly
researched. A **placeholder** is undated, which makes it an `ERROR` and marks
every total it reaches unverified.

The remaining cherry and plywood numbers are invented. The sizes, grades and
thicknesses in that file are real; only that money is not, and it will not be
until somebody phones O'Brien Hardwoods on (207) 536-7860 and writes the shelf
prices down with the date attached. Issue #3 lists exactly what to ask for.

## Known limitation of the 3-D views

matplotlib has no depth buffer, so nearly-coincident surfaces sort
unreliably — in the plan view the centre rail appears to lie over the slats it
actually sits beneath. Use the STEP or STL export in a real viewer when that
matters. `test_centre_rail_sits_below_the_slats` pins the geometry so the
artifact cannot be mistaken for a model error.

See [NOTES.md](NOTES.md) for what these checks caught on the first real project,
and for the list of things still worth building.
