# MTConnect Alarm Monitor (Classic)

Polls an Okuma MTConnect agent for CNC alarms and sends push notifications via [ntfy.sh](https://ntfy.sh) when alarms fire or clear.

---

## Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Python** | 3.8.x | **Last version supporting Windows 7** |
| **OS** | Windows 7+ | Windows 10/11 recommended |
| **Network** | Internet | For ntfy.sh notifications |

> ⚠️ **Windows 7 users**: Python 3.8.10 is the newest version that works on Windows 7. Download it [here](https://www.python.org/downloads/release/python-3810/).

---

## Quick Start

### 1. Install Python 3.8

- Download Python 3.8.10 from [python.org](https://www.python.org/downloads/release/python-3810/)
- Run installer, **check "Add Python to PATH"**

### 2. Download This Project

```bash
git clone https://github.com/NotoHACS/mtconnect-alarm-monitor-classic.git
cd mtconnect-alarm-monitor-classic
```

Or download the ZIP from GitHub and extract it.

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Interactive Setup

```bash
python setup.py
```

This will ask you for:
- Your MTConnect agent IP/hostname
- Your ntfy.sh topic name (pick something unique/private)
- Polling interval

### 5. Start Monitoring

```bash
python main.py
```

---

## Manual Configuration

If you prefer to edit `config.py` directly:

```python
# MTConnect Agent settings
MTCONNECT_HOST = "localhost"
MTCONNECT_PORT = 5000
MTCONNECT_DEVICE = "CNC_7"

# NTFY settings (use a private, random topic name)
NTFY_TOPIC = "your-private-topic-12345"
```

---

## Dependencies

- **requests** ≥ 2.31.0 — HTTP client for MTConnect API and ntfy.sh

Optional:
- **ntfy** — Python ntfy library (falls back to requests if not installed)

---

## How It Works

1. **Polls** your MTConnect agent every 10 seconds (configurable)
2. **Detects** new alarms, cleared alarms, and reactivations
3. **Sends** push notifications to your phone via ntfy.sh
4. **Retries** on network errors with exponential backoff

---

## Notification Priority

| Alarm Level | Priority | Tags |
|-------------|----------|------|
| P (Emergency) | 5 (max) | 🔥 fire, rotating_light |
| A (Critical) | 5 (max) | rotating_light, bell |
| B | 4 (high) | warning, bell |
| C | 3 (default) | warning |
| D | 2 (low) | information_source |
| Cleared | 3 | ✅ white_check_mark |

---

## Getting ntfy Notifications

1. Install the [ntfy Android app](https://f-droid.org/en/packages/io.heckel.ntfy/) or use the web
2. Subscribe to your topic: `https://ntfy.sh/your-topic-name`
3. Test it: visit the URL in a browser

---

## Running as a Service (Windows)

To run automatically on startup, use [NSSM](https://nssm.cc/):

```bash
nssm install MTConnectAlarmMonitor
# Set Path to python.exe
# Set Arguments to: C:\path\to\main.py
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Python not found" | Reinstall Python, check "Add to PATH" |
| "No module named requests" | Run `pip install requests` |
| No notifications | Check your topic name matches in ntfy app |
| SSL errors | Retry logic handles this; check internet connection |

---

## Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point, runs the poll loop |
| `poller.py` | MTConnect XML parsing and state tracking |
| `notifier.py` | ntfy.sh integration with retry logic |
| `config.py` | All user-configurable settings |
| `models.py` | Alarm data structures |
| `alarm_db.json` | Alarm code lookup database |
| `setup.py` | Interactive configuration wizard |

---

## License

MIT — See LICENSE file

## Contributing

Issues and PRs welcome at https://github.com/NotoHACS/mtconnect-alarm-monitor-classic
