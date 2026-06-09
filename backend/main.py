"""
FastAPI backend for CNS-MultiModalAI GUI MVP.

Research prototype only:
GBM/LGG-like similarity, not clinical diagnosis.
"""

from pathlib import Path
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Make frozen Phase 14 package importable.
PROJECT_ROOT = Path("/path/to/CNS-MultiModalAI")
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from backend.app.routes import health, infer_rna, infer_patches, results

app = FastAPI(
    title="CNS-MultiModalAI API",
    description="""
# CNS-MultiModalAI GUI MVP

⚠️ **RESEARCH PROTOTYPE — not for clinical use.**

This API exposes the CNS-MultiModalAI inference pipeline for academic thesis demonstration.

Outputs are GBM-like vs LGG-like research similarity outputs only.
""",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Important:
# infer_rna.py and infer_patches.py already define prefix="/api/infer".
# Therefore, do NOT add prefix="/api/infer" here again.
app.include_router(health.router, prefix="/api")
app.include_router(infer_rna.router)
app.include_router(infer_patches.router)
app.include_router(results.router)


@app.get("/")
def root():
    return {
        "project": "CNS-MultiModalAI",
        "status": "ok",
        "docs": "/docs",
        "warning": (
            "Research prototype only. GBM/LGG-like similarity outputs. "
            "Not a pan-CNS classifier and not for clinical use."
        ),
    }
