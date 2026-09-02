---
status: active
project: jarvis
type: plan
---
# Backlog

Brain is live via company **Console API key** (not a personal Pro login). Key lives in macOS Keychain item `claude-console-api` — never in a file, never in a note. Desktop launcher `Talk to Jarvis.command` loads it on start. Usage meters the company API bill.

Voice is installed. Open mic + **Hey Jarvis** wake phrase. Right Option still interrupts.

## Voice

- [ ] First spoken hello + hold-to-talk actually works (Input Monitoring for Terminal, Microphone permission on first run).
- [ ] Optional later: ElevenLabs, hands-free, resume-last-session, auto-approve. Do not flip these unasked.
- [ ] Remove ElevenLabs — it's the only opt-in external TTS path (off by default, falls back to local Kokoro); tear it out of `mouth.py` and `backtalk.json` so voice output is fully local.
- [x] Mute / unmute control for the app. Unmute opens the mic (starts capture); mute fully closes it (stops capture at the device level, not just ignoring audio) — no hot mic listening in the background while muted. Overlay MIC ON/OFF writes `.voice_mute`; backtalk will not open PortAudio while muted.

## Always-on-top status overlay (Siri-style)

- [x] Floating matrix HUD via PyWebview, always-on-top (`NSStatusWindowLevel`), rain face in overlay mode. Same live state as the full face: listening / thinking / speaking, agent color, model, live transcript. HISTORY opens the conversation list in the browser. Launcher starts it with voice; quitting the voice line kills the overlay.
- [x] `ai-visualizer` already renders this exact state (reads `.voice_state` off backtalk's signal bus, already wired via `bus_dir`, already running on port 8790) — it's a browser tab today, not an always-on-top overlay.
- [x] Gap to close: wrap/host the visualizer face in a native or borderless always-on-top window (not just a browser tab) so it behaves like the Siri overlay. Approach chosen: PyWebview.
- [x] Handoff prompt for implementation: Build an always-on-top status overlay for Jarvis using PyWebview. The visualizer already runs locally on port 8790 and renders live voice state (listening / thinking / speaking) pulled straight off backtalk's signal bus. Right now it only shows up as a browser tab. Replace that with a PyWebview window loading that same local page, but make it frameless, no title bar, sized like a small pill or bar instead of a full window, and pinned to a corner of the screen. Once the window's created, use PyObjC to grab the NSWindow and set its level to floating, so it sits above every other window, fullscreen apps included, same as Siri's popup. Wire it into the existing launcher so it starts alongside backtalk and the visualizer server, and make sure quitting Jarvis actually closes it too, no zombie windows left behind. Don't touch the existing voice state logic in backtalk or the visualizer's rendering code — this is just a new host window around what's already there.

## Claude connection: SSO vs API key

Current state (verified 2026-09-02): connected via **Console API key**, not SSO. Key lives in macOS Keychain item `claude-console-api`, exported as `ANTHROPIC_API_KEY` env var, injected by `Talk to Jarvis.command` at launch. Every token is metered onto the company API bill.

- [ ] **Option A — API key (current).** Company Console API key in Keychain (`claude-console-api`) → exported as `ANTHROPIC_API_KEY` → picked up automatically by Claude Code on start. No login flow, no browser, no user session — just an env var. Usage bills per-token against the company's Console account. Works headless, survives reboots without re-auth.
- [ ] **Option B — SSO (personal Pro/Max login).** Run `claude login` (or `/login` inside a session) to launch a browser OAuth flow against a personal Anthropic account (Claude Pro or Max). No API key stored anywhere; auth token lives in Claude Code's own credential store instead of Keychain. Usage draws down the personal subscription's included quota instead of metered API billing. Requires re-auth if the session/token expires, and needs a one-time interactive browser login (not fully headless).
- [ ] Decision not yet made — pick one before wiring it permanently into the launcher.

## Conversation history

- [x] Persist full transcript of every conversation (voice and typed) as JSON in `~/Library/Application Support/jarvis/conversations/`. Overlay HISTORY opens the browser ChatGPT-style list+thread; HISTORY on the rain face opens the same UI in-page. Overlay auto-hides while idle.
- [ ] Save conversations in Firebase.

## Overlay polish (queue — one at a time, test before the next)

- [x] No borders on the mic/history icons or any HUD boxes.
- [x] Mic must not pick up speaker / TTS output (echo). Only the person's voice.
- [x] App in `/Applications`: click opens the widget only (no rain browser tab). Closing the app kills the whole stack. `/Applications/Jarvis.app` — source in `apps/Jarvis.app`.
- [ ] Interrupt (barge-in): while Jarvis or Friday is speaking, talk over them — they stop and that utterance is the next command. Ignore speaker echo and room noise. Code is in `backtalk/backtalk/ears.py` + command-session mic in `main.py`; prove it on a clean launch.

## Not voice

- [ ] Vault profile interview — `VAULT-INDEX.md` is structurally complete with thin identity. Interview and fill Who I Am, work, people, priorities.
- [ ] Accessibility permission for Desktop Hands (System Settings → Privacy & Security → Accessibility) so pyautogui can move the mouse. Camera permission too, if the first launch prompts.
- [ ] Pick a default visualizer face if board is not the one you want (board / radial / rain / neural).
