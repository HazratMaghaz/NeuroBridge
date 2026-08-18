# Model Pipeline Architecture

## 1. Overview
NeuroBridge implements a modular, bidirectional architecture coupling pathology vision transformers and RNA-seq molecular embeddings.

```text
       [Bulk RNA-seq]                          [Diagnostic WSI]
             |                                         |
             v                                         v
   (5,000 HVG Expression)                   (CTransPath Transformer)
             |                                         |
             v                                         v
     [PCA 128-dim]                           [Slide Mean 768-dim]
             |                                         |
             +--------------------+--------------------+
                                  |
                                  v
                    [Multimodal Concatenation]
                                  |
                                  v
                   [Phase 8D v5 Robust Classifier]
                                  |
               +------------------+------------------+
               |                                     |
               v                                     v
       (GBM-like Probability)               (LGG-like Probability)
```

---

## 2. Model Specifications

### A. Phase 8D v5 Missing-Modality Robust Classifier
- **Input**: Multimodal embedding $[X_{\text{RNA\_128}}, X_{\text{WSI\_768}}]$ ($896$-dim).
- **Architecture**: Ensembled Ridge / Logistic Regression classifier trained with modality dropout (0%, 50%, 100% missing modality).
- **Target**: Canonical classification (`GBM` vs. `LGG`).

### B. Phase 15G Image-to-Biology Ridge Model
- **Input**: 768-dimensional CTransPath patch embedding.
- **Targets**: 25 biologically prioritized targets including proliferative markers (*AURKA*, *CCNB1*, *KIF11*), ECM remodeling pathways (*COL4A1*, *ANGPT2*), and histone chromatin drivers (*HIST1H3B*).
- **Output**: Scaled target prediction scores and directionality (`high` vs. `low`).

### C. Gene2Morph Reference Patch Retrieval Engine
- **Input**: 128-dimensional RNA molecular embedding.
- **Transformation**: Linear projection to 768-dimensional predicted CTransPath embedding.
- **Retrieval Engine**: Cosine similarity heap search over 686 WSI H5 feature files.
- **LOO Self-Exclusion**: Filters out any H5 files or candidate patches matching `query_patient_id`.
- **Deterministic Sort**: Final ordering by `score DESC, h5_path ASC, patch_index ASC`.
