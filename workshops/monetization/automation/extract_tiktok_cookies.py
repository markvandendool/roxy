#!/usr/bin/env /home/mark/llm-benchmarks/venv/bin/python
"""
Extract TikTok cookies from running Chrome session
No manual export needed - grabs directly from Chrome's cookie DB
"""
import sqlite3
import os
import json
from pathlib import Path
import shutil

# Chrome cookie locations
CHROME_COOKIES = Path.home() / ".config/google-chrome/Default/Cookies"
OUTPUT_FILE = Path.home() / ".roxy/workshops/monetization/.tiktok_cookies.json"

def get_chrome_cookies():
    """Extract TikTok cookies from Chrome"""
    
    # Copy to temp (Chrome locks the file)
    temp_db = "/tmp/chrome_cookies_copy.db"
    shutil.copy2(CHROME_COOKIES, temp_db)
    
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    
    # Query TikTok cookies
    cursor.execute("""
        SELECT name, value, host_key, path, expires_utc, is_secure, is_httponly
        FROM cookies
        WHERE host_key LIKE '%tiktok.com%'
    """)
    
    cookies = []
    for row in cursor.fetchall():
        cookies.append({
            "name": row[0],
            "value": row[1],
            "domain": row[2],
            "path": row[3],
            "expires": row[4],
            "secure": bool(row[5]),
            "httpOnly": bool(row[6])
        })
    
    conn.close()
    os.remove(temp_db)
    
    return cookies

if __name__ == "__main__":
    print("🍪 Extracting TikTok cookies from Chrome...")
    
    if not CHROME_COOKIES.exists():
        print(f"❌ Chrome cookies not found at {CHROME_COOKIES}")
        print("   Make sure Chrome is closed or use different browser")
        exit(1)
    
    cookies = get_chrome_cookies()
    
    if not cookies:
        print("❌ No TikTok cookies found. Make sure you're logged in.")
        exit(1)
    
    # Save cookies
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(cookies, f, indent=2)
    
    OUTPUT_FILE.chmod(0o600)
    
    print(f"✅ Extracted {len(cookies)} TikTok cookies")
    print(f"📁 Saved to: {OUTPUT_FILE}")
    print(f"🔒 Permissions: 600 (secure)")
    
    # Show key cookies
    key_cookies = [c['name'] for c in cookies if c['name'] in ['sessionid', 'sid_tt', 'msToken']]
    if key_cookies:
        print(f"🔑 Found auth cookies: {', '.join(key_cookies)}")
    else:
        print("⚠️  No auth cookies found - you may not be logged in")
