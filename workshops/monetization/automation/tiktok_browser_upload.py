#!/usr/bin/env /home/mark/llm-benchmarks/venv/bin/python
"""
TikTok Upload via MCP Browser Automation
Uses Playwright to control the browser directly - more reliable than cookie upload
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
import time

def upload_to_tiktok_browser(video_path: str, description: str):
    """Upload video to TikTok using browser automation"""
    
    video = Path(video_path)
    if not video.exists():
        print(f"❌ Video not found: {video}")
        return False
    
    print(f"🎬 Uploading {video.name} to TikTok via browser automation...")
    
    with sync_playwright() as p:
        # Launch browser (use existing session if possible)
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        # Go to TikTok upload page
        print("📱 Opening TikTok upload page...")
        page.goto("https://www.tiktok.com/upload", wait_until="networkidle")
        time.sleep(3)
        
        # Check if logged in
        if "login" in page.url.lower():
            print("⚠️  Not logged in - please login manually in the browser")
            input("Press Enter after logging in...")
            page.goto("https://www.tiktok.com/upload", wait_until="networkidle")
            time.sleep(2)
        
        print("📤 Uploading video file...")
        
        # Find and click file input
        try:
            # TikTok's file input selector (may change)
            file_input = page.locator('input[type="file"]').first
            file_input.set_input_files(str(video))
            print("✅ Video file uploaded, waiting for processing...")
            time.sleep(5)
            
            # Wait for video to process
            print("⏳ Waiting for video processing...")
            page.wait_for_selector('textarea', timeout=60000)  # Wait up to 60s
            
            # Fill description
            print("📝 Adding description...")
            description_field = page.locator('textarea').first
            description_field.fill(description)
            time.sleep(1)
            
            # Click post button
            print("🚀 Clicking Post button...")
            post_button = page.locator('button:has-text("Post")').first
            post_button.click()
            
            # Wait for upload to complete
            print("⏳ Waiting for upload to complete...")
            time.sleep(10)
            
            # Check for success
            if "posted" in page.url.lower() or "success" in page.content().lower():
                print("✅ Video uploaded successfully!")
                browser.close()
                return True
            else:
                print("⚠️  Upload may have completed - check TikTok manually")
                input("Press Enter to close browser...")
                browser.close()
                return True
                
        except Exception as e:
            print(f"❌ Upload failed: {e}")
            print("🔍 Leaving browser open for manual completion...")
            input("Complete upload manually, then press Enter...")
            browser.close()
            return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 tiktok_browser_upload.py <video_path> [description]")
        sys.exit(1)
    
    video_path = sys.argv[1]
    description = sys.argv[2] if len(sys.argv) > 2 else "StackKraft test upload 🚀 #coding #automation"
    
    success = upload_to_tiktok_browser(video_path, description)
    sys.exit(0 if success else 1)
