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

## Addendum: a fence, and what buying by the foot asked of the toolkit

The cedar price list arrived looking for a project, and the project it wanted
was the one this repository did not have: 38 ft of fence at 4 ft, plus two 10 ft
sections with gates in them. `projects/cedar_fence.py` builds it in three
styles — spaced picket, board on board, and horizontal — off one frame of 4x4
line posts, 6x6 gate posts and 2x4 rails.

### What it costs, and what that number does not include

| Style | Lineal ft | Total | Per foot of fence |
| --- | --- | --- | --- |
| picket | 615 | $1,817 | $31 |
| horizontal | 622 | $1,850 | $32 |
| board on board | 812 | $2,269 | $39 |

Every rate behind those is Lumbery's, quoted 2026-08-17, and every total says
so. What they exclude is worth as much as what they contain: **hardware is not
in `stock.yaml`** — hinges, latches, drop rods, rail brackets and a keg of
ring-shank nails — and neither is crushed stone, nor labour, nor the machine
that digs eleven holes 4 ft deep. On a pair of 4'-8" leaves the hinge hardware
alone is not a rounding error, and the checks say so rather than letting the
lumber total pass for a project total.

### Rough sawn is a different table, exactly as predicted

The prediction in the price addendum above was that `NOMINAL_TO_ACTUAL` would
have to grow a rough-sawn sibling "the first time a rough-sawn fence wants a
cut list". It did: `rough_dimensions_mm` returns full nominal dimensions, and
`Board(..., rough=True)` sizes a part from it. This is not a detail. A fence
laid out from the dressed table has boards 5-1/2" wide instead of 6", which is
one extra board every 12 ft, and rails 3-1/2" deep instead of 4", which is 25%
less stiffness.

### Nominal size does not identify stock, part two

The same lesson the price work learned about *entries* turned out to apply to
*parts*. "Cedar 1x6" is eight entries in `stock.yaml` spanning $1.30 to $3.75
a lineal foot, so a part has to say which one it means. `Board` now carries
`grade` and `stock_profile` through to `CutPart`, and
`Inventory.dimensional_for` **refuses to guess**: asked for cedar 1x6 with no
grade it raises and names the eight candidates rather than returning whichever
sorted first. A lookup that quietly picked one would have been a 3x error
wearing the clothes of a function call.

That also fixed a quieter bug in the price report. `check_price_provenance`
maps a softwood part to *every entry in its species*, because a pine part could
be cut from any of them — which on a fence meant a provenance report listing all
twenty-eight cedar entries, twenty-four of which the design never touches. It
now takes an explicit `stock=`, and the fence hands it the four entries it
actually buys.

### A buying list is not a cut list

`woodshop/cutlist/dimensional.py` is new, and it exists because of an absence:
the guide prices the stock and publishes **no lengths at all**. So there is
nothing for `optimize_1d` to solve. The plan groups parts by the entry they
buy, totals the lineal feet, adds a stated 10% offcut allowance, and prices it
in the supplier's own unit — then the project emits a `WARN` per group saying
that this is 561 LF to buy and not a cut list, and to come back when the yard
says what lengths they carry. `--assume-lengths 8,10,12` will lay a plan out
against lengths you supply and labels every line of it as your assumption.

The alternative was to default to 8 ft sticks. That would have produced a
beautiful cutting diagram for lumber nobody has confirmed exists, which is the
same failure as an undated price and harder to spot, because a diagram looks
like evidence.

The gallery had to learn the distinction too: `build_project` now picks a
hardwood nesting or a lineal plan by asking whether the species is *stocked* as
hardwood, rather than assuming every solid part comes off a random-width board.

### The checks a fence needs and furniture does not

A bed is not trying to survive outdoors, and nothing in it swings. The fence
findings are mostly about time and weather:

- **frost** — 4 ft of embedment against a 4 ft frost depth in southern Maine,
  which is exactly why the line posts are 8 ft sticks: 4 ft in, 4 ft out, no
  offcut. The gate posts are 8'-6" and get an `INFO` saying that comes off a
  10 ft stick with 18" left over.
- **durability** — cedar heartwood resists rot; cedar *sapwood* does not, and a
  post is bought by the stick rather than sorted. Set posts on crushed stone,
  not in a concrete cup that holds water against the one part of the fence
  nobody can inspect.
- **gate** — a leaf's weight acts at half its width, so a 56-1/4" leaf pulls
  about 20 kg on its top hinge; the brace runs bottom-hinge to top-latch so it
  works in compression, and a brace put in the other way is a gate that sags in
  a season.
- **rhythm** — the one nobody would think to look for. A gate leaf is laid out
  on its own, because both its edges have to land on a whole board, so its
  board spacing does not match the fence beside it. On the picket style that
  mismatch is 23/32", which is visible from ten feet, and the check reports it
  as a `WARN` with the trade to make.

`beam_deflection_mm` came out of `check_slat_deflection` while this was being
written, because a bed slat and a fence rail are the same sum with different
words around it. The rails are nowhere near their limit — span/5000 against a
span/240 limit — which is worth publishing precisely because it says the bay
length is chosen for racking and looks, not for sag.

### What is still open

- **The ground is assumed level.** A real 58 ft line rises and falls, and a
  fence either steps or rakes to follow it. Both change post lengths, board
  lengths and the ground gap, and neither is modelled. This is the largest
  single gap between this model and a fence.
- **Wind and racking are not modelled.** A board-on-board fence is a sail; what
  holds it up is the post in the ground and the panel's resistance to
  parallelogramming, and nothing here computes either.
- **Hardware has no home in `stock.yaml`.** Hinges are sold by the pair,
  fasteners by the box, and the schema has neither unit.
- **The lengths.** One phone call to Lumbery on (207) 835-7023 turns this
  buying list into a cut list. Until then the `WARN` stays.

## Addendum: every variant on the sheet, and the two that had no unit

The fence was built on four entries out of a price list with thirty-four lines
on it. Pricing the other thirty asked three things of the file, and the third
one is the interesting one.

### The missing prices were the ones nobody could model

`stock.yaml` held every cedar line Lumbery prices **by the foot** and none of
the ones priced any other way: three grades of 3/8" shakes at $155, $85 and $20
a bundle, and 4x8 lattice at $250 a sheet. They were left out deliberately —
"a bundle is not a unit this schema has" — and the effect was perverse. The
only prices absent from a complete price list were the two nobody could reason
about, which is the opposite of the rule this file exists to enforce: record
what is known, and record what is missing *as missing*.

`UnitStock` is the fix, and it is deliberately dumb. It holds a species, an
item, a unit, and a price; `coverage_sqft` and `thickness_in` default to
``None`` and stay there, because the guide says nothing about either. A bundle
of shakes covers whatever the exposure it is laid at makes it cover, and the
lattice thickness is simply not published — which is why lattice is not a
`SheetStock`: nothing could check whether it fits a groove.

### A discount is a property of the order, not of a board

The volume tiers — 5% over $5,000, 10% over $7,500, 15% over $10,000 — had
been a comment for the same reason: there is nowhere on a stock entry to put
them, because 15% off changes every line at once or none of them. They now live
under `suppliers`, with the yard's phone number beside them, and
`Supplier.discount_for` answers the question a total actually raises. The fence
prints it: *$2,269 is below Lumbery's first volume tier: 5% starts at $5,000,
$2,731 away.* Which is worth knowing before somebody adds a third gate.

### What a board covers is a third width

Half the guide is milled — tongue and groove, shiplap, nickel gap, drop siding,
clapboard — and a milled board has three widths, not one: what it **measures**
(5-1/2" for a 1x6), what it **covers** once the tongue is inside its neighbour
(about 5-1/8"), and the **nominal** size it is ordered by. A layout that uses
the wrong one is out by a board in forty.

`Board(covers_mm=...)` models the part at what it covers and remembers the face
as `face_width_mm`, and the cut list grew a `stock` column so a row reading
5-1/8" wide still says *1x6 tongue & groove, dressed (STK)* — otherwise a shop
goes looking for 5-1/8" boards nobody sells.

**Every coverage figure in this repository is assumed.** Lumbery prices twelve
milled profiles and publishes the coverage of none, because what a board shows
is set by the moulder that cut it. `ASSUMED_COVERAGE_IN` holds the
industry-standard figures, in the project rather than in `stock.yaml`, and any
fence built on them gets a `WARN` naming the number and saying to measure a
sample. The clapboard is worse still: it is tapered, so its coverage is the
*exposure* the person nailing it up chooses. 4" is a convention, not a fact.

### Interlocking stock cannot be spaced or lapped

A tongue and groove picket fence has no gaps to set — the boards butt, and the
remainder cannot be spread across forty joints, so the last board in each
stretch is ripped narrow. That is how the stuff is laid, and the rip is now a
row in the cut list with a note rather than a surprise on site. Board-on-board
in tongue and groove is refused outright at construction: there is nothing to
lap over.

### The answer

`--variants` prices the same 58 ft of fence in every cedar Lumbery stocks:

```
1x6 rough sawn (low)                     $1.30/LF     $1,708
1x6 tongue & groove, dressed (low)       $1.45/LF     $1,786   butts solid
1x8 dressed (low)                        $2.20/LF     $1,973
1x6 rough sawn (STK)                     $2.30/LF     $2,269   ← the default
1x6 tongue & groove, dressed (STK)       $3.60/LF     $2,983
5/4x4 eased edge decking (STK)           $2.25/LF     $3,540
```

Twenty-two infill variants, four rail variants, three post variants, and a
list of what the yard sells that this fence cannot use — the 2 ft cutoff, the
shakes, the lattice — each with the reason. A catalogue that silently dropped
what it could not handle would read exactly like a catalogue of everything
available, which is the same failure as an undated price.

The cheapest way to build this fence is 2.1x cheaper than the dearest, and
every number in that range is real and dated. What is *not* in any of them is
still the same list: hardware, stone, labour, and the lengths.

## Addendum: a log fence, and the two prices nobody would sell me

The fourth style is peeled round cedar posts and rails with black coated welded
wire between them — the fence you can see through, and the one that keeps a dog
in. It is the first design here whose *total refuses to be a total*, and that
turned out to be the most useful thing about it.

### A log is not a turning

`Turning` already described round parts, and it describes them as a **square
blank with the corners turned away**: largest diameter plus a blank margin,
plus an inch of length for the drive centre. That is exactly right for a
nightstand leg and exactly wrong for a fence post. You buy a log round, by the
foot, and the only work anybody does to it is a cut at each end.

So `Pole` exists, with `shape="pole"`, and its stock dimensions are the round
thing itself. The two classes draw identically and could not be less alike on
an order — which is the same distinction this repository keeps making, between
what a part *is* and what somebody has to buy for it.

Two consequences fell out:

- `estimate_mass_kg` was treating every solid of revolution as the prism its
  side view implies, which makes a 5" log 27% heavier than it is. It now scales
  turnings and poles by π/4. The nightstand's legs got lighter and its tipping
  finding got slightly more honest.
- `check_material_suitability` gained one line: a pole in sheet goods is an
  `ERROR`, because nothing you can do to a sheet makes a log.

`beam_deflection_mm` bends rectangles, and a rail is a circle. A circle's
second moment is `πd⁴/64` where the square it fits inside has `d⁴/12`, so a
round rail is **59%** of that square — passing the diameter as both dimensions
would have overstated a log rail by 70%. The check now passes an equivalent
breadth and says so in the finding, because "a 4" log is not a 4x4" is exactly
the sort of thing somebody substitutes on site.

### Mesh is neither lumber nor sheet goods

It comes off a roll of a fixed height, and the only question is how many feet
of fence there are to cover. Area is the wrong unit: 400 sq ft of roll does not
cover 400 sq ft of a 4 ft fence unless the roll is 4 ft tall, which is a thing
to *check* rather than assume — so `MeshPlan` checks it and reports an `ERROR`
when the fence is taller than the roll, because mesh cannot be stretched and a
horizontal seam across a fence is a line everybody sees.

`plan_dimensional` had to learn the same thing from the other side. Handed a
sheet of mesh it used to say "no nominal size — dimensional stock is bought by
nominal size", which is true and useless. It now recognises material that is
stocked *by the roll or the bundle*, names it, and carries it into the total's
excluded list, so a fence total that leaves the mesh out says which mesh it
left out. `UnitStock` gained a `material` key to make that link.

### The two prices this environment could not get

Neither material is priced, and the reasons are different and both worth
recording:

- **Peeled round cedar.** Lumbery's guide is thirty lines of sawn stock and not
  one round one. Round posts are a real and common Maine product; what is
  missing is a published number. The entries carry sizes and no price.
- **Black coated welded wire.** This one is a stocked retail product with
  published prices — a search puts the 4 ft × 100 ft 14 ga PVC-coated roll at
  about $160 — and **every retailer domain is blocked by this environment's
  egress proxy**: homedepot.com, tractorsupply.com, themillstores.com,
  tridentfence.com, all refused. So the number was never read off a page.

Copying $159.99 out of a search snippet was the tempting move and would have
been the worst one available: undated, unread, and indistinguishable in print
from a price somebody checked. That is the precise failure this file has spent
three addenda learning to refuse. It stays unpriced, the finding says why, and
one dated line closes it.

What the machinery does with that is the payoff. The log fence prints:

```
total 299 LF, $231 (prices as of 2026-08-17; excludes unpriced white_cedar
log 4 peeled log, white_cedar log 5 peeled log, white_cedar log 6 peeled log,
steel welded wire mesh, 2x4, 14 ga, black PVC coated 4 ft x 100 ft)
```

$231 of sawn gate frames, and a total that says out loud it is four materials
short. Nobody can mistake that for the price of a fence — which is the whole
point, and it needed no new code to say it.

`--variants` learned the same manners: a **partial** total now sorts *below*
every complete one rather than by its number, because $231 of a fence is not
cheaper than $2,269 of one, it is less of a total.

### What this style is actually for

- **2" × 4" mesh keeps a dog in and a deer out and stops nothing smaller.** A
  rabbit walks through it. If that matters, the answer is 1" hex on the bottom
  18" with a buried apron, because a dog digs where the fence meets the ground.
- **The gates are sawn frames**, not logs, and the check says why: a round rail
  cannot be half-lapped into a round stile, and a gate held together by tenons
  alone racks the first time somebody swings on it.
- **Cedar eats plain steel.** Its extractives corrode ordinary fasteners and
  stain the wood black around every one of them — which on a mesh fence is
  several hundred staples. That finding now runs in every style, not just this
  one. And every cut end of the mesh is a place the black coating is not: cut
  into the line wire where you can, paint the ends where you cannot.
- **A peeled log keeps the tree's sapwood as its outer skin**, and that skin is
  the whole of what touches soil. A sawn 4x4 out of the middle of the same log
  shows heartwood on all four faces. Round posts are the look and the cheaper
  stick; they are not the more durable one, and the check says so rather than
  letting "cedar" stand in for "will last".

### Still open

The lengths, the hardware, the slope — unchanged from the last addendum. Plus
one more: **the mesh is drawn as a thin sheet**, not as wires. Four hundred
solids a bay would render as a grey haze and take an hour, so the model is
honest about where the mesh is and silent about the pattern. The mass estimate
uses the mesh's own areal weight (about 0.4 lb/ft²) rather than the density of
steel, which would have been fourteen times out.

## Addendum: drawing the ground

Every model in this repository used to stop at its own bounding box, which is
fine for furniture and wrong for a fence: a third of every post is below grade,
and the drawing showed it as a stick hanging in space with nothing to say where
the ground was.

`render_assembly` now draws a transparent plane at `z = 0` whenever the model
goes below it. Three details earned their place:

- **It is transparent on purpose.** What is under it is the part of the fence
  nobody can inspect once it is built — the embedment the frost check argues
  about — so hiding it behind an opaque slab would remove exactly the thing
  worth looking at.
- **It is split into a grid of quads** rather than being one big rectangle.
  matplotlib sorts whole polygons by average depth, so one rectangle would pass
  entirely in front of the fence or entirely behind it. Splitting it lets the
  sort be local, which is as close to a depth buffer as this renderer gets.
- **It reaches across the narrow axis.** A fence is 58 ft long and 8 inches
  deep; a plane that only cleared the model would be a ribbon. Giving the short
  axis a share of the long one puts some earth in front of the fence and some
  behind it, which is what makes it read as ground rather than as a shelf.

Furniture gets none of this, because it does not go below zero — the guess is
"is any of this in the ground?", and `ground=True` or `ground=False` overrides
it where the guess is wrong.

## Addendum: the catalogue, and what it says my fences got wrong

The Lumbery's store page — lumberystore.com/fence-panels-and-posts, read
2026-08-18 — turned out to describe a different product from the one this
project had been designing. They are AVO's exclusive retailer in Maine and New
Hampshire, and AVO sells **pre-assembled panels**: 8 ft units in six styles and
three heights, hung on posts bored at the mill for their dowelled rail ends.

Everything I had built was stick-built: boards nailed to rails on site, boards
running past the posts, the bay chosen to suit the run. That is a real way to
build a fence and it is not what this yard sells.

### What the catalogue settles

Numbers I had been inferring, which they simply publish:

- **Board sizes.** Two of them, and they are milled sizes rather than any
  nominal size's dressed answer: 7/8" x 2-7/8" (stockade, spaced picket) and
  3/4" x 3-1/2" (privacy board, spaced board). My rough sawn 1x6 at a full
  1" x 6" was a third heavier than either.
- **The rail.** 2" x 3" S2S dowelled Colonial rail, double-nailed top and
  bottom. A dressed 2x3 would be 1-1/2" x 2-1/2"; theirs is not, so
  `StockChoice` and `Board` grew `actual_in` / `actual_mm`, which is the same
  principle as the coverage work: a supplier that states the section is
  believed over a table that guesses it.
- **Heights.** 4, 5 and 6 ft in every style, and the custom order form circles
  36, 48, 60, 72, 84 and 96 inches. The 4 ft I was asked for is a stocked size.
- **Post lengths and burial**, from their own sizing table: a 6 ft post for a
  4 ft fence, 4 ft up and 2 ft down; 8 ft for 5 ft; 10 ft for 6 ft.
- **Grades**, in their words: Premium (#1), #2, Economy (#3) — and which styles
  are offered in which. Spaced picket has no Economy grade.

### Where it disagrees with what I built

Three disagreements, and all three are now findings rather than opinions.

**The run has to divide.** A stick-built fence puts its posts where it likes.
A panel fence cannot: the bay *is* the panel, and 38 ft is four 8 ft panels and
two 3 ft leftovers. The catalogue builds custom panels and does not stock them,
so those two are lead time and a separate price — and the check says the
stretches are 19 ft each, and that 16 ft or 24 ft would take whole panels.

**Their burial is half of mine.** I had every post 4 ft down, to clear the
southern Maine frost line. Their table says 2 ft for a 4 ft fence, and it is
their fence — so the panel design follows their table and the frost check now
fires against the supplier rather than against my own guess:

```
WARN [frost] 22" of post in the ground against a 48" frost depth for southern
     Maine — this is the catalogue's own sizing, and it is half the depth the
     frost line asks for. It is what most of these fences are built to and it
     is why they lean; the next post up (8 ft) buys 46" and costs one post size
```

Note the 22": their table says 24", and hanging the panel 2" clear of grade
takes two inches out of the hole. The gap under a panel comes from somewhere.

**Gates are not a product.** Every panel page says the same thing: gates are
custom, cannot be pre-ordered online, email for pricing. So the panel design
draws the gate and refuses to order it, and the order prints it as a quoted
line. This is the first thing in this repository that is deliberately *not*
costed because the supplier declines to.

### An order is not a cut list

This is the structural thing the panel line asked for. Everything else here
produces a cut list — parts, dimensions, what to buy them from. A panel fence
cuts nothing: it is counted, not measured. `PanelOrder` is that: panels by
style, height and grade, posts by *position* (end, line, gate — a pre-routed
post is bored on the faces its rails come into, so a line post in an end
position is a post with a hole in the wrong side), caps by the post, and the
gates as a line that says "ask".

The parts still get drawn — boards, rails, balusters — because a picture of a
box labelled "panel" would check nothing. The report says so in as many words,
so nobody takes the parts list to a saw.

### Still not priced, and now for a third reason

The store publishes the whole catalogue as page text and renders the money
client-side from an API this fetch does not reach. So the options are recorded
and the prices are blank — which now makes three distinct reasons for a blank
in this file: nobody publishes it (round cedar, before this), the page is
blocked (the mesh), and the page publishes it somewhere I cannot read (all of
AVO). Every one of them prints as a partial total that names what it left out,
and every one of them is one phone call from being filled in: (207) 835-7023.

The round cedar entries did get better, though. They were recorded as "peeled
log, NOT PRICED, Lumbery's guide is sawn stock only" — and the store side sells
round posts in 5 to 8 ft and round rails in 3", 3-1/2" and 4". So the log fence
is buying a catalogue item after all, and the entries now say so.
