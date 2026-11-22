"""Managed, read-only Drive Buddy bridge for experimental Comma hardware.

Vehicle control and CAN writers are intentionally not imported or accessed.
Requires DRIVEBUDDY_SHADOW_TOKEN and explicit DRIVEBUDDY_SHADOW_ENABLED=1.
"""
import os
from threading import Thread
from http.server import ThreadingHTTPServer

from openpilot.drivebuddy_shadow.comma_carstate_reader import CommaCarStateReader
from openpilot.drivebuddy_shadow.receiver import NOTICE_PATH, make_handler


def main():
  if os.environ.get("DRIVEBUDDY_SHADOW_ENABLED") != "1":
    return
  token = os.environ.get("DRIVEBUDDY_SHADOW_TOKEN", "")
  if len(token) < 16:
    raise RuntimeError("DRIVEBUDDY_SHADOW_TOKEN must contain at least 16 characters")
  NOTICE_PATH.unlink(missing_ok=True)
  reader = CommaCarStateReader()
  handler = make_handler(token, "/tmp/drivebuddy-shadow-advisories.jsonl", reader.snapshot, notice_path=NOTICE_PATH)
  with ThreadingHTTPServer(("0.0.0.0", 8765), handler) as server:
    # msgq wakes the thread that created the subscription, so poll on that same thread.
    http_thread = Thread(target=server.serve_forever, name="drivebuddy-http", daemon=True)
    http_thread.start()
    try:
      reader.run()
    finally:
      server.shutdown()
      http_thread.join()


if __name__ == "__main__":
  main()
