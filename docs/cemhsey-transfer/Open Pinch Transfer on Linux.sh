#!/bin/sh
set -eu
folder=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
exec xdg-open "$folder/index.html"
