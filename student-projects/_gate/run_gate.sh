#!/usr/bin/env bash
# Thin wrapper around gate.py -- see student-projects/_gate/README.md.
#
# Usage:
#   student-projects/_gate/run_gate.sh <slug> [extra gate.py args...]
#
# Example:
#   student-projects/_gate/run_gate.sh 01-word-seg-pos
#   student-projects/_gate/run_gate.sh 01-word-seg-pos --skip-venv   # fast local dry run
set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "usage: $0 <slug> [extra gate.py args...]" >&2
    exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${VIETNLP_PYTHON:-python3}"

exec "$PYTHON" "$SCRIPT_DIR/gate.py" "$@"
