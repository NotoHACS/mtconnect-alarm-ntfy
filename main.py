#!/usr/bin/env python3
"""
MTConnect Alarm Poller — main entry point.

Polls the Okuma MTConnect agent for active alarms and sends Ntfy push
notifications when alarms appear, change, or clear. Runs continuously
in a loop.

Usage::

    python main.py              # production (polls forever)
    python main.py --dry-run    # log what would happen, don't notify
    python main.py --once      # poll once and exit (for testing)
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
import ssl

# Fix TLS for Windows 7 - force TLS 1.2+ and modern cipher suites
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

class TLSAdapter(HTTPAdapter):
    """Custom adapter to force TLS 1.2 on older systems like Windows 7."""
    def init_poolmanager(self, *args, **kwargs):
        # Use PROTOCOL_TLS (not CLIENT) to avoid check_hostname default
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        ctx.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

from config import (
    MTCONNECT_URL,
    MTCONNECT_DEVICE,
    POLL_INTERVAL_SECONDS,
    NTFY_URL,
    NTFY_PRIORITY,
    NTFY_TAGS,
)
from poller import AlarmPoller
from models import Alarm
from notifier import NtfyNotifier

# -- Logging -------------------------------------------------------------------

LOG_FILE = "alarm_poller.log"
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("poller_service")


# -- Alarm database lookup -----------------------------------------------------

_ALARM_DB = None


def _load_alarm_db() -> dict:
    """Load alarm database from alarm_db.json if present."""
    global _ALARM_DB
    if _ALARM_DB is None:
        db_path = os.path.join(os.path.dirname(__file__), "alarm_db.json")
        if os.path.exists(db_path):
            with open(db_path, "r", encoding="utf-8") as f:
                _ALARM_DB = json.load(f)
        else:
            _ALARM_DB = {}
    return _ALARM_DB


def _lookup_alarm(alarm_no: str) -> dict:
    """Look up alarm by AlarmNo. Returns {name, level, description} or empty dict."""
    db = _load_alarm_db()
    return db.get(str(alarm_no), {})


# -- NTFY via curl -------------------------------------------------------------

def _ntfy_send(title: str, message: str, tags: list = None, priority: int = NTFY_PRIORITY) -> bool:
    """Send a notification to the NTFY endpoint using the ``requests`` library.
    This avoids reliance on the external ``curl`` executable, which is often missing
    on Windows installations.
    """
    tags_str = ",".join(tags or NTFY_TAGS)
    try:
        import requests
        # Use custom TLS adapter for Windows 7 compatibility
        session = requests.Session()
        session.mount('https://', TLSAdapter())
        
        headers = {
            "Content-Type": "text/plain; charset=utf-8",
            "Title": title,
            "Tags": tags_str,
            "Priority": str(priority),
        }
        resp = session.post(NTFY_URL, data=message.encode("utf-8"), headers=headers, timeout=15, verify=False)
        resp.raise_for_status()
        logger.info("NTFY (requests) OK: %s", title)
        return True
    except Exception as exc:
        logger.error("NTFY (requests) failed: %s", exc)
        return False



# -- Notification formatting ----------------------------------------------------

def _format_title(alarm: Alarm) -> str:
    """Get alarm title — try DB lookup first, then native_message."""
    if alarm.native_code:
        db = _lookup_alarm(alarm.native_code)
        if db:
            return db.get("name", alarm.native_code)
    msg = alarm.native_message or ""
    lines = msg.split("\n")
    if len(lines) >= 2:
        return lines[1].strip()
    parts = msg.split(None, 1)
    return parts[1].strip() if len(parts) > 1 else (alarm.native_code or "ALARM")


def _format_body(alarm: Alarm) -> str:
    """Get alarm body text."""
    if alarm.native_code:
        db = _lookup_alarm(alarm.native_code)
        if db:
            desc = db.get("description", "")
            level = db.get("level", "")
            parts = [f"[Level {level}]"] if level else []
            parts.append(desc)
            return " ".join(parts)
    msg = alarm.native_message or ""
    lines = msg.split("\n")
    return lines[1].strip() if len(lines) > 1 else msg


# -- Alarm Priority Scheme ------------------------------------------------------
# Priority mapping: P (most urgent) ? 5, A ? 5, B ? 4, C ? 3, D ? 2, ERR ? 4, unknown ? 3
ALARM_PRIORITY = {
    "P":   5,
    "A":   5,
    "B":   4,
    "C":   3,
    "D":   2,
    "ERR": 4,
}
DEFAULT_PRIORITY = 3

# Tag mapping
ALARM_TAGS = {
    "P":   ["skull", "rotating_light", "bell"],     # most urgent
    "A":   ["rotating_light", "bell"],              # critical
    "B":   ["warning", "bell"],
    "C":   ["warning"],
    "D":   ["information_source"],                   # lowest
    "ERR": ["warning", "bell"],
}
DEFAULT_TAGS = ["warning", "bell"]
CLEARED_TAGS = ["white_check_mark"]


def _get_priority_and_tags(alarm: Alarm) -> tuple:
    """Return (priority, tags) based on Okuma alarm level.
    
    Level is determined by:
      1. okuma_level extracted from native_message text (ALARM_D, ALARM_P, etc.)
      2. Falls back to alarm_db.json level for codes like ERR that have no
         ALARM_X pattern in the text.
    """
    level = alarm.okuma_level.upper() if alarm.okuma_level else ""
    if not level and alarm.native_code:
        db = _lookup_alarm(alarm.native_code)
        level = db.get("level", "").upper()
    priority = ALARM_PRIORITY.get(level, DEFAULT_PRIORITY)
    tags = ALARM_TAGS.get(level, DEFAULT_TAGS)
    return priority, tags


# -- Event handlers ------------------------------------------------------------

def on_new_alarm(alarm: Alarm, dry_run: bool = False):
    title = _format_title(alarm)
    body = _format_body(alarm)
    priority, tags = _get_priority_and_tags(alarm)
    logger.info("NEW ALARM — %s: %s", alarm.native_code or "?", title)
    if not dry_run:
        _ntfy_send(title, body, tags=tags, priority=priority)


def on_cleared_alarm(alarm: Alarm, dry_run: bool = False):
    title = f"[CLEARED] {alarm.native_code or '?'}"
    body = _format_body(alarm)
    logger.info("CLEARED — %s", alarm.native_code or alarm.key)
    if not dry_run:
        _ntfy_send(title, body, tags=CLEARED_TAGS, priority=3)


# -- Main poll loop ------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Okuma MTConnect Alarm Poller")
    parser.add_argument("--once", action="store_true", help="Poll once and exit")
    parser.add_argument("--dry-run", action="store_true", help="Log actions without sending Ntfy")
    args = parser.parse_args()

    logger.info("Starting MTConnect Alarm Poller — target=%s/%s", MTCONNECT_URL, MTCONNECT_DEVICE)
    if args.dry_run:
        logger.info("DRY RUN — no notifications will be sent")

    poller = AlarmPoller()

    if args.once:
        for event in poller.poll():
            if event["type"] == "new":
                on_new_alarm(event["alarm"], dry_run=args.dry_run)
            elif event["type"] == "cleared":
                on_cleared_alarm(event["alarm"], dry_run=args.dry_run)
            elif event["type"] == "reactivated":
                on_new_alarm(event["alarm"], dry_run=args.dry_run)
        logger.info("Single poll complete.")
        return

    # Continuous polling loop
    while True:
        try:
            for event in poller.poll():
                if event["type"] == "new":
                    on_new_alarm(event["alarm"], dry_run=args.dry_run)
                elif event["type"] == "cleared":
                    on_cleared_alarm(event["alarm"], dry_run=args.dry_run)
                elif event["type"] == "reactivated":
                    on_new_alarm(event["alarm"], dry_run=args.dry_run)
        except Exception as exc:
            logger.error("Poll loop error: %s", exc)

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()