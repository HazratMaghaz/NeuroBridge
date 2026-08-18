# Project Overview — NeuroBridge / CNS-MultiModalAI

## 1. Executive Summary
NeuroBridge (CNS-MultiModalAI) is a computational pathology and multimodal AI research framework designed to bridge histopathology whole-slide images (WSIs) and gene-expression transcriptomics in high-grade (GBM) and lower-grade (LGG) Central Nervous System (CNS) gliomas.

## 2. Research Objectives
- **Bidirectional Integration**: Map between pathology image representations and RNA-seq molecular signatures.
- **Missing-Modality Robustness**: Maintain clinical diagnostic performance (GBM vs. LGG) even when either histology or transcriptomics is unavailable.
- **Biomarker & Pathway Inference**: Predict key oncogenic programs, cell cycle drivers, extracellular matrix (ECM) pathways, and chromatin remodelers directly from WSI patch embeddings.
- **Gene2Morph Reference Retrieval**: Transform bulk RNA-seq gene-expression profiles into predicted image embeddings and retrieve real, coordinate-aware histology reference patches from a whole-slide image database under strict Leave-One-Patient-Out (LOO) patient self-exclusion.

## 3. Data Cohorts
- **Internal Cohort (TCGA)**: $N=686$ paired patients (195 TCGA-GBM, 491 TCGA-LGG) with matched diagnostic WSIs and STAR-Counts RNA-seq.
- **External Cohort (CPTAC-GBM)**: $N=99$ independent GBM patients with diagnostic WSIs and RNA-seq profiles.

## 4. Key Performance Benchmarks
| Task | Target | Performance | Validation |
|---|---|---|---|
| Multimodal Classification | GBM vs LGG | ROC-AUC > 0.98 | Repeated 5-Fold CV |
| Missing Modality (WSI-only) | GBM vs LGG | ROC-AUC > 0.97 | Repeated 5-Fold CV |
| Missing Modality (RNA-only) | GBM vs LGG | ROC-AUC > 0.97 | Repeated 5-Fold CV |
| External Validation | CPTAC-GBM | 99% GBM-like concordance | Independent Test |
| Gene2Morph LOO Retrieval | Peak Cosine | 0.8986 mean peak | LOO 6-Query Pilot |
| Gene2Morph Diagnosis Match | Canonical Class | 5/6 (83.3%) | LOO 6-Query Pilot |
