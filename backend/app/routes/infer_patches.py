import inspect
"""
Patch ZIP upload route for CNS-MultiModalAI GUI MVP.
"""

from typing import List, Optional
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from backend.app.services.inference_service import handle_patch_upload
from backend.app.services.batch_inference_service import handle_batch_patch_upload

router = APIRouter(prefix="/api/infer", tags=["Inference – Patches"])


@router.post("/patches")
async def infer_patches(
    file: UploadFile = File(..., description="ZIP archive of patch images"),
    run_model: bool = Form(False, description="Run real frozen Phase 14 patch inference"),
):
    """
    Upload a ZIP archive of histology patch images.

    This endpoint safely saves/extracts patches. If run_model=true, it runs the frozen CTransPath patch inference pipeline.
    """
    try:
        return await handle_patch_upload(file=file, run_model=run_model)
    except Exception as e:
        raise HTTPException(status_code=400, detail=repr(e)) from e

@router.post("/patches/batch")
async def infer_patches_batch(request: Request):
    """
    Robust Patch/Image batch endpoint.

    Accepts multipart fields:
    - file=<single ZIP>
    - files=<one ZIP or many ZIPs>

    Manual form parsing avoids FastAPI/Pydantic 422 list parsing issues.
    """
    form = await request.form()

    uploaded_files = []

    for item in form.getlist("files"):
        if hasattr(item, "filename") and item.filename:
            uploaded_files.append(item)

    single_file = form.get("file")
    if single_file is not None and hasattr(single_file, "filename") and single_file.filename:
        uploaded_files.append(single_file)

    def form_bool(name: str, default: bool = True) -> bool:
        v = form.get(name)
        if v is None:
            return default
        return str(v).lower() in {"1", "true", "yes", "on"}

    run_model = form_bool("run_model", True)

    if not uploaded_files:
        return {
            "status": "failed",
            "batch_mode": True,
            "batch_type": "patches",
            "error": "No Patch ZIP file(s) received. Expected multipart field 'file' or 'files'.",
        }

    candidate_kwargs = {
        "files": uploaded_files,
        "file": uploaded_files[0] if uploaded_files else None,
        "run_model": run_model,
    }

    sig = inspect.signature(handle_batch_patch_upload)
    accepted_kwargs = {
        k: v for k, v in candidate_kwargs.items()
        if k in sig.parameters
    }

    result = handle_batch_patch_upload(**accepted_kwargs)
    if inspect.isawaitable(result):
        result = await result
    return result

