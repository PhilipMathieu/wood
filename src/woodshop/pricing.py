"""Money, and how much of it you are allowed to believe.

Every other number this repository prints is derived from geometry: a board
foot is a measurement, a sheet count is a consequence of nesting, and both are
true the day they are computed and true a year later.  A price is neither.  It
comes from outside — a quote, a price list, a conversation at a counter — and
it is only true on the day it was given.

So a price is never carried as a bare float.  It travels as a
:class:`PriceLine`: an amount, the quantity it multiplies, and *where and when
the rate came from*.  A :class:`CostSummary` collects those lines and refuses
to render a total without saying either the date behind it or that there is no
date behind it.  That is the whole point of this module — a dollar figure with
no provenance reads as researched however the source file labels it, and the
only reliable fix is to make the unqualified rendering impossible to obtain.

Example
-------
>>> from datetime import date
>>> line = PriceLine("cherry 4/4", 46.7, "bd ft", 12.50, as_of=None)
>>> line.to_text()
'$584 (unverified)'
>>> CostSummary.of([line]).to_text()
'$584 (UNVERIFIED — placeholder prices)'
>>> dated = PriceLine("cherry 4/4", 46.7, "bd ft", 12.50, as_of=date(2026, 8, 16))
>>> CostSummary.of([dated]).to_text()
'$584 (prices as of 2026-08-16)'
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from woodshop.cutlist.optimize_2d import Cut2DResult
    from woodshop.inventory import Inventory, SheetStock

__all__ = [
    "UNVERIFIED_MARKER",
    "PriceLine",
    "CostSummary",
    "format_money",
    "sheet_cost_summary",
    "sheet_for_key",
]

#: Text that must accompany any total built from an undated price.
UNVERIFIED_MARKER = "UNVERIFIED — placeholder prices"


def format_money(amount: float) -> str:
    """Render an amount as whole dollars, e.g. ``'$1,097'``.

    Cents are noise on a figure whose rate is a phone quote from three months
    ago, and rounding to the dollar keeps the eye on the qualifier that follows
    it.
    """
    return f"${amount:,.0f}"


@dataclass(frozen=True)
class PriceLine:
    """One priced quantity, with the provenance of the rate behind it.

    Parameters
    ----------
    label : str
        What was bought, e.g. ``'cherry 4/4'``.
    quantity : float
        How much of it, in *unit*.
    unit : str
        Unit the rate is quoted in — ``'bd ft'``, ``'sheet'``, ``'piece'``.
    unit_price : float
        Cost of one *unit*.
    as_of : datetime.date or None
        The day the rate was true.  ``None`` means nobody has verified it, and
        every rendering of this line says so.
    valid_until : datetime.date or None, optional
        The last day the rate is known to hold.  Set for a *sale* price, which
        is real, dated, sourced — and temporary.  A special that has run out
        is as wrong as an invented number and much more convincing.
    source : str, optional
        Where the rate came from, e.g. ``"O'Brien Hardwoods, phone quote"``.
    source_url : str, optional
        A link to the source, where one exists.
    """

    label: str
    quantity: float
    unit: str
    unit_price: float
    as_of: date | None = None
    valid_until: date | None = None
    source: str = ""
    source_url: str = ""

    @property
    def amount(self) -> float:
        """Cost of this line."""
        return self.quantity * self.unit_price

    @property
    def verified(self) -> bool:
        """``True`` if the rate carries a date."""
        return self.as_of is not None

    @property
    def qualifier(self) -> str:
        """Short parenthetical for this line: a date, or the lack of one."""
        if self.as_of is None:
            return "unverified"
        text = f"as of {self.as_of.isoformat()}"
        if self.valid_until is not None:
            text += f", sale ends {self.valid_until.isoformat()}"
        return text

    def expired(self, today: date) -> bool:
        """Return ``True`` if this is a sale price whose end date has passed."""
        return self.valid_until is not None and today > self.valid_until

    def to_text(self) -> str:
        """Render the amount, always qualified, e.g. ``'$584 (unverified)'``."""
        return f"{format_money(self.amount)} ({self.qualifier})"

    def rate_text(self) -> str:
        """Render the rate itself, e.g. ``'$12.50/bd ft, unverified'``."""
        return f"${self.unit_price:,.2f}/{self.unit}, {self.qualifier}"


@dataclass(frozen=True)
class CostSummary:
    """A total, the lines behind it, and the materials it had to leave out.

    A summary with no lines is not an error and not a zero — it is a project
    whose materials are all unpriced, and it renders as exactly that.

    Parameters
    ----------
    lines : tuple[PriceLine, ...]
        Priced quantities contributing to the total.
    unpriced : tuple[str, ...]
        Labels of stock the design uses that carries no price at all.  These
        are named in every rendering: a total that quietly omits a material is
        worse than no total, because it looks complete.
    """

    lines: tuple[PriceLine, ...] = ()
    unpriced: tuple[str, ...] = ()

    @classmethod
    def of(
        cls,
        lines: Iterable[PriceLine] = (),
        unpriced: Iterable[str] = (),
    ) -> "CostSummary":
        """Build a summary from any iterables."""
        return cls(tuple(lines), tuple(unpriced))

    def __add__(self, other: "CostSummary") -> "CostSummary":
        """Merge two summaries, keeping every line and every gap."""
        if not isinstance(other, CostSummary):  # pragma: no cover - defensive
            return NotImplemented
        return CostSummary(self.lines + other.lines, self.unpriced + other.unpriced)

    @property
    def total(self) -> float | None:
        """Sum of the priced lines, or ``None`` if nothing is priced.

        This is a *partial* total whenever :attr:`unpriced` is non-empty, which
        is why nothing renders it without :meth:`to_text`.
        """
        if not self.lines:
            return None
        return sum(line.amount for line in self.lines)

    @property
    def verified(self) -> bool:
        """``True`` if every contributing rate carries a date."""
        return bool(self.lines) and all(line.verified for line in self.lines)

    @property
    def complete(self) -> bool:
        """``True`` if nothing the design uses was left out of the total."""
        return not self.unpriced

    @property
    def oldest_as_of(self) -> date | None:
        """The oldest date among the contributing rates, if all are dated.

        A total is only as current as its stalest ingredient, so this is the
        date a total is quoted with.
        """
        dates = [line.as_of for line in self.lines if line.as_of is not None]
        if not dates or len(dates) != len(self.lines):
            return None
        return min(dates)

    @property
    def earliest_valid_until(self) -> date | None:
        """The first sale end date among the contributing rates, if any.

        A total built partly from specials is only good until the first of
        them runs out, so that is the date it is quoted with.
        """
        ends = [line.valid_until for line in self.lines if line.valid_until is not None]
        return min(ends) if ends else None

    @property
    def sources(self) -> list[str]:
        """De-duplicated source descriptions, in first-seen order."""
        out: list[str] = []
        for line in self.lines:
            if line.source and line.source not in out:
                out.append(line.source)
        return out

    def qualifier(self) -> str:
        """Return the parenthetical a total must carry: dates, and what is missing."""
        parts = []
        oldest = self.oldest_as_of
        parts.append(
            f"prices as of {oldest.isoformat()}" if oldest else UNVERIFIED_MARKER
        )
        ends = self.earliest_valid_until
        if ends is not None:
            parts.append(f"includes sale prices ending {ends.isoformat()}")
        if self.unpriced:
            parts.append(f"excludes unpriced {', '.join(self.unpriced)}")
        return "; ".join(parts)

    def to_label(self) -> str:
        """Render the total compactly, for a pill or a badge.

        Shorter than :meth:`to_text` and still never bare — a figure small
        enough to fit in a card is exactly the one most likely to be read
        without its context.
        """
        if self.total is None:
            return "unpriced"
        oldest = self.oldest_as_of
        mark = f"as of {oldest.isoformat()}" if oldest else "unverified"
        partial = ", partial" if self.unpriced else ""
        return f"{format_money(self.total)} ({mark}{partial})"

    def to_text(self) -> str:
        """Render the total — never bare, never silently partial.

        Returns
        -------
        str
            ``'$1,097 (prices as of 2026-08-16)'``, or an explanation of why
            there is no total at all.
        """
        if self.total is None:
            if self.unpriced:
                return f"no priced stock — {', '.join(self.unpriced)} unpriced"
            return "nothing to price"
        return f"{format_money(self.total)} ({self.qualifier()})"


def sheet_for_key(inventory: "Inventory", key: str) -> "SheetStock | None":
    """Return the sheet entry a :func:`pack_by_material` key came from.

    The packer keys its results ``"{material} {nominal} ({size})"`` because a
    human has to read them.  Pricing needs the other direction, and rebuilding
    the same string is the only mapping that cannot drift from the one that
    produced it.

    Parameters
    ----------
    inventory : Inventory
        Stock inventory to search.
    key : str
        A key from :func:`woodshop.cutlist.optimize_2d.pack_by_material`.

    Returns
    -------
    SheetStock or None
        The matching entry, or ``None`` if the key names no stocked sheet.
    """
    for sheet in inventory.sheet_goods:
        if f"{sheet.material} {sheet.nominal_thickness} ({sheet.size_label})" == key:
            return sheet
    return None


def sheet_cost_summary(
    results: dict[str, "Cut2DResult"],
    inventory: "Inventory",
) -> CostSummary:
    """Price a sheet-goods nesting run.

    Parameters
    ----------
    results : dict[str, Cut2DResult]
        Nesting results as :func:`pack_by_material` returns them.
    inventory : Inventory
        Stock inventory supplying sheet prices and their provenance.

    Returns
    -------
    CostSummary
        One line per priced sheet group; every unpriced group named.
    """
    lines: list[PriceLine] = []
    unpriced: list[str] = []
    for key, result in results.items():
        if not result.sheets_used:
            continue
        sheet = sheet_for_key(inventory, key)
        if sheet is None or sheet.price_per_sheet is None:
            unpriced.append(key)
            continue
        lines.append(sheet.price_line(result.sheets_used))
    return CostSummary.of(lines, unpriced)
