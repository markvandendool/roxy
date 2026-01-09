#!/usr/bin/env python3
"""
StackCraft Account Creator - Military Grade Factory
Creates accounts across all 21 platforms with consistent branding

Brand: StackCraft
Email: stackcraft@proton.me
Password: [Generated securely]

Platforms:
- Tier 1: YouTube, TikTok, Instagram, Twitter, LinkedIn, Facebook
- Tier 2: Reddit, GitHub, Dev.to, Hacker News, Discord
- Tier 3: Bluesky, Mastodon, Twitch, Medium, Threads
- Tier 4: Gumroad, Ko-fi, Patreon, ProductHunt, IndieHackers
"""

import os
import sys
import json
import secrets
import string
from pathlib import Path
from datetime import datetime

BRAND = "stackcraft"
EMAIL = f"{BRAND}@proton.me"

def generate_password(length=24):
    """Generate military-grade password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def print_header(text):
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")

def save_progress(credentials):
    """Save credentials after each platform"""
    creds_file = Path.home() / ".roxy" / "workshops" / "monetization" / ".stackcraft_creds.json"
    creds_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(creds_file, "w") as f:
        json.dump(credentials, f, indent=2)
    
    creds_file.chmod(0o600)
    return creds_file

def main():
    print_header("STACKCRAFT ACCOUNT FACTORY")
    
    # Generate password
    password = generate_password()
    
    print(f"🏷️  BRAND: {BRAND}")
    print(f"📧 EMAIL: {EMAIL}")
    print(f"🔑 PASSWORD: {password}")
    print(f"\n⚠️  SAVE THIS PASSWORD - You'll use it everywhere!")
    
    input("\nPress Enter to start account creation...")
    
    credentials = {
        "brand": BRAND,
        "email": EMAIL,
        "password": password,
        "created": datetime.now().isoformat(),
        "platforms": {}
    }
    
    # Platform creation guide
    platforms = [
        # Tier 1
        {
            "name": "ProtonMail",
            "tier": 1,
            "url": "https://proton.me/mail",
            "steps": [
                "Click 'Get Proton for free'",
                f"Username: {BRAND}",
                f"Password: {password}",
                "Complete CAPTCHA",
                f"Email: {EMAIL}"
            ],
            "api_needed": False
        },
        {
            "name": "YouTube",
            "tier": 1,
            "url": "https://youtube.com",
            "steps": [
                "Create Google account with ProtonMail",
                f"Channel name: StackCraft",
                "Enable YouTube Data API v3 (later for automation)",
                "OAuth setup required for API access"
            ],
            "api_needed": True
        },
        {
            "name": "TikTok",
            "tier": 1,
            "url": "https://tiktok.com/signup",
            "steps": [
                f"Sign up with email: {EMAIL}",
                f"Password: {password}",
                f"Username: @{BRAND}",
                "Complete profile",
                "Export cookies for API (use browser extension)"
            ],
            "api_needed": True
        },
        {
            "name": "Instagram",
            "tier": 1,
            "url": "https://instagram.com/accounts/emailsignup",
            "steps": [
                f"Email: {EMAIL}",
                f"Username: @{BRAND}",
                f"Password: {password}",
                "Complete profile",
                "Connect to Facebook for cross-posting"
            ],
            "api_needed": True
        },
        {
            "name": "Twitter/X",
            "tier": 1,
            "url": "https://twitter.com/signup",
            "steps": [
                f"Email: {EMAIL}",
                f"Password: {password}",
                f"Username: @{BRAND}",
                "Apply for Developer account at developer.twitter.com",
                "Create app, get API keys"
            ],
            "api_needed": True
        },
        {
            "name": "LinkedIn",
            "tier": 1,
            "url": "https://linkedin.com/signup",
            "steps": [
                f"Email: {EMAIL}",
                f"Password: {password}",
                "First name: Stack",
                "Last name: Craft",
                "Headline: 'Tech automation, AI workflows, guitar + code'",
                f"Custom URL: /in/{BRAND}"
            ],
            "api_needed": False
        },
        {
            "name": "Facebook",
            "tier": 1,
            "url": "https://facebook.com/signup",
            "steps": [
                f"Email: {EMAIL}",
                f"Password: {password}",
                "Name: Stack Craft",
                "Create Page: 'StackCraft'",
                "Join groups: Tech, AI, Music Production, Guitar",
                "Enable Meta Business Suite for API access"
            ],
            "api_needed": True
        },
        # Tier 2
        {
            "name": "Reddit",
            "tier": 2,
            "url": "https://reddit.com/register",
            "steps": [
                f"Username: {BRAND}",
                f"Password: {password}",
                f"Email: {EMAIL}",
                "Go to reddit.com/prefs/apps",
                "Create app (type: script)",
                "Save client_id and secret"
            ],
            "api_needed": True
        },
        {
            "name": "GitHub",
            "tier": 2,
            "url": "https://github.com/signup",
            "steps": [
                f"Email: {EMAIL}",
                f"Password: {password}",
                f"Username: {BRAND}",
                "Complete profile",
                "Create Personal Access Token (Settings → Developer)",
                "Scope: repo, user, workflow"
            ],
            "api_needed": True
        },
        {
            "name": "Dev.to",
            "tier": 2,
            "url": "https://dev.to/enter",
            "steps": [
                f"Email: {EMAIL}",
                f"Username: @{BRAND}",
                f"Password: {password}",
                "Complete profile",
                "Settings → API Keys (for automated posting)"
            ],
            "api_needed": True
        },
        {
            "name": "Hacker News",
            "tier": 2,
            "url": "https://news.ycombinator.com",
            "steps": [
                f"Username: {BRAND}",
                f"Password: {password}",
                "About: 'Tech automation, AI workflows'",
                "No API - manual posting only"
            ],
            "api_needed": False
        },
        {
            "name": "Discord",
            "tier": 2,
            "url": "https://discord.com/register",
            "steps": [
                f"Email: {EMAIL}",
                f"Username: {BRAND}",
                f"Password: {password}",
                "Create server: 'StackCraft Community'",
                "Join servers: AI, Python, Music Production"
            ],
            "api_needed": False
        },
        # Tier 3
        {
            "name": "Bluesky",
            "tier": 3,
            "url": "https://bsky.app",
            "steps": [
                f"Handle: @{BRAND}.bsky.social",
                f"Email: {EMAIL}",
                f"Password: {password}",
                "Invitation code may be required"
            ],
            "api_needed": False
        },
        {
            "name": "Mastodon",
            "tier": 3,
            "url": "https://mastodon.social/auth/sign_up",
            "steps": [
                f"Username: {BRAND}",
                f"Email: {EMAIL}",
                f"Password: {password}",
                "Choose instance: mastodon.social or fosstodon.org"
            ],
            "api_needed": True
        },
        {
            "name": "Twitch",
            "tier": 3,
            "url": "https://twitch.tv/signup",
            "steps": [
                f"Username: {BRAND}",
                f"Password: {password}",
                f"Email: {EMAIL}",
                "Set up channel for live coding/music streams"
            ],
            "api_needed": True
        },
        {
            "name": "Medium",
            "tier": 3,
            "url": "https://medium.com/m/signin",
            "steps": [
                f"Sign up with Google (use {EMAIL})",
                f"Username: @{BRAND}",
                "Or use Substack: substack.com"
            ],
            "api_needed": False
        },
        {
            "name": "Threads",
            "tier": 3,
            "url": "https://threads.net",
            "steps": [
                "Link Instagram account",
                "Same username/profile as Instagram",
                "Cross-posts with Instagram Reels"
            ],
            "api_needed": False
        },
        # Tier 4
        {
            "name": "Gumroad",
            "tier": 4,
            "url": "https://gumroad.com/signup",
            "steps": [
                f"Email: {EMAIL}",
                f"Password: {password}",
                "Click 'Start Selling'",
                "Settings → Advanced → Generate API Key",
                "Upload product: Roxy AI Starter Kit ($49)"
            ],
            "api_needed": True
        },
        {
            "name": "Ko-fi",
            "tier": 4,
            "url": "https://ko-fi.com/manage/register",
            "steps": [
                f"Email: {EMAIL}",
                f"Password: {password}",
                f"Page URL: ko-fi.com/{BRAND}",
                "Set up shop, memberships"
            ],
            "api_needed": False
        },
        {
            "name": "Patreon",
            "tier": 4,
            "url": "https://patreon.com/signup",
            "steps": [
                f"Email: {EMAIL}",
                f"Password: {password}",
                f"Page name: StackCraft",
                "Set up tiers, exclusive content"
            ],
            "api_needed": True
        },
        {
            "name": "ProductHunt",
            "tier": 4,
            "url": "https://producthunt.com/join",
            "steps": [
                f"Sign up with email: {EMAIL}",
                f"Username: @{BRAND}",
                "Complete profile",
                "Prepare to launch products"
            ],
            "api_needed": False
        },
        {
            "name": "IndieHackers",
            "tier": 4,
            "url": "https://indiehackers.com/sign-up",
            "steps": [
                f"Email: {EMAIL}",
                f"Password: {password}",
                f"Username: @{BRAND}",
                "Share revenue milestones, journey"
            ],
            "api_needed": False
        }
    ]
    
    # Guide through each platform
    for i, platform in enumerate(platforms, 1):
        tier = platform['tier']
        name = platform['name']
        
        print_header(f"[{i}/21] {name} (Tier {tier})")
        print(f"🔗 URL: {platform['url']}\n")
        
        for j, step in enumerate(platform['steps'], 1):
            print(f"  {j}. {step}")
        
        if platform['api_needed']:
            print(f"\n⚙️  API/Credentials needed for automation")
        
        print()
        response = input(f"Account created? (y/n/skip): ").strip().lower()
        
        credentials['platforms'][name.lower().replace('/', '_')] = {
            'created': response == 'y',
            'tier': tier,
            'url': platform['url'],
            'api_needed': platform['api_needed'],
            'timestamp': datetime.now().isoformat()
        }
        
        # Save progress after each platform
        save_progress(credentials)
        print(f"💾 Progress saved")
    
    # Final summary
    print_header("ACCOUNT CREATION COMPLETE")
    
    created = sum(1 for p in credentials['platforms'].values() if p['created'])
    total = len(credentials['platforms'])
    
    print(f"✅ Created: {created}/{total} accounts")
    print(f"📧 Email: {EMAIL}")
    print(f"🔑 Password: {password}")
    print(f"\n💾 Credentials: ~/.roxy/workshops/monetization/.stackcraft_creds.json")
    
    print("\n" + "="*70)
    print("NEXT STEPS:")
    print("="*70)
    print("1. Upload product to Gumroad")
    print("2. Get API keys for Twitter, Reddit, YouTube")
    print("3. Test content_publisher.py")
    print("4. Start posting!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Account creation paused")
        print("💾 Progress saved - run again to continue")
        sys.exit(0)
