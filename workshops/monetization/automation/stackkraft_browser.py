#!/usr/bin/env /home/mark/llm-benchmarks/venv/bin/python
"""
StackKraft Browser Automation
Auto-fills account creation forms with correct credentials
"""

import json
import sys
import time
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright

# Load credentials
CREDS_FILE = Path.home() / ".roxy" / "workshops" / "monetization" / ".credentials.json"
with open(CREDS_FILE) as f:
    CREDS = json.load(f)

EMAIL = CREDS["email_primary"]  # StackKraft@gmail.com
PASSWORD = CREDS["password"]    # 6Stackkraft@@#@
USERNAME = CREDS["brand"]       # stackkraft
RECOVERY = CREDS["email_backup"]  # stackkraft@proton.me

print(f"""
🚀 StackKraft Browser Automation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 Email:    {EMAIL}
👤 Username: {USERNAME}
🔑 Password: {PASSWORD}
💾 Recovery: {RECOVERY}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")

def wait_user(msg="Press Enter to continue..."):
    """Pause for user"""
    input(f"\n⏸️  {msg}")

def fill_safe(page, selector, value, timeout=5000):
    """Safely fill field if it exists"""
    try:
        page.fill(selector, value, timeout=timeout)
        return True
    except Exception as e:
        print(f"   ⚠️  Could not fill {selector}: {e}")
        return False

def click_safe(page, selector, timeout=5000):
    """Safely click if element exists"""
    try:
        page.click(selector, timeout=timeout)
        return True
    except Exception as e:
        print(f"   ⚠️  Could not click {selector}: {e}")
        return False


def twitter_signup(page):
    """Fill Twitter signup form"""
    print("\n🐦 Twitter/X Signup")
    page.goto("https://twitter.com/i/flow/signup")
    time.sleep(3)
    
    # Click "Create account"
    click_safe(page, 'text="Create account"')
    time.sleep(2)
    
    # Name
    fill_safe(page, 'input[name="name"]', "StackKraft")
    
    # Email (might need to switch from phone)
    if not fill_safe(page, 'input[name="email"]', EMAIL):
        click_safe(page, 'text="Use email instead"')
        time.sleep(1)
        fill_safe(page, 'input[name="email"]', EMAIL)
    
    # Birthday (25 years old)
    fill_safe(page, 'select[name="month"]', "3")
    fill_safe(page, 'select[name="day"]', "15")
    fill_safe(page, 'select[name="year"]', "1999")
    
    wait_user("Complete captcha/verification, then press Enter")
    
    # Password (comes later)
    fill_safe(page, 'input[name="password"]', PASSWORD)
    
    # Username
    fill_safe(page, 'input[name="username"]', USERNAME)
    
    wait_user("Finish Twitter signup, then press Enter")


def instagram_signup(page):
    """Fill Instagram signup form"""
    print("\n📷 Instagram Signup")
    page.goto("https://www.instagram.com/accounts/emailsignup/")
    time.sleep(3)
    
    fill_safe(page, 'input[name="emailOrPhone"]', EMAIL)
    fill_safe(page, 'input[name="fullName"]', "StackKraft")
    fill_safe(page, 'input[name="username"]', USERNAME)
    fill_safe(page, 'input[name="password"]', PASSWORD)
    
    wait_user("Complete birthday/verification, then press Enter")


def tiktok_signup(page):
    """Fill TikTok signup form"""
    print("\n🎵 TikTok Signup")
    page.goto("https://www.tiktok.com/signup/phone-or-email/email")
    time.sleep(3)
    
    # Birthday first
    fill_safe(page, 'select:nth-of-type(1)', "March")
    fill_safe(page, 'select:nth-of-type(2)', "15")
    fill_safe(page, 'select:nth-of-type(3)', "1999")
    click_safe(page, 'button:has-text("Next")')
    time.sleep(2)
    
    # Email
    fill_safe(page, 'input[type="text"]', EMAIL)
    click_safe(page, 'button:has-text("Send code")')
    
    wait_user("Enter verification code, then press Enter")
    
    # Password
    fill_safe(page, 'input[type="password"]', PASSWORD)
    
    wait_user("Complete TikTok signup, then press Enter")


def linkedin_signup(page):
    """Fill LinkedIn signup form"""
    print("\n💼 LinkedIn Signup")
    page.goto("https://www.linkedin.com/signup")
    time.sleep(3)
    
    fill_safe(page, 'input[name="email"]', EMAIL)
    fill_safe(page, 'input[name="password"]', PASSWORD)
    click_safe(page, 'button:has-text("Agree & Join")')
    time.sleep(2)
    
    fill_safe(page, 'input[name="firstName"]', "Stack")
    fill_safe(page, 'input[name="lastName"]', "Kraft")
    
    wait_user("Complete LinkedIn verification, then press Enter")


def facebook_signup(page):
    """Fill Facebook signup form"""
    print("\n📘 Facebook Signup")
    page.goto("https://www.facebook.com/reg/")
    time.sleep(3)
    
    fill_safe(page, 'input[name="firstname"]', "Stack")
    fill_safe(page, 'input[name="lastname"]', "Kraft")
    fill_safe(page, 'input[name="reg_email__"]', EMAIL)
    fill_safe(page, 'input[name="reg_email_confirmation__"]', EMAIL)
    fill_safe(page, 'input[name="reg_passwd__"]', PASSWORD)
    
    # Birthday
    fill_safe(page, 'select[name="birthday_day"]', "15")
    fill_safe(page, 'select[name="birthday_month"]', "3")
    fill_safe(page, 'select[name="birthday_year"]', "1999")
    
    wait_user("Select gender and complete signup, then press Enter")


def reddit_signup(page):
    """Fill Reddit signup form"""
    print("\n🤖 Reddit Signup")
    page.goto("https://www.reddit.com/register/")
    time.sleep(3)
    
    fill_safe(page, 'input[name="email"]', EMAIL)
    fill_safe(page, 'input[name="username"]', USERNAME)
    fill_safe(page, 'input[name="password"]', PASSWORD)
    
    wait_user("Complete captcha, then press Enter")


def github_signup(page):
    """Fill GitHub signup form"""
    print("\n💻 GitHub Signup")
    page.goto("https://github.com/signup")
    time.sleep(3)
    
    fill_safe(page, 'input[name="email"]', EMAIL)
    click_safe(page, 'button:has-text("Continue")')
    time.sleep(2)
    
    fill_safe(page, 'input[name="password"]', PASSWORD)
    click_safe(page, 'button:has-text("Continue")')
    time.sleep(2)
    
    fill_safe(page, 'input[name="login"]', USERNAME)
    
    wait_user("Complete GitHub puzzles, then press Enter")


def devto_signup(page):
    """Fill Dev.to signup form"""
    print("\n👨‍💻 Dev.to Signup")
    page.goto("https://dev.to/enter")
    time.sleep(3)
    
    click_safe(page, 'a:has-text("Email")')
    time.sleep(2)
    
    fill_safe(page, 'input[name="user[email]"]', EMAIL)
    fill_safe(page, 'input[name="user[username]"]', USERNAME)
    fill_safe(page, 'input[name="user[password]"]', PASSWORD)
    
    wait_user("Complete Dev.to signup, then press Enter")


PLATFORMS = {
    "twitter": twitter_signup,
    "instagram": instagram_signup,
    "tiktok": tiktok_signup,
    "linkedin": linkedin_signup,
    "facebook": facebook_signup,
    "reddit": reddit_signup,
    "github": github_signup,
    "devto": devto_signup,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--platform", choices=list(PLATFORMS.keys()))
    parser.add_argument("--tier1", action="store_true", help="Twitter, Instagram, TikTok, LinkedIn, Facebook")
    parser.add_argument("--tier2", action="store_true", help="Reddit, GitHub, Dev.to")
    args = parser.parse_args()
    
    platforms = []
    if args.platform:
        platforms = [args.platform]
    elif args.tier1:
        platforms = ["twitter", "instagram", "tiktok", "linkedin", "facebook"]
    elif args.tier2:
        platforms = ["reddit", "github", "devto"]
    else:
        parser.print_help()
        sys.exit(1)
    
    print(f"\n🎯 Processing {len(platforms)} platforms: {', '.join(platforms)}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Visible browser
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        for pf in platforms:
            try:
                PLATFORMS[pf](page)
                print(f"✅ {pf.upper()} complete\n")
            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted")
                break
            except Exception as e:
                print(f"❌ Error on {pf}: {e}\n")
        
        wait_user("All done! Press Enter to close browser")
        browser.close()


if __name__ == "__main__":
    main()
