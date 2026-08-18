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
2. **Missing-Modality Classification**: Cross-modal fusion and missing-modality robust classifiers (Phase 8D v5) maintaining classification performance when either WSI or RNA-seq is missing.
3. **WSI-to-Biology Prediction**: Direct inference of key molecular biomarkers, biological pathways, and oncogenic programs (Phase 15G Ridge Model) from CTransPath pathology embeddings.
4. **Gene2Morph Reference Morphology Retrieval**: Bidirectional transformation mapping gene-expression profiles to predicted CTransPath embeddings and retrieving real histology reference patches using Leave-One-Patient-Out (LOO) self-exclusion.
5. **Interactive GUI**: Full-stack web user interface (React/Next.js frontend + FastAPI backend) supporting deep zoom visualization (OpenSeadragon) and automated molecular report generation.

---

## System Architecture

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
         |                                             |
         v (CTransPath)                                v (Log2-TPM)
+------------------+                          +------------------+
| 768-dim Image    |                          | 5,000 HVG        |
| Embedding        |                          | Expression       |
+------------------+                          +------------------+
         |                                             |
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

## Scientific Summary & Validated Results

- **Multimodal Classification**: Achieves 0.985+ ROC-AUC on internal TCGA validation and 0.970+ ROC-AUC under single-modality missing condition.
- **External Validation**: Evaluated on CPTAC-GBM independent external cohort ($N=99$).
- **Gene2Morph Reference Retrieval**: Leave-One-Patient-Out (LOO) pilot retrieval across 6 manuscript query cases achieved:
  - **Mean Peak Cosine Similarity**: $0.8986$ (100% robust under LOO query-patient self-exclusion).
  - **Diagnosis Agreement**: $5/6$ (83.3%) matching canonical diagnosis.
  - **Top Source Slide Consistency**: 100% identical top-source slide assignment across all queries.
  - **LOO Self-Exclusion**: 3,000 total candidate self-patches evaluated; zero query-patient self-patches present in final top-300 results.

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
│   └── RESULTS_PROVENANCE.md
├── manuscript_figures/         # Publication figures (Figure 5 LOO)
├── environment.yml             # Conda environment definition
├── pyproject.toml              # Build & dependency metadata
├── CITATION.cff                # Citation file format
└── README.md
```

---

## Getting Started

### 1. Environment Setup

```bash
# Clone repository
git clone https://github.com/HazratMaghaz/CNS-MultiModalAI.git
cd CNS-MultiModalAI

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
python scripts/run_genemorph_loo_rerun.py --execute --output-root results/genemorph_loo_rerun
```

---

## Citation

If you use NeuroBridge / CNS-MultiModalAI in your research, please cite:

```bibtex
@article{maghaz2026neurobridge,
  title={NeuroBridge: A Bidirectional Multimodal AI Framework for Missing-Modality Glioma Subtyping and Morphology Retrieval},
  author={Maghaz, Hazrat},
  journal={Bioinformatics / Computational Pathology},
  year={2026}
}
```

---

## License

This project is licensed under the [MIT License](LICENSE). Third-party datasets (TCGA, CPTAC, CTransPath weights) are subject to their respective institutional data access policies and licenses.