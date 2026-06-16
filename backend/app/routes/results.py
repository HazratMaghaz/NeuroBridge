"""
Safe result-file access route for CNS-MultiModalAI GUI MVP.
"""

from pathlib import Path
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

PROJECT_ROOT = Path(os.getenv("CNS_PROJECT_ROOT", "/path/to/CNS-MultiModalAI"))
GUI_RUN_ROOT = Path(os.getenv("CNS_GUI_RUN_ROOT", str(PROJECT_ROOT / "results" / "gui_mvp_runs")))

router = APIRouter(prefix="/api/results", tags=["Results"])


@router.get("/{run_id}/file")
def get_result_file(run_id: str, relative_path: str):
    """
    Serve a result file from a specific GUI run folder.

    Security:
    - Only serves files inside results/gui_mvp_runs/{run_id}
    - Blocks path traversal
    """
    run_dir = (GUI_RUN_ROOT / run_id).resolve()
    if not run_dir.exists() or not run_dir.is_dir():
        raise HTTPException(status_code=404, detail="Run folder not found.")

    target = (run_dir / relative_path).resolve()

    try:
        target.relative_to(run_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Unsafe file path blocked.") from exc

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found.")

    return FileResponse(target)


@router.get("/{run_id}/deepzoom/{relative_path:path}")
async def get_deepzoom_file(run_id: str, relative_path: str):
    """
    Serve Deep Zoom .dzi and tile files from:
    results/gui_mvp_runs/<run_id>/deepzoom/

    This route is needed because OpenSeadragon resolves tile paths relative
    to the DZI URL. Query-string based file serving is not reliable for DZI tiles.
    """
    import os
    from fastapi import HTTPException

    run_root = Path(os.environ.get("CNS_GUI_RUN_ROOT", "/path/to/CNS-MultiModalAI/results/gui_mvp_runs"))
    run_dir = (run_root / run_id).resolve()
    deepzoom_root = (run_dir / "deepzoom").resolve()
    target = (deepzoom_root / relative_path).resolve()

    if not str(target).startswith(str(deepzoom_root)):
        raise HTTPException(status_code=400, detail="Invalid DeepZoom path.")

    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="DeepZoom file not found.")

    suffix = target.suffix.lower()
    media_type = "application/octet-stream"
    if suffix == ".dzi":
        media_type = "application/xml"
    elif suffix in [".jpg", ".jpeg"]:
        media_type = "image/jpeg"
    elif suffix == ".png":
        media_type = "image/png"

    return FileResponse(target, media_type=media_type)

