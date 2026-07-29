#!/bin/bash
# Scoreboard OCR Tracker — launcher script (macOS)
# Uses the bundled .venv with all dependencies (EasyOCR, PyQt6, etc.)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="${SCRIPT_DIR}/../.venv"

if [ ! -d "$VENV" ]; then
    osascript -e 'display dialog "Virtual environment not found at '"$VENV"'. Please run setup first." buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi

export PATH="${VENV}/bin:$PATH"
export PYTHONPATH="${SCRIPT_DIR}/../src:${PYTHONPATH}"

exec "${VENV}/bin/python" -m scoreboard_ocr.app
