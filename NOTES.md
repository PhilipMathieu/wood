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

One subtlety worth recording: bounding the bin count with a greedy pass is
wrong once lengths are heterogeneous — four 900 mm legs are cheaper as four
1000 mm boards (400 mm waste) than as two 8 ft boards (877 mm waste), and a
tight bound cuts that solution off. I got this wrong twice; see the review
addendum for why one bin per cut is the only sound bound when the objective is
purchased length. Regression tests:
`test_more_short_boards_can_beat_fewer_long_ones`,
`test_bin_bound_does_not_hide_a_cheaper_many_short_boards_plan`.

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
- ~~**Cost of sheet goods in the summary.**~~ Done — `sheet_cost_summary`
  totals it, with the same provenance rules as the board plan. See the
  addendum on prices.
- ~~**3-D export.**~~ Done — see the addendum on drawing the model.
- ~~**Cut-order sheets.**~~ Done — `cut_sequence` reads the strips back out.

The joinery gap turns out to be worse than it reads. Every joinery cut is a
boolean, and a boolean returns anonymous geometry that drops straight out of the
cut list — see the nightstand addendum and `retag`.

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
(207) 536-7860. (Since #3 the file says so in a way the code can read — see the
addendum on prices below; the numbers themselves are unchanged, and still need
that phone call.)

### Lumbery is the wrong yard for this

[Lumbery](https://lumbery-me.com/) in Cape Elizabeth curates Maine-grown wood
from small family sawmills — white cedar, premium pine, reclaimed stock. A
genuinely interesting supplier, but softwood-focused: no cherry, no hardwood
plywood. Worth remembering for a different project; nothing here to model.

(That last sentence aged badly, in the best way. Lumbery publishes a complete
white cedar price list, and a fence is exactly the different project. See the
addendum on the first real prices.)

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

## Addendum: what a review pass found

Ran a review over the whole branch before asking anyone else to read it. Six
findings, all reproduced before fixing, all real. Notably every one is in the
code written to *fix* an earlier bug — the second-order mistakes, not the
obvious ones.

**The bin bound was unsound.** Fixing "only the longest stock length is used"
introduced a greedy first-fit bound on the bin count. But a greedy pass bounds
the *number of bins*, and the objective is *purchased length* — the cheapest
plan may legitimately use more bins than any bin-minimising one. One 2900 mm
cut plus ten 999s against 1000 and 3000 mm stock: the optimum is one 3000 plus
ten 1000s, eleven boards and 13000 mm, and the bound capped the search at six
and returned 18000. Reverted to one bin per cut, which is the only sound
general bound here.

**A group's sheet was sized from one part.** `_match_sheet` picked the sheet
from the single longest part, so a long narrow part and a wide short one in the
same group stranded each other in `unpacked`. Now one size is used where one
will do, and the group is split across two sizes when nothing else works —
which is what a shop does: buy both.

**Jointing was subtracted twice, then not at all.** The allowance was applied
to the staving decision but not to the nesting width, so parts were laid out
across width the jointer removes. Eight 85 mm rails nested two-across to
173.2 mm on a board with 171.45 mm of usable width. Board feet still bill the
full width, because that is what you buy.

**Grain lost to `rotation_allowed=False`.** Grain is a constraint, not a
preference, and it was being checked *after* the rotation flag — so disabling
rotation offered a grain-locked part its one illegal orientation and nothing
else. The cherry headboard panel came back un-nestable while `check_sheet_fit`
said it fitted.

**Two smaller ones.** A hardwood row with no `lengths_ft` died on
`min() arg is an empty sequence` instead of naming the row; and the split-slat
warning blamed stock for a split that had been requested by hand, quoting the
very sheet that would take the slats whole.

The pattern worth remembering: none of these were in the original code. They
all arrived with a fix, and four of the six were only visible on inputs the bed
itself never produces — which is exactly why they survived a green test suite.

## Addendum: the nightstand, which is not made of rectangles

The bed validated a lot of machinery and exercised none of it on anything
curved. Every part in it is a box. Adding Chilton's
[Mysa nightstand](https://www.chiltons.com/products/mysa-nightstand-cherry) —
18" round, 1-1/2" top, three turned legs tapering 1-1/2" to 1" — broke four
assumptions at once, and each break is worth writing down because each one was
invisible while the only project was rectilinear.

### 1. A blank is not a part — **built**

`Board` and `Panel` are `Box` subclasses; `CutPart` carries length, width and
thickness and nothing about shape. A round top could not be represented at all.

The fix is not "add a circle". It is the observation that **the cut list should
describe what you buy**, which is the same principle the hardwood nester was
built on, generalised from one dimension to two. So every part now carries
both:

- `length_mm` / `width_mm` / `thickness_mm` — the finished part
- `stock_length_mm` / `stock_width_mm` / `stock_thickness_mm` — the blank

For a rectangle these coincide apart from a trim allowance, so nothing about the
bed changed. For an 18" disc the blank is an 18-1/4" square, and for a tapered
leg it is a 1-3/4" square 1" longer than the spindle. `Disc` and `Turning` are
the two new part classes; both are surfaces of revolution about +Z.

A small trap on the way: Open Cascade refuses to build a cone from two identical
radii, so a *parallel* turning has to be a cylinder. `ShapedPart` picks the
primitive rather than making the caller think about it.

### 2. Yield was quietly lying — **fixed**

Nesting an 18" disc as an 18-1/4" square is correct for purchasing and wrong for
yield: 21% of that square leaves as shavings, and the old `yield_fraction`
counted every square millimetre of it as used. There are genuinely two numbers
here and they answer different questions, so there are now two:

- `yield_fraction` — how well did I nest? (blanks against boards bought)
- `finished_yield_fraction` — how much of the board ends up in the furniture?

They are identical for anything rectangular, and both are printed only when they
differ. The nightstand nests at 63% and finishes at 47%.

A related bug fell out of this. `BoardGroup.nesting` runs on the *usable* width
— typical width less the jointing allowance — so the nesting's own yield divides
by a narrower board than the one you paid for. The board diagram was quoting
that number while the plan summary quoted the billed one: 65% and 63% for the
same board on the same page. Both now bill against the width you buy.

### 3. A boolean cut silently drops a part from the cut list — **built**

A leg turned between centres ends square to its own axis. Lean it 6° and that
end is no longer level: the model came out 22-1/16" tall with its lowest point
1/16" underground, and the real leg would rock. Every splayed-leg piece is
levelled after glue-up, so the model should show the leg that leaves the shop,
not the one that leaves the lathe.

Cutting the foot flat is one boolean — and the result is anonymous geometry.
`extract` keys on the `material` attribute, so the three legs vanished from the
cut list without a word. This is not specific to feet: **every mortise, rabbet,
and dado has the same problem**, which is why the joinery gap listed above is
worse than it looks.

`woodshop.parts.retag(solid, like=part)` is the two-line fix at the call site.
It does not merge or recompute anything, because a mortise does not change the
blank you buy — which is exactly why the metadata should survive the cut.
`test_a_boolean_cut_loses_the_cut_list_without_retag` pins the failure mode so
the reason for the function does not get lost.

### 4. A check that compares a material against an operation — **built**

Every check up to now compared a number against a number. This piece needed a
different kind: a 3/4" Baltic birch slat and a 3/4" Baltic birch turned leg have
*identical rows on a cut list*, and only one of them is possible.

`check_material_suitability` is the first check keyed on shape rather than size:

```
ERROR [material] leg is turned but specified in plywood_baltic_birch: sheet
                 goods have no long grain running the length of a spindle, so
                 the alternating plies tear out at the skew and the piece snaps
                 at the first catch — turn it from solid stock
WARN  [material] top is round and specified in plywood_cherry: the cut exposes
                 edge plies round the whole circumference
INFO  [material] top (18" dia. round …) in solid cherry: it will move across
                 the grain and not along it, so it goes out of round
```

There is a deliberately unbuildable `--variant plywood` for the nightstand whose
only purpose is to make that ERROR fire. It is not in the gallery.

Writing it exposed a related hole: `check_sheet_fit` only ever asked about
length and width, so a 1-3/4" turning blank "fitted" a 3/4" sheet. It now also
checks thickness, and distinguishes a lamination from a mistake — two layers of
45/64" cherry ply is an INFO with the layer count, 1-3/4" of 45/64" Baltic birch
is an ERROR.

### The finding I did not expect

The tipping check was written to make the tripod geometry concrete, on the
assumption it would report something reassuring. It does not:

```
WARN [stability] 4.8 kg on 3 legs: a load of 3.6 kg (8 lb) on the rim between
                 two legs tips it (rim 9", tipping edge 3-7/8" from centre)
```

Three legs stand on a triangle, and the nearest edge of that triangle is at
`foot_radius × cos(π/3)` — exactly **half** the foot radius. Four legs get
`cos(π/4)`, or 71%. That factor is the whole difference between three legs and
four, and it is why a tripod with the same footprint is so much tippier.

The interesting part is that this is not a consequence of my inferred splay
angle. It is forced by the published envelope: the feet plus their own radius
have to stay inside the quoted 18", which caps the foot radius at about 8-1/2",
which caps the tipping edge at 4-1/4" under a 9" rim. **Any** 18"-round tripod
of this height tips under about 8 kg on the rim. The design is not wrong — it is
a nightstand, not a step stool — but the toolkit found a real property of the
piece from two published numbers and a bit of trigonometry, which is the best
argument for having checks at all.

### What reused cleanly, as hoped

- `stave_wide_parts` split the 18-1/4" top into 4 staves of 4-9/16" with no
  changes, keyed only on width. The staves nest as rectangles — the shape only
  appears after the glue-up comes off the clamps — but they carry their share of
  the finished area so the yield stays honest.
- 8/4 cherry surfaces to 1-3/4", which is both enough for a 1-1/2" top and
  exactly a leg blank. Both parts land in one thickness group; the whole
  nightstand is one 6" × 10 ft board.
- `check_envelope` against the published 18" × 22" needed nothing new.

## Addendum: the gallery

Everything above produced files in a gitignored `build/` that lived about as
long as the terminal scrollback. `scripts/build_gallery.py` writes a static site
instead: an index of cards, a page per project with the four views, the cut
list, the nesting layouts, the check report styled by severity, and the
STEP/STL/CSV.

### Projects had to become discoverable first

`projects/*.py` were scripts with bespoke `main()` and argparse — fine for a
human running one at a time, hopeless for anything that wants to run all of
them. `woodshop/project.py` is a registry: a module publishes a module-level
`PROJECTS` list of `ProjectSpec`, and `discover_projects()` finds it.

A `ProjectSpec` is deliberately thin — a slug, a name, and the two callables
that matter, `build` and `check`. Everything else is derived from those two by
machinery that already existed. Modules with no `PROJECTS` are skipped rather
than treated as an error, because `workbench.py` legitimately has no geometry to
show.

Only the queen bed is registered, in both variants. Five sizes × two variants is
ten pages differing in nothing but their numbers, and a gallery of
near-identical cards teaches less than two that differ in something real.

### What the pages would not do

**Publish the prices.** A dollar figure on a web page reads as researched
however loudly the source file labels it, and every price in `stock.yaml` is
invented (#3). Costs are omitted by default; `--with-costs` puts them back
inside a warning block. `test_no_dollar_figure_appears_by_default` asserts no
`$` reaches any page. (Since #3 the pages publish the *provenance* either way —
which material, from where, dated when — because that part is useful and not
embarrassing.)

**Pretend the renders are perfect.** The plan view still draws the centre rail
over the slats it sits beneath. That is documented in a terminal workflow and
would read as a mistake on a gallery page, so every render carries the
painter's-algorithm caveat as a caption.

**Truncate silently.** The faithful queen takes sixteen boards, and sixteen
near-identical diagrams down a page is not information. Four are shown, the
count of what was dropped is stated, and the full set is linked as the PDF —
because a silent cut would read as "this is all of it" when the number of boards
*is* the cost of the project.

### Two things the gallery fixed in the renderers

- `render_sheet_diagram` and `render_board_diagram` only ever wrote multi-page
  PDFs, which no web page can embed. `save_figures` writes one PNG or SVG per
  figure. The PDF is still written first, because it is the one you carry to the
  saw.
- A 6" × 10 ft board drawn with length up the page is a ribbon twenty times
  taller than it is wide — legible in no medium at all. Long stock is now drawn
  lying down, chosen from the aspect ratio, with the grain arrow and the hatching
  turned to match. Sheets are unaffected: a 4×8 at 2:1 stands up fine.

### Still not built

- **No CI.** "Regenerate the gallery on push" needs a workflow this repository
  does not have. The generated site is gitignored; publishing it to Pages is a
  deliberate decision left to a human, not a side effect of a build.
- **A size selector.** One page per design covering all five bed sizes would be
  better than registering one size, and needs client-side state the pages
  currently have none of.

## Addendum: the bed was wrong, and the 360 viewer said so

The owner's review of the nightstand PR: *"a lot of the details of the Mysa bed
are inaccurate — missing the slant to the headboard, the foot shapes, etc. Some
of these should be visible in scrapes, particularly if you pull the 360 degree
views."*

They were right, and it was worse than the slant.

### What the source material actually had

The product page carries a **Cylindo 360 viewer** — customer 6989, product code
`MYSABED`, one frame every 11.25° with `SIZE`, `MATTRESS` and `WOOD` as
features. Frames 1, 9 and 17 are the foot, side and head elevations, and they
are close enough to orthographic to measure. Scaled against the published
87" × 64" × 40" envelope, they give the geometry directly.

That material was there the whole time. The first model was built from the
listing's prose, and prose does not describe a curve.

### What the model had wrong

| Modelled from prose | Measured from the 360 |
|---|---|
| 1-3/4" square posts, vertical | 2"-thick **shaped stiles**: back edge straight, front edge a curve — 3-3/8" deep at the floor, 6" at rail height, 3-1/4" at a rounded top |
| Frame-and-panel headboard, two rails and grooves | **One slab**, raked back 10° |
| A 15" footboard rail | **No footboard.** The foot is the rail |
| Rectangular legs | **Bandsawn**: outer edge vertical, inner edge sweeping 5-5/8" to 2-3/4" |
| Slats in a rail rabbet | Slats on an **inner ledger**, rail standing proud |

The published numbers survived: the 9-3/4" gap, the 14" slat height, the slat
count and spacing, the envelope. Everything the prose *did* say was right;
everything it did not say was invented, and all of it was wrong.

### The measurement that confirmed itself

The stile's measured depth of 6" looked large. It is: with a 1" foot rail it
leaves `87 − 6 − 1 = 80"` of mattress length, which is **exactly** a queen
mattress. That is not a coincidence, and it is the strongest evidence that the
reading is right — the design is dimensioned from the mattress out.
`test_the_measured_stile_depth_leaves_exactly_a_queen_mattress` pins it.

### The gap it exposed: flat parts that are not rectangles

Rectangles were `Board`/`Panel`. Surfaces of revolution were `Disc`/`Turning`.
A bandsawn leg is neither: it is a **flat part with a shaped outline**, and
there was nowhere to put one.

`ShapedBoard` takes a closed 2-D profile and extrudes it. It slots into the
blank-versus-finished machinery built for the nightstand without changing it:

* the **blank** is the profile's bounding rectangle plus a margin — which is
  what you buy and what you clamp to the saw;
* the **finished area** is the polygon's own area, by the shoelace formula, so
  the waste between the curve and the rectangle lands in
  `finished_yield_fraction` instead of vanishing.

That is the third shape family, and the second time the same distinction has
paid for itself.

A convention worth writing down: `ShapedBoard` takes profile-X as the part's
*length*, so a stile's profile is drawn with **height along X**. That looks
odd until the cut list prints `head_stile 40-1/4" x 6-1/4" x 2"` instead of the
transpose. The grain runs up a leg, and length means along the grain.

### What the rebuild also fixed

- **Interpenetration went from eight pairs to one.** The old bed had tenons in
  posts and slats in rabbets, and the clash test enumerated eight legitimate
  overlaps. This bed has exactly one — the panel housed in the stiles.
  Everything else *meets*: the slats sit on the ledgers, the rails sit on the
  legs, the rails butt the stiles where the brackets go. A simpler joint list
  is a better-understood model.
- **The rails are not centred on the bed.** The head stile eats 6" out of one
  end and nothing out of the other, so the deck's centre line is 2-1/2" off the
  bed's. Getting that wrong is invisible in a render and puts every slat in the
  wrong place; `deck_centre_y` now exists to say so once.
- **A short-grain note.** `check_material_suitability` gained a case for shaped
  solid parts: wherever the curve crosses the grain the part is left on short
  grain, which is where a leg breaks.

### The cost of being right

84 bd ft became 111. The real bed has 5-1/2" rails, 6"-deep stiles out of 10/4,
and bandsawn legs whose blanks are much bigger than the parts. The earlier
figure was cheaper because the earlier bed was lighter — and imaginary.

### What still is not measured

The elevations give outlines, not sections. The panel and rail *thicknesses*
(1") come from the listing, the panel's housing is a guess, and the ledger,
centre rail and spacers are ordinary practice rather than observation. Those
are listed in the module docstring under "What is still inferred", which is now
a much shorter list than it was.

## Addendum: prices, and the date a price stops being true

Issue #3. Every price in `stock.yaml` was invented — written so the cost
machinery had something to multiply — and the file said so in a comment, which
is to say it said so to humans and to nobody else. `nest_hardwood` happily
turned those numbers into `$1,097` in the same font as the board feet, and the
board feet are real.

### Two different problems, and only one of them is about honesty

The first is provenance: nothing in the schema could record where a price came
from. The second is that **lumber prices move**, so even a real quote is only
true on the day it was given, and nothing could record that either. A schema
that can hold a supplier's name but not a date solves half the problem and
produces a confident-looking number the following spring.

So `price_as_of` is the load-bearing field, not `price_source`. A price with a
date can go stale and be flagged; a price without one cannot be trusted at all.

### Undated means unverified, not deleted

The tempting move was to strip the fabricated numbers out. That would have left
the cost machinery with nothing to exercise and no way to tell "we have not
priced this yet" from "this is free". Instead, a price with no `price_as_of` is
*unverified*: it still multiplies, and every total built from it carries
`UNVERIFIED — placeholder prices`. The placeholders stay in the file precisely
because they now read as placeholders to the code as well as to the reader, and
they can be replaced one at a time — number, date and source together — as
somebody actually collects them.

### Severities, which took a minute to settle

- **`ERROR`** — a price with no date. It makes a total *wrong* while looking
  complete, and the total cannot say so on its own.
- **`WARN`** — a price older than 180 days, and a material with no price at
  all. Absence makes a total incomplete, which the total now says out loud.

Six months is a starting point, not a considered figure. Hardwood moves faster
than sheet goods and the threshold probably wants to be per material — there is
no price history here to judge it against yet.

The price findings are deliberately **not** folded into a project's design
report. `CheckReport.ok` answers "can this be built as drawn", and an undated
quote has no opinion about joinery. They are a separate report, printed under
its own heading by the project scripts and rendered in its own section on every
gallery page.

### The fix that makes it stick is a type, not a check

A check runs where someone remembers to call it. What stops a bare figure
reaching a page is that there is no longer an easy way to obtain one:

- `PriceLine` is a quantity, a rate, and the rate's provenance. `to_text()`
  renders `$467 (unverified)` or `$584 (as of 2026-08-16)` — there is no
  format that omits the qualifier.
- `CostSummary` collects lines and *names* what it had to leave out. Its
  `to_text()` is the only rendering of a total, and it always ends in either a
  date or the unverified marker.

`HardwoodPlan.cost` used to return `None` if *any* group was unpriced, so one
missing price silently deleted the cost line rather than flagging it. It now
totals what it can, and `cost_summary` reports which entries are missing from
that total and that they are missing rather than free. The sheet-goods summary
gained the same treatment, which closes an older backlog item as a side effect.

### A price per piece means nothing without a length

`DimensionalStock` had no price field at all. Adding one exposed a small trap:
softwood is sold by the stick, and a 2x4 is stocked in 8, 10 and 12 ft, so
`price_per_piece: 6.48` is three different prices depending on which stick you
mean. It therefore comes with `price_length_ft`, defaulting to the shortest
length stocked, and `price_unit` renders as `8 ft piece` so the ambiguity
cannot survive as far as a printed line.

### What this does not do — the phone call

**No real prices were collected.** O'Brien Hardwoods publishes none online, so
every acceptance criterion in #3 that depends on a quote is still open, and the
issue's shopping list is now repeated in the header of `stock.yaml`: cherry per
board foot in 4/4 through 10/4, whether the quote is rough, S2S or S4S, and
whether it is by grade; cherry ply 3/4" 4x8; Baltic birch 3/4" in *both* 5x5
and 4x8, which are different products and should not be assumed to track; birch
ply 3/4" and 1/2"; and any sheet minimums or cut charges. (207) 536-7860.

Grade is the interesting omission. FAS and #1 Common differ by a large fraction
of the price in the same species and thickness, and they yield differently —
`typical_width_in` is really a grade assumption with no grade attached. A single
`price_per_bf` on an entry is a price *and* an unstated grade, which is worth
modelling once there is a real quote to hang it on.

## Addendum: the first real prices, which are cedar

Three sources went looking for real numbers. One of them had them.

**Lumbery** publishes a complete [White Cedar Lumber Pricing
Guide](https://lumbery-me.com/pricing-guide-featuring-cedar-shiplap-siding/) —
28 board profiles and grades, priced per lineal foot. Read on 2026-08-17 and
recorded, every entry dated and linked to the page it came from. These are the
first prices in `stock.yaml` that anybody could stand behind, and they arrive
just in time for a fence.

**O'Brien Hardwoods** still publishes none. Their `/specials` page does post a
few each month — as a PNG, which this session's egress policy would not fetch,
and which nothing here could read if it had. Their product pages give sizes and
thicknesses only; the cherry page confirms 4/4 through 12/4 with 16/4 to order,
which is what `stock.yaml` already claimed. A photograph of the price board is
still the thing that settles it.

**Atlantic Hardwoods** is blocked outright by the egress policy
(`www.atlantichardwoods.com`, 403 at the proxy). Not retried, not routed
around; recorded here and in `stock.yaml` so the next person knows the page
exists and this session simply could not open it.

### What real data asked of the schema

Recording an actual price list, rather than imagining one, immediately broke
three assumptions:

- **A price per piece is not the only unit.** Lumbery quotes per lineal foot;
  O'Brien quotes hardwood per board foot; a big-box shelf tag quotes per stick.
  `DimensionalStock` now carries `price_per_piece` *or* `price_per_lineal_ft`,
  never both — converting one into the other would have meant storing a number
  the supplier never printed, which is the whole failure this work exists to
  stop. The one per-piece entry in the file is the 2 ft dressed cutoff at
  $1.00 each, which really is sold that way.
- **Nominal size does not identify stock.** A rough sawn 1x6 in STK grade is
  $2.30/LF and the same board in low grade is $1.30 — a 77% difference under
  one label. `grade` and `profile` are now fields, and they appear in
  `stock_label`, so the provenance report names `white_cedar 1x6 rough sawn
  (STK)` rather than a `white_cedar 1x6` that could be either. The same gap is
  still open on hardwood, where FAS versus #1 Common is the equivalent split.
- **A published price does not imply a published length.** The guide prices
  every profile and lists no lengths at all, so those entries carry
  `lengths_ft: []`. That is enough to estimate a fence by the foot and not
  enough to lay out a cut list, and saying so in the data beats inventing an
  8 ft default that would quietly become a cut list nobody could buy.

`lumber.NOMINAL_TO_ACTUAL` gained 5/4x3, 5/4x4, 5/4x6 and 6x6 to match what
cedar is actually sold in. Worth writing down: that table holds *dressed*
sizes, and rough sawn stock is close to full dimension — a rough 1x6 is about
a full 1" x 6". Half the cedar list is rough sawn, so the table does not
describe it. Nothing depends on that yet; it will the first time a rough-sawn
fence wants a cut list.

### What did not need to change

Nothing in `pricing.py`, and nothing in the checks. A dated price flows through
the machinery built for the placeholders and comes out the other end as
`$166 (as of 2026-08-17)` instead of `$166 (unverified)`; the gallery's warning
block drops itself when a page's rates are all dated. That was the point of
making provenance a type rather than a lint rule, and it is pleasant to have it
demonstrated by real data on the first try.

The volume discounts on the guide — 5% over $5,000, 10% over $7,500, 15% over
$10,000 — are recorded in the file's header and not modelled. So are the cedar
shakes ($155/bundle clear, $85 wall, $20 low) and the 4x8 lattice sheets ($250
each, thickness unpublished): a bundle is not a unit this schema has, and a
sheet whose thickness nobody states is not a `SheetStock`.

## Addendum: a sale price is a third kind of number

Two domains came off the blocklist, and both suppliers turned out to have real
prices after all — which promptly broke the model again, in a way worth
recording.

**O'Brien's specials do exist**, as a PNG on their CDN. August 2026:

```
4/4 Red Oak          $2.99 BF        6/4 Cherry           $5.25 BF
5/4 White Oak        $8.90 BF        8/4 White Oak        $9.79 BF
6mm Baltic 4x8 B/BB  $61.00 ea
```

**Atlantic Hardwoods** lists one lumber special — 4/4 walnut, 4-6 ft shorts, at
$8.50/bf — alongside red oak stair treads by the piece and prefinished flooring
by the square foot, neither of which is stock this schema can hold.

The cherry number is the one that stings. The placeholder sitting in that slot
was **$14.00/bf**. The real August price is **$5.25**. Nobody would have caught
that by reading the file; it took a picture of a sign.

### The problem with a real price

A special is real, dated, sourced — and temporary. That is a third state, and
until now the file had two: dated (believe it) and undated (do not). Recording
$5.25 as *the* price for 6/4 cherry would be true for two weeks and then
quietly wrong, and wrong in the most convincing possible way, because every
qualifier the machinery prints would say it was verified.

So `price_valid_until` now exists, and the check reads it:

- inside the window → `INFO`, *"a sale price good to 2026-08-31 … not the shelf
  price"*
- past it → `WARN`, *"the shelf price is not recorded, so this total is a total
  at last month's discount"*

`CostSummary.earliest_valid_until` propagates it, because a total built partly
from specials is only good until the first of them runs out. The expiry finding
deliberately supersedes the staleness one: both apply to an old special, and
"the sale ended" explains the number where "this is 200 days old" only
describes it.

The assumption worth flagging: the sheet says "AUGUST SPECIALS" and prints no
end date, so 2026-08-31 is inferred. That is recorded in the comment beside the
entries rather than presented as quoted.

### What the specials did not settle

The shelf prices. Four cherry thicknesses are still placeholders, and the bed
uses all of them — its total still prints `UNVERIFIED`, correctly, because one
real sale price among four invented ones does not make a verified total. The
specials also brought in two species (red and white oak) whose widths, lengths
and grades the sheet does not give: those fields follow the cherry convention
and are commented as assumptions, because a yield estimate built on an assumed
7" board is a different kind of claim from a price read off a sign.

And there is a maintenance problem the file cannot solve: **the specials change
every month**. A price list that has to be re-photographed to stay true will
not stay true. Hence #9 on scheduled refreshes — the machinery for noticing
staleness is now in place, and something has to actually go and look. The
first version proposed there does not even parse the sign: it notices the
image changed and shows it to a human, because a scraper that launders a bad
parse into a dated price would undo everything #3 built.

## Addendum: the media console, where the plywood decides the dimensions

The first piece in this repo that is not a reproduction. The brief is prose:
80" x 24" x 13" in cherry plywood, five record bays 15" wide and 13-1/2" tall,
a shallower 8" row above for CDs, a clear top for the turntable, solid cherry
front edges, dados, clear finish. Everything below came out of trying to make
all of those numbers true at once, which they are not.

### The brief is over-specified by 3/8" and an eighth of an inch

Add it up. Five 15" bays and six 3/4" panels is 79-1/2", not 80". The two
openings and three 3/4" panels come to 23-3/4" of the 24". The brief is
internally inconsistent at exactly the scale that nobody notices on paper and
everybody notices at the saw.

Then the plywood moves both numbers again, in the *same* direction. `3/4"`
cherry plywood measures 45/64", so six verticals take 4-7/32" instead of 4-1/2"
and three horizontals take 2-3/32" instead of 2-1/4". The design's whole job is
deciding where that slack goes:

- **Across the width**: into the bays. They come out 15-5/32" clear, an eighth
  over the brief. The alternative is a case 79-1/32" wide, and the envelope is
  the number a room cares about.
- **Up the height**: into the floor. The openings are held at 13-1/2" and 8"
  exactly, and the 25/64" left over becomes a **toe reveal** — the bay bottoms
  are housed that far off the floor and the case stands on its six panel ends.

The second one is the better decision of the two. A 3/8" reveal is too small to
read as a plinth, so it does not pretend to be one; what it does is keep a
plywood bottom off a floor that is never flat, and give the piece a shadow line
where it meets it. `check_envelope` confirms all three published dimensions to
the sixteenth, which they only are because the openings were held and the bays
were not.

### The five bays are not a structural number — **and the check says so**

`check_shelf_deflection` is new: the same simply-supported beam under a UDL
that `check_slat_deflection` already used, factored out into
`_udl_deflection_mm` and asked a different question.

The difference is not cosmetic. A slat's load is *fixed* — 250 kg of mattress
and people, however many slats there are — so its deflection goes as 1/n and
the remedy is more slats. A shelf's load **comes with its length**: twice the
shelf holds twice the records. So sag goes as the fourth power of the span, and
the remedy is a divider. Two functions, because the two remedies are different
sentences.

What it found is the useful part. A full bay bottom — 75 records, 19 kg over a
15-5/32" span — sags **0.1 mm**, span/2686. Undivided, the same bottom at the
same load per foot sags **100 mm**, and the check reports that three bays would
be enough to meet span/360.

So the five bays are not holding the plywood up. They are there because a run
of records much over 15" leans, slumps and bends the sleeves at the ends of it,
which is a fact about records and not about stiffness — and the report now says
both, in order, instead of leaving a reader to assume the dividers are
structural.

Shelves are held to span/360, not the span/240 the bed deck gets. Sag this side
of collapse is an appearance problem, and appearance is stricter than
serviceability.

### `check_clearance` was telling a bookcase about its mattress

Reusing it for the finger's room above a record sleeve turned up a hard-coded
`"tight, mattress may bind"` in a general-purpose check. The band is general;
what being outside it *costs* is not, and only the caller knows. `tight_note`
and `loose_note` are now parameters, and the bed passes its own mattress
wording. One call site made it look like a style choice; the second made it a
bug.

### The renderer was clipping the console and saying nothing

The front elevation lost its right-hand end. mplot3d honours the *ratio* of
`set_box_aspect` and not the size, so a long, low plot box runs past the axes
and is silently cropped — a failure mode with no error, no warning, and a
plausible-looking picture. `_fit_zoom` zooms out in proportion to how far the
longest span exceeds its share of the diagonal: 1.0 for anything roughly cubic,
so the bed and the nightstand render exactly as before, and 0.85 for an 80" x
13" x 24" console.

This is the second time the views have caught something no dimension check
could. It is worth repeating that the renderer earns its keep as a *check*, not
as decoration — and that a renderer which crops instead of failing is worse
than one that draws nothing.

### Dados, cut rather than described

Every other project in the repo models parts that meet; this one models parts
that are *housed*, and `woodshop.joinery.Dado` had been sitting unused since it
was written. The verticals are housed 1/4" into the underside of the top (a
rabbet at each end, a dado at each divider) and the shelves 1/4" into the
verticals — twenty-six housings in all, four in every divider and two in each
end panel — and every one of them is a real boolean followed by `retag`.

The cut is what makes `test_the_housings_are_really_cut_away` possible: the
intersection of a divider and the shelf running into it has zero volume. Model
the joint as a note and the shelf ends sit inside solid plywood, which no
dimension check would ever notice and every dry fit would.

### What the cut list says, and one thing it overstates

Two sheets of 4x8 cherry plywood at 52% yield, and a single 4/4 cherry board
for the edging. The yield number is honest and unflattering: the parts total
about 1.05 sheets of area, so the second sheet is mostly offcut — enough for a
shorter second case, or for a back if the piece ever wants one.

The overstatement is the edging. It is 31 lineal feet of 1/4"-wide strip milled
to the plywood's 45/64", and `nest_hardwood` buys 4/4 stock for it and bills the
full board thickness. Resawn, one 4/4 board yields two or three times what the
plan assumes. The nester has no idea a part can be *cut out of the thickness*
of a board rather than off its width, and that is the next real gap in it.

## Addendum: the console became a kit, and then a second console

The dado version above lasted about an hour. Asked to make it modular *like the
original*, I went and found out what the original actually is — and it is not a
case at all.

### What the Grid System turned out to be

`luccahouse.com` is blocked from this machine, so nothing here is measured off
it and no photograph was read; what follows is from search results, and it is
recorded that way in the module docstring too. **(Superseded — the domain was
opened up later the same day and the photographs contradicted this section on
one point. See "the pictures were right and the model was wrong, again", at the
end.)** Lucca House's **Grid System** is
prefinished maple plywood panels **notched to slide together**: no tools, no
glue, no hardware, assembled or taken apart in under a minute, named by the
grid they make (`5x1`, `4x2`, `5x4`), with three part sizes producing six
products and resizing done by swapping the long parts.

That is a different animal from a glued case, and copying the *look* of it
without the joinery would have been the wrong answer to the question.

### One decision does all the work

Every crossing is a half-lap: the shelf notched half its depth from the **back**
edge, the upright half its depth from the **front**, sliding together front to
back until each fills the other. Four consequences fall straight out of it, and
none of them had to be designed separately:

- **The parts collapse to three.** Six uprights, two shelves, a top. The
  bottom shelf and the CD shelf are the same part; so are all six uprights,
  end panels included, because a slot open at an edge is symmetrical and
  therefore not handed. The dado version had ten shelves in two labels, four
  dividers and two sides.
- **The front edging reverses.** Where a shelf crosses an upright, the front of
  the case *is* the shelf — there is no upright material there to glue a strip
  to. So the horizontals' edging runs unbroken and the uprights' is in one
  piece per row, which is the opposite of the glued version and was not a
  styling choice.
- **A 25/64" problem appeared at the floor.** Below the bottom shelf each
  upright shows a foot of toe reveal, too little to edge and too much to leave
  bare. The fix is the base rail: the bottom shelf's edging deepened to 1-1/32"
  so it covers the shelf and the feet together, stopping a sixteenth short of
  the floor so the uprights still carry the piece and can still be shimmed.
- **The slot tolerance stops being cosmetic.** A dado 1/32" wide of the panel
  is a glue line. A *slot* 1/32" wide of it, in a case with no glue anywhere,
  is a wobble — so `check_thickness_substitution`'s warning is now joined by a
  `kit` warning that says to cut one test slot in an offcut first.

`test_at_a_crossing_each_part_has_only_its_own_half` is the whole design in one
assertion: probe the front half of the depth at a crossing and the upright has
no material there; probe the back half and the shelf has none. They interlock
and never intersect, which a bounding-box test cannot tell you.

### The painted build, which is not the same piece in cheaper clothes

Then: a plain painted plywood build with a solid wood top. That is a variant in
the repo's usual sense — same grid, same openings, same envelope — but almost
every derived number moves, and *that is the point of deriving them*:

| | cherry | painted |
| --- | --- | --- |
| sheet | cherry ply, **45/64"** | paint-grade birch, **23/32"** |
| bays | 15-5/32" | **14-15/16"** |
| toe reveal | 25/64" | 5/16" |
| front edges | solid cherry, 15 strips | none — filled and painted |
| top | a member of the grid | solid cherry, 3/4", overhanging 1/2" each end |
| pieces | 9 panels + 15 strips | 8 panels + 1 board |

Two things worth writing down:

**The overhang pays for the thicker sheet.** A solid top that projects past the
ends takes its overhang out of the *case*, not out of the room: the console is
80" wide either way, the grid under it is 79", and the bays land at 14-15/16" —
within a sixteenth of the 15" the brief asked for and closer than the cherry
build gets. Birch ply being thicker than cherry ply would have pushed them the
other way; the overhang more than cancels it.

**A plywood case does not move and a solid top always does.** Hence
`check_wood_movement`, which is new: tangential shrinkage from the Wood
Handbook, a six-point seasonal moisture swing, and the answer for this piece is
**3/16" across 13" of cherry**. That is not a rounding error, and it decides a
joint: the top's housings run front to back, the same way it moves, so nothing
restrains it and the slab simply lies on the grid under its own weight. Screws
up through the shelves would be the one mistake that splits it — pass
`allowance_mm=0.0` and the check says so in as many words.

The check earns its keep beyond this piece. Every other check in the module
asks whether a design *can be built*; this one asks whether it will still be
built the same way in February.

### And one thing the renderer nearly hid

The 80" console was being cropped in the front and plan elevations — mplot3d
honours the *ratio* of `set_box_aspect` and not the size, so a long, low plot
box runs off the axes and is cropped with no error and no warning. `_fit_zoom`
scales the drawing back by how far the longest span exceeds its share of the
diagonal: 1.0 for anything roughly cubic, so the bed and the nightstand are
untouched, and 0.85 for this. A renderer that crops silently is worse than one
that fails, because the picture still looks plausible — and the picture is what
this repo uses to catch the mistakes no dimension check can.

## Addendum: the pictures were right and the model was wrong, again

The console was designed from prose, because `luccahouse.com` was blocked by
the egress proxy. Then `cdn.shopify.com` and the site itself were allowlisted,
the manufacturer's own images could be read, and they contradicted the model.

This is the second time in this repo. The bed was built from a listing's prose
and rebuilt from the 360 viewer; the console was built from search snippets and
corrected from tearsheets. **Prose describes what a thing is for. Pictures
describe what it is.** Worth writing on the wall.

### Correction 1: the slot direction was backwards

The model had the shelves notched from the back and the uprights from the
front, so the horizontals ran unbroken across the front of the case. Every
consequence of that — the edging arrangement, the base rail — followed from it,
and it is wrong.

The evidence is a photograph of a single crossing with red edge banding
(`4x2_color_swatch_red.jpg` on their CDN). At the crossing the **vertical**
band runs through unbroken and the **horizontal** band butts into it on both
sides. The member visible at the front owns the front half-depth. So:

- uprights are slotted from the **back**, and keep their front half;
- shelves are slotted from the **front**.

Flipping it took two lines and deleted a part. With the uprights unbroken at
the front, each one's edging is a single strip from the floor to the underside
of the top — which covers the 25/64" of foot that the base rail was invented to
hide. The rail, its `base_rail_float_in` parameter and its test are gone, and
the front now reads as six verticals with shelf edges between them.

The lesson is not "check the reference" — it is that a design decision with
four consequences hanging off it deserves a source, and "it looked better to me
that way" was doing the work of one.

### Correction 2: the radius was more than twice too big

The first radius was 2", picked by eye. Their tearsheets are dimensioned
orthographic drawings, and they self-calibrate: the parts in the 4x2 sheet
measure exactly 11-1/2" x 23-1/2" and 11-1/2" x 47-1/2", which gives 17.1 px/in
directly off the image. Thresholding the panel colour and measuring where each
panel's top row starts against its leftmost column gives the radius without
any curve fitting:

```
4x2 tearsheet   long parts  197 x 803 px, r = 13-14 px   ->  0.76-0.82"
4x2 tearsheet   short parts 403 x 197 px, r = 14-18 px   ->  0.82-1.05"
1x1 tearsheet   parts       279 x 279 px, r = 19-26 px   ->  0.78-1.07"
```

Call it **0.8", and 0.07 of the panel's width** — which is the number that
travels, because their panels are 11-1/2" wide and this console's are 12-3/4".
`REFERENCE_RADIUS_RATIO` holds the ratio and `reference_corner_radius`
multiplies it out: **7/8"** here. Rendered beside the old 2", the difference is
not subtle — 2" reads as a rounded box, 7/8" as a square panel with the corners
taken off, which is what the photographs show.

### What was deliberately not adopted

Their stock is **1/2"** plywood at **11-1/2"** deep, and their members overrun
every crossing — the horizontals run past the end uprights and the uprights
stand proud above and below. That is a shelf that wants to look like a grid.
This is a console that has to hold 200 lb of records at browsing height inside
a published 80" x 24" x 13", so it keeps 3/4"-class stock, a closed envelope,
and a top that caps the uprights rather than letting them through.

Both facts are recorded in the module docstring under *Where the joinery came
from*, along with which two things are measured and which are borrowed. The
distinction is the whole point: this piece is not a reproduction, and the file
should never be able to be mistaken for one.

### Correction 3: everything overruns, and that is the whole look

The two corrections above were about *where* material sits at a joint. This one
is about whether the joint is a joint at all.

In the reference, **every member runs past its outermost crossing** — the
horizontals past the end uprights, the uprights above the top shelf and below
the bottom one, which is also what they stand on. So every joint is a
full-width lap with stock on both sides of it, and nothing terminates at a
joint. The console had the end uprights flush with the ends, which turns the
four crossings there into corner notches and the top's outer housings into
rabbets. That is why it kept reading as a box with a grid drawn on it.

The parts drawings give the number without any perspective to argue with,
because the slots are dimensioned by their own positions:

```
23-1/2" parts (4 slots)   0.44"*  4.03"          19.44"  23.06"*
47-1/2" parts (6 slots)   0.38"*  4.03"  15.00"  31.87"  42.85"  46.44"*
                          * = the corner radius, not a slot
```

So the outer slots sit **4.03" from one end and 4.06"/4.4" from the other** —
a constant ~4" overrun on an 11-1/2" panel, **0.35 of the panel's width**, the
same in both directions. `REFERENCE_OVERHANG_RATIO` holds it and
`end_overhang` multiplies it out: **4-7/16"** on this console's 12-3/4" panels.

**It is bought out of the bays, and the report says so.** The envelope is
published at 80", so 8-7/8" of overrun takes 1-25/32" off every opening: bays
of **13-3/8"** instead of 15-5/32", which leaves 1" beside a 12-3/8" sleeve
rather than 2-3/4". `end_overhang_in=0` takes the old bays back along with the
corner notches, and both numbers are printed either way.

Two consequences worth stating rather than discovering later:

- **An ear is a ledge, not a bay.** There is no upright beyond it, so records
  in the outer 4-7/16" have nothing to lean against. It is somewhere to put a
  record down while the other side plays, and the check says so as a `WARN`
  rather than leaving it to be found out.
- **The uprights cannot overrun.** The reference stands them ~4" proud top and
  bottom; a 24" envelope with 13-1/2" and 8" openings has 25/64" left over
  once three panels have had theirs. The toe reveal is what survives of that
  idea. Matching it would mean a 33" console or shorter rows, and the brief
  says 24".

That last one is the honest limit of borrowing a system for a piece it was not
drawn for. The horizontal half of the language fits inside the brief; the
vertical half does not, and pretending otherwise would mean quietly changing
what the piece is for.

### Shipped: both proportions on by default, and the ears got a job

`corner_radius_in` and `end_overhang_in` both now default to `None`, meaning
*the maker's proportion* — 7/8" of radius and 4-7/16" of overrun on these
12-3/4" panels. Passing `0` to either goes back to square corners or flush
ends. Holding them as ratios rather than inches is what makes that work: the
painted build's panels are 13" wide, so it takes 0.91" and 4-9/16" without
anybody restating the numbers.

The ears turned out to be the point rather than the price. They are the only
surfaces on the piece at a height you look *at* rather than down on, and they
are for a plant or something small — so the report now weighs them as ledges:
5 kg on the very tip of one deflects it 0.02 mm, ear/4539, which says the limit
is what will sit still on a 4-7/16" shelf and not the plywood under it. Two
warnings keep their company, because a ledge that is good for a plant is bad
for two other things:

- **Not a bay.** Nothing stands beyond an ear, so records put there walk off
  the end.
- **Water.** A pot of damp soil on end grain and edge veneer is the one place
  on this piece where a ring is likely — saucer and cork mat, and on the
  painted build's plywood edge a ring is swelling, not a stain.

That is the sort of thing a check is for: the design got a new use, and the
consequences of that use are now printed next to it rather than remembered.

## Addendum: the bed was the wrong bed

The Mysa's shapes still looked off next to the product photos, so the 360
frames got a second, more careful pass — all 32 of them this time, measured
programmatically (silhouette masks, contour tables every quarter inch) rather
than by eye, with a vision pass over the key frames to settle what the numbers
could not.

### The render is the California King

The first pass scaled the elevations against the queen's published
87" x 64" x 40". Two findings say that was the wrong envelope:

- The CDN's own error message, on a failed frame fetch, names the underlying
  product **`MYSABEDCK`** — the Cal King.
- The side elevation's silhouette aspect ratio is 91/40 **to four
  figures** (2.2754 measured, 2.2750 published for the Cal King's
  91" x 79" x 40"; the queen predicts 2.175). Recalibrated at L = 91", the
  frame's vertical and horizontal scales agree to 0.02%; at L = 87" they
  disagreed by 4.5%.

Every cross-bed dimension in the first pass was therefore ~19% small at the
source and every lengthwise one ~4.5% small, error that landed unevenly in
whichever member was being read. That is where the 2" stile came from: it was
never 2".

### What the second pass changed

| | first pass | second pass |
|---|---|---|
| Stile thickness | 2" (needs 10/4) | 1-3/4" (8/4, exactly) |
| Stile front edge | peak 6" at 16", long taper to 3-1/4" | quarter-sine to 5-3/4", **held to the panel's bottom edge**, then raked with the panel to a ~2" bullnose |
| Foot leg | stops under the rail, 1-3/4" thick | **forms the corner** — rails butt into it, rounded runner tip ~3/4" proud of the rail top; 1-1/2" thick |
| Rails | 5-1/2" deep | 4-1/2" deep |
| Head rail | none | spans post-to-post at rail height, under the gap |
| Panel rake | 10° | 11°, and the stile's hidden front edge is the same line |
| Panel reveal | 3/4" | 1-1/2" |

The interpenetration count survives the rebuild: still exactly one legitimate
overlap, the panel housed in the stiles. The rails no longer overlap anything
— they butt.

### What a projection is allowed to say

The lesson of the pass is about trust boundaries. Within one frame, at the
**near plane**, a silhouette is honest: the side view's bounding box is set by
members at the near side, so lengths and depths read there are true once the
envelope is right — that is what the 0.02% isotropy check certifies. Across
planes it is not: the far half of the bed projects shifted, scaled, and
half-swallowed by nearer members, and no single pinhole model reconciled all
three dead-on frames (Cylindo evidently reframes per shot). Two early
"discoveries" — a full-width scroll headboard, under-bed stringers — were
artifacts of reading far-plane pixels against near-plane scale, and died when
the oblique frames were put in front of eyes rather than thresholds.

So the method that stands: classify all 32 frames by silhouette aspect
(mirror-symmetry pins the dead-on views), calibrate each frame at its near
plane, take only near-plane measurements from any frame, and let a visual pass
arbitrate topology. The queen model keeps its published envelope and derives
lengths from it; what it takes from the Cal King render is the *sections and
shapes*, which a maker holds constant across sizes.

### The 2" stile, exhumed

One number deserves its own funeral. The first pass measured the stile at 2"
and the note said 10/4 stock, which was believable and expensive. At the Cal
King scale the stile is 1-3/4" — which is not just cheaper, it is *exactly
what 8/4 surfaces to*, the kind of number a furniture maker actually picks.
The corrected bed uses one fewer thickness class of cherry, and the test that
pinned "stiles need 10/4" now pins the opposite.

## Addendum: the deck gate, or the case against a diagonal

First outdoor piece, and the first that is not furniture: a gate for the
deck stairs so the dog can be let out unescorted. The deck's railing is 4x4
posts, 2x4 rails, vertical 1x1 slats with parallel 45° miters, and a dressed
cedar 1x6 laid flat as a cap; the gate (`projects/deck_gate.py`) is that
railing section rebuilt as a swinging frame, after Young House Love's
"DeckGate" pattern. Built first on a placeholder 36" x 36" opening; the
tape measure arrived a day later — 36-1/2" between the posts, rail top
41-1/2" and bottom-rail underside 3-3/4" above the decking — and the
parameters were reshaped to match how the deck was actually measured
(opening width, rail-top height, bottom gap) rather than an abstract
gate height, so the gate hangs on the railing's own lines and the
placeholder never appears again.

### The bracing question got a check instead of an opinion

Whether a gate needs a diagonal is the racking moment against the corner
joints' capacity, and both are computable, so `check_racking` computes them
rather than the working log asserting them. The demand is almost entirely
the dog: a cedar gate this size weighs ~11 lb and contributes ~21 N·m about
the hinge line, while a 60 lb dog landing paws on the latch corner at a 1.5
dynamic factor contributes ~357 N·m. Each rail-stile corner turns its share
into a ~2.1 kN force couple across the rail's 3-1/2" depth. A glued
half-lap — ~12 in² of long-grain glue face, held to a wet-service 200 psi —
carries that with a 2.1x margin, so the default gate has no diagonal and
says why. Rebuild it with `corner_joinery="pocket_screw"` and the same
check flips to WARN at 0.4x and names the remedies (`brace="cable"`, or the
half-laps). The check that would have been an argument is now a regression
test in both directions.

### What the toolkit learned

* **`DENSITY_KG_M3` had no `white_cedar`** and fell back to 600 kg/m³ —
  nearly double the Wood Handbook's ~320 for northern white cedar, which
  would have doubled the gate's self-weight in the racking numbers. A test
  now trips if the species falls out of the table.
* **The gallery assumed every species is bought rough.** `build_project`
  called `nest_hardwood` on any solid part, and cedar bought as dimensional
  2x4s from Lumbery's price list (already in `stock.yaml` from the fence
  estimate) has nothing to nest. Softwood projects now skip the hardwood
  plan instead of crashing the gallery.
* **A mitered slat is not a `ShapedBoard`.** Modelled as a profile, the
  cut list invented an oversized blank and the suitability check warned
  about short grain on what is a straight stick. The slat is a `Board` with
  the corner triangles sawn off the solid and `retag` keeping its identity
  — the miter takes no stock, and the cut list now says a plain 1x1, long
  point to long point.
* **`MATERIAL_COLORS` gained cedar**, because the first render was gray and
  a gray gate reads as aluminum.

Still deliberately unmodelled: hinges, latch, and the cable turnbuckle
(`brace="cable"` changes the checks and the notes, not the cut list), and
the half-laps themselves are notes on the stiles rather than subtracted
geometry — the joint that matters here is an area and an allowable, not a
solid.

The railing's own pitch turned out to be the sharpest finding: 5" centres,
which is 4-1/4" clear between 1x1s — wider than the 4"-sphere rule. The
railing predates the rule; a new gate does not, so the gate defaults to six
slats at 3.45" and says so, and `match_railing_pitch=True` copies the
railing's five-slat rhythm with the guard check refusing to look away
(pinned as an ERROR by a test in both directions).
