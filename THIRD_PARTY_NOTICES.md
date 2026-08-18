# Third-Party Licenses & Notices

NeuroBridge / CNS-MultiModalAI relies on and interoperates with several open-source software libraries and public research datasets. This document details third-party notices, licensing terms, and data use policies.

---

## 1. CTransPath (TransPath) Model Architecture & Weights

- **Original Project**: CTransPath / TransPath
- **Source Repository**: [https://github.com/Xiyue-Wang/TransPath](https://github.com/Xiyue-Wang/TransPath)
- **Primary Publication**: Wang, X., et al. "Transformer-based unsupervised contrastive learning for histopathological image representation." *Medical Image Analysis* 81 (2022): 102559.
- **License**: GNU General Public License v3.0 (GPLv3) / Academic Non-Commercial Use.
- **Notice**: CTransPath source code and pre-trained weights (`ctranspath.h5`) are **NOT** redistributed within this repository. NeuroBridge dynamically loads external CTransPath weights via configurable paths (`config.CTRANSPATH_CKPT`). Users utilizing CTransPath feature extraction must comply with the licensing and non-commercial academic usage terms of the original authors.

---

## 2. PyTorch & Torchvision

- **Project**: PyTorch & Torchvision
- **Source Repository**: [https://github.com/pytorch/pytorch](https://github.com/pytorch/pytorch)
- **License**: BSD-style License.
- **Notice**: Used as the primary deep learning framework for feature extraction and neural network inference.

---

## 3. Scikit-learn & SciPy Stack

- **Project**: Scikit-Learn, NumPy, Pandas, SciPy, Matplotlib
- **License**: BSD 3-Clause License / MIT License / PSF License.
- **Notice**: Used for preprocessing, latent space modeling, PCA projection, evaluation metrics, and figure generation.

---

## 4. TCGA Data Use Notice (NCI / GDC)

- **Data Sources**: The Cancer Genome Atlas (TCGA-LGG, TCGA-GBM)
- **Access Portal**: NCI Genomic Data Commons (GDC) ([https://portal.gdc.cancer.gov](https://portal.gdc.cancer.gov))
- **Notice**: All primary TCGA Whole Slide Images (WSIs), STAR RNA-seq expression archives, and clinical metadata were obtained from open and controlled-access GDC tiers under appropriate Institutional Review Board (IRB) policies and NCI/NIH Data Use Certification. No raw controlled-access genomic or patient-identifiable data are redistributed within this software repository.

---

## 5. CPTAC Data Use Notice (NCI / PDC)

- **Data Sources**: Clinical Proteomic Tumor Analysis Consortium (CPTAC-3 Glioblastoma)
- **Access Portal**: NCI Proteomic Data Commons (PDC) ([https://pdc.cancer.gov](https://pdc.cancer.gov))
- **Notice**: External validation RNA-seq expression data were derived from CPTAC-3 open-access resources in compliance with CPTAC data release guidelines.
