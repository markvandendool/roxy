#!/usr/bin/env python3
"""
Automated Account Creator - Browser Automation
Creates all social media accounts automatically using Playwright
"""

import asyncio
import random
import string
from playwright.async_api import async_playwright
import json
from datetime import datetime

# Generated brand from previous run
BRAND = {
    "username": "codehub59",
    "email": "codehub59@proton.me",
    "display_name": "CodeHub - Daily Coding Tips",
    "bio": "Daily coding tips & AI tutorials 🚀 | DM for collabs"
}

def generate_password():
    """Generate secure password"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(random.choice(chars) for _ in range(16))
    return password

PASSWORD = generate_password()

async def create_protonmail_account(page):
    """Create ProtonMail account"""
    print("1️⃣  Creating ProtonMail account...")
    
    try:
        await page.goto("https://proton.me/mail/signup")
        await page.wait_for_load_state("networkidle")
        
        # Fill username
        await page.fill('input[name="username"]', BRAND["username"])
        
        # Fill password
        await page.fill('input[type="password"]', PASSWORD)
        
        # Click create account
        await page.click('button[type="submit"]')
        
        await page.wait_for_timeout(5000)
        
        print(f"   ✅ Created: {BRAND['email']}")
        print(f"   🔐 Password: {PASSWORD}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

async def create_gumroad_account(page):
    """Create Gumroad account"""
    print("2️⃣  Creating Gumroad account...")
    
    try:
        await page.goto("https://gumroad.com/start")
        await page.wait_for_load_state("networkidle")
        
        # Fill email
        await page.fill('input[type="email"]', BRAND["email"])
        
        # Fill name
        await page.fill('input[name="name"]', BRAND["display_name"])
        
        # Fill password
        await page.fill('input[type="password"]', PASSWORD)
        
        # Submit
        await page.click('button[type="submit"]')
        
        await page.wait_for_timeout(3000)
        
        print(f"   ✅ Created Gumroad account")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

async def create_youtube_account(page):
    """Create YouTube account"""
    print("3️⃣  Creating YouTube account...")
    
    try:
        await page.goto("https://youtube.com")
        await page.click('text="Sign in"')
        
        await page.wait_for_timeout(2000)
        
        # Click "Create account"
        await page.click('text="Create account"')
        
        # Select "For my business"
        await page.click('text="For my business"')
        
        # Fill email
        await page.fill('input[type="email"]', BRAND["email"])
        await page.click('button:has-text("Next")')
        
        await page.wait_for_timeout(2000)
        
        # Fill password
        await page.fill('input[type="password"]', PASSWORD)
        await page.click('button:has-text("Next")')
        
        await page.wait_for_timeout(3000)
        
        print(f"   ✅ Created YouTube account")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

async def create_tiktok_account(page):
    """Create TikTok account"""
    print("4️⃣  Creating TikTok account...")
    
    try:
        await page.goto("https://tiktok.com/signup/phone-or-email/email")
        await page.wait_for_load_state("networkidle")
        
        # Fill email
        await page.fill('input[type="email"]', BRAND["email"])
        
        # Fill password
        await page.fill('input[type="password"]', PASSWORD)
        
        # Submit
        await page.click('button[type="submit"]')
        
        await page.wait_for_timeout(3000)
        
        print(f"   ✅ Created TikTok account")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

async def create_twitter_account(page):
    """Create Twitter account"""
    print("5️⃣  Creating Twitter account...")
    
    try:
        await page.goto("https://twitter.com/i/flow/signup")
        await page.wait_for_load_state("networkidle")
        
        # Fill email
        await page.fill('input[autocomplete="email"]', BRAND["email"])
        
        # Fill name
        await page.fill('input[autocomplete="name"]', BRAND["display_name"])
        
        # Click Next
        await page.click('div[role="button"]:has-text("Next")')
        
        await page.wait_for_timeout(2000)
        
        # Skip phone
        await page.click('text="Use email instead"')
        
        await page.wait_for_timeout(2000)
        
        print(f"   ✅ Created Twitter account")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

async def create_reddit_account(page):
    """Create Reddit account"""
    print("6️⃣  Creating Reddit account...")
    
    try:
        await page.goto("https://reddit.com/register")
        await page.wait_for_load_state("networkidle")
        
        # Fill email
        await page.fill('input[name="email"]', BRAND["email"])
        
        # Fill username
        await page.fill('input[name="username"]', BRAND["username"])
        
        # Fill password
        await page.fill('input[name="password"]', PASSWORD)
        
        # Submit
        await page.click('button[type="submit"]')
        
        await page.wait_for_timeout(3000)
        
        print(f"   ✅ Created Reddit account")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

async def save_credentials():
    """Save all credentials securely"""
    credentials = {
        "brand": BRAND,
        "password": PASSWORD,
        "created_at": datetime.now().isoformat(),
        "accounts": {
            "protonmail": BRAND["email"],
            "gumroad": BRAND["email"],
            "youtube": BRAND["email"],
            "tiktok": BRAND["email"],
            "twitter": BRAND["email"],
            "reddit": BRAND["email"]
        }
    }
    
    creds_file = f"{__file__.replace('account_creator.py', '')}.credentials.json"
    
    with open(creds_file, 'w') as f:
        json.dump(credentials, f, indent=2)
    
    print(f"\n💾 Credentials saved to: {creds_file}")
    print("\n⚠️  IMPORTANT: Keep this file secure!")

async def main():
    print("🤖 AUTOMATED ACCOUNT CREATOR")
    print("=" * 60)
    print(f"Brand: {BRAND['display_name']}")
    print(f"Email: {BRAND['email']}")
    print("=" * 60)
    print()
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Create accounts one by one
        success = []
        
        if await create_protonmail_account(page):
            success.append("ProtonMail")
            await asyncio.sleep(5)
        
        if await create_gumroad_account(page):
            success.append("Gumroad")
            await asyncio.sleep(5)
        
        if await create_youtube_account(page):
            success.append("YouTube")
            await asyncio.sleep(5)
        
        if await create_tiktok_account(page):
            success.append("TikTok")
            await asyncio.sleep(5)
        
        if await create_twitter_account(page):
            success.append("Twitter")
            await asyncio.sleep(5)
        
        if await create_reddit_account(page):
            success.append("Reddit")
        
        await browser.close()
        
        print()
        print("=" * 60)
        print(f"✅ Successfully created {len(success)} accounts:")
        for acc in success:
            print(f"   • {acc}")
        print("=" * 60)
        
        # Save credentials
        await save_credentials()
        
        print()
        print("NEXT STEPS:")
        print("1. Upload product to Gumroad")
        print("2. Upload videos to YouTube/TikTok")
        print("3. Post links on Twitter/Reddit")

if __name__ == "__main__":
    asyncio.run(main())
