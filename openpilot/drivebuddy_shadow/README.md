# Drive Buddy read-only bridge for comma four

Stage 1 uses comma's prebuilt `release-mici` v0.11.2 tree at
[`f7db927`](https://github.com/commaai/openpilot/commit/f7db927c728bab57bb1263e05465766a8f28fc9d).
The candidate uses the release's ARM64 binaries, Python 3.12.13, AGNOS 19.9 and
vendored opendbc and msgq. The bridge is off by default.

- Drive Buddy Android sends an authenticated advisory to
  `http://<comma-private-ip>:8765/v1/advisory`. The advisory target is the
  captured posted speed plus 8 km/h. It is logged as data only.
- `GET /v1/blindspots` exposes the release's left and right `carState` fields
  for a Toyota with the opendbc `HAS_BSM` flag. Missing capability, invalid
  messages, or stale messages produce unavailable readings.
- Both endpoints require `X-DriveBuddy-Token`. The bridge never publishes
  openpilot messages, writes CAN frames, or changes vehicle controls.
  Android companion code is in [RouteCollector PR #5](https://github.com/fitzgr/RouteCollector/pull/5).

## Stage 1 validation

The branch workflow runs the shadow HTTP protocol tests and a Linux host
integration test. The integration test starts and restarts the real
`PythonProcess` launcher, uses the host-built msgq extension and release
Cap'n Proto schemas, and sends synthetic `carState` messages to the bridge.
A temporary file supplies serialized `CarParams` in place of the device's
ARM64 Params library. The test checks Toyota capability, both sides, invalid
and stale messages, missing capability, and HTTP authentication.

The 2024 Toyota RAV4 is covered by the baseline's RAV4 2023–25 platform
definition. Live fingerprinting, reception of the BSM CAN message, on-device
startup and rollback are pending an approved hardware session.

## Install candidate after approval

1. Record the currently installed software and preserve any locally stored
   data you need. Keep the comma four on bench power with the vehicle harness
   disconnected for the install and first boot.
2. From comma four's Software settings, use **uninstall openpilot** to return
   to setup. Connect to Wi-Fi and choose **Custom Software**. Enter:

   ```text
   https://installer.comma.ai/fitzgr/test/drivebuddy-release-mici
   ```

3. Let setup finish, then verify the booted branch and compare
   `git -C /data/openpilot rev-parse HEAD` over SSH with the approved candidate
   SHA. The installer follows the branch head at install time. Leave the
   bridge disabled for first boot. Confirm the UI starts and port 8765 is closed.
4. Before any separately approved vehicle-connected check, turn off **enable
   openpilot** in Toggles while offroad and follow the restart prompt. Keep
   that setting off throughout the telemetry check. Validate a bench session
   first and keep this candidate out of driving service.

The URL was checked off-device using the setup request's AGNOS user agent and
`mici` device-type header. The response was an ARM64 ELF installer with the
fork URL and exact branch embedded. Download validation does not execute the
installer or establish first-boot compatibility.

## Enable the bridge for an approved test

Set `DRIVEBUDDY_SHADOW_ENABLED=1` and `DRIVEBUDDY_SHADOW_TOKEN` (a randomly
generated ASCII token, at least 16 characters) in the test manager's
environment before starting it. Configure Drive Buddy with the same token.
Port 8765 serves plain HTTP on all IPv4 interfaces, so use an isolated,
trusted Wi-Fi network without port forwarding. Confirm authenticated
`/v1/status` reports `appliedToVehicle: false` and an unauthenticated request
returns HTTP 401. With no on-road Toyota telemetry, `/v1/blindspots` should
return `available: false` and null left/right readings. Treat unavailable
readings as missing data.

## Roll back

1. Stop the test and switch Drive Buddy away from the candidate. Remove any
   bridge environment configuration and restart the manager to disable it.
2. On the comma four, use **uninstall openpilot** in Software settings, then
   enter `https://openpilot.comma.ai` in setup to install comma's current
   official release. Verify the official branch boots and the bridge port is
   closed before reconnecting the vehicle harness. The official URL tracks
   current releases.
3. If the UI is unusable, use [comma's factory flashing
   procedure](https://comma.ai/support/flash-your-comma), then reinstall stock
   openpilot. Factory flashing erases on-device software and data.
