#!/usr/bin/env python3
"""
System tray application for MTConnect Alarm Monitor.

Provides a system tray icon with Start/Stop polling control,
a Settings window (opens config_gui.py), and graceful shutdown.
Auto-starts polling on launch.

Usage:
    pythonw tray_app.py          # no console window
    python  tray_app.py          # with console (for debug)
"""

import importlib
import logging
import os
import subprocess
import sys
import threading
import time

def _ensure_deps():
    for pkg in ("pystray", "PIL"):
        try:
            __import__(pkg)
        except ImportError:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "pystray", "Pillow"],
                timeout=120,
            )
            break

_ensure_deps()

import pystray
from PIL import Image, ImageDraw

APP_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(APP_DIR, "alarm_poller.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("tray_app")


# ── Icon generation ────────────────────────────────────────────────────────

def _make_icon(color):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    dc = ImageDraw.Draw(img)
    dc.ellipse([(8, 8), (56, 56)], fill=color, outline=(40, 40, 40), width=2)
    return img

ICON_RUNNING = _make_icon((46, 204, 113))
ICON_STOPPED = _make_icon((170, 170, 170))


# ── Polling engine ─────────────────────────────────────────────────────────

class PollingEngine:
    def __init__(self):
        self._thread = None
        self._stop_event = threading.Event()
        self._running = False
        self._lock = threading.Lock()

    @property
    def running(self):
        return self._running

    def start(self):
        with self._lock:
            if self._running:
                return
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()
            self._running = True
            logger.info("Polling started")

    def stop(self):
        with self._lock:
            if not self._running:
                return
            self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=30)
        with self._lock:
            self._running = False
            self._thread = None
        logger.info("Polling stopped")

    def _run(self):
        for mod_name in ("config", "poller", "models", "notifier", "main"):
            if mod_name in sys.modules:
                importlib.reload(sys.modules[mod_name])

        from config import MTCONNECT_URL, MTCONNECT_DEVICE, POLL_INTERVAL_SECONDS
        try:
            from config import SUPPRESS_CODES
        except ImportError:
            SUPPRESS_CODES = []

        from poller import AlarmPoller
        from main import on_new_alarm, on_cleared_alarm

        logger.info(
            "Polling target=%s/%s interval=%ds",
            MTCONNECT_URL, MTCONNECT_DEVICE, POLL_INTERVAL_SECONDS,
        )

        poller = AlarmPoller()

        while not self._stop_event.is_set():
            try:
                for event in poller.poll():
                    alarm = event["alarm"]
                    if alarm.native_code and str(alarm.native_code) in [str(c) for c in SUPPRESS_CODES]:
                        continue
                    if event["type"] in ("new", "reactivated"):
                        on_new_alarm(alarm)
                    elif event["type"] == "cleared":
                        on_cleared_alarm(alarm)
            except Exception as exc:
                logger.error("Poll loop error: %s", exc)

            self._stop_event.wait(timeout=POLL_INTERVAL_SECONDS)


# ── Settings window ────────────────────────────────────────────────────────

_settings_window = None
_tk_root = None

def _open_settings(icon, item):
    global _settings_window, _tk_root

    import tkinter as tk

    if _tk_root is None:
        _tk_root = tk.Tk()
        _tk_root.withdraw()

    if _settings_window is not None and _settings_window.winfo_exists():
        _settings_window.lift()
        return

    from config_gui import ConfigGUI
    _settings_window = ConfigGUI(parent=_tk_root)


# ── Tray app ───────────────────────────────────────────────────────────────

engine = PollingEngine()


def _start_polling(icon, item):
    engine.start()
    icon.icon = ICON_RUNNING
    icon.title = "MTConnect Alarm Monitor — Polling"
    _refresh_menu(icon)


def _stop_polling(icon, item):
    engine.stop()
    icon.icon = ICON_STOPPED
    icon.title = "MTConnect Alarm Monitor — Stopped"
    _refresh_menu(icon)


def _quit(icon, item):
    engine.stop()
    icon.stop()
    if _tk_root:
        try:
            _tk_root.destroy()
        except Exception:
            pass


def _refresh_menu(icon):
    icon.menu = _build_menu()


def _build_menu():
    if engine.running:
        status_text = "Polling: Running"
        start_enabled = False
        stop_enabled = True
    else:
        status_text = "Polling: Stopped"
        start_enabled = True
        stop_enabled = False

    return pystray.Menu(
        pystray.MenuItem(status_text, lambda: None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Start Polling", _start_polling, enabled=start_enabled),
        pystray.MenuItem("Stop Polling", _stop_polling, enabled=stop_enabled),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Settings...", _open_settings),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Quit", _quit),
    )


def main():
    icon = pystray.Icon(
        name="mtconnect_alarm",
        icon=ICON_RUNNING,
        title="MTConnect Alarm Monitor — Polling",
        menu=_build_menu(),
    )

    engine.start()

    icon.run()


if __name__ == "__main__":
    main()