"""
MTConnect polling logic.

Responsible for:
  1. Fetching the /current endpoint
  2. Parsing the XML response into Alarm objects
  3. Tracking which alarms are currently active vs cleared
  4. Emitting state-change events for the notifier to consume
"""

import logging
import re
import xml.etree.ElementTree as ET
from typing import Set, Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import (
    MTCONNECT_URL,
    MTCONNECT_DEVICE,
    REQUEST_TIMEOUT_SECONDS,
)
from models import Alarm

logger = logging.getLogger(__name__)


# ── AlarmPoller ────────────────────────────────────────────────────────────────

class AlarmPoller:
    """
    Polls the MTConnect /current endpoint, tracks alarm state, and yields
    state-change events.

    Usage::

        poller = AlarmPoller()
        for event in poller.poll():
            if event["type"] == "new":
                send_notification_new_alarm(event["alarm"])
            elif event["type"] == "cleared":
                send_notification_cleared_alarm(event["alarm"])
    """

    def __init__(self) -> None:
        self._url = f"{MTCONNECT_URL}/current"
        # active_alarms maps Alarm.key → Alarm instance
        self._active_alarms: Dict[str, Alarm] = {}

        # Track which device name/path the agent uses so we can find alarms
        self._device_name = MTCONNECT_DEVICE

        # Build a session with retry logic and forced HTTP/1.1 close to handle
        # agents that don't properly support keep-alive
        self._session = requests.Session()
        retry = Retry(total=2, backoff_factor=0.5, allowed_methods=["GET"])
        adapter = HTTPAdapter(max_retries=retry)
        self._session.mount("http://", adapter)
        self._session.headers.update({"Accept": "application/xml"})

    # ── Public API ────────────────────────────────────────────────────────────

    def poll(self):
        """
        Perform one poll of the MTConnect endpoint.
        Returns a generator of state-change dicts::

            {"type": "new",       "alarm": Alarm}
            {"type": "cleared",   "alarm": Alarm}
            {"type": "reactivated","alarm": Alarm}   # was cleared, now active again
        """
        try:
            alarms = self._fetch_and_parse()
        except requests.RequestException as exc:
            logger.error("Network error polling MTConnect: %s", exc)
            return
        except ET.ParseError as exc:
            logger.error("XML parse error from MTConnect response: %s", exc)
            return

        if alarms is None:
            logger.debug("No alarm data found in MTConnect response.")
            return

        # Find which alarms are currently active in this poll
        current_active: Set[str] = set()
        for alarm in alarms:
            if alarm.is_active:
                current_active.add(alarm.key)

        # Determine what changed
        previously_active = set(self._active_alarms.keys())

        # ── 1. Alarms that are new (active now, not in our tracked set) ──────
        for key in current_active - previously_active:
            alarm = next(a for a in alarms if a.key == key)
            self._active_alarms[key] = alarm
            logger.info("New alarm detected: %s", alarm)
            yield {"type": "new", "alarm": alarm}

        # ── 2. Alarms that have cleared (in tracked set, not in current) ──────
        for key in previously_active - current_active:
            cleared_alarm = self._active_alarms.pop(key)
            logger.info("Alarm cleared: %s", cleared_alarm)
            yield {"type": "cleared", "alarm": cleared_alarm}

        # ── 3. Reactivated alarms (key existed but alarm object changed) ──────
        for key in current_active & previously_active:
            new_alarm = next(a for a in alarms if a.key == key)
            old_alarm = self._active_alarms[key]
            if (new_alarm.native_message != old_alarm.native_message
                    or new_alarm.severity != old_alarm.severity):
                self._active_alarms[key] = new_alarm
                logger.info("Alarm reactivated/changed: %s", new_alarm)
                yield {"type": "reactivated", "alarm": new_alarm}

        # ── 4. Still-active alarms — update stored object (new timestamp, etc.) ─
        for key in current_active & previously_active:
            self._active_alarms[key] = next(a for a in alarms if a.key == key)

    @property
    def active_alarms(self) -> Dict[str, Alarm]:
        """Return the currently-tracked active alarm map."""
        return dict(self._active_alarms)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _fetch_and_parse(self) -> Optional[List[Alarm]]:
        """
        Hit the /current endpoint and return a list of Alarm objects.

        Returns None if no alarm data could be extracted (empty document,
        no alarm DataItems, etc.) so the caller can treat that as a no-op.
        """
        logger.debug("Fetching MTConnect /current from %s", self._url)
        response = self._session.get(
            self._url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"Accept": "application/xml", "Connection": "close"},
        )
        response.raise_for_status()
        xml_bytes = response.content

        alarms = self._parse_xml(xml_bytes)
        logger.debug("Parsed %d alarm element(s) from MTConnect XML", len(alarms))
        return alarms

    # -------------------------------------------------------------------------

    def _parse_xml(self, xml_bytes: bytes) -> List[Alarm]:
        """
        Parse MTConnect /current XML and return a list of Alarm objects.
        """

        try:
            tree = ET.fromstring(xml_bytes)
        except ET.ParseError as exc:
            logger.warning("XML parse failed: %s", exc)
            raise

        alarms: List[Alarm] = []
        alarms.extend(self._extract_from_tree(tree))

        return alarms

    def _extract_from_tree(self, root) -> List[Alarm]:
        """
        Extract alarm/condition data from an MTConnect Streams XML document.

        MTConnect uses <Condition> blocks inside ComponentStream.
        The four condition states are element names:
          <Normal/>        — healthy, no alarm
          <Warning/>       — caution state
          <Fault/>         — active alarm
          <Unavailable/>   — condition unknown

        We look for <Fault> and <Warning> elements specifically, plus any
        element that carries a nativeCode attribute.
        """
        alarms: List[Alarm] = []

        for elem in root.iter():
            # Strip namespace prefix if present
            tag_local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

            # Condition states: Fault and Warning are active alarm conditions
            is_condition_alarm = tag_local in ("Fault", "Warning")
            has_native_code = "nativeCode" in elem.attrib

            if is_condition_alarm or has_native_code:
                alarm = self._elem_to_alarm(elem, tag_local)
                if alarm is not None:
                    alarms.append(alarm)

        return alarms

    def _elem_to_alarm(self, elem, tag_local: str = "") -> Optional[Alarm]:
        """
        Convert a single XML element to an Alarm.

        For Condition elements (<Fault>, <Warning>), the element name
        determines the alarm state. For other elements, check 'state' attr.
        """
        try:
            native_code = (
                elem.get("nativeCode")
                or elem.get("code")
                or ""
            )
            if not native_code:
                return None

            # For Condition-type elements, Fault/Warning = always active
            if tag_local in ("Fault", "Warning"):
                state = "active"
                is_active = True
            elif tag_local == "Normal":
                state = "cleared"
                is_active = False
            else:
                state_attr = elem.get("state", "").lower()
                state = state_attr if state_attr else "available"
                is_active = state == "active"

            # Parse via the standard from_element, then override state
            alarm = Alarm.from_element(elem)
            alarm.state = state

            # Text content of the element is the nativeMessage (alarm description)
            if elem.text and elem.text.strip():
                alarm.native_message = elem.text.strip()

            # Parse severity letter from native_message text (e.g. "4708 ALARM_D DOOR" → "D")
            if alarm.native_message:
                m = re.search(r'ALARM_([A-DP])', alarm.native_message, re.IGNORECASE)
                if m:
                    alarm.okuma_level = m.group(1).upper()

            # Default component name
            if not alarm.component or alarm.component == "Unknown":
                alarm.component = "CNC"

            return alarm

        except Exception as exc:
            logger.warning("Failed to parse alarm element %s: %s", elem.tag, exc)
            return None


# ── One-shot convenience ───────────────────────────────────────────────────────

def fetch_current_alarms() -> List[Alarm]:
    """Fetch and return the current alarm list (one-shot, no state tracking)."""
    poller = AlarmPoller()
    alarms = []
    for event in poller.poll():
        alarms.append(event["alarm"])
    return alarms
