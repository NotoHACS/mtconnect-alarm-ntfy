# MTConnect Alarm Monitor (Classic)

Polls an Okuma MTConnect agent for CNC alarms and sends push notifications via [ntfy.sh](https://ntfy.sh) when alarms fire or clear.

---

## Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Python** | 3.8.x | **Last version supporting Windows 7** |
| **OS** | Windows 7+ | Windows 10/11 recommended |
| **Network** | Internet | For ntfy.sh notifications |

> [!] **Windows 7 users**: Python 3.8.10 is the newest version that works on Windows 7. Download it [here](https://www.python.org/downloads/release/python-3810/).

---

## Quick Start

### 1. Install Python 3.8

- Download Python 3.8.10 from [python.org](https://www.python.org/downloads/release/python-3810/)
- Run installer, **check "Add Python to PATH"**

### 2. Download This Project

Download the ZIP from GitHub and extract it, or clone:

```bash
git clone https://github.com/NotoHACS/mtconnect-alarm-ntfy.git
cd mtconnect-alarm-ntfy
```

### 3. Launch the System Tray App

Double-click **`start_tray.bat`** — it will:

1. Install Python dependencies automatically (first run only)
2. Start the system tray icon

On first launch, the app detects that no NTFY topic has been set and shows a notification prompting you to configure settings before polling begins.

### 4. Configure Settings

1. Right-click the tray icon → **Settings...**
2. Set your **NTFY Topic** (required — this is your notification channel)
3. Adjust other settings as needed (MTConnect host, poll interval, etc.)
4. Click **Save**
5. Right-click tray icon → **Start Polling** (or restart the app)

> The NTFY Topic is required — you cannot save settings without it. Subscribe to the same topic in the [ntfy app](https://ntfy.sh) on your phone to receive push notifications.

---

## Two Ways to Run

### System Tray App (Recommended)

```
start_tray.bat          # Double-click to launch
```

- Lives in the system tray with a green/gray status icon
- Start/stop polling via right-click menu
- Open Settings GUI from the tray menu
- Auto-starts polling if already configured; stays stopped on first run

### Headless CLI (For Servers / No GUI)

```bash
python main.py              # polls forever
python main.py --dry-run    # log without sending notifications
python main.py --once       # single poll and exit
```

Run via Task Scheduler or `start_monitor.bat` for unattended operation.

---

## System Tray Menu

| Menu Item | Action |
|-----------|--------|
| Polling: Running / Stopped | Status indicator (disabled) |
| Start Polling | Begin the poll loop (disabled if already running) |
| Stop Polling | Stop the poll loop cleanly |
| Settings... | Open the configuration GUI |
| Quit | Stop polling and exit |

---

## Configuration GUI

Run `python config_gui.py` or open via the tray menu.

All settings are stored in **`config_defaults.py`** — the same file the app reads at runtime. Changes are written directly; no intermediate `config_local.py` is needed. If a `config_local.py` exists from a previous setup, the GUI will detect it and offer to delete it.

### Settings Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `MTCONNECT_HOST` | `localhost` | MTConnect agent IP or hostname |
| `MTCONNECT_PORT` | `5000` | MTConnect agent port |
| `MTCONNECT_DEVICE` | *(empty)* | Device name filter (leave empty for single CNC per IP) |
| `POLL_INTERVAL_SECONDS` | `5` | Seconds between polls |
| `REQUEST_TIMEOUT_SECONDS` | `15` | HTTP request timeout |
| `NTFY_TOPIC` | *(empty — required)* | Your notification channel name |
| `NTFY_SERVER` | `https://ntfy.sh` | NTFY server URL |
| `NTFY_PRIORITY` | `4` | Default notification priority (1–5) |
| `NTFY_TAGS` | `["warning", "bell"]` | Default notification tags |
| `LOG_FILE` | `alarm_poller.log` | Log file path |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `ALARM_MIN_LIFETIME_SECONDS` | `15.0` | Min seconds an alarm must be active before notifying |
| `SUPPRESS_CODES` | `[]` | Alarm codes to never notify on (e.g. `["1234", "5678"]`) |

---

## Updating

Double-click **`update.bat`** — it will:

1. Download the latest code from GitHub
2. Update all program files
3. **Smart-merge `config_defaults.py`** — your existing values are preserved; new keys from the update are added with their defaults

No need to reconfigure after updates!

---

## Getting ntfy Notifications

1. Install the [ntfy app](https://ntfy.sh) from F-Droid, Google Play, or the App Store
2. Subscribe to your topic: `https://ntfy.sh/your-topic-name`
3. Test it: visit the URL in a browser

---

## Notification Priority

Okuma alarm levels map to ntfy priorities and tags:

| Alarm Level | NTFY Priority | Tags |
|-------------|---------------|------|
| P (Emergency) | 5 (max) | skull, rotating_light, bell |
| A (Critical) | 5 (max) | rotating_light, bell |
| B | 4 (high) | warning, bell |
| C | 3 (default) | warning |
| D | 2 (low) | information_source |
| Cleared | 3 | white_check_mark |

---

## Running Automatically on Windows Startup

### Option 1: Startup Folder (Easiest)

1. Press `Win + R`, type `shell:startup`, press Enter
2. Create a shortcut to `start_tray.bat` in the Startup folder

### Option 2: Windows Task Scheduler (Recommended)

1. Open Task Scheduler (`taskschd.msc`)
2. Create a new task:
   - **General**: Name it "MTConnect Alarm Monitor"
   - **Triggers**: Begin the task: **At logon**, delay for **1 minute**
   - **Actions**: Start a program: `pythonw.exe`
   - **Arguments**: `C:\path\to\mtconnect-alarm-ntfy\tray_app.py`
   - **Conditions**: Uncheck "Start the task only if the computer is on AC power"
3. The tray icon will appear in the system tray after login

### Option 3: Headless / Service Mode

Use `start_monitor.bat` (5-minute delayed start) or set up Task Scheduler to run `python main.py` directly — no GUI, no tray icon, just polling.

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **requests** | >= 2.31.0 | HTTP client for MTConnect API and ntfy.sh |
| **pystray** | >= 1.10.0 | System tray icon |
| **Pillow** | >= 10.0.0 | Icon image generation |

All dependencies are auto-installed on first launch via `start_tray.bat` or `tray_app.py`.

Optional:
- **ntfy** — Python ntfy library (falls back to requests if not installed)

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Python not found" | Reinstall Python 3.8, check "Add to PATH" |
| "No module named pystray" | Run `pip install -r requirements.txt` or re-run `start_tray.bat` |
| First-run: polling won't start | Set your NTFY topic in Settings, then Start Polling |
| No notifications | Check your topic name matches in the ntfy app |
| SSL errors on Windows 7 | TLS 1.2 adapter is included; check internet connection |

---

## Files

| File | Purpose |
|------|---------|
| `tray_app.py` | System tray app with start/stop and settings |
| `config_gui.py` | Tkinter configuration GUI |
| `main.py` | Headless CLI poll loop |
| `poller.py` | MTConnect XML parsing and alarm state tracking |
| `notifier.py` | ntfy.sh integration with retry logic |
| `config.py` | Config import wrapper (loads `config_local.py` → `config_defaults.py`) |
| `config_defaults.py` | All configuration values |
| `models.py` | Alarm data structures |
| `alarm_db.json` | Alarm code lookup database |
| `start_tray.bat` | Tray app launcher (auto-installs deps) |
| `start_monitor.bat` | Headless launcher with 5-minute delay |
| `update.bat` / `update_helper.py` | Auto-updater with smart config merge |

---

## License

MIT — See LICENSE file

## Contributing

Issues and PRs welcome at https://github.com/NotoHACS/mtconnect-alarm-ntfy