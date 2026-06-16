"""
RNA inference route for CNS-MultiModalAI GUI MVP.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from backend.app.services.inference_service import handle_rna_upload

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
