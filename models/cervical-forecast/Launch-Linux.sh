#!/bin/sh
set -eu
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$base/forward.py" "${1:-$base/example.json}"
