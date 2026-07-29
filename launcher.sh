#!/bin/bash
# Scoreboard OCR Tracker — launcher script (macOS)
# Launch from project root with PaddleOCR backend

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"
VENV="${PROJECT_DIR}/.venv"

if [ ! -d "$VENV" ]; then
    echo "ERROR: Virtual environment not found at $VENV"
    echo "Run: cd $PROJECT_DIR && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'"
    exit 1
fi

export PYTHONPATH="${PROJECT_DIR}/src:${PYTHONPATH}"
exec "${VENV}/bin/python" -m scoreboard_ocr.app
