#!/usr/bin/env python3
"""
Content Publisher - One Command, All Platforms
Uses existing Roxy infrastructure + official APIs

Architecture:
- clip_extractor.py: Opus Clip killer (viral moment detection)
- broadcast_intelligence.py: Platform optimization + timing
- Official APIs: YouTube, Twitter, Reddit
- Unofficial: tiktok-uploader (works great)

Usage:
    python3 content_publisher.py --video path/to/video.mp4
    python3 content_publisher.py --video path/to/video.mp4 --platforms youtube,tiktok
    python3 content_publisher.py --extract-clips --video raw_stream.mp4  # Extract viral clips first
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add Roxy to path
sys.path.insert(0, str(Path.home() / ".roxy"))

# Import existing Roxy infrastructure
try:
    from broadcast_intelligence import analyze_content, get_optimal_time
    from clip_extractor import process_video
except ImportError as e:
    print(f"[ERROR] Missing Roxy infrastructure: {e}")
    print("Make sure broadcast_intelligence.py and clip_extractor.py are in ~/.roxy/")
    sys.exit(1)


class ContentPublisher:
    """
    Publish content to all platforms with one command
    
    Features:
    - Automatic platform optimization (aspect ratios, lengths)
    - Virality analysis via existing broadcast_intelligence
    - Optimal posting time calculation
    - Credential management
    """
    
    def __init__(self, credentials_file: Optional[Path] = None):
        if credentials_file is None:
            credentials_file = Path.home() / ".roxy" / "workshops" / "monetization" / ".credentials.json"
        
        self.creds_file = credentials_file
        self.creds = self._load_credentials()
    
    def _load_credentials(self) -> Dict:
        """Load credentials from secure file"""
        if not self.creds_file.exists():
            print(f"[WARN] No credentials found at {self.creds_file}")
            print("Run manual account setup first, then save credentials to this file")
            return {}
        
        with open(self.creds_file) as f:
            return json.load(f)
    
    def extract_viral_clips(self, video_path: Path, output_dir: Optional[Path] = None) -> List[Dict]:
        """
        Use existing clip_extractor.py to find viral moments
        
        This is the Opus Clip killer - uses Whisper + LLM
        """
        if output_dir is None:
            output_dir = Path.home() / ".roxy" / "clips" / video_path.stem
        
        print(f"\n{'='*60}")
        print(f"  EXTRACTING VIRAL CLIPS")
        print(f"{'='*60}")
        print(f"Video: {video_path}")
        print(f"Output: {output_dir}\n")
        
        # Call existing clip extractor
        clips = process_video(video_path, output_dir, min_score=70)
        
        print(f"\n✅ Extracted {len(clips)} viral clips")
        return clips
    
    def analyze_for_platform(self, video_path: Path, platform: str, metadata: Dict) -> Dict:
        """
        Use existing broadcast_intelligence.py for optimization
        
        Returns optimized metadata + best posting time
        """
        content = {
            "title": metadata.get("title", ""),
            "description": metadata.get("description", ""),
            "platform": platform,
            "has_video": True,
            "tags": metadata.get("tags", [])
        }
        
        # Use existing Roxy broadcast intelligence
        analysis = analyze_content(content)
        optimal_time = get_optimal_time(platform)
        
        return {
            "virality_score": analysis.get("virality_score", 0),
            "optimal_time": optimal_time,
            "improvements": analysis.get("improvements", []),
            "predicted_reach": analysis.get("predicted_performance", {})
        }
    
    def publish_to_youtube(self, video_path: Path, metadata: Dict) -> Dict:
        """
        YouTube Shorts via official YouTube Data API v3
        
        Requires:
        - Google account with YouTube channel
        - YouTube Data API enabled
        - OAuth credentials saved to .credentials.json
        """
        if "youtube" not in self.creds:
            return {"error": "YouTube credentials not found. Set up OAuth first."}
        
        try:
            from googleapiclient.discovery import build
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            import pickle
            
            # Load OAuth token
            creds = None
            token_file = Path.home() / ".roxy" / "workshops" / "monetization" / ".youtube_token.pickle"
            
            if token_file.exists():
                with open(token_file, 'rb') as f:
                    creds = pickle.load(f)
            
            # Build YouTube service
            youtube = build('youtube', 'v3', credentials=creds)
            
            # Upload video
            request = youtube.videos().insert(
                part="snippet,status",
                body={
                    "snippet": {
                        "title": metadata['title'],
                        "description": f"{metadata['description']}\n\n🔗 {self.creds.get('gumroad', {}).get('product_url', '')}",
                        "tags": metadata.get('tags', []),
                        "categoryId": "28"  # Science & Technology
                    },
                    "status": {
                        "privacyStatus": "public",
                        "selfDeclaredMadeForKids": False
                    }
                },
                media_body=str(video_path)
            )
            
            response = request.execute()
            
            return {
                "success": True,
                "platform": "youtube",
                "video_id": response['id'],
                "url": f"https://youtube.com/shorts/{response['id']}"
            }
            
        except Exception as e:
            return {"error": f"YouTube upload failed: {e}"}
    
    def publish_to_tiktok(self, video_path: Path, metadata: Dict) -> Dict:
        """
        TikTok via tiktok-uploader (unofficial but works)
        
        Requires:
        - TikTok account created manually
        - Cookies saved from browser session (one-time)
        - pip install tiktok-uploader
        """
        if "tiktok" not in self.creds:
            return {"error": "TikTok credentials not found. Save cookies first."}
        
        try:
            from tiktok_uploader.upload import upload_video
            
            # TikTok description (no external links allowed in description)
            description = f"{metadata['description']}\n\n🔗 Link in bio"
            
            result = upload_video(
                str(video_path),
                description=description[:2200],  # TikTok limit
                cookies=self.creds['tiktok']['cookies']
            )
            
            return {
                "success": True,
                "platform": "tiktok",
                "result": result
            }
            
        except Exception as e:
            return {"error": f"TikTok upload failed: {e}"}
    
    def publish_to_twitter(self, video_path: Path, metadata: Dict) -> Dict:
        """
        Twitter/X via official API v2
        
        Requires:
        - Twitter Developer account (free tier: 1500 tweets/month)
        - API keys saved to .credentials.json
        - pip install tweepy
        """
        if "twitter" not in self.creds:
            return {"error": "Twitter credentials not found. Get API keys first."}
        
        try:
            import tweepy
            
            # Authenticate
            client = tweepy.Client(
                bearer_token=self.creds['twitter'].get('bearer_token'),
                consumer_key=self.creds['twitter'].get('api_key'),
                consumer_secret=self.creds['twitter'].get('api_secret'),
                access_token=self.creds['twitter'].get('access_token'),
                access_token_secret=self.creds['twitter'].get('access_secret')
            )
            
            # Upload media (need API v1.1 for media)
            auth = tweepy.OAuth1UserHandler(
                self.creds['twitter']['api_key'],
                self.creds['twitter']['api_secret'],
                self.creds['twitter']['access_token'],
                self.creds['twitter']['access_secret']
            )
            api = tweepy.API(auth)
            
            media = api.media_upload(str(video_path))
            
            # Post tweet with video
            tweet_text = f"{metadata['description']}\n\n{self.creds.get('gumroad', {}).get('product_url', '')}"
            
            response = client.create_tweet(
                text=tweet_text[:280],
                media_ids=[media.media_id]
            )
            
            return {
                "success": True,
                "platform": "twitter",
                "tweet_id": response.data['id'],
                "url": f"https://twitter.com/i/status/{response.data['id']}"
            }
            
        except Exception as e:
            return {"error": f"Twitter post failed: {e}"}
    
    def publish_to_reddit(self, video_path: Path, metadata: Dict, subreddit: str = "learnprogramming") -> Dict:
        """
        Reddit via PRAW (official wrapper)
        
        Requires:
        - Reddit account created manually
        - App created at reddit.com/prefs/apps
        - Credentials saved to .credentials.json
        - pip install praw
        """
        if "reddit" not in self.creds:
            return {"error": "Reddit credentials not found. Create app first."}
        
        try:
            import praw
            
            reddit = praw.Reddit(
                client_id=self.creds['reddit']['client_id'],
                client_secret=self.creds['reddit']['secret'],
                user_agent="RoughDraft Content Bot v1.0",
                username=self.creds['reddit']['username'],
                password=self.creds['reddit']['password']
            )
            
            sub = reddit.subreddit(subreddit)
            
            submission = sub.submit_video(
                title=metadata['title'],
                video_path=str(video_path),
                without_websockets=True
            )
            
            return {
                "success": True,
                "platform": "reddit",
                "post_id": submission.id,
                "url": submission.url
            }
            
        except Exception as e:
            return {"error": f"Reddit post failed: {e}"}
    
    def publish_everywhere(
        self,
        video_path: Path,
        metadata: Dict,
        platforms: List[str] = ["youtube", "tiktok", "twitter", "reddit"]
    ) -> Dict[str, Dict]:
        """
        Publish to all platforms with one command
        
        Returns results for each platform
        """
        results = {}
        
        print(f"\n{'='*60}")
        print(f"  PUBLISHING TO {len(platforms)} PLATFORMS")
        print(f"{'='*60}")
        print(f"Video: {video_path}")
        print(f"Platforms: {', '.join(platforms)}\n")
        
        # Analyze for each platform
        for platform in platforms:
            analysis = self.analyze_for_platform(video_path, platform, metadata)
            print(f"\n{platform.upper()} Analysis:")
            print(f"  Virality Score: {analysis['virality_score']:.1f}/100")
            print(f"  Optimal Time: {analysis['optimal_time'].get('datetime', 'N/A')}")
            print(f"  Improvements: {len(analysis['improvements'])} suggestions")
        
        # Publish to each platform
        print(f"\n{'='*60}")
        print(f"  UPLOADING...")
        print(f"{'='*60}\n")
        
        if "youtube" in platforms:
            print("▶ Uploading to YouTube...")
            results['youtube'] = self.publish_to_youtube(video_path, metadata)
        
        if "tiktok" in platforms:
            print("▶ Uploading to TikTok...")
            results['tiktok'] = self.publish_to_tiktok(video_path, metadata)
        
        if "twitter" in platforms:
            print("▶ Posting to Twitter...")
            results['twitter'] = self.publish_to_twitter(video_path, metadata)
        
        if "reddit" in platforms:
            print("▶ Posting to Reddit...")
            results['reddit'] = self.publish_to_reddit(video_path, metadata)
        
        # Print results
        print(f"\n{'='*60}")
        print(f"  RESULTS")
        print(f"{'='*60}\n")
        
        for platform, result in results.items():
            if result.get("success"):
                print(f"✅ {platform.upper()}: {result.get('url', 'Posted successfully')}")
            else:
                print(f"❌ {platform.upper()}: {result.get('error', 'Unknown error')}")
        
        return results


def main():
    parser = argparse.ArgumentParser(description="Publish content to all platforms")
    parser.add_argument("--video", type=Path, required=True, help="Video file to publish")
    parser.add_argument("--title", type=str, help="Video title")
    parser.add_argument("--description", type=str, help="Video description")
    parser.add_argument("--tags", type=str, help="Comma-separated tags")
    parser.add_argument("--platforms", type=str, default="youtube,tiktok,twitter,reddit", 
                        help="Platforms to publish to (comma-separated)")
    parser.add_argument("--extract-clips", action="store_true", 
                        help="Extract viral clips first using Opus Clip Killer")
    parser.add_argument("--metadata-file", type=Path, 
                        help="JSON file with metadata (overrides command-line args)")
    
    args = parser.parse_args()
    
    if not args.video.exists():
        print(f"[ERROR] Video not found: {args.video}")
        sys.exit(1)
    
    # Load metadata
    if args.metadata_file and args.metadata_file.exists():
        with open(args.metadata_file) as f:
            metadata = json.load(f)
    else:
        metadata = {
            "title": args.title or args.video.stem.replace("_", " ").title(),
            "description": args.description or "Check out this content!",
            "tags": args.tags.split(",") if args.tags else []
        }
    
    # Initialize publisher
    publisher = ContentPublisher()
    
    # Extract clips if requested
    if args.extract_clips:
        clips = publisher.extract_viral_clips(args.video)
        print(f"\n✅ Extracted {len(clips)} clips to ~/.roxy/clips/{args.video.stem}/")
        print("\nRe-run with --video pointing to extracted clips to publish")
        return
    
    # Publish
    platforms = args.platforms.split(",")
    results = publisher.publish_everywhere(args.video, metadata, platforms)
    
    # Save results
    results_file = args.video.parent / f"{args.video.stem}_publish_results.json"
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "video": str(args.video),
            "metadata": metadata,
            "results": results
        }, f, indent=2)
    
    print(f"\n📊 Results saved to: {results_file}")


if __name__ == "__main__":
    main()
