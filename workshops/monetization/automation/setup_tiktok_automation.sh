#!/bin/bash
# TikTok Browser Automation Setup (No API needed!)

echo "🎬 Setting up TikTok automation with tiktok-uploader..."

# 1. Install package
pip install tiktok-uploader

# 2. Save cookies from browser
echo "
📋 NEXT STEPS:

1. Open TikTok in Chrome/Firefox: https://www.tiktok.com
2. Login as stackkraft (already done)
3. Install 'Get cookies.txt' extension:
   - Chrome: https://chrome.google.com/webstore/detail/get-cookiestxt/bgaddhkoddajcdgocldbbfleckgcbcid
   - Firefox: https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/
4. Click extension icon → Export cookies for tiktok.com
5. Save as: ~/.roxy/workshops/monetization/.tiktok_cookies.txt
6. Run: chmod 600 ~/.roxy/workshops/monetization/.tiktok_cookies.txt

Then test upload:
  python3 content_publisher.py --video /tmp/stackkraft_test_001.mp4 --platforms tiktok
"
