# NeuroBridge

Source-only research code for **GBM-like versus LGG-like** analysis using matched histopathology and gene-expression features. This retrospective methods package provides patient-level classification, missing-modality representation mapping, and histology-to-molecular target modeling. **Research only; not a diagnostic application.**

## Install and test (Linux, Python 3.11)

```bash
conda create -n neurobridge python=3.11 -y
conda activate neurobridge
bash setup_cpu.sh  # installs CLI and CPU-only PyTorch into active neurobridge env
neurobridge demo
```

To use a CUDA GPU, follow [PyTorch's official selector](https://pytorch.org/get-started/locally/) rather than installing the CPU wheel. Installing `requirements-full.txt` may download CUDA libraries on Linux. A lightweight installation can run `neurobridge --help` and input validation **without PyTorch**.

## Run on the original prepared study features

```bash
cp configs/example.yaml my-study.yaml
# Edit project: to point to YOUR prepared TCGA study directory.
neurobridge validate --config my-study.yaml --stage classification
neurobridge run --config my-study.yaml --stage classification
```

Use `--stage core` to run classification and biological target analysis, or `--stage external` to **verify historical external output files** (not refit external models). `--stage full` requires saved historical CPTAC and Gene2Morph files. Results are written under `PROJECT/results/corrected_v3/RUN_ID/`; every new analysis needs a distinct `run_id`. See [reproducibility and stage instructions](docs/REPRODUCIBILITY.md).

`neurobridge demo` uses **synthetic data** and is strictly a software smoke test, not a re-evaluation of the manuscript. The canonical retrospective fixed-test group was previously examined during development. No patient data, raw slides, trained weights, or generated predictions are shipped in this repository.
