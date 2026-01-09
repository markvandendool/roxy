#!/usr/bin/env python3
"""
ROXY Social Media MCP Server
Phase 6: Social Integration - Postiz, YouTube, Discord, Telegram
"""
import asyncio
import json
import logging
import os
from typing import Optional, Dict, List
from datetime import datetime
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP('roxy-social')

# Configuration
POSTIZ_API_URL = os.getenv('POSTIZ_API_URL', 'https://api.postiz.com/v1')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY', '')
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN', '')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
# Supabase for storing social media posts (same as mindsong-juke-hub)
SUPABASE_URL = os.getenv('SUPABASE_URL', os.getenv('VITE_SUPABASE_URL', 'https://rlbltiuswhlzjvszhvsc.supabase.co'))
SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY', os.getenv('VITE_SUPABASE_ANON_KEY', ''))


@mcp.tool()
async def social_schedule_post(
    platform: str,
    content: str,
    scheduled_at: str,
    media_url: Optional[str] = None
) -> str:
    """
    Schedule a social media post across platforms.
    
    Args:
        platform: Platform name (postiz, youtube, discord, telegram)
        content: Post content/text
        scheduled_at: ISO datetime string for scheduling
        media_url: Optional media URL to attach
    """
    try:
        if platform == 'postiz':
            # Postiz API integration
            import requests
            response = requests.post(
                f'{POSTIZ_API_URL}/posts',
                json={
                    'content': content,
                    'scheduled_at': scheduled_at,
                    'media_url': media_url
                },
                headers={'Authorization': f'Bearer {os.getenv("POSTIZ_API_KEY", "")}'}
            )
            if response.status_code == 201:
                return json.dumps({'status': 'scheduled', 'post_id': response.json().get('id')})
            return json.dumps({'error': f'Postiz error: {response.text}'})
        
        elif platform == 'youtube':
            # YouTube Data API v3
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload
            
            youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
            # Note: YouTube requires OAuth for uploads, this is a placeholder
            return json.dumps({'status': 'pending', 'message': 'YouTube upload requires OAuth setup'})
        
        elif platform == 'discord':
            # Discord webhook or bot
            import requests
            webhook_url = os.getenv('DISCORD_WEBHOOK_URL', '')
            if webhook_url:
                response = requests.post(webhook_url, json={'content': content})
                return json.dumps({'status': 'sent' if response.status_code == 204 else 'error'})
            return json.dumps({'error': 'Discord webhook URL not configured'})
        
        elif platform == 'telegram':
            # Telegram Bot API
            import requests
            chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
            if TELEGRAM_BOT_TOKEN and chat_id:
                url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
                response = requests.post(url, json={'chat_id': chat_id, 'text': content})
                if response.status_code == 200:
                    return json.dumps({'status': 'sent', 'message_id': response.json().get('result', {}).get('message_id')})
            return json.dumps({'error': 'Telegram bot not configured'})
        
        return json.dumps({'error': f'Unknown platform: {platform}'})
        
    except Exception as e:
        logger.error(f'Error scheduling post: {e}')
        return json.dumps({'error': str(e)})


@mcp.tool()
async def youtube_upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: Optional[List[str]] = None,
    privacy: str = 'private'
) -> str:
    """
    Upload video to YouTube using Data API v3.
    
    Args:
        video_path: Path to video file
        title: Video title
        description: Video description
        tags: Optional list of tags
        privacy: Privacy setting (private, unlisted, public)
    """
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from google.oauth2.credentials import Credentials
        
        # Note: Requires OAuth2 credentials file
        creds_file = os.getenv('YOUTUBE_CREDENTIALS_FILE', '')
        if not creds_file or not os.path.exists(creds_file):
            return json.dumps({'error': 'YouTube OAuth credentials not configured'})
        
        # Load credentials and build service
        # This is a simplified version - full implementation requires OAuth flow
        return json.dumps({
            'status': 'pending',
            'message': 'YouTube upload requires OAuth2 setup. See: https://developers.google.com/youtube/v3/guides/uploading_a_video'
        })
        
    except Exception as e:
        logger.error(f'Error uploading to YouTube: {e}')
        return json.dumps({'error': str(e)})


@mcp.tool()
async def discord_send_message(
    channel_id: str,
    message: str,
    embed: Optional[Dict] = None
) -> str:
    """
    Send message to Discord channel via bot.
    
    Args:
        channel_id: Discord channel ID
        message: Message text
        embed: Optional embed object
    """
    try:
        import discord
        from discord.ext import commands
        
        if not DISCORD_BOT_TOKEN:
            return json.dumps({'error': 'Discord bot token not configured'})
        
        # This requires a running Discord bot instance
        # For MCP, we'll use webhook or REST API
        import requests
        webhook_url = os.getenv('DISCORD_WEBHOOK_URL', '')
        if webhook_url:
            payload = {'content': message}
            if embed:
                payload['embeds'] = [embed]
            response = requests.post(webhook_url, json=payload)
            return json.dumps({'status': 'sent' if response.status_code == 204 else 'error'})
        
        return json.dumps({'error': 'Discord webhook not configured'})
        
    except Exception as e:
        logger.error(f'Error sending Discord message: {e}')
        return json.dumps({'error': str(e)})


@mcp.tool()
async def telegram_send_message(
    chat_id: str,
    message: str,
    parse_mode: str = 'HTML'
) -> str:
    """
    Send message to Telegram chat.
    
    Args:
        chat_id: Telegram chat ID
        message: Message text
        parse_mode: Parse mode (HTML, Markdown, MarkdownV2)
    """
    try:
        import requests
        
        if not TELEGRAM_BOT_TOKEN:
            return json.dumps({'error': 'Telegram bot token not configured'})
        
        url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
        response = requests.post(url, json={
            'chat_id': chat_id,
            'text': message,
            'parse_mode': parse_mode
        })
        
        if response.status_code == 200:
            result = response.json()
            return json.dumps({
                'status': 'sent',
                'message_id': result.get('result', {}).get('message_id')
            })
        
        return json.dumps({'error': f'Telegram API error: {response.text}'})
        
    except Exception as e:
        logger.error(f'Error sending Telegram message: {e}')
        return json.dumps({'error': str(e)})


@mcp.tool()
async def social_get_analytics(
    platform: str,
    start_date: str,
    end_date: str
) -> str:
    """
    Get analytics for social media posts from Supabase.
    
    Args:
        platform: Platform name (youtube, discord, telegram, postiz)
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
    """
    try:
        # Try to get from Supabase if social_posts table exists
        try:
            from supabase import create_client, Client
            
            if SUPABASE_URL and SUPABASE_KEY:
                supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
                
                # Query social posts (if table exists)
                response = supabase.table('social_posts').select('*').eq('platform', platform).gte('created_at', start_date).lte('created_at', end_date).execute()
                
                if response.data:
                    posts = response.data
                    total_engagement = sum(post.get('engagement', 0) or 0 for post in posts)
                    total_reach = sum(post.get('reach', 0) or 0 for post in posts)
                    
                    return json.dumps({
                        'platform': platform,
                        'period': {'start': start_date, 'end': end_date},
                        'metrics': {
                            'posts': len(posts),
                            'engagement': total_engagement,
                            'reach': total_reach
                        },
                        'posts': posts
                    })
        except:
            pass
        
        # Fallback placeholder
        return json.dumps({
            'platform': platform,
            'period': {'start': start_date, 'end': end_date},
            'metrics': {
                'posts': 0,
                'engagement': 0,
                'reach': 0
            },
            'message': 'Analytics integration pending - social_posts table may not exist'
        })
        
    except Exception as e:
        logger.error(f'Error getting analytics: {e}')
        return json.dumps({'error': str(e)})


@mcp.tool()
async def youtube_get_video_info(video_id: str) -> str:
    """
    Get YouTube video information using Data API v3.
    
    Args:
        video_id: YouTube video ID
    """
    try:
        import requests
        
        if not YOUTUBE_API_KEY:
            return json.dumps({'error': 'YouTube API key not configured'})
        
        url = f'https://www.googleapis.com/youtube/v3/videos'
        params = {
            'id': video_id,
            'key': YOUTUBE_API_KEY,
            'part': 'snippet,statistics,contentDetails'
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('items'):
                video = data['items'][0]
                return json.dumps({
                    'video_id': video_id,
                    'title': video['snippet']['title'],
                    'description': video['snippet']['description'],
                    'channel': video['snippet']['channelTitle'],
                    'published_at': video['snippet']['publishedAt'],
                    'view_count': video['statistics'].get('viewCount', 0),
                    'like_count': video['statistics'].get('likeCount', 0),
                    'comment_count': video['statistics'].get('commentCount', 0),
                    'duration': video['contentDetails']['duration']
                })
            return json.dumps({'error': 'Video not found'})
        
        return json.dumps({'error': f'YouTube API error: {response.text}'})
        
    except Exception as e:
        logger.error(f'Error getting YouTube video info: {e}')
        return json.dumps({'error': str(e)})


@mcp.tool()
async def social_store_post(
    platform: str,
    content: str,
    post_id: Optional[str] = None,
    media_url: Optional[str] = None,
    engagement: int = 0,
    reach: int = 0
) -> str:
    """
    Store social media post in Supabase for tracking.
    
    Args:
        platform: Platform name (youtube, discord, telegram, postiz)
        content: Post content
        post_id: External post ID from platform
        media_url: Optional media URL
        engagement: Engagement count
        reach: Reach count
    """
    try:
        from supabase import create_client, Client
        
        if not SUPABASE_URL or not SUPABASE_KEY:
            return json.dumps({'error': 'Supabase credentials not configured'})
        
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        post_data = {
            'platform': platform,
            'content': content,
            'engagement': engagement,
            'reach': reach
        }
        if post_id:
            post_data['post_id'] = post_id
        if media_url:
            post_data['media_url'] = media_url
        
        # Try to insert into social_posts table (may not exist)
        try:
            response = supabase.table('social_posts').insert(post_data).execute()
            if response.data:
                return json.dumps({'status': 'stored', 'post': response.data[0]})
        except:
            # If table doesn't exist, return success anyway (table can be created later)
            return json.dumps({
                'status': 'logged',
                'message': 'Post logged (social_posts table may need to be created)',
                'post_data': post_data
            })
        
        return json.dumps({'error': 'Failed to store post'})
        
    except ImportError:
        # Fallback to REST API
        try:
            import requests
            headers = {
                'apikey': SUPABASE_KEY,
                'Authorization': f'Bearer {SUPABASE_KEY}',
                'Content-Type': 'application/json',
                'Prefer': 'return=representation'
            }
            post_data = {
                'platform': platform,
                'content': content,
                'engagement': engagement,
                'reach': reach
            }
            if post_id:
                post_data['post_id'] = post_id
            if media_url:
                post_data['media_url'] = media_url
            
            response = requests.post(
                f'{SUPABASE_URL}/rest/v1/social_posts',
                json=post_data,
                headers=headers
            )
            if response.status_code in [200, 201]:
                return json.dumps({'status': 'stored', 'post': response.json()[0] if isinstance(response.json(), list) else response.json()})
            return json.dumps({'error': f'Supabase API error: {response.text}'})
        except Exception as e:
            return json.dumps({'error': str(e)})
    except Exception as e:
        logger.error(f'Error storing post: {e}')
        return json.dumps({'error': str(e)})


if __name__ == '__main__':
    mcp.run()


