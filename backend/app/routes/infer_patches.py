"""
POST /api/infer/patches

Accepts a ZIP file upload containing patch images and extracts it under
results/gui_mvp_runs/patches_<timestamp>/.

⚠️  RESEARCH PROTOTYPE — not validated for clinical use.
"""

import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.app.services.inference_service import handle_patch_upload

router = APIRouter()

_ACCEPTED_MIME = {
    "application/zip",
    "application/x-zip-compressed",
    "application/octet-stream",
}
_MAX_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB guard-rail


@router.post("/patches", summary="Upload patch ZIP for image-based inference (placeholder)")
async def infer_patches(
    file: UploadFile = File(..., description="ZIP archive of .jpg/.png patch images"),
):
    """
    **Research Prototype** — Accepts a ZIP archive of histology patch images,
    extracts it to a timestamped run folder under ``results/gui_mvp_runs/``,
    and returns run metadata including how many images were found.

    Actual model inference (``predict_from_patch_folder()``) is **not**
    triggered automatically in this MVP build.  See
    ``app/services/inference_service.py`` for the placeholder comment showing
    where to enable it.

    ZIP contents
    ------------
    * Flat or nested folder of ``.jpg``, ``.jpeg``, ``.png``, ``.tif``,
      or ``.tiff`` patch images.
    * Recommended patch size: 224×224 px (matching CTransPath input).
    * The service will walk all sub-directories recursively.
    """
    # ── basic validation ─────────────────────────────────────────────────────
    if file.content_type not in _ACCEPTED_MIME and not (
        file.filename or ""
    ).lower().endswith(".zip"):
        raise HTTPException(
            status_code=415,
            detail="Only ZIP archives are accepted for patch upload.",
        )

    # ── buffer to temp file, then hand off to service ────────────────────────
    with tempfile.NamedTemporaryFile(
        suffix=".zip", delete=False, prefix="cns_patch_upload_"
    ) as tmp:
        tmp_path = Path(tmp.name)
        total = 0
        chunk_size = 1024 * 512  # 512 KB
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX_BYTES:
                tmp_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"Upload exceeds {_MAX_BYTES // (1024**3)} GB limit.",
                )
            tmp.write(chunk)

    try:
        result = handle_patch_upload(tmp_path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    if result.get("status") == "error":
        raise HTTPException(status_code=422, detail=result["detail"])

    return result
