"""Export an assembly to interchange formats, and preview it interactively.

The model is real solid geometry, so it can leave this project as STEP for
another CAD package or STL for a viewer or printer.  Nothing here is
woodworking-specific — it exists because a model nobody can open is a model
nobody checks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = ["export_assembly", "preview"]


def export_assembly(
    assembly: Any,
    output_step: str | Path | None = None,
    output_stl: str | Path | None = None,
) -> list[Path]:
    """Write *assembly* to STEP and/or STL.

    Parameters
    ----------
    assembly : build123d.Compound
        The assembly to export.
    output_step : str or Path, optional
        Destination for a STEP file.
    output_stl : str or Path, optional
        Destination for an STL mesh.

    Returns
    -------
    list[Path]
        The files written, in the order requested.
    """
    from build123d import export_step, export_stl

    written: list[Path] = []
    if output_step is not None:
        export_step(assembly, str(output_step))
        written.append(Path(output_step))
    if output_stl is not None:
        export_stl(assembly, str(output_stl))
        written.append(Path(output_stl))
    return written


def preview(assembly: Any, port: int = 3939) -> bool:
    """Show *assembly* in an ``ocp_vscode`` viewer if one is reachable.

    Parameters
    ----------
    assembly : build123d.Compound
        The assembly to show.
    port : int, optional
        Viewer port, default 3939.

    Returns
    -------
    bool
        ``True`` if the model was sent to a viewer, ``False`` if ``ocp_vscode``
        is not installed or no viewer is listening.  Never raises — a missing
        viewer is not a reason to fail a build.
    """
    try:
        from ocp_vscode import set_port, show  # type: ignore[import]

        set_port(port)
        show(assembly)
        return True
    except Exception:
        return False
