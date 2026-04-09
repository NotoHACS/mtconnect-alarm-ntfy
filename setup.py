#!/usr/bin/env python3
"""
Interactive setup wizard for MTConnect Alarm Monitor.

Guides the user through configuration — no need to edit files manually.
"""

import os
import sys
import re


def print_header(text):
    print(f"\n{'=' * 50}")
    print(f"  {text}")
    print(f"{'=' * 50}\n")


def print_section(text):
    print(f"\n{text}")
    print("-" * 40)


def ask(prompt, default=None, validator=None, help_text=None):
    """Ask for input with optional default and validation."""
    while True:
        if default:
            full_prompt = f"{prompt} [{default}]: "
        else:
            full_prompt = f"{prompt}: "

        answer = input(full_prompt).strip()

        if not answer and default:
            answer = default

        if not answer:
            print("  ⚠️  This field is required.")
            continue

        if validator and not validator(answer):
            if help_text:
                print(f"  ⚠️  {help_text}")
            continue

        return answer


def ask_yes_no(prompt, default="yes"):
    """Ask a yes/no question."""
    while True:
        suffix = " [Y/n]" if default.lower() == "yes" else " [y/N]"
        answer = input(f"{prompt}{suffix}: ").strip().lower()

        if not answer:
            answer = default.lower()

        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False

        print("  ⚠️  Please enter 'yes' or 'no'")


def validate_ip_or_hostname(value):
    """Basic validation for IP or hostname."""
    if not value:
        return False
    # Allow simple hostnames, IPs, localhost
    return re.match(r'^[\w\-\.]+$', value) is not None


def validate_port(value):
    """Validate port number."""
    try:
        port = int(value)
        return 1 <= port <= 65535
    except ValueError:
        return False


def validate_topic(value):
    """Validate ntfy topic name."""
    if not value:
        return False
    # ntfy topics: alphanumeric, dashes, underscores
    return re.match(r'^[a-zA-Z0-9_-]+$', value) is not None and len(value) >= 3


def generate_random_topic():
    """Generate a random topic name."""
    import random
    import string
    adjectives = ["red", "blue", "fast", "cool", "dark", "bright", "quiet", "loud"]
    nouns = ["cnc", "mill", "lathe", "okuma", "alarm", "machine", "shop"]
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"{random.choice(adjectives)}-{random.choice(nouns)}-{suffix}"


def main():
    print_header("MTConnect Alarm Monitor - Setup")
    print("This wizard will help you configure the alarm monitor.")
    print("You'll need:")
    print("  • Your CNC machine's IP address or hostname")
    print("  • A unique ntfy.sh topic name (for phone notifications)")
    print()

    if not ask_yes_no("Ready to start?", default="yes"):
        print("\nSetup cancelled. You can run this again anytime with: python setup.py")
        sys.exit(0)

    # ── MTConnect Agent Configuration ───────────────────────────────────────
    print_section("Step 1: MTConnect Agent Configuration")
    print("The MTConnect agent runs on your CNC or a connected PC.")
    print("It provides alarm data over HTTP.")
    print()

    mtconnect_host = ask(
        "Enter the MTConnect agent IP or hostname",
        default="localhost",
        validator=validate_ip_or_hostname,
        help_text="Use an IP like 192.168.1.100 or a hostname like 'cnc-machine'"
    )

    mtconnect_port = ask(
        "Enter the MTConnect agent port",
        default="5000",
        validator=validate_port,
        help_text="Port must be a number between 1 and 65535"
    )

    mtconnect_device = ask(
        "Enter the MTConnect device name",
        default="CNC_7",
        help_text="This is the device identifier in the MTConnect XML"
    )

    # ── NTFY Configuration ───────────────────────────────────────────────────
    print_section("Step 2: Notification Setup (ntfy.sh)")
    print("ntfy.sh sends free push notifications to your phone.")
    print("Pick a unique topic name that others won't guess.")
    print()

    suggested_topic = generate_random_topic()
    print(f"Suggested topic: {suggested_topic}")
    print()

    ntfy_topic = ask(
        "Enter your ntfy.sh topic name",
        default=suggested_topic,
        validator=validate_topic,
        help_text="Topic must be 3+ characters, letters/numbers/dashes/underscores only"
    )

    print()
    print("📱 To receive notifications:")
    print(f"   1. Install the ntfy app from F-Droid or Google Play")
    print(f"   2. Subscribe to topic: {ntfy_topic}")
    print(f"   3. Or visit: https://ntfy.sh/{ntfy_topic}")
    print()

    if ask_yes_no("Would you like to test notifications now?", default="yes"):
        print("\n  Sending test notification...")
        try:
            import requests
            resp = requests.post(
                f"https://ntfy.sh/{ntfy_topic}",
                data="MTConnect Alarm Monitor is now configured! 🎉",
                headers={"Title": "Setup Complete"},
                timeout=10
            )
            if resp.status_code == 200:
                print("  ✅ Test notification sent! Check your phone.")
            else:
                print(f"  ⚠️  Unexpected response: {resp.status_code}")
        except Exception as e:
            print(f"  ⚠️  Could not send test: {e}")
            print("      (You can test later by running: python main.py)")

    # ── Polling Interval ──────────────────────────────────────────────────────
    print_section("Step 3: Polling Settings")
    print("How often should we check for new alarms?")
    print("  • 10 seconds = Fast detection, more network traffic")
    print("  • 30 seconds = Balanced (recommended)")
    print("  • 60 seconds = Slower detection, minimal traffic")
    print()

    poll_interval = ask(
        "Enter poll interval in seconds",
        default="10",
        validator=lambda x: x.isdigit() and int(x) >= 1,
        help_text="Must be a number (seconds)"
    )

    # ── Confirm and Write ────────────────────────────────────────────────────
    print_section("Configuration Summary")
    print(f"  MTConnect Host:  {mtconnect_host}")
    print(f"  MTConnect Port:  {mtconnect_port}")
    print(f"  Device Name:     {mtconnect_device}")
    print(f"  ntfy Topic:      {ntfy_topic}")
    print(f"  Poll Interval:   {poll_interval} seconds")
    print()

    if not ask_yes_no("Save this configuration?", default="yes"):
        print("\nSetup cancelled. No changes were made.")
        sys.exit(0)

    # ── Write config.py ──────────────────────────────────────────────────────
    config_content = f'''"""
Configuration for the Okuma MTConnect Alarm Poller.
Generated by setup.py on {os.popen('date').read().strip()}
"""

# ── MTConnect Agent ──────────────────────────────────────────────────────────
MTCONNECT_HOST = "{mtconnect_host}"
MTCONNECT_PORT = {mtconnect_port}
MTCONNECT_URL = f"http://{{MTCONNECT_HOST}}:{{MTCONNECT_PORT}}"
MTCONNECT_DEVICE = "{mtconnect_device}"

# ── Polling Settings ───────────────────────────────────────────────────────────
POLL_INTERVAL_SECONDS = {poll_interval}
REQUEST_TIMEOUT_SECONDS = 15

# ── NTFY ─────────────────────────────────────────────────────────────────────
NTFY_TOPIC = "{ntfy_topic}"
NTFY_URL = f"https://ntfy.sh/{{NTFY_TOPIC}}"
NTFY_SERVER = "https://ntfy.sh"
NTFY_PRIORITY = 4
NTFY_TAGS = ["warning", "bell"]
NTFY_CLICK = "https://ntfy.sh"

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE = "alarm_poller.log"
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
'''

    try:
        with open("config.py", "w") as f:
            f.write(config_content)
        print("\n✅ Configuration saved to config.py")
    except Exception as e:
        print(f"\n❌ Failed to save config: {e}")
        sys.exit(1)

    # ── Done ───────────────────────────────────────────────────────────────────
    print()
    print("=" * 50)
    print("  Setup Complete!")
    print("=" * 50)
    print()
    print("Next steps:")
    print("  1. Run: python main.py")
    print("  2. Check your phone for notifications")
    print("  3. Edit config.py anytime to change settings")
    print()
    print("To run automatically on Windows startup, see README.md")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(0)
