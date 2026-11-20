#!/bin/sh
cd "$(dirname "$0")" || exit 1
python3 shared-motion-model/run_examples.py
result=$?
if [ -t 0 ] && [ -t 1 ]; then
  printf '\nPress Enter to close. '
  read -r answer
fi
exit "$result"
