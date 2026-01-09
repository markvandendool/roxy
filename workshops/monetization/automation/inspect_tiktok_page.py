#!/usr/bin/env /home/mark/llm-benchmarks/venv/bin/python
"""
Inspect TikTok upload page to get REAL selectors
"""
from playwright.sync_api import sync_playwright
import json

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    print("📱 Loading TikTok upload page...")
    page.goto("https://www.tiktok.com/upload", wait_until="networkidle")
    
    input("\n⏸️  Press Enter after page loads fully (wait for any popups to appear)...")
    
    print("\n🔍 INSPECTING PAGE STRUCTURE...")
    
    # Get file input
    file_inputs = page.locator('input[type="file"]').all()
    print(f"\n📎 File inputs found: {len(file_inputs)}")
    for i, inp in enumerate(file_inputs):
        attrs = inp.evaluate("el => ({id: el.id, name: el.name, class: el.className})")
        print(f"  [{i}] {attrs}")
    
    # Get all buttons
    buttons = page.locator('button').all()
    print(f"\n🔘 Buttons found: {len(buttons)}")
    for i, btn in enumerate(buttons[:20]):  # First 20
        try:
            text = btn.inner_text()[:50]
            attrs = btn.evaluate("el => ({id: el.id, class: el.className, type: el.type})")
            print(f"  [{i}] '{text}' - {attrs}")
        except:
            pass
    
    # Get textareas
    textareas = page.locator('textarea').all()
    print(f"\n📝 Textareas found: {len(textareas)}")
    for i, ta in enumerate(textareas):
        attrs = ta.evaluate("el => ({id: el.id, placeholder: el.placeholder, class: el.className})")
        print(f"  [{i}] {attrs}")
    
    # Get all divs with contenteditable
    editables = page.locator('[contenteditable="true"]').all()
    print(f"\n✏️  Contenteditable elements: {len(editables)}")
    for i, el in enumerate(editables):
        attrs = el.evaluate("el => ({tag: el.tagName, class: el.className, role: el.role})")
        print(f"  [{i}] {attrs}")
    
    # Screenshot for reference
    page.screenshot(path="/tmp/tiktok_upload_page.png")
    print(f"\n📸 Screenshot saved to /tmp/tiktok_upload_page.png")
    
    # Save full HTML for analysis
    html = page.content()
    with open("/tmp/tiktok_upload_page.html", "w") as f:
        f.write(html)
    print(f"📄 HTML saved to /tmp/tiktok_upload_page.html")
    
    input("\n⏸️  Press Enter to close browser...")
    browser.close()
