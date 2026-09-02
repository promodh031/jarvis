#!/bin/bash
# Always-on-top matrix overlay. Kills a previous overlay, waits for 8790,
# then pins the rain HUD above every other window.
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
pkill -f "ai-visualizer/overlay.py" 2>/dev/null || true
pkill -f "overlay.py$" 2>/dev/null || true
sleep 0.3
VENV="$HERE/.overlay-venv"
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q --upgrade pip
  "$VENV/bin/pip" install -q pywebview pyobjc-framework-Cocoa
fi
exec "$VENV/bin/python" "$HERE/overlay.py"
