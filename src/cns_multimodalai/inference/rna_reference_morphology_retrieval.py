# CNS JSON safety patch: prevents ndarray JSON serialization failures
from cns_multimodalai.inference.json_safety import patch_json_encoder
patch_json_encoder()

import os
import json
import math
import heapq
import gc
from collections import defaultdict
from pathlib import Path
import re

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw

try:
    import h5py
    HAS_H5PY = True
except Exception as e:
    HAS_H5PY = False
    H5PY_ERROR = repr(e)

try:
    import openslide
    HAS_OPENSLIDE = True
except Exception as e:
    HAS_OPENSLIDE = False
    OPENSLIDE_ERROR = repr(e)

from cns_multimodalai import config

def decode_attr_value(v):
    if v is None:
        return None
    if isinstance(v, bytes):
        return v.decode("utf-8", errors="ignore")
    if isinstance(v, np.bytes_):
        return v.decode("utf-8", errors="ignore")
    if isinstance(v, np.ndarray):
        if v.shape == ():
            return decode_attr_value(v.item())
        if len(v) == 1:
            return decode_attr_value(v[0])
        return [decode_attr_value(x) for x in v.tolist()]
    return str(v)

def find_dataset(h5, preferred_names, min_ndim=None):
    for name in preferred_names:
        if name in h5:
            ds = h5[name]
            if min_ndim is None or len(ds.shape) >= min_ndim:
                return name, ds

    candidates = []
    def walk(name, obj):
        if isinstance(obj, h5py.Dataset):
            lname = name.lower()
            for pref in preferred_names:
                lp = pref.lower()
                if lname == lp or lname.endswith(lp) or lp in lname:
                    if min_ndim is None or len(obj.shape) >= min_ndim:
                        candidates.append((name, obj))
                        break

    h5.visititems(walk)
    if candidates:
        return candidates[0]
    return None, None

def get_h5_attrs(h):
    attrs = {str(k): decode_attr_value(v) for k, v in h.attrs.items()}
    slide_path = (
        attrs.get("slide_path")
        or attrs.get("wsi_path")
        or attrs.get("source_wsi_path")
        or attrs.get("svs_path")
    )
    patient_id = (
        attrs.get("patient_id")
        or attrs.get("case_id")
    )
    slide_id = (
        attrs.get("slide_id")
        or attrs.get("wsi_id")
        or (Path(str(slide_path)).name if slide_path else None)
    )
    diagnosis_label = (
        attrs.get("diagnosis_label")
        or attrs.get("diagnosis")
        or attrs.get("label")
        or attrs.get("class")
    )
    return {
        "slide_path": slide_path,
        "patient_id": patient_id,
        "slide_id": slide_id,
        "diagnosis_label": diagnosis_label,
        "raw_attrs": attrs,
    }

def normalize_coords(coords):
    coords = np.asarray(coords)
    if coords.ndim != 2 or coords.shape[1] < 2:
        raise ValueError(f"Invalid coords shape: {coords.shape}")

    out = {
        "x": coords[:, 0].astype(int),
        "y": coords[:, 1].astype(int),
    }

    if coords.shape[1] >= 4:
        out["raw_col2"] = coords[:, 2].astype(int)
        out["raw_col3"] = coords[:, 3].astype(int)
    else:
        out["raw_col2"] = np.full(coords.shape[0], -1, dtype=int)
        out["raw_col3"] = np.full(coords.shape[0], -1, dtype=int)

    return out

def draw_header(draw, width, title, h=42):
    draw.rectangle([0, 0, width, h], fill=(10, 30, 46))
    draw.text((12, 13), title, fill=(255, 255, 255))

def make_blank_patch(size=256, text="missing"):
    img = Image.new("RGB", (size, size), (230, 230, 230))
    draw = ImageDraw.Draw(img)
    draw.text((10, size // 2 - 8), text, fill=(80, 80, 80))
    return img

def safe_name(text, max_len=60):
    text = str(text)
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text)
    return text[:max_len]

def open_slide_read_fixed(slide, x, y, slide_w, slide_h, size=256):
    x = int(x)
    y = int(y)
    size = int(size)
    x = max(0, min(x, max(0, slide_w - size)))
    y = max(0, min(y, max(0, slide_h - size)))
    img = slide.read_region((x, y), 0, (size, size)).convert("RGB")
    return img.copy(), x, y

def save_patch_panel(df, out_path, title, max_rows=40, patch_size=128, n_cols=10, pad=8):
    view = df[df["retrieved_patch_exists"] == True].head(max_rows).copy()
    n = len(view)
    if n == 0:
        return out_path
    
    n_rows = max(1, math.ceil(n / n_cols))
    header_h = 44
    canvas_w = n_cols * patch_size + (n_cols + 1) * pad
    canvas_h = header_h + n_rows * patch_size + (n_rows + 1) * pad

    canvas = Image.new("RGB", (canvas_w, canvas_h), (245, 245, 245))
    draw = ImageDraw.Draw(canvas)
    draw_header(draw, canvas_w, f"{title} | n={n}", header_h)

    for i, (_, row) in enumerate(view.iterrows()):
        r = i // n_cols
        c = i % n_cols
        x0 = pad + c * (patch_size + pad)
        y0 = header_h + pad + r * (patch_size + pad)

        try:
            img = Image.open(row["retrieved_patch_image"]).convert("RGB").resize((patch_size, patch_size))
        except Exception:
            img = make_blank_patch(size=patch_size)

        canvas.paste(img, (x0, y0))

    canvas.save(out_path, quality=94)
    return out_path

def save_source_grouped_panel(df, out_path, max_rows=80, patch_size=128, n_cols=10, pad=8):
    view = df[df["retrieved_patch_exists"] == True].copy()
    if len(view) == 0:
        return out_path
    
    view = view.sort_values(["source_slide_id", "rank"]).head(max_rows).reset_index(drop=True)
    n = len(view)

    n_rows = max(1, math.ceil(n / n_cols))
    header_h = 44
    canvas_w = n_cols * patch_size + (n_cols + 1) * pad
    canvas_h = header_h + n_rows * patch_size + (n_rows + 1) * pad

    canvas = Image.new("RGB", (canvas_w, canvas_h), (245, 245, 245))
    draw = ImageDraw.Draw(canvas)
    draw_header(draw, canvas_w, f"Source-grouped retrieved patches | n={n}", header_h)

    prev_src = None
    for i, (_, row) in enumerate(view.iterrows()):
        r = i // n_cols
        c = i % n_cols
        x0 = pad + c * (patch_size + pad)
        y0 = header_h + pad + r * (patch_size + pad)

        try:
            img = Image.open(row["retrieved_patch_image"]).convert("RGB").resize((patch_size, patch_size))
        except Exception:
            img = make_blank_patch(size=patch_size)

        canvas.paste(img, (x0, y0))

        src = str(row["source_slide_id"])[:18]
        if src != prev_src:
            draw.rectangle([x0, y0, x0 + patch_size, y0 + 18], fill=(0, 90, 90))
            draw.text((x0 + 4, y0 + 3), src, fill=(255, 255, 255))
            prev_src = src

    canvas.save(out_path, quality=94)
    return out_path

def save_reference_coordinate_layout(df, out_path, patch_size=96, max_canvas_side=1800, max_n=160):
    view = df[df["retrieved_patch_exists"] == True].head(max_n).copy()
    if view.empty:
        return None

    counts = view["source_slide_id"].value_counts()
    top_slide = counts.index[0]
    source_view = view[view["source_slide_id"] == top_slide].copy()

    if len(source_view) < 3:
        return None

    x_col = "x_safe" if "x_safe" in source_view.columns and source_view["x_safe"].notna().any() else "x"
    y_col = "y_safe" if "y_safe" in source_view.columns and source_view["y_safe"].notna().any() else "y"

    min_x, max_x = int(source_view[x_col].min()), int(source_view[x_col].max())
    min_y, max_y = int(source_view[y_col].min()), int(source_view[y_col].max())

    span_x = max(1, max_x - min_x)
    span_y = max(1, max_y - min_y)

    scale = min(max_canvas_side / span_x, max_canvas_side / span_y)

    canvas_w = max(420, int(span_x * scale) + patch_size + 40)
    canvas_h = max(420, int(span_y * scale) + patch_size + 60)

    canvas = Image.new("RGB", (canvas_w, canvas_h), (245, 245, 245))
    draw = ImageDraw.Draw(canvas)
    draw_header(
        draw,
        canvas_w,
        f"Reference-coordinate layout | source={str(top_slide)[:35]} | n={len(source_view)}",
        38,
    )

    source_view = source_view.sort_values([y_col, x_col]).reset_index(drop=True)

    for _, row in source_view.iterrows():
        try:
            img = Image.open(row["retrieved_patch_image"]).convert("RGB").resize((patch_size, patch_size))
        except Exception:
            img = make_blank_patch(size=patch_size)

        x0 = int((int(row[x_col]) - min_x) * scale) + 20
        y0 = int((int(row[y_col]) - min_y) * scale) + 42

        canvas.paste(img, (x0, y0))
        draw.rectangle([x0, y0, x0 + patch_size, y0 + patch_size], outline=(0, 120, 120), width=1)

    canvas.save(out_path, quality=94)

    return {
        "path": str(out_path),
        "top_source_slide": str(top_slide),
        "top_source_patch_count": int(len(source_view)),
        "top_source_patient_id": str(source_view["source_patient_id"].iloc[0]),
        "note": "Reference coordinates belong to retrieved source WSI, not RNA query sample.",
    }


def run_reference_morphology_retrieval(
    query_embedding: np.ndarray,
    query_patient_id: str,
    output_dir: Path,
    top_k: int = 100,
    max_patch_images: int = 40,
    chunk_size: int = 128,
    patch_read_size: int = 256,
    h5_dir: str = "/path/to/CNS-MultiModalAI/features/ctranspath_7B_wsi_streaming_full/slide_h5",
) -> dict:
    """
    Advanced RNA -> Reference Morphology Retrieval.
    Given a 1D or 2D (1, 768) CTransPath predicted embedding, retrieves best matching patches
    from the WSI H5 bank, extracts them, and generates visual layouts.
    """
    if not HAS_H5PY:
        raise ImportError("h5py is required but not installed.")
        
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    h5_dir = Path(h5_dir)
    h5_files = sorted(h5_dir.glob("*.h5"))
    if not h5_files:
        raise FileNotFoundError(f"No H5 files found in {h5_dir}")
        
    Q = np.asarray(query_embedding, dtype=np.float32)
    if Q.ndim == 1:
        Q = Q.reshape(1, -1)
        
    q_norm = Q / (np.linalg.norm(Q, axis=1, keepdims=True) + 1e-8)
    
    top_heap = []
    counter = 0
    
    for h5_path in h5_files:
        try:
            with h5py.File(h5_path, "r") as h:
                feat_name, feat_ds = find_dataset(
                    h,
                    ["features", "embeddings", "ctranspath_features"],
                    min_ndim=2,
                )
                coord_name, coord_ds = find_dataset(
                    h,
                    ["coords_level0", "coords", "coordinates", "patch_coords"],
                    min_ndim=2,
                )

                if feat_ds is None or coord_ds is None:
                    continue

                n_patches, feat_dim = feat_ds.shape
                if feat_dim != Q.shape[1]:
                    continue
                
                attrs = get_h5_attrs(h)

                for start in range(0, n_patches, chunk_size):
                    end = min(start + chunk_size, n_patches)
                    X = feat_ds[start:end].astype(np.float32)
                    coords = coord_ds[start:end]

                    X_norm = X / (np.linalg.norm(X, axis=1, keepdims=True) + 1e-8)
                    scores = X_norm @ q_norm.T  # chunk x 1
                    s = scores[:, 0]

                    cdict = normalize_coords(coords)
                    
                    local_keep = min(top_k, len(s))
                    local_top_idx = np.argsort(s)[-local_keep:]

                    for local_idx in local_top_idx:
                        global_idx = start + int(local_idx)
                        score = float(s[local_idx])

                        record = {
                            "query_patient_id": query_patient_id,
                            "score": score,
                            "h5_path": str(h5_path),
                            "patch_index": int(global_idx),
                            "x": int(cdict["x"][local_idx]),
                            "y": int(cdict["y"][local_idx]),
                            "raw_col2": int(cdict["raw_col2"][local_idx]),
                            "raw_col3": int(cdict["raw_col3"][local_idx]),
                            "slide_path": attrs.get("slide_path"),
                            "source_patient_id": attrs.get("patient_id"),
                            "source_slide_id": attrs.get("slide_id"),
                            "source_diagnosis_label": attrs.get("diagnosis_label"),
                        }

                        counter += 1
                        item = (score, counter, record)

                        if len(top_heap) < top_k:
                            heapq.heappush(top_heap, item)
                        elif score > top_heap[0][0]:
                            heapq.heapreplace(top_heap, item)

                    del X, X_norm, scores, coords

        except Exception as e:
            continue

    top_records = [item[2] for item in sorted(top_heap, key=lambda x: x[0], reverse=True)]
    for rank, rec in enumerate(top_records, start=1):
        rec["rank"] = rank

    df = pd.DataFrame(top_records)
    if df.empty:
        raise ValueError("No patches retrieved from H5 bank.")
        
    df["retrieved_patch_image"] = None
    df["retrieved_patch_exists"] = False
    df["patch_extract_status"] = "not_attempted"
    df["patch_extract_error"] = ""
    df["x_safe"] = np.nan
    df["y_safe"] = np.nan
    
    patch_dir = output_dir / "retrieved_patch_images"
    patch_dir.mkdir(parents=True, exist_ok=True)
    
    extract_df = df.head(min(max_patch_images, len(df))).copy()
    grouped_indices = defaultdict(list)
    for idx, row in extract_df.iterrows():
        slide_path = row.get("slide_path")
        if slide_path is None or str(slide_path) in ["None", "nan", ""]:
            df.loc[idx, "patch_extract_status"] = "missing_slide_path"
            continue
        grouped_indices[str(slide_path)].append(idx)

    extracted = 0
    if HAS_OPENSLIDE:
        for slide_path, indices in grouped_indices.items():
            slide_path_obj = Path(slide_path)
            if not slide_path_obj.exists():
                for idx in indices:
                    df.loc[idx, "patch_extract_status"] = "slide_file_not_found"
                continue

            slide = None
            try:
                slide = openslide.OpenSlide(str(slide_path_obj))
                slide_w, slide_h = slide.dimensions

                for idx in indices:
                    row = df.loc[idx]
                    try:
                        img, x_safe, y_safe = open_slide_read_fixed(
                            slide, row["x"], row["y"], slide_w, slide_h, size=patch_read_size
                        )
                        source_slide = safe_name(row.get("source_slide_id", "slide"), 45)
                        out_name = f"rank_{int(row['rank']):04d}_{source_slide}_x{x_safe}_y{y_safe}.jpg"
                        out_path = patch_dir / out_name
                        img.save(out_path, quality=90, optimize=True)
                        img.close()

                        df.loc[idx, "retrieved_patch_image"] = str(out_path)
                        df.loc[idx, "retrieved_patch_exists"] = True
                        df.loc[idx, "patch_extract_status"] = "ok"
                        df.loc[idx, "x_safe"] = int(x_safe)
                        df.loc[idx, "y_safe"] = int(y_safe)
                        extracted += 1
                    except Exception as e:
                        df.loc[idx, "patch_extract_status"] = "failed"
                        df.loc[idx, "patch_extract_error"] = repr(e)

            except Exception as e:
                for idx in indices:
                    df.loc[idx, "patch_extract_status"] = "slide_open_failed"
                    df.loc[idx, "patch_extract_error"] = repr(e)
            finally:
                if slide is not None:
                    try:
                        slide.close()
                    except Exception:
                        pass
                gc.collect()

    csv_path = output_dir / "reference_morphology_retrieval.csv"
    df.to_csv(csv_path, index=False)
    
    top_panel_path = output_dir / "reference_morphology_top_patch_panel.jpg"
    source_panel_path = output_dir / "reference_morphology_source_grouped_panel.jpg"
    layout_path = output_dir / "reference_morphology_coordinate_layout.jpg"
    
    save_patch_panel(df, top_panel_path, f"Top Reference Patches | {query_patient_id}", max_rows=max_patch_images)
    save_source_grouped_panel(df, source_panel_path, max_rows=max_patch_images)
    ref_info = save_reference_coordinate_layout(df, layout_path)
    
    unique_sources = int(df.head(max_patch_images)["source_slide_id"].nunique())
    best_score = float(df["score"].max()) if not df.empty else 0.0
    mean_top_score = float(df.head(10)["score"].mean()) if not df.empty else 0.0

    summary = {
        "status": "completed",
        "method": "RNA-predicted CTransPath embedding searched against internal H5 WSI patch bank",
        "top_k": top_k,
        "patch_images_extracted": extracted,
        "unique_source_slides": unique_sources,
        "best_similarity_score": best_score,
        "mean_top_similarity_score": mean_top_score,
        "warning": "Reference retrieval only; not RNA-to-WSI reconstruction.",
        "query_patient_id": query_patient_id,
        "top_panel": str(top_panel_path) if top_panel_path.exists() else None,
        "source_panel": str(source_panel_path) if source_panel_path.exists() else None,
        "coordinate_layout": str(layout_path) if layout_path.exists() else None,
        "retrieval_csv": str(csv_path),
        "reference_layout_info": ref_info,
    }
    
    summary_path = output_dir / "reference_morphology_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
        
    return summary
