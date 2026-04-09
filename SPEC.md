# Alarm Poller — Specification

## Overview

Polls the Okuma MTConnect agent for active alarms and sends Ntfy push notifications when alarms appear, change, or clear.

## Alarm Severity Priority Scheme

Okuma alarm levels are encoded in the `native_message` text as `ALARM_X` (where X is the severity letter), and are also stored in `alarm_db.json` as `level`.

### Priority Mapping (NTFY priority 1–5)

| Okuma Level | NTFY Priority | Tags                              | Notes                     |
|-------------|---------------|-----------------------------------|---------------------------|
| P           | 5             | `fire`, `rotating_light`, `bell`  | Most urgent               |
| A           | 5             | `rotating_light`, `bell`           | Critical                  |
| B           | 4             | `warning`, `bell`                 |                           |
| C           | 3             | `warning`                         |                           |
| D           | 2             | `information_source`               | Lowest                    |
| ERR         | 4             | `warning`, `bell`                 | System errors (DB-only)   |
| Unknown     | 3             | `warning`, `bell`                 | Default                   |

Cleared alarms → priority 3, tags: `white_check_mark`

## Data Model

### Alarm (models.py)

Key fields:

- `data_item_id` — MTConnect `<DataItem>` id attribute
- `native_code` — alarm code, e.g. `"4708"`
- `native_message` — raw text, e.g. `"4708 ALARM_D DOOR"`
- `severity` — from `nativeSeverity` XML attribute (not the Okuma level letter)
- **`okuma_level`** — severity letter extracted from `native_message` (A, B, C, D, P, or ERR)
- `state` — `"active"` | `"cleared"` | `"available"` | `"unavailable"`
- `component` — source component, e.g. `"CNC"`, `"Spindle"`
- `is_active` — True when state == "active"
- `key` — unique id = `{native_code}@{component}` (case-insensitive)

## Architecture

```
poller.py      — AlarmPoller class: fetches /current, parses XML, tracks state changes
main.py        — poll loop, notification formatting, ntfy dispatch
models.py      — Alarm dataclass
config.py      — all settings
alarm_db.json  — Okuma alarm code → {name, level, description} lookup
notifier.py    — NtfyNotifier class (sends to ntfy.sh)
```

## Notification Flow

1. `AlarmPoller.poll()` yields `{"type": "new"|"cleared"|"reactivated", "alarm": Alarm}`
2. `on_new_alarm()` / `on_cleared_alarm()` format the message and determine priority/tags
3. `_ntfy_send()` runs `curl` subprocess to publish to NTFY topic

## Phase 2 TODO

- [x] **Alarm severity priority scheme** — Okuma levels A/B/C/D/P/ERR map to NTFY priority + tags
- [ ] Screenshot on alarm — capture machine screen when critical alarm fires
