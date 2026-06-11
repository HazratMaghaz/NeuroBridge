import os
import json
import pandas as pd
import numpy as np
import joblib
from sklearn.linear_model import RidgeCV
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from scipy.stats import pearsonr

PROJECT_ROOT = "/path/to/CNS-MultiModalAI"

IMAGE_FEAT_PATH = os.path.join(PROJECT_ROOT, "features/ctranspath_7B_wsi_streaming_full/patient_level_ctranspath_mean_embeddings.csv")
TARGET_PATH = os.path.join(PROJECT_ROOT, "results/tables/phase11a_image_to_gene_pathway_prediction/phase11a_target_gene_pathway_matrix.csv")

MODEL_DIR = os.path.join(PROJECT_ROOT, "models/phase15g_image_to_gene_pathway/")
REVIEW_DIR = os.path.join(PROJECT_ROOT, "results/tables/phase15g_freeze_image_to_gene_pathway_model/")

def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(REVIEW_DIR, exist_ok=True)

    print("1. Loading data...")
    df_feat = pd.read_csv(IMAGE_FEAT_PATH)
    df_tgt = pd.read_csv(TARGET_PATH)

    print("2. Merging and splitting...")
    df = pd.merge(df_feat, df_tgt, on="patient_id", how="inner")

    # Select columns
    x_cols = [c for c in df.columns if c.startswith("ctranspath_feat_")]
    y_cols = [c for c in df.columns if c.startswith("gene__") or c.startswith("program__") or c.startswith("pathway__")]

    print(f"   Selected {len(x_cols)} image features.")
    print(f"   Selected {len(y_cols)} targets.")

    if "split" not in df.columns:
        raise ValueError("Missing 'split' column in merged dataframe")

    train_df = df[df["split"] == "train"].copy()
    test_df = df[df["split"].isin(["val", "test"])].copy()

    X_train_raw = train_df[x_cols].values
    Y_train_raw = train_df[y_cols].values
    X_test_raw = test_df[x_cols].values
    Y_test_raw = test_df[y_cols].values

    print(f"   Train samples: {len(train_df)}")
    print(f"   Validation/Test samples: {len(test_df)}")

    print("3. Scaling data...")
    x_scaler = StandardScaler()
    y_scaler = StandardScaler()

    X_train = x_scaler.fit_transform(X_train_raw)
    Y_train = y_scaler.fit_transform(Y_train_raw)

    X_test = x_scaler.transform(X_test_raw)

    print("4. Training RidgeCV model...")
    alphas = [0.1, 1.0, 10.0, 100.0, 1000.0]
    model = RidgeCV(alphas=alphas)
    model.fit(X_train, Y_train)

    print(f"   Selected alpha: {model.alpha_}")

    print("5. Predicting and evaluating on test/val set...")
    Y_test_pred_scaled = model.predict(X_test)
    Y_test_pred = y_scaler.inverse_transform(Y_test_pred_scaled)

    print("6. Saving models and metadata...")
    joblib.dump(model, os.path.join(MODEL_DIR, "ridge_model.joblib"))
    joblib.dump(x_scaler, os.path.join(MODEL_DIR, "x_scaler.joblib"))
    joblib.dump(y_scaler, os.path.join(MODEL_DIR, "y_scaler.joblib"))
    
    with open(os.path.join(MODEL_DIR, "image_feature_cols.json"), "w") as f:
        json.dump(x_cols, f, indent=2)
    with open(os.path.join(MODEL_DIR, "target_cols.json"), "w") as f:
        json.dump(y_cols, f, indent=2)
    
    metadata = {
        "model_type": "RidgeCV",
        "alphas_tested": alphas,
        "best_alpha": float(model.alpha_),
        "n_features": len(x_cols),
        "n_targets": len(y_cols),
        "n_train_samples": len(train_df),
        "x_scaled": True,
        "y_scaled": True
    }
    with open(os.path.join(MODEL_DIR, "model_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print("7. Preparing outputs and metrics...")
    meta_cols = ["patient_id", "split"]
    if "project_id" in test_df.columns: meta_cols.append("project_id")
    if "label" in test_df.columns: meta_cols.append("label")
    if "diagnosis_label" in test_df.columns: meta_cols.append("diagnosis_label")

    pred_df = test_df[meta_cols].copy()
    
    metrics = []
    
    for i, target in enumerate(y_cols):
        target_type = target.split("__")[0]
        
        true_vals = Y_test_raw[:, i]
        pred_vals = Y_test_pred[:, i]
        
        pred_df[f"pred__ridge__{target}"] = pred_vals
        pred_df[f"true__{target}"] = true_vals
        
        mse = mean_squared_error(true_vals, pred_vals)
        mae = mean_absolute_error(true_vals, pred_vals)
        
        if np.std(true_vals) > 0:
            r2 = r2_score(true_vals, pred_vals)
            if np.std(pred_vals) > 0:
                p_r, _ = pearsonr(true_vals, pred_vals)
            else:
                p_r = np.nan
        else:
            r2 = np.nan
            p_r = np.nan
            
        metrics.append({
            "target_name": target,
            "target_type": target_type,
            "mse": mse,
            "mae": mae,
            "r2": r2,
            "pearson_r": p_r
        })

    pred_df.to_csv(os.path.join(REVIEW_DIR, "phase15g_test_predicted_gene_pathway_scores.csv"), index=False)
    
    metrics_df = pd.DataFrame(metrics)
    metrics_df.to_csv(os.path.join(REVIEW_DIR, "phase15g_target_metrics.csv"), index=False)
    
    val_summary = {
        "n_test_samples": len(test_df),
        "mean_r2": float(metrics_df["r2"].mean()),
        "median_r2": float(metrics_df["r2"].median()),
        "mean_pearson_r": float(metrics_df["pearson_r"].mean()),
        "median_pearson_r": float(metrics_df["pearson_r"].median())
    }
    with open(os.path.join(REVIEW_DIR, "phase15g_validation_summary.json"), "w") as f:
        json.dump(val_summary, f, indent=2)

    top_preview = metrics_df.sort_values(by="pearson_r", ascending=False).head(50)
    top_preview.to_csv(os.path.join(REVIEW_DIR, "phase15g_top_predicted_targets_preview.csv"), index=False)
    
    print("\n--- Summary ---")
    print(f"Model saved to: {MODEL_DIR}")
    print(f"Validation reports saved to: {REVIEW_DIR}")
    print(f"Mean Pearson R across targets: {val_summary['mean_pearson_r']:.4f}")
    print(f"Median Pearson R across targets: {val_summary['median_pearson_r']:.4f}")
    print("Done.")

if __name__ == "__main__":
    main()
