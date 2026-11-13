# NeuroBridge: research reproducibility and inputs

## Scope

This repository implements the corrected V3 retrospective **feature-level** TCGA-GBM/LGG evaluation. It is not a WSI-to-result workflow, a FASTQ processor, a trained patient-level predictor, or a production API. It does not automatically download GDC/TCIA data. Source WSIs, gene-expression processing and pretrained pathology feature extraction were performed upstream and are not reproduced end-to-end here.

## Environment

Install on Linux with Python 3.11:

```bash
conda create -n neurobridge python=3.11 -y
conda activate neurobridge
bash setup_cpu.sh
python -m unittest discover -s tests -p 'test_*.py' -v
python -m unittest discover -s analysis/tests -p 'test_*.py' -v
```

PyTorch is required for the classification or demo stage, but not for preflight. For a CPU build:

```bash
neurobridge demo --output /tmp/neurobridge-synthetic-demo
```

For GPU execution, choose the supported CUDA build from [PyTorch installation instructions](https://pytorch.org/get-started/locally/). Optional Enrichr selection uses `python -m pip install '.[enrichment]'` and requires network access.

## Configure and validate

Copy `configs/example.yaml` to a private/local YAML file. Set `project` to the directory containing the original *prepared* patient-level feature matrices. In the configuration, `split_csv` is resolved relative to that project; `project` itself is resolved relative to the YAML file when not absolute. **Do not commit the local configuration or any real cohort files.**

```bash
neurobridge validate --config my-study.yaml --stage classification
neurobridge run --config my-study.yaml --stage classification
```

### Required files under `project`

| Path | Requirement |
| --- | --- |
| `metadata/phase6b_patient_splits.csv` | Patient IDs, `split`, `project_id`; exactly 480 train, 103 validation, 103 test |
| `data/expression/processed/expression_matrix_log2_tpm_filtered.csv` | 686 matched patient IDs and ENSG expression columns |
| `features/ctranspath_7B_wsi_streaming_full/patient_level_ctranspath_mean_embeddings.csv` | 768 indexed CTransPath columns and 686 patient IDs |
| `embeddings/slide_embeddings/resnet50_full_selected_best_mean_pool_patient_embeddings_final.csv` | 2,048 indexed ResNet50 columns and 686 patient IDs |
| `data/expression/processed/expression_gene_annotation.csv` | Required by biology stage; `gene_id_clean` and `gene_type` |

The validator checks files, patient identity/splits, and feature-column dimensions. The scientific scripts additionally check finite numerical inputs and prevent silent patient joins. Input access follows applicable dataset licenses and approvals.

## Supported run stages

- `classification`: corrected fold-isolated evaluation, eight feature-availability scenarios and six core scenarios; generates figure-source tables and Figures 2–3.
- `biology`: development-selected molecular targets with Ridge estimation; requires annotation. `programs_only` works offline; `enrichr` requires gseapy/network and uses a live external library; `.gmt` accepts a prespecified independent gene set file.
- `core`: classification then biology; does **not** require historical external data.
- `external`: verifies saved historical CPTAC RNA, CPTAC WSI and six Gene2Morph LOO source files; does **not** regenerate model predictions.
- `package`: requires completed classification, biology, and external manifests, then produces the review ZIP.
- `full`: classification + biology + external + package; preflight requires all historical source outputs.

```bash
neurobridge run --config my-study.yaml --stage core
neurobridge run --config my-study.yaml --stage classification --dry-run
```

Stages refuse to overwrite existing non-empty output directories. Use a fresh `run_id` for reruns. Outputs are always saved under `project/results/corrected_v3/<run_id>/` to preserve existing algorithms; this release does **not** support a separate output-root flag for real analyses.

## Scientific boundaries

The 103-patient fixed TCGA test cohort was examined in historical project experiments, so the corrected classification is **retrospective re-evaluation, not pristine prospective testing**. PCA, supervised molecular encoders and cross-modal mappings are refitted within outer development folds. External CPTAC-GBM is GBM-only; patient-level GBM-positive recognition does not establish LGG specificity or external binary accuracy. Gene2Morph retrieves actual reference histology patches; current public code verifies six-query historical output rather than rerunning the whole retrieval bank. Histology-to-expression prediction estimates selected targets rather than complete measured RNA.

`SOURCE_SHA256.json` records original and staged scientific code hashes. CLI and validation code are additional wrappers; the core scientific algorithms remain unchanged.
