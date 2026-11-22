"""Host smoke test for the release manager, msgq, Cap'n Proto and bridge HTTP API.

The Params fixture supplies serialized CarParams via a temporary file because
the release's on-device Params shared library is built for ARM64.
"""

import importlib
import json
import os
from pathlib import Path
import tempfile
import time
from types import ModuleType
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

import openpilot.cereal.messaging as messaging
from opendbc.car.structs import CarParams
from opendbc.car.toyota.values import ToyotaFlags


TOKEN = "release-smoke-test-token"


class ReleaseBridgeTest(unittest.TestCase):
  def test_managed_process_and_toyota_carstate(self):
    with tempfile.TemporaryDirectory() as directory:
      params_file = Path(directory) / "CarParams"
      params_module = ModuleType("openpilot.common.params")

      class Params:
        def get(self, key, block=False):
          if key != "CarParams" or block:
            raise AssertionError((key, block))
          try:
            return params_file.read_bytes()
          except FileNotFoundError:
            return None

      params_module.Params = Params
      prefix = "drivebuddy-test-" + uuid4().hex
      shm_path = Path("/dev/shm", "msgq_" + prefix)
      shm_path.mkdir()
      self.addCleanup(shm_path.rmdir)
      self.addCleanup((shm_path / "carState").unlink, missing_ok=True)
      with patch.dict(os.environ, OPENPILOT_PREFIX=prefix, DRIVEBUDDY_SHADOW_ENABLED="0",
                      DRIVEBUDDY_SHADOW_TOKEN=TOKEN), patch.dict("sys.modules", {"openpilot.common.params": params_module}):
        config = importlib.import_module("openpilot.system.manager.process_config")
        self.assertFalse(config.managed_processes["drivebuddy_shadow"].enabled)
        os.environ["DRIVEBUDDY_SHADOW_ENABLED"] = "1"
        process = importlib.reload(config).managed_processes["drivebuddy_shadow"]
        self.assertTrue(process.enabled)
        publisher = messaging.PubMaster(["carState"])

        def set_params(brand, flags, not_car=False):
          # Match production's atomic replacement of a Params value.
          staging = params_file.with_suffix(".new")
          staging.write_bytes(CarParams.new_message(brand=brand, flags=int(flags), notCar=not_car).to_bytes())
          staging.replace(params_file)

        def read_status(token=TOKEN):
          request = Request("http://127.0.0.1:8765/v1/blindspots", headers={"X-DriveBuddy-Token": token})
          with urlopen(request, timeout=1) as response:
            return json.load(response)

        def wait_for(expected, *, send=None):
          deadline = time.monotonic() + 4
          latest = None
          while time.monotonic() < deadline:
            self.assertTrue(process.proc.is_alive(), process.proc.exitcode)
            if send is not None:
              publisher.send("carState", send())
            try:
              latest = read_status()
            except OSError:
              time.sleep(0.03)
              continue
            self.assertIs(latest["appliedToVehicle"], False)
            actual = latest["available"], latest["leftBlindspot"], latest["rightBlindspot"]
            if actual == expected:
              return
            time.sleep(0.03)
          self.fail(f"Expected {expected}, received {latest}")

        def car_state(left, right, *, valid=True, old=False):
          message = messaging.new_message("carState", valid=valid)
          message.carState.leftBlindspot = left
          message.carState.rightBlindspot = right
          if old:
            message.logMonoTime -= 3_000_000_000
          return message

        unavailable = (False, None, None)
        process.start()
        try:
          wait_for(unavailable)
          with self.assertRaises(HTTPError) as unauthorized:
            read_status(token="wrong")
          self.assertEqual(401, unauthorized.exception.code)
          for brand, flags, not_car in (
            ("honda", ToyotaFlags.HAS_BSM, False),
            ("toyota", 0, False),
            ("toyota", ToyotaFlags.HAS_BSM, True),
          ):
            set_params("toyota", ToyotaFlags.HAS_BSM)
            wait_for((True, True, False), send=lambda: car_state(True, False))
            set_params(brand, flags, not_car)
            wait_for(unavailable, send=lambda: car_state(True, True))

          set_params("toyota", ToyotaFlags.HAS_BSM)
          wait_for((True, True, False), send=lambda: car_state(True, False))
          wait_for((True, False, True), send=lambda: car_state(False, True))
          wait_for((True, False, False), send=lambda: car_state(False, False))
          wait_for(unavailable, send=lambda: car_state(True, True, valid=False))
          wait_for((True, True, True), send=lambda: car_state(True, True))
          wait_for(unavailable, send=lambda: car_state(False, False, old=True))
          wait_for((True, True, True), send=lambda: car_state(True, True))
          wait_for(unavailable)
          wait_for((True, True, True), send=lambda: car_state(True, True))
          params_file.unlink()
          wait_for(unavailable, send=lambda: car_state(True, True))
        finally:
          self.assertEqual(0, process.stop())

        process.start()
        try:
          wait_for(unavailable)
        finally:
          self.assertEqual(0, process.stop())


if __name__ == "__main__":
  unittest.main()
