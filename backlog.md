---
status: active
project: jarvis
type: plan
---
# Backlog

Brain is live via company **Console API key** (not a personal Pro login). Key lives in macOS Keychain item `claude-console-api` — never in a file, never in a note. Desktop launcher `Talk to Jarvis.command` loads it on start. Usage meters the company API bill.

Voice is installed. Open mic + **Hey Jarvis** wake phrase. Right Option still interrupts.

## Voice

- [x] Claude Code can answer (verified 2026-09-02: `authMethod=api_key`, probe replied `pong`).
- [x] Install and wire **backtalk**: venv, speech models, `backtalk.json` (`agent_dir` = this repo, `name` = Jarvis, `extra_dirs` = vault, `barehands_state_dir` set). Open mic + `wake_phrase=hey jarvis` (fuzzy name match in `backtalk/main.py` `_gate_wake`). Right Option still interrupts. **Re-apply after `update.sh`** — this is a local patch.
- [x] Desktop shortcut: `Talk to Jarvis.command` (face + voice, Keychain export). `Update Jarvis.command` runs `backtalk/update.sh`.
- [x] Face bus: `ai-visualizer.json` `bus_dir` points at the backtalk folder. Face launcher no longer uses `--mock`.
- [ ] First spoken hello + hold-to-talk actually works (Input Monitoring for Terminal, Microphone permission on first run).
- [ ] Optional later: ElevenLabs, hands-free, resume-last-session, auto-approve. Do not flip these unasked.

## Not voice

- [ ] Vault profile interview — `VAULT-INDEX.md` is structurally complete with thin identity. Interview and fill Who I Am, work, people, priorities.
- [ ] Accessibility permission for Desktop Hands (System Settings → Privacy & Security → Accessibility) so pyautogui can move the mouse. Camera permission too, if the first launch prompts.
- [ ] Pick a default visualizer face if board is not the one you want (board / radial / rain / neural).
