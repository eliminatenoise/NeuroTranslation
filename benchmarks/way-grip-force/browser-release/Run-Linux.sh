#!/bin/sh
here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || exit 1
exec xdg-open "$here/index.html"
