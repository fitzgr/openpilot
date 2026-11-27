#!/usr/bin/env bash

export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1

# models get lower priority than ui
# - ui is ~5ms
# - modeld is 20ms
# - DM is 10ms
# in order to run ui at 60fps (16.67ms), we need to allow
# it to preempt the model workloads. we have enough
# headroom for this until ui is moved to the CPU.
export QCOM_PRIORITY=12

if [ -z "$AGNOS_VERSION" ]; then
  export AGNOS_VERSION="19.9"
fi

export STAGING_ROOT="/data/safe_staging"

# Drive Buddy hardware bench test only. Keep this marker absent for driving.
# The local token is deliberately outside the repository; never log its value.
# The bridge remains disabled unless explicitly opted in.
if [[ -f /data/drivebuddy-test/enable && -f /data/drivebuddy-test/token && -r /data/drivebuddy-test/token ]]; then
  if [[ "$(stat -c '%a' /data/drivebuddy-test/token 2>/dev/null)" == "600" ]]; then
    DRIVEBUDDY_SHADOW_TOKEN=$(< /data/drivebuddy-test/token)
    if [[ ${#DRIVEBUDDY_SHADOW_TOKEN} -ge 16 && "$DRIVEBUDDY_SHADOW_TOKEN" =~ ^[[:graph:]]+$ ]]; then
      export DRIVEBUDDY_SHADOW_TOKEN
      export DRIVEBUDDY_SHADOW_ENABLED=1
    else
      unset DRIVEBUDDY_SHADOW_TOKEN
    fi
  fi
fi
