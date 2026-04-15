#!/usr/bin/env python3
"""
Interactive setup wizard for MTConnect Alarm Monitor.

Guides the user through configuration -- no need to edit files manually.
"""

import os
import sys
import re
from datetime import datetime


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
            print("  [!] This field is required.")
            continue

        if validator and not validator(answer):
            if help_text:
                print(f"  [!] {help_text}")
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

        print("  [!] Please enter 'yes' or 'no'")


def ask_choice(prompt, choices, default=None):
    """Ask user to select from a list of choices."""
    print(f"\n{prompt}")
    for i, (key, desc) in enumerate(choices, 1):
        marker = " *" if key == default else ""
        print(f"  {i}. {desc}{marker}")
    print()

    while True:
        answer = input(f"Enter choice (1-{len(choices)}): ").strip()
        if not answer and default:
            return default
        try:
            idx = int(answer) - 1
            if 0 <= idx < len(choices):
                return choices[idx][0]
        except ValueError:
            pass
        print(f"  [!] Please enter a number 1-{len(choices)}")


def validate_ip_or_hostname(value):
    """Basic validation for IP or hostname."""
    if not value:
        return False
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
    return re.match(r'^[a-zA-Z0-9_-]+$', value) is not None and len(value) >= 3


def validate_url(value):
    """Basic URL validation."""
    if not value:
        return False
    return value.startswith(('http://', 'https://'))


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
    print()

    if not ask_yes_no("Ready to start?", default="yes"):
        print("\nSetup cancelled. You can run this again anytime with: python setup.py")
        sys.exit(0)

    # -- MTConnect Agent Configuration -----------------------------------------
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

    # -- NTFY Server Selection -------------------------------------------------
    print_section("Step 2: Notification Server")
    print("Choose where to send notifications:")
    print()
    print("  Public (ntfy.sh): Free, easy setup, no server needed")
    print("  Private server:   Your own ntfy instance (more control)")
    print()

    ntfy_server_type = ask_choice(
        "Select notification server type:",
        [("public", "Public ntfy.sh (default)"),
         ("private", "Private ntfy server")],
        default="public"
    )

    ntfy_server = "https://ntfy.sh"
    ntfy_topic = ""
    test_url = ""

    if ntfy_server_type == "public":
        # -- Public ntfy.sh setup ----------------------------------------------
        print_section("Step 2a: ntfy.sh Topic")
        print("Pick a unique topic name that others won't guess.")
        print("Anyone who knows the topic name can subscribe.")
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

        test_url = f"https://ntfy.sh/{ntfy_topic}"

    else:
        # -- Private ntfy server setup -----------------------------------------
        print_section("Step 2a: Private NTFY Server")
        print("Configure your own ntfy server.")
        print()

        ntfy_server = ask(
            "Enter your ntfy server URL (e.g., https://ntfy.example.com)",
            default="https://ntfy.yourdomain.com",
            validator=validate_url,
            help_text="Must start with http:// or https://"
        )

        ntfy_topic = ask(
            "Enter your ntfy topic name",
            default="cnc-alarms",
            validator=validate_topic,
            help_text="Topic must be 3+ characters, letters/numbers/dashes/underscores only"
        )

        test_url = f"{ntfy_server.rstrip('/')}/{ntfy_topic}"

    print()
    print("[i] To receive notifications:")
    if ntfy_server_type == "public":
        print(f"   1. Install the ntfy app from F-Droid or Google Play")
        print(f"   2. Subscribe to topic: {ntfy_topic}")
        print(f"   3. Or visit: {test_url}")
    else:
        print(f"   1. Install the ntfy app")
        print(f"   2. Add your server: {ntfy_server}")
        print(f"   3. Subscribe to topic: {ntfy_topic}")
    print()

    if ask_yes_no("Would you like to test notifications now?", default="yes"):
        print("\n  Sending test notification...")
        try:
            import requests
            resp = requests.post(
                test_url,
                data=f"MTConnect Alarm Monitor configured! Topic: {ntfy_topic}",
                headers={"Title": "Setup Complete"},
                timeout=10
            )
            if resp.status_code == 200:
                print("  [OK] Test notification sent! Check your phone.")
            else:
                print(f"  [!] Unexpected response: {resp.status_code}")
        except Exception as e:
            print(f"  [!] Could not send test: {e}")
            print("      (You can test later by running: python main.py)")

    # -- Polling Interval ------------------------------------------------------
    print_section("Step 3: Polling Settings")
    print("How often should we check for new alarms?")
    print("  * 10 seconds = Fast detection, more network traffic")
    print("  * 30 seconds = Balanced (recommended)")
    print("  * 60 seconds = Slower detection, minimal traffic")
    print()

    poll_interval = ask(
        "Enter poll interval in seconds",
        default="10",
        validator=lambda x: x.isdigit() and int(x) >= 1,
        help_text="Must be a number (seconds)"
    )

    # -- Alarm Filtering ------------------------------------------------------
    print_section("Step 4: Alarm Filtering (Optional)")
    print("Suppress specific alarm codes and prevent spam notifications.")
    print("Useful for filtering out nuisance alarms or alarms that blink quickly.")
    print()

    suppress_codes = []
    alarm_min_lifetime = "15.0"

    if ask_yes_no("Enable alarm suppression?", default="no"):
        print("\nEnter alarm codes to completely suppress (never notify).")
        print("Example: 1234, 5678")
        print("Enter multiple codes separated by commas, or 'none' for none.")
        print()

        codes_input = ask(
            "Suppress codes",
            default="none",
            help_text="Comma-separated list of alarm codes to suppress"
        )

        if codes_input.lower() != "none":
            suppress_codes = [c.strip() for c in codes_input.split(",") if c.strip()]

    alarm_min_lifetime = ask(
        "Minimum alarm lifetime (seconds) before notifying",
        default="15.0",
        help_text="Alarms must be active this long before first notification"
    )

    # -- Confirm and Write -----------------------------------------------------
    print_section("Configuration Summary")
    print(f"  MTConnect Host:  {mtconnect_host}")
    print(f"  MTConnect Port:  {mtconnect_port}")
    print(f"  Device Name:     {mtconnect_device}")
    print(f"  NTFY Server:     {ntfy_server}")
    print(f"  NTFY Topic:      {ntfy_topic}")
    print(f"  Poll Interval:   {poll_interval} seconds")
    if suppress_codes:
        print(f"  Suppress Codes:  {', '.join(suppress_codes)}")
    print(f"  Min Lifetime:    {alarm_min_lifetime} seconds")
    print()

    if not ask_yes_no("Save this configuration?", default="yes"):
        print("\nSetup cancelled. No changes were made.")
        sys.exit(0)

    # -- Write config_local.py -------------------------------------------------
    config_content = f'''"""
Local configuration for MTConnect Alarm Monitor.
Generated by setup.py on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This file overrides config_defaults.py for machine-specific settings.
"""

# -- MTConnect Agent ----------------------------------------------------------
MTCONNECT_HOST = "{mtconnect_host}"
MTCONNECT_PORT = {mtconnect_port}
MTCONNECT_URL = f"http://{{MTCONNECT_HOST}}:{{MTCONNECT_PORT}}"
MTCONNECT_DEVICE = "{mtconnect_device}"

# -- Polling Settings -----------------------------------------------------------
POLL_INTERVAL_SECONDS = {poll_interval}

# -- NTFY ---------------------------------------------------------------------
NTFY_TOPIC = "{ntfy_topic}"
NTFY_URL = f"{ntfy_server}/{{NTFY_TOPIC}}"
NTFY_SERVER = "{ntfy_server}"
NTFY_PRIORITY = 4
NTFY_TAGS = ["warning", "bell"]
NTFY_CLICK = "{ntfy_server}"

# -- Logging ------------------------------------------------------------------
LOG_FILE = "alarm_poller.log"
LOG_LEVEL = "INFO"
'''

    config_content += f'''
# -- Alarm Filtering --------------------------------------------------------
ALARM_MIN_LIFETIME_SECONDS = {alarm_min_lifetime}
'''
    if suppress_codes:
        config_content += f'SUPPRESS_CODES = {suppress_codes!r}\n'

    try:
        with open("config_local.py", "w") as f:
            f.write(config_content)
        print("\n[OK] Configuration saved to config_local.py")
        print("     (This file is NOT tracked by git - machine-specific)")
    except Exception as e:
        print(f"\n[X] Failed to save config: {e}")
        sys.exit(1)

    # -- Done ------------------------------------------------------------------
    print()
    print("=" * 50)
    print("  Setup Complete!")
    print("=" * 50)
    print()
    print("Next steps:")
    print("  1. Run: python main.py")
    print("  2. Check your phone for notifications")
    print("  3. Edit config_local.py anytime to change settings")
    print()
    print("To run automatically on Windows startup, see README.md")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(0)
