#!/bin/sh
here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || exit 1
exec open "$here/index.html"
