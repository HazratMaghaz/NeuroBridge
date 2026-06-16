import inspect
# CNS JSON safety patch: prevents ndarray JSON serialization failures
from cns_multimodalai.inference.json_safety import patch_json_encoder
patch_json_encoder()

"""
RNA inference route for CNS-MultiModalAI GUI MVP.
"""

from typing import List, Optional
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from backend.app.services.inference_service import handle_rna_upload
from backend.app.services.batch_inference_service import handle_batch_rna_upload

router = APIRouter(prefix="/api/infer", tags=["Inference – RNA"])


@router.post("/rna")
async def infer_rna(
    file: UploadFile = File(..., description="RNA-seq expression CSV"),
    run_model: bool = Form(True, description="Run real frozen Phase 14 RNA inference"),
    make_canvas: bool = Form(False, description="Generate morphology canvas; slower"),
    max_cases: int | None = Form(None, description="Optional case limit for testing"),
    run_reference_morphology: bool = Form(False, description="Run coordinate-aware WSI patch retrieval"),
):
    """
    Upload RNA-seq CSV and optionally run GBM/LGG-like inference.

    Expected CSV format:

    - Rows = samples/patients
    - Required column: patient_id
    - Gene columns should preferably be Ensembl IDs such as ENSG000001...
    - This matches the frozen Phase 14 RNA inference pipeline.
    """
    try:
        return await handle_rna_upload(
            file=file,
            run_model=run_model,
            make_canvas=make_canvas,
            max_cases=max_cases,
            run_reference_morphology=run_reference_morphology,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=repr(e)) from e

@router.post("/rna/batch")
async def infer_rna_batch(request: Request):
    """
    Robust RNA batch endpoint.

    Accepts multipart fields:
    - file=<single CSV>
    - files=<one CSV or many CSVs>

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

    def form_bool(name: str, default: bool = False) -> bool:
        v = form.get(name)
        if v is None:
            return default
        return str(v).lower() in {"1", "true", "yes", "on"}

    def form_int(name: str, default: int = 0) -> int:
        v = form.get(name)
        if v is None or v == "":
            return default
        try:
            return int(v)
        except Exception:
            return default

    run_model = form_bool("run_model", True)
    run_canvas = False
    run_reference_morphology = form_bool("run_reference_morphology", False)
    batch_ref_morph_n = form_int("batch_ref_morph_n", 0)

    if not uploaded_files:
        return {
            "status": "failed",
            "batch_mode": True,
            "batch_type": "rna",
            "error": "No RNA CSV file(s) received. Expected multipart field 'file' or 'files'.",
        }

    # Compatibility layer:
    # batch_inference_service.py changed during Phase 16G, so only pass
    # arguments that the current handle_batch_rna_upload() actually accepts.
    candidate_kwargs = {
        "files": uploaded_files,
        "file": uploaded_files[0] if uploaded_files else None,
        "run_model": run_model,
        "run_canvas": run_canvas,
        "run_reference_morphology": run_reference_morphology,
        "batch_ref_morph_n": batch_ref_morph_n,
    }

    sig = inspect.signature(handle_batch_rna_upload)
    accepted_kwargs = {
        k: v for k, v in candidate_kwargs.items()
        if k in sig.parameters
    }

    result = handle_batch_rna_upload(**accepted_kwargs)
    if inspect.isawaitable(result):
        result = await result
    return result


