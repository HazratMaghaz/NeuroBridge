from pathlib import Path
import re
import numpy as np
import pandas as pd
from PIL import Image, ImageFilter
from sklearn.preprocessing import normalize
from sklearn.metrics.pairwise import cosine_similarity

from cns_multimodalai import config
from cns_multimodalai.preprocessing.harmonize_expression import select_ctranspath_feature_cols

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

def retrieve_real_patches_from_predicted_image_embedding(pred_img_embedding, n_patches=None, patch_root=None):
    if n_patches is None:
        n_patches = config.PATCHES_PER_CANVAS

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
        paths = patch_df[patch_df["patient_id"].eq(pid)]["patch_path"].tolist()
        if not paths:
            continue

        take = min(config.PATCHES_PER_SOURCE_PATIENT, len(paths), n_patches - len(selected_paths))
        for p in paths[:take]:
            selected_paths.append(p)
            retrieval_rows.append({
                "source_patient_id": pid,
                "source_similarity": float(r["similarity"]),
                "patch_path": p,
            })

        if len(selected_paths) >= n_patches:
            break

    if len(selected_paths) < n_patches:
        already = set(selected_paths)
        for p in patch_df["patch_path"].tolist():
            if p in already:
                continue
            selected_paths.append(p)
            retrieval_rows.append({
                "source_patient_id": extract_tcga_patient_id(p),
                "source_similarity": np.nan,
                "patch_path": p,
            })
            if len(selected_paths) >= n_patches:
                break

    return selected_paths[:n_patches], pd.DataFrame(retrieval_rows)
