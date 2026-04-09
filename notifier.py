"""
NTFY notification integration.

Sends push notifications to the configured ntfy.sh topic when alarms
fire or clear.  Supports both the python-ntfy library and a plain requests-
based fallback, so the module works even if the optional dependency isn't
installed.
"""

import logging
import sys
from typing import Optional, List

import requests

from config import (
    NTFY_URL,
    NTFY_SERVER,
    NTFY_TOPIC,
    NTFY_PRIORITY,
    NTFY_TAGS,
    NTFY_CLICK,
)
from models import Alarm

logger = logging.getLogger(__name__)

_ntfy_lib_available = False
try:
    import ntfy
    _ntfy_lib_available = True
except ImportError:
    logger.debug("python-ntfy not installed — using requests fallback")


# ── Notification messages ──────────────────────────────────────────────────────

def _format_title(event_type: str, alarm: Alarm) -> str:
    """
    Notification title — uses the alarm name (description) from native_message,
    matching what the operator sees on the machine screen.

    Falls back to the alarm code if the name can't be extracted.
    """
    msg = alarm.native_message or ""

    # native_message format: "1701 ALARM_A\nEmergency stop"
    # The description (alarm name) is on the second line, or use the code
    lines = msg.split("\n")
    if len(lines) >= 2:
        name = lines[1].strip()
    else:
        # Try: "1701 ALARM_A" — take everything after the code
        parts = msg.split(None, 1)
        name = parts[1].strip() if len(parts) > 1 else alarm.native_code

    # Fallback
    if not name:
        name = alarm.native_code

    return name


def _format_message(alarm: Alarm) -> str:
    """
    Body text matching the machine's alarm screen format::

        ALARM_A
        Emergency stop

    Parses the native_message text (e.g. '1701 ALARM_A') to extract
    just the alarm class (ALARM_A) and description.
    """
    msg = alarm.native_message or ""

    # native_message typically contains: "1701 ALARM_A" or "1701 ALARM_A\nSome description"
    # Extract everything after the alarm code (first token) for the description
    parts = msg.split(None, 1)
    if len(parts) > 1:
        description = parts[1].strip()
    else:
        description = msg

    # If the description still has a new line, take first line only
    description = description.split("\n")[0].strip()

    return description


# ── NTFY Sender ────────────────────────────────────────────────────────────────

class NtfyNotifier:
    """
    Sends NTFY notifications for alarm events.

    Uses the python-ntfy library when available, otherwise falls back to
    raw ``requests`` POST.  Both paths produce identical notifications.

    Parameters
    ----------
    url:
        Full ntfy publish URL (e.g. ``https://ntfy.sh/cnc1``).
    server:
        ntfy.sh server base (used only by the python-ntfy library).
    priority:
        1 (min) – 5 (max).
    tags:
        List of ntfy tag tokens shown in the client.
    click_url:
        URL opened when the notification is tapped.
    """

    def __init__(
        self,
        url: str = NTFY_URL,
        server: str = NTFY_SERVER,
        priority: int = NTFY_PRIORITY,
        tags: Optional[List[str]] = None,
        click_url: Optional[str] = None,
    ) -> None:
        self.url = url
        self.server = server
        self.priority = priority
        self.tags = tags or NTFY_TAGS
        self.click_url = click_url or NTFY_CLICK

        self._lib: Optional[object] = None
        if _ntfy_lib_available:
            try:
                self._lib = ntfy
            except Exception as exc:
                logger.warning("ntfy library present but failed to import: %s", exc)

    # ── Public API ─────────────────────────────────────────────────────────────

    def send(self, event_type: str, alarm: Alarm) -> bool:
        """
        Send a notification for an alarm state-change event.

        Returns True on success, False on failure.
        """
        title = _format_title(event_type, alarm)
        message = _format_message(alarm)

        logger.debug(
            "Sending NTFY notification — type=%s alarm=%s title=%r",
            event_type, alarm.key, title,
        )

        if self._lib is not None:
            return self._send_via_lib(title, message, alarm)
        else:
            return self._send_via_requests(title, message, alarm)

    # ── python-ntfy path ──────────────────────────────────────────────────────

    def _send_via_lib(self, title: str, message: str, alarm: Alarm) -> bool:
        """Publish via the python-ntfy library."""
        try:
            ntfy.Notifier(
                server=self.server,
                topic=self.NTFY_TOPIC,  # class-level attr fallback
            ).publish(
                title=title,
                message=message,
                tags=self.tags,
                priority=self.priority,
                click=self.click_url,
            )
            logger.info("NTFY notification sent (lib): %s", title)
            return True
        except Exception as exc:
            logger.error("NTFY lib publish failed: %s — falling back to requests", exc)
            self._lib = None          # stop trying the lib on next call
            return self._send_via_requests(title, message, alarm)

    @property
    def NTFY_TOPIC(self) -> str:
        """Backwards-compat: derive topic from the full URL."""
        return self.url.rstrip("/").rsplit("/", 1)[-1]

    # ── requests fallback path ─────────────────────────────────────────────────

    def _send_via_requests(self, title: str, message: str, alarm: Alarm) -> bool:
        """
        Publish directly to the ntfy.sh REST API using ``requests``.
        Includes retry logic with exponential backoff for transient failures.

        See: https://ntfy.sh/docs/publish/
        """
        headers = {
            "Content-Type": "text/plain; charset=utf-8",
            "Title": title,
            "Tags": ",".join(self.tags),
            "Priority": str(self.priority),
            "Click": self.click_url,
            "X-Custom": f"alarm:{alarm.key}",  # useful for ntfy filtering rules
        }

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                resp = requests.post(
                    self.url,
                    data=message,
                    headers=headers,
                    timeout=15,
                )
                resp.raise_for_status()
                logger.info("NTFY notification sent (requests): %s", title)
                return True

            except requests.exceptions.SSLError as exc:
                logger.warning(
                    "NTFY SSL error (attempt %d/%d): %s — retrying...",
                    attempt, max_retries, exc
                )
                if attempt < max_retries:
                    import time
                    time.sleep(2 ** attempt)  # exponential backoff: 2s, 4s
                else:
                    logger.error("NTFY SSL error exhausted retries: %s", exc)

            except requests.exceptions.ConnectionError as exc:
                logger.warning(
                    "NTFY connection error (attempt %d/%d): %s — retrying...",
                    attempt, max_retries, exc
                )
                if attempt < max_retries:
                    import time
                    time.sleep(2 ** attempt)
                else:
                    logger.error("NTFY connection error exhausted retries: %s", exc)

            except requests.exceptions.Timeout as exc:
                logger.warning(
                    "NTFY timeout (attempt %d/%d): %s — retrying...",
                    attempt, max_retries, exc
                )
                if attempt < max_retries:
                    import time
                    time.sleep(2 ** attempt)
                else:
                    logger.error("NTFY timeout exhausted retries: %s", exc)

            except requests.RequestException as exc:
                logger.error("NTFY request failed (non-retryable): %s", exc)
                return False

        return False


# ── Module-level convenience ───────────────────────────────────────────────────

_notifier: Optional[NtfyNotifier] = None


def get_notifier() -> NtfyNotifier:
    """Return the shared NtfyNotifier instance (lazy singleton)."""
    global _notifier
    if _notifier is None:
        _notifier = NtfyNotifier()
    return _notifier


def notify(event_type: str, alarm: Alarm) -> bool:
    """One-shot notify helper."""
    return get_notifier().send(event_type, alarm)
