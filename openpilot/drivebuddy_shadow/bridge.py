"""Managed, read-only Drive Buddy bridge for experimental Comma hardware.

Vehicle control and CAN writers are intentionally not imported or accessed.
Requires DRIVEBUDDY_SHADOW_TOKEN and explicit DRIVEBUDDY_SHADOW_ENABLED=1.
"""
import os

from openpilot.drivebuddy_shadow.receiver import make_handler
from openpilot.drivebuddy_shadow.comma_carstate_reader import CommaCarStateReader
from http.server import ThreadingHTTPServer


def main():
  if os.environ.get("DRIVEBUDDY_SHADOW_ENABLED") != "1":
    return
  token = os.environ.get("DRIVEBUDDY_SHADOW_TOKEN", "")
  if len(token) < 16:
    raise RuntimeError("DRIVEBUDDY_SHADOW_TOKEN must contain at least 16 characters")
  reader = CommaCarStateReader()
  reader.start()
  server = ThreadingHTTPServer(("0.0.0.0", 8765), make_handler(token, "/tmp/drivebuddy-shadow-advisories.jsonl", reader.snapshot))
  try:
    server.serve_forever()
  finally:
    server.server_close()
    reader.stop()


if __name__ == "__main__":
  main()
