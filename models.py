"""
Alarm data model.
Represents a single alarm/event received from the MTConnect /current endpoint.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import time


@dataclass
class Alarm:
    """
    Represents one alarm received from MTConnect.

    Fields come from the MTConnect "Events" data item with a nativeCode
    attribute, or from the "Alarms" data item type when the agent exposes
    them explicitly.  The exact XML structure depends on the Okuma MTConnect
    agent's implementation, so this class accepts whatever fields are present
    and degrades gracefully for missing attributes.
    """

    # ── Raw identity ────────────────────────────────────────────────────────
    data_item_id: str = ""           # MTConnect <DataItem> id attribute
    name:        str = ""           # MTConnect <DataItem> name attribute

    # ── Alarm identification ─────────────────────────────────────────────────
    native_code:   str = ""         # The alarm code, e.g. "E001", "1010"
    native_message: str = ""        # Human-readable alarm text

    # ── Severity / category (if provided) ───────────────────────────────────
    severity: str = ""              # e.g. "error", "warning", "critical"
    okuma_level: str = ""          # Okuma severity letter: A, B, C, D, P, ERR (from ALARM_X in native_message)
    state:    str = ""              # "active" | "cleared" | "available" | "unavailable"

    # ── Source ──────────────────────────────────────────────────────────────
    device_uuid: str = ""           # UUID of the device that raised the alarm
    component:  str = ""            # Component name, e.g. "CNC", "Spindle"
    timestamp:  Optional[datetime] = None  # When the alarm was raised

    # ── Computed ────────────────────────────────────────────────────────────
    # Internal sequence number used for ordering when no timestamp exists
    _seq: int = field(default_factory=lambda: int(time.time() * 1_000_000))

    # ── Convenience helpers ──────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        """True when the alarm state indicates it is currently active."""
        return self.state.lower() == "active"

    @property
    def key(self) -> str:
        """
        Unique identifier for this alarm within the running session.
        Uses native_code + component so that clearing a code on the same
        component counts as the same alarm clearing, while the same code
        on a different component is distinct.
        """
        return f"{self.native_code}@{self.component}".lower()

    def __repr__(self) -> str:
        state_str = "ACTIVE" if self.is_active else self.state.upper()
        return (
            f"<Alarm key={self.key!r} code={self.native_code!r} "
            f"msg={self.native_message!r:.40} state={state_str}>"
        )

    @classmethod
    def from_element(cls, element) -> "Alarm":
        """
        Parse an MTConnect <Events> or <Alarms> element into an Alarm instance.

        Expected XML fragment (MTConnect 1.x / 2.x variant)::

            <Component name="CNC">
              <DataItem id="d1" name="alarm" type="ALARM"
                        category="EVENT" nativeCode="E001"
                        nativeSeverity="ERROR" state="active"
                        qualifiers="[LOW]">Spindle Overload</DataItem>
            </Component>

        or the flat /current response structure::

            <Events>
              <Event id="d1" name="alarm" nativeCode="E001"
                    nativeMessage="Spindle Overload"
                    timestamp="2025-01-01T12:00:00Z" />
            </Events>
        """
        def attr(tag: str, default: str = "") -> str:
            return element.get(tag, default)

        raw_timestamp = attr("timestamp")
        ts = None
        if raw_timestamp:
            try:
                # ISO-8601 with Z suffix — strptime can't parse 'Z' directly
                ts = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        return cls(
            data_item_id=attr("id"),
            name=attr("name"),
            native_code=attr("nativeCode") or attr("code", ""),
            native_message=element.text.strip() if element.text else attr("message", ""),
            severity=attr("nativeSeverity") or attr("severity", ""),
            state=attr("state", "available"),
            device_uuid=attr("deviceUuid", ""),
            component=attr("component", "Unknown"),
            timestamp=ts,
        )
