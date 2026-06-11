import os
import random
import csv
import cv2
import numpy as np
from pathlib import Path

try:
    import openslide
except ImportError:
    openslide = None

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

    return {
        "patch_dir": str(patches_dir),
        "patch_manifest_csv": str(manifest_csv),
        "n_patches_saved": len(accepted_patches),
        "wsi_width": w_wsi,
        "wsi_height": h_wsi,
        "attempts": attempts
    }
