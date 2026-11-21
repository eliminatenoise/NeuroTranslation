#!/bin/sh
set -eu
folder=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
exec xdg-open "$folder/index.html"
