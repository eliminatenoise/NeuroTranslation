#!/bin/sh
cd "$(dirname "$0")" || exit 1
python3 specialist.py invented-window.json
status=$?
if [ -t 0 ]; then printf '\nPress Enter to close. '; read -r answer; fi
exit "$status"
