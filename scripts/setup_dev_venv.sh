#!/usr/bin/env bash
# Create or refresh the single project virtualenv at repo-root .venv/
# Matches CI: Python 3.12 + requirements.txt (+ optional GPS script deps).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PY="${PYTHON:-python3.12}"
if ! command -v "$PY" >/dev/null 2>&1; then
  PY=python3
fi

echo "Using interpreter: $($PY --version 2>&1)"

if [[ ! -d .venv ]]; then
  echo "Creating .venv ..."
  "$PY" -m venv .venv
else
  echo "Refreshing existing .venv ..."
fi

# shellcheck source=/dev/null
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt -r requirements-gps-script.txt

echo ""
echo "Done. Activate with:"
echo "  cd $ROOT"
echo "  source .venv/bin/activate"
echo ""
echo "Verify:"
echo "  python -c \"import pandas; import streamlit; print('ok', pandas.__version__)\""
echo "  pytest tests/ -q"
