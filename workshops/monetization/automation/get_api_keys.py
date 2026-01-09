#!/usr/bin/env /home/mark/llm-benchmarks/venv/bin/python
"""
StackKraft API Key Setup
Opens each platform's developer portal to get API credentials
"""

import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

CREDS_FILE = Path.home() / ".roxy" / "workshops" / "monetization" / ".credentials.json"

PLATFORMS = {
    "twitter": {
        "url": "https://developer.twitter.com/en/portal/dashboard",
        "name": "Twitter/X Developer Portal",
        "keys_needed": ["API Key", "API Secret", "Bearer Token", "Access Token", "Access Token Secret"],
        "instructions": """
        1. Click "Create Project" or use existing
        2. Create an App
        3. Go to "Keys and tokens" tab
        4. Generate API Key & Secret
        5. Generate Access Token & Secret
        6. Set permissions to "Read and Write"
        """
    },
    "reddit": {
        "url": "https://www.reddit.com/prefs/apps",
        "name": "Reddit App Preferences",
        "keys_needed": ["Client ID", "Client Secret"],
        "instructions": """
        1. Scroll to bottom, click "create another app"
        2. Name: StackKraft Bot
        3. Type: script
        4. Redirect URI: http://localhost:8080
        5. Click "create app"
        6. Copy client ID (under app name)
        7. Copy secret
        """
    },
    "youtube": {
        "url": "https://console.cloud.google.com/apis/credentials",
        "name": "Google Cloud Console",
        "keys_needed": ["API Key", "OAuth Client ID", "OAuth Client Secret"],
        "instructions": """
        1. Create new project: "StackKraft"
        2. Enable YouTube Data API v3
        3. Go to Credentials
        4. Create API Key (restrict to YouTube Data API)
        5. Create OAuth 2.0 Client ID (Desktop app)
        6. Download OAuth credentials JSON
        """
    },
    "tiktok": {
        "url": "https://developers.tiktok.com/",
        "name": "TikTok for Developers",
        "keys_needed": ["Client Key", "Client Secret"],
        "instructions": """
        1. Log in with StackKraft TikTok account
        2. Create new app
        3. Request "Content Posting API" access
        4. Copy Client Key and Secret
        Note: May require manual approval (1-2 days)
        """
    },
    "instagram": {
        "url": "https://developers.facebook.com/apps/",
        "name": "Meta for Developers",
        "keys_needed": ["App ID", "App Secret", "Access Token"],
        "instructions": """
        1. Create new app (type: Business)
        2. Add Instagram Basic Display
        3. Configure OAuth redirect: http://localhost:8080
        4. Get App ID and Secret from Settings > Basic
        5. Generate User Access Token from Tools
        Note: Requires Instagram Business account
        """
    },
    "linkedin": {
        "url": "https://www.linkedin.com/developers/apps",
        "name": "LinkedIn Developers",
        "keys_needed": ["Client ID", "Client Secret"],
        "instructions": """
        1. Create app
        2. Request "Share on LinkedIn" permission
        3. Add redirect URL: http://localhost:8080
        4. Get Client ID and Secret from Auth tab
        """
    }
}


def wait_user(msg="Press Enter when ready..."):
    input(f"\n⏸️  {msg}")


def main():
    print("""
🔑 StackKraft API Key Setup
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This script will open each platform's developer portal.
Follow the instructions to get API credentials.

We'll get keys for:
  1. Twitter/X - Post tweets programmatically
  2. Reddit - Post to subreddits
  3. YouTube - Upload videos via API
  4. TikTok - Upload videos (may need approval)
  5. Instagram - Post via Graph API
  6. LinkedIn - Share posts

Let's go! 🚀
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
    
    wait_user("Press Enter to start...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()
        
        api_keys = {}
        
        for platform, config in PLATFORMS.items():
            print(f"\n{'='*60}")
            print(f"🔧 {config['name']}")
            print(f"{'='*60}")
            print(f"\n📋 Keys needed:")
            for key in config['keys_needed']:
                print(f"   - {key}")
            
            print(f"\n📖 Instructions:")
            print(config['instructions'])
            
            print(f"\n🌐 Opening {config['url']}...")
            page.goto(config['url'])
            time.sleep(2)
            
            wait_user(f"Get {platform.upper()} API keys, then press Enter...")
            
            # Collect keys
            print(f"\n✏️  Enter your {platform.upper()} API keys:")
            platform_keys = {}
            for key_name in config['keys_needed']:
                value = input(f"   {key_name}: ").strip()
                if value:
                    # Convert key name to snake_case
                    key_snake = key_name.lower().replace(" ", "_").replace("&", "and")
                    platform_keys[key_snake] = value
            
            api_keys[platform] = platform_keys
            
            # Save immediately
            save_api_keys(api_keys)
            print(f"   ✅ {platform.upper()} keys saved!")
        
        print("\n" + "="*60)
        print("🎉 All API keys collected!")
        print("="*60)
        print(f"\n📁 Saved to: {CREDS_FILE}")
        print("\n🚀 Next steps:")
        print("   1. Test API connections")
        print("   2. Upload first video")
        print("   3. Automate posting schedule")
        
        wait_user("Press Enter to close browser...")
        browser.close()


def save_api_keys(api_keys):
    """Save API keys to credentials file"""
    with open(CREDS_FILE) as f:
        creds = json.load(f)
    
    if "api_keys" not in creds:
        creds["api_keys"] = {}
    
    creds["api_keys"].update(api_keys)
    
    with open(CREDS_FILE, "w") as f:
        json.dump(creds, f, indent=2)
    
    # Ensure secure permissions
    CREDS_FILE.chmod(0o600)


if __name__ == "__main__":
    main()
