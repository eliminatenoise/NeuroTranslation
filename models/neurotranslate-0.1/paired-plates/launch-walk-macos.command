#!/usr/bin/env bash
set -e
launcher_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.9 or later is needed to run aligned_walk.py." >&2
  exit 1
fi
exec python3 -B "$launcher_dir/aligned_walk.py" "$@"
