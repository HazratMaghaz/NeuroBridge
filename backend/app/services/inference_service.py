"""
Inference service — thin wrapper around the frozen cns_multimodalai package.

⚠️  RESEARCH PROTOTYPE — not validated for clinical use.

Design intent
-------------
* All heavy model calls (CTransPath, LightGBM, morphology canvas) are
  intentionally **commented-out / placeholder** in the MVP.
* Only file I/O and path management run automatically.
* When you are ready to enable real inference, uncomment the relevant blocks
  and ensure the model weights are present at the paths defined in
  ``src/cns_multimodalai/config.py``.
"""

import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Output root for all GUI runs.
# Must stay under results/ so it lands in the protected data area and is
# never accidentally deleted by backend refactors.
# ---------------------------------------------------------------------------
GUI_RUNS_ROOT = Path("/path/to/CNS-MultiModalAI/results/gui_mvp_runs")

_WARNING = (
    "⚠️  RESEARCH PROTOTYPE — output is GBM-like vs LGG-like similarity only. "
    "Not a pan-CNS classifier. Not for clinical use."
)



def _safe_extract_zip(zip_path: Path, dest_dir: Path) -> None:
    """
    Safely extract a ZIP archive while preventing path traversal.

    This prevents files such as ../../evil.py from escaping the run folder.
    """
    dest_dir = Path(dest_dir).resolve()
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            target = (dest_dir / member.filename).resolve()
            try:
                target.relative_to(dest_dir)
            except ValueError as exc:
                raise ValueError(f"Unsafe ZIP path blocked: {member.filename}") from exc
        zf.extractall(dest_dir)


def _make_run_dir(prefix: str) -> Path:
    """Create a timestamped run directory under GUI_RUNS_ROOT."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = GUI_RUNS_ROOT / f"{prefix}_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


# ---------------------------------------------------------------------------
# RNA inference
# ---------------------------------------------------------------------------

def handle_rna_upload(csv_path: Path) -> dict:
    """
    Save the uploaded RNA CSV to a dedicated run folder and prepare the
    inference result envelope.

    Heavy model call is PLACEHOLDER — uncomment when ready.

    Parameters
    ----------
    csv_path : Path
        Temporary path where the uploaded CSV was saved by the route handler.

    Returns
    -------
    dict
        Run metadata including output directory, file paths, and status.
    """
    run_dir = _make_run_dir("rna")
    dest_csv = run_dir / csv_path.name
    shutil.copy2(csv_path, dest_csv)

    result = {
        "status": "uploaded",
        "run_dir": str(run_dir),
        "input_csv": str(dest_csv),
        "warning": _WARNING,
        "inference_result": None,  # populated below when inference is enabled
    }

    # ------------------------------------------------------------------
    # ▼▼▼  PLACEHOLDER — uncomment to run RNA inference  ▼▼▼
    # ------------------------------------------------------------------
    # from cns_multimodalai.inference.predict_from_rna import run_rna_inference
    #
    # inference_result = run_rna_inference(
    #     expression_csv=dest_csv,
    #     output_dir=run_dir,
    #     make_morphology_canvas=False,   # set True to generate morphology canvas
    #     strategy="log2_fpkm_uq_plus1",
    # )
    # result["status"] = "complete"
    # result["inference_result"] = inference_result
    # ------------------------------------------------------------------

    return result


# ---------------------------------------------------------------------------
# Patch-based inference
# ---------------------------------------------------------------------------

def handle_patch_upload(zip_path: Path) -> dict:
    """
    Extract the uploaded patch ZIP to a dedicated run folder and prepare the
    inference result envelope.

    Heavy model call is PLACEHOLDER — uncomment when ready.

    Parameters
    ----------
    zip_path : Path
        Temporary path where the uploaded ZIP was saved by the route handler.

    Returns
    -------
    dict
        Run metadata including output directory, extracted patch directory,
        and status.
    """
    run_dir = _make_run_dir("patches")
    patch_dir = run_dir / "patches"
    patch_dir.mkdir(parents=True, exist_ok=True)

    _safe_extract_zip(zip_path, patch_dir)

    # Count extracted images for a quick sanity check
    image_extensions = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}
    n_images = sum(
        1 for p in patch_dir.rglob("*") if p.suffix.lower() in image_extensions
    )

    result = {
        "status": "uploaded",
        "run_dir": str(run_dir),
        "patch_dir": str(patch_dir),
        "n_images_found": n_images,
        "warning": _WARNING,
        "inference_result": None,  # populated below when inference is enabled
    }

    if n_images == 0:
        result["status"] = "error"
        result["detail"] = (
            "No image files found in the uploaded ZIP. "
            "Expected .jpg/.jpeg/.png/.tif/.tiff files."
        )
        return result

    # ------------------------------------------------------------------
    # ▼▼▼  PLACEHOLDER — uncomment to run patch-based inference  ▼▼▼
    # ------------------------------------------------------------------
    # from cns_multimodalai.inference.predict_from_patches import (
    #     predict_from_patch_folder,
    # )
    #
    # inference_result, emb, clf_pack = predict_from_patch_folder(
    #     patch_dir=patch_dir,
    #     output_dir=run_dir,
    # )
    # result["status"] = "complete"
    # result["inference_result"] = inference_result
    # ------------------------------------------------------------------

    return result
