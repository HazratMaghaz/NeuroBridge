import os
import json
import pandas as pd
import numpy as np
import joblib

from cns_multimodalai import config

MODEL_DIR = os.path.join(str(config.PROJECT_ROOT), "models", "phase15g_image_to_gene_pathway")

def predict_gene_pathway_from_embedding(
    embedding_csv, 
    output_dir, 
    top_n=25,
    run_id=None,
    sample_id=None,
    source_type="image_embedding"
):
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Load one-row image embedding
    df = pd.read_csv(embedding_csv)
    
    # 2. Load model and artifacts
    model_path = os.path.join(MODEL_DIR, "ridge_model.joblib")
    x_scaler_path = os.path.join(MODEL_DIR, "x_scaler.joblib")
    y_scaler_path = os.path.join(MODEL_DIR, "y_scaler.joblib")
    target_cols_path = os.path.join(MODEL_DIR, "target_cols.json")
    image_feature_cols_path = os.path.join(MODEL_DIR, "image_feature_cols.json")
    
    if not all(os.path.exists(p) for p in [model_path, x_scaler_path, y_scaler_path, target_cols_path, image_feature_cols_path]):
        raise FileNotFoundError(f"Missing Phase 15G model artifacts in {MODEL_DIR}")
        
    model = joblib.load(model_path)
    x_scaler = joblib.load(x_scaler_path)
    y_scaler = joblib.load(y_scaler_path)
    with open(target_cols_path, "r") as f:
        target_cols = json.load(f)
    with open(image_feature_cols_path, "r") as f:
        expected_features = json.load(f)

    # 3. Select 768 CTransPath features robustly and map columns
    input_col_map = {}
    for c in df.columns:
        if c.startswith("ctranspath"):
            digits = ''.join(filter(str.isdigit, c))
            if digits:
                input_col_map[int(digits)] = c

    x_cols = []
    missing = []
    for exp_feat in expected_features:
        if exp_feat in df.columns:
            x_cols.append(exp_feat)
        else:
            digits = ''.join(filter(str.isdigit, exp_feat))
            if digits and int(digits) in input_col_map:
                x_cols.append(input_col_map[int(digits)])
            else:
                missing.append(exp_feat)

    if missing:
        raise ValueError(f"Missing mapping for expected features. First 10 missing: {missing[:10]}")

    X_raw = df[x_cols].values
        
    # 4. Scale X
    X_scaled = x_scaler.transform(X_raw)
    
    # 5. Predict Y_scaled
    Y_pred_scaled = model.predict(X_scaled)
    
    # 6. Inverse transform Y
    Y_pred = y_scaler.inverse_transform(Y_pred_scaled)
    
    scores = Y_pred[0]
    
    # 7. Create full prediction table
    predictions = []
    for tgt, score in zip(target_cols, scores):
        target_type = tgt.split("__")[0]
        target_display_name = tgt.replace(f"{target_type}__", "").replace("_", " ")
        predictions.append({
            "target_name": tgt,
            "target_type": target_type,
            "target_display_name": target_display_name,
            "predicted_score": float(score)
        })
        
    pred_df = pd.DataFrame(predictions)
    pred_csv_path = os.path.join(output_dir, "image_to_gene_pathway_predictions.csv")
    pred_df.to_csv(pred_csv_path, index=False)
    
    # 7b. Create matrix format outputs
    if not run_id:
        # Default run_id to parent dir of output_dir
        run_id = os.path.basename(os.path.dirname(os.path.abspath(output_dir)))
    if not sample_id:
        sample_id = run_id
        
    matrix_base = {
        "run_id": run_id,
        "sample_id": sample_id,
        "source_type": source_type
    }
    
    # Full pathway/gene matrix
    pathway_matrix_dict = matrix_base.copy()
    for tgt, score in zip(target_cols, scores):
        pathway_matrix_dict[tgt] = score
    pathway_matrix_df = pd.DataFrame([pathway_matrix_dict])
    pathway_matrix_csv_path = os.path.join(output_dir, "image_to_gene_pathway_prediction_matrix.csv")
    pathway_matrix_df.to_csv(pathway_matrix_csv_path, index=False)
    
    # Gene expression matrix (only 'gene__' targets)
    expr_matrix_dict = matrix_base.copy()
    for tgt, score in zip(target_cols, scores):
        if tgt.startswith("gene__"):
            clean_gene = tgt.replace("gene__", "")
            expr_matrix_dict[clean_gene] = score
    expr_matrix_df = pd.DataFrame([expr_matrix_dict])
    expr_matrix_csv_path = os.path.join(output_dir, "image_to_gene_expression_matrix.csv")
    expr_matrix_df.to_csv(expr_matrix_csv_path, index=False)
    
    # 8. Create top feature table
    pred_df["abs_score"] = pred_df["predicted_score"].abs()
    top_df = pred_df.sort_values(by="abs_score", ascending=False).head(top_n).copy()
    
    top_features = []
    for _, row in top_df.iterrows():
        score = row["predicted_score"]
        direction = "high" if score >= 0 else "low"
        tgt_name = row["target_name"]
        tgt_type = row["target_type"]
        
        # Rule-based interpretation
        tgt_lower = tgt_name.lower()
        if "histone" in tgt_lower or "chromatin" in tgt_lower:
            interp = "chromatin-associated signal"
        elif any(k in tgt_lower for k in ["aurka", "ccnb", "kif", "cdca", "cell_cycle", "mitotic"]):
            interp = "proliferative/cell-cycle signal"
        elif any(k in tgt_lower for k in ["col4", "ecm", "emt", "rho", "angpt2", "extracellular"]):
            interp = "ECM/invasion/vascular remodeling signal"
        elif "synap" in tgt_lower or "neural" in tgt_lower:
            interp = "neural/synaptic signal"
        else:
            interp = "image-derived molecular signature target"
            
        feat_dict = {
            "feature_name": row["target_display_name"],
            "feature_type": tgt_type,
            "predicted_score": round(score, 4),
            "predicted_direction": direction,
            "relative_score": round(score, 4), # For backwards compatibility with frontend PatchTopFeature type
            "interpretation": interp,
            "evidence_basis": "Phase 15G frozen image-to-gene/pathway Ridge model"
        }
        top_features.append(feat_dict)
        
    top_features_csv_path = os.path.join(output_dir, "image_to_gene_pathway_top_features.csv")
    top_features_df = pd.DataFrame(top_features)
    top_features_df.to_csv(top_features_csv_path, index=False)
    
    # 9. Create markdown report
    report_md_path = os.path.join(output_dir, "image_to_gene_pathway_report.md")
    md = "# Image-to-Gene/Pathway Inference Report\n\n"
    md += f"Successfully predicted {len(target_cols)} gene, program, and pathway targets from {len(x_cols)} CTransPath image features using the frozen Phase 15G model.\n\n"
    md += f"## Top {top_n} Predicted Features\n\n"
    for f in top_features:
        md += f"- **{f['feature_name']}** ({f['feature_type']}): predicted {f['predicted_direction']} (score: {f['predicted_score']}) — {f['interpretation']}\n"
    md += "\n## Scope and Caution\n"
    model_scope_note = "This is a computational image-to-molecular inference derived from histology patch embeddings. It represents similarity to established molecular programs but is NOT measured RNA-seq, NOT a full transcriptome reconstruction, and NOT intended for clinical diagnosis."
    md += f"{model_scope_note}\n"
    
    with open(report_md_path, "w") as f:
        f.write(md)
        
    return {
        "predictions_csv": pred_csv_path,
        "top_features_csv": top_features_csv_path,
        "report_md": report_md_path,
        "gene_expression_matrix_csv": expr_matrix_csv_path,
        "gene_pathway_matrix_csv": pathway_matrix_csv_path,
        "top_features": top_features,
        "model_scope_note": model_scope_note
    }
