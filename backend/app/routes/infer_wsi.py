"""
WSI Local Path inference route for CNS-MultiModalAI GUI MVP.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.app.services.inference_service import handle_wsi_path_inference

router = APIRouter(prefix="/api/infer", tags=["Inference – WSI"])

class WsiPathRequest(BaseModel):
    wsi_path: str
    max_patches: int = 100
    run_model: bool = True

@router.post("/wsi-path")
async def infer_wsi_path(req: WsiPathRequest):
    """
    Local path inference for Whole Slide Images (.svs/.tif).
    
    This endpoint extracts patches from a local WSI file and optionally
    runs the frozen CTransPath inference and gene/pathway prediction pipelines.
    """
    try:
        return handle_wsi_path_inference(
            wsi_path=req.wsi_path,
            max_patches=req.max_patches,
            run_model=req.run_model
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=repr(e)) from e
