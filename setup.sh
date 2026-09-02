#!/bin/bash
# One-shot Mac setup for a clone of this repo. Safe to re-run.
# Does not write secrets. Does not overwrite an existing backtalk.json.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
SUPPORT="$HOME/Library/Application Support/jarvis"
VAULT="${JARVIS_VAULT:-$HOME/jarvis-vault}"

echo "== Jarvis setup =="
echo "    repo:  $ROOT"
echo "    vault: $VAULT"

mkdir -p "$SUPPORT/conversations"
printf '%s\n' "$ROOT" > "$SUPPORT/install_root"

need_brew() {
  if ! command -v brew >/dev/null 2>&1; then
    echo "Homebrew is required: https://brew.sh"
    exit 1
  fi
}

pkg() {
  if brew list --formula "$1" >/dev/null 2>&1; then
    echo "-- $1: already present"
  else
    echo "-- installing $1"
    brew install "$1"
  fi
}

if [ "$(uname -s)" = "Darwin" ]; then
  need_brew
  pkg python
  pkg ffmpeg
  pkg espeak-ng
  pkg portaudio
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "-- installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

echo "-- backtalk environment"
(
  cd "$ROOT/backtalk"
  uv venv .venv -q 2>/dev/null || true
  uv sync -q --inexact 2>/dev/null || uv pip install --python .venv/bin/python -q -e .
)

echo "-- overlay venv (PyWebview + AppKit)"
OV="$ROOT/ai-visualizer/.overlay-venv"
if [ ! -x "$OV/bin/python" ]; then
  python3 -m venv "$OV"
fi
"$OV/bin/pip" install -q --upgrade pip
"$OV/bin/pip" install -q pywebview pyobjc-framework-Cocoa

if [ ! -f "$ROOT/backtalk/backtalk.json" ]; then
  echo "-- writing backtalk.json for this machine"
  python3 - "$ROOT" "$VAULT" <<'PY'
import json, os, sys
root, vault = sys.argv[1], sys.argv[2]
cfg = {
    "agent_dir": root,
    "name": "Jarvis",
    "extra_dirs": [vault] if os.path.isdir(vault) else [],
    "ptt_key": "right_option",
    "mic_mode": "open",
    "wake_phrase": "hey jarvis",
    "voice": "bm_lewis",
    "permission_mode": "bypassPermissions",
    "resume_last_session": False,
    "barehands_state_dir": os.path.join(root, "barehands", "state"),
    "thinking_sound": "assets/thinking.wav",
    "greeting": "Standing by, sir.",
    "greeting_open_mic": "Standing by, sir.",
    "command_silence_ms": 1000,
    "agents": {
        "jarvis": {
            "name": "Jarvis",
            "voice": "bm_lewis",
            "face": "rain",
            "prompt": "You are Jarvis. You are not Friday. This conversation is Jarvis only. Never call yourself Friday.",
        },
        "friday": {
            "name": "Friday",
            "voice": "af_heart",
            "face": "rain",
            "prompt": "You are Friday, a female AI operator. You are not Jarvis. Never introduce yourself as Jarvis. This conversation is yours alone, separate from Jarvis.",
        },
    },
}
path = os.path.join(root, "backtalk", "backtalk.json")
with open(path, "w") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")
print("   wrote", path)
PY
else
  echo "-- backtalk.json: leaving the existing file"
fi

if [ ! -f "$ROOT/ai-visualizer/ai-visualizer.json" ]; then
  echo "-- writing ai-visualizer.json for this machine"
  python3 - "$ROOT" <<'PY'
import json, os, sys
root = sys.argv[1]
cfg = {
    "name": "JARVIS",
    "badge": "",
    "face": "rain",
    "port": 8790,
    "bus_dir": os.path.join(root, "backtalk"),
    "thinking_sound": True,
}
path = os.path.join(root, "ai-visualizer", "ai-visualizer.json")
with open(path, "w") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")
print("   wrote", path)
PY
else
  echo "-- ai-visualizer.json: leaving the existing file"
fi

if [ ! -d "$VAULT" ]; then
  echo "-- vault not at $VAULT (optional). Copy jarvis-vault there, or set JARVIS_VAULT."
fi

echo "-- installing /Applications/Jarvis.app"
ditto "$ROOT/apps/Jarvis.app" /Applications/Jarvis.app
chmod +x /Applications/Jarvis.app/Contents/MacOS/Jarvis
chmod +x /Applications/Jarvis.app/Contents/MacOS/jarvis-host.py
codesign --force --deep -s - /Applications/Jarvis.app >/dev/null 2>&1 || true

if ! security find-generic-password -a "$USER" -s claude-console-api -w >/dev/null 2>&1; then
  echo
  echo "!! Keychain item claude-console-api is missing."
  echo "   Store the Console API key (never in a file):"
  echo "   security add-generic-password -a \"\$USER\" -s claude-console-api -w 'THE_KEY' -U"
fi

echo
echo "Done. Open Jarvis from Applications, or: open -a Jarvis"
echo "First voice line downloads Whisper + Kokoro (~1GB). Mic + Accessibility prompts are one-time."
echo "Wake: Hey Jarvis / Hey Friday. Quit the dock icon to kill the stack."
