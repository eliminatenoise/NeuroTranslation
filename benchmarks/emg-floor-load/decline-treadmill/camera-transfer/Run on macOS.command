#!/bin/sh
exec python3 "$(dirname "$0")/forecast.py" "$@"
