# Drive Buddy ↔ comma read-only test bridge

**Experimental. Not tested on comma hardware. Do not install over your known-good driving software yet.**

This branch is based on the current upstream development fork, **not** a verified installation of the hardware release. Nothing in this package changes cruise, CAN, throttle, brakes or steering.

## How it works
- Drive Buddy Android debug build POSTs an authenticated advisory to `http://<comma-private-ip>:8765/v1/advisory`.
- It carries the posted speed and an advisory target of **posted + 8 km/h**; no vehicle actuation.
- Drive Buddy polls `/v1/blindspots` and displays left/right signals published by openpilot carState. Missing/stale/unsupported readings return **signal unavailable** and never imply a safe lane.
- The receiver uses a shared token provided in `X-DriveBuddy-Token`; keep the HTTP service on a trusted private Wi-Fi only.

## Test activation
The managed process is configured **off by default** and only starts when explicitly set using environment variables `DRIVEBUDDY_SHADOW_ENABLED=1` and `DRIVEBUDDY_SHADOW_TOKEN=<16+ character token>`. These are development-only test controls; don't expose the service to public networks.

These changes are staged on a feature branch pending hardware-specific build, restart behavior, safe rollout, and rollback validation. There is **no installer URL** yet.

Android companion code: https://github.com/fitzgr/RouteCollector/pull/5
