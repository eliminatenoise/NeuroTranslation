#!/bin/sh
set -eu
folder=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
exec /usr/bin/open "$folder/index.html"
