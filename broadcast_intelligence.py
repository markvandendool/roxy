#!/usr/bin/env python3
"""
ROXY Broadcasting Intelligence Module
Content optimization for maximum engagement across platforms
"""
import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger("roxy.broadcast")


class Platform(Enum):
    """Supported broadcasting platforms"""
    YOUTUBE = "youtube"
    TWITCH = "twitch"
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    LINKEDIN = "linkedin"


class ContentType(Enum):
    """Types of content"""
    VIDEO = "video"
    STREAM = "stream"
    SHORT = "short"
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"


@dataclass
class PlatformConfig:
    """Configuration for a platform"""
    name: str
    optimal_length: tuple  # (min, max) in appropriate unit
    best_days: List[str]
    best_hours: List[int]  # 24-hour format
    title_length: tuple = (50, 60)
    hashtag_limit: int = 30
    media_boost: float = 1.0


@dataclass
class ContentAnalysis:
    """Result of content analysis"""
    virality_score: float
    optimal_time: Dict[str, Any]
    platform_recommendations: List[Dict]
    improvements: List[str]
    predicted_performance: Dict[str, Any]
    confidence: float


class BroadcastIntelligence:
    """
    Content optimization engine for maximum engagement.
    
    Features:
    - Virality prediction based on content factors
    - Optimal posting time calculation
    - Platform-specific recommendations
    - Title and thumbnail optimization
    - Audience engagement prediction
    """
    
    # Platform configurations based on industry research
    PLATFORM_CONFIGS = {
        Platform.YOUTUBE: PlatformConfig(
            name="YouTube",
            optimal_length=(10, 20),  # minutes
            best_days=['Tuesday', 'Thursday', 'Saturday'],
            best_hours=[14, 15, 16, 17],  # 2-5 PM EST
            title_length=(50, 60),
            media_boost=1.0
        ),
        Platform.TWITCH: PlatformConfig(
            name="Twitch",
            optimal_length=(120, 240),  # minutes (2-4 hours)
            best_days=['Friday', 'Saturday', 'Sunday'],
            best_hours=[19, 20, 21, 22, 23],  # 7 PM - 12 AM
            media_boost=1.0
        ),
        Platform.TWITTER: PlatformConfig(
            name="Twitter/X",
            optimal_length=(200, 280),  # characters
            best_days=['Monday', 'Tuesday', 'Wednesday', 'Thursday'],
            best_hours=[9, 12, 17, 20],
            hashtag_limit=3,
            media_boost=2.1
        ),
        Platform.INSTAGRAM: PlatformConfig(
            name="Instagram",
            optimal_length=(20, 60),  # seconds for Reels
            best_days=['Monday', 'Wednesday', 'Friday'],
            best_hours=[11, 13, 19, 21],
            hashtag_limit=30,
            media_boost=1.8
        ),
        Platform.TIKTOK: PlatformConfig(
            name="TikTok",
            optimal_length=(15, 60),  # seconds
            best_days=['Tuesday', 'Thursday', 'Friday'],
            best_hours=[19, 20, 21],
            hashtag_limit=5,
            media_boost=2.5
        ),
        Platform.LINKEDIN: PlatformConfig(
            name="LinkedIn",
            optimal_length=(1000, 1500),  # characters
            best_days=['Tuesday', 'Wednesday', 'Thursday'],
            best_hours=[7, 8, 12, 17],
            hashtag_limit=5,
            media_boost=1.4
        )
    }
    
    # Virality trigger words (weighted)
    TRIGGER_WORDS = {
        'high_impact': ['secret', 'revealed', 'shocking', 'exclusive', 'breaking', 'urgent'],
        'medium_impact': ['amazing', 'incredible', 'ultimate', 'essential', 'proven'],
        'engagement': ['you', 'your', 'how', 'why', 'what', 'when'],
        'emotional': ['love', 'hate', 'fear', 'joy', 'angry', 'sad', 'excited'],
        'action': ['get', 'try', 'make', 'start', 'stop', 'learn', 'discover']
    }
    
    # Trending topics (would be fetched from API in production)
    CURRENT_TRENDS = [
        'ai', 'chatgpt', 'claude', 'tech', 'coding', 'python',
        '2026', 'tutorial', 'tips', 'productivity', 'automation'
    ]
    
    def __init__(self):
        """Initialize broadcasting intelligence."""
        self.analysis_cache: Dict[str, ContentAnalysis] = {}
        logger.info("Broadcasting Intelligence initialized")
    
    def analyze_content(self, content: Dict[str, Any]) -> ContentAnalysis:
        """
        Perform comprehensive content analysis.
        
        Args:
            content: Dict containing title, description, tags, platform, etc.
            
        Returns:
            ContentAnalysis with all optimization recommendations
        """
        # Generate cache key
        cache_key = hashlib.md5(json.dumps(content, sort_keys=True).encode()).hexdigest()
        
        if cache_key in self.analysis_cache:
            return self.analysis_cache[cache_key]
        
        analysis = ContentAnalysis(
            virality_score=self._calculate_virality(content),
            optimal_time=self._find_optimal_time(content),
            platform_recommendations=self._recommend_platforms(content),
            improvements=self._suggest_improvements(content),
            predicted_performance=self._predict_metrics(content),
            confidence=0.75
        )
        
        self.analysis_cache[cache_key] = analysis
        return analysis
    
    def _calculate_virality(self, content: Dict) -> float:
        """
        Calculate virality score (0-1) based on content factors.
        
        Factors:
        - Title optimization (30%)
        - Emotional triggers (25%)
        - Curiosity gap (20%)
        - Trending alignment (15%)
        - Format optimization (10%)
        """
        score = 0.0
        
        # Title analysis (30% weight)
        if title := content.get('title', ''):
            title_lower = title.lower()
            
            # Length optimization
            if 50 <= len(title) <= 60:
                score += 0.10
            elif 40 <= len(title) <= 70:
                score += 0.05
            
            # Engagement words
            if any(word in title_lower for word in self.TRIGGER_WORDS['engagement']):
                score += 0.08
            
            # Punctuation and emoji
            if any(char in title for char in ['!', '?', '🔥', '😱', '🚀', '💡']):
                score += 0.05
            
            # Numbers (lists perform well)
            if any(char.isdigit() for char in title):
                score += 0.04
            
            # Power words
            if any(word in title_lower for word in self.TRIGGER_WORDS['high_impact']):
                score += 0.03
        
        # Emotional triggers (25% weight)
        content_text = str(content).lower()
        emotional_count = sum(1 for word in self.TRIGGER_WORDS['emotional'] 
                            if word in content_text)
        score += min(emotional_count * 0.05, 0.25)
        
        # Curiosity gap (20% weight)
        curiosity_indicators = ['teaser', 'preview', 'sneak peek', 'coming soon',
                               'wait for it', 'you won\'t believe', 'the truth about']
        if any(ind in content_text for ind in curiosity_indicators):
            score += 0.20
        elif '...' in content_text or content.get('has_cliffhanger'):
            score += 0.10
        
        # Trending alignment (15% weight)
        trending_match = sum(1 for topic in self.CURRENT_TRENDS if topic in content_text)
        score += min(trending_match * 0.03, 0.15)
        
        # Format optimization (10% weight)
        if content.get('has_thumbnail'):
            score += 0.03
        if content.get('has_video'):
            score += 0.04
        if content.get('has_captions'):
            score += 0.03
        
        return min(score, 1.0)
    
    def _find_optimal_time(self, content: Dict) -> Dict[str, Any]:
        """
        Calculate best posting time based on platform and content type.
        
        Returns:
            Dict with datetime, timezone, and confidence
        """
        platform_name = content.get('platform', 'youtube').lower()
        
        try:
            platform = Platform(platform_name)
        except ValueError:
            platform = Platform.YOUTUBE
        
        config = self.PLATFORM_CONFIGS.get(platform, self.PLATFORM_CONFIGS[Platform.YOUTUBE])
        
        now = datetime.now()
        best_slots = []
        
        # Find next 5 optimal slots
        for days_ahead in range(14):  # Look up to 2 weeks ahead
            future_date = now + timedelta(days=days_ahead)
            day_name = future_date.strftime('%A')
            
            if day_name in config.best_days:
                for hour in config.best_hours:
                    slot = future_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                    if slot > now:
                        # Calculate slot score
                        slot_score = 1.0
                        # Prefer sooner dates
                        slot_score -= days_ahead * 0.02
                        # Prefer prime hours
                        if hour in [14, 15, 19, 20]:
                            slot_score += 0.1
                        
                        best_slots.append({
                            'datetime': slot.isoformat(),
                            'day': day_name,
                            'hour': hour,
                            'score': slot_score
                        })
        
        # Sort by score and take best
        best_slots.sort(key=lambda x: x['score'], reverse=True)
        
        if best_slots:
            best = best_slots[0]
            return {
                'platform': platform.value,
                'datetime': best['datetime'],
                'day': best['day'],
                'hour': best['hour'],
                'timezone': 'Local',
                'confidence': 0.85,
                'alternatives': best_slots[1:4]  # Next 3 best slots
            }
        
        # Fallback
        tomorrow = (now + timedelta(days=1)).replace(hour=14, minute=0)
        return {
            'platform': platform.value,
            'datetime': tomorrow.isoformat(),
            'timezone': 'Local',
            'confidence': 0.50
        }
    
    def _recommend_platforms(self, content: Dict) -> List[Dict]:
        """
        Recommend best platforms for the content.
        
        Returns:
            List of platform recommendations with reasons
        """
        recommendations = []
        
        content_type = content.get('type', 'text')
        content_length = len(content.get('text', content.get('description', '')))
        has_video = content.get('has_video', False)
        is_tutorial = any(word in str(content).lower() 
                        for word in ['tutorial', 'how to', 'guide', 'learn'])
        is_news = any(word in str(content).lower() 
                     for word in ['breaking', 'news', 'update', 'announcement'])
        
        # YouTube - best for long-form video
        if has_video or is_tutorial:
            recommendations.append({
                'platform': 'youtube',
                'priority': 1 if has_video else 2,
                'reason': 'Video content performs best on YouTube',
                'expected_reach': 'High',
                'content_tips': [
                    'Add timestamps in description',
                    'Create custom thumbnail with face',
                    'First 30 seconds are critical'
                ]
            })
        
        # Twitter - best for short updates and engagement
        if content_length < 500 or is_news:
            recommendations.append({
                'platform': 'twitter',
                'priority': 1 if is_news else 3,
                'reason': 'Quick updates and engagement on Twitter/X',
                'expected_reach': 'Medium-High',
                'content_tips': [
                    'Add relevant hashtags (max 3)',
                    'Include media for 2x engagement',
                    'Thread for longer content'
                ]
            })
        
        # LinkedIn - best for professional/technical
        if any(word in str(content).lower() for word in ['professional', 'career', 'business', 'tech']):
            recommendations.append({
                'platform': 'linkedin',
                'priority': 2,
                'reason': 'Professional audience for technical content',
                'expected_reach': 'Medium',
                'content_tips': [
                    'Start with a hook question',
                    'Use line breaks for readability',
                    'End with call to action'
                ]
            })
        
        # TikTok/Instagram - best for short-form
        if content.get('has_short_video') or content_length < 200:
            recommendations.append({
                'platform': 'tiktok',
                'priority': 2,
                'reason': 'High engagement for short-form content',
                'expected_reach': 'High (viral potential)',
                'content_tips': [
                    'Hook in first 3 seconds',
                    'Use trending sounds',
                    'Vertical format required'
                ]
            })
        
        # Sort by priority
        recommendations.sort(key=lambda x: x['priority'])
        return recommendations
    
    def _suggest_improvements(self, content: Dict) -> List[str]:
        """
        Generate specific, actionable improvements.
        
        Returns:
            List of improvement suggestions
        """
        suggestions = []
        
        # Title optimization
        title = content.get('title', '')
        if title:
            if len(title) < 40:
                suggestions.append(f"📝 Expand title from {len(title)} to 50-60 characters for better CTR")
            elif len(title) > 70:
                suggestions.append(f"📝 Shorten title from {len(title)} to under 60 characters")
            
            if not any(char in title for char in ['!', '?', '|', '-', ':']):
                suggestions.append("📝 Add punctuation (!, ?, |) for emotional impact")
            
            if not any(char.isdigit() for char in title):
                suggestions.append("📝 Consider adding a number (e.g., '5 Tips', '3 Secrets')")
            
            title_lower = title.lower()
            if not any(word in title_lower for word in ['you', 'your', 'how', 'why']):
                suggestions.append("📝 Include 'you/your' or 'how/why' for personal connection")
        else:
            suggestions.append("⚠️ Add a compelling title!")
        
        # Thumbnail
        if not content.get('has_thumbnail'):
            suggestions.append("🖼️ Create custom thumbnail with: face + text + high contrast")
        
        # Description
        description = content.get('description', '')
        if len(description) < 100:
            suggestions.append("📄 Expand description to 200+ characters with keywords")
        
        # Tags/Hashtags
        tags = content.get('tags', [])
        if len(tags) < 3:
            suggestions.append("🏷️ Add 5-10 relevant tags for discoverability")
        
        # Video-specific
        if content.get('has_video'):
            if not content.get('has_captions'):
                suggestions.append("💬 Add captions/subtitles (85% watch without sound)")
            if not content.get('has_timestamps'):
                suggestions.append("⏱️ Add chapter timestamps in description")
        
        # Call to action
        if not any(word in str(content).lower() for word in ['subscribe', 'follow', 'like', 'comment', 'share']):
            suggestions.append("📢 Add clear call-to-action (subscribe, follow, etc.)")
        
        return suggestions
    
    def _predict_metrics(self, content: Dict) -> Dict[str, Any]:
        """
        Predict performance metrics based on content analysis.
        
        Returns:
            Dict with estimated views, engagement, shares
        """
        virality = self._calculate_virality(content)
        
        # Base metrics (conservative estimates)
        base_views = content.get('subscriber_count', 1000)
        
        # Virality multiplier (exponential growth potential)
        viral_multiplier = 1 + (virality ** 2) * 10
        
        estimated_views = int(base_views * viral_multiplier)
        engagement_rate = 2 + (virality * 8)  # 2-10% range
        share_rate = virality * 0.05  # 0-5% range
        
        return {
            'estimated_views': {
                'low': int(estimated_views * 0.5),
                'mid': estimated_views,
                'high': int(estimated_views * 2)
            },
            'engagement_rate': f"{engagement_rate:.1f}%",
            'estimated_likes': int(estimated_views * engagement_rate / 100),
            'estimated_comments': int(estimated_views * engagement_rate / 500),
            'estimated_shares': int(estimated_views * share_rate),
            'viral_probability': f"{virality * 100:.0f}%",
            'confidence': 0.70 + (0.20 if virality > 0.5 else 0)
        }
    
    def optimize_title(self, title: str, platform: str = 'youtube') -> Dict[str, Any]:
        """
        Optimize a title for maximum engagement.
        
        Args:
            title: Original title
            platform: Target platform
            
        Returns:
            Dict with optimized title and suggestions
        """
        suggestions = []
        optimized = title
        
        # Length optimization
        if len(title) < 40:
            suggestions.append("Title is too short - aim for 50-60 characters")
        elif len(title) > 70:
            suggestions.append("Title is too long - trim to under 60 characters")
            optimized = title[:57] + "..."
        
        # Power words
        if not any(word in title.lower() for word in self.TRIGGER_WORDS['engagement']):
            suggestions.append("Add engaging words like 'How', 'Why', 'You'")
        
        # Calculate score
        score = self._calculate_virality({'title': title})
        
        return {
            'original': title,
            'optimized': optimized,
            'score': score,
            'suggestions': suggestions,
            'character_count': len(title),
            'optimal_range': '50-60 characters'
        }
    
    def get_trending_topics(self) -> List[Dict[str, Any]]:
        """
        Get current trending topics.
        
        Returns:
            List of trending topics with metadata
        """
        # In production, would fetch from social APIs
        return [
            {'topic': topic, 'growth': 'trending', 'relevance': 0.8}
            for topic in self.CURRENT_TRENDS
        ]
    
    def schedule_content(self, content_list: List[Dict]) -> List[Dict]:
        """
        Generate optimal schedule for multiple pieces of content.
        
        Args:
            content_list: List of content items to schedule
            
        Returns:
            List of scheduled content with optimal times
        """
        scheduled = []
        used_slots = set()
        
        for content in content_list:
            analysis = self.analyze_content(content)
            
            # Find available slot
            optimal = analysis.optimal_time
            slot_key = (optimal.get('datetime', ''), optimal.get('platform', ''))
            
            # If slot is taken, use alternative
            if slot_key in used_slots and 'alternatives' in optimal:
                for alt in optimal['alternatives']:
                    alt_key = (alt['datetime'], optimal.get('platform', ''))
                    if alt_key not in used_slots:
                        optimal['datetime'] = alt['datetime']
                        slot_key = alt_key
                        break
            
            used_slots.add(slot_key)
            
            scheduled.append({
                'content': content,
                'scheduled_time': optimal['datetime'],
                'platform': optimal.get('platform'),
                'virality_score': analysis.virality_score,
                'predicted_performance': analysis.predicted_performance
            })
        
        # Sort by scheduled time
        scheduled.sort(key=lambda x: x['scheduled_time'])
        return scheduled


# Singleton instance
_broadcast_intel: Optional[BroadcastIntelligence] = None


def get_broadcast_intelligence() -> BroadcastIntelligence:
    """Get or create singleton instance."""
    global _broadcast_intel
    if _broadcast_intel is None:
        _broadcast_intel = BroadcastIntelligence()
    return _broadcast_intel


# Convenience functions
def analyze_content(content: Dict) -> Dict:
    """Analyze content for optimization."""
    bi = get_broadcast_intelligence()
    analysis = bi.analyze_content(content)
    return asdict(analysis)


def get_optimal_time(platform: str = 'youtube') -> Dict:
    """Get optimal posting time for platform."""
    bi = get_broadcast_intelligence()
    return bi._find_optimal_time({'platform': platform})


def optimize_title(title: str, platform: str = 'youtube') -> Dict:
    """Optimize title for platform."""
    bi = get_broadcast_intelligence()
    return bi.optimize_title(title, platform)


def predict_performance(content: Dict) -> Dict:
    """Predict content performance."""
    bi = get_broadcast_intelligence()
    return bi._predict_metrics(content)
