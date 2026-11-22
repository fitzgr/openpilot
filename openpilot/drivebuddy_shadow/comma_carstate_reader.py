"""Subscribe to openpilot carState and expose only fresh Toyota blind-spot data."""

import threading
import time


class CommaCarStateReader:
    STALE_AFTER_SECONDS = 2.0
    CAPABILITY_CHECK_SECONDS = 1.0

    def __init__(self):
        # Delay native imports until the opt-in bridge starts.
        import openpilot.cereal.messaging as messaging
        from openpilot.common.params import Params
        from opendbc.car.structs import CarParams
        from opendbc.car.toyota.values import ToyotaFlags

        self._params = Params()
        self._car_params = CarParams
        self._bsm_flag = ToyotaFlags.HAS_BSM
        self._subscriber = messaging.SubMaster(["carState"], poll="carState")
        self._lock = threading.Lock()
        self._latest = None
        self._supported = False
        self._params_blob = None

    def _detect_capability(self):
        blob = self._params.get("CarParams", block=False)
        if blob == self._params_blob:
            return

        supported = False
        if blob:
            try:
                with self._car_params.from_bytes(blob) as params:
                    supported = params.brand == "toyota" and not params.notCar and bool(params.flags & self._bsm_flag)
            except Exception:
                # Malformed or incompatible CarParams must never enable telemetry.
                pass

        with self._lock:
            self._params_blob = blob
            self._supported = supported
            self._latest = None

    def _read_state(self):
        sm = self._subscriber
        sm.update(500)
        with self._lock:
            if not self._supported or not sm.alive["carState"] or not sm.valid["carState"]:
                self._latest = None
            elif sm.updated["carState"]:
                state = sm["carState"]
                self._latest = (
                    bool(state.leftBlindspot),
                    bool(state.rightBlindspot),
                    int(time.time() * 1000),
                    sm.logMonoTime["carState"] / 1e9,
                )

    def run(self):
        next_capability_check = 0.0
        while True:
            now = time.monotonic()
            if now >= next_capability_check:
                try:
                    self._detect_capability()
                except Exception:
                    with self._lock:
                        self._params_blob = None
                        self._supported = False
                        self._latest = None
                next_capability_check = now + self.CAPABILITY_CHECK_SECONDS

            try:
                self._read_state()
            except Exception:
                with self._lock:
                    self._latest = None
                time.sleep(0.25)

    def snapshot(self):
        with self._lock:
            latest = self._latest
            available = latest is not None and 0 <= time.monotonic() - latest[3] <= self.STALE_AFTER_SECONDS
            return {
                "schema": "drivebuddy.blindspot_status.v1",
                "mode": "shadow_only",
                "source": "openpilot.carState",
                "appliedToVehicle": False,
                "available": available,
                "leftBlindspot": latest[0] if available else None,
                "rightBlindspot": latest[1] if available else None,
                "capturedAtMs": latest[2] if available else None,
                "vehicleCapabilityConfirmed": self._supported,
            }
