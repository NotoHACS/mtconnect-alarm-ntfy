#!/usr/bin/env python3
"""
GUI Configuration Editor for MTConnect Alarm Monitor.
Reads/writes config_defaults.py directly. Replaces the setup.py wizard workflow.
"""

import ast
import os
import re
import tkinter as tk
from tkinter import ttk, messagebox

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config_defaults.py")
LOCAL_FILE = os.path.join(os.path.dirname(__file__), "config_local.py")


def parse_config(filepath):
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


def render_value(val):
    if isinstance(val, list):
        return ", ".join(str(v) for v in val)
    return str(val) if val is not None else ""


def parse_list_input(text):
    parts = [p.strip() for p in text.split(",") if p.strip()]
    return parts


def parse_int_input(text):
    text = text.strip()
    if not text:
        return None
    return int(text)


def parse_float_input(text):
    text = text.strip()
    if not text:
        return None
    return float(text)


STRING_FIELDS = {
    "MTCONNECT_HOST": "MTConnect Agent Host",
    "MTCONNECT_DEVICE": "MTConnect Device Name",
    "NTFY_TOPIC": "NTFY Topic",
    "NTFY_SERVER": "NTFY Server URL",
    "NTFY_CLICK": "NTFY Click URL",
    "LOG_FILE": "Log File Path",
    "LOG_FORMAT": "Log Format String",
    "LOG_DATE_FORMAT": "Log Date Format",
}

INT_FIELDS = {
    "MTCONNECT_PORT": "MTConnect Agent Port",
    "POLL_INTERVAL_SECONDS": "Poll Interval (seconds)",
    "REQUEST_TIMEOUT_SECONDS": "Request Timeout (seconds)",
    "NTFY_PRIORITY": "NTFY Priority (1-5)",
}

FLOAT_FIELDS = {
    "ALARM_MIN_LIFETIME_SECONDS": "Min Alarm Lifetime (seconds)",
}

CHOICE_FIELDS = {
    "LOG_LEVEL": ("Log Level", ["DEBUG", "INFO", "WARNING", "ERROR"]),
}

LIST_FIELDS = {
    "NTFY_TAGS": "NTFY Tags (comma separated)",
    "SUPPRESS_CODES": "Suppress Alarm Codes (comma separated)",
}


class ConfigGUI(tk.Toplevel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.title("MTConnect Alarm Monitor — Config")
        self.resizable(True, True)

        self.values = parse_config(CONFIG_FILE)
        self.widgets = {}

        self._build_ui()

        if os.path.exists(LOCAL_FILE):
            self._show_local_warning()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)

        row = 0

        # ── Local config warning (hidden by default) ──────────────────────
        self.local_warn_frame = ttk.Frame(main)
        self.local_warn_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))
        self.local_warn_label = ttk.Label(
            self.local_warn_frame,
            text="",
            foreground="white",
            background="#c0392b",
            padding=(8, 4),
        )
        self.local_warn_label.pack(fill="x", side="left", expand=True)
        self.delete_local_btn = ttk.Button(
            self.local_warn_frame, text="Delete config_local.py", command=self._delete_local
        )
        self.delete_local_btn.pack(side="right", padx=(8, 0))
        self.local_warn_frame.grid_remove()
        row += 1

        # ── MTConnect Agent ──────────────────────────────────────────────
        sep = ttk.Separator(main, orient="horizontal")
        sep.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(4, 4))
        row += 1
        ttk.Label(main, text="MTConnect Agent", font=("", 10, "bold")).grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(0, 4)
        )
        row += 1
        row = self._add_fields(main, row, STRING_FIELDS, INT_FIELDS)

        # ── NTFY ─────────────────────────────────────────────────────────
        sep = ttk.Separator(main, orient="horizontal")
        sep.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(8, 4))
        row += 1
        ttk.Label(main, text="NTFY Notifications", font=("", 10, "bold")).grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(0, 4)
        )
        row += 1
        row = self._add_fields(main, row, {}, {
            "NTFY_TOPIC": "NTFY Topic",
            "NTFY_SERVER": "NTFY Server URL",
            "NTFY_PRIORITY": "NTFY Priority (1-5)",
        })
        row = self._add_list_field(main, row, "NTFY_TAGS", "NTFY Tags (comma separated)")

        # ── Polling ──────────────────────────────────────────────────────
        sep = ttk.Separator(main, orient="horizontal")
        sep.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(8, 4))
        row += 1
        ttk.Label(main, text="Polling", font=("", 10, "bold")).grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(0, 4)
        )
        row += 1
        row = self._add_fields(main, row, {}, {
            "POLL_INTERVAL_SECONDS": "Poll Interval (seconds)",
            "REQUEST_TIMEOUT_SECONDS": "Request Timeout (seconds)",
        })

        # ── Logging ──────────────────────────────────────────────────────
        sep = ttk.Separator(main, orient="horizontal")
        sep.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(8, 4))
        row += 1
        ttk.Label(main, text="Logging", font=("", 10, "bold")).grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(0, 4)
        )
        row += 1
        row = self._add_fields(main, row, {"LOG_FILE": "Log File Path"}, {})
        row = self._add_choice_field(main, row, "LOG_LEVEL")

        # ── Alarm Filtering ──────────────────────────────────────────────
        sep = ttk.Separator(main, orient="horizontal")
        sep.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(8, 4))
        row += 1
        ttk.Label(main, text="Alarm Filtering", font=("", 10, "bold")).grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(0, 4)
        )
        row += 1
        row = self._add_fields(main, row, {}, {}, FLOAT_FIELDS)
        row = self._add_list_field(main, row, "SUPPRESS_CODES", "Suppress Codes (comma separated)")
        row = self._add_field(main, row, "MTCONNECT_DEVICE", "Device Name")

        # ── Buttons ──────────────────────────────────────────────────────
        row += 1
        btn_frame = ttk.Frame(main)
        btn_frame.grid(row=row, column=0, columnspan=3, pady=(16, 0))

        ttk.Button(btn_frame, text="Test Notification", command=self._test_notification).pack(
            side="left", padx=(0, 8)
        )
        ttk.Button(btn_frame, text="Save", command=self._save).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Cancel", command=self._on_close).pack(side="left", padx=4)

        # stretch last row
        main.columnconfigure(1, weight=1)

    def _add_field(self, parent, row, key, label_text):
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=2)
        var = tk.StringVar(value=render_value(self.values.get(key, "")))
        entry = ttk.Entry(parent, textvariable=var)
        entry.grid(row=row, column=1, sticky="ew", pady=2)
        self.widgets[key] = var
        return row + 1

    def _add_fields(self, parent, row, string_map=None, int_map=None, float_map=None):
        if string_map:
            for key, label in string_map.items():
                row = self._add_field(parent, row, key, label)
        if int_map:
            for key, label in int_map.items():
                row = self._add_field(parent, row, key, label)
        if float_map:
            for key, label in float_map.items():
                row = self._add_field(parent, row, key, label)
        return row

    def _add_choice_field(self, parent, row, key):
        label = CHOICE_FIELDS[key][0]
        choices = CHOICE_FIELDS[key][1]
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=2)
        var = tk.StringVar(value=self.values.get(key, choices[0]))
        menu = ttk.Combobox(parent, textvariable=var, values=choices, state="readonly")
        menu.grid(row=row, column=1, sticky="ew", pady=2)
        self.widgets[key] = var
        return row + 1

    def _add_list_field(self, parent, row, key, label):
        return self._add_field(parent, row, key, label)

    def _show_local_warning(self):
        self.local_warn_label.config(
            text="config_local.py exists and will override these values. "
                 "Delete it to ensure the GUI config takes full effect."
        )
        self.local_warn_frame.grid()

    def _delete_local(self):
        try:
            os.remove(LOCAL_FILE)
            self.local_warn_frame.grid_remove()
            messagebox.showinfo("Deleted", "config_local.py has been deleted.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete config_local.py:\n{e}")

    def _test_notification(self):
        topic = self.widgets.get("NTFY_TOPIC", tk.StringVar()).get().strip()
        server = self.widgets.get("NTFY_SERVER", tk.StringVar()).get().strip()
        if not topic or not server:
            messagebox.showwarning("Missing", "Set NTFY Topic and Server URL first.")
            return

        url = f"{server.rstrip('/')}/{topic}"
        try:
            import requests
            import ssl
            from requests.adapters import HTTPAdapter
            from urllib3.util.ssl_ import create_urllib3_context

            class TLSAdapter(HTTPAdapter):
                def init_poolmanager(self, *args, **kwargs):
                    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS)
                    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
                    ctx.verify_mode = ssl.CERT_NONE
                    kwargs["ssl_context"] = ctx
                    return super().init_poolmanager(*args, **kwargs)

            session = requests.Session()
            session.mount("https://", TLSAdapter())
            resp = session.post(
                url,
                data="MTConnect Alarm Monitor — config test",
                headers={"Title": "Config Test", "Tags": "bell"},
                timeout=15,
                verify=False,
            )
            if resp.status_code == 200:
                messagebox.showinfo("Test Sent", f"Notification sent to {url}")
            else:
                messagebox.showwarning("Unexpected", f"Server replied with status {resp.status_code}")
        except ImportError:
            messagebox.showerror("Missing", "requests library not installed.\nRun: pip install requests")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send test:\n{e}")

    def _collect_values(self):
        result = {}
        for key, var in self.widgets.items():
            raw = var.get().strip()
            if key in LIST_FIELDS:
                result[key] = parse_list_input(raw)
            elif key in INT_FIELDS:
                try:
                    result[key] = parse_int_input(raw)
                except ValueError:
                    raise ValueError(f"{key}: invalid integer '{raw}'")
            elif key in FLOAT_FIELDS:
                try:
                    result[key] = parse_float_input(raw)
                except ValueError:
                    raise ValueError(f"{key}: invalid number '{raw}'")
            elif key in CHOICE_FIELDS:
                result[key] = raw
            else:
                result[key] = raw
        return result

    def _generate_config(self, values):
        lines = []
        lines.append('"""')
        lines.append("Configuration defaults for MTConnect Alarm Monitor.")
        lines.append("Edited via config_gui.py.")
        lines.append('"""')
        lines.append("")

        def section(title):
            lines.append("")
            lines.append(f"# {'─' * 4} {title} {'─' * (50 - len(title) - 6)}")
            lines.append("")

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

    def _save(self):
        try:
            values = self._collect_values()
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
            return

        content = self._generate_config(values)
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write(content)

            if os.path.exists(LOCAL_FILE):
                os.remove(LOCAL_FILE)
                self.local_warn_frame.grid_remove()

            messagebox.showinfo("Saved", f"Configuration saved to config_defaults.py\n\nconfig_local.py was deleted.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save:\n{e}")

    def _on_close(self):
        self.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    app = ConfigGUI(parent=root)
    app.protocol("WM_DELETE_WINDOW", lambda: (app.destroy(), root.destroy()))
    root.mainloop()
