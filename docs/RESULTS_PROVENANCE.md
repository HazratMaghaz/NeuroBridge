# Results Provenance Map — NeuroBridge / CNS-MultiModalAI

## 1. Overview
This document maps manuscript claims, table entries, and figure panels to their authoritative source scripts, notebooks, and result data files.

---

## 2. Provenance Mapping Table

| Manuscript Element | Section | Authoritative Source Code | Source Output File / Directory | Status |
|---|---|---|---|---|
| Multimodal ROC-AUC | Results 4.2 | `notebooks/08D_missing_modality_robust_classifier_v5_STRICT_PATHS.ipynb` | `results/metrics/phase8d_canonical_test_metrics_v5.csv` | Frozen |
| WSI-to-Biology Ridge Model | Results 4.5 | `src/cns_multimodalai/inference/predict_gene_pathway_from_image.py` | `models/phase15g_image_to_gene_pathway/` | Frozen |
| External CPTAC Validation | Results 4.6 | `notebooks/12C_v2_CPTAC_WSI_reanalysis_no_patch_extraction.ipynb` | `results/final_summary/phase10a_v2/` | Frozen |
| Gene2Morph LOO Retrieval | Results 4.7 | `scripts/run_genemorph_loo_rerun.py` | `results/genemorph_loo_rerun_20260818/` | Verified |
| Figure 5 (LOO Retrieval Panel) | Figure 5 | `scripts/generate_figure5_loo.py` | `manuscript_figures/Figure_05_Gene2Morph_LOO/` | Verified |

---

## 3. Data Integrity & Verification Standards
- **No Data Fabrication**: All reported numbers are computed directly from raw model outputs or saved metrics.
- **Deterministic Ordering**: Top-$K$ retrieval sorting enforces explicit tie-breaking (`score DESC, h5_path ASC, patch_index ASC`).
- **Audit Artifact Generation**: Every rerun produces SHA256 file hashes, git commit provenance, execution environment metadata, and self-exclusion verification reports.
