# backtalk: talk to your Claude Code agent out loud.
# Copyright (C) 2026 Jared Rhodenizer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The signal bus — tiny files any other program can watch.

The voice line leaves notes; faces read the notes. That one dumb trick
is the whole integration surface:

  .voice_state        idle | listening | thinking | speaking
  .voice_waveform     JSON {ts, samples: [64 floats]} while audio plays
  .voice_loading_pid  exists while the thinking sound is playing
  .voice_heard        JSON {ts, text} — live transcript while you talk
  .voice_rate_limits  JSON {window: {utilization, resets_at}} — only
                      written when show_usage is on

Written to signals_dir (default: the repo root). Visualizers built on
this contract just work.

THE BAREHANDS SEAM: set barehands_state_dir in backtalk.json to a
barehands checkout's state/ folder and the same signals are mirrored in
its format (state/state as a bare word, state/wave.json normalized
0..1) — the on-screen ring becomes your agent's face with zero glue.

Every write is wrapped: the bus must never crash the voice line.
"""
import json
import os
import subprocess
import sys
import time

import numpy as np

from backtalk.config import CFG

_DIR = CFG["signals_dir"]
_STATE_FILE = os.path.join(_DIR, ".voice_state")
_WAVEFORM_FILE = os.path.join(_DIR, ".voice_waveform")
_LOADING_PID_FILE = os.path.join(_DIR, ".voice_loading_pid")
_DIRECTION_FILE = os.path.join(_DIR, ".voice_direction")
_REPLY_DONE_FILE = os.path.join(_DIR, ".voice_reply_done")
_RATE_LIMIT_FILE = os.path.join(_DIR, ".voice_rate_limits")
_AGENT_FILE = os.path.join(_DIR, ".voice_agent")
_HEARD_FILE = os.path.join(_DIR, ".voice_heard")
_MUTE_FILE = os.path.join(_DIR, ".voice_mute")
_TOKENS_FILE = os.path.join(_DIR, ".voice_tokens")

_hold_listening = False
_reply_open = False


def hold_listening(on: bool):
    """After TTS, park on listening (command session) instead of idle."""
    global _hold_listening
    _hold_listening = bool(on)


def reply_begin():
    """A reply is in flight — do not park the face on listening yet."""
    global _reply_open
    _reply_open = True


def reply_end():
    global _reply_open
    _reply_open = False


def park_after_speech():
    # Between sentences of the same reply the mouth queue is empty for
    # a beat. Command sessions used to snap back to LISTENING there,
    # so the HUD never showed THINKING / REPLYING. Stay on thinking
    # until the whole reply is done.
    if _reply_open:
        set_state("thinking")
        return
    set_state("listening" if _hold_listening else "idle")


_agent = {"name": "", "face": "rain", "model": ""}


def set_agent(name: str | None = None, face: str | None = None,
              model: str | None = None):
    """Tell the face who is on duty, and which model is live.
    None = leave that field as-is. Empty name = standby."""
    if name is not None:
        _agent["name"] = name
    if face is not None:
        _agent["face"] = face
    if model is not None:
        _agent["model"] = model
    try:
        with open(_AGENT_FILE, "w") as f:
            json.dump(_agent, f)
    except OSError:
        pass


def set_heard(text: str):
    """Live transcript of what the ears just decoded. Empty clears it."""
    try:
        with open(_HEARD_FILE, "w") as f:
            json.dump({"ts": time.time(), "text": str(text or "")}, f)
    except OSError:
        pass


def set_muted(on: bool):
    """True = hardware mic is closed. Overlay mute writes this."""
    try:
        with open(_MUTE_FILE, "w") as f:
            f.write("1" if on else "0")
    except OSError:
        pass


def muted() -> bool:
    try:
        return os.path.exists(_MUTE_FILE) and open(_MUTE_FILE).read().strip() == "1"
    except OSError:
        return False


def set_tokens(in_tokens: int = 0, out_tokens: int = 0):
    """This conversation's input/output token counts. Face reads them."""
    try:
        with open(_TOKENS_FILE, "w") as f:
            json.dump({"in": int(in_tokens or 0),
                       "out": int(out_tokens or 0),
                       "ts": time.time()}, f)
    except OSError:
        pass


_LAST_SAID: list[str] = []


def note_said(text: str):
    t = " ".join((text or "").lower().split())
    if t:
        _LAST_SAID.append(t)
        del _LAST_SAID[:-8]


def is_echo(text: str) -> bool:
    """True if this transcript is the mouth hearing itself."""
    t = " ".join("".join(ch if "a" <= ch <= "z" else " "
                         for ch in (text or "").lower()).split())
    if len(t) < 6:
        return False
    tw = set(t.split())
    if not tw:
        return False
    for s in _LAST_SAID:
        n = " ".join("".join(ch if "a" <= ch <= "z" else " "
                             for ch in s).split())
        if not n:
            continue
        if t in n or n in t:
            return True
        sw = set(n.split())
        if sw and len(tw & sw) / max(len(tw), 1) >= 0.72:
            return True
    return False

_BH = CFG.get("barehands_state_dir") or ""
_BH_STATE = os.path.join(_BH, "state") if _BH else ""
_BH_WAVE = os.path.join(_BH, "wave.json") if _BH else ""

_THINKING_SOUND = CFG.get("thinking_sound") or ""

_WAVEFORM_MIN_INTERVAL = 1.0 / 15   # ~15 writes/sec is plenty for 60fps reads
_last_waveform_write = 0.0
_static_proc: subprocess.Popen | None = None


def set_state(name: str):
    """Write the state. Never raises — the show must go on."""
    try:
        with open(_STATE_FILE, "w") as f:
            f.write(name)
    except OSError:
        pass
    if _BH_STATE:
        try:
            with open(_BH_STATE, "w") as f:
                f.write(name)
        except OSError:
            pass


def feed_waveform(pcm: np.ndarray):
    """Feed one PCM block (int16) — throttled, downsampled to 64 points.

    Also re-asserts state="speaking" on the same throttle: this only runs
    while the mouth is audibly playing, so the bus self-heals within
    ~70ms if a stray writer stomps the state mid-speech. (That self-heal
    rule once closed a bug that took a whole evening to find.)"""
    global _last_waveform_write
    if pcm.size == 0:
        return
    now = time.time()
    if now - _last_waveform_write < _WAVEFORM_MIN_INTERVAL:
        return
    _last_waveform_write = now
    try:
        idx = np.linspace(0, pcm.size - 1, 64).astype(int)
        raw = pcm[idx].astype(float)
        with open(_WAVEFORM_FILE, "w") as f:
            f.write(json.dumps({"ts": now, "samples": raw.tolist()}))
        if _BH_WAVE:
            norm = np.clip(np.abs(raw) / 32768.0, 0.0, 1.0)
            with open(_BH_WAVE, "w") as f:
                f.write(json.dumps({"ts": now, "samples": norm.tolist()}))
    except (OSError, ValueError):
        pass
    set_state("speaking")


def direction(items):
    """Stage directions the agent wrote into its reply, published at the
    moment the audio carrying them starts playing.

    Your agent can emit `<<anything>>` inline and backtalk will never speak
    it. What the tag MEANS is deliberately not backtalk's business: it
    publishes the raw strings and something else decides. That is the whole
    reason this is a file and not a plugin API.

    The timing is the point, and it is the one part a watcher cannot do for
    itself: these fire when the sentence becomes AUDIBLE, not when the model
    generated it. A screen cue lands on the spoken word instead of seconds
    early. Never raises."""
    if not items:
        return
    try:
        with open(_DIRECTION_FILE, "w") as f:
            f.write(json.dumps({"ts": time.time(), "directions": list(items)}))
    except OSError:
        pass


def reply_done():
    """One reply has finished speaking and its audio has fully drained.

    Distinct from the state going idle, which also happens in the gaps
    BETWEEN sentences of the same reply. Anything waiting for the agent to
    genuinely stop talking wants this rather than a state flicker. Never
    raises."""
    try:
        with open(_REPLY_DONE_FILE, "w") as f:
            f.write(json.dumps({"ts": time.time()}))
    except OSError:
        pass


_rate_limits: dict = {}


def set_rate_limit(window: str, utilization, resets_at):
    """One usage window's reading — how much of the plan is spent.

    Merged rather than replaced, because the reading arrives one window
    at a time and a face wants to draw both at once. `utilization` is a
    0..1 fraction (or None when the window has not reported a number
    yet, which is a real state and not an error); `resets_at` is a unix
    epoch.

    NOTHING CALLS THIS UNLESS show_usage IS ON. That is a privacy
    default, not a performance one: this is the account holder's own
    spend, and it renders on a face that may well be pointed at a
    camera. It never appears without being asked for. (Community fix,
    ai-visualizer issue #1.)

    Never raises."""
    if not window:
        return
    _rate_limits[window] = {"utilization": utilization,
                            "resets_at": resets_at}
    try:
        with open(_RATE_LIMIT_FILE, "w") as f:
            f.write(json.dumps(_rate_limits))
    except OSError:
        pass


def _player_cmd(path: str) -> list[str] | None:
    if sys.platform == "darwin":
        return ["afplay", "-v", "0.35", path]
    for cand in ("ffplay", "aplay", "paplay"):
        from shutil import which
        if which(cand):
            if cand == "ffplay":
                return ["ffplay", "-nodisp", "-autoexit", "-loglevel",
                        "quiet", "-volume", "35", path]
            return [cand, path]
    return None


def static_start():
    """Optional thinking sound — plays while the brain works."""
    global _static_proc
    if not _THINKING_SOUND or not os.path.exists(_THINKING_SOUND):
        return
    static_stop()
    cmd = _player_cmd(_THINKING_SOUND)
    if not cmd:
        return
    try:
        _static_proc = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with open(_LOADING_PID_FILE, "w") as f:
            f.write(str(_static_proc.pid))
    except OSError:
        _static_proc = None


def static_stop():
    global _static_proc
    if _static_proc is not None:
        try:
            _static_proc.terminate()
        except OSError:
            pass
        _static_proc = None
    try:
        os.remove(_LOADING_PID_FILE)
    except OSError:
        pass
