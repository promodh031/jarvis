#!/usr/bin/env python3
"""Jarvis.app — widget only. Quit the dock icon to kill the whole stack."""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import urllib.request

SUPPORT = os.path.expanduser("~/Library/Application Support/jarvis")
MARKER = os.path.join(SUPPORT, "install_root")
LOG = "/tmp/jarvis-app.log"

_kids: list[subprocess.Popen] = []


def install_root() -> str:
    env = (os.environ.get("JARVIS_ROOT") or "").strip()
    if env and os.path.isdir(env):
        return os.path.abspath(env)
    try:
        p = open(MARKER, encoding="utf-8").read().strip()
        if p and os.path.isdir(p):
            return os.path.abspath(p)
    except OSError:
        pass
    # Running from the copy inside the repo: .../apps/Jarvis.app/Contents/MacOS/
    here = os.path.abspath(os.path.dirname(__file__))
    cand = os.path.abspath(os.path.join(here, "..", "..", "..", ".."))
    if os.path.isdir(os.path.join(cand, "backtalk")):
        return cand
    return os.path.expanduser("~/Projects/Me/jarvis")


ROOT = install_root()
VIZ = os.path.join(ROOT, "ai-visualizer")
BT = os.path.join(ROOT, "backtalk")
STATE = "http://127.0.0.1:8790/state"


def log(msg: str) -> None:
    line = msg.rstrip() + "\n"
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass
    sys.stderr.write(line)


def env() -> dict:
    e = os.environ.copy()
    e["PATH"] = os.path.expanduser("~/.local/bin") + ":/opt/homebrew/bin:/usr/local/bin:" + e.get("PATH", "")
    e["JARVIS_ROOT"] = ROOT
    try:
        key = subprocess.check_output(
            ["security", "find-generic-password", "-a", os.environ.get("USER", ""),
             "-s", "claude-console-api", "-w"],
            text=True).strip()
    except subprocess.CalledProcessError:
        key = ""
    if key:
        e["ANTHROPIC_API_KEY"] = key
    return e


def kill_stack() -> None:
    for p in list(_kids):
        try:
            p.terminate()
        except OSError:
            pass
    for p in list(_kids):
        try:
            p.wait(timeout=2)
        except Exception:
            try:
                p.kill()
            except OSError:
                pass
    _kids.clear()
    subprocess.call(["pkill", "-f", "backtalk[.]main"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.call(["pkill", "-f", "ai-visualizer/overlay.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.call(["pkill", "-f", "Python overlay.py"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        out = subprocess.check_output(["lsof", "-tiTCP:8790", "-sTCP:LISTEN"], text=True)
        for pid in out.split():
            subprocess.call(["kill", pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        pass
    log("[jarvis-app] stack down")


def wait_viz(timeout=20) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(STATE, timeout=1) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.25)
    return False


def spawn(cmd, cwd=None) -> subprocess.Popen:
    lf = open(LOG, "a", encoding="utf-8")
    p = subprocess.Popen(cmd, cwd=cwd, env=env(), stdout=lf, stderr=lf,
                         start_new_session=True)
    _kids.append(p)
    return p


def start_stack() -> None:
    kill_stack()
    if not os.path.isdir(os.path.join(BT, "backtalk")):
        log(f"[jarvis-app] install root looks wrong: {ROOT}")
        return
    if not env().get("ANTHROPIC_API_KEY"):
        log("[jarvis-app] Keychain item claude-console-api is missing")
        return
    log("[jarvis-app] starting (widget only, no browser)")
    spawn(["python3", os.path.join(VIZ, "server.py"), "--no-open"], cwd=VIZ)
    if not wait_viz():
        log("[jarvis-app] visualizer did not come up on 8790")
        kill_stack()
        return
    spawn(["bash", os.path.join(BT, "run.sh")], cwd=BT)
    ov = os.path.join(VIZ, ".overlay-venv", "bin", "python")
    if not os.path.isfile(ov):
        ov = "python3"
    spawn([ov, os.path.join(VIZ, "overlay.py")], cwd=VIZ)
    log("[jarvis-app] widget up")


def main() -> None:
    os.chdir(ROOT)
    try:
        from AppKit import (
            NSApplication, NSApplicationActivationPolicyRegular, NSObject,
        )
        from PyObjCTools import AppHelper
    except ImportError:
        log("[jarvis-app] AppKit missing — running headless until SIGTERM")
        start_stack()

        def _die(signum, frame):
            kill_stack()
            sys.exit(0)

        signal.signal(signal.SIGTERM, _die)
        signal.signal(signal.SIGINT, _die)
        try:
            while True:
                time.sleep(1)
                if _kids and all(p.poll() is not None for p in _kids):
                    break
        finally:
            kill_stack()
        return

    class Delegate(NSObject):
        def applicationDidFinishLaunching_(self, _note):
            start_stack()

        def applicationShouldTerminate_(self, _sender):
            kill_stack()
            return True

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
    delegate = Delegate.alloc().init()
    app.setDelegate_(delegate)
    AppHelper.runEventLoop()


if __name__ == "__main__":
    main()
