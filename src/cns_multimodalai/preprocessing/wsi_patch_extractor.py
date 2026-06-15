import os
import random
import csv
import cv2
import numpy as np
import math
import json
import pandas as pd
from PIL import Image, ImageDraw
from pathlib import Path

try:
    import openslide
except ImportError:
    openslide = None

def create_wsi_thumbnail_and_mask(wsi_path: Path, out_dir: Path, max_side: int = 1600):
    if openslide is None:
        raise ImportError("OpenSlide is not available.")
    
    slide = openslide.OpenSlide(str(wsi_path))
    w, h = slide.dimensions

    scale = max(w, h) / max_side
    thumb_size = (max(1, int(w / scale)), max(1, int(h / scale)))
    thumb = slide.get_thumbnail(thumb_size).convert("RGB")

    thumb_path = out_dir / "wsi_thumbnail.jpg"
    thumb.save(thumb_path, quality=92)

    arr = np.array(thumb)
    hsv = cv2.cvtColor(arr, cv2.COLOR_RGB2HSV)
    _, s_ch, v_ch = cv2.split(hsv)
    mask = ((s_ch > 20) & (v_ch < 245)).astype(np.uint8) * 255
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    mask_path = out_dir / "wsi_tissue_mask.png"
    Image.fromarray(mask).save(mask_path)

    slide.close()

    return {
        "wsi_width": int(w),
        "wsi_height": int(h),
        "thumbnail_size": list(thumb.size),
        "thumbnail_path": str(thumb_path),
        "tissue_mask_path": str(mask_path),
        "scale_level0_to_thumbnail": thumb.size[0] / w,
    }

def infer_patch_size(df: pd.DataFrame, default_patch_size: int = 512) -> int:
    for c in ["patch_size", "read_size", "tile_size"]:
        if c in df.columns:
            vals = pd.to_numeric(df[c], errors="coerce").dropna()
            if len(vals):
                return int(vals.iloc[0])
    return default_patch_size

def create_patch_overlay(thumbnail_path, manifest_df, wsi_width, wsi_height, out_dir, patch_size=512):
    thumb = Image.open(thumbnail_path).convert("RGB")
    draw = ImageDraw.Draw(thumb)

    sx = thumb.size[0] / wsi_width
    sy = thumb.size[1] / wsi_height

    for _, row in manifest_df.iterrows():
        x = int(row["x"])
        y = int(row["y"])
        x1 = int(x * sx)
        y1 = int(y * sy)
        x2 = int((x + patch_size) * sx)
        y2 = int((y + patch_size) * sy)
        draw.rectangle([x1, y1, x2, y2], outline=(255, 220, 0), width=2)

    label = f"Patch overlay: {len(manifest_df)} accepted patches"
    draw.rectangle([8, 8, 520, 44], fill=(0, 0, 0))
    draw.text((16, 18), label, fill=(255, 255, 255))

    out_path = out_dir / "wsi_patch_overlay.jpg"
    thumb.save(out_path, quality=94)
    return str(out_path)

def create_coordinate_patch_mosaic(manifest_df, out_dir, max_canvas_side=2200, patch_thumb_size=96, background=(245, 245, 245)):
    df = manifest_df.copy()
    if df.empty:
        raise ValueError("No patches provided for mosaic.")

    min_x, max_x = int(df["x"].min()), int(df["x"].max())
    min_y, max_y = int(df["y"].min()), int(df["y"].max())
    span_x = max(1, max_x - min_x)
    span_y = max(1, max_y - min_y)

    scale = min(max_canvas_side / span_x, max_canvas_side / span_y)
    canvas_w = max(300, int(span_x * scale) + patch_thumb_size + 40)
    canvas_h = max(300, int(span_y * scale) + patch_thumb_size + 60)

    canvas = Image.new("RGB", (canvas_w, canvas_h), background)
    draw = ImageDraw.Draw(canvas)
    df = df.sort_values(["y", "x"]).reset_index(drop=True)

    for _, row in df.iterrows():
        try:
            patch = Image.open(row["patch_path"]).convert("RGB")
            patch.thumbnail((patch_thumb_size, patch_thumb_size))
        except Exception:
            continue

        cx = int((int(row["x"]) - min_x) * scale) + 20
        cy = int((int(row["y"]) - min_y) * scale) + 40
        canvas.paste(patch, (cx, cy))
        draw.rectangle([cx, cy, cx + patch.size[0], cy + patch.size[1]], outline=(20, 120, 120), width=1)

    title = f"Coordinate-aware WSI patch mosaic | n={len(df)}"
    draw.rectangle([0, 0, canvas_w, 34], fill=(10, 30, 46))
    draw.text((12, 10), title, fill=(255, 255, 255))

    out_path = out_dir / "wsi_coordinate_patch_mosaic.jpg"
    canvas.save(out_path, quality=94)

    return {
        "mosaic_path": str(out_path),
        "n_patches": int(len(df)),
        "bbox_level0": {"min_x": min_x, "max_x": max_x, "min_y": min_y, "max_y": max_y},
        "canvas_size": [canvas_w, canvas_h],
        "scale_level0_to_mosaic": scale,
    }

def create_spatial_contact_sheet(manifest_df, out_dir, patch_thumb_size=128, n_cols=10, pad=8):
    df = manifest_df.sort_values(["y", "x"]).reset_index(drop=True)
    n = len(df)
    n_rows = math.ceil(n / n_cols)
    header_h = 42

    canvas_w = n_cols * patch_thumb_size + (n_cols + 1) * pad
    canvas_h = header_h + n_rows * patch_thumb_size + (n_rows + 1) * pad

    canvas = Image.new("RGB", (canvas_w, canvas_h), (245, 245, 245))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, canvas_w, header_h], fill=(10, 30, 46))
    draw.text((12, 13), f"Spatially sorted patch contact sheet | n={n}", fill=(255, 255, 255))

    for i, row in df.iterrows():
        r = i // n_cols
        c = i % n_cols
        x0 = pad + c * (patch_thumb_size + pad)
        y0 = header_h + pad + r * (patch_thumb_size + pad)
        try:
            patch = Image.open(row["patch_path"]).convert("RGB")
            patch = patch.resize((patch_thumb_size, patch_thumb_size))
            canvas.paste(patch, (x0, y0))
        except Exception:
            draw.rectangle([x0, y0, x0 + patch_thumb_size, y0 + patch_thumb_size], fill=(220, 220, 220))

    out_path = out_dir / "wsi_spatial_contact_sheet.jpg"
    canvas.save(out_path, quality=94)
    return str(out_path)

def create_wsi_visualization_summary(thumbnail_info, overlay_path, mosaic_info, contact_sheet_path, out_dir):
    summary = {
        "wsi_thumbnail": thumbnail_info,
        "wsi_patch_overlay_path": overlay_path,
        "wsi_coordinate_patch_mosaic": mosaic_info,
        "wsi_spatial_contact_sheet_path": contact_sheet_path,
        "note": "Visualizations preserve approximate patch coordinates from the original WSI."
    }
    
    out_path = out_dir / "wsi_visualization_summary.json"
    with out_path.open("w") as f:
        json.dump(summary, f, indent=2)
    return str(out_path)

def extract_patches_from_wsi(
    wsi_path: str,
    output_dir: str,
    max_patches: int = 100,
    patch_size: int = 512,
    target_mag: float = 20.0,
    target_mpp: float = 0.50,
    min_patch_tissue_percent: float = 50.0,
    min_patch_contrast: float = 10.0,
    min_patch_blur: float = 5.0,
    random_seed: int = 42
) -> dict:
    """
    Extracts random patches from a local WSI file using OpenSlide.
    Includes simple tissue masking and QC heuristics.
    """
    if openslide is None:
        raise ImportError("openslide-python is not installed.")

    wsi_path = Path(wsi_path)
    output_dir = Path(output_dir)
    
    if not wsi_path.exists():
        raise FileNotFoundError(f"WSI file not found: {wsi_path}")

    random.seed(random_seed)
    np.random.seed(random_seed)

    # Output folders
    patches_dir = output_dir / "patches"
    patches_dir.mkdir(parents=True, exist_ok=True)
    manifest_csv = output_dir / "patch_manifest.csv"

    # Open slide
    slide = openslide.OpenSlide(str(wsi_path))
    w_wsi, h_wsi = slide.dimensions

    # 1. Generate tissue mask from thumbnail
    thumb_size = (w_wsi // 32, h_wsi // 32)
    thumb = np.array(slide.get_thumbnail(thumb_size))
    
    # Convert to HSV and threshold for tissue
    if thumb.shape[2] == 4:
        thumb = cv2.cvtColor(thumb, cv2.COLOR_RGBA2RGB)
    
    hsv = cv2.cvtColor(thumb, cv2.COLOR_RGB2HSV)
    # Basic saturation threshold to find tissue (ignoring white background)
    _, s, v = cv2.split(hsv)
    mask = (s > 20) & (v > 20)
    
    tissue_indices = np.argwhere(mask)
    if len(tissue_indices) == 0:
        raise ValueError("No tissue found in WSI thumbnail mask.")

    # 2. Sample coordinates
    accepted_patches = []
    attempts = 0
    max_attempts = max_patches * 50

    with manifest_csv.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["wsi_path", "patch_path", "x", "y", "tissue_percent", "contrast", "blur_score"])

        while len(accepted_patches) < max_patches and attempts < max_attempts:
            attempts += 1
            
            # Pick a random tissue thumbnail pixel
            idx = random.randint(0, len(tissue_indices) - 1)
            ty, tx = tissue_indices[idx]
            
            # Map to level 0 coordinates
            x_lvl0 = int(tx * 32)
            y_lvl0 = int(ty * 32)
            
            # Read region at level 0
            # Read an area slightly larger or equal depending on MPP mismatch
            # Simplified: just read patch_size x patch_size at level 0
            # (Assuming level 0 is ~20x or close enough for MVP)
            region = slide.read_region((x_lvl0, y_lvl0), 0, (patch_size, patch_size))
            patch_rgb = np.array(region.convert("RGB"))
            
            # QC Checks
            # Tissue percent in patch
            patch_hsv = cv2.cvtColor(patch_rgb, cv2.COLOR_RGB2HSV)
            _, patch_s, patch_v = cv2.split(patch_hsv)
            patch_mask = (patch_s > 20) & (patch_v > 20)
            tissue_pct = (np.sum(patch_mask) / (patch_size * patch_size)) * 100.0
            
            if tissue_pct < min_patch_tissue_percent:
                continue
                
            # Contrast (std dev of grayscale)
            patch_gray = cv2.cvtColor(patch_rgb, cv2.COLOR_RGB2GRAY)
            contrast = np.std(patch_gray)
            if contrast < min_patch_contrast:
                continue
                
            # Blur (Laplacian variance)
            blur_score = cv2.Laplacian(patch_gray, cv2.CV_64F).var()
            if blur_score < min_patch_blur:
                continue
                
            # Accept patch
            patch_filename = f"patch_{x_lvl0}_{y_lvl0}.png"
            patch_path = patches_dir / patch_filename
            
            # Save patch
            region.convert("RGB").save(str(patch_path))
            
            # Log
            writer.writerow([
                str(wsi_path),
                str(patch_path),
                x_lvl0,
                y_lvl0,
                round(tissue_pct, 2),
                round(contrast, 2),
                round(blur_score, 2)
            ])
            
            accepted_patches.append(str(patch_path))

    # Generate Spatial Visualizations
    vis_paths = {}
    if openslide is not None and len(accepted_patches) > 0:
        try:
            df = pd.read_csv(manifest_csv)
            max_x = int(df["x"].max())
            max_y = int(df["y"].max())
            
            if max_x <= w_wsi and max_y <= h_wsi:
                vis_dir = output_dir / "visualizations"
                vis_dir.mkdir(parents=True, exist_ok=True)
                
                thumb_info = create_wsi_thumbnail_and_mask(wsi_path, vis_dir)
                p_size = infer_patch_size(df, patch_size)
                
                overlay_path = create_patch_overlay(
                    thumb_info["thumbnail_path"], df, 
                    thumb_info["wsi_width"], thumb_info["wsi_height"], 
                    vis_dir, patch_size=p_size
                )
                
                mosaic_info = create_coordinate_patch_mosaic(df, vis_dir)
                contact_sheet_path = create_spatial_contact_sheet(df, vis_dir)
                
                summary_path = create_wsi_visualization_summary(
                    thumb_info, overlay_path, mosaic_info, contact_sheet_path, vis_dir
                )
                
                vis_paths = {
                    "wsi_thumbnail_path": thumb_info["thumbnail_path"],
                    "wsi_tissue_mask_path": thumb_info["tissue_mask_path"],
                    "wsi_patch_overlay_path": overlay_path,
                    "wsi_coordinate_mosaic_path": mosaic_info["mosaic_path"],
                    "wsi_spatial_contact_sheet_path": contact_sheet_path,
                    "wsi_visualization_summary_path": summary_path
                }
            else:
                print(f"Warning: Patch coordinates (max x:{max_x}, y:{max_y}) exceed WSI dimensions ({w_wsi}x{h_wsi}). Skipping visualization.")
        except Exception as e:
            print(f"Warning: Failed to generate WSI visualizations. {e}")

    return {
        "patch_dir": str(patches_dir),
        "patch_manifest_csv": str(manifest_csv),
        "n_patches_saved": len(accepted_patches),
        "wsi_width": w_wsi,
        "wsi_height": h_wsi,
        "attempts": attempts,
        "visualizations": vis_paths
    }
