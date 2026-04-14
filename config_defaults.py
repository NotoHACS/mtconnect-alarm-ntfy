# Configuration defaults for MTConnect Alarm Monitor
# These are fallback values - machine-specific config goes in config_local.py

# ── MTConnect Agent ──────────────────────────────────────────────────────────
MTCONNECT_HOST = "localhost"
MTCONNECT_PORT = 5000
MTCONNECT_URL = f"http://{MTCONNECT_HOST}:{MTCONNECT_PORT}"

# Device name for filtering (optional - leave empty if only 1 device per IP)
# Set this to the <Device> name from your MTConnect XML if multiple devices share an IP
MTCONNECT_DEVICE = ""  # Empty = accept all devices (single CNC per IP)

POLL_INTERVAL_SECONDS = 10
REQUEST_TIMEOUT_SECONDS = 15

# ── NTFY ───────────────────────────────────────────────────────────────────────
NTFY_TOPIC = "cnc"
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"
NTFY_SERVER = "https://ntfy.sh"
NTFY_PRIORITY = 4
NTFY_TAGS = ["warning", "bell"]
NTFY_CLICK = "https://ntfy.sh"

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE = "alarm_poller.log"
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ── Misload Detection ─────────────────────────────────────────────────────────
# Minimum time an alarm must be active before reporting "cleared" (seconds)
# Alarms that clear faster than this are suppressed (spam prevention)
ALARM_MIN_LIFETIME_SECONDS = 10.0

# Alarm codes that indicate a misload condition
# When these alarms blink on/off, send "MISLOAD DETECTED" instead of spam
# Example: ["2395", "4209"]  # <-- Set this in config_local.py
MISLOAD_ALARM_CODES = []
