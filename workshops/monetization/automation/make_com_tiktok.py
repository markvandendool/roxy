#!/usr/bin/env /home/mark/llm-benchmarks/venv/bin/python
"""
Make.com TikTok Upload Integration
===================================
Zero-human automation via Make.com webhook
"""

import requests
import base64
import json
from pathlib import Path
import sys

CREDENTIALS_FILE = Path.home() / ".roxy/workshops/monetization/.credentials.json"

def load_credentials():
    """Load Make.com webhook URL from credentials"""
    if CREDENTIALS_FILE.exists():
        with open(CREDENTIALS_FILE) as f:
            creds = json.load(f)
            return creds.get("api_keys", {}).get("make_com", {})
    return {}

def save_webhook_url(webhook_url):
    """Save Make.com webhook URL to credentials"""
    if CREDENTIALS_FILE.exists():
        with open(CREDENTIALS_FILE) as f:
            creds = json.load(f)
    else:
        creds = {"api_keys": {}}
    
    if "api_keys" not in creds:
        creds["api_keys"] = {}
    if "make_com" not in creds["api_keys"]:
        creds["api_keys"]["make_com"] = {}
    
    creds["api_keys"]["make_com"]["tiktok_webhook"] = webhook_url
    
    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(creds, f, indent=2)
    
    print(f"✅ Saved webhook URL to {CREDENTIALS_FILE}")

def upload_to_tiktok_via_make(video_path, caption, webhook_url=None):
    """
    Upload video to TikTok via Make.com webhook
    
    Args:
        video_path: Path to video file
        caption: Video caption/description
        webhook_url: Make.com webhook URL (optional, loads from credentials if not provided)
    
    Returns:
        bool: Success status
    """
    video_path = Path(video_path)
    
    if not video_path.exists():
        print(f"❌ Video not found: {video_path}")
        return False
    
    # Load webhook URL from credentials if not provided
    if not webhook_url:
        creds = load_credentials()
        webhook_url = creds.get("tiktok_webhook")
        
        if not webhook_url:
            print("❌ No Make.com webhook URL configured!")
            print("\n📋 Setup instructions:")
            print("1. Go to https://www.make.com/en/register")
            print("2. Create a new scenario")
            print("3. Add 'Webhooks > Custom webhook' as first module")
            print("4. Copy the webhook URL")
            print("5. Run: python3 make_com_tiktok.py --setup <webhook_url>")
            return False
    
    # Read video file and encode as base64
    print(f"📤 Uploading {video_path.name} ({video_path.stat().st_size / 1024 / 1024:.2f}MB)...")
    
    with open(video_path, 'rb') as f:
        video_data = base64.b64encode(f.read()).decode('utf-8')
    
    # Prepare payload
    payload = {
        "video_data": video_data,
        "filename": video_path.name,
        "caption": caption,
        "platform": "tiktok",
        "account": "stackkraft"
    }
    
    try:
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=120  # 2 minutes for upload
        )
        
        if response.status_code == 200:
            print(f"✅ Successfully uploaded to Make.com!")
            print(f"📊 Response: {response.text[:200]}")
            return True
        else:
            print(f"❌ Upload failed: HTTP {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False

def setup_instructions():
    """Print detailed Make.com setup instructions"""
    print("""
╔════════════════════════════════════════════════════════════════╗
║                 Make.com TikTok Setup Guide                     ║
╚════════════════════════════════════════════════════════════════╝

STEP 1: Create Make.com Account
────────────────────────────────────────────────────────────────
1. Go to: https://www.make.com/en/register
2. Sign up (FREE tier = 1000 operations/month)
3. Verify email

STEP 2: Create TikTok Scenario
────────────────────────────────────────────────────────────────
1. Click "Create a new scenario"
2. Add module: Webhooks > Custom webhook
3. Click "Create a webhook"
4. Name it: "StackKraft TikTok Upload"
5. Copy the webhook URL (looks like: https://hook.us1.make.com/xxxxx)
6. Click "OK"

STEP 3: Add TikTok Upload Module
────────────────────────────────────────────────────────────────
1. Click the + button after webhook
2. Search for "TikTok"
3. Select "TikTok > Upload a Video"
4. Click "Create a connection"
5. Log in with TikTok (stackkraft@gmail.com)
6. Map fields:
   - Video: {{video_data}} (decode from base64)
   - Caption: {{caption}}
   - Privacy: Public

STEP 4: Configure Video Decoder
────────────────────────────────────────────────────────────────
Between webhook and TikTok modules, add:
1. Tools > Base64 Decode
2. Input: {{video_data}}
3. Save decoded data

STEP 5: Test & Activate
────────────────────────────────────────────────────────────────
1. Click "Run once" to test
2. Send test from terminal (see below)
3. If successful, toggle scenario to "ON"
4. Save scenario

STEP 6: Save Webhook to StackKraft
────────────────────────────────────────────────────────────────
Run this command with your webhook URL:

python3 make_com_tiktok.py --setup YOUR_WEBHOOK_URL

════════════════════════════════════════════════════════════════

TESTING:

python3 make_com_tiktok.py /tmp/stackkraft_test_001.mp4 "Test upload! 🚀"

════════════════════════════════════════════════════════════════

TROUBLESHOOTING:

If TikTok module not available in Make.com:
→ Use alternative: "HTTP > Make a request" module
→ Send POST to TikTok API directly
→ Or use buffer/publer integration instead

════════════════════════════════════════════════════════════════
""")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        setup_instructions()
        sys.exit(0)
    
    if sys.argv[1] == "--setup":
        if len(sys.argv) < 3:
            print("❌ Usage: python3 make_com_tiktok.py --setup <webhook_url>")
            sys.exit(1)
        save_webhook_url(sys.argv[2])
        print("\n✅ Setup complete! Test with:")
        print(f"python3 make_com_tiktok.py /tmp/stackkraft_test_001.mp4 'Test! 🚀'")
        sys.exit(0)
    
    if sys.argv[1] == "--help":
        setup_instructions()
        sys.exit(0)
    
    # Upload mode
    video_path = sys.argv[1]
    caption = sys.argv[2] if len(sys.argv) > 2 else "StackKraft automation 🚀"
    
    success = upload_to_tiktok_via_make(video_path, caption)
    sys.exit(0 if success else 1)
