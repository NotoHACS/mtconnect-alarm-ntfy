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

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure

```bash
python setup.py
```

This interactive wizard will ask for:
- Your MTConnect agent IP/hostname and port
- Your ntfy.sh topic name (pick something unique/private)
- Polling interval and alarm filtering

Or manually edit `config_defaults.py` — see [Configuration](#configuration) below.

### 5. Start Monitoring

```bash
python main.py              # polls forever
python main.py --dry-run    # log without sending notifications
python main.py --once       # single poll and exit (for testing)
```

---

## Configuration

### Via Setup Wizard (Easiest)

```bash
python setup.py
```

Creates `config_local.py` with your machine-specific settings, which overrides `config_defaults.py`.

### Manual Configuration

Edit `config_defaults.py` directly:

```python
# MTConnect Agent
MTCONNECT_HOST = "localhost"
MTCONNECT_PORT = 5000
MTCONNECT_DEVICE = ""        # empty = accept all devices

# NTFY (pick a unique, private topic name)
NTFY_TOPIC = "your-private-topic-12345"

# Polling
POLL_INTERVAL_SECONDS = 5
REQUEST_TIMEOUT_SECONDS = 15

# Alarm filtering
ALARM_MIN_LIFETIME_SECONDS = 15.0
SUPPRESS_CODES = []          # e.g. ["1234", "5678"]
```

### Configuration Files

| File | Purpose | Edit? |
|------|---------|-------|
| `config.py` | Import wrapper | **No** |
| `config_defaults.py` | Default values | Yes (or use `setup.py`) |
| `config_local.py` | Machine-specific overrides (created by `setup.py`) | Yes |

---

## Updating

Double-click **`update.bat`** — it will:

1. Download the latest code from GitHub
2. Update all program files
3. **Preserve your `config_local.py` settings**

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
2. Copy `start_monitor.bat` into the Startup folder
3. Edit the path inside if needed — the script waits 5 minutes before starting

### Option 2: Windows Task Scheduler (Recommended)

1. Open Task Scheduler (`taskschd.msc`)
2. Create a new task:
   - **General**: Name it "MTConnect Alarm Monitor"
   - **Triggers**: Begin the task: **At startup**, delay for **5 minutes**
   - **Actions**: Start a program: `python.exe`
   - **Arguments**: `C:\path\to\mtconnect-alarm-ntfy\main.py`
   - **Conditions**: Uncheck "Start the task only if the computer is on AC power"
   - **Settings**: Check "Run whether user is logged on or not" (optional)

### Option 3: NSSM (Service)

For advanced users, use [NSSM](https://nssm.cc/):

```bash
nssm install MTConnectAlarmMonitor
# Set Path to: C:\path\to\python.exe
# Set Arguments to: C:\path\to\main.py
```

---

## Features

### User Reserve Code Enhancement

Okuma user reserve codes (alarms 2395, 4209, etc.) display their custom messages instead of generic "VDOUT=****" text.

**Before:** `VDOUT[990]=**** is specified in a program.`  
**After:** `[4209] SELECT RESTART`

### Alarm Suppression

Alarms that clear within `ALARM_MIN_LIFETIME_SECONDS` (default 15s) are silently discarded to prevent notification spam. Add alarm codes to `SUPPRESS_CODES` to completely suppress them.

### Automatic Updates

Run `update.bat` anytime to get the latest features without reconfiguring. Settings in `config_local.py` are preserved automatically.

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **requests** | >= 2.31.0 | HTTP client for MTConnect API and ntfy.sh |

Optional:
- **ntfy** — Python ntfy library (falls back to requests if not installed)

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Python not found" | Reinstall Python 3.8, check "Add to PATH" |
| "No module named requests" | Run `pip install -r requirements.txt` |
| No notifications | Check your topic name matches in the ntfy app |
| SSL errors | TLS 1.2 adapter is included; check internet connection |

---

## Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point, runs the poll loop |
| `poller.py` | MTConnect XML parsing and alarm state tracking |
| `notifier.py` | ntfy.sh integration with retry logic |
| `config.py` | Config import wrapper (`config_local.py` → `config_defaults.py`) |
| `config_defaults.py` | Default configuration values |
| `models.py` | Alarm data structures |
| `alarm_db.json` | Alarm code lookup database |
| `setup.py` | Interactive configuration wizard |
| `start_monitor.bat` | Windows startup launcher (5-minute delay) |
| `update.bat` / `update_helper.py` | Auto-updater from GitHub |

---

## License

MIT — See LICENSE file

## Contributing

Issues and PRs welcome at https://github.com/NotoHACS/mtconnect-alarm-ntfy