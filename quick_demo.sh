#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
DEMO_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/neurobridge-demo.XXXXXX")"
python analysis/tests/create_synthetic_dataset.py --out "$DEMO_ROOT"
OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 python analysis/scripts/01_corrected_classification.py   --project "$DEMO_ROOT" --run-id synthetic_smoke   --cv-folds 2 --cv-repeats 1 --epochs 1 --patience 1   --pca-dim 16 --topvar 100 --img-to-mol ridge --device cpu   --demo --skip-resnet
printf 'Synthetic smoke test complete (NOT manuscript results): %s
' "$DEMO_ROOT"
