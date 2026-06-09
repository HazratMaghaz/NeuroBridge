"""
Backend service layer for CNS-MultiModalAI GUI MVP.

This module handles upload saving, safe ZIP extraction, and controlled calls
to the frozen Phase 14 inference package.

Research prototype only:
GBM/LGG-like similarity, not clinical diagnosis.
"""

from pathlib import Path
from datetime import datetime, timezone
import shutil
import zipfile
import uuid
from urllib.parse import quote

from fastapi import UploadFile

from cns_multimodalai.inference.predict_from_rna import run_rna_inference

PROJECT_ROOT = Path("/path/to/CNS-MultiModalAI")
GUI_RUN_ROOT = PROJECT_ROOT / "results" / "gui_mvp_runs"

WARNING_TEXT = (
    "⚠️ RESEARCH PROTOTYPE — output is GBM-like vs LGG-like similarity only. "
    "Not a pan-CNS classifier. Not for clinical use."
)

RNA_MAX_BYTES = 500 * 1024 * 1024
PATCH_ZIP_MAX_BYTES = 2 * 1024 * 1024 * 1024


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _safe_name(name: str) -> str:
    name = Path(name).name
    keep = []
    for ch in name:
        if ch.isalnum() or ch in {".", "_", "-"}:
            keep.append(ch)
        else:
            keep.append("_")
    cleaned = "".join(keep).strip("._")
    return cleaned or f"upload_{uuid.uuid4().hex[:8]}"


def _make_run_dir(prefix: str) -> Path:
    GUI_RUN_ROOT.mkdir(parents=True, exist_ok=True)
    run_dir = GUI_RUN_ROOT / f"{prefix}_{_timestamp()}_{uuid.uuid4().hex[:6]}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


async def _save_upload(file: UploadFile, dest: Path, max_bytes: int) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    total = 0

    with dest.open("wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise ValueError(f"Upload too large. Limit is {max_bytes} bytes.")
            f.write(chunk)

    return total




def _result_file_url(file_path: str | Path, run_dir: Path) -> str | None:
    """
    Convert an absolute result file path into a frontend-accessible API URL.
    """
    if not file_path:
        return None

    file_path = Path(file_path)
    run_dir = Path(run_dir)

    try:
        rel = file_path.resolve().relative_to(run_dir.resolve()).as_posix()
    except Exception:
        return None

    run_id = run_dir.name
    return f"/api/results/{run_id}/file?relative_path={quote(rel, safe='/')}"


def _safe_extract_zip(zip_path: Path, dest_dir: Path) -> None:
    """
    Safely extract ZIP while blocking path traversal.
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


async def handle_rna_upload(
    file: UploadFile,
    run_model: bool = True,
    make_canvas: bool = False,
    max_cases: int | None = None,
) -> dict:
    """
    Save uploaded RNA CSV and optionally run real frozen Phase 14 RNA inference.

    Expected CSV:
    patient_id, ENSG000001..., ENSG000002..., ...
    """
    run_dir = _make_run_dir("rna")
    filename = _safe_name(file.filename or "rna_upload.csv")
    input_csv = run_dir / filename

    bytes_saved = await _save_upload(file, input_csv, RNA_MAX_BYTES)

    response = {
        "status": "uploaded",
        "run_dir": str(run_dir),
        "input_csv": str(input_csv),
        "bytes_saved": bytes_saved,
        "warning": WARNING_TEXT,
        "inference_enabled": bool(run_model),
        "canvas_enabled": bool(make_canvas),
        "inference_result": None,
    }

    if run_model:
        try:
            result = run_rna_inference(
                expression_csv=input_csv,
                output_dir=run_dir / "inference",
                make_morphology_canvas=make_canvas,
                max_cases=max_cases,
            )

            response["status"] = "completed"
            response["inference_result"] = result

            pred_csv = Path(result["predictions_csv"])
            if pred_csv.exists():
                import pandas as pd

                pred_df = pd.read_csv(pred_csv)
                cols = [
                    c for c in [
                        "patient_id",
                        "prob_GBM_like",
                        "predicted_label",
                        "predicted_class",
                        "expression_strategy",
                        "shared_gene_count",
                        "selected_gene_count",
                    ]
                    if c in pred_df.columns
                ]

                response["prediction_preview"] = pred_df[cols].head(10).to_dict(orient="records")

            # Frontend-ready result URLs
            result_files = {
                "predictions_url": _result_file_url(result.get("predictions_csv"), run_dir),
                "report_url": _result_file_url(result.get("report_md"), run_dir),
                "canvas_index_url": _result_file_url(result.get("canvas_index_csv"), run_dir),
                "canvas_files": [],
            }

            canvas_index_csv = result.get("canvas_index_csv")
            if canvas_index_csv and Path(canvas_index_csv).exists():
                canvas_df = pd.read_csv(canvas_index_csv)
                for _, row in canvas_df.iterrows():
                    result_files["canvas_files"].append({
                        "patient_id": row.get("patient_id"),
                        "canvas_url": _result_file_url(row.get("canvas_path"), run_dir),
                        "retrieval_csv_url": _result_file_url(row.get("retrieval_csv"), run_dir),
                        "note": row.get("note"),
                    })

            response["result_files"] = result_files

        except Exception as e:
            response["status"] = "failed"
            response["error"] = repr(e)

    return response


async def handle_patch_upload(file: UploadFile, run_model: bool = False) -> dict:
    """
    Save and safely extract uploaded patch ZIP.

    Real patch inference is intentionally disabled by default in GUI MVP step 1.
    """
    run_dir = _make_run_dir("patches")
    filename = _safe_name(file.filename or "patches.zip")

    if not filename.lower().endswith(".zip"):
        raise ValueError("Patch upload must be a .zip archive.")

    zip_path = run_dir / filename
    patch_dir = run_dir / "patches"

    bytes_saved = await _save_upload(file, zip_path, PATCH_ZIP_MAX_BYTES)
    patch_dir.mkdir(parents=True, exist_ok=True)

    _safe_extract_zip(zip_path, patch_dir)

    image_exts = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"}
    n_images = sum(1 for p in patch_dir.rglob("*") if p.is_file() and p.suffix.lower() in image_exts)

    return {
        "status": "uploaded",
        "run_dir": str(run_dir),
        "zip_path": str(zip_path),
        "patch_dir": str(patch_dir),
        "bytes_saved": bytes_saved,
        "n_images_found": n_images,
        "warning": WARNING_TEXT,
        "inference_enabled": bool(run_model),
        "inference_result": None,
        "note": "Patch model inference is still disabled in this backend step. Enable after RNA endpoint is stable.",
    }
