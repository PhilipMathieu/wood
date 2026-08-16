"""Re-exports of bd_warehouse fasteners actually stocked in the shop.

Add entries here as you acquire hardware. Each entry re-exports a fastener
class from ``bd_warehouse`` under a project-local alias so the rest of the
codebase is insulated from upstream name changes.

Example::

    from woodshop.hardware import WoodScrew_6x1_5
    screw = WoodScrew_6x1_5(fastener_type="wood_screw")
"""

from __future__ import annotations

# Lazy imports — only materialise when actually used, to avoid forcing
# bd_warehouse to be fully resolved at import time if the user has not
# installed it yet.

try:
    from bd_warehouse.fastener import (  # type: ignore[import]
        CounterSunkScrew,
        PanHeadScrew,
        SetScrew,
    )

    __all__ = ["CounterSunkScrew", "PanHeadScrew", "SetScrew"]
except ImportError:  # pragma: no cover
    __all__ = []
