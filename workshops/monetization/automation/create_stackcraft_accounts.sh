#!/bin/bash
# StackCraft Account Creation Guide
# Brand: stackcraft
# Same credentials across all 21 platforms

BRAND="stackcraft"
EMAIL="${BRAND}@proton.me"

echo "============================================================"
echo "  STACKCRAFT - ACCOUNT CREATION CHECKLIST"
echo "============================================================"
echo ""
echo "Brand: $BRAND"
echo "Email: $EMAIL"
echo "Password: [Use same password for ALL platforms]"
echo ""
echo "Generate password:"
echo "  openssl rand -base64 24"
echo ""
read -p "Press Enter to generate password..." 
PASSWORD=$(openssl rand -base64 24)
echo ""
echo "🔑 YOUR PASSWORD: $PASSWORD"
echo ""
echo "⚠️  SAVE THIS PASSWORD NOW!"
echo "   You'll use it for all 21 accounts."
echo ""
read -p "Press Enter when saved..."

# Save credentials template
mkdir -p ~/.roxy/workshops/monetization
cat > ~/.roxy/workshops/monetization/.credentials.json << EOF
{
  "brand": "$BRAND",
  "email": "$EMAIL", 
  "password": "$PASSWORD",
  "platforms": {
    "tier1": {
      "youtube": {"status": "pending", "url": ""},
      "tiktok": {"status": "pending", "username": "@$BRAND"},
      "instagram": {"status": "pending", "username": "@$BRAND"},
      "twitter": {"status": "pending", "username": "@$BRAND"},
      "linkedin": {"status": "pending", "url": "linkedin.com/in/$BRAND"},
      "facebook": {"status": "pending", "page": "facebook.com/$BRAND"}
    },
    "tier2": {
      "reddit": {"status": "pending", "username": "u/$BRAND"},
      "github": {"status": "pending", "username": "$BRAND"},
      "devto": {"status": "pending", "username": "@$BRAND"},
      "hackernews": {"status": "pending", "username": "$BRAND"},
      "discord": {"status": "pending", "username": "$BRAND"}
    },
    "tier3": {
      "bluesky": {"status": "pending", "handle": "@$BRAND.bsky.social"},
      "mastodon": {"status": "pending", "handle": "@$BRAND@mastodon.social"},
      "twitch": {"status": "pending", "username": "$BRAND"},
      "medium": {"status": "pending", "username": "@$BRAND"},
      "threads": {"status": "pending", "username": "@$BRAND"}
    },
    "tier4": {
      "gumroad": {"status": "pending", "url": "gumroad.com/l/$BRAND"},
      "kofi": {"status": "pending", "url": "ko-fi.com/$BRAND"},
      "patreon": {"status": "pending", "url": "patreon.com/$BRAND"},
      "producthunt": {"status": "pending", "username": "@$BRAND"},
      "indiehackers": {"status": "pending", "username": "$BRAND"}
    }
  }
}
EOF

chmod 600 ~/.roxy/workshops/monetization/.credentials.json

echo ""
echo "============================================================"
echo "  TIER 1: CRITICAL PLATFORMS (START HERE)"
echo "============================================================"
echo ""

echo "[1/6] PROTONMAIL"
echo "─────────────────────────────────────────────────────────────"
echo "1. Open: https://proton.me/mail"
echo "2. Click 'Get Proton for free'"
echo "3. Username: $BRAND"
echo "4. Password: $PASSWORD"
echo "5. Complete verification"
echo ""
read -p "✅ Press Enter when ProtonMail account created..."

echo ""
echo "[2/6] YOUTUBE"
echo "─────────────────────────────────────────────────────────────"
echo "1. Create Google account: https://accounts.google.com/signup"
echo "2. Use email: $EMAIL"
echo "3. Password: $PASSWORD"
echo "4. Go to youtube.com"
echo "5. Create channel: 'StackCraft'"
echo "6. Description: 'Crafting tech stacks. AI, automation, code tutorials.'"
echo ""
read -p "✅ Press Enter when YouTube created..."

echo ""
echo "[3/6] TIKTOK"
echo "─────────────────────────────────────────────────────────────"
echo "1. Open: https://tiktok.com/signup"
echo "2. Sign up with email: $EMAIL"
echo "3. Password: $PASSWORD"
echo "4. Username: @$BRAND"
echo "5. Display name: StackCraft"
echo "6. Bio: 'Crafting tech stacks 🔨 AI • Automation • Code'"
echo ""
read -p "✅ Press Enter when TikTok created..."

echo ""
echo "[4/6] INSTAGRAM"
echo "─────────────────────────────────────────────────────────────"
echo "1. Open: https://instagram.com/accounts/emailsignup/"
echo "2. Email: $EMAIL"
echo "3. Username: @$BRAND"
echo "4. Password: $PASSWORD"
echo "5. Name: StackCraft"
echo "6. Bio: 'Crafting tech stacks 🔨 AI • Automation • Tutorials'"
echo ""
read -p "✅ Press Enter when Instagram created..."

echo ""
echo "[5/6] TWITTER/X"
echo "─────────────────────────────────────────────────────────────"
echo "1. Open: https://twitter.com/i/flow/signup"
echo "2. Email: $EMAIL"
echo "3. Username: @$BRAND"
echo "4. Password: $PASSWORD"
echo "5. Display name: StackCraft"
echo "6. Bio: 'Crafting tech stacks. AI automation, code tutorials, learning in public.'"
echo ""
read -p "✅ Press Enter when Twitter created..."

echo ""
echo "[6/6] FACEBOOK"
echo "─────────────────────────────────────────────────────────────"
echo "1. Create account: https://facebook.com/reg"
echo "2. Email: $EMAIL"
echo "3. Password: $PASSWORD"
echo "4. Name: Stack Craft"
echo ""
echo "5. Create Page: https://facebook.com/pages/create"
echo "6. Page name: StackCraft"
echo "7. Category: Education"
echo "8. Bio: 'Crafting tech stacks. AI, automation, coding tutorials.'"
echo ""
read -p "✅ Press Enter when Facebook created..."

echo ""
echo "============================================================"
echo "  TIER 2: HIGH VALUE COMMUNITIES"
echo "============================================================"
echo ""

echo "[7/21] REDDIT"
echo "─────────────────────────────────────────────────────────────"
echo "1. Open: https://reddit.com/register"
echo "2. Username: $BRAND"
echo "3. Password: $PASSWORD"
echo "4. Email: $EMAIL"
echo ""
read -p "✅ Press Enter when Reddit created..."

echo ""
echo "[8/21] GITHUB"
echo "─────────────────────────────────────────────────────────────"
echo "1. Open: https://github.com/signup"
echo "2. Email: $EMAIL"
echo "3. Username: $BRAND"
echo "4. Password: $PASSWORD"
echo "5. Bio: 'Crafting tech stacks. Sharing automation scripts and AI workflows.'"
echo ""
read -p "✅ Press Enter when GitHub created..."

echo ""
echo "[9/21] DEV.TO"
echo "─────────────────────────────────────────────────────────────"
echo "1. Open: https://dev.to/enter"
echo "2. Sign up with email: $EMAIL"
echo "3. Username: @$BRAND"
echo "4. Display name: StackCraft"
echo ""
read -p "✅ Press Enter when Dev.to created..."

echo ""
echo "[10/21] LINKEDIN"
echo "─────────────────────────────────────────────────────────────"
echo "1. Open: https://linkedin.com/signup"
echo "2. Email: $EMAIL"
echo "3. Password: $PASSWORD"
echo "4. Name: Stack Craft"
echo "5. Headline: 'Building AI automation & tech stacks. Sharing workflows.'"
echo ""
read -p "✅ Press Enter when LinkedIn created..."

echo ""
echo "[11/21] DISCORD"
echo "─────────────────────────────────────────────────────────────"
echo "1. Open: https://discord.com/register"
echo "2. Email: $EMAIL"
echo "3. Username: $BRAND"
echo "4. Password: $PASSWORD"
echo ""
read -p "✅ Press Enter when Discord created..."

echo ""
echo "============================================================"
echo "  TIER 3: GROWING PLATFORMS"
echo "============================================================"
echo ""

echo "[12/21] BLUESKY"
echo "─────────────────────────────────────────────────────────────"
echo "1. Get invite code: https://bsky.app"
echo "2. Handle: @$BRAND.bsky.social"
echo "3. Email: $EMAIL"
echo "4. Password: $PASSWORD"
echo ""
read -p "✅ Press Enter when Bluesky created (or skip)..."

echo ""
echo "[13/21] MASTODON"
echo "─────────────────────────────────────────────────────────────"
echo "1. Open: https://mastodon.social/auth/sign_up"
echo "2. Username: $BRAND"
echo "3. Email: $EMAIL"
echo "4. Password: $PASSWORD"
echo ""
read -p "✅ Press Enter when Mastodon created..."

echo ""
echo "[14/21] TWITCH"
echo "─────────────────────────────────────────────────────────────"
echo "1. Open: https://twitch.tv/signup"
echo "2. Username: $BRAND"
echo "3. Password: $PASSWORD"
echo "4. Email: $EMAIL"
echo "5. Display name: StackCraft"
echo ""
read -p "✅ Press Enter when Twitch created..."

echo ""
echo "[15/21] MEDIUM"
echo "─────────────────────────────────────────────────────────────"
echo "1. Open: https://medium.com"
echo "2. Sign up with email: $EMAIL"
echo "3. Username: @$BRAND"
echo "4. Name: StackCraft"
echo ""
read -p "✅ Press Enter when Medium created..."

echo ""
echo "[16/21] THREADS"
echo "─────────────────────────────────────────────────────────────"
echo "1. Open Threads app or web"
echo "2. Login with Instagram (@$BRAND)"
echo "3. Auto-creates Threads account"
echo ""
read -p "✅ Press Enter when Threads activated..."

echo ""
echo "============================================================"
echo "  TIER 4: MONETIZATION PLATFORMS"
echo "============================================================"
echo ""

echo "[17/21] GUMROAD"
echo "─────────────────────────────────────────────────────────────"
echo "1. Open: https://gumroad.com/signup"
echo "2. Email: $EMAIL"
echo "3. Password: $PASSWORD"
echo "4. Click 'Start selling'"
echo "5. Username: $BRAND"
echo ""
echo "6. Create product:"
echo "   - Upload: ~/mindsong-products/roxy-ai-starter-v1.zip"
echo "   - Title: Roxy AI Starter Kit"
echo "   - Price: \$49"
echo ""
read -p "✅ Press Enter when Gumroad created..."

echo ""
echo "[18/21] KO-FI"
echo "─────────────────────────────────────────────────────────────"
echo "1. Open: https://ko-fi.com/signup"
echo "2. Email: $EMAIL"
echo "3. Password: $PASSWORD"
echo "4. Page name: ko-fi.com/$BRAND"
echo ""
read -p "✅ Press Enter when Ko-fi created..."

echo ""
echo "[19/21] PATREON"
echo "─────────────────────────────────────────────────────────────"
echo "1. Open: https://patreon.com/signup"
echo "2. Email: $EMAIL"
echo "3. Password: $PASSWORD"
echo "4. Page: patreon.com/$BRAND"
echo ""
read -p "✅ Press Enter when Patreon created..."

echo ""
echo "[20/21] PRODUCT HUNT"
echo "─────────────────────────────────────────────────────────────"
echo "1. Open: https://producthunt.com/join"
echo "2. Email: $EMAIL"
echo "3. Username: @$BRAND"
echo "4. Password: $PASSWORD"
echo ""
read -p "✅ Press Enter when ProductHunt created..."

echo ""
echo "[21/21] INDIE HACKERS"
echo "─────────────────────────────────────────────────────────────"
echo "1. Open: https://indiehackers.com/sign-up"
echo "2. Email: $EMAIL"
echo "3. Username: $BRAND"
echo "4. Password: $PASSWORD"
echo ""
read -p "✅ Press Enter when IndieHackers created..."

echo ""
echo "============================================================"
echo "  ✅ ALL 21 ACCOUNTS CREATED!"
echo "============================================================"
echo ""
echo "Credentials saved to:"
echo "  ~/.roxy/workshops/monetization/.credentials.json"
echo ""
echo "Next steps:"
echo "1. Test content_publisher.py with your videos"
echo "2. Get API keys for automated posting (Twitter, Reddit, YouTube)"
echo "3. Start publishing!"
echo ""
echo "Quick test:"
echo "  cd ~/.roxy/workshops/monetization/automation"
echo "  python3 content_publisher.py --video /tmp/faceless_videos/final_coding*.mp4"
echo ""
