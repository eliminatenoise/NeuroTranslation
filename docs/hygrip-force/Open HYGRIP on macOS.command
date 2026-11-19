#!/bin/sh
set -eu
folder=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
exec /usr/bin/open "$folder/index.html"
