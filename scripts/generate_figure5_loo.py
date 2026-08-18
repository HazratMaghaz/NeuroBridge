#!/usr/bin/env python3
"""
Generate Corrected Figure 5 under manuscript_figures/Figure_05_Gene2Morph_LOO/
Combines Query 0 (TCGA-02-0003, GBM) and Query 4 (TCGA-CS-4941, LGG) LOO retrieval panels.
"""

import os
import matplotlib.pyplot as plt
from PIL import Image
from pathlib import Path
from datetime import datetime

OUT_DIR = Path("manuscript_figures/Figure_05_Gene2Morph_LOO")
OUT_DIR.mkdir(parents=True, exist_ok=True)

import sys
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--input-dir", default="results/genemorph_loo_rerun_20260818_final", help="Path to LOO rerun output root")
args = parser.parse_args()

IN_DIR = Path(args.input_dir)
Q0_DIR = IN_DIR / "query_00_TCGA-02-0003"
Q4_DIR = IN_DIR / "query_04_TCGA-CS-4941"

q0_patch_panel = Image.open(Q0_DIR / "reference_morphology_top_patch_panel.jpg")
q0_coord_layout = Image.open(Q0_DIR / "reference_morphology_coordinate_layout.jpg")

q4_patch_panel = Image.open(Q4_DIR / "reference_morphology_top_patch_panel.jpg")
q4_coord_layout = Image.open(Q4_DIR / "reference_morphology_coordinate_layout.jpg")

fig, axes = plt.subplots(2, 2, figsize=(16, 12), gridspec_kw={'height_ratios': [1, 1], 'width_ratios': [1.3, 1]})

# Query 00: TCGA-02-0003 (GBM)
axes[0, 0].imshow(q0_patch_panel)
axes[0, 0].set_title("A. Query: TCGA-02-0003 (Glioblastoma, GBM) — Top-40 Retrieved Reference Patches (LOO)", fontsize=11, fontweight='bold', pad=10)
axes[0, 0].axis('off')

axes[0, 1].imshow(q0_coord_layout)
axes[0, 1].set_title("B. Top Source Slide Coordinate Mosaic: TCGA-06-5856", fontsize=11, fontweight='bold', pad=10)
axes[0, 1].axis('off')

# Query 04: TCGA-CS-4941 (LGG)
axes[1, 0].imshow(q4_patch_panel)
axes[1, 0].set_title("C. Query: TCGA-CS-4941 (Lower Grade Glioma, LGG) — Top-40 Retrieved Reference Patches (LOO)", fontsize=11, fontweight='bold', pad=10)
axes[1, 0].axis('off')

axes[1, 1].imshow(q4_coord_layout)
axes[1, 1].set_title("D. Top Source Slide Coordinate Mosaic: TCGA-DU-7011", fontsize=11, fontweight='bold', pad=10)
axes[1, 1].axis('off')

plt.suptitle("Figure 5: Gene2Morph Leave-One-Patient-Out (LOO) Reference Morphology Retrieval", fontsize=14, fontweight='bold', y=0.98)
plt.tight_layout(rect=[0, 0.03, 1, 0.95])

# Save in PNG, PDF, and SVG formats
png_path = OUT_DIR / "Figure_05_Gene2Morph_LOO.png"
pdf_path = OUT_DIR / "Figure_05_Gene2Morph_LOO.pdf"
svg_path = OUT_DIR / "Figure_05_Gene2Morph_LOO.svg"

plt.savefig(png_path, dpi=300, bbox_inches='tight')
plt.savefig(pdf_path, bbox_inches='tight')
plt.savefig(svg_path, bbox_inches='tight')
plt.close()

# Provenance file
prov_path = OUT_DIR / "Figure_05_Gene2Morph_LOO_provenance.txt"
with open(prov_path, "w") as f:
    f.write("NeuroBridge manuscript Figure 5 LOO Provenance\n")
    f.write("============================================================\n")
    f.write(f"Generated: {datetime.now().isoformat()}\n")
    f.write("Mode: Leave-One-Patient-Out (LOO) Query-Patient Self-Exclusion\n")
    f.write("Query 0: TCGA-02-0003 (GBM) -> Top Source Slide TCGA-06-5856 (49/300 patches)\n")
    f.write("Query 4: TCGA-CS-4941 (LGG) -> Top Source Slide TCGA-DU-7011 (26/300 patches)\n")
    f.write(f"Source run: {IN_DIR}\n")

print(f"Generated Figure 5 LOO artifacts in {OUT_DIR}")
