#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
page="index.html"
[ -f "$page" ] || page="../../docs/neural-and-muscle-composites/index.html"
exec xdg-open "$page"
