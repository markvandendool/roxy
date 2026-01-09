#!/usr/bin/env python3
"""
ROXY Content Pipeline - Viral Moment Detection
Uses Ollama LLM to analyze transcripts and identify viral-worthy clips
"""
import json
import logging
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OLLAMA_URL = 'http://127.0.0.1:11435/api/generate'
MODEL = 'llama3.2'  # or mistral, mixtral, etc.

@dataclass
class ViralMoment:
    start_time: float
    end_time: float
    title: str
    hook: str
    viral_score: int  # 1-10
    reasoning: str
    category: str  # hook, story, insight, humor, controversy, emotion
    transcript_excerpt: str

ANALYSIS_PROMPT = '''You are a viral content expert analyzing a video transcript. Your job is to identify moments that would make compelling short-form clips (30-90 seconds) for TikTok, YouTube Shorts, and Instagram Reels.

TRANSCRIPT:
{transcript}

SEGMENT TIMESTAMPS:
{segments}

Analyze this transcript and identify up to {max_clips} viral moments. For each moment, provide:
1. Start and end timestamps (in seconds)
2. A catchy title (max 10 words)
3. The hook - the first thing viewers will hear (must grab attention in 3 seconds)
4. Viral score (1-10) based on: emotional impact, shareability, uniqueness, controversy potential
5. Brief reasoning for why this will perform well
6. Category: hook, story, insight, humor, controversy, or emotion

IMPORTANT:
- Focus on moments with strong emotional hooks
- Look for surprising statements, hot takes, or relatable content
- Identify natural story arcs that fit in 30-90 seconds
- Prioritize segments where the speaker is passionate or animated
- Avoid segments that require too much context

Respond ONLY with valid JSON in this format:
{{
  clips: [
    {{
      start_time: 123.5,
      end_time: 178.2,
      title: Catchy Title Here,
      hook: First 3 seconds hook text,
      viral_score: 8,
      reasoning: Why this will go viral,
      category: insight,
      transcript_excerpt: Key quote from this segment
    }}
  ]
}}
'''

class ViralDetector:
    def __init__(self, model: str = MODEL, ollama_url: str = OLLAMA_URL):
        self.model = model
        self.ollama_url = ollama_url
    
    def analyze(self, transcript_data: Dict, max_clips: int = 10) -> List[ViralMoment]:
        """
        Analyze transcript and return ranked viral moments.
        
        Args:
            transcript_data: Output from Transcriber with 'text' and 'segments'
            max_clips: Maximum number of clips to suggest
            
        Returns:
            List of ViralMoment sorted by viral_score descending
        """
        # Prepare segment info for context
        segments_info = []
        for seg in transcript_data.get('segments', []):
            segments_info.append(f"[{seg['start']:.1f}s - {seg['end']:.1f}s] {seg['text']}")
        
        prompt = ANALYSIS_PROMPT.format(
            transcript=transcript_data.get('text', ''),
            segments='\n'.join(segments_info),
            max_clips=max_clips
        )
        
        logger.info(f'Analyzing transcript ({len(transcript_data.get("text", ""))} chars) for viral moments...')
        
        # Call Ollama
        response = requests.post(
            self.ollama_url,
            json={
                'model': self.model,
                'prompt': prompt,
                'stream': False,
                'options': {
                    'temperature': 0.7,
                    'num_predict': 4096
                }
            },
            timeout=300
        )
        
        if response.status_code != 200:
            raise Exception(f'Ollama error: {response.status_code} - {response.text}')
        
        result = response.json()
        raw_response = result.get('response', '')
        
        # Parse JSON from response
        try:
            # Find JSON in response
            json_start = raw_response.find('{')
            json_end = raw_response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = raw_response[json_start:json_end]
                clips_data = json.loads(json_str)
            else:
                raise ValueError('No JSON found in response')
        except json.JSONDecodeError as e:
            logger.error(f'Failed to parse LLM response: {e}')
            logger.debug(f'Raw response: {raw_response}')
            return []
        
        # Convert to ViralMoment objects
        moments = []
        for clip in clips_data.get('clips', []):
            try:
                moment = ViralMoment(
                    start_time=float(clip.get('start_time', 0)),
                    end_time=float(clip.get('end_time', 0)),
                    title=clip.get('title', 'Untitled'),
                    hook=clip.get('hook', ''),
                    viral_score=int(clip.get('viral_score', 5)),
                    reasoning=clip.get('reasoning', ''),
                    category=clip.get('category', 'other'),
                    transcript_excerpt=clip.get('transcript_excerpt', '')
                )
                moments.append(moment)
            except Exception as e:
                logger.warning(f'Failed to parse clip: {e}')
        
        # Sort by viral score
        moments.sort(key=lambda x: x.viral_score, reverse=True)
        
        logger.info(f'Found {len(moments)} viral moments')
        return moments
    
    def to_json(self, moments: List[ViralMoment]) -> str:
        """Convert moments to JSON string."""
        return json.dumps([{
            'start_time': m.start_time,
            'end_time': m.end_time,
            'duration': m.end_time - m.start_time,
            'title': m.title,
            'hook': m.hook,
            'viral_score': m.viral_score,
            'reasoning': m.reasoning,
            'category': m.category,
            'transcript_excerpt': m.transcript_excerpt
        } for m in moments], indent=2)
    
    def save_clips(self, moments: List[ViralMoment], output_path: str):
        """Save clip suggestions to JSON file."""
        with open(output_path, 'w') as f:
            f.write(self.to_json(moments))
        logger.info(f'Saved {len(moments)} clip suggestions to {output_path}')


def detect_viral_moments(transcript_path: str, output_path: str = None, max_clips: int = 10) -> List[ViralMoment]:
    """
    Convenience function to analyze a transcript file.
    """
    with open(transcript_path) as f:
        transcript_data = json.load(f)
    
    detector = ViralDetector()
    moments = detector.analyze(transcript_data, max_clips)
    
    if output_path:
        detector.save_clips(moments, output_path)
    
    return moments


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print('Usage: python viral_detector.py <transcript.json> [output.json] [max_clips]')
        sys.exit(1)
    
    transcript_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else transcript_path.replace('.json', '_clips.json')
    max_clips = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    
    moments = detect_viral_moments(transcript_path, output_path, max_clips)
    
    print(f'\n🎬 Found {len(moments)} viral moments:\n')
    for i, m in enumerate(moments, 1):
        print(f'{i}. [{m.viral_score}/10] {m.title}')
        print(f'   ⏱️  {m.start_time:.1f}s - {m.end_time:.1f}s ({m.end_time - m.start_time:.0f}s)')
        print(f'   🎯 Hook: {m.hook}')
        print(f'   📝 {m.reasoning}')
        print()
