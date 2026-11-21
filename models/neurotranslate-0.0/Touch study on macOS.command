#!/bin/sh
set -eu
cd -P -- "$(dirname -- "$0")"
exec /bin/sh "./Demo on macOS.command" --touch "$@"
