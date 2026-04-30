#!/usr/bin/env python3
"""
Update script for MTConnect Alarm Monitor.
Called by update.bat. Downloads latest from GitHub and updates files.
"""

import ast
import argparse
import os
import shutil
import ssl
import sys
import urllib.request
import zipfile


def download_zip(url, output_path):
    """Download ZIP from GitHub."""
    try:
        # Bypass SSL certificate verification (needed for industrial Windows machines)
        ssl._create_default_https_context = ssl._create_unverified_context
        urllib.request.urlretrieve(url, output_path)
        print(f"Download successful: {url}")
        return True
    except Exception as e:
        print(f"Download failed: {e}")
        return False


def extract_zip(zip_path, extract_path):
    """Extract ZIP file."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        print(f"Extraction successful to {extract_path}")
        return True
    except Exception as e:
        print(f"Extraction failed: {e}")
        return False


def _generate_config(values):
    """Generate config_defaults.py content from a values dict."""
    lines = []
    lines.append('"""')
    lines.append("Configuration defaults for MTConnect Alarm Monitor.")
    lines.append("Edited via config_gui.py.")
    lines.append('"""')
    lines.append("")

    def section(title):
        lines.append("")
        lines.append(f"# {'─' * 4} {title} {'─' * (50 - len(title) - 6)}")

    section("MTConnect Agent")
    host = values.get("MTCONNECT_HOST", "localhost")
    port = values.get("MTCONNECT_PORT", 5000)
    lines.append(f'MTCONNECT_HOST = "{host}"')
    lines.append(f"MTCONNECT_PORT = {port}")
    lines.append(f'MTCONNECT_URL = f"http://{{MTCONNECT_HOST}}:{{MTCONNECT_PORT}}"')
    device = values.get("MTCONNECT_DEVICE", "")
    lines.append(f'MTCONNECT_DEVICE = "{device}"')
    lines.append("")
    lines.append(f"POLL_INTERVAL_SECONDS = {values.get('POLL_INTERVAL_SECONDS', 5)}")
    lines.append(f"REQUEST_TIMEOUT_SECONDS = {values.get('REQUEST_TIMEOUT_SECONDS', 15)}")

    section("NTFY")
    topic = values.get("NTFY_TOPIC", "cnc")
    server = values.get("NTFY_SERVER", "https://ntfy.sh")
    lines.append(f'NTFY_TOPIC = "{topic}"')
    lines.append(f'NTFY_URL = f"{server}/{{NTFY_TOPIC}}"')
    lines.append(f'NTFY_SERVER = "{server}"')
    lines.append(f"NTFY_PRIORITY = {values.get('NTFY_PRIORITY', 4)}")
    tags = values.get("NTFY_TAGS", ["warning", "bell"])
    lines.append(f"NTFY_TAGS = {tags!r}")
    click = values.get("NTFY_CLICK", server)
    lines.append(f'NTFY_CLICK = "{click}"')

    section("Logging")
    lines.append(f'LOG_FILE = "{values.get("LOG_FILE", "alarm_poller.log")}"')
    lines.append(f'LOG_LEVEL = "{values.get("LOG_LEVEL", "INFO")}"')
    lines.append(f'LOG_FORMAT = "{values.get("LOG_FORMAT", "%(asctime)s [%(levelname)s] %(name)s \u2014 %(message)s")}"')
    lines.append(f'LOG_DATE_FORMAT = "{values.get("LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S")}"')

    section("Alarm Filtering")
    lines.append(f"ALARM_MIN_LIFETIME_SECONDS = {values.get('ALARM_MIN_LIFETIME_SECONDS', 15.0)}")
    suppress = values.get("SUPPRESS_CODES", [])
    lines.append(f"SUPPRESS_CODES = {suppress!r}")

    lines.append("")
    return "\n".join(lines)


def _parse_config(filepath):
    """Parse a Python config file into {NAME: value} dict."""
    tree = ast.parse(open(filepath, encoding="utf-8").read())
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            name = node.targets[0].id if isinstance(node.targets[0], ast.Name) else None
            if name and name.isupper():
                try:
                    values[name] = ast.literal_eval(node.value)
                except (ValueError, SyntaxError):
                    values[name] = None
    return values


def merge_config_defaults(source_dir, dest_dir):
    """Merge repo config_defaults.py with user's existing values.

    New keys from the repo are added with their defaults.
    User's existing values are preserved.
    Removed keys are dropped.
    """
    new_path = os.path.join(source_dir, "config_defaults.py")
    user_path = os.path.join(dest_dir, "config_defaults.py")

    if not os.path.exists(new_path):
        print("  Not found in update: config_defaults.py (skipped)")
        return

    new_vals = _parse_config(new_path)
    user_vals = _parse_config(user_path) if os.path.exists(user_path) else {}

    merged = dict(new_vals)
    for k, v in user_vals.items():
        if k in merged:
            merged[k] = v

    content = _generate_config(merged)
    with open(user_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated: config_defaults.py (values preserved)")


def update_files(source_dir):
    """Copy updated files from source to current directory."""
    files_to_update = [
        'main.py',
        'poller.py',
        'models.py',
        'notifier.py',
        'config.py',
        'config_defaults.py',
        'config_gui.py',
        'tray_app.py',
        'start_tray.bat',
        'start_monitor.bat',
        'SPEC.md',
        'alarm_db.json',
        'requirements.txt',
        'update.bat',
        'update_helper.py',
    ]

    updated_count = 0
    for file in files_to_update:
        src = os.path.join(source_dir, file)
        if os.path.exists(src):
            try:
                if file == "config_defaults.py":
                    merge_config_defaults(source_dir, ".")
                else:
                    shutil.copy2(src, file)
                    print(f"Updated: {file}")
                updated_count += 1
            except Exception as e:
                print(f"Failed to update {file}: {e}")
        else:
            print(f"Not found in update: {file} (skipped)")

    return updated_count


def main():
    parser = argparse.ArgumentParser(description='Update MTConnect Alarm Monitor')
    parser.add_argument('branch', nargs='?', default='master', help='Git branch to update from')
    args = parser.parse_args()

    branch = args.branch
    zip_url = f"https://github.com/NotoHACS/mtconnect-alarm-ntfy/archive/refs/heads/{branch}.zip"
    temp_zip = "update_temp.zip"
    extract_path = "update_temp"

    print(f"Updating from branch: {branch}")
    print(f"URL: {zip_url}")

    # Clean up any old files
    if os.path.exists(temp_zip):
        os.remove(temp_zip)
    if os.path.exists(extract_path):
        shutil.rmtree(extract_path)

    # Download
    print("\nDownloading...")
    if not download_zip(zip_url, temp_zip):
        return 1

    # Extract
    print("\nExtracting...")
    if not extract_zip(temp_zip, extract_path):
        return 1

    # Find extracted folder
    extracted_dirs = [d for d in os.listdir(extract_path) if os.path.isdir(os.path.join(extract_path, d))]
    if not extracted_dirs:
        print("No extracted directory found!")
        return 1

    source_dir = os.path.join(extract_path, extracted_dirs[0])

    # Update files
    print("\nUpdating files...")
    updated_count = update_files(source_dir)
    print(f"\nUpdated {updated_count} files")

    # Cleanup
    print("\nCleaning up...")
    shutil.rmtree(extract_path)
    os.remove(temp_zip)

    print("Update complete!")
    return 0


if __name__ == '__main__':
    sys.exit(main())
