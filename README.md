# CNS-MultiModalAI

**Bidirectional WSI–Transcriptome Missing-Modality Framework for GBM/LGG Glioma Analysis**

CNS-MultiModalAI is a research framework for multimodal CNS tumor analysis using paired histopathology whole-slide images (WSIs) and gene-expression profiles. The project focuses on GBM/LGG glioma classification, bidirectional missing-modality inference, image-to-biology prediction, and molecular-to-morphology retrieval-based visualization.

> Current validated scope: **GBM-like vs LGG-like analysis using TCGA-GBM/TCGA-LGG as the internal reference cohort.**  
> External testing currently includes **CPTAC-GBM** as an independent GBM-positive validation cohort.

---

## Project Summary

This repository contains the code, notebooks, and documentation for a thesis-stage multimodal AI framework that integrates:

- WSI patch extraction and pathology feature learning
- ResNet-50 baseline image embeddings
- CTransPath pathology-specific image embeddings
- gene-expression molecular representations
- image → molecular missing-modality prediction
- molecular → image embedding prediction
- missing-modality robust GBM/LGG classification
- WSI/image → selected gene/pathway/program prediction
- molecular profile → real-patch morphology retrieval canvas
- experimental synthetic-like patch generation
- external validation workflow using CPTAC-GBM

---

## Main Research Question

Can histopathology image representations and gene-expression representations be integrated into a bidirectional multimodal AI framework that remains useful when one modality is missing?

---

## Locked Thesis-Safe Flows

### 1. WSI / patch images → biology prediction

```text
WSI / patch folder
↓
CTransPath embedding
↓
GBM-like / LGG-like prediction
↓
selected gene/pathway/program prediction
↓
clinical relevance summary
```

### 2. Gene expression → morphology preview

```text
gene-expression profile
↓
molecular representation
↓
GBM-like / LGG-like prediction
↓
predicted image embedding
↓
retrieved real patches
↓
1000-patch morphology canvas
↓
clinical relevance summary
```

Important: the morphology canvas is **retrieval-based** and uses **real histology patches**. It is not a true WSI reconstruction.

---

## Current Dataset Status

### Internal reference cohort

| Dataset | Use |
|---|---|
| TCGA-GBM | internal GBM reference |
| TCGA-LGG | internal LGG reference |
| Paired WSI + expression | main multimodal training/evaluation |

Current internal cohort:

```text
686 paired patients
195 TCGA-GBM
491 TCGA-LGG
```

### External validation cohort

| Dataset | Current status |
|---|---|
| CPTAC-GBM RNA | downloaded and organized |
| CPTAC-GBM WSI | downloaded and organized |
| PDC clinical metadata | downloaded and organized |

Current CPTAC-GBM external files:

```text
527 SVS WSI files
126 GB WSI folder size
RNA archive + extracted RNA files available
PDC clinical CSVs available
```

CPTAC-GBM is used as an independent **GBM-positive** external cohort. It does not provide full GBM-vs-LGG external validation by itself.

---

## Repository Structure

Recommended local structure:

```text
.
├── notebooks/
│   ├── phase01_*.ipynb
│   ├── phase07_*.ipynb
│   ├── phase08_*.ipynb
│   ├── phase09_*.ipynb
│   ├── phase10_*.ipynb
│   ├── phase11_*.ipynb
│   └── phase12_*.ipynb
├── scripts/
│   ├── preprocessing/
│   ├── embeddings/
│   ├── modeling/
│   ├── external_validation/
│   └── utils/
├── src/
│   └── cns_multimodalai/
│       ├── data/
│       ├── models/
│       ├── inference/
│       ├── visualization/
│       └── reporting/
├── configs/
├── docs/
├── results/
├── review_packages/
├── metadata/
├── qc/
└── README.md
```

Large datasets are **not** committed to GitHub.

---

## Data Policy

This repository should contain code, notebooks, configs, metadata templates, and documentation.

Do **not** commit:

- `.svs` whole-slide images
- raw RNA archives
- extracted expression matrices if large
- model checkpoints
- patch folders
- generated embeddings
- review ZIPs
- generated result folders
- private clinical metadata if restricted

Use the provided `.gitignore`.

Recommended options for large file tracking:

- DVC for reproducible local data versioning
- Git LFS only for small model artifacts if absolutely needed
- external storage / institutional storage for WSI and omics data

---

## Completed Phases

| Phase | Status | Summary |
|---|---|---|
| 1–3 | Complete | data matching, WSI QC, expression QC |
| 4–6 | Complete | patch extraction, ResNet-50 baseline |
| 7 | Complete | CTransPath setup, embeddings, encoder comparison |
| 8A | Complete | molecular encoder baselines |
| 8B | Complete | image → molecular embedding prediction |
| 8C/8C-2 | Complete | molecular → image embedding prediction |
| 8D | Complete | missing-modality robust classifier |
| 9A–9C | Complete | biomarkers, pathway enrichment, protein-coding interpretation |
| 10A/v2 | Complete | final internal result consolidation |
| 11A | Complete | WSI/image → selected gene/pathway prediction |
| 11B | Complete | molecular → representative patch retrieval |
| 11C | Complete | molecular → 1000 real-patch morphology canvas |
| 11D | Experimental | synthetic-like patch generation |
| 12A | Template ready | external inference/validation template |
| 12B | Pending | CPTAC-GBM RNA preparation |
| 12C | Pending | CPTAC-GBM WSI validation |
| 12D | Pending | final external validation summary |

---

## Current Main Claims

Safe thesis-ready claim:

> This project developed a bidirectional multimodal AI framework integrating histopathology WSI embeddings and gene-expression representations for GBM/LGG glioma analysis. The framework supports missing-modality inference, predicts selected biologically relevant gene/pathway programs from WSI embeddings, and generates real-patch morphology previews from molecular profiles.

Avoid overclaiming:

- not a pan-CNS tumor classifier yet
- not true WSI reconstruction
- not full transcriptome reconstruction
- not clinically validated biomarkers
- not a diagnostic tool

---

## External Validation Plan

### CPTAC-GBM

Use as independent GBM-positive external validation:

```text
CPTAC-GBM WSI
↓
patch extraction
↓
CTransPath embedding
↓
expected result: GBM-like
```

```text
CPTAC-GBM RNA
↓
Phase 12B preparation
↓
Phase 12A expression inference
↓
expected result: GBM-like
```

### Remaining External LGG Need

CPTAC-GBM does not include LGG. For true external GBM-vs-LGG accuracy, add:

- CGGA expression cohort
- REMBRANDT expression cohort
- external LGG WSI cohort if available

---

## Installation

Example environment:

```bash
conda activate ai-gpu

pip install numpy pandas scipy scikit-learn matplotlib pillow tqdm
pip install torch torchvision
pip install gseapy
```

CTransPath requires its repository and checkpoint to be placed locally:

```text
models/external/TransPath/
models/weights/ctranspath/ctranspath.pth
```

---

## Running the Project

Recommended order:

```bash
# 1. Internal project phases
notebooks/phase01_to_phase11/

# 2. External validation
notebooks/phase12A_external_inference_and_validation_template.ipynb
notebooks/phase12B_prepare_CPTAC_GBM_RNA_for_external_validation.ipynb
notebooks/phase12C_CPTAC_GBM_WSI_external_validation.ipynb

# 3. Final report writing
docs/thesis/
docs/manuscript/
```

---

## Planned Software/Product Version

Future GUI:

```text
Frontend: Next.js / React
Backend: FastAPI
Worker: background inference jobs
Model layer: PyTorch + scikit-learn
Storage: local / MinIO / S3
Deployment: Docker Compose first
```

Planned user flows:

1. Upload WSI patches → get GBM/LGG-like prediction + gene/pathway report.
2. Upload gene-expression CSV → get GBM/LGG-like prediction + morphology canvas.
3. Download PDF/CSV report.

---

## Keywords

`multimodal-ai`, `computational-pathology`, `glioblastoma`, `low-grade-glioma`, `cns-tumors`, `whole-slide-images`, `gene-expression`, `missing-modality`, `ctranspath`, `resnet50`, `transcriptomics`, `pathomics`, `bioinformatics`, `precision-oncology`, `medical-ai`, `deep-learning`

---

## Suggested Citation

If this repository is used, please cite the thesis/manuscript associated with this project once available.

---

## License

Code license: MIT License  
Data: not included; governed by the original data providers such as TCGA/GDC, CPTAC/PDC, and TCIA.

---

## Maintainer

Hazrat Maghaz  
Bioinformatics / Computational Biology / Multimodal AI