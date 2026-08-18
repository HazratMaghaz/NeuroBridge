# Data Preparation & Preprocessing Pipeline

## 1. Overview
This document outlines the data acquisition, quality control (QC), and feature extraction protocols for TCGA and CPTAC cohorts.

---

## 2. Transcriptomics Preprocessing (RNA-seq)
- **Source Data**: GDC STAR - Counts files for TCGA-GBM and TCGA-LGG.
- **Normalization Pipeline**:
  1. Parse STAR count files to generate raw count matrices.
  2. Compute Transcripts Per Million (TPM) and apply $\log_2(\text{TPM} + 1)$ transformation.
  3. Filter low-expression genes ($\text{mean } \log_2\text{-TPM} > 0.1$).
  4. Select top 5,000 Highly Variable Genes (HVGs) based on variance.
  5. Compute 128-dimensional PCA embeddings for downstream multimodal fusion.

---

## 3. Histopathology Preprocessing (WSI)
- **Slide Selection**: Primary diagnostic whole-slide images (`.svs` format at 20x/40x magnification). One best slide per patient selected.
- **Patch Extraction**:
  - Otsu thresholding for tissue detection.
  - $256 \times 256$ pixel non-overlapping patch extraction at 20x magnification.
  - Background filtering (>50% tissue fraction threshold).
- **Feature Encoders**:
  - **ResNet-50**: ImageNet pre-trained baseline encoder ($2048$-dim).
  - **CTransPath**: Pathology-specific vision transformer encoder ($768$-dim).
  - Mean slide-level feature pooling for patient-level classifier inputs.
  - Streaming H5 feature storage ($768$-dim features + coordinate metadata `coords_level0`) for reference patch retrieval.
