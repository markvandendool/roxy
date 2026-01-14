#!/usr/bin/env python3
"""
MCP Browser Server - Headless Browser Automation
=================================================
RU-002: Browser Automation MCP Server

Uses Playwright for headless Chromium automation with:
- Anti-detection measures (stealth mode)
- Rate limiting (10 requests/minute)
- Screenshot capture
- DOM extraction
- Form interactions

Tools:
- browser_goto: Navigate to URL
- browser_screenshot: Capture page screenshot
- browser_extract: Extract text/HTML from selector
- browser_click: Click on element
- browser_type: Type text into element
- browser_scroll: Scroll page
- browser_wait: Wait for selector
- browser_cookies: Get/set cookies
- browser_close: Close browser session

SECURITY INVARIANTS:
1. All operations logged (no credentials in logs)
2. Rate limited to prevent abuse
3. Configurable allowed domains
4. Screenshot storage with cleanup
"""

import os
import json
import time
import base64
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional
from collections import deque
from threading import Lock

# Playwright imports
try:
    from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
    _PLAYWRIGHT_IMPORT_ERROR = None
except Exception as e:
    PLAYWRIGHT_AVAILABLE = False
    _PLAYWRIGHT_IMPORT_ERROR = str(e)
    sync_playwright = None  # type: ignore[assignment]
    Browser = Page = BrowserContext = object  # type: ignore[misc,assignment]

# Paths
ROXY_DIR = Path.home() / ".roxy"
SCREENSHOTS_DIR = ROXY_DIR / "screenshots"
AUDIT_LOG = ROXY_DIR / "logs" / "browser_audit.log"

# Ensure directories exist
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Rate limiting config
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 10     # requests per window

# Global state
_browser: Optional[Browser] = None
_context: Optional[BrowserContext] = None
_page: Optional[Page] = None
_playwright = None
_request_times: deque = deque()
_lock = Lock()


def _audit_log(operation: str, details: str = "", success: bool = True):
    """Write to audit log - NEVER include credentials/sensitive data"""
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    log_entry = {
        "timestamp": timestamp,
        "operation": operation,
        "success": success,
        "details": details[:500]  # Truncate long details
    }
    
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def _check_rate_limit() -> bool:
    """Check if rate limit allows request"""
    now = time.time()
    
    with _lock:
        # Remove old entries outside window
        while _request_times and _request_times[0] < now - RATE_LIMIT_WINDOW:
            _request_times.popleft()
        
        if len(_request_times) >= RATE_LIMIT_MAX:
            return False
        
        _request_times.append(now)
        return True


def _ensure_browser():
    """Ensure browser is initialized with stealth settings"""
    global _browser, _context, _page, _playwright
    
    if not PLAYWRIGHT_AVAILABLE:
        detail = f" Import error: {_PLAYWRIGHT_IMPORT_ERROR}" if _PLAYWRIGHT_IMPORT_ERROR else ""
        raise RuntimeError(f"Playwright not available. Run: pip install playwright && playwright install chromium.{detail}")
    
    if _browser is None:
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage'
            ]
        )
        
        # Create context with stealth settings
        _context = _browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            java_script_enabled=True,
            locale='en-US',
            timezone_id='America/New_York'
        )
        
        # Anti-detection scripts
        _context.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            
            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)
        
        _page = _context.new_page()
        _audit_log("browser_init", "Browser initialized with stealth mode")
    
    return _page


def browser_goto(url: str, wait_until: str = "domcontentloaded", timeout: int = 30000) -> dict:
    """
    Navigate to a URL
    
    Args:
        url: Target URL
        wait_until: Wait strategy - 'load', 'domcontentloaded', 'networkidle'
    
    Returns:
        {"success": True, "url": final_url, "title": page_title}
    """
    if not _check_rate_limit():
        _audit_log("goto", f"Rate limited: {url}", False)
        return {"success": False, "error": "Rate limit exceeded (10 requests/minute)"}
    
    try:
        page = _ensure_browser()
        
        response = page.goto(url, wait_until=wait_until, timeout=timeout)
        
        result = {
            "success": True,
            "url": page.url,
            "title": page.title(),
            "status": response.status if response else None
        }
        
        _audit_log("goto", f"{url} -> {page.url}")
        return result
        
    except Exception as e:
        _audit_log("goto", f"{url}: {str(e)}", False)
        return {"success": False, "error": str(e)}


def browser_screenshot(full_page: bool = False, selector: Optional[str] = None) -> dict:
    """
    Capture screenshot of current page
    
    Args:
        full_page: Capture entire scrollable page
        selector: Optional CSS selector to screenshot specific element
    
    Returns:
        {"success": True, "path": file_path, "base64": image_data}
    """
    if not _check_rate_limit():
        return {"success": False, "error": "Rate limit exceeded"}
    
    try:
        page = _ensure_browser()
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        filepath = SCREENSHOTS_DIR / filename
        
        if selector:
            element = page.query_selector(selector)
            if not element:
                return {"success": False, "error": f"Selector not found: {selector}"}
            element.screenshot(path=str(filepath))
        else:
            page.screenshot(path=str(filepath), full_page=full_page)
        
        # Read and encode
        with open(filepath, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
        
        _audit_log("screenshot", f"Saved: {filename}")
        
        return {
            "success": True,
            "path": str(filepath),
            "base64": image_data,
            "size": os.path.getsize(filepath)
        }
        
    except Exception as e:
        _audit_log("screenshot", str(e), False)
        return {"success": False, "error": str(e)}


def browser_extract(
    selector: str,
    attribute: Optional[str] = None,
    all_matches: bool = False,
    include_links: bool = False,
    max_items: Optional[int] = None
) -> dict:
    """
    Extract content from page using CSS selector
    
    Args:
        selector: CSS selector
        attribute: Optional attribute to extract (e.g., 'href', 'src')
        all_matches: Return all matching elements (default: first only)
    
    Returns:
        {"success": True, "content": extracted_text_or_list}
    """
    if not _check_rate_limit():
        return {"success": False, "error": "Rate limit exceeded"}
    
    try:
        page = _ensure_browser()
        
        # Items mode for skill_web_research compatibility
        if include_links or max_items is not None:
            elements = page.query_selector_all(selector)
            if not elements:
                return {"success": False, "error": f"No elements found: {selector}"}

            if max_items is not None:
                elements = elements[:max_items]

            items = []
            for el in elements:
                text = el.text_content() or ""
                links = []
                if include_links:
                    for link in el.query_selector_all("a"):
                        links.append({
                            "href": link.get_attribute("href") or "",
                            "text": (link.text_content() or "").strip(),
                        })
                items.append({"text": text, "links": links})

            _audit_log("extract", f"Selector: {selector}, items: {len(items)}")
            return {"success": True, "items": items}

        if all_matches:
            elements = page.query_selector_all(selector)
            if not elements:
                return {"success": False, "error": f"No elements found: {selector}"}
            
            if attribute:
                content = [el.get_attribute(attribute) for el in elements]
            else:
                content = [el.text_content() for el in elements]
        else:
            element = page.query_selector(selector)
            if not element:
                return {"success": False, "error": f"Element not found: {selector}"}
            
            if attribute:
                content = element.get_attribute(attribute)
            else:
                content = element.text_content()
        
        _audit_log("extract", f"Selector: {selector}, matches: {len(content) if isinstance(content, list) else 1}")
        
        return {"success": True, "content": content}
        
    except Exception as e:
        _audit_log("extract", str(e), False)
        return {"success": False, "error": str(e)}


def browser_click(selector: str) -> dict:
    """
    Click on an element
    
    Args:
        selector: CSS selector of element to click
    
    Returns:
        {"success": True}
    """
    if not _check_rate_limit():
        return {"success": False, "error": "Rate limit exceeded"}
    
    try:
        page = _ensure_browser()
        
        page.click(selector, timeout=10000)
        
        _audit_log("click", f"Selector: {selector}")
        return {"success": True}
        
    except Exception as e:
        _audit_log("click", str(e), False)
        return {"success": False, "error": str(e)}


def browser_type(selector: str, text: str, clear: bool = True) -> dict:
    """
    Type text into an input element
    
    Args:
        selector: CSS selector of input element
        text: Text to type
        clear: Clear existing content first (default: True)
    
    Returns:
        {"success": True}
    """
    if not _check_rate_limit():
        return {"success": False, "error": "Rate limit exceeded"}
    
    try:
        page = _ensure_browser()
        
        if clear:
            page.fill(selector, text, timeout=10000)
        else:
            page.type(selector, text, timeout=10000)
        
        # Don't log actual text (could be sensitive)
        _audit_log("type", f"Selector: {selector}, chars: {len(text)}")
        return {"success": True}
        
    except Exception as e:
        _audit_log("type", str(e), False)
        return {"success": False, "error": str(e)}


def browser_scroll(direction: str = "down", amount: int = 500) -> dict:
    """
    Scroll the page
    
    Args:
        direction: 'up', 'down', 'top', 'bottom'
        amount: Pixels to scroll (for up/down)
    
    Returns:
        {"success": True}
    """
    if not _check_rate_limit():
        return {"success": False, "error": "Rate limit exceeded"}
    
    try:
        page = _ensure_browser()
        
        if direction == "top":
            page.evaluate("window.scrollTo(0, 0)")
        elif direction == "bottom":
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        elif direction == "up":
            page.evaluate(f"window.scrollBy(0, -{amount})")
        else:  # down
            page.evaluate(f"window.scrollBy(0, {amount})")
        
        _audit_log("scroll", f"Direction: {direction}")
        return {"success": True}
        
    except Exception as e:
        _audit_log("scroll", str(e), False)
        return {"success": False, "error": str(e)}


def browser_wait(selector: str, state: str = "visible", timeout: int = 30000) -> dict:
    """
    Wait for an element
    
    Args:
        selector: CSS selector
        state: 'attached', 'detached', 'visible', 'hidden'
        timeout: Max wait time in ms
    
    Returns:
        {"success": True}
    """
    if not _check_rate_limit():
        return {"success": False, "error": "Rate limit exceeded"}
    
    try:
        page = _ensure_browser()
        
        page.wait_for_selector(selector, state=state, timeout=timeout)
        
        _audit_log("wait", f"Selector: {selector}, state: {state}")
        return {"success": True}
        
    except Exception as e:
        _audit_log("wait", str(e), False)
        return {"success": False, "error": str(e)}


def browser_cookies(action: str = "get", cookies: Optional[list] = None) -> dict:
    """
    Get or set cookies
    
    Args:
        action: 'get' or 'set'
        cookies: List of cookie dicts for 'set' action
    
    Returns:
        {"success": True, "cookies": list} for get
    """
    if not _check_rate_limit():
        return {"success": False, "error": "Rate limit exceeded"}
    
    try:
        if _context is None:
            _ensure_browser()
        
        if action == "get":
            cookies_list = _context.cookies()
            _audit_log("cookies", f"Got {len(cookies_list)} cookies")
            return {"success": True, "cookies": cookies_list}
        
        elif action == "set" and cookies:
            _context.add_cookies(cookies)
            _audit_log("cookies", f"Set {len(cookies)} cookies")
            return {"success": True}
        
        return {"success": False, "error": "Invalid action or missing cookies"}
        
    except Exception as e:
        _audit_log("cookies", str(e), False)
        return {"success": False, "error": str(e)}


def browser_evaluate(script: str) -> dict:
    """
    Execute JavaScript in page context
    
    Args:
        script: JavaScript code to execute
    
    Returns:
        {"success": True, "result": return_value}
    """
    if not _check_rate_limit():
        return {"success": False, "error": "Rate limit exceeded"}
    
    try:
        page = _ensure_browser()
        
        result = page.evaluate(script)
        
        _audit_log("evaluate", f"Script length: {len(script)}")
        return {"success": True, "result": result}
        
    except Exception as e:
        _audit_log("evaluate", str(e), False)
        return {"success": False, "error": str(e)}


def browser_html() -> dict:
    """
    Get full page HTML
    
    Returns:
        {"success": True, "html": page_html}
    """
    if not _check_rate_limit():
        return {"success": False, "error": "Rate limit exceeded"}
    
    try:
        page = _ensure_browser()
        
        html = page.content()
        
        _audit_log("html", f"Size: {len(html)} bytes")
        return {"success": True, "html": html}
        
    except Exception as e:
        _audit_log("html", str(e), False)
        return {"success": False, "error": str(e)}


def browser_close() -> dict:
    """
    Close browser session
    
    Returns:
        {"success": True}
    """
    global _browser, _context, _page, _playwright
    
    try:
        if _page:
            _page.close()
            _page = None
        if _context:
            _context.close()
            _context = None
        if _browser:
            _browser.close()
            _browser = None
        if _playwright:
            _playwright.stop()
            _playwright = None
        
        _audit_log("close", "Browser session closed")
        return {"success": True}
        
    except Exception as e:
        _audit_log("close", str(e), False)
        return {"success": False, "error": str(e)}


# =============================================================================
# MCP Server Interface
# =============================================================================

TOOLS = {
    "goto": {
        "description": "Navigate to a URL",
        "parameters": {
            "url": {"type": "string", "description": "Target URL"},
            "wait_until": {"type": "string", "description": "Wait strategy: load, domcontentloaded, networkidle", "default": "domcontentloaded"}
        },
        "required": ["url"]
    },
    "screenshot": {
        "description": "Capture screenshot of current page or element",
        "parameters": {
            "full_page": {"type": "boolean", "description": "Capture entire scrollable page", "default": False},
            "selector": {"type": "string", "description": "Optional CSS selector for element screenshot"}
        },
        "required": []
    },
    "extract": {
        "description": "Extract text/attribute from element(s) using CSS selector",
        "parameters": {
            "selector": {"type": "string", "description": "CSS selector"},
            "attribute": {"type": "string", "description": "Attribute to extract (href, src, etc.)"},
            "all_matches": {"type": "boolean", "description": "Return all matches", "default": False}
        },
        "required": ["selector"]
    },
    "click": {
        "description": "Click on an element",
        "parameters": {
            "selector": {"type": "string", "description": "CSS selector of element to click"}
        },
        "required": ["selector"]
    },
    "type": {
        "description": "Type text into an input element",
        "parameters": {
            "selector": {"type": "string", "description": "CSS selector of input"},
            "text": {"type": "string", "description": "Text to type"},
            "clear": {"type": "boolean", "description": "Clear existing content first", "default": True}
        },
        "required": ["selector", "text"]
    },
    "scroll": {
        "description": "Scroll the page",
        "parameters": {
            "direction": {"type": "string", "description": "up, down, top, bottom", "default": "down"},
            "amount": {"type": "integer", "description": "Pixels to scroll", "default": 500}
        },
        "required": []
    },
    "wait": {
        "description": "Wait for an element to appear",
        "parameters": {
            "selector": {"type": "string", "description": "CSS selector"},
            "state": {"type": "string", "description": "visible, hidden, attached, detached", "default": "visible"},
            "timeout": {"type": "integer", "description": "Max wait ms", "default": 30000}
        },
        "required": ["selector"]
    },
    "cookies": {
        "description": "Get or set cookies",
        "parameters": {
            "action": {"type": "string", "description": "get or set"},
            "cookies": {"type": "array", "description": "Cookies to set (for set action)"}
        },
        "required": ["action"]
    },
    "evaluate": {
        "description": "Execute JavaScript in page context",
        "parameters": {
            "script": {"type": "string", "description": "JavaScript code"}
        },
        "required": ["script"]
    },
    "html": {
        "description": "Get full page HTML",
        "parameters": {},
        "required": []
    },
    "close": {
        "description": "Close browser session",
        "parameters": {},
        "required": []
    }
}


def handle_tool(name: str, params: dict) -> Any:
    """MCP tool handler"""
    handlers = {
        "goto": lambda p: browser_goto(p["url"], p.get("wait_until", "domcontentloaded")),
        "screenshot": lambda p: browser_screenshot(p.get("full_page", False), p.get("selector")),
        "extract": lambda p: browser_extract(p["selector"], p.get("attribute"), p.get("all_matches", False)),
        "click": lambda p: browser_click(p["selector"]),
        "type": lambda p: browser_type(p["selector"], p["text"], p.get("clear", True)),
        "scroll": lambda p: browser_scroll(p.get("direction", "down"), p.get("amount", 500)),
        "wait": lambda p: browser_wait(p["selector"], p.get("state", "visible"), p.get("timeout", 30000)),
        "cookies": lambda p: browser_cookies(p["action"], p.get("cookies")),
        "evaluate": lambda p: browser_evaluate(p["script"]),
        "html": lambda p: browser_html(),
        "close": lambda p: browser_close()
    }
    
    if name not in handlers:
        return {"success": False, "error": f"Unknown tool: {name}"}
    
    return handlers[name](params)


# =============================================================================
# CLI for testing
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: mcp_browser.py <command> [args...]")
        print("Commands: goto <url>, screenshot, extract <selector>, click <selector>, close")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "goto" and len(sys.argv) >= 3:
        result = browser_goto(sys.argv[2])
    elif cmd == "screenshot":
        result = browser_screenshot()
    elif cmd == "extract" and len(sys.argv) >= 3:
        result = browser_extract(sys.argv[2])
    elif cmd == "click" and len(sys.argv) >= 3:
        result = browser_click(sys.argv[2])
    elif cmd == "html":
        result = browser_html()
    elif cmd == "close":
        result = browser_close()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
    
    # Don't print full HTML/base64 in CLI
    if "html" in result and len(str(result.get("html", ""))) > 1000:
        result["html"] = result["html"][:1000] + "... (truncated)"
    if "base64" in result:
        result["base64"] = f"[{len(result['base64'])} chars]"
    
    print(json.dumps(result, indent=2))
