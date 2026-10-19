"""
Optional tracing. Off normally; start the app as
    QUICKKEY_DEBUG=1 python main.py
to print a line at each step of the volume-bar path (key seen -> volume read ->
sent to the device), which is the quickest way to see where something stops.
"""

import os
import time

ENABLED = bool(os.environ.get("QUICKKEY_DEBUG"))


def debug(message: str):
    if ENABLED:
        print(f"[debug {time.monotonic() % 1000:7.3f}] {message}", flush=True)
