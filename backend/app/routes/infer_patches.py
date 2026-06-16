"""
Patch ZIP upload route for CNS-MultiModalAI GUI MVP.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

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
async def infer_patches_batch(
    file: UploadFile = File(..., description="ZIP archive containing one subfolder per sample"),
):
    """
    Batch processing for a ZIP containing multiple sample folders.
    """
    try:
        return await handle_batch_patch_upload(file=file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=repr(e)) from e
