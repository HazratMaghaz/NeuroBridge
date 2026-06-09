"""
CNS-MultiModalAI GUI MVP — FastAPI application entry point.

⚠️  RESEARCH PROTOTYPE
This API is a proof-of-concept built during academic thesis research.
It is NOT validated for clinical use and must NOT be used for patient
management or medical decision-making.

Usage
-----
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

The ``--reload`` flag is for development only; omit it in production.
"""

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Make the frozen src package importable when the server is launched from the
# project root (uvicorn backend.main:app).
# In production you would install the package via `pip install -e src/` or
# add it to PYTHONPATH instead.
# ---------------------------------------------------------------------------
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.routes import health, infer_rna, infer_patches

# ---------------------------------------------------------------------------
# Application metadata
# ---------------------------------------------------------------------------
_DESCRIPTION = """
## CNS-MultiModalAI GUI MVP

**⚠️ RESEARCH PROTOTYPE — not for clinical use.**

This REST API exposes the CNS-MultiModalAI inference pipeline for development
and demonstration purposes.  It accepts RNA-seq expression CSVs and
histology-patch ZIPs and saves them to run folders under
`results/gui_mvp_runs/`.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Service status and project metadata |
| POST | `/api/infer/rna` | Upload RNA-seq CSV (placeholder inference) |
| POST | `/api/infer/patches` | Upload patch ZIP (placeholder inference) |

All responses include a `warning` field reiterating the research-prototype
status of the underlying models.
"""

app = FastAPI(
    title="CNS-MultiModalAI API",
    description=_DESCRIPTION,
    version="0.1.0-mvp",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS — allow all origins in the MVP (restrict to the GUI domain in prod)
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # ← tighten to GUI origin before any deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health.router,        prefix="/api",        tags=["Health"])
app.include_router(infer_rna.router,     prefix="/api/infer",  tags=["Inference – RNA"])
app.include_router(infer_patches.router, prefix="/api/infer",  tags=["Inference – Patches"])


# ---------------------------------------------------------------------------
# Root redirect to docs
# ---------------------------------------------------------------------------
from fastapi.responses import RedirectResponse  # noqa: E402

@app.get("/", include_in_schema=False)
def root():
    """Redirect bare root to the interactive API docs."""
    return RedirectResponse(url="/docs")
