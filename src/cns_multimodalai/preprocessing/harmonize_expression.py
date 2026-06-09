import re
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.cross_decomposition import PLSRegression

from cns_multimodalai import config

def is_ensembl_col(c):
    return str(c).startswith("ENSG")


def select_ctranspath_feature_cols(df, expected_dim=768):
    """
    Robustly select the 768 CTransPath feature columns.

    Handles column names such as:
    - ctranspath_000 ... ctranspath_767
    - ctranspath_0 ... ctranspath_767
    - feat_0 ... feat_767
    - feature_0 ... feature_767
    - img_0 ... img_767
    - numeric column names 0 ... 767
    """
    forbidden = {
        "patient_id", "slide_id", "project_id", "diagnosis_label", "label", "split",
        "status", "n_patches", "mean_embedding_norm", "external_cohort",
        "source", "case_id", "sample_id", "submitter_id"
    }

    numeric = [
        c for c in df.columns
        if str(c) not in forbidden and pd.api.types.is_numeric_dtype(df[c])
    ]

    # First priority: feature columns with known prefixes and ending index.
    indexed = []
    prefixes = [
        "ctranspath_", "ctranspath_feat_", "img_", "feat_", "feature_",
        "embedding_", "x_"
    ]

    for c in numeric:
        s = str(c)
        if any(s.startswith(pref) for pref in prefixes):
            m = re.search(r"(\d+)$", s)
            if m:
                idx = int(m.group(1))
                if 0 <= idx < expected_dim:
                    indexed.append((idx, c))

    indexed = sorted(indexed, key=lambda x: x[0])

    # Keep one column per index.
    final = []
    seen = set()
    for idx, col in indexed:
        if idx not in seen:
            final.append(col)
            seen.add(idx)

    if len(final) == expected_dim:
        return final

    # Second priority: pure numeric column names 0..767.
    pure_numeric = []
    for c in numeric:
        s = str(c)
        if s.isdigit():
            idx = int(s)
            if 0 <= idx < expected_dim:
                pure_numeric.append((idx, c))

    pure_numeric = [c for idx, c in sorted(pure_numeric, key=lambda x: x[0])]
    if len(pure_numeric) == expected_dim:
        return pure_numeric

    # Third priority: if exactly expected_dim numeric columns remain.
    if len(numeric) == expected_dim:
        return numeric

    # Fourth priority: if too many numeric columns, remove common metadata by shape/name and retry.
    metadata_like = {
        "Unnamed: 0", "index", "level_0", "overlap", "score", "rows", "features",
        "feature_count", "row_count", "patient_count"
    }
    numeric2 = [c for c in numeric if str(c) not in metadata_like]

    indexed2 = []
    for c in numeric2:
        s = str(c)
        m = re.search(r"(\d+)$", s)
        if m and any(s.startswith(pref) for pref in prefixes):
            idx = int(m.group(1))
            if 0 <= idx < expected_dim:
                indexed2.append((idx, c))

    indexed2 = [c for idx, c in sorted(indexed2, key=lambda x: x[0])]
    if len(indexed2) == expected_dim:
        return indexed2

    print("Could not auto-select CTransPath columns.")
    print("numeric count:", len(numeric))
    print("indexed count:", len(final))
    print("numeric preview:", [str(c) for c in numeric[:30]])
    raise ValueError(
        f"Could not select {expected_dim} CTransPath features. "
        f"numeric={len(numeric)}, indexed={len(final)}"
    )

def load_internal_expression_and_labels():
    selected = pd.read_csv(config.SELECTED_CSV)
    selected["patient_id"] = selected["patient_id"].astype(str)

    labels = selected[["patient_id", "project_id"]].drop_duplicates("patient_id").copy()
    labels["label"] = labels["project_id"].map({"TCGA-LGG": 0, "TCGA-GBM": 1})

    expr = pd.read_csv(config.INTERNAL_EXPRESSION_CSV)
    expr["patient_id"] = expr["patient_id"].astype(str)

    return expr, labels

def harmonize_external_expression(external_csv, strategy="log2_fpkm_uq_plus1", hvg_n=None):
    """
    Harmonize an external expression CSV to the internal TCGA expression space.

    Expected external format:
        patient_id, ENSG0000..., ENSG0000...

    Default strategy:
        log2(FPKM_UQ + 1), based on Phase 12A-v2 CPTAC RNA validation.
    """
    if hvg_n is None:
        hvg_n = config.RNA_HVG_N

    internal_expr, labels = load_internal_expression_and_labels()
    ext = pd.read_csv(external_csv)

    if "patient_id" not in ext.columns:
        ext.insert(0, "patient_id", [f"external_{i:04d}" for i in range(len(ext))])

    ext["patient_id"] = ext["patient_id"].astype(str)

    internal_gene_cols = [c for c in internal_expr.columns if is_ensembl_col(c) and pd.api.types.is_numeric_dtype(internal_expr[c])]
    external_gene_cols = [c for c in ext.columns if is_ensembl_col(c) and pd.api.types.is_numeric_dtype(ext[c])]

    shared_genes = sorted(list(set(internal_gene_cols) & set(external_gene_cols)))
    if len(shared_genes) < 1000:
        raise ValueError(f"Too few shared genes between internal and external expression: {len(shared_genes)}")

    internal_labeled = labels.merge(internal_expr[["patient_id"] + shared_genes], on="patient_id", how="inner").dropna(subset=["label"])
    gene_var = internal_labeled[shared_genes].var(axis=0).sort_values(ascending=False)
    selected_genes = gene_var.head(min(hvg_n, len(gene_var))).index.tolist()

    X_internal = internal_labeled[selected_genes].to_numpy(dtype=np.float32)
    y_internal = internal_labeled["label"].astype(int).to_numpy()

    X_external_raw = ext[selected_genes].to_numpy(dtype=np.float32)

    if strategy == "log2_fpkm_uq_plus1":
        X_external = np.log2(np.clip(X_external_raw, 0, None) + 1.0).astype(np.float32)
    elif strategy == "raw":
        X_external = X_external_raw.astype(np.float32)
    else:
        raise ValueError(f"Unsupported strategy: {strategy}")

    return {
        "external_df": ext,
        "external_patient_ids": ext["patient_id"].tolist(),
        "selected_genes": selected_genes,
        "shared_gene_count": len(shared_genes),
        "X_internal": X_internal,
        "y_internal": y_internal,
        "X_external": X_external,
        "internal_labeled": internal_labeled,
        "labels": labels,
        "strategy": strategy,
    }

def train_rna_classifier(X_internal, y_internal, random_state=None):
    if random_state is None:
        random_state = config.RANDOM_STATE

    n_pca = min(config.RNA_PCA_DIM, X_internal.shape[0] - 1, X_internal.shape[1])
    model = Pipeline([
        ("scaler", StandardScaler()),
        ("pca", PCA(n_components=n_pca, random_state=random_state)),
        ("clf", LogisticRegression(max_iter=5000, class_weight="balanced", solver="lbfgs", C=0.5)),
    ])
    model.fit(X_internal, y_internal)
    return model

def predict_rna_gbm_like(external_csv, strategy="log2_fpkm_uq_plus1"):
    data = harmonize_external_expression(external_csv, strategy=strategy)
    model = train_rna_classifier(data["X_internal"], data["y_internal"])

    prob = model.predict_proba(data["X_external"])[:, 1]
    pred = (prob >= 0.5).astype(int)

    out = pd.DataFrame({
        "patient_id": data["external_patient_ids"],
        "prob_GBM_like": prob,
        "predicted_label": pred,
        "predicted_class": np.where(pred == 1, "GBM-like", "LGG-like"),
        "expression_strategy": strategy,
        "shared_gene_count": data["shared_gene_count"],
        "selected_gene_count": len(data["selected_genes"]),
    })

    return out, data, model

def train_molecular_to_image_model(data):
    """
    Train internal expression PCA -> internal CTransPath image embedding mapping.
    Used for RNA -> predicted image embedding -> morphology canvas.
    """
    internal_img = pd.read_csv(config.INTERNAL_CTRANSPATH_CSV)
    internal_img["patient_id"] = internal_img["patient_id"].astype(str)

    img_cols = select_ctranspath_feature_cols(internal_img)

    internal_labeled = data["internal_labeled"]
    merged = internal_labeled[["patient_id"] + data["selected_genes"]].merge(
        internal_img[["patient_id"] + img_cols],
        on="patient_id",
        how="inner"
    )

    X = merged[data["selected_genes"]].to_numpy(dtype=np.float32)
    Y = merged[img_cols].to_numpy(dtype=np.float32)

    x_scaler = StandardScaler()
    Xs = x_scaler.fit_transform(X)

    n_pca = min(config.RNA_PCA_DIM, Xs.shape[0] - 1, Xs.shape[1])
    pca = PCA(n_components=n_pca, random_state=config.RANDOM_STATE)
    Xp = pca.fit_transform(Xs)

    xp_scaler = StandardScaler()
    y_scaler = StandardScaler()

    Xps = xp_scaler.fit_transform(Xp)
    Ys = y_scaler.fit_transform(Y)

    n_pls = min(config.PLS_COMPONENTS, Xps.shape[1], Ys.shape[1], Xps.shape[0] - 1)
    pls = PLSRegression(n_components=n_pls, scale=False)
    pls.fit(Xps, Ys)

    return {
        "img_cols": img_cols,
        "x_scaler": x_scaler,
        "pca": pca,
        "xp_scaler": xp_scaler,
        "y_scaler": y_scaler,
        "pls": pls,
    }

def predict_image_embedding_from_rna(data, mol2img_model):
    X_external = data["X_external"]
    Xs = mol2img_model["x_scaler"].transform(X_external)
    Xp = mol2img_model["pca"].transform(Xs)
    Xps = mol2img_model["xp_scaler"].transform(Xp)
    Ys = mol2img_model["pls"].predict(Xps)
    Y = mol2img_model["y_scaler"].inverse_transform(Ys)
    return Y.astype(np.float32)
