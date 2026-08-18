# NeuroBridge / CNS-MultiModalAI

**Bidirectional WSI–Transcriptome Missing-Modality Framework for GBM/LGG Glioma Analysis**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-green.svg)](environment.yml)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-EE4C2C.svg)](https://pytorch.org/)
[![Reproducibility](https://img.shields.io/badge/LOO_Rerun-PASS-brightgreen.svg)](docs/REPRODUCIBILITY.md)

NeuroBridge (CNS-MultiModalAI) is a computational pathology and precision neuro-oncology framework that integrates paired whole-slide histopathology images (WSIs) and bulk RNA-sequencing gene-expression profiles for Central Nervous System (CNS) gliomas.

> **Scope**: GBM-like vs. LGG-like analysis using TCGA-GBM and TCGA-LGG paired cohorts as the internal reference dataset ($N=686$ patients) and CPTAC-GBM ($N=99$ patients) for independent external validation.

---

## Key Features

1. **Pathology Feature Encoding**: CTransPath pathology-specific vision transformer embeddings (768-dim) extracted from whole-slide images.
2. **Missing-Modality Classification**: Cross-modal fusion and missing-modality robust classifiers (Phase 8D v5) maintaining high accuracy when either WSI or RNA-seq is missing.
3. **WSI-to-Biology Prediction**: Direct inference of key molecular biomarkers, biological pathways, and oncogenic programs from CTransPath pathology embeddings.
4. **Gene2Morph Reference Morphology Retrieval**: Bidirectional transformation mapping gene-expression profiles to predicted CTransPath embeddings and retrieving real histology reference patches under strict Leave-One-Patient-Out (LOO) query-patient self-exclusion.
5. **Interactive GUI**: Full-stack web user interface (React/Next.js frontend + FastAPI backend) supporting deep zoom visualization (OpenSeadragon) and automated molecular report generation.

---

## System Architecture & Data Pipeline

```text
               +----------------------------------+
               |  Paired TCGA-GBM/LGG & CPTAC    |
               +----------------------------------+
                                |
         +----------------------+----------------------+
         |                                             |
         v                                             v
+------------------+                          +------------------+
| Whole-Slide WSI  |                          | Bulk RNA-seq     |
+------------------+                          +------------------+
         | (CTransPath 768-dim)                        | (60,616 raw STAR counts)
         v                                             v (Low-info filtering)
+------------------+                          +------------------+
| 768-dim Image    |                          | 48,860 Modeling  |
| Embedding        |                          | Matrix (Log2-TPM)|
+------------------+                          +------------------+
         |                                             | (PCA-128 / MLP Latent-64)
         +----------------------+----------------------+
                                |
                                v
               +----------------------------------+
               |  Phase 8D v5 Classifier          |
               |  (Multimodal / Missing Modality) |
               +----------------------------------+
                                |
         +----------------------+----------------------+
         |                                             |
         v (Image -> Biology)                          v (Gene2Morph LOO)
+------------------+                          +------------------+
| Biomarker &      |                          | Real Reference   |
| Pathway Report   |                          | Morphology Panel |
+------------------+                          +------------------+
```

---

## Validated Scientific Performance Benchmarks

### 1. Molecular & Vision Encoders (Repeated Cross-Validation)
- **ResNet-50 Baseline (Image-Only)**: $90.73\%$ Balanced Accuracy
- **CTransPath Vision Transformer (Image-Only)**: $92.46\%$ Balanced Accuracy
- **Image Fusion Model**: $92.70\%$ Balanced Accuracy
- **PCA-128 Expression Encoders (RNA-Only)**: $98.92\%$ Balanced Accuracy
- **Supervised MLP Latent-64 (RNA-Only)**: $99.67\%$ Balanced Accuracy

### 2. Multimodal & Robust Missing-Modality Classifiers
- **Complete Multimodal Classifier**: $99.42\%$ Mean Balanced Accuracy (5-fold Repeated CV)
- **Canonical Locked Test Set**: $98.65\%$ Balanced Accuracy
- **External Validation (CPTAC RNA, N=99)**: $99/99$ ($100\%$) GBM-positive recognition

### 3. WSI & Morphology Generalization Metrics
- **Direct WSI Patient Recognition**: $125/200$ ($62.5\%$)
- **Domain-Robust Cosine Similarity Recognition**: $181/200$ ($90.5\%$)
- **Max Slide-to-Patient Aggregation**: $184/200$ ($92.0\%$)

### 4. Gene2Morph Reference Morphology Retrieval (LOO Rerun)
- **Mean Peak Cosine Similarity**: $0.8986$ (Mean Top-300 Cosine: $0.8716$)
- **Diagnosis Agreement**: $5/6$ ($83.3\%$) matching query diagnosis
- **Top Source Slide Consistency**: $100\%$ identical top-source slide assignment across all pilot queries
- **Self-Exclusion Policy**: $3,000$ query-patient patch candidates were excluded from the reference search across the six queries (500 candidate patches per query slide).
  - *Historical top-300 self-patches*: 6
  - *Final LOO top-300 self-patches*: 0

---

## Repository Structure

```text
.
├── src/cns_multimodalai/       # Core Python library
│   ├── config.py               # Dynamic project root & paths
│   ├── data/                   # Data loaders & QC utilities
│   ├── models/                 # Neural architectures & encoders
│   ├── inference/              # RNA, WSI, and Gene2Morph LOO inference
│   └── visualization/          # Plotting & coordinate canvas generators
├── scripts/                    # Command-line execution scripts
│   ├── run_genemorph_loo_rerun.py  # Production LOO scientific runner
│   └── generate_figure5_loo.py # Figure 5 generation
├── tests/                      # Unit test suite (16 LOO tests)
├── docs/                       # Comprehensive documentation
│   ├── PROJECT_OVERVIEW.md
│   ├── DATA_PREPARATION.md
│   ├── REPRODUCIBILITY.md
│   ├── MODEL_PIPELINE.md
│   ├── GENEMORPH.md
│   ├── RESULTS_PROVENANCE.md
│   └── LICENSE_RECOMMENDATION.md
├── manuscript_figures/         # Publication figures (Figure 5 LOO)
├── environment.yml             # Conda environment definition
├── pyproject.toml              # Build & dependency metadata
├── CITATION.cff                # Citation file format
├── THIRD_PARTY_NOTICES.md      # Licensing & third-party data notices
└── README.md
```

---

## Getting Started

### 1. Environment Setup

```bash
# Clone repository
git clone https://github.com/HazratMaghaz/CNS-MultiModalAI.git
cd CNS-MultiModalAI

# Set environment variables (portable)
export CNS_PROJECT_ROOT="$(pwd)"
export PYTHONPATH="$CNS_PROJECT_ROOT/src:$PYTHONPATH"

# Create conda environment
conda env create -f environment.yml
conda activate ai-gpu

# Install package in editable mode
pip install -e .
```

### 2. Running Unit Tests

```bash
python -m unittest discover -v -s tests -p "test_*.py"
```

### 3. Executing Gene2Morph LOO Rerun

```bash
# Dry-run validation mode (no H5 bank search)
python scripts/run_genemorph_loo_rerun.py

# Full scientific execution
python scripts/run_genemorph_loo_rerun.py --execute --output-root results/genemorph_loo_rerun_20260818_final
```

---

## Citation

If you use NeuroBridge / CNS-MultiModalAI in your research, please cite the software repository using `CITATION.cff` or BibTeX:

```bibtex
@software{maghaz2026neurobridge,
  title = {NeuroBridge: Deep Multimodal AI Framework for CNS Tumor Classification and Morphology Retrieval},
  author = {Maghaz, Hazrat},
  url = {https://github.com/HazratMaghaz/CNS-MultiModalAI},
  version = {1.0.0},
  year = {2026}
}
```

---

## License & Third-Party Notices

NeuroBridge source code is licensed under the [MIT License](LICENSE). Third-party dependencies and datasets (TCGA, CPTAC, CTransPath model weights) are subject to their respective institutional licenses detailed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).