#!/bin/sh
set -eu
cd "$(dirname "$0")"
exec open "$(pwd -P)/forecast.html"
