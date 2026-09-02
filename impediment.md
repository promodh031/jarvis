# Jarvis Setup — Impediments & Status

## What's done

- [x] Python 3.12.14 installed (via Homebrew)
- [x] espeak-ng installed (Kokoro TTS phonemizer)
- [x] `uv` package manager available
- [x] backtalk Python venv created with all packages (~900MB): claude-agent-sdk, faster-whisper, mlx-whisper, kokoro, sounddevice, pynput, webrtcvad, numpy, httpx
- [x] Overlay venv created with pywebview + pyobjc-framework-Cocoa
- [x] `backtalk.json` config created (agent name: Jarvis, PTT key: home, voice: bm_lewis)
- [x] `ai-visualizer.json` config created (face: board, bus wired to backtalk)
- [x] ai-visualizer server ready (zero dependencies)
- [x] Anthropic API key stored in macOS Keychain (`claude-console-api`)
- [x] Barehands glass board running (`http://127.0.0.1:8794/stage.html`)

## Remaining blocker

### Zscaler blocks HuggingFace — cannot download ML models

The corporate Zscaler proxy returns **403 Forbidden** for all requests to `huggingface.co` and mirrors like `hf-mirror.com`. This blocks downloading:

- **Whisper STT model** (`mlx-community/whisper-small.en-mlx`) — ~500MB, speech-to-text
- **Kokoro TTS model** (`hexgrad/Kokoro-82M`) — ~500MB, text-to-speech

These are the AI's ears and mouth — without them, the voice loop cannot start.

**How to fix (pick one):**

1. **Connect to a non-corporate network** (home Wi-Fi, phone hotspot), then run:
   ```bash
   cd "/Users/pmunjeti/OTC Web/jarvis/backtalk"
   SSL_CERT_FILE=/opt/homebrew/etc/openssl@3/cert.pem .venv/bin/python -c "
   import warnings; warnings.filterwarnings('ignore')
   from backtalk.ears import warm as warm_ears
   from backtalk.mouth import warm as warm_mouth
   warm_ears()
   warm_mouth()
   print('Models ready')
   "
   ```

2. **Request IT to whitelist huggingface.co** in Zscaler (domains: `huggingface.co`, `cdn-lfs.huggingface.co`)

3. **Download on another machine** and copy the cache:
   - Models cache to: `~/.cache/huggingface/hub/`
   - Need: `models--mlx-community--whisper-small.en-mlx` and `models--hexgrad--Kokoro-82M`

## What to do after the blocker is resolved

### 1. Download the models
Run the command from "How to fix" option 1 above. Takes ~5 minutes on a decent connection.

### 2. Launch the full stack
```bash
# Option A — launch everything at once via the macOS app:
open "/Users/pmunjeti/OTC Web/jarvis/apps/Jarvis.app"

# Option B — start components individually:
cd "/Users/pmunjeti/OTC Web/jarvis/ai-visualizer" && ./run.sh &     # Face server (port 8790)
cd "/Users/pmunjeti/OTC Web/jarvis/ai-visualizer" && ./overlay.sh &  # Floating widget
cd "/Users/pmunjeti/OTC Web/jarvis/backtalk" && ./run.sh             # Voice engine
```

### 3. Grant macOS permissions (prompted on first run)
- **Microphone** — for Whisper speech-to-text
- **Input Monitoring** — for push-to-talk key (System Settings → Privacy & Security → Input Monitoring → add your terminal app)

### 4. Talk to Jarvis
- Hold the **Home** key (PTT) and speak, then release
- Or say "Hey Jarvis" if open-mic mode is enabled in `backtalk.json`
- Say "goodbye Jarvis" to end the session

### 5. Barehands glass board
Already running at `http://127.0.0.1:8794/stage.html`. Open in **Chrome** for webcam hand tracking.
- **Pinch-drag** to move items
- **Clap** to clear the board
- **Claw gesture** to grab distant items
- **Two-hand pinch** to scale
- **Flick** to throw

### 6. Desktop-hands (optional)
Webcam mouse control — requires separate setup:
```bash
cd "/Users/pmunjeti/OTC Web/jarvis/desktop-hands"
pip install -r requirements.txt
python desktop_hands.py
```
