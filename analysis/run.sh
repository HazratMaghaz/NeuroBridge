#!/usr/bin/env bash
# End-to-end retrospective V3 analysis. Historical project results are never overwritten.
set -euo pipefail
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" || $# -eq 0 ]]; then
  echo "Usage: PROJECT=/path/to/study bash analysis/run.sh RUN_ID [enrichr|programs_only|/path/genes.gmt]"
  exit 0
fi
: "${PROJECT:?Set PROJECT to the directory containing the locally obtained study inputs}"
RUN_ID="${1:-}"
ENRICHMENT_MODE="${2:-enrichr}" # enrichr | programs_only | /absolute/path/to/gene_sets.gmt
IMG_TO_MOL="${IMG_TO_MOL:-ridge}" # ridge (new fixed choice) | mlp (Phase8B-like, slower)
CV_FOLDS="${CV_FOLDS:-5}"; CV_REPEATS="${CV_REPEATS:-3}"
DEVICE="${DEVICE:-cpu}"
if [[ -z "$RUN_ID" ]]; then
  echo 'Usage: bash run_local.sh v3_corrected_20261019_r01 [enrichr|programs_only|/absolute/path/to/genes.gmt]' >&2
  exit 2
fi
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$PROJECT/results/corrected_v3/$RUN_ID"
echo "===== STRICT V3 ANALYSIS: $RUN_ID ====="
echo '1/4 Corrected classification: all preprocessing + representation + mapping refit within each development fold.'
python "$HERE/scripts/01_corrected_classification.py" \
  --project "$PROJECT" --run-id "$RUN_ID" --cv-folds "$CV_FOLDS" --cv-repeats "$CV_REPEATS" \
  --epochs 150 --patience 20 --pca-dim 128 --topvar 5000 --img-to-mol "$IMG_TO_MOL" --device "$DEVICE"
echo '2/4 Development-only biomarker and pathway selection + molecular decoder.'
if [[ "$ENRICHMENT_MODE" == 'enrichr' ]]; then
  python "$HERE/scripts/02_corrected_biology.py" --project "$PROJECT" --run-id "$RUN_ID" --enrichr
elif [[ "$ENRICHMENT_MODE" == 'programs_only' ]]; then
  python "$HERE/scripts/02_corrected_biology.py" --project "$PROJECT" --run-id "$RUN_ID"
else
  python "$HERE/scripts/02_corrected_biology.py" --project "$PROJECT" --run-id "$RUN_ID" --gmt "$ENRICHMENT_MODE"
fi
echo '3/4 Historical CPTAC and strict Gene2Morph LOO assertions/reporting.'
python "$HERE/scripts/03_external_genemorph_reporting.py" --project "$PROJECT" --run-id "$RUN_ID"
echo '4/4 Verify all files and create review ZIP.'
python "$HERE/scripts/04_verify_and_package.py" --project "$PROJECT" --run-id "$RUN_ID"
echo 'DONE. Send the review ZIP from:'
echo "$PROJECT/results/corrected_v3/${RUN_ID}_REVIEW_BUNDLE.zip"
