"""Visual output: cut-list tables, nesting diagrams, 3-D views, and CAD export."""

from woodshop.render.export import export_assembly
from woodshop.render.model3d import (
    MATERIAL_COLORS,
    STANDARD_VIEWS,
    View,
    render_assembly,
)
from woodshop.render.sheets import (
    render_board_diagram,
    render_sheet_diagram,
    save_figures,
)
from woodshop.render.tables import render_cut_list

__all__ = [
    "render_cut_list",
    "render_sheet_diagram",
    "render_board_diagram",
    "render_assembly",
    "export_assembly",
    "save_figures",
    "View",
    "STANDARD_VIEWS",
    "MATERIAL_COLORS",
]
