"""
POST /api/infer/rna

Accepts a CSV file upload (RNA-seq expression matrix) and saves it under
results/gui_mvp_runs/rna_<timestamp>/.

⚠️  RESEARCH PROTOTYPE — not validated for clinical use.
"""

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.app.services.inference_service import handle_rna_upload

router = APIRouter()

_ACCEPTED_MIME = {"text/csv", "application/csv", "application/octet-stream"}
_MAX_BYTES = 500 * 1024 * 1024  # 500 MB guard-rail


@router.post("/rna", summary="Upload RNA-seq CSV for GBM/LGG-like inference (placeholder)")
async def infer_rna(file: UploadFile = File(..., description="RNA-seq expression CSV")):
    """
    **Research Prototype** — Accepts an RNA-seq expression CSV, saves it to a
    timestamped run folder under ``results/gui_mvp_runs/``, and returns run
    metadata.

    Actual model inference (``run_rna_inference()``) is **not** triggered
    automatically in this MVP build.  See
    ``app/services/inference_service.py`` for the placeholder comment showing
    where to enable it.

    Expected CSV format
    -------------------
    * Rows = samples/patients
    * Required column: patient_id
    * Gene columns should preferably be Ensembl IDs such as ENSG000001...
    * This matches the frozen Phase 14 RNA inference pipeline.
    """
    # ── basic validation ─────────────────────────────────────────────────────
    if file.content_type not in _ACCEPTED_MIME and not (
        file.filename or ""
    ).lower().endswith(".csv"):
        raise HTTPException(
            status_code=415,
            detail="Only CSV files are accepted for RNA-seq upload.",
        )

    # ── buffer to temp file, then hand off to service ────────────────────────
    with tempfile.NamedTemporaryFile(
        suffix=".csv", delete=False, prefix="cns_rna_upload_"
    ) as tmp:
        tmp_path = Path(tmp.name)
        total = 0
        chunk_size = 1024 * 256  # 256 KB
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX_BYTES:
                tmp_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"Upload exceeds {_MAX_BYTES // (1024*1024)} MB limit.",
                )
            tmp.write(chunk)

    # rename with the original filename so it lands nicely in the run dir
    named_path = tmp_path.parent / (file.filename or "expression_upload.csv")
    tmp_path.rename(named_path)

    try:
        result = handle_rna_upload(named_path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        named_path.unlink(missing_ok=True)

    return result
