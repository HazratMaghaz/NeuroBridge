from pathlib import Path
import re
import numpy as np
import pandas as pd
from PIL import Image, ImageFilter
from sklearn.preprocessing import normalize
from sklearn.metrics.pairwise import cosine_similarity

from cns_multimodalai import config
from cns_multimodalai.preprocessing.harmonize_expression import select_ctranspath_feature_cols
from cns_multimodalai.inference.rna_reference_morphology_retrieval import assert_final_output_loo_clean

PATCH_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"}
TCGA_RE = re.compile(r"(TCGA-[A-Z0-9]{2}-[A-Z0-9]{4})", re.IGNORECASE)

def extract_tcga_patient_id(text):
    m = TCGA_RE.search(str(text))
    return m.group(1).upper() if m else None

def build_clean_patch_bank(patch_root=None):
    if patch_root is None:
        patch_root = config.PATCH_ROOT
    patch_root = Path(patch_root)

    rows = []
    for p in patch_root.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in PATCH_EXTS:
            continue
        s = str(p).lower()
        if "patch_images" not in s:
            continue
        if "sample_grids" in s or "grid" in p.name.lower():
            continue

        pid = extract_tcga_patient_id(str(p))
        if pid is None:
            continue

        rows.append({"patient_id": pid, "patch_path": str(p)})

    patch_df = pd.DataFrame(rows)
    if len(patch_df) == 0:
        raise RuntimeError(f"No clean patch bank found under {patch_root}")
    return patch_df

def make_canvas(patch_paths, out_path, tile_size=None, cols=None, soft_edges=True):
    if tile_size is None:
        tile_size = config.CANVAS_TILE_SIZE
    if cols is None:
        cols = config.CANVAS_COLUMNS

    patch_paths = list(patch_paths)
    rows = int(np.ceil(len(patch_paths) / cols))
    canvas = Image.new("RGB", (cols * tile_size, rows * tile_size), (255, 255, 255))

    mask = None
    if soft_edges:
        mask = Image.new("L", (tile_size, tile_size), 255)
        mask = mask.filter(ImageFilter.GaussianBlur(radius=6))

    for i, p in enumerate(patch_paths):
        try:
            img = Image.open(p).convert("RGB").resize((tile_size, tile_size))
            x = (i % cols) * tile_size
            y = (i // cols) * tile_size
            if mask is not None:
                canvas.paste(img, (x, y), mask=mask)
            else:
                canvas.paste(img, (x, y))
        except Exception:
            continue

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path, quality=95)
    return out_path

def retrieve_real_patches_from_predicted_image_embedding(
    pred_img_embedding,
    n_patches=None,
    patch_root=None,
    query_patient_id=None,
    exclude_query_patient=False,
    strict_loo=False,
):
    """
    Retrieves real reference patches matching a predicted image embedding.
    Supports Leave-One-Patient-Out (LOO) self-exclusion when exclude_query_patient=True.
    """
    if n_patches is None:
        n_patches = config.PATCHES_PER_CANVAS

    norm_query_pid = extract_tcga_patient_id(query_patient_id) if query_patient_id else None
    if strict_loo and not norm_query_pid:
        raise ValueError(f"Strict LOO Error: query_patient_id must be a valid TCGA case ID, got '{query_patient_id}'.")

    internal_img = pd.read_csv(config.INTERNAL_CTRANSPATH_CSV)
    internal_img["patient_id"] = internal_img["patient_id"].astype(str)
    img_cols = select_ctranspath_feature_cols(internal_img)

    patch_df = build_clean_patch_bank(patch_root=patch_root)

    X_db = normalize(internal_img[img_cols].to_numpy(dtype=np.float32))
    q = normalize(np.asarray(pred_img_embedding, dtype=np.float32).reshape(1, -1))
    sims = cosine_similarity(q, X_db).ravel()

    db = internal_img[["patient_id"]].copy()
    db["similarity"] = sims
    db = db.sort_values("similarity", ascending=False)

    selected_paths = []
    retrieval_rows = []

    for _, r in db.iterrows():
        pid = r["patient_id"]
        norm_pid = extract_tcga_patient_id(pid)

        if strict_loo and not norm_pid:
            continue  # Skip unresolved source patient in strict LOO mode

        # LOO Self-Exclusion in Primary Ranking
        if exclude_query_patient and norm_query_pid and norm_pid and norm_query_pid == norm_pid:
            continue

        paths = patch_df[patch_df["patient_id"].eq(pid)]["patch_path"].tolist()
        if not paths:
            continue

        take = min(config.PATCHES_PER_SOURCE_PATIENT, len(paths), n_patches - len(selected_paths))
        for p in paths[:take]:
            selected_paths.append(p)
            retrieval_rows.append({
                "query_patient_id": query_patient_id,
                "source_patient_id": norm_pid or pid,
                "source_similarity": float(r["similarity"]),
                "patch_path": p,
            })

        if len(selected_paths) >= n_patches:
            break

    # Fallback patch-filling logic (also strictly LOO-safe)
    if len(selected_paths) < n_patches:
        already = set(selected_paths)
        for p in patch_df["patch_path"].tolist():
            if p in already:
                continue
            p_norm_pid = extract_tcga_patient_id(p)

            if strict_loo and not p_norm_pid:
                continue  # Skip unresolved fallback patch in strict LOO mode

            # LOO Self-Exclusion in Fallback Patch Filling
            if exclude_query_patient and norm_query_pid and p_norm_pid and norm_query_pid == p_norm_pid:
                continue

            selected_paths.append(p)
            retrieval_rows.append({
                "query_patient_id": query_patient_id,
                "source_patient_id": p_norm_pid or extract_tcga_patient_id(p),
                "source_similarity": np.nan,
                "patch_path": p,
            })
            if len(selected_paths) >= n_patches:
                break

    ret_df = pd.DataFrame(retrieval_rows)
    if not ret_df.empty and (strict_loo or exclude_query_patient):
        assert_final_output_loo_clean(ret_df, query_patient_id, strict_loo=strict_loo)

    return selected_paths[:n_patches], ret_df

