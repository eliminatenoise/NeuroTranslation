#!/bin/sh
cd "$(dirname "$0")" || exit 1
python3 predict.py example.json
status=$?
printf '\nPress Enter to close. '
read -r answer
exit "$status"
