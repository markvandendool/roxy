#!/usr/bin/env python3
"""
Automated Social Media Account Setup
Creates fresh accounts for monetization workshop - separate from Million Song Mind
"""

import time
import random
import string
from datetime import datetime

# Account details generator
def generate_brand_name():
    """Generate a fresh brand name"""
    prefixes = ["Code", "Tech", "AI", "Quick", "Dev", "Brain", "Byte", "Smart"]
    suffixes = ["Tips", "Hacks", "Shorts", "Daily", "Lab", "Zone", "Hub", "Stack"]
    
    brand = f"{random.choice(prefixes)}{random.choice(suffixes)}"
    number = random.randint(10, 99)
    
    return {
        "brand": brand,
        "username": f"{brand.lower()}{number}",
        "display_name": f"{brand} - Daily Coding Tips"
    }

def generate_email_options():
    """Email service recommendations"""
    return """
EMAIL OPTIONS (No Phone Required):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. ProtonMail (Best for privacy)
   → proton.me/mail
   → Free tier: 1GB, no phone needed
   → Command: firefox https://proton.me/mail/signup &

2. Tutanota (Good alternative)
   → tutanota.com
   → Free tier, encrypted, no phone
   → Command: firefox https://tutanota.com/signup &

3. Temp Mail (For quick testing)
   → temp-mail.org
   → Instant disposable email
   → Not for long-term use

4. SimpleLogin (Email aliases)
   → simplelogin.io
   → Create unlimited aliases
   → Forward to your real email

RECOMMENDED STRATEGY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
→ Use ProtonMail for main account
→ Use SimpleLogin aliases for each platform
→ Example: tiktok-{random}@simplelogin.co → your protonmail
"""

def generate_account_plan(brand_info):
    """Generate complete account creation plan"""
    
    plan = f"""
╔══════════════════════════════════════════════════════════════╗
║        AUTOMATED ACCOUNT CREATION PLAN                       ║
╚══════════════════════════════════════════════════════════════╝

BRAND IDENTITY:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Brand Name:     {brand_info['brand']}
Username:       {brand_info['username']}
Display Name:   {brand_info['display_name']}
Bio:            Daily coding tips & AI tutorials 🚀 | DM for collabs

STEP-BY-STEP AUTOMATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1️⃣  CREATE EMAIL (5 min)
   □ Open ProtonMail: https://proton.me/mail/signup
   □ Username: {brand_info['username']}@proton.me
   □ Strong password (save to password manager)
   □ Skip recovery email/phone
   □ Verify email

2️⃣  GUMROAD ACCOUNT (5 min)
   □ Go to: https://gumroad.com/start
   □ Email: {brand_info['username']}@proton.me
   □ Username: {brand_info['username']}
   □ Display name: {brand_info['display_name']}
   □ Connect bank/PayPal for payouts
   □ Upload product ZIP

3️⃣  YOUTUBE ACCOUNT (10 min)
   □ Go to: https://youtube.com
   □ "Sign in" → "Create account" → "For my business"
   □ Use ProtonMail email
   □ Channel name: {brand_info['display_name']}
   □ Handle: @{brand_info['username']}
   □ Skip phone verification (use voice.google.com if needed)
   □ Enable monetization (YouTube Partner Program)

4️⃣  TIKTOK ACCOUNT (5 min)
   □ Go to: https://tiktok.com/signup
   □ Use "Email" signup (not phone)
   □ Email: {brand_info['username']}@proton.me
   □ Username: @{brand_info['username']}
   □ Display name: {brand_info['brand']}
   □ Bio: Daily coding tips 🚀
   □ Profile pic: Simple logo (Canva.com/logos)

5️⃣  TWITTER/X ACCOUNT (5 min)
   □ Go to: https://twitter.com/i/flow/signup
   □ Email: {brand_info['username']}@proton.me
   □ Username: @{brand_info['username']}
   □ Display name: {brand_info['brand']}
   □ Bio: Daily coding tips & AI tutorials | New video every day
   □ Skip phone (or use Google Voice)

6️⃣  REDDIT ACCOUNT (2 min)
   □ Go to: https://reddit.com/register
   □ Email: {brand_info['username']}@proton.me
   □ Username: {brand_info['username']}
   □ Subscribe to: r/Python r/learnprogramming r/coding

7️⃣  INSTAGRAM (OPTIONAL - 5 min)
   □ Go to: https://instagram.com/accounts/emailsignup
   □ Email: {brand_info['username']}@proton.me
   □ Username: @{brand_info['username']}
   □ Business account
   □ Category: Education

AUTOMATION TOOLS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Browser Automation (for bulk account creation):
→ Install: sudo apt install python3-playwright
→ Run: playwright install chromium
→ Script: ~/.roxy/workshops/monetization/automation/account_creator.py

Password Manager:
→ Install: sudo apt install keepassxc
→ Store all credentials securely

ANTI-DETECTION TIPS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Use different browser profile for each account
✓ Clear cookies between signups
✓ Use VPN (ProtonVPN free tier) if creating multiple accounts
✓ Don't sign up for all platforms in 1 day (spread over 3 days)
✓ Add profile pictures and complete bios immediately
✓ Wait 24 hours before posting content

CREDENTIALS TEMPLATE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Email:     {brand_info['username']}@proton.me
Password:  [Generate strong password]
Recovery:  [Your personal email - keep separate]

Gumroad:   {brand_info['username']}@proton.me
YouTube:   {brand_info['username']}@proton.me
TikTok:    {brand_info['username']}@proton.me
Twitter:   {brand_info['username']}@proton.me
Reddit:    {brand_info['username']}@proton.me

Save to: ~/.roxy/workshops/monetization/.credentials (ENCRYPTED)

NEXT STEPS AFTER ACCOUNT CREATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Upload product to Gumroad
2. Upload 3 videos to YouTube/TikTok
3. Share Gumroad link in video descriptions
4. Post on Reddit/Twitter with link
5. Track sales in revenue tracker

TIME ESTIMATE: 45 minutes total for all accounts
"""
    
    return plan

def main():
    print("🤖 AUTOMATED SOCIAL MEDIA ACCOUNT SETUP")
    print("=" * 60)
    print()
    
    # Generate brand identity
    brand = generate_brand_name()
    
    print(f"Generated Brand: {brand['brand']}")
    print(f"Username: {brand['username']}")
    print(f"Display Name: {brand['display_name']}")
    print()
    
    # Show email options
    print(generate_email_options())
    
    # Generate complete plan
    plan = generate_account_plan(brand)
    
    # Save plan to file
    plan_file = f"/tmp/account_creation_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(plan_file, 'w') as f:
        f.write(plan)
    
    print(plan)
    print()
    print(f"📄 Plan saved to: {plan_file}")
    print()
    print("=" * 60)
    print("QUICK START:")
    print("=" * 60)
    print(f"1. Open ProtonMail: firefox https://proton.me/mail/signup &")
    print(f"2. Create email: {brand['username']}@proton.me")
    print(f"3. Follow plan above")
    print()

if __name__ == "__main__":
    main()
