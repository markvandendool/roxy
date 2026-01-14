# Account Creation & Submission Checklist (Human)

Purpose: exact fields and sample copy to create Gumroad product, YouTube channel, and TikTok Business account, plus submission hints for TikTok Content API and YouTube OAuth consent.

---

## 1) Gumroad — List OBS Automation Scripts
URL: https://gumroad.com/

Required fields & sample copy:
- Seller email: mark@example.com (use Proton/Gmail)
- Product title: "Roxy OBS Automation Scripts — Scene & Workflow Helpers"
- Price: $29 (one-time)
- Short description (<= 200 chars): "Automate OBS workflows and scene management — ready-to-use Python & Bash utilities for streamers and studios. Includes installation guide and examples."
- Long description: include Features, What’s Included, Installation, License, Support contact.
  Sample:
  "This package contains 12 production-ready OBS automation scripts. Install instructions, example scenes, and a sample workflow are included. Use for stream automation, recording workflows, and scene scheduling."
- Tags: obs, streaming, automation, scripts, roxy
- Product files: upload `releases/roxy-obs-scripts-v1.zip` (produced by package_obs.sh)
- Screenshots / Demo GIFs: at least 1 demo GIF + 2 screenshots (800x450 recommended)
- Refund policy: set clearly (e.g., 14-day refund)
- Payout info: connect payout (Stripe / PayPal) in Gumroad account settings
- Privacy / Terms: link to a short terms page or include text in product page

Checklist before publish:
- [ ] ZIP contains README.md and LICENSE
- [ ] Include a short demo GIF (200–400 KB)
- [ ] Verify `package_obs.sh` version metadata
- [ ] Publish and copy public product URL for marketing

---

## 2) YouTube — Create Channel & Upload 3 Shorts
URL: https://studio.youtube.com/

Channel creation fields:
- Google account (use ProtonMail or Gmail per policy)
- Channel name: "StackKraft — OBS Tools"
- Channel description: short pitch + product link
  Sample: "Tools & automation for ambitious streamers — OBS scripts, sample scenes, and automation workflows. Get the OBS scripts: <Gumroad URL>"
- Channel art & avatar: 2560x1440 art, 98x98 avatar
- Country & Contact email: stackkraft@gmail.com
- Verification: follow Google verification steps (phone)

Upload checklist for each Short:
- Title: include keyword + brand (e.g., "Automate OBS Scenes with Roxy Tools — Quick Demo")
- Description: 1-2 line summary + link to Gumroad product, timestamp if relevant
- Tags: obs, streaming, automation, stackkraft, roxy
- Hashtags: #OBS #Streaming #Automation
- Thumbnail: custom 1280x720 recommended (Shorts will use auto thumb but include good visuals)
- Visibility: Unlisted (for testing) → Public when ready

Acceptance (Human):
- [ ] 3 Shorts uploaded and links saved
- [ ] Analytics capture: views, CTR, watch time in a CSV

---

## 3) TikTok — Business Account & Content API Application
URL: https://www.tiktok.com/business/ & https://developer.tiktok.com/

Account creation fields:
- Email or phone
- Display name: StackKraft
- Username: @stackkraft
- Business name: StackKraft
- Website: https://stackkraft.example (or GitHub page)
- Business address (optional)
- Upload profile image & 1 paragraph bio

TikTok Content API Application (TikTok for Developers) — sample copy
- App Name: StackKraft Content Publisher
- Company: StackKraft (Mark — Founder)
- App Description: "Programmatic content publishing for StackKraft brand — short-form videos automation via official Content Publishing API."
- Redirect URL: https://stackkraft.example/oauth/callback (placeholder, can be changed later)
- Privacy Policy URL: https://stackkraft.example/privacy
- Terms of Service URL: https://stackkraft.example/terms
- Data Use: "We will post videos to brand account only; no scraping or automated behavior beyond official posting endpoints."

Notes & Hints:
- TikTok review may take 3–7 days — track application daily.
- Keep a copy of all submitted docs and receipts.

---

## 4) Quick Checklist for Mark (two-step actions)
1. Create ProtonMail for brand (if not already): https://proton.me/
2. Create Gumroad account and keep payout info ready.
3. Create YouTube channel using new email; upload 3 Shorts manually.
4. Create TikTok Business account; submit Content API application.
5. Paste all resulting public URLs (YouTube, TikTok profile, Gumroad product link) into Slack or a shared doc and notify Claude.

---

## 5) Contacts and Notes
- Support email: stackkraft@gmail.com
- For docs and forms, use the following sample contact: Mark — Founder, +1 (optional), stackkraft@proton.me

---

End of checklist.
