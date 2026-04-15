# ═══════════════════════════════════════════════════════════════════════════════
# Machine-Specific Configuration for CNC12
# ═══════════════════════════════════════════════════════════════════════════════
#
# HOW TO USE THIS FILE:
#   1. Copy this file to config_local.py in the same folder
#   2. Edit config_local.py with your machine-specific settings
#   3. config_local.py is NOT tracked by git (see .gitignore)
#   4. This file OVERRIDES config_defaults.py
#
# DEPLOYMENT NOTES:
#   - Both CNC12 and CNC13 can run the SAME codebase
#   - Only the config_local.py file differs between machines
#   - Keep this example file in git for reference, but config_local.py is local
#
# ═══════════════════════════════════════════════════════════════════════════════

# ── MTConnect Agent Settings ───────────────────────────────────────────────────
# CNC12 typically uses standard port 5000
MTCONNECT_HOST = "10.0.1.100"  # <-- Change to your CNC12 IP
MTCONNECT_PORT = 5000
MTCONNECT_URL = f"http://{MTCONNECT_HOST}:{MTCONNECT_PORT}"

# Device name (optional - only needed if multiple devices per IP)
MTCONNECT_DEVICE = ""  # Empty = accept all devices

# Polling intervals
POLL_INTERVAL_SECONDS = 10
REQUEST_TIMEOUT_SECONDS = 15

# ── NTFY Notification Settings ─────────────────────────────────────────────────
# Use a unique topic for CNC12 to distinguish from CNC13
NTFY_TOPIC = "cnc12"
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"
NTFY_SERVER = "https://ntfy.sh"

# Priority: 1=min, 3=default, 5=max
NTFY_PRIORITY = 4

# Tags shown as emoji icons in ntfy
NTFY_TAGS = ["warning", "bell"]

# Click action when notification is tapped
NTFY_CLICK = "https://ntfy.sh"

# ── Logging Settings ───────────────────────────────────────────────────────────
LOG_FILE = "cnc12_alarm_poller.log"
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ── Misload Detection (Optional) ───────────────────────────────────────────────
# Minimum time an alarm must be active before reporting "cleared" (seconds)
# Alarms that clear faster than this are suppressed (spam prevention)
ALARM_MIN_LIFETIME_SECONDS = 10.0

# MISLOAD ALARM CODES
# Uncomment and set these to detect misload conditions
# When these alarms blink on/off, sends "MISLOAD DETECTED" instead of spam
#
# Example Okuma alarm codes for misload detection:
#   "2395" - Tool change error
#   "4209" - User reserve code (custom misload alarm)
#
# MISLOAD_ALARM_CODES = ["2395", "4209"]
MISLOAD_ALARM_CODES = []

# ═══════════════════════════════════════════════════════════════════════════════
# END OF CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════
