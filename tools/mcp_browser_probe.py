#!/usr/bin/env python3
"""
Probe for Playwright & MCP browser availability and write canonical evidence.
"""
import json
from pathlib import Path
import sys
EVIDENCE = Path.home() / '.roxy' / 'evidence'
EVIDENCE.mkdir(parents=True, exist_ok=True)
OUT = EVIDENCE / 'browser_probe.json'

report = {
    'playwright_importable': False,
    'chromium_available': False,
    'mcp_module_present': False,
    'mcp_browser_flag': None,
    'errors': []
}

# Check Playwright import
try:
    import playwright
    report['playwright_importable'] = True
except Exception as e:
    report['errors'].append(f'playwright_import_error: {e}')

# Check playwright browser runtime by trying to launch headless chromium
if report['playwright_importable']:
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            # browser.version may be a property or method depending on Playwright version
            try:
                browser_version = browser.version() if callable(browser.version) else browser.version
            except Exception:
                try:
                    browser_version = browser.version
                except Exception:
                    browser_version = None
            browser.close()
            report['chromium_available'] = True
            report['chromium_version'] = browser_version
    except Exception as e:
        report['errors'].append(f'chromium_launch_error: {e}')

# Check mcp_browser module presence and its PLAYWRIGHT_AVAILABLE flag via file inspection
mcp_path = Path.home() / '.roxy' / 'mcp' / 'mcp_browser.py'
if mcp_path.exists():
    report['mcp_module_present'] = True
    # quick grep for PLAYWRIGHT_AVAILABLE assignment
    text = mcp_path.read_text(errors='ignore')
    if 'PLAYWRIGHT_AVAILABLE' in text:
        if "PLAYWRIGHT_AVAILABLE = True" in text:
            report['mcp_browser_flag'] = True
        elif "PLAYWRIGHT_AVAILABLE = False" in text:
            report['mcp_browser_flag'] = False
        else:
            report['mcp_browser_flag'] = None
else:
    report['errors'].append('mcp_module_error: mcp/mcp_browser.py not found')

# Final verdict
report['available'] = report['playwright_importable'] and report['chromium_available'] and report['mcp_module_present'] and bool(report['mcp_browser_flag'])

OUT.write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))

if not report['available']:
    sys.exit(2)
print('Probe OK')
