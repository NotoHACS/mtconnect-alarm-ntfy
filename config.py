# Configuration for MTConnect Alarm Monitor
# Machine-specific settings go in config_local.py (not tracked by git)
# This file imports from config_local if it exists, otherwise uses config_defaults

try:
    # Try to import machine-specific config
    from config_local import *
except ImportError:
    # Fall back to defaults
    from config_defaults import *
