#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 predict.py example.json
