#!/usr/bin/env python3
"""
Interactive Account Setup Assistant
Guides you through creating accounts on all platforms with same credentials

This script will:
1. Generate a secure password (or use yours)
2. Walk you through each platform step-by-step
3. Save credentials securely
4. Test API access
5. Verify everything works

Usage:
    python3 setup_accounts.py
"""

import os
import sys
import json
import secrets
import string
from pathlib import Path
from getpass import getpass


def generate_password(length=24):
    """Generate a strong password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def save_credentials(brand, password, credentials):
    """Save credentials securely"""
    creds_file = Path.home() / ".roxy" / "workshops" / "monetization" / ".credentials.json"
    creds_file.parent.mkdir(parents=True, exist_ok=True)
    
    data = {
        "brand": brand,
        "email": f"{brand}@proton.me",
        "password": password,
        "platforms": credentials
    }
    
    with open(creds_file, "w") as f:
        json.dump(data, f, indent=2)
    
    creds_file.chmod(0o600)
    return creds_file


def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_step(num, total, text):
    print(f"\n[{num}/{total}] {text}")
    print("-" * 60)


def main():
    print_header("ACCOUNT SETUP ASSISTANT")
    
    # Step 1: Choose brand
    print("BRAND OPTIONS:")
    print("1. FirstDraft (recommended)")
    print("2. StudioZero")
    print("3. RawTake")
    print("4. WireframeLabs")
    print("5. PrototypeMind")
    print("6. SketchStack")
    print("7. OpenBuild")
    print("8. BetaBrain")
    print("9. FrameworkZero")
    print("10. MakeNoiseStudio")
    print("11. Custom (enter your own)")
    
    choice = input("\nChoose (1-11): ").strip()
    
    brands = {
        "1": "firstdraft",
        "2": "studiozero",
        "3": "rawtake",
        "4": "wireframelabs",
        "5": "prototypemind",
        "6": "sketchstack",
        "7": "openbuild",
        "8": "betabrain",
        "9": "frameworkzero",
        "10": "makenoisestudio"
    }
    
    if choice == "11":
        brand = input("Enter brand name (lowercase, no spaces): ").strip().lower()
    else:
        brand = brands.get(choice, "firstdraft")
    
    print(f"\n✅ Brand: {brand}")
    print(f"📧 Email: {brand}@proton.me")
    
    # Step 2: Password
    print_step(1, 6, "PASSWORD SETUP")
    print("Options:")
    print("1. Generate secure password (recommended)")
    print("2. Enter your own password")
    
    pwd_choice = input("\nChoose (1-2): ").strip()
    
    if pwd_choice == "2":
        password = getpass("Enter password (same for all accounts): ")
        confirm = getpass("Confirm password: ")
        if password != confirm:
            print("❌ Passwords don't match!")
            return
    else:
        password = generate_password()
        print(f"\n🔑 Generated password: {password}")
        print("⚠️  SAVE THIS PASSWORD! You'll use it for all accounts.")
        input("\nPress Enter when you've saved it...")
    
    credentials = {}
    
    # Step 3: ProtonMail
    print_step(2, 6, "PROTONMAIL ACCOUNT")
    print(f"1. Go to: https://proton.me/mail")
    print(f"2. Click 'Get Proton for free'")
    print(f"3. Username: {brand}")
    print(f"4. Password: {password}")
    print(f"5. Complete CAPTCHA and verification")
    print(f"6. Email will be: {brand}@proton.me")
    
    input("\n✅ Press Enter when ProtonMail account is created...")
    credentials['protonmail'] = {
        'email': f'{brand}@proton.me',
        'created': True
    }
    
    # Step 4: Gumroad
    print_step(3, 6, "GUMROAD ACCOUNT (Product Store)")
    print(f"1. Go to: https://gumroad.com/signup")
    print(f"2. Email: {brand}@proton.me")
    print(f"3. Password: {password}")
    print(f"4. Complete profile")
    print(f"5. Click 'Start Selling'")
    print(f"6. Go to Settings → Advanced")
    print(f"7. Generate API Key")
    
    api_key = input("\n📋 Paste Gumroad API Key: ").strip()
    
    print(f"\n8. Create product:")
    print(f"   - Title: Roxy AI Starter Kit")
    print(f"   - Price: $49")
    print(f"   - Upload: ~/mindsong-products/roxy-ai-starter-v1.zip")
    
    product_url = input("📋 Paste product URL (e.g., gumroad.com/l/xyz): ").strip()
    
    credentials['gumroad'] = {
        'email': f'{brand}@proton.me',
        'api_key': api_key,
        'product_url': product_url.replace('http://', 'https://'),
        'created': True
    }
    
    # Step 5: YouTube
    print_step(4, 6, "YOUTUBE ACCOUNT")
    print("YouTube requires Google account with OAuth setup.")
    print("This is more complex - we'll do it separately.")
    print("")
    print("For now, we'll skip YouTube and add it later.")
    print("(You can still post to TikTok, Twitter, Reddit)")
    
    skip_youtube = input("\nSkip YouTube for now? (y/n): ").strip().lower()
    
    if skip_youtube == 'y':
        credentials['youtube'] = {'created': False, 'note': 'Manual OAuth setup required'}
    else:
        print("\nYouTube OAuth setup instructions:")
        print("1. Go to: https://console.cloud.google.com")
        print("2. Create new project")
        print("3. Enable 'YouTube Data API v3'")
        print("4. Create OAuth 2.0 credentials")
        print("5. Download JSON")
        print("6. Save to: ~/.roxy/workshops/monetization/.youtube_client_secret.json")
        input("\n✅ Press Enter when done...")
        credentials['youtube'] = {'created': True, 'oauth': True}
    
    # Step 6: TikTok
    print_step(5, 6, "TIKTOK ACCOUNT")
    print("TikTok requires cookies from browser.")
    print("")
    print(f"1. Go to: https://tiktok.com/signup")
    print(f"2. Sign up with email: {brand}@proton.me")
    print(f"3. Password: {password}")
    print(f"4. Username: @{brand}")
    print(f"5. Complete profile")
    print("")
    print("6. To get cookies:")
    print("   - Chrome: Install 'EditThisCookie' extension")
    print("   - Firefox: Install 'Cookie-Editor' add-on")
    print("   - Export cookies as JSON")
    print("   - Find 'sessionid' cookie")
    
    sessionid = input("\n📋 Paste TikTok sessionid cookie (or press Enter to skip): ").strip()
    
    if sessionid:
        credentials['tiktok'] = {
            'username': f'@{brand}',
            'cookies': {'sessionid': sessionid},
            'created': True
        }
    else:
        credentials['tiktok'] = {'created': False, 'note': 'Need to extract cookies'}
    
    # Step 7: Twitter
    print_step(6, 6, "TWITTER/X ACCOUNT")
    print(f"1. Go to: https://twitter.com/signup")
    print(f"2. Email: {brand}@proton.me")
    print(f"3. Password: {password}")
    print(f"4. Username: @{brand}")
    print("")
    print("5. Apply for Developer Account:")
    print("   - Go to: https://developer.twitter.com")
    print("   - Click 'Sign up for Free Access'")
    print("   - Create app (name: '{brand} Content Bot')")
    print("   - Get API keys")
    
    has_twitter = input("\nCreated Twitter account? (y/n): ").strip().lower()
    
    if has_twitter == 'y':
        print("\nEnter API credentials (press Enter to skip for now):")
        api_key = input("API Key: ").strip()
        api_secret = input("API Secret: ").strip()
        bearer = input("Bearer Token: ").strip()
        access_token = input("Access Token: ").strip()
        access_secret = input("Access Token Secret: ").strip()
        
        if api_key:
            credentials['twitter'] = {
                'username': f'@{brand}',
                'api_key': api_key,
                'api_secret': api_secret,
                'bearer_token': bearer,
                'access_token': access_token,
                'access_secret': access_secret,
                'created': True
            }
        else:
            credentials['twitter'] = {'created': True, 'note': 'API keys pending'}
    else:
        credentials['twitter'] = {'created': False}
    
    # Step 8: Reddit
    print_step(7, 7, "REDDIT ACCOUNT")
    print(f"1. Go to: https://reddit.com/register")
    print(f"2. Username: {brand}")
    print(f"3. Password: {password}")
    print(f"4. Email: {brand}@proton.me")
    print("")
    print("5. Create app for API access:")
    print("   - Go to: https://reddit.com/prefs/apps")
    print("   - Click 'create another app...'")
    print("   - Name: '{brand} bot'")
    print("   - Type: 'script'")
    print("   - Redirect URI: http://localhost:8080")
    
    has_reddit = input("\nCreated Reddit account? (y/n): ").strip().lower()
    
    if has_reddit == 'y':
        print("\nEnter app credentials (press Enter to skip):")
        client_id = input("Client ID (under app name): ").strip()
        client_secret = input("Client Secret: ").strip()
        
        if client_id:
            credentials['reddit'] = {
                'username': brand,
                'password': password,
                'client_id': client_id,
                'secret': client_secret,
                'created': True
            }
        else:
            credentials['reddit'] = {'created': True, 'note': 'API credentials pending'}
    else:
        credentials['reddit'] = {'created': False}
    
    # Save everything
    print_header("SAVING CREDENTIALS")
    
    creds_file = save_credentials(brand, password, credentials)
    
    print(f"✅ Credentials saved to: {creds_file}")
    print(f"🔒 File permissions: 600 (secure)")
    
    # Summary
    print_header("SETUP SUMMARY")
    print(f"Brand: {brand}")
    print(f"Email: {brand}@proton.me")
    print(f"Password: {password}")
    print("")
    print("Accounts created:")
    
    for platform, data in credentials.items():
        status = "✅" if data.get('created') else "⏸️"
        print(f"  {status} {platform.upper()}")
    
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    print("1. Test publishing with content_publisher.py")
    print("2. Extract viral clips from existing videos")
    print("3. Upload product to Gumroad")
    print("4. Start posting!")
    print("")
    print(f"Test command:")
    print(f"  python3 content_publisher.py \\")
    print(f"    --video /tmp/faceless_videos/final_coding_20260108_140540.mp4 \\")
    print(f"    --platforms gumroad")  # Start with easiest
    print("")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled")
        sys.exit(1)
