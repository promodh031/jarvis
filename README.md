# Jarvis

One repo. Voice (Jarvis + Friday), rain overlay widget, visualizer, barehands board, desktop hands. Clone it, run setup, talk.

## New Mac

```bash
git clone https://github.com/promodh031/jarvis.git
cd jarvis
./setup.sh
```

`setup.sh` writes this clone's path to `~/Library/Application Support/jarvis/install_root`, builds the Python envs, writes machine-local config if missing, and copies `apps/Jarvis.app` to `/Applications`.

Then:

1. Put the company Console API key in Keychain as `claude-console-api` (never a file):
   `security add-generic-password -a "$USER" -s claude-console-api -w 'THE_KEY' -U`
2. Copy the vault to `~/jarvis-vault` (or `JARVIS_VAULT=/path ./setup.sh`). The vault is memory, not this repo.
3. Open **Jarvis** from Applications. First launch downloads Whisper + Kokoro (~1GB). Allow Microphone (and Accessibility if you use desktop hands).
4. **Hey Jarvis** / **Hey Friday**. Quit the dock icon to kill the whole stack.

`open -a Jarvis` fails on a raw Python shebang (`-10669`). The bundle's executable is a bash stub that runs `jarvis-host.py` with the overlay venv.

## Layout

- `backtalk/` — ears, mouth, dual-agent sessions
- `ai-visualizer/` — rain face + overlay
- `apps/Jarvis.app` — widget host; quit kills visualizer, voice, overlay
- `barehands/` — glass board
- `CLAUDE.md` — Friday boot file for Claude Code in this folder

Configs `backtalk/backtalk.json` and `ai-visualizer/ai-visualizer.json` are local (gitignored). Examples live in `examples/`.
