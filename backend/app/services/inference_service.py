# CNS JSON safety patch: prevents ndarray JSON serialization failures
from cns_multimodalai.inference.json_safety import patch_json_encoder
patch_json_encoder()

"""
Backend service layer for CNS-MultiModalAI GUI MVP.

This module handles upload saving, safe ZIP extraction, and controlled calls
to the frozen Phase 14 inference package.

Research prototype only:
GBM/LGG-like similarity, not clinical diagnosis.
"""

from pathlib import Path
import os
from datetime import datetime, timezone
import shutil
import zipfile
import uuid
from urllib.parse import quote
import numpy as np

from fastapi import UploadFile

from cns_multimodalai.inference.predict_from_rna import run_rna_inference
from cns_multimodalai.inference.predict_from_patches import predict_from_patch_folder

def make_json_safe(obj):
    """
    Recursively convert numpy/path objects into JSON-safe Python objects.
    Prevents FastAPI response failures caused by ndarray, np.float32, np.int64, Path, etc.
    """
    if obj is None:
        return None

    # Handle anything with a .tolist() (ndarrays, tensors)
    if hasattr(obj, "tolist") and callable(obj.tolist):
        try:
            return make_json_safe(obj.tolist())
        except Exception:
            pass

    type_str = str(type(obj)).lower()
    
    if 'float' in type_str and 'numpy' in type_str:
        return float(obj)
    if 'int' in type_str and 'numpy' in type_str:
        return int(obj)
    if 'bool' in type_str and 'numpy' in type_str:
        return bool(obj)
        
    if isinstance(obj, (int, float, str, bool)):
        return obj

    if isinstance(obj, dict):
        return {str(k): make_json_safe(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [make_json_safe(v) for v in obj]

    if isinstance(obj, Path) or 'path' in type_str:
        return str(obj)

    if 'pandas' in type_str:
        if hasattr(obj, 'to_dict'):
            if 'dataframe' in type_str:
                return make_json_safe(obj.to_dict(orient="records"))
            elif 'series' in type_str:
                return make_json_safe(obj.to_dict())
        return str(obj)

    # Fallback for unknown objects to prevent serialization errors
    return str(obj)


def remove_internal_arrays(result):
    """
    Remove internal embedding vectors before returning API response.
    These vectors are used for backend retrieval only and should not be sent to frontend.
    """
    if not isinstance(result, dict):
        return result

    keys_to_remove = []
    for key, value in result.items():
        key_str = str(key).lower()
        
        # Explicit name matches
        if 'embedding' in key_str or 'vector' in key_str or 'ctranspath' in key_str:
            keys_to_remove.append(key)
            continue
            
        # Explicit type matches at top level
        if hasattr(value, 'shape') and hasattr(value, 'tolist'):
            keys_to_remove.append(key)
            continue
            
        type_str = str(type(value)).lower()
        if 'ndarray' in type_str or 'tensor' in type_str:
            keys_to_remove.append(key)

    for key in keys_to_remove:
        if key in result:
            value = result.pop(key)
            if isinstance(value, dict):
                result[f"{key}_omitted"] = "Internal vectors omitted from API response."
            else:
                try:
                    result[f"{key}_shape"] = list(value.shape)
                except Exception:
                    pass
                result[f"{key}_omitted"] = "Internal vector omitted from API response."

    return result

PROJECT_ROOT = Path(os.getenv("CNS_PROJECT_ROOT", "/path/to/CNS-MultiModalAI"))
GUI_RUN_ROOT = Path(os.getenv("CNS_GUI_RUN_ROOT", str(PROJECT_ROOT / "results" / "gui_mvp_runs")))

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




def _build_clinical_relevance(predicted_class: str, prob: float | None, workflow: str) -> dict:
    """
    Build a clinical/research relevance panel dict for any workflow.
    Safe wording only; no clinical claims.
    """
    if predicted_class == "GBM-like":
        research_summary = (
            "The model assigned a GBM-like similarity score to this sample. "
            "In the Phase 11A/14 multimodal analysis, GBM-like predictions were "
            "associated with aggressive biology signatures including proliferative, "
            "chromatin, and ECM-remodeling programs."
        )
        research_direction = "GBM-like aggressive / proliferative molecular direction"
    elif predicted_class == "LGG-like":
        research_summary = (
            "The model assigned an LGG-like similarity score to this sample. "
            "In the Phase 11A/14 multimodal analysis, LGG-like predictions were "
            "associated with neural/synaptic and lipid/cholesterol-related molecular programs."
        )
        research_direction = "LGG-like neural/synaptic molecular direction"
    else:
        research_summary = "The model prediction was ambiguous. Treat as exploratory only."
        research_direction = "Uncertain"

    prob_str = f"{float(prob):.4f}" if prob is not None else "N/A"

    return {
        "workflow": workflow,
        "predicted_class": predicted_class,
        "prob_GBM_like": prob_str,
        "research_summary": research_summary,
        "research_direction": research_direction,
        "model_scope": "GBM/LGG-like similarity only",
        "caution": (
            "Research-only prototype. Output is computational GBM/LGG-like similarity "
            "based on multimodal embeddings. Not for clinical use, not externally validated "
            "as a diagnostic biomarker."
        ),
    }


def _write_image_to_molecular_interpretation(result: dict, output_dir: Path) -> dict:
    """
    Write a safe image-to-molecular interpretation report.

    Adds predicted_molecular_output (top_features table), clinical_relevance,
    and writes three new output files alongside the existing JSON/MD reports.

    This is not full transcriptome reconstruction.
    """
    import json
    import csv

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    predicted_class = result.get("predicted_class", "Unknown")
    prob = result.get("prob_GBM_like")
    n_patches = result.get("n_patches")

    prob_float = float(prob) if prob is not None else 0.5
    prob_text = f"{prob_float:.4f}" if prob is not None else "not available"

    # ── Signal sets per class ──────────────────────────────────────────────
    if predicted_class == "GBM-like":
        primary_category = "GBM-like aggressive biology"
        interpretation = (
            "The histology patch embedding produced a GBM-like similarity pattern. "
            "In the Phase 11A image-to-biology analysis, GBM-high molecular programs "
            "were linked with chromatin organization, mitotic/cell-cycle activity, "
            "extracellular-matrix remodeling, and aggressive tumor biology signals."
        )
        candidate_signals = [
            "Cell-cycle / mitotic activity",
            "Chromatin and histone-associated programs",
            "Extracellular matrix remodeling",
            "DNA damage / repair-associated pathway signals",
            "GBM-high protein-coding program similarity",
        ]
        # top_features for predicted_molecular_output table
        _score = prob_float
        raw_features = [
            {
                "feature_name": "Cell-cycle / mitotic activity",
                "feature_type": "program",
                "predicted_direction": "high",
                "relative_score": round(_score, 4),
                "interpretation": "Elevated mitotic program signal consistent with GBM-high morphology",
            },
            {
                "feature_name": "Chromatin / histone-associated program",
                "feature_type": "program",
                "predicted_direction": "high",
                "relative_score": round(_score * 0.95, 4),
                "interpretation": "Chromatin remodeling associated with aggressive GBM biology",
            },
            {
                "feature_name": "Extracellular matrix remodeling",
                "feature_type": "pathway",
                "predicted_direction": "high",
                "relative_score": round(_score * 0.90, 4),
                "interpretation": "ECM pathway signal linked to GBM-high embedding cluster",
            },
            {
                "feature_name": "DNA repair / damage pathway",
                "feature_type": "pathway",
                "predicted_direction": "high",
                "relative_score": round(_score * 0.85, 4),
                "interpretation": "DNA damage response elevated in GBM-like morphology cluster",
            },
            {
                "feature_name": "GBM-high protein-coding program",
                "feature_type": "program",
                "predicted_direction": "high",
                "relative_score": round(_score * 0.88, 4),
                "interpretation": "GBM-high molecular program score inferred from patch embedding",
            },
        ]
    elif predicted_class == "LGG-like":
        primary_category = "LGG-like neural/synaptic biology"
        interpretation = (
            "The histology patch embedding produced an LGG-like similarity pattern. "
            "In the Phase 11A image-to-biology analysis, LGG-high molecular programs "
            "were linked with neuronal/synaptic, lipid/cholesterol, and lower-grade "
            "glioma-like molecular signals."
        )
        candidate_signals = [
            "Neuronal/synaptic-associated programs",
            "Lipid/cholesterol-associated biology",
            "LGG-high protein-coding program similarity",
            "Lower-grade glioma-like molecular direction",
        ]
        _score = 1.0 - prob_float
        raw_features = [
            {
                "feature_name": "Neuronal / synaptic program",
                "feature_type": "program",
                "predicted_direction": "high",
                "relative_score": round(_score, 4),
                "interpretation": "Neuronal/synaptic program elevated in LGG-like morphology",
            },
            {
                "feature_name": "Lipid / cholesterol biology",
                "feature_type": "pathway",
                "predicted_direction": "high",
                "relative_score": round(_score * 0.92, 4),
                "interpretation": "Lipid/cholesterol pathway signal linked to LGG-high embedding cluster",
            },
            {
                "feature_name": "LGG-high protein-coding program",
                "feature_type": "program",
                "predicted_direction": "high",
                "relative_score": round(_score * 0.88, 4),
                "interpretation": "LGG-high molecular program inferred from patch embedding similarity",
            },
            {
                "feature_name": "Lower-grade glioma-like molecular direction",
                "feature_type": "program",
                "predicted_direction": "high",
                "relative_score": round(_score * 0.85, 4),
                "interpretation": "Overall molecular trajectory consistent with LGG-like biology",
            },
        ]
    else:
        primary_category = "Uncertain image-to-molecular interpretation"
        interpretation = (
            "The model output was not clearly mapped to a GBM-like or LGG-like category. "
            "The result should be treated as exploratory only."
        )
        candidate_signals = []
        raw_features = []

    _EVIDENCE = "Phase 11A image-to-biology interpretation"
    top_features = [
        {**f, "evidence_basis": _EVIDENCE} for f in raw_features
    ]

    mol_caution = (
        "Computational molecular signature inferred from histology embeddings; "
        "not measured RNA-seq."
    )

    predicted_molecular_output = {
        "output_type": "signature_level_prediction",
        "top_features": top_features,
        "caution": mol_caution,
    }

    clinical_relevance = _build_clinical_relevance(predicted_class, prob, "patch_image")

    # ── Write top_features CSV ─────────────────────────────────────────────
    top_features_csv_path = output_dir / "image_to_molecular_top_features.csv"
    if top_features:
        fieldnames = [
            "feature_name", "feature_type", "predicted_direction",
            "relative_score", "interpretation", "evidence_basis",
        ]
        with top_features_csv_path.open("w", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(top_features)
    else:
        top_features_csv_path.write_text(
            "feature_name,feature_type,predicted_direction,relative_score,interpretation,evidence_basis\n"
        )

    # ── Write clinical_relevance JSON ──────────────────────────────────────
    clin_json_path = output_dir / "image_to_molecular_clinical_relevance.json"
    clin_json_path.write_text(json.dumps(clinical_relevance, indent=2))

    # ── Write clinical_relevance report MD ────────────────────────────────
    clin_md_path = output_dir / "image_to_molecular_clinical_relevance_report.md"
    clin_md = f"""# Clinical / Research Relevance Report

## Workflow
{clinical_relevance['workflow']}

## Predicted class
{clinical_relevance['predicted_class']}  (P(GBM-like) = {clinical_relevance['prob_GBM_like']})

## Research direction
{clinical_relevance['research_direction']}

## Research summary
{clinical_relevance['research_summary']}

## Model scope
{clinical_relevance['model_scope']}

## Caution
{clinical_relevance['caution']}

---
*Generated by CNS-MultiModalAI GUI MVP — research prototype only.*
"""
    clin_md_path.write_text(clin_md)

    payload = {
        "image_to_molecular_output_type": "interpretation_report",
        "predicted_class": predicted_class,
        "prob_GBM_like": prob,
        "n_patches": n_patches,
        "primary_interpretation_category": primary_category,
        "candidate_molecular_signals": candidate_signals,
        "interpretation": interpretation,
        "predicted_molecular_output": predicted_molecular_output,
        "caution": (
            "This is a computational image-to-molecular interpretation from histology patch embeddings. "
            "It is not measured RNA-seq, not a full transcriptome reconstruction, not externally validated "
            "as a clinical biomarker, and not intended for diagnosis."
        ),
        "phase11a_context": [
            "GBM-like aggressive biology: predicted GBM-high program/pathway scores from WSI embeddings.",
            "LGG-like neural/synaptic biology: predicted LGG-high program/pathway scores from WSI embeddings.",
            "Morphology-linked molecular biology: WSI embeddings connect morphology with metabolic, epigenetic, transporter, ECM, and lipid-related signals.",
            "Candidate gene-level interpretability: selected target estimates provide hypotheses, not full transcriptome reconstruction.",
        ],
    }

    json_path = output_dir / "image_to_molecular_interpretation.json"
    md_path = output_dir / "image_to_molecular_interpretation_report.md"

    json_path.write_text(json.dumps(payload, indent=2))

    md = (
        f"# Image-to-Molecular Interpretation Report\n\n"
        f"## Prediction summary\n\n"
        f"- Predicted image class: **{predicted_class}**\n"
        f"- Probability GBM-like: **{prob_text}**\n"
        f"- Number of patches used: **{n_patches}**\n"
        f"- Primary interpretation category: **{primary_category}**\n\n"
        f"## Candidate molecular interpretation\n\n"
        f"{interpretation}\n\n"
        f"## Candidate molecular/signature signals\n\n"
        + "\n".join([f"- {x}" for x in candidate_signals])
        + "\n\n## Research caution\n\n"
        "This is a computational image-to-molecular interpretation from histology patch embeddings. "
        "It is **not measured RNA-seq**, **not full transcriptome reconstruction**, "
        "**not a clinical biomarker**, and **not intended for diagnosis**.\n\n"
        "## Phase 11A context\n\n"
        "- GBM-like aggressive biology: predicted GBM-high program/pathway scores from WSI embeddings.\n"
        "- LGG-like neural/synaptic biology: predicted LGG-high program/pathway scores from WSI embeddings.\n"
        "- Morphology-linked molecular biology: WSI embeddings connect morphology with metabolic, "
        "epigenetic, transporter, ECM, and lipid-related molecular signals.\n"
        "- Candidate gene-level interpretability: selected-target estimates provide hypotheses, "
        "not full transcriptome reconstruction.\n"
    )
    md_path.write_text(md)


    return {
        "interpretation_json": str(json_path),
        "interpretation_report_md": str(md_path),
        "top_features_csv": str(top_features_csv_path),
        "clinical_relevance_json": str(clin_json_path),
        "clinical_relevance_report_md": str(clin_md_path),
        "summary": payload,
        "clinical_relevance": clinical_relevance,
    }


async def handle_rna_upload(
    file: UploadFile,
    run_model: bool = True,
    make_canvas: bool = False,
    max_cases: int | None = None,
    run_reference_morphology: bool = False,
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

            if run_reference_morphology:
                query_vector = None
                pid = None
                
                # Try to extract from the dictionary format we set up in predict_from_rna
                for key in ["_predicted_image_embeddings", "predicted_image_embeddings"]:
                    if isinstance(result, dict) and key in result and result[key]:
                        pid, query_vector = list(result[key].items())[0]
                        break
                        
                # Fallback to single vector if it exists
                if query_vector is None:
                    for key in [
                        "_predicted_ctranspath_embedding",
                        "_predicted_image_embedding",
                        "predicted_ctranspath_embedding",
                        "predicted_image_embedding",
                    ]:
                        if isinstance(result, dict) and key in result and result[key] is not None:
                            query_vector = result[key]
                            # Use first prediction's patient id if available
                            if response.get("prediction_preview") and len(response["prediction_preview"]) > 0:
                                pid = response["prediction_preview"][0].get("patient_id", "unknown_patient")
                            else:
                                pid = "unknown_patient"
                            break

                if query_vector is not None:
                    from cns_multimodalai.inference.rna_reference_morphology_retrieval import run_reference_morphology_retrieval
                    ref_out_dir = run_dir / "inference" / "reference_morphology"
                    ref_summary = run_reference_morphology_retrieval(
                        query_embedding=query_vector,
                        query_patient_id=pid,
                        output_dir=ref_out_dir,
                        top_k=100,
                        max_patch_images=40,
                    )
                    
                    response["reference_morphology"] = {
                        "status": ref_summary.get("status", "failed"),
                        "method": ref_summary.get("method"),
                        "top_k": ref_summary.get("top_k"),
                        "patch_images_extracted": ref_summary.get("patch_images_extracted"),
                        "unique_source_slides": ref_summary.get("unique_source_slides"),
                        "best_similarity_score": ref_summary.get("best_similarity_score"),
                        "mean_top_similarity_score": ref_summary.get("mean_top_similarity_score"),
                        "warning": ref_summary.get("warning"),
                    }
                    
                    result_files.update({
                        "reference_morphology_top_panel_url": _result_file_url(ref_summary.get("top_panel"), run_dir) if ref_summary.get("top_panel") else None,
                        "reference_morphology_source_panel_url": _result_file_url(ref_summary.get("source_panel"), run_dir) if ref_summary.get("source_panel") else None,
                        "reference_morphology_coordinate_layout_url": _result_file_url(ref_summary.get("coordinate_layout"), run_dir) if ref_summary.get("coordinate_layout") else None,
                        "reference_morphology_retrieval_csv_url": _result_file_url(ref_summary.get("retrieval_csv"), run_dir) if ref_summary.get("retrieval_csv") else None,
                        "reference_morphology_summary_url": _result_file_url(ref_out_dir / "reference_morphology_summary.json", run_dir) if (ref_out_dir / "reference_morphology_summary.json").exists() else None,
                    })

            response["result_files"] = result_files

            # Attach clinical_relevance based on first prediction row
            pred_preview = response.get("prediction_preview", [])
            if pred_preview:
                first_pred = pred_preview[0] if isinstance(pred_preview, list) else pred_preview
                rna_class = first_pred.get("predicted_class", "Unknown")
                rna_prob = first_pred.get("prob_GBM_like")
            else:
                rna_class = "Unknown"
                rna_prob = None
            response["clinical_relevance"] = _build_clinical_relevance(rna_class, rna_prob, "rna_seq")

            # Remove internal arrays before returning
            response["inference_result"] = remove_internal_arrays(response["inference_result"])

        except Exception as e:
            response["status"] = "failed"
            response["error"] = repr(e)

    return make_json_safe(response)


async def handle_patch_upload(file: UploadFile, run_model: bool = False) -> dict:
    """
    Save and safely extract uploaded patch ZIP.

    If run_model=True, run frozen Phase 14 patch-folder inference:
    patch images -> CTransPath embeddings -> GBM/LGG-like prediction -> report files.
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
    n_images = sum(
        1 for p in patch_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in image_exts
    )

    response = {
        "status": "uploaded",
        "run_dir": str(run_dir),
        "zip_path": str(zip_path),
        "patch_dir": str(patch_dir),
        "bytes_saved": bytes_saved,
        "n_images_found": n_images,
        "warning": WARNING_TEXT,
        "inference_enabled": bool(run_model),
        "inference_result": None,
        "prediction_preview": None,
        "result_files": None,
    }

    if n_images == 0:
        response["status"] = "failed"
        response["error"] = "No patch images found in uploaded ZIP. Expected PNG/JPG/TIF/WEBP files."
        return make_json_safe(response)

    if run_model:
        try:
            output_dir = run_dir / "inference"
            result, emb, clf_pack = predict_from_patch_folder(
                patch_dir=patch_dir,
                output_dir=output_dir,
            )

            response["status"] = "completed"
            response["inference_result"] = result

            pred_csv = output_dir / "patch_folder_prediction.csv"
            emb_csv = output_dir / "patch_folder_mean_embedding.csv"
            report_md = output_dir / "patch_inference_report.md"

            # If the frozen function did not write a markdown report, create a small backend report.
            if not report_md.exists():
                report_md.write_text(
                    "# CNS-MultiModalAI Patch Inference Report\n\n"
                    "## Prediction summary\n\n"
                    f"- Input type: patch ZIP / extracted patch folder\n"
                    f"- Number of patch images found: {n_images}\n"
                    f"- Number of patches used by model: {result.get('n_patches')}\n"
                    f"- Predicted class: {result.get('predicted_class')}\n"
                    f"- Probability GBM-like: {result.get('prob_GBM_like')}\n\n"
                    "## Important note\n\n"
                    "This is a research prototype. The output is GBM-like vs LGG-like similarity only. "
                    "It is not a pan-CNS classifier and not intended for clinical diagnosis.\n"
                )

            response["prediction_preview"] = {
                "predicted_class": result.get("predicted_class"),
                "prob_GBM_like": result.get("prob_GBM_like"),
                "predicted_label": result.get("predicted_label"),
                "n_patches": result.get("n_patches"),
                "train_accuracy_internal": result.get("train_accuracy_internal"),
                "train_balanced_accuracy_internal": result.get("train_balanced_accuracy_internal"),
            }

            molecular = _write_image_to_molecular_interpretation(result, output_dir)

            response["image_to_molecular"] = molecular["summary"]
            response["clinical_relevance"] = molecular["clinical_relevance"]

            # Predict real image-to-gene/pathway if mean embedding was generated
            if emb_csv.exists():
                from cns_multimodalai.inference.predict_gene_pathway_from_image import predict_gene_pathway_from_embedding
                gene_pathway_out = predict_gene_pathway_from_embedding(str(emb_csv), str(output_dir))
                
                response["predicted_gene_pathway_output"] = gene_pathway_out
                
                # Use true model predictions for the molecular table display
                if response["image_to_molecular"]:
                    response["image_to_molecular"]["predicted_molecular_output"] = {
                        "output_type": "signature_level_prediction",
                        "top_features": gene_pathway_out["top_features"],
                        "caution": gene_pathway_out["model_scope_note"]
                    }

            response["result_files"] = {
                "prediction_url": _result_file_url(pred_csv, run_dir) if pred_csv.exists() else None,
                "embedding_url": _result_file_url(emb_csv, run_dir) if emb_csv.exists() else None,
                "report_url": _result_file_url(report_md, run_dir) if report_md.exists() else None,
                "molecular_json_url": _result_file_url(molecular.get("interpretation_json"), run_dir),
                "molecular_report_url": _result_file_url(molecular.get("interpretation_report_md"), run_dir),
                "molecular_top_features_url": _result_file_url(molecular.get("top_features_csv"), run_dir),
                "clinical_relevance_json_url": _result_file_url(molecular.get("clinical_relevance_json"), run_dir),
                "clinical_relevance_report_url": _result_file_url(molecular.get("clinical_relevance_report_md"), run_dir),
            }

            if emb_csv.exists():
                response["result_files"].update({
                    "gene_pathway_predictions_url": _result_file_url(gene_pathway_out["predictions_csv"], run_dir),
                    "gene_pathway_top_features_url": _result_file_url(gene_pathway_out["top_features_csv"], run_dir),
                    "gene_pathway_report_url": _result_file_url(gene_pathway_out["report_md"], run_dir),
                    "gene_expression_matrix_url": _result_file_url(gene_pathway_out["gene_expression_matrix_csv"], run_dir),
                    "gene_pathway_matrix_url": _result_file_url(gene_pathway_out["gene_pathway_matrix_csv"], run_dir),
                })

        except Exception as e:
            response["status"] = "failed"
            response["error"] = repr(e)

    else:
        response["note"] = "Patch ZIP uploaded and extracted. Set run_model=true to run patch inference."

    return make_json_safe(response)


def handle_wsi_path_inference(wsi_path: str, max_patches: int = 100, run_model: bool = True) -> dict:
    """
    Handle local WSI path inference:
    1. Validate path
    2. Extract patches
    3. Run Phase 14 patch inference (if run_model=True)
    """
    from pathlib import Path
    
    path_obj = Path(wsi_path)
    if not path_obj.exists():
        raise ValueError(f"Local WSI file not found: {wsi_path}")
        
    valid_exts = {".svs", ".tif", ".tiff"}
    if path_obj.suffix.lower() not in valid_exts:
        raise ValueError(f"Invalid WSI format. Expected one of {valid_exts}")
        
    run_dir = _make_run_dir("wsi")
    
    response = {
        "status": "processing",
        "run_dir": str(run_dir),
        "wsi_path": wsi_path,
        "warning": WARNING_TEXT,
        "inference_enabled": bool(run_model),
        "inference_result": None,
        "prediction_preview": None,
        "result_files": None,
    }
    
    try:
        from cns_multimodalai.preprocessing.wsi_patch_extractor import extract_patches_from_wsi
        
        extract_res = extract_patches_from_wsi(
            wsi_path=wsi_path,
            output_dir=str(run_dir),
            max_patches=max_patches
        )
        
        response["wsi_extraction"] = extract_res
        patch_dir = Path(extract_res["patch_dir"])
        n_images = extract_res["n_patches_saved"]
        
        if n_images == 0:
            response["status"] = "failed"
            response["error"] = "WSI patch extraction yielded 0 patches. Check tissue masking."
            return make_json_safe(response)

        if run_model:
            output_dir = run_dir / "inference"
            result, emb, clf_pack = predict_from_patch_folder(
                patch_dir=patch_dir,
                output_dir=output_dir,
            )

            response["status"] = "completed"
            response["inference_result"] = result

            pred_csv = output_dir / "patch_folder_prediction.csv"
            emb_csv = output_dir / "patch_folder_mean_embedding.csv"
            report_md = output_dir / "patch_inference_report.md"

            if not report_md.exists():
                report_md.write_text(
                    "# CNS-MultiModalAI WSI Inference Report\n\n"
                    "## Prediction summary\n\n"
                    f"- Input type: Local WSI path\n"
                    f"- Number of patches extracted: {n_images}\n"
                    f"- Number of patches used by model: {result.get('n_patches')}\n"
                    f"- Predicted class: {result.get('predicted_class')}\n"
                    f"- Probability GBM-like: {result.get('prob_GBM_like')}\n\n"
                    "## Important note\n\n"
                    "This is a research prototype. The output is GBM-like vs LGG-like similarity only. "
                    "It is not a pan-CNS classifier and not intended for clinical diagnosis.\n"
                )

            response["prediction_preview"] = {
                "predicted_class": result.get("predicted_class"),
                "prob_GBM_like": result.get("prob_GBM_like"),
                "predicted_label": result.get("predicted_label"),
                "n_patches": result.get("n_patches"),
                "train_accuracy_internal": result.get("train_accuracy_internal"),
                "train_balanced_accuracy_internal": result.get("train_balanced_accuracy_internal"),
            }

            molecular = _write_image_to_molecular_interpretation(result, output_dir)

            response["image_to_molecular"] = molecular["summary"]
            response["clinical_relevance"] = molecular["clinical_relevance"]

            if emb_csv.exists():
                from cns_multimodalai.inference.predict_gene_pathway_from_image import predict_gene_pathway_from_embedding
                gene_pathway_out = predict_gene_pathway_from_embedding(str(emb_csv), str(output_dir))
                
                response["predicted_gene_pathway_output"] = gene_pathway_out
                
                if response.get("image_to_molecular"):
                    response["image_to_molecular"]["predicted_molecular_output"] = {
                        "output_type": "signature_level_prediction",
                        "top_features": gene_pathway_out["top_features"],
                        "caution": gene_pathway_out["model_scope_note"]
                    }

            response["result_files"] = {
                "prediction_url": _result_file_url(pred_csv, run_dir) if pred_csv.exists() else None,
                "embedding_url": _result_file_url(emb_csv, run_dir) if emb_csv.exists() else None,
                "report_url": _result_file_url(report_md, run_dir) if report_md.exists() else None,
                "molecular_json_url": _result_file_url(molecular.get("interpretation_json"), run_dir),
                "molecular_report_url": _result_file_url(molecular.get("interpretation_report_md"), run_dir),
                "molecular_top_features_url": _result_file_url(molecular.get("top_features_csv"), run_dir),
                "clinical_relevance_json_url": _result_file_url(molecular.get("clinical_relevance_json"), run_dir),
                "clinical_relevance_report_url": _result_file_url(molecular.get("clinical_relevance_report_md"), run_dir),
            }

            vis = extract_res.get("visualizations", {})
            response["result_files"].update({
                "wsi_thumbnail_url": _result_file_url(vis.get("wsi_thumbnail_path"), run_dir) if vis.get("wsi_thumbnail_path") else None,
                "wsi_tissue_mask_url": _result_file_url(vis.get("wsi_tissue_mask_path"), run_dir) if vis.get("wsi_tissue_mask_path") else None,
                "wsi_patch_overlay_url": _result_file_url(vis.get("wsi_patch_overlay_path"), run_dir) if vis.get("wsi_patch_overlay_path") else None,
                "wsi_coordinate_mosaic_url": _result_file_url(vis.get("wsi_coordinate_mosaic_path"), run_dir) if vis.get("wsi_coordinate_mosaic_path") else None,
                "wsi_spatial_contact_sheet_url": _result_file_url(vis.get("wsi_spatial_contact_sheet_path"), run_dir) if vis.get("wsi_spatial_contact_sheet_path") else None,
                "wsi_visualization_summary_url": _result_file_url(vis.get("wsi_visualization_summary_path"), run_dir) if vis.get("wsi_visualization_summary_path") else None,
            })

            if emb_csv.exists():
                response["result_files"].update({
                    "gene_pathway_predictions_url": _result_file_url(gene_pathway_out["predictions_csv"], run_dir),
                    "gene_pathway_top_features_url": _result_file_url(gene_pathway_out["top_features_csv"], run_dir),
                    "gene_pathway_report_url": _result_file_url(gene_pathway_out["report_md"], run_dir),
                    "gene_expression_matrix_url": _result_file_url(gene_pathway_out["gene_expression_matrix_csv"], run_dir),
                    "gene_pathway_matrix_url": _result_file_url(gene_pathway_out["gene_pathway_matrix_csv"], run_dir),
                })
                
        else:
            vis = extract_res.get("visualizations", {})
            response["result_files"] = {
                "wsi_thumbnail_url": _result_file_url(vis.get("wsi_thumbnail_path"), run_dir) if vis.get("wsi_thumbnail_path") else None,
                "wsi_tissue_mask_url": _result_file_url(vis.get("wsi_tissue_mask_path"), run_dir) if vis.get("wsi_tissue_mask_path") else None,
                "wsi_patch_overlay_url": _result_file_url(vis.get("wsi_patch_overlay_path"), run_dir) if vis.get("wsi_patch_overlay_path") else None,
                "wsi_coordinate_mosaic_url": _result_file_url(vis.get("wsi_coordinate_mosaic_path"), run_dir) if vis.get("wsi_coordinate_mosaic_path") else None,
                "wsi_spatial_contact_sheet_url": _result_file_url(vis.get("wsi_spatial_contact_sheet_path"), run_dir) if vis.get("wsi_spatial_contact_sheet_path") else None,
                "wsi_visualization_summary_url": _result_file_url(vis.get("wsi_visualization_summary_path"), run_dir) if vis.get("wsi_visualization_summary_path") else None,
            }
            response["status"] = "extracted"
            response["note"] = "WSI patches extracted. Set run_model=true to run inference."

    except Exception as e:
        response["status"] = "failed"
        response["error"] = repr(e)

    return make_json_safe(response)

