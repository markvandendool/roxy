#!/usr/bin/env bash
set -euo pipefail

# Balanced baseline for thermal stability and consistent responsiveness.
# Intended to run as root via systemd.

log() {
  echo "[balanced-baseline] $*"
}

log "applying balanced power profile"
if command -v powerprofilesctl >/dev/null 2>&1; then
  powerprofilesctl set balanced >/dev/null 2>&1 || true
fi

log "unlocking CPU frequency floor"
if [ -w /sys/devices/system/cpu/intel_pstate/min_perf_pct ]; then
  echo 20 > /sys/devices/system/cpu/intel_pstate/min_perf_pct || true
fi
if [ -w /sys/devices/system/cpu/intel_pstate/max_perf_pct ]; then
  echo 100 > /sys/devices/system/cpu/intel_pstate/max_perf_pct || true
fi
if [ -w /sys/devices/system/cpu/intel_pstate/no_turbo ]; then
  echo 0 > /sys/devices/system/cpu/intel_pstate/no_turbo || true
fi

for p in /sys/devices/system/cpu/cpufreq/policy*; do
  [ -d "$p" ] || continue

  if [ -w "$p/scaling_governor" ]; then
    echo powersave > "$p/scaling_governor" || true
  fi

  if [ -r "$p/cpuinfo_min_freq" ] && [ -w "$p/scaling_min_freq" ]; then
    min_freq=$(cat "$p/cpuinfo_min_freq" 2>/dev/null || true)
    [ -n "${min_freq:-}" ] && echo "$min_freq" > "$p/scaling_min_freq" || true
  fi

  if [ -r "$p/cpuinfo_max_freq" ] && [ -w "$p/scaling_max_freq" ]; then
    max_freq=$(cat "$p/cpuinfo_max_freq" 2>/dev/null || true)
    [ -n "${max_freq:-}" ] && echo "$max_freq" > "$p/scaling_max_freq" || true
  fi

  if [ -w "$p/energy_performance_preference" ]; then
    echo balance_performance > "$p/energy_performance_preference" || true
  fi
done

log "setting GPU power modes"
if [ -w /sys/class/drm/card0/device/power_dpm_force_performance_level ]; then
  echo auto > /sys/class/drm/card0/device/power_dpm_force_performance_level || true
fi
if [ -w /sys/class/drm/card1/device/power_dpm_force_performance_level ]; then
  echo low > /sys/class/drm/card1/device/power_dpm_force_performance_level || true
fi

log "restoring GPU automatic fan control"
for pwm_enable in /sys/class/drm/card*/device/hwmon/hwmon*/pwm1_enable; do
  [ -w "$pwm_enable" ] || continue
  echo 2 > "$pwm_enable" || true

done

log "balanced baseline applied"
