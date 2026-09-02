# backtalk: talk to your Claude Code agent out loud.
# Copyright (C) 2026 Jared Rhodenizer
#
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Persist spoken and typed turns locally, one file per conversation.

Lives in ~/Library/Application Support/jarvis/conversations/ so it
survives repo updates. The visualizer reads the same folder.
"""
import json
import os
import re
import shutil
import threading
from datetime import datetime

from backtalk.config import CFG

_DIR = os.path.expanduser(
    "~/Library/Application Support/jarvis/conversations")
_OLD = os.path.join(CFG["signals_dir"], "logs", "history")
_lock = threading.Lock()
_cur: dict | None = None
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")
_migrated = False


def _now():
    return datetime.now().astimezone()


def _iso(dt=None):
    return (dt or _now()).strftime("%Y-%m-%dT%H:%M:%S")


def _path(sid: str) -> str:
    return os.path.join(_DIR, sid + ".json")


def _migrate():
    global _migrated
    if _migrated:
        return
    _migrated = True
    os.makedirs(_DIR, exist_ok=True)
    if not os.path.isdir(_OLD):
        return
    for name in os.listdir(_OLD):
        if not name.endswith(".json"):
            continue
        src = os.path.join(_OLD, name)
        dst = os.path.join(_DIR, name)
        if os.path.exists(dst):
            continue
        try:
            shutil.copy2(src, dst)
        except OSError:
            pass


def _write(doc: dict):
    _migrate()
    os.makedirs(_DIR, exist_ok=True)
    path = _path(doc["id"])
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def start(agent: str):
    """Open a new conversation for this wake. Closes any current one."""
    global _cur
    agent = (agent or "Jarvis").strip() or "Jarvis"
    with _lock:
        if _cur is not None:
            _cur["ended"] = _iso()
            try:
                _write(_cur)
            except OSError:
                pass
        ts = _now()
        sid = _SAFE.sub("-", ts.strftime("%Y%m%d-%H%M%S") + "-"
                        + agent.lower()).strip("-")
        _cur = {
            "id": sid,
            "agent": agent,
            "started": _iso(ts),
            "ended": None,
            "title": "",
            "preview": "",
            "turns": [],
        }
        try:
            _write(_cur)
        except OSError:
            pass


def ensure(agent: str):
    with _lock:
        if _cur is not None:
            return
    start(agent)


def add(role: str, text: str):
    text = " ".join((text or "").split())
    if not text:
        return
    with _lock:
        if _cur is None:
            return
        turns = _cur["turns"]
        if (turns and turns[-1]["role"] == role
                and role.lower() != "you"):
            turns[-1]["text"] = (turns[-1]["text"] + " " + text).strip()
            turns[-1]["ts"] = _iso()
        else:
            turns.append({"role": role, "text": text, "ts": _iso()})
        if role.lower() == "you" and not _cur.get("title"):
            _cur["title"] = text[:80]
            _cur["preview"] = text[:120]
        try:
            _write(_cur)
        except OSError:
            pass


def close():
    global _cur
    with _lock:
        if _cur is None:
            return
        _cur["ended"] = _iso()
        try:
            _write(_cur)
        except OSError:
            pass
        _cur = None
