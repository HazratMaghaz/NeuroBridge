import os
import shutil
import uuid
from pathlib import Path
import pandas as pd
import numpy as np
from fastapi import UploadFile

from backend.app.services.inference_service import (
    _make_run_dir,
    _save_upload,
    _result_file_url,
    _safe_extract_zip,
    remove_internal_arrays,
    make_json_safe,
    RNA_MAX_BYTES,
    PATCH_ZIP_MAX_BYTES
)

from cns_multimodalai.inference.predict_from_rna import run_rna_inference
from cns_multimodalai.inference.rna_reference_morphology_retrieval import run_reference_morphology_retrieval
from cns_multimodalai.inference.predict_from_patches import run_patch_inference, extract_and_classify_ctranspath
from cns_multimodalai.inference.predict_wsi_local import run_local_wsi_inference


async def handle_batch_rna_upload(
    file: UploadFile,
    batch_ref_morph_n: int = 3,
    run_reference_morphology: bool = True
) -> dict:
    run_dir = _make_run_dir("rna_batch")
    response = {
        "status": "uploaded",
        "batch_mode": True,
        "batch_type": "rna",
        "run_dir": str(run_dir),
        "n_samples_total": 0,
        "n_samples_completed": 0,
        "n_samples_failed": 0,
        "reference_morphology_samples_requested": batch_ref_morph_n if run_reference_morphology else 0,
        "reference_morphology_samples_completed": 0,
        "result_files": {}
    }
    
    try:
        # Save upload
        input_dir = run_dir / "input"
        input_dir.mkdir(parents=True, exist_ok=True)
        csv_path = input_dir / file.filename
        await _save_upload(file, csv_path, RNA_MAX_BYTES)
        
        # Read CSV and format IDs
        df = pd.read_csv(csv_path)
        
        id_col = None
        for col in ["patient_id", "sample_id", "case_id"]:
            if col in df.columns:
                id_col = col
                break
        
        if not id_col:
            df["sample_id"] = [f"sample_{i:04d}" for i in range(1, len(df) + 1)]
            id_col = "sample_id"
            
        if id_col != "patient_id":
            df["patient_id"] = df[id_col]
            
        df.to_csv(csv_path, index=False)
        response["n_samples_total"] = len(df)
        
        # Run inference
        inference_out_dir = run_dir / "inference"
        result = run_rna_inference(
            expression_csv=str(csv_path),
            output_dir=inference_out_dir,
            make_morphology_canvas=False
        )
        
        emb_dict = {}
        for key in ["_predicted_image_embeddings", "predicted_image_embeddings"]:
            if key in result:
                emb_dict = result[key]
                break

        response["inference_result"] = remove_internal_arrays(result)
        
        pred_csv = inference_out_dir / "rna_gbm_lgg_like_predictions.csv"
        errors = []
        
        if pred_csv.exists():
            pred_df = pd.read_csv(pred_csv)
            per_sample_dir = run_dir / "per_sample"
            per_sample_dir.mkdir(exist_ok=True)
            
            pids = pred_df["patient_id"].tolist()
            ref_summary_rows = []
            
            for i, pid in enumerate(pids):
                try:
                    # Save per-sample prediction
                    pid_dir = per_sample_dir / str(pid)
                    pid_dir.mkdir(exist_ok=True)
                    row_df = pred_df[pred_df["patient_id"] == pid]
                    row_df.to_csv(pid_dir / f"{pid}_prediction.csv", index=False)
                    
                    # Morphology retrieval
                    if run_reference_morphology and i < batch_ref_morph_n:
                        if pid in emb_dict:
                            query_vector = emb_dict[pid]
                            ref_out_dir = pid_dir / "reference_morphology"
                            ref_summary = run_reference_morphology_retrieval(
                                query_embedding=query_vector,
                                query_patient_id=pid,
                                output_dir=ref_out_dir,
                                top_k=100,
                                max_patch_images=40,
                            )
                            ref_summary["patient_id"] = pid
                            ref_summary_rows.append(ref_summary)
                            response["reference_morphology_samples_completed"] += 1
                            
                    response["n_samples_completed"] += 1
                except Exception as e:
                    errors.append({"sample_id": pid, "error": str(e)})
                    response["n_samples_failed"] += 1
                    
            if run_reference_morphology and ref_summary_rows:
                batch_ref_df = pd.DataFrame(ref_summary_rows)
                batch_ref_csv = inference_out_dir / "batch_reference_morphology_summary.csv"
                batch_ref_df.to_csv(batch_ref_csv, index=False)
                response["result_files"]["batch_reference_morphology_summary_url"] = _result_file_url(batch_ref_csv, run_dir)
                
            response["result_files"]["batch_summary_url"] = _result_file_url(pred_csv, run_dir)
            response["result_files"]["batch_report_url"] = _result_file_url(inference_out_dir / "rna_inference_report.md", run_dir)
            response["result_files"]["batch_manifest_url"] = _result_file_url(csv_path, run_dir)
            
        if errors:
            errors_df = pd.DataFrame(errors)
            errors_csv = run_dir / "batch_errors.csv"
            errors_df.to_csv(errors_csv, index=False)
            response["result_files"]["batch_errors_url"] = _result_file_url(errors_csv, run_dir)
            response["status"] = "completed_with_errors"
        else:
            response["status"] = "completed"

    except Exception as e:
        response["status"] = "failed"
        response["error"] = repr(e)

    return make_json_safe(response)


async def handle_batch_patch_upload(file: UploadFile) -> dict:
    run_dir = _make_run_dir("patch_batch")
    response = {
        "status": "uploaded",
        "batch_mode": True,
        "batch_type": "patch",
        "run_dir": str(run_dir),
        "n_samples_total": 0,
        "n_samples_completed": 0,
        "n_samples_failed": 0,
        "result_files": {}
    }
    
    try:
        input_dir = run_dir / "input"
        input_dir.mkdir(parents=True, exist_ok=True)
        zip_path = input_dir / file.filename
        await _save_upload(file, zip_path, PATCH_ZIP_MAX_BYTES)
        
        extract_dir = run_dir / "extracted_patches"
        _safe_extract_zip(zip_path, extract_dir)
        
        # Look for subdirectories
        subdirs = [d for d in extract_dir.iterdir() if d.is_dir()]
        
        if not subdirs:
            response["status"] = "failed"
            response["error"] = "No subfolders found in ZIP. For batch patch mode, the ZIP must contain one folder per sample."
            return make_json_safe(response)
            
        response["n_samples_total"] = len(subdirs)
        
        per_sample_dir = run_dir / "per_sample"
        per_sample_dir.mkdir(exist_ok=True)
        
        all_preds = []
        all_expr = []
        all_pathways = []
        errors = []
        
        for subdir in subdirs:
            pid = subdir.name
            out_dir = per_sample_dir / pid
            out_dir.mkdir(exist_ok=True)
            
            try:
                emb_dict, pred_path = extract_and_classify_ctranspath(subdir, output_dir=out_dir)
                
                if pred_path and Path(pred_path).exists():
                    p_df = pd.read_csv(pred_path)
                    p_df["patient_id"] = pid
                    all_preds.append(p_df)
                    
                expr_csv = out_dir / "predicted_gene_expression_matrix.csv"
                pathway_csv = out_dir / "predicted_pathway_activity_matrix.csv"
                
                if expr_csv.exists():
                    e_df = pd.read_csv(expr_csv)
                    e_df["patient_id"] = pid
                    all_expr.append(e_df)
                    
                if pathway_csv.exists():
                    pw_df = pd.read_csv(pathway_csv)
                    pw_df["patient_id"] = pid
                    all_pathways.append(pw_df)
                    
                response["n_samples_completed"] += 1
            except Exception as e:
                errors.append({"sample_id": pid, "error": str(e)})
                response["n_samples_failed"] += 1
                
        # Aggregate
        batch_out_dir = run_dir / "batch_results"
        batch_out_dir.mkdir(exist_ok=True)
        
        if all_preds:
            batch_pred_df = pd.concat(all_preds, ignore_index=True)
            batch_pred_csv = batch_out_dir / "batch_patch_predictions_summary.csv"
            batch_pred_df.to_csv(batch_pred_csv, index=False)
            response["result_files"]["batch_summary_url"] = _result_file_url(batch_pred_csv, run_dir)
            
        if all_expr:
            batch_expr_df = pd.concat(all_expr, ignore_index=True)
            batch_expr_csv = batch_out_dir / "batch_gene_expression_matrix.csv"
            batch_expr_df.to_csv(batch_expr_csv, index=False)
            response["result_files"]["batch_gene_expression_url"] = _result_file_url(batch_expr_csv, run_dir)
            
        if all_pathways:
            batch_pw_df = pd.concat(all_pathways, ignore_index=True)
            batch_pw_csv = batch_out_dir / "batch_gene_pathway_matrix.csv"
            batch_pw_df.to_csv(batch_pw_csv, index=False)
            response["result_files"]["batch_gene_pathway_url"] = _result_file_url(batch_pw_csv, run_dir)
            
        if errors:
            errors_df = pd.DataFrame(errors)
            errors_csv = run_dir / "batch_errors.csv"
            errors_df.to_csv(errors_csv, index=False)
            response["result_files"]["batch_errors_url"] = _result_file_url(errors_csv, run_dir)
            response["status"] = "completed_with_errors"
        else:
            response["status"] = "completed"
            
    except Exception as e:
        response["status"] = "failed"
        response["error"] = repr(e)

    return make_json_safe(response)


async def handle_batch_wsi_upload(file: UploadFile) -> dict:
    run_dir = _make_run_dir("wsi_batch")
    response = {
        "status": "uploaded",
        "batch_mode": True,
        "batch_type": "wsi",
        "run_dir": str(run_dir),
        "n_samples_total": 0,
        "n_samples_completed": 0,
        "n_samples_failed": 0,
        "result_files": {}
    }
    
    try:
        input_dir = run_dir / "input"
        input_dir.mkdir(parents=True, exist_ok=True)
        csv_path = input_dir / file.filename
        await _save_upload(file, csv_path, RNA_MAX_BYTES) # re-use size limit for CSV
        
        df = pd.read_csv(csv_path)
        required_cols = {"sample_id", "wsi_path"}
        if not required_cols.issubset(set(df.columns)):
            response["status"] = "failed"
            response["error"] = f"Manifest CSV missing required columns. Need at least: {required_cols}"
            return make_json_safe(response)
            
        response["n_samples_total"] = len(df)
        
        per_sample_dir = run_dir / "per_sample"
        per_sample_dir.mkdir(exist_ok=True)
        
        all_preds = []
        all_expr = []
        all_pathways = []
        errors = []
        
        for idx, row in df.iterrows():
            pid = str(row["sample_id"])
            wsi_path = str(row["wsi_path"])
            max_p = int(row.get("max_patches", 300))
            
            out_dir = per_sample_dir / pid
            out_dir.mkdir(exist_ok=True)
            
            try:
                res = run_local_wsi_inference(wsi_path, output_dir=out_dir, max_patches=max_p)
                pred_path = res.get("predictions_csv")
                
                if pred_path and Path(pred_path).exists():
                    p_df = pd.read_csv(pred_path)
                    p_df["patient_id"] = pid
                    p_df["wsi_path"] = wsi_path
                    all_preds.append(p_df)
                    
                expr_csv = out_dir / "predicted_gene_expression_matrix.csv"
                pathway_csv = out_dir / "predicted_pathway_activity_matrix.csv"
                
                if expr_csv.exists():
                    e_df = pd.read_csv(expr_csv)
                    e_df["patient_id"] = pid
                    all_expr.append(e_df)
                    
                if pathway_csv.exists():
                    pw_df = pd.read_csv(pathway_csv)
                    pw_df["patient_id"] = pid
                    all_pathways.append(pw_df)
                    
                response["n_samples_completed"] += 1
            except Exception as e:
                errors.append({"sample_id": pid, "wsi_path": wsi_path, "error": str(e)})
                response["n_samples_failed"] += 1
                
        # Aggregate
        batch_out_dir = run_dir / "batch_results"
        batch_out_dir.mkdir(exist_ok=True)
        
        if all_preds:
            batch_pred_df = pd.concat(all_preds, ignore_index=True)
            batch_pred_csv = batch_out_dir / "batch_wsi_summary.csv"
            batch_pred_df.to_csv(batch_pred_csv, index=False)
            response["result_files"]["batch_summary_url"] = _result_file_url(batch_pred_csv, run_dir)
            
        if all_expr:
            batch_expr_df = pd.concat(all_expr, ignore_index=True)
            batch_expr_csv = batch_out_dir / "batch_gene_expression_matrix.csv"
            batch_expr_df.to_csv(batch_expr_csv, index=False)
            response["result_files"]["batch_gene_expression_url"] = _result_file_url(batch_expr_csv, run_dir)
            
        if all_pathways:
            batch_pw_df = pd.concat(all_pathways, ignore_index=True)
            batch_pw_csv = batch_out_dir / "batch_gene_pathway_matrix.csv"
            batch_pw_df.to_csv(batch_pw_csv, index=False)
            response["result_files"]["batch_gene_pathway_url"] = _result_file_url(batch_pw_csv, run_dir)
            
        response["result_files"]["batch_manifest_url"] = _result_file_url(csv_path, run_dir)
            
        if errors:
            errors_df = pd.DataFrame(errors)
            errors_csv = run_dir / "batch_errors.csv"
            errors_df.to_csv(errors_csv, index=False)
            response["result_files"]["batch_errors_url"] = _result_file_url(errors_csv, run_dir)
            response["status"] = "completed_with_errors"
        else:
            response["status"] = "completed"
            
    except Exception as e:
        response["status"] = "failed"
        response["error"] = repr(e)

    return make_json_safe(response)
