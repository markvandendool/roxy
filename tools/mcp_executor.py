#!/usr/bin/env python3
"""
MCP JSON plan executor using Playwright sync API.
- Write artifacts to evidence dir
- Dry-run mode: block destructive submits
"""
import json
import argparse
import time
from pathlib import Path
from typing import Dict, Any

EVIDENCE_ROOT = Path.home() / '.roxy' / 'evidence' / 'browser_runs'
EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)

DANGEROUS_SELECTORS = ['input[type=submit]', 'button[type=submit]', 'form']

parser = argparse.ArgumentParser()
parser.add_argument('plan', help='JSON plan file')
parser.add_argument('--dry-run', action='store_true', help='Do not perform destructive actions')
args = parser.parse_args()

plan = json.loads(Path(args.plan).read_text())

# Load credentials from secure local file if present and substitute placeholders
creds_path = Path.home() / '.roxy' / 'credentials' / 'tuya.json'
creds = {}
if creds_path.exists():
    try:
        creds = json.loads(creds_path.read_text())
    except Exception:
        creds = {}

# Substitute any <<vault:key>> placeholders in plan
def substitute_placeholders(obj):
    if isinstance(obj, dict):
        return {k: substitute_placeholders(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [substitute_placeholders(x) for x in obj]
    if isinstance(obj, str):
        if obj.startswith('<<vault:') and obj.endswith('>>'):
            key = obj[len('<<vault:'):-2]
            return creds.get(key, obj)
        return obj
    return obj

plan = substitute_placeholders(plan)

run_ts = time.strftime('%Y%m%dT%H%M%SZ')
run_dir = EVIDENCE_ROOT / f'run_{run_ts}'
run_dir.mkdir(parents=True)
(screens_dir := (run_dir / 'screens')).mkdir()
(html_dir := (run_dir / 'html')).mkdir()
runlog = []

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context()
    page = context.new_page()

    step_idx = 0
    for step in plan:
        step_idx += 1
        action = step.get('cmd')
        rec = {'step': step_idx, 'action': action, 'detail': step, 'time': time.time()}
        try:
            # Pre-action: detect common captcha elements
            try:
                captcha_selectors = ['iframe[src*="recaptcha"]', '.g-recaptcha', '.h-captcha', 'input[name="captcha"]', 'div.recaptcha']
                for cs in captcha_selectors:
                    el = page.query_selector(cs)
                    if el:
                        rec['error'] = 'captcha_detected'
                        rec['captcha_selector'] = cs
                        rec['result'] = 'human_action_required'
                        runlog.append(rec)
                        print(json.dumps(rec))
                        raise SystemExit('CAPTCHA detected; human action required')
            except SystemExit:
                raise
            except Exception:
                # ignore DOM detection errors
                pass

            if action == 'goto':
                url = step['url']
                page.goto(url, wait_until=step.get('wait_until', 'domcontentloaded'))
                rec['result'] = 'ok'

            elif action == 'wait':
                selector = step['selector']
                state = step.get('state', 'visible')
                page.wait_for_selector(selector, timeout=step.get('timeout', 30000), state=state)
                rec['result'] = 'ok'

            elif action == 'type':
                sel = step['selector']
                text = step['text']
                if args.dry_run:
                    rec['result'] = f'dry-run: would type into {sel}'
                else:
                    page.fill(sel, text)
                    rec['result'] = 'ok'

            elif action == 'click':
                sel = step['selector']
                # Basic heuristic: if selector mentions known destructive keywords, treat as destructive
                destructive_keywords = ['submit', 'delete', 'confirm', 'buy', 'remove']
                is_danger = any(k in sel.lower() for k in destructive_keywords)
                if is_danger and args.dry_run:
                    rec['result'] = f'dry-run: blocked destructive click {sel}'
                else:
                    page.click(sel)
                    rec['result'] = 'ok'

            elif action == 'find_and_click':
                text = step['text']
                scope = step.get('selector', 'body')
                nodes = page.query_selector_all(scope)
                found = False
                for n in nodes:
                    try:
                        txt = n.inner_text()
                        if text in txt:
                            # click the element
                            if args.dry_run and any(k in txt.lower() for k in ['delete', 'confirm', 'buy', 'remove']):
                                rec['result'] = f'dry-run: blocked destructive click on node with text {text}'
                                found = True
                                break
                            n.click()
                            rec['clicked_text'] = text
                            rec['result'] = 'ok'
                            found = True
                            break
                    except Exception:
                        continue
                if not found:
                    rec['result'] = 'not_found'

            elif action == 'assert_text':
                text = step['text']
                body = page.inner_text('body')
                rec['found'] = text in body
                rec['result'] = 'ok' if rec['found'] else 'not_found'

            elif action == 'screenshot':
                filename = screens_dir / f'step_{step_idx:03d}.png'
                page.screenshot(path=str(filename), full_page=step.get('full_page', False))
                rec['screenshot'] = str(filename)
                rec['result'] = 'ok'

            elif action == 'html':
                filename = html_dir / f'step_{step_idx:03d}.html'
                filename.write_text(page.content())
                rec['html'] = str(filename)
                rec['result'] = 'ok'

            elif action == 'extract':
                sel = step['selector']
                attr = step.get('attribute')
                nodes = page.query_selector_all(sel)
                out = []
                for n in nodes:
                    try:
                        if attr:
                            out.append(n.get_attribute(attr))
                        else:
                            out.append(n.inner_text())
                    except Exception:
                        out.append(None)
                rec['extracted'] = out
                rec['result'] = 'ok'

            elif action == 'evaluate':
                script = step['script']
                res = page.evaluate(script)
                rec['result'] = res

            elif action == 'close':
                rec['result'] = 'closing'
                break

            else:
                rec['result'] = f'unknown action {action}'
        except SystemExit as se:
            # Critical stop (e.g., CAPTCHA) -- write runlog and re-raise
            runlog.append(rec)
            print(json.dumps(rec))
            raise
        except Exception as e:
            rec['error'] = str(e)
        print(json.dumps(rec))
        runlog.append(rec)

    # final screenshot
    final_shot = screens_dir / 'final.png'
    page.screenshot(path=str(final_shot), full_page=True)
    runlog.append({'final_screenshot': str(final_shot)})
    context.close()
    browser.close()

# write runlog
(Path(run_dir) / 'runlog.json').write_text(json.dumps(runlog, indent=2))
print('Run completed. Artifacts in', run_dir)
