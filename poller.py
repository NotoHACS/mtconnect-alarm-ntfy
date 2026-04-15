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
import time
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

# Handle optional config values with defaults (backwards compatibility)
try:
    from config import ALARM_MIN_LIFETIME_SECONDS
except ImportError:
    ALARM_MIN_LIFETIME_SECONDS = 10.0  # Default: suppress alarms clearing faster than 10s

logger = logging.getLogger(__name__)


# ── Misload Detection Helper ────────────────────────────────────────────────────

class MisloadDetector:
    """
    Detects "blinking" alarms (on/off within seconds) and suppresses spam.

    - Tracks when alarms first appear
    - Suppresses "cleared" events for alarms that clear too quickly
    - Can identify misload conditions and send custom message instead
    """

    def __init__(self, min_lifetime: float = 10.0, misload_codes: Optional[Set[str]] = None):
        self._min_lifetime = min_lifetime  # seconds before cleared is reported
        self._misload_codes = misload_codes or set()  # alarm codes indicating misload
        self._alarm_first_seen: Dict[str, float] = {}  # key -> timestamp
        self._misload_detected: Dict[str, bool] = {}   # key -> is misload

    def on_alarm_active(self, alarm: Alarm) -> Optional[str]:
        """
        Called when alarm becomes active.
        Returns 'misload' if this is a misload condition, None otherwise.
        """
        import time
        now = time.time()

        # Track first seen time
        if alarm.key not in self._alarm_first_seen:
            self._alarm_first_seen[alarm.key] = now

        # Check if this is a misload alarm code
        if alarm.native_code in self._misload_codes:
            if alarm.key not in self._misload_detected:
                self._misload_detected[alarm.key] = True
                return "misload"

        return None

    def on_alarm_cleared(self, alarm: Alarm) -> tuple[bool, Optional[str]]:
        """
        Called when alarm clears.
        Returns (should_report, custom_message):
          - should_report: True if we should notify, False if suppressed
          - custom_message: Optional custom message (e.g., "MISLOAD CLEARED")
        """
        import time
        now = time.time()

        # Calculate how long alarm was active
        first_seen = self._alarm_first_seen.get(alarm.key, now)
        lifetime = now - first_seen

        # Check if this was a misload that is now cleared
        is_misload = self._misload_detected.pop(alarm.key, False)
        self._alarm_first_seen.pop(alarm.key, None)

        # Suppress if cleared too quickly
        if lifetime < self._min_lifetime:
            logger.info("Suppressing cleared alarm %s (lifetime %.1fs < %.1fs)",
                       alarm.key, lifetime, self._min_lifetime)
            return False, None

        # Was a misload that stayed active long enough
        if is_misload:
            return True, "MISLOAD CLEARED - Casting misloaded in workholding"

        return True, None

    def get_misload_message(self, alarm: Alarm) -> str:
        """Get the custom misload message."""
        return "🚨 MISLOAD DETECTED - Casting misloaded in workholding"


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
        self._alarm_first_seen: Dict[str, float] = {}  # key -> timestamp
        self._notified_active: Set[str] = set()  # keys already notified

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
        # Track new alarms silently, don't notify yet
        for key in current_active - previously_active:
            alarm = next(a for a in alarms if a.key == key)
            self._active_alarms[key] = alarm
            self._alarm_first_seen[key] = time.time()  # Track when first seen
            logger.info("Alarm detected (pending): %s", alarm)

        # Check pending alarms - notify if lifetime >= min_lifetime
        for key in list(self._active_alarms.keys()):
            if key in self._notified_active:
                continue
            first_seen = self._alarm_first_seen.get(key, 0)
            lifetime = time.time() - first_seen
            if lifetime >= ALARM_MIN_LIFETIME_SECONDS:
                self._notified_active.add(key)
                alarm = self._active_alarms[key]
                logger.info("Alarm active (notifying): %s", alarm)
                yield {"type": "new", "alarm": alarm}

        # ── 2. Alarms that have cleared (in tracked set, not in current) ──────
        for key in previously_active - current_active:
            cleared_alarm = self._active_alarms.pop(key)
            self._alarm_first_seen.pop(key, None)
            was_notified = key in self._notified_active
            self._notified_active.discard(key)
            
            if was_notified:
                logger.info("Alarm cleared: %s", cleared_alarm)
                yield {"type": "cleared", "alarm": cleared_alarm}
            else:
                logger.info("Alarm cleared silently (too fast): %s", cleared_alarm.key)

        # ── 3. Reactivated alarms (key existed but alarm object changed) ──────
        for key in current_active & previously_active:
            new_alarm = next(a for a in alarms if a.key == key)
            old_alarm = self._active_alarms[key]
            if (new_alarm.native_message != old_alarm.native_message
                    or new_alarm.severity != old_alarm.severity):
                self._active_alarms[key] = new_alarm
                logger.info("Alarm reactivated/changed: %s", new_alarm)
                yield {"type": "reactivated", "alarm": new_alarm}

        # ── 4. Still-active alarms - update stored object (new timestamp, etc.) ─
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
          <Normal/>        - healthy, no alarm
          <Warning/>       - caution state
          <Fault/>         - active alarm
          <Unavailable/>   - condition unknown

        We look for <Fault> and <Warning> elements specifically, plus any
        element that carries a nativeCode attribute.

        NEW: Also extracts VDOUT/VACUM data for Okuma user reserve codes to
        provide additional context about custom alarms.
        """
        alarms: List[Alarm] = []

        # First pass: extract VDOUT/VACUM data for correlation
        vdout_data = self._extract_vdout_data(root)
        vacum_data = self._extract_vacum_data(root)
        
        # Second pass: extract alarms
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

    def _extract_vdout_data(self, root) -> Dict[str, str]:
        """
        Extract VDOUT variable values from the XML.
        VDOUT[990-993] are Okuma user reserve code outputs.
        Returns dict: {"VDOUT990": "1234", "VDOUT991": "5678", ...}
        """
        vdout_data: Dict[str, str] = {}

        for elem in root.iter():
            tag_local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

            # Look for VDOUT data items or similar
            if tag_local in ("VDOUT", "Sample"):
                # Try to get the data item name
                data_item_id = elem.get("dataItemId", "")
                if "VDOUT" in data_item_id.upper():
                    # Extract the VDOUT number and value
                    match = re.search(r'VDOUT\[(\d+)\]', data_item_id, re.IGNORECASE)
                    if match:
                        vdout_num = match.group(1)
                        value = elem.get("value", "").strip()
                        if value and value != "UNAVAILABLE":
                            vdout_data[f"VDOUT{vdout_num}"] = value
                            logger.debug("Found VDOUT[%s] = %s", vdout_num, value)

        return vdout_data

    def _extract_vacum_data(self, root) -> Dict[str, str]:
        """
        Extract VACUM variable values (custom messages) from the XML.
        VACUM variables hold the 16-character custom alarm messages.
        Returns dict: {"VACUM1234": "CASTING MISLOAD", ...}
        """
        vacum_data: Dict[str, str] = {}

        for elem in root.iter():
            tag_local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

            # Look for VACUM data items or similar
            if tag_local in ("VACUM", "Sample", "Event"):
                data_item_id = elem.get("dataItemId", "")
                if "VACUM" in data_item_id.upper():
                    # Extract VACUM number and message
                    match = re.search(r'VACUM\[(\d+)\]', data_item_id, re.IGNORECASE)
                    if match:
                        vacum_num = match.group(1)
                        # Get value from text or attribute
                        value = elem.text.strip() if elem.text else elem.get("value", "")
                        if value and value != "UNAVAILABLE":
                            vacum_data[f"VACUM{vacum_num}"] = value
                            logger.debug("Found VACUM[%s] = '%s'", vacum_num, value)

        return vacum_data

    def _elem_to_alarm(self, elem, tag_local: str = "") -> Optional[Alarm]:
        """
        Convert a single XML element to an Alarm.

        For Condition-type elements (<Fault>, <Warning>), the element name
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

            # NEW: Enhance user reserve code alarms with custom message from alarm text
            # VDOUT values are masked (****) in XML, but custom message is in alarm text
            # Pattern 1: "User reserve code 1 'SELECT RESTART'; ..."
            # Pattern 2: "4209 User reserve code 1 SELECT RESTART" (new machine format)
            if "User reserve code" in alarm.native_message:
                # Try multiple patterns for extracting the custom message
                custom_msg = None
                
                # Pattern 1: Single quotes around message
                match = re.search(r"User reserve code \d+ '([^']+)'", alarm.native_message)
                if match:
                    custom_msg = match.group(1)
                
                # Pattern 2: Code followed by "User reserve code N <message>"
                # Format: "4209 User reserve code 1 SELECT RESTART" or similar
                if not custom_msg:
                    match = re.search(r"User reserve code\s+\d+\s+(.+?)(?:\s*;|\s*$)", alarm.native_message, re.IGNORECASE)
                    if match:
                        custom_msg = match.group(1).strip()
                
                # Pattern 3: Verbose format with code/severity prefix
                # Format: "4209 ALARM_D 1 SELECT RESTART; Date:2026/04/14 Time:13:51:49 4209 User reserve code"
                if not custom_msg:
                    match = re.search(r"\d+\s+ALARM_[A-Z]\s+\d+\s+(.+?);\s*Date:", alarm.native_message)
                    if match:
                        custom_msg = match.group(1).strip()
                
                if custom_msg:
                    alarm.native_message = f"[{alarm.native_code}] {custom_msg}"
                    logger.info("Enhanced user reserve alarm: %s", alarm.native_message)
                else:
                    # Fallback: just add brackets around code for consistent formatting
                    alarm.native_message = f"[{alarm.native_code}] {alarm.native_message}"
                    logger.info("Enhanced user reserve alarm (fallback): %s", alarm.native_message)

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
