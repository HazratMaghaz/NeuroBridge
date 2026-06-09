"""
GET /api/health

Returns the project name, version, and status.

⚠️  RESEARCH PROTOTYPE — not validated for clinical use.
"""

from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter()

# ---------------------------------------------------------------------------
# Metadata pulled from the frozen src package at import time.
# No heavy modules are loaded here.
# ---------------------------------------------------------------------------
try:
    from cns_multimodalai import __version__, __project__
except ImportError:  # graceful fallback if src/ not on sys.path yet
    __version__ = "unknown"
    __project__ = "CNS-MultiModalAI"

_WARNING = (
    "⚠️  RESEARCH PROTOTYPE — This service is a proof-of-concept built "
    "during academic thesis research. The underlying models are GBM/LGG-focused and "
    "output GBM-like vs LGG-like similarity scores only. They are NOT a "
    "pan-CNS classifier and are NOT intended for clinical diagnosis or "
    "patient management."
)


@router.get("/health", summary="API health check")
def health_check():
    """
    Returns the project status, package version, and a research-prototype
    warning.  Always returns HTTP 200 when the server is reachable.
    """
    return {
        "status": "ok",
        "project": __project__,
        "version": __version__,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "endpoints": {
            "POST /api/infer/rna":     "Upload an RNA-seq CSV for GBM/LGG-like inference",
            "POST /api/infer/patches": "Upload a ZIP of patch images for patch-based inference",
        },
        "warning": _WARNING,
    }
