# Reproducing the NeuroBridge analysis

## Research scope

The corrected research analysis distinguishes GBM-like from LGG-like patterns in paired TCGA cohorts. This repository distributes methods code and unit tests only. It is not the historic thesis working directory or the optional research GUI.

## Software

Use Python 3.11 on Linux. Install `requirements.txt` and run `python -m unittest discover -s analysis/tests -p 'test_*.py' -v` before processing biomedical data. GPU execution requires a compatible PyTorch/CUDA installation.

## Required external inputs (not included)

All paths below are relative to the root selected by `PROJECT`:

- `metadata/phase6b_patient_splits.csv`: `patient_id`, `split`, `project_id`, with train/val/test rows.
- `data/expression/processed/expression_matrix_log2_tpm_filtered.csv`: patient rows and gene-expression columns.
- `data/expression/processed/expression_gene_annotation.csv`: annotation used for target selection.
- `features/ctranspath_7B_wsi_streaming_full/patient_level_ctranspath_mean_embeddings.csv`: patient-level CTransPath embeddings.
- `embeddings/slide_embeddings/resnet50_full_selected_best_mean_pool_patient_embeddings_final.csv`: patient-level ResNet-50 embeddings.

The full retrospective four-stage run also needs existing external CPTAC and strict Gene2Morph LOO tables. Consult `analysis/scripts/03_external_genemorph_reporting.py` for its expected file locations. The script checks supplied outputs; it **does not** independently regenerate external predictions.

Acquire source datasets through their original portals and comply with the data-use agreements. Do not commit patient-level CSVs, diagnostic WSIs, or restricted records.

## Running

```bash
PROJECT=/absolute/path/to/your/local/study \
NEUROBRIDGE_SPLITS_CSV=metadata/phase6b_patient_splits.csv \
DEVICE=cpu \
IMG_TO_MOL=ridge \
bash analysis/run.sh release_reproduction programs_only
```

`enrichr` is an optional online pathway-enrichment mode requiring `gseapy` and a network connection. Other software dependencies are documented in `requirements.txt`.

## Methods and interpretation boundaries

Corrected development evaluation refits molecular transformations, supervised representation learning, and cross-modal estimators inside development cross-validation folds. The fixed 103-patient partition was examined historically and must be described as retrospective, not an untouched independent test. External CPTAC-GBM contains only GBM cases, so its evaluations cannot establish LGG specificity. Gene2Morph retrieves real reference patches, not synthetic histology images.

## Version provenance

The scripts are copied from the connected private NeuroBridge V3 analysis source. The staging script changes **only machine-specific default file paths**, never model-fitting or evaluation logic. `SOURCE_SHA256.json` contains checksums of staged scripts for audit and traceability.
