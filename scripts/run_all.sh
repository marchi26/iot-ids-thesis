#!/usr/bin/env bash
set -euo pipefail

if [ -f ".venv/bin/activate" ]; then
  . .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
  . .venv/Scripts/activate
fi

python src/experiments/run_all.py
