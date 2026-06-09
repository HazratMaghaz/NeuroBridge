from pathlib import Path
import sys
import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader

from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score

from cns_multimodalai import config
from cns_multimodalai.preprocessing.patch_loader import list_patch_images, PatchImageDataset
from cns_multimodalai.preprocessing.harmonize_expression import select_ctranspath_feature_cols

def load_ctranspath_model(device=None):
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    if not config.CTRANSPATH_REPO.exists():
        raise FileNotFoundError(f"CTransPath repo not found: {config.CTRANSPATH_REPO}")
    if not config.CTRANSPATH_CKPT.exists():
        raise FileNotFoundError(f"CTransPath checkpoint not found: {config.CTRANSPATH_CKPT}")

    if str(config.CTRANSPATH_REPO) not in sys.path:
        sys.path.insert(0, str(config.CTRANSPATH_REPO))

    from ctran import ctranspath
    model = ctranspath()

    ckpt = torch.load(config.CTRANSPATH_CKPT, map_location="cpu")
    state = ckpt.get("model", ckpt.get("state_dict", ckpt)) if isinstance(ckpt, dict) else ckpt

    clean_state = {}
    for k, v in state.items():
        nk = k[len("module."):] if str(k).startswith("module.") else k
        clean_state[nk] = v

    model.load_state_dict(clean_state, strict=False)
    model.to(device)
    model.eval()
    return model

def extract_ctranspath_embedding_from_patch_folder(patch_dir, batch_size=64, num_workers=8, device=None):
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    patch_paths = list_patch_images(patch_dir)
    if len(patch_paths) == 0:
        raise RuntimeError(f"No patch images found in {patch_dir}")

    model = load_ctranspath_model(device=device)
    ds = PatchImageDataset(patch_paths, size=config.CTRANSPATH_INPUT_SIZE)
    dl = DataLoader(ds, batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=True)

    feats = []
    paths_used = []

    with torch.no_grad():
        for xb, paths in dl:
            xb = xb.to(device, non_blocking=True)
            if hasattr(model, "forward_features"):
                out = model.forward_features(xb)
            else:
                raw = model(xb)
                out = raw if isinstance(raw, torch.Tensor) else raw[0]

            feats.append(out.detach().cpu().numpy().astype(np.float32))
            paths_used.extend(paths)

    patch_features = np.vstack(feats)
    if patch_features.shape[1] != config.CTRANSPATH_DIM:
        raise ValueError(f"Expected {config.CTRANSPATH_DIM} features, got {patch_features.shape[1]}")

    mean_embedding = patch_features.mean(axis=0)

    return {
        "mean_embedding": mean_embedding,
        "patch_features": patch_features,
        "patch_paths": paths_used,
        "n_patches": len(paths_used),
    }

def train_internal_image_classifier():
    selected = pd.read_csv(config.SELECTED_CSV)
    selected["patient_id"] = selected["patient_id"].astype(str)

    labels = selected[["patient_id", "project_id"]].drop_duplicates("patient_id")
    labels["label"] = labels["project_id"].map({"TCGA-LGG": 0, "TCGA-GBM": 1})

    internal_img = pd.read_csv(config.INTERNAL_CTRANSPATH_CSV)
    internal_img["patient_id"] = internal_img["patient_id"].astype(str)
    img_cols = select_ctranspath_feature_cols(internal_img)

    train_df = labels.merge(internal_img[["patient_id"] + img_cols], on="patient_id", how="inner").dropna(subset=["label"])
    train_df["label"] = train_df["label"].astype(int)

    X = train_df[img_cols].to_numpy(dtype=np.float32)
    y = train_df["label"].to_numpy(dtype=int)

    clf = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=5000, class_weight="balanced", solver="lbfgs", C=0.5)),
    ])
    clf.fit(X, y)

    train_prob = clf.predict_proba(X)[:, 1]
    train_pred = (train_prob >= 0.5).astype(int)

    return {
        "classifier": clf,
        "img_cols": img_cols,
        "train_accuracy": float(accuracy_score(y, train_pred)),
        "train_balanced_accuracy": float(balanced_accuracy_score(y, train_pred)),
        "train_n": int(len(y)),
    }

def predict_from_patch_folder(patch_dir, output_dir=None):
    emb = extract_ctranspath_embedding_from_patch_folder(patch_dir)
    clf_pack = train_internal_image_classifier()

    X = emb["mean_embedding"].reshape(1, -1)
    prob = clf_pack["classifier"].predict_proba(X)[0, 1]
    pred = int(prob >= 0.5)

    result = {
        "input_type": "patch_folder",
        "patch_dir": str(patch_dir),
        "n_patches": int(emb["n_patches"]),
        "prob_GBM_like": float(prob),
        "predicted_label": pred,
        "predicted_class": "GBM-like" if pred == 1 else "LGG-like",
        "model_scope_note": config.MODEL_SCOPE_NOTE,
        "train_accuracy_internal": clf_pack["train_accuracy"],
        "train_balanced_accuracy_internal": clf_pack["train_balanced_accuracy"],
    }

    if output_dir is not None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([result]).to_csv(output_dir / "patch_folder_prediction.csv", index=False)
        pd.DataFrame([emb["mean_embedding"]], columns=[f"ctranspath_{i:03d}" for i in range(config.CTRANSPATH_DIM)]).to_csv(
            output_dir / "patch_folder_mean_embedding.csv",
            index=False
        )

    return result, emb, clf_pack
