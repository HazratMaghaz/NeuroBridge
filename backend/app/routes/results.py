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
