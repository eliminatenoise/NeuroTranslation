#!/bin/sh
set -eu
case $# in
  0) exec xdg-open "$(dirname "$0")/forecast.html" ;;
  *) exec node "$(dirname "$0")/launch.mjs" "$@" ;;
esac
