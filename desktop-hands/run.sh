#!/bin/bash
# Desktop Hands — gesture mouse. Ctrl-C quits.
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
if [ ! -x .venv/bin/python ]; then
  echo "Desktop Hands venv missing. Recreate it from the Jarvis repo."
  exit 1
fi
if [ ! -f hand_landmarker.task ]; then
  echo "Missing hand_landmarker.task — the MediaPipe model never downloaded."
  exit 1
fi
exec .venv/bin/python desktop_hands.py "$@"
