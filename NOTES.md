# Design journal — reproducing the Mysa sleigh bed

First real project through this codebase: a reproduction of Chilton Furniture's
[Mysa sleigh bed](https://www.chiltons.com/products/mysa-sleigh-bed-cherry) in
solid cherry, then a variant with a cherry-plywood headboard panel and Baltic
birch slats.

The point of the exercise was as much to find out what the toolkit was missing
as to get a cut list. This is the log: what broke, what got built, and what is
written down but deliberately not built yet.

## Gaps found, and what was done about them

### 1. `woodshop.parts` did not exist — **built**

`cutlist/extract.py` imported `woodshop.parts.Board` and `Panel` in its
docstring and keyed its traversal on a `material` attribute, but the module was
never written. Nothing could be modelled at all.

`src/woodshop/parts.py` now provides `Board` (solid stock, by nominal size or
milled dimensions) and `Panel` (sheet goods), both build123d solids carrying
`material`, `grain_direction`, `stock_length_mm`, `qty`, and `notes`.

### 2. Cut dimensions were read off the placed bounding box — **fixed**

`extract._walk` took width from `bbox.size.Y` and thickness from `bbox.size.Z`.
That is only true while a part sits in its local frame. Every side rail in this
bed is rotated onto its edge, which would have reported a 1" × 4-1/2" rail as
4-1/2" × 1". Dimensions now come from the part; the bounding box is only a
fallback for hand-tagged solids. Regression test:
`test_cut_dimensions_survive_rotation_into_an_assembly`.

### 3. No part consolidation — **built**

`extract` produced one row per leaf, so sixteen slats were sixteen identical
rows. `extract(..., consolidate_parts=True)` (the default) now groups identical
parts and sums `qty`.

### 4. `stock.yaml` was dead data, and its schema was too narrow — **built**

Nothing loaded it. Worse, it could only describe softwood dimensional lumber and
48" × 96" sheets — neither of which this project uses.

`src/woodshop/inventory.py` loads it and adds two stock kinds:

- **`hardwood`** — sold rough, in quarter thicknesses, in random widths, priced
  by the board foot. Width is an outcome of milling, not a property of the
  stock, so entries carry a typical width for yield estimates.
- **`sheet_goods`** gained real sheet sizes and a face-grain flag, because
  **not every sheet is 48" × 96"** — Baltic birch is stocked as 60" × 60" *and*
  4' × 8', and which one you can get decides whether this bed's slats can be
  cut in one piece. See the addendum at the end.

### 5. `optimize_1d` binned different cross-sections onto the same board — **fixed**

A 2x4 cut and a 1x6 cut cannot come off the same board. The solver ignored
thickness and width entirely. It now groups by `(material, thickness, width)`
and solves each group independently.

### 6. `optimize_1d` ignored all but the longest stock length — **fixed**

The docstring admitted it ("multi-length optimisation is not yet implemented")
and silently binned everything against the longest length. Each board now
chooses its own stock length, and the default objective minimises *purchased
length* rather than board count, because that is what you pay for.

One subtlety worth recording: bounding the bin count with a greedy pass on the
longest stock is wrong once lengths are heterogeneous — four 900 mm legs are
cheaper as four 1000 mm boards (400 mm waste) than as two 8 ft boards (877 mm
waste), and the tight bound cuts that solution off. The bound is now the worst
case across all usable lengths. Regression test:
`test_more_short_boards_can_beat_fewer_long_ones`.

### 7. `optimize_2d` claimed to respect grain and did not — **fixed**

The docstring described grain constraints in detail; the code passed a single
global `rotation` flag to rectpack and never looked at `grain_direction`.

Rewritten with a shelf packer that takes per-part orientation constraints. Two
properties matter for woodworking and neither was there before:

- **Grain locking.** A part whose grain runs along its length must lie along the
  sheet's face grain and cannot be turned to make it fit.
- **Guillotine-cuttable layouts.** A table saw cannot lift a rectangle out of
  the middle of a sheet. Shelf layouts are always cuttable: crosscut into
  strips, then rip each strip. The old maxrects layouts frequently were not.

rectpack is still reachable as `strategy="maxrects"` — tighter, generally not
cuttable, useful as a lower bound on sheet count.

Sheet goods are also now grouped by material *and* thickness before packing;
3/4" cherry ply and 1/2" birch ply were previously packed onto the same sheet.

### 8. 1-D cutting-stock is the wrong model for hardwood — **built**

This was the biggest one, and the model looked fine until the numbers came out.
The first faithful queen cut list bought **26 boards and 210 linear feet** of
cherry, including one 8-foot board for each individual 2-1/2" slat.

Hardwood is not sold in fixed widths. You rip parts out of a board's width as
well as its length, so the layout problem is two-dimensional and the unit of
purchase is the board foot.

`src/woodshop/cutlist/hardwood.py` nests solid parts onto boards of
representative width using the same shelf packer, picks the cheapest stocked
board length per thickness group, and totals board feet and cost. The queen
went from 210 linear feet of nonsense to **83.8 bd ft, about $1,100** — a
believable number against a $3,595 retail price.

`optimize_1d` is still the right tool for dimensional lumber, where width really
is fixed.

### 9. Wide solid panels are glue-ups, not parts — **built**

Once hardwood nesting was in, the 61-1/4" × 11-1/2" headboard panel was
correctly reported as impossible to cut from a 7" board. It is of course a
glue-up. `stave_wide_parts` splits over-wide solid parts into equal staves
(allowing for jointing both edges) and reports the glue-up separately, so the
cut list says "2 staves of 5-3/4", edge-glued" instead of failing.

### 10. Nothing checked a design before cutting — **built**

`src/woodshop/checks.py` runs against the model and returns findings rather than
raising:

| Check | What it catches |
| --- | --- |
| `check_envelope` | model drifting from the published overall size |
| `check_clearance` | mattress pocket too tight or too loose |
| `check_sheet_fit` | a part that no sheet of its material can yield |
| `check_thickness_substitution` | "3/4" plywood" that is not 3/4" |
| `check_slat_deflection` | a floppy slat deck, with the remedy |
| `alternative_sheets` | other stocked material that *would* fit |

Three of these earned their keep immediately — see below.

### 11. `tabulate` was an undeclared dependency — **fixed**

`render_cut_list(output_md=...)` calls `DataFrame.to_markdown`, which needs
`tabulate`. Nothing had ever exercised that path. Added to `pyproject.toml`.

### 12. `SheetStock.fits` disagreed with the packer — **fixed**

Caught by the checks contradicting the nester: `fits` assumed a part's length
ran along the sheet's *width*, the opposite of the grain convention
`optimize_2d` uses. It wrongly reported the cherry headboard panel as
impossible. Both now share one convention — face grain runs along the sheet's
height. Regression test:
`test_long_grained_part_fits_along_the_sheet_grain`.

## What the checks found in the actual design

**The faithful reproduction** hits the published envelope exactly in all five
sizes, and the derived detail dimensions land on the published numbers (slat
tops at 14", headboard gap at 9-3/4"). Two standing warnings:

- The mattress pocket is loose — 1" per side and 1-3/4" per end on a queen.
  This is not a modelling error; it falls out of the published envelope. The
  listed overall widths imply between 2" and 3-1/2" of total side clearance
  depending on size, which is more than a bed usually carries. Marketing
  numbers are rounded, so the reproduction inherits the rounding.
- A 2" nominal post is really 1-3/4", because that is what 8/4 cherry surfaces
  to. A true 2" post needs 10/4 stock or a lamination.

**The plywood variant** turned up three things worth knowing before ordering:

1. **The slats do not fit — on the sheet I assumed.** A queen slat is 62-1/2",
   and I had Baltic birch down as 60" × 60" only. That is a hard blocker for
   queen and larger. Resolved by splitting each slat in two over the centre
   rail with a 3" cap giving each half 1-1/2" of bearing.

   **Then the supplier data arrived and dissolved it** — see the addendum
   below. The split machinery is still there and still correct; it just is not
   needed if you can buy the 4' × 8' sheet.
2. **Neither "3/4" plywood" is 3/4".** Cherry ply measures 45/64" (17.86 mm)
   and Baltic birch is a metric 18 mm. The headboard panel groove has to be cut
   to fit the sheet, not to the nominal number — a 3/4" groove would be over a
   millimetre loose.
3. **Baltic birch slats are meaningfully floppier than cherry.** 4.2 mm midspan
   deflection against a span/240 limit of 3.1 mm, where solid cherry passes at
   2.5 mm. The check names the remedies: 22 slats instead of 16, or 25/32"
   stock. Left as a warning rather than silently redesigning the deck — the ask
   was to swap the material, and the slat count is part of the published spec.

One pleasant side effect of modelling it properly: the spacers automatically
follow the slat thickness, so the plywood variant's spacers came out 11/16"
rather than 3/4" without anyone having to remember.

## Specced but not built

Deliberately left undone, in rough order of how much they would have helped:

- **Joinery that knows what it mates with.** `woodshop/joinery` has `Mortise`,
  `Tenon`, `Dado`, `Rabbet`, and `PocketHole`, but they are bare `Box`
  subclasses with no positioning and no relationship to the parts they join.
  Nothing verifies that a tenon has a mortise, that they are the same size, or
  that a mortise has not been placed where it would blow out the back of a
  1-3/4" post. This bed has twelve mortise-and-tenon joints modelled only as
  notes on a cut list. Wanted: joints as first-class objects that cut both
  parts, carry a fit allowance, and can be checked for wall thickness and
  interference.
- **A hardware BOM.** The published spec says "metal hardware secures rails to
  posts" — four bed-rail bracket sets, plus screws for the centre rail cap.
  `woodshop/hardware` re-exports three bd_warehouse fastener classes and is
  otherwise empty. Nothing counts fasteners or puts them on a shopping list.
- **Random-width hardwood.** `nest_hardwood` uses one representative width per
  species, which is a real simplification — an actual pile of cherry is 5" to
  11" wide and the nesting changes with it. Wanted: a width distribution, and a
  yield estimate with error bars rather than a single number.
- **Rough-to-finished milling allowances.** `SURFACING_ALLOWANCE_MM` is defined
  and unused. Cut lists should carry both the rough size to cut and the
  finished size to mill to, since you cut oversize and mill down.
- **Seasonal wood movement.** The solid headboard panel is 11-1/2" of flatsawn
  cherry across the grain; it will move roughly 1/8" between a humid summer and
  a dry winter. That is why it floats in a groove, and the model knows to say so
  in a note — but nothing computes the number or checks that the groove is deep
  enough to stay housed. The plywood variant sidesteps this entirely, which is
  arguably its best argument.
- **Cost of sheet goods in the summary.** `stock.yaml` carries
  `price_per_sheet` and the hardwood plan reports cost, but the sheet-goods
  summary does not total it.
- ~~**3-D export.**~~ Done — see the addendum on drawing the model.
- ~~**Cut-order sheets.**~~ Done — `cut_sequence` reads the strips back out.

## Addendum: what the supplier actually stocks

Everything above was built against a `stock.yaml` I wrote from general
knowledge. Checking [O'Brien Hardwoods](https://obrienhardwoods.com/) in
Portland — the obvious supplier for a Maine cherry bed — changed two
conclusions and exposed one more gap in the toolkit.

### Baltic birch comes in 4' × 8' too, and that dissolves the blocker

I had Baltic birch down as 60" × 60", full stop. O'Brien stocks **both**:

> We stock the sheets in 5'x5' & 4x8, in a B/BB grade. […] The 5' × 5' sheet
> uses an interior glue that works well if you are using a laser to cut the
> material. The 4x8 use an exterior grade glue which can make the laser burn
> and char the plywood surface.

A 62-1/2" queen slat clears the 96" dimension of a 4x8 easily. So the split is
not required after all — the plywood queen now cuts **16 whole slats from one
4x8 sheet at 54% yield**, and `split_slats` decides that by itself.

The choice is not purely about size, either: the 5x5 is interior glue and the
4x8 exterior. For a bed, either is fine; for anything damp or laser-cut, the
distinction matters, so it is recorded in each entry's `notes`.

### The inventory could not express two sizes of the same material — **fixed**

This was the gap the real data exposed. `sheet_for(material, thickness)`
returned the *first* match, and both `check_sheet_fit` and `optimize_2d` picked
a sheet by closest thickness. With two 3/4" Baltic birch entries that is a coin
flip — and picking the 5x5 would have silently re-imposed a blocker that does
not exist.

Added `Inventory.sheets_for` and `Inventory.best_sheet_for`, which choose the
**smallest sheet the part actually fits on** and fall back to the largest
available so error messages name the biggest real option. `sheet_for` now
documents that it returns the smallest size. Regression tests:
`test_best_sheet_upgrades_when_the_part_is_too_long`,
`test_pack_by_material_upgrades_to_the_larger_sheet_when_needed`.

This generalises past plywood — it is the same problem as 8-ft versus 10-ft
boards, one dimension up.

### Cherry is stocked in 4/4 through 12/4, so the 1-3/4" post is a guess

O'Brien lists cherry in **4/4, 5/4, 6/4, 8/4, 10/4 and 12/4** (16/4 to order),
kiln dried to 6–10%, sold RWL — *random widths and lengths*, which is exactly
the premise `nest_hardwood` was built on.

That undercuts my stated reason for a 1-3/4" post. I had argued a true 2" post
would need a lamination; with 10/4 on the shelf it simply does not. 1-3/4" is
still a reasonable guess at what Chilton did, but it is now a guess rather than
a constraint, and the docstring says so. `post_in=2.0` builds it the other way.

`stock.yaml` gained 6/4 and 10/4 to match.

### The prices are still invented

O'Brien publishes no prices, so **every `price_per_bf` and `price_per_sheet` in
`stock.yaml` is a placeholder**, now labelled as such with a provenance header.
The board-foot quantities and yields are real; the dollar totals are not, and
the ~$1,100 cherry figure should not be quoted at anyone until someone phones
(207) 536-7860.

### Lumbery is the wrong yard for this

[Lumbery](https://lumbery-me.com/) in Cape Elizabeth curates Maine-grown wood
from small family sawmills — white cedar, premium pine, reclaimed stock. A
genuinely interesting supplier, but softwood-focused: no cherry, no hardwood
plywood. Worth remembering for a different project; nothing here to model.

## Addendum: drawing the model

Everything above measures the bed. Nothing had ever *drawn* it, which meant
every claim rested on `bounding_box()` and a cut list — and a part rotated about
the wrong axis, or buried inside another, passes both without complaint.

`woodshop/render/` now produces shaded isometric, front, side and plan views
from `Shape.tessellate`, so what appears is the real solid rather than a stand-in
built from part dimensions. Parts are coloured by material, which makes the
plywood substitution visible at a glance.

**The verdict: it looks like a bed.** Which is a low bar, and exactly the bar
nothing had cleared until now.

Three things came out of actually looking at it.

### Two rendering bugs, found by looking

The first render put an X across every board. Tessellation splits each
rectangular face into two triangles, and drawing triangle edges draws the
diagonal too. Fixed by dropping edges entirely and shading each triangle by its
normal against a fixed light — which reads better anyway, since a flat fill
makes a solid look like a silhouette.

The second was worse: each part was its own `Poly3DCollection`, so matplotlib
depth-sorted *within* parts but not *between* them. Everything now goes into one
collection.

### A limitation that stays

Even with one collection, matplotlib has no depth buffer, and near-coincident
surfaces still sort unreliably: in the plan view the centre rail appears to lie
over the slats. It does not — its top is at 13-1/4" and the slats run 13-1/4" to
14". `test_centre_rail_sits_below_the_slats` pins that, and the STEP/STL export
is there for when it matters. Worth knowing before someone files a bug against
the model for what is a bug in the picture.

### What the drawing prompted: nothing is buried

The obvious question once you can see it — is anything inside anything else? —
turns out to be answerable in about fifteen lines of bounding-box overlap. The
answer for the queen is that exactly eight pairs of parts interpenetrate, and
all eight are joints:

    foot_post / footboard_rail            tenon
    head_post / headboard_{top,bottom}_rail   tenons
    head_post / headboard_panel           panel into the post groove
    headboard_panel / both rails          panel tongue in the groove
    side_rail / slat, side_rail / spacer  slat ends in the rabbet

Nothing else touches anything. That is now
`test_only_joinery_parts_interpenetrate`, and it is the closest thing to joinery
validation the project has — a stand-in until joints become real objects, since
it would catch a mortise moved to the wrong face even though it knows nothing
about mortises.

### Also fixed while in there

- Sheet diagrams never closed their figures; generating every size and variant
  sailed past matplotlib's twenty-figure warning. Now closed by default, with
  `close=False` for callers who want them.
- Layout diagrams had inch axis *labels* over millimetre *ticks*. Mixed units on
  a drawing read next to a tape measure is a bad way to lose a board.
- Grain direction is now hatched on every nested part, so "why is this one
  sideways?" is answered by the drawing.
- Output filenames were being built from keys like `plywood_cherry 3/4 (48" x
  96")`, producing filenames containing quotes and parentheses.
