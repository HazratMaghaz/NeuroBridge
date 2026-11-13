#!/usr/bin/env bash
# Install source CLI and CPU-only PyTorch into an already-activated environment.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -z "${VIRTUAL_ENV:-}" && ( -z "${CONDA_DEFAULT_ENV:-}" || "${CONDA_DEFAULT_ENV}" == "base" ) ]]; then
  echo 'ERROR: First activate a dedicated Conda or venv environment (not base).' >&2
  echo 'Example: conda create -n neurobridge python=3.11 -y && conda activate neurobridge' >&2
  exit 2
fi
python -m pip install -e "$ROOT"
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
printf 'NeuroBridge installed. Run: neurobridge demo\n'
