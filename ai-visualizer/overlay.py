#!/usr/bin/env python3
"""Always-on-top matrix status overlay (Siri-style).

Hides while standby/idle; comes back on listening / thinking / speaking.
"""
import json
import sys
import threading
import time
import urllib.request

URL = "http://127.0.0.1:8790/faces/rain/?overlay=1&v=phase2"
WIDTH, HEIGHT, MARGIN = 520, 300, 22
STATE = "http://127.0.0.1:8790/state"


def wait_server(timeout=20):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(STATE, timeout=1) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def corner_xy():
    try:
        from AppKit import NSScreen
        vf = NSScreen.mainScreen().visibleFrame()
        frame = NSScreen.mainScreen().frame()
        x = int(vf.origin.x + vf.size.width - WIDTH - MARGIN)
        y = int(frame.size.height - (vf.origin.y + vf.size.height) + MARGIN)
        return x, y
    except Exception:
        return None, None


def read_state():
    try:
        with urllib.request.urlopen(STATE, timeout=1) as r:
            return json.loads(r.read().decode())
    except Exception:
        return None


def want_visible(st):
    if not st:
        return False
    # Muted stays on screen so you can unmute. Otherwise the widget
    # vanishes while idle with no agent on duty.
    if st.get("muted"):
        return True
    agent = str(st.get("name") or "").strip()
    phase = str(st.get("state") or "idle")
    return bool(agent) or phase in ("listening", "thinking", "speaking")


def main():
    if not wait_server():
        print("[overlay] visualizer is not up on 8790 — giving up", flush=True)
        sys.exit(1)
    try:
        from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
        NSApplication.sharedApplication().setActivationPolicy_(
            NSApplicationActivationPolicyAccessory)
    except Exception:
        pass
    import webview
    x, y = corner_xy()
    kw = dict(width=WIDTH, height=HEIGHT, frameless=True, on_top=True,
              transparent=True, background_color="#000000",
              hidden=not want_visible(read_state()))
    if x is not None:
        kw["x"] = x
        kw["y"] = y
    window = webview.create_window("Jarvis", URL, **kw)
    shown = {"on": not kw.get("hidden")}
    glassed = {"on": False}

    def on_gui(fn):
        try:
            from PyObjCTools.AppHelper import callAfter
            callAfter(fn)
        except Exception:
            try:
                fn()
            except Exception:
                pass

    def glass():
        try:
            from AppKit import NSColor
            from webview.platforms.cocoa import BrowserView
            clear = NSColor.clearColor()
            for view in BrowserView.instances.values():
                view.window.setOpaque_(False)
                view.window.setHasShadow_(False)
                view.window.setBackgroundColor_(clear)
                try:
                    view.webview.setUnderPageBackgroundColor_(clear)
                except Exception:
                    pass
        except Exception:
            pass

    def poll():
        idle_since = None
        while True:
            time.sleep(0.35)
            if not glassed["on"]:
                glassed["on"] = True
                on_gui(glass)
            vis = want_visible(read_state())
            now = time.time()
            if vis:
                idle_since = None
                if not shown["on"]:
                    shown["on"] = True
                    on_gui(window.show)
            else:
                if idle_since is None:
                    idle_since = now
                if shown["on"] and now - idle_since >= 0.8:
                    shown["on"] = False
                    on_gui(window.hide)

    threading.Thread(target=poll, daemon=True).start()
    print("[overlay] matrix HUD up", flush=True)
    webview.start()


if __name__ == "__main__":
    main()
