#!/bin/sh
set -eu
package_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec xdg-open "$package_dir/Run Forecasts.html"
