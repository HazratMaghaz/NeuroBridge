# End-to-End Reproducibility Guide

## 1. Environment & Hardware Requirements
- **OS**: Linux (Ubuntu 22.04 LTS / Linux Mint / RHEL)
- **Python**: 3.10+
- **Conda Environment**: `ai-gpu`
- **Key Packages**: `torch>=2.0`, `scikit-learn>=1.2`, `h5py>=3.8`, `pandas>=2.0`, `numpy>=1.24`, `matplotlib>=3.7`

---

## 2. Environment Variables & Setup
Set portable project root environment variables:
```bash
export CNS_PROJECT_ROOT="$(pwd)"
export PYTHONPATH="$CNS_PROJECT_ROOT/src:$PYTHONPATH"
```

---

## 3. Unit Test Execution
Execute the comprehensive test suite verifying patient ID normalization, canonical diagnosis labeling, self-exclusion, bank audit accounting, and deterministic retrieval tie-breaking:
```bash
python -m unittest discover -v -s tests -p "test_*.py"
```

---

## 4. Reproducing Gene2Morph LOO Scientific Results
To reproduce the 6-query Leave-One-Patient-Out (LOO) reference morphology retrieval rerun:
```bash
# Dry-run validation mode (no H5 bank search required)
python scripts/run_genemorph_loo_rerun.py

# Full scientific execution against H5 feature bank
python scripts/run_genemorph_loo_rerun.py --execute --output-root results/genemorph_loo_rerun_20260818_final
```

Verify generated outputs in `results/genemorph_loo_rerun_20260818_final/`:
- `old_vs_loo_query_comparison.csv`
- `figure5_identity_verification.csv`
- `self_exclusion_assertion_report.txt`
- `manuscript_impact.md`

Optionally pass `--h5-dir` if feature banks are located in a custom directory:
```bash
python scripts/run_genemorph_loo_rerun.py --execute --h5-dir /path/to/slide_h5 --output-root results/genemorph_loo_rerun_20260818_final
```
