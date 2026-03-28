#!/usr/bin/env bash
# run.sh — start Unifi Browser inside a Python virtual environment
set -euo pipefail

VENV_DIR="$(dirname "$0")/.venv"
REQUIREMENTS="$(dirname "$0")/requirements.txt"

# ── Create venv if it doesn't exist ──────────────────────────────────────────
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR ..."
    python3 -m venv "$VENV_DIR"
fi

# ── Activate venv ─────────────────────────────────────────────────────────────
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# ── Install / update dependencies ─────────────────────────────────────────────
echo "Installing requirements ..."
pip install --quiet --upgrade pip
pip install --quiet -r "$REQUIREMENTS"

# ── Launch the app ────────────────────────────────────────────────────────────
echo "Starting Unifi Browser ..."
python3 "$(dirname "$0")/main.py"
