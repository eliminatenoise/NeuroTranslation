#!/bin/sh
set -eu
cd "$(dirname "$0")"
exec xdg-open "$(pwd -P)/index.html"
