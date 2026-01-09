#!/usr/bin/env python3
"""Simple runbook executor for ROXY (dry-run default).
Supported tools (initial):
 - exec: runs a command (command, args)
 - tuya: calls ha-integration/tuya-control.py on/off
 - obs_ws / obs_ws_send: uses Roxy's OBSController if available (best-effort)
 - output: print a message

Usage:
  ./runbook_executor.py --run ~/.roxy/runbooks/warmup_studio.yaml --dry-run
  ./runbook_executor.py --run ... --live --yes
"""
from __future__ import annotations
import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

RUNBOOK_P = Path(sys.argv[0]).parent.parent / 'runbooks'


def simple_yaml_load(path: Path) -> Dict[str, Any]:
    """Minimal YAML loader for our simple runbook format (safe fallback).
    Expects simple mapping and a top-level list under 'steps:'."""
    data = {'steps': []}
    cur = None
    with path.open() as f:
        for raw in f:
            line = raw.rstrip('\n')
            if not line.strip() or line.strip().startswith('#'):
                continue
            if line.startswith('name:') and 'name:' in line:
                if not data.get('name'):
                    data['name'] = line.split(':', 1)[1].strip().strip('"')
            if line.strip().startswith('- name:'):
                cur = {'name': line.split(':', 1)[1].strip().strip('"')}
                data['steps'].append(cur)
                continue
            if cur is None:
                continue
            # very simple key: value pairs 2-space indent
            if line.startswith('    ') or line.startswith('  '):
                kv = line.strip()
                if ':' in kv:
                    k, v = kv.split(':', 1)
                    key = k.strip()
                    val = v.strip()
                    # simple list handling
                    if val.startswith('[') and val.endswith(']'):
                        items = [x.strip().strip('"') for x in val[1:-1].split(',') if x.strip()]
                        cur[key] = items
                    elif val.startswith('{') and val.endswith('}'):
                        cur[key] = val
                    elif val == 'true' or val == 'True':
                        cur[key] = True
                    elif val == 'false' or val == 'False':
                        cur[key] = False
                    elif val.startswith('"') and val.endswith('"'):
                        cur[key] = val.strip('"')
                    else:
                        # try int
                        try:
                            cur[key] = int(val)
                        except:
                            cur[key] = val
    return data


class RunbookExecutor:
    def __init__(self, runbook_path: Path, dry_run: bool = True, yes: bool = False):
        self.runbook_path = runbook_path
        self.dry_run = dry_run
        self.yes = yes
        self.runbook = self._load()

    def _load(self) -> Dict[str, Any]:
        try:
            import yaml
            with self.runbook_path.open() as f:
                return yaml.safe_load(f)
        except Exception:
            # fallback
            return simple_yaml_load(self.runbook_path)

    def _log(self, msg: str) -> None:
        print(msg)

    def _do_exec(self, args: Dict[str, Any]):
        cmd = args.get('command')
        cmd_args = args.get('args', []) or []
        if self.dry_run:
            self._log(f"[DRY] exec: {cmd} {' '.join(map(str,cmd_args))}")
            return True
        self._log(f"exec: {cmd} {' '.join(map(str,cmd_args))}")
        try:
            result = subprocess.run([cmd] + list(cmd_args), capture_output=True, text=True, timeout=60)
            self._log(result.stdout)
            return result.returncode == 0
        except Exception as e:
            self._log(f"exec error: {e}")
            return False

    def _do_tuya(self, args: Dict[str, Any]):
        device = args.get('device') or args.get('name')
        if self.dry_run:
            self._log(f"[DRY] tuya: turn ON {device}")
            return True
        script = Path(__file__).parent.parent / 'ha-integration' / 'tuya-control.py'
        cmd = ['python3', str(script), 'on', device]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            self._log(r.stdout)
            return 'Success' in r.stdout
        except Exception as e:
            self._log(f"tuya error: {e}")
            return False

    def _do_obs_ws(self, args: Dict[str, Any]):
        if self.dry_run:
            self._log(f"[DRY] obs_ws connect {args}")
            return True
        # try to use Roxy's OBSController
        try:
            from . import ha_integration  # not used, keep safe import
        except Exception:
            pass
        try:
            from .ha_integration.roxy_hardware import OBSController
        except Exception:
            try:
                from .roxy_hardware import OBSController
            except Exception:
                OBSController = None
        if not OBSController:
            self._log("OBSController not available; install websocket-client and ensure roxy_hardware is importable")
            return False
        obs = OBSController(host=args.get('host', '127.0.0.1'), port=int(args.get('port', 4455)))
        ok = obs.connect()
        self._log(f"OBS connect: {ok}")
        return ok

    def _do_obs_ws_send(self, args: Dict[str, Any]):
        if self.dry_run:
            self._log(f"[DRY] obs_ws_send: {args}")
            return True
        try:
            from .roxy_hardware import OBSController
            obs = OBSController(host=args.get('host', '127.0.0.1'), port=int(args.get('port', 4455)))
            if not obs.connect():
                return False
            req_type = args.get('requestType') or args.get('op')
            data = args.get('requestData') or args.get('requestData') or args
            resp = obs._send_request(req_type, data if isinstance(data, dict) else None)
            self._log(f"OBS resp: {resp}")
            return True
        except Exception as e:
            self._log(f"obs_ws_send error: {e}")
            return False

    def _do_output(self, args: Dict[str, Any]):
        msg = args.get('message') or args.get('output')
        if msg:
            self._log(msg)
            return True
        return False

    def step(self, s: Dict[str, Any]) -> bool:
        name = s.get('name')
        tool = s.get('tool')
        args = s.get('args', {}) or {}
        self._log(f"== Step: {name} (tool={tool}) ==")
        if tool == 'exec':
            return self._do_exec(args)
        if tool == 'tuya':
            return self._do_tuya(args)
        if tool == 'obs_ws':
            return self._do_obs_ws(args)
        if tool == 'obs_ws_send':
            return self._do_obs_ws_send(args)
        if tool == 'output':
            return self._do_output(args)
        self._log(f"Unknown tool: {tool}")
        return False

    def run(self):
        steps: List[Dict[str, Any]] = self.runbook.get('steps', [])
        self._log(f"Runbook: {self.runbook.get('name','<unnamed>')} ({'DRY' if self.dry_run else 'LIVE'})")
        for s in steps:
            ok = self.step(s)
            if not ok:
                self._log(f"STEP FAILED: {s.get('name')}")
                return False
            # support wait
            w = s.get('wait') or s.get('sleep')
            if w:
                time.sleep(int(w))
        self._log("Runbook finished")
        return True


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--run', '-r', required=True, help='Path to runbook YAML')
    p.add_argument('--live', action='store_true', help='Execute live (not dry-run)')
    p.add_argument('--yes', action='store_true', help='Confirm live execution')
    args = p.parse_args()

    path = Path(args.run).expanduser()
    if not path.exists():
        print(f"Runbook not found: {path}")
        sys.exit(2)

    rb = RunbookExecutor(path, dry_run=not args.live, yes=args.yes)
    if args.live and not args.yes:
        print("Live mode requires --yes to confirm. Aborting.")
        sys.exit(3)
    ok = rb.run()
    sys.exit(0 if ok else 4)