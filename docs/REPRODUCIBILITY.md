# End-to-End Reproducibility Guide

## 1. Environment & Hardware Requirements
- **OS**: Ubuntu 22.04 LTS / Linux Mint 21+
- **Python**: 3.10.12
- **Conda Environment**: `ai-gpu`
- **Key Packages**: `torch>=2.0`, `scikit-learn>=1.2`, `h5py>=3.8`, `pandas>=2.0`, `numpy>=1.24`, `matplotlib>=3.7`

---

## 2. Environment Variables
Set the project root directory before running any scripts:
```bash
export CNS_PROJECT_ROOT=/path/to/CNS-MultiModalAI
export PYTHONPATH=/path/to/CNS-MultiModalAI/src:$PYTHONPATH
```

---

## 3. Unit Test Execution
Execute the comprehensive test suite verifying patient ID normalization, canonical diagnosis labeling, self-exclusion, bank audit accounting, and deterministic retrieval tie-breaking:
```bash
PYTHONPATH=src python -m unittest discover -v -s tests -p "test_*.py"
```

---

## 4. Reproducing Gene2Morph LOO Scientific Results
To reproduce the 6-query Leave-One-Patient-Out (LOO) reference morphology retrieval rerun:
```bash
python scripts/run_genemorph_loo_rerun.py --execute --output-root results/genemorph_loo_rerun_20260818
```

Verify generated outputs in `results/genemorph_loo_rerun_20260818/`:
- `old_vs_loo_query_comparison.csv`
- `figure5_identity_verification.csv`
- `self_exclusion_assertion_report.txt`
- `manuscript_impact.md`
