# NeuroBridge

Research code for **GBM-like versus LGG-like** analysis using paired histopathology and gene-expression features.

NeuroBridge provides corrected patient-level evaluation, missing-modality feature mapping, and molecular-target analysis. **Research use only — not a diagnostic or clinical tool.**

## Quick start

```bash
# After cloning this repository:
conda create -n neurobridge python=3.11 -y
conda activate neurobridge
python -m pip install -r requirements.txt
python -m unittest discover -s analysis/tests -p 'test_*.py' -v
bash quick_demo.sh  # small synthetic CPU execution, not manuscript results
```

The five included tests use **synthetic inputs**. You can inspect the full workflow without data:

```bash
python analysis/scripts/01_corrected_classification.py --help
bash analysis/run.sh --help
```

## Run an analysis

You must first obtain the original research datasets and prepare the required patient-level feature matrices. Dataset locations are described in [the reproducibility guide](docs/REPRODUCIBILITY.md).

```bash
export PROJECT=/path/to/your/research/data
export NEUROBRIDGE_SPLITS_CSV=metadata/phase6b_patient_splits.csv
export DEVICE=cpu
bash analysis/run.sh my_reproduction programs_only
```

The full four-stage command also needs saved **historical external-validation and Gene2Morph inputs**, which are **not** included here. It will stop rather than invent missing results.

## Contents

- [`analysis/`](analysis/) — corrected analysis scripts and invariants
- [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) — data contract and evaluation details
- [`LICENSE`](LICENSE) and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) — license boundaries

**No patient data, WSIs, model weights, trained checkpoints, or generated predictions are included.** The retrospective test set was previously examined during model development. These scripts are not a clinically validated inference application.
