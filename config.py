# ── Alarm Priority Scheme ──────────────────────────────────────────────────────
# Okuma alarm levels mapped to NTFY priority (1=min, 5=max):
#   P   → 5  (most urgent, skull emoji)
#   A   → 5  (critical)
#   B   → 4
#   C   → 3
#   D   → 2  (lowest)
#   ERR → 4  (system errors)
# Unknown → 3

"""
Configuration for the Okuma MTConnect Alarm Poller.
All settings are defined here — no magic numbers elsewhere.
"""

# ── MTConnect Agent ──────────────────────────────────────────────────────────
# IP address (or hostname) of the MTConnect agent
MTCONNECT_HOST = "localhost"

# HTTP port the MTConnect agent listens on
MTCONNECT_PORT = 5000

# Base URL — constructed automatically, but can be overridden directly
MTCONNECT_URL = f"http://{MTCONNECT_HOST}:{MTCONNECT_PORT}"

# Device name as reported by the MTConnect agent (used to find the right XML element)
MTCONNECT_DEVICE = "CNC_7"

# Polling interval in SECONDS
POLL_INTERVAL_SECONDS = 10

# Request timeout in SECONDS (per poll request)
REQUEST_TIMEOUT_SECONDS = 15

# ── NTFY ───────────────────────────────────────────────────────────────────────
# NTFY topic (the part after the last / in your ntfy.sh URL)
NTFY_TOPIC = "cnc7"

# Full NTFY publish URL
NTFY_URL = "https://ntfy.tailf7384b.ts.net/cnc7"

# Optional: ntfy.sh server URL (used by the python-ntfy library)
NTFY_SERVER = "https://ntfy.tailf7384b.ts.net"

# Notification priority (1=min … 5=max)
NTFY_PRIORITY = 4

# Tags shown in the ntfy client (see https://ntfy.sh/docs/config/#tags)
# Common ones: warning, error, bell, gear, robot
NTFY_TAGS = ["warning", "bell"]

# Click action — open this URL when the notification is tapped (e.g. your NTFY dashboard)
NTFY_CLICK = "https://ntfy.tailf7384b.ts.net"

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE = "alarm_poller.log"
LOG_LEVEL = "INFO"   # DEBUG | INFO | WARNING | ERROR | CRITICAL
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
