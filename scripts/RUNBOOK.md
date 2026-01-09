# SDMA Repro Runbook

## Goal
Reproduce the SDMA0 ring timeout + gfxhub page fault signature observed in the amdgpu devcoredumps, while isolating Thunderbolt (TB) involvement.

## Modes
- MODE A (TB-min): disconnect or power down TB devices/docks, keep only essential devices.
- MODE B (TB-on): reintroduce TB devices one-by-one (dock, NVMe, display), run the same script each time.

## Pre-flight checks
1) Confirm target GPU is the NAVI10 / W5700X:
   - `lspci -nnk | egrep -A3 -B1 'VGA|Display|AMD'`
2) Verify GPU selection proof (script enforces this):
   - `DRI_PRIME=pci-0000_09_00_0 glxinfo -B` should show NAVI10/W5700X
3) Make sure an X session is active (DISPLAY set).

## Script
- Script: `~/.roxy/scripts/sdma_repro.sh`
- Evidence: `~/.roxy/evidence/sdma_repro_YYYYMMDD_HHMMSS/`
  - `pre_state.txt` includes TB status, render-node mapping, and baseline counts
  - `gpu_bind.log` shows which `/dev/dri/renderD*` the stress process opened

### Default stages (auto)
- Stage 0: 60s
- Stage 1: 5m
- Stage 2: 15m
- Stage 3: 45m (run only after manual review; set `STAGES_SPEC=60,300,900,2700`)

## Run commands
MODE A (TB-min):
```
MODE=A TB_STATUS=unplugged TB_ATTEST_START="operator_attested_start" TB_ATTEST_END="operator_attested_end" \
  TARGET_BDF=0000:09:00.0 DRI_PRIME=pci-0000_09_00_0 \
  ~/.roxy/scripts/sdma_repro.sh
```

MODE B (TB-on), each device added:
```
MODE=B TB_STATUS=plugged TB_ATTEST_START="operator_attested_start" TB_ATTEST_END="operator_attested_end" \
  TARGET_BDF=0000:09:00.0 DRI_PRIME=pci-0000_09_00_0 \
  ~/.roxy/scripts/sdma_repro.sh
```

## Environment overrides
- `STAGES_SPEC=60,300,900,2700` (seconds per stage)
- `TB_STATUS=unplugged|plugged|unknown` (operator note)
- `TB_ATTEST_START=...` and `TB_ATTEST_END=...` (operator attestation strings)
- `GPU_TEX_SIZE=8192` (stress-ng GPU texture size)
- `GPU_UPLOAD=16` (upload count)
- `GPU_FRAG=1` (shader usage per pixel)
- `WINDOW_SECS=30` (kernel log window)
- `POLL_SECS=5` (monitor cadence)
- `GPU_PROOF_PATTERN='NAVI10|W5700X|Navi 10|Radeon Pro W5700X'`
- `ROXY_HEALTH_URL=http://127.0.0.1:8766/health` (optional)

## Abort gates (automatic)
Any of the following will abort and mark FAIL:
- New devcoredump directory
- New kernel lines matching: sdma, ring timeout, gfxhub, vm_fault, page fault, GPU reset, amdgpu.*hang
- Any new AER/BadTLP lines (if AER logging is enabled)
- Optional: ROXY health check failure (if configured)

## PASS/FAIL criteria
PASS:
- No new devcoredumps
- No hard fault keywords in kernel window
- No AER/BadTLP lines

FAIL:
- Any of the abort gate conditions
- Script reports first failure line and stage in `verdict.txt`

## Notes / limitations
- stress-ng --gpu is a GL workload; it may not isolate SDMA as purely as a DMA-only test. This is a proxy for DMA pressure via uploads and texture operations.
- Journal retention is limited; devcoredump binaries are the canonical fault evidence.
