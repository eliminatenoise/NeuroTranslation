#!/bin/sh
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -n "${NEUROTRANSLATION_BROWSER:-}" ]; then
  exec "$NEUROTRANSLATION_BROWSER" "$here/index.html"
fi
exec xdg-open "$here/index.html"
