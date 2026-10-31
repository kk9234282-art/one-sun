#!/bin/sh
set -eu
cd /workspace/one-sun
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -c 'from intelligence import create_app; create_app()'
