"""
Radio Session Queue & Mixer
Orchestrates music, host segments, and news
"""

import random
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class SegmentType(str, Enum):
    """Types of radio segments"""
    MUSIC = "music"
    HOST_INTRO = "host_intro"
    HOST_TRANSITION = "host_transition"
    HOST_MOTIVATION = "host_motivation"
    HOST_AD = "host_ad"
    NEWS_INTRO = "news_intro"
    NEWS_SEGMENT = "news_segment"


@dataclass
class Segment:
    """A single radio segment"""
    type: SegmentType
    duration_seconds: int
    content: Dict[str, Any]
    host: Optional[str] = None
    generated_at: str = None
    
    def __post_init__(self):
        if self.generated_at is None:
            self.generated_at = datetime.now().isoformat()


class RadioQueue:
    """Manages the queue of segments to play"""
    
    def __init__(self, music_weight: float = 0.5, news_weight: float = 0.3, ad_weight: float = 0.1):
        self.music_weight = music_weight
        self.news_weight = news_weight
        self.ad_weight = ad_weight
        self.queue: List[Segment] = []
        self.played: List[Segment] = []
    
    def update_weights(self, music_weight: float, news_weight: float, ad_weight: float):
        """Update content mix weights"""
        self.music_weight = music_weight
        self.news_weight = news_weight
        self.ad_weight = ad_weight
    
    def decide_next_segment_type(self) -> SegmentType:
        """Decide what type of segment to play next"""
        # Normalize weights
        total = self.music_weight + self.news_weight + self.ad_weight
        if total == 0:
            return SegmentType.MUSIC
        
        music_prob = self.music_weight / total
        news_prob = self.news_weight / total
        ad_prob = self.ad_weight / total
        
        rand = random.random()
        
        if rand < music_prob:
            return SegmentType.MUSIC
        elif rand < music_prob + news_prob:
            return SegmentType.NEWS_SEGMENT
        else:
            return SegmentType.HOST_AD
    
    def add_segment(self, segment: Segment):
        """Add segment to queue"""
        self.queue.append(segment)
    
    def get_next_segment(self) -> Optional[Segment]:
        """Get next segment from queue"""
        if self.queue:
            segment = self.queue.pop(0)
            self.played.append(segment)
            return segment
        return None
    
    def peek_next(self) -> Optional[Segment]:
        """Peek at next segment without removing it"""
        return self.queue[0] if self.queue else None
    
    def queue_length(self) -> int:
        """Get queue length"""
        return len(self.queue)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        return {
            "queued_segments": len(self.queue),
            "played_segments": len(self.played),
            "music_weight": self.music_weight,
            "news_weight": self.news_weight,
            "ad_weight": self.ad_weight
        }


class SessionBuilder:
    """Builds a radio session with segments"""
    
    def __init__(self, duration_minutes: int = 60):
        self.duration_seconds = duration_minutes * 60
        self.queue = RadioQueue()
        self.session_id = datetime.now().isoformat()
    
    async def build(self, 
                   music_tracks: List[Dict[str, Any]],
                   host_generator,
                   news_service,
                   host_personality: str = "alex") -> List[Segment]:
        """Build a complete radio session"""
        
        segments = []
        elapsed = 0
        stalled_iterations = 0

        # Opening segment
        intro = Segment(
            type=SegmentType.HOST_INTRO,
            duration_seconds=10,
            content={
                "text": f"Hey, it's your personal radio station. Let's make this count."
            },
            host=host_personality
        )
        segments.append(intro)
        elapsed += 10

        # Generate segments until we fill the duration
        while elapsed < self.duration_seconds:
            before = elapsed
            segment_type = self.queue.decide_next_segment_type()
            
            if segment_type == SegmentType.MUSIC:
                # Add music track
                if music_tracks:
                    track = random.choice(music_tracks)
                    duration = min(int(track.get("duration", 180)), 300)  # Cap at 5 min
                    
                    segment = Segment(
                        type=SegmentType.MUSIC,
                        duration_seconds=duration,
                        content={
                            "artist": track.get("artist"),
                            "title": track.get("title"),
                            "album": track.get("album"),
                            "stream_url": track.get("stream_url")
                        }
                    )
                    segments.append(segment)
                    elapsed += duration
            
            elif segment_type == SegmentType.NEWS_SEGMENT:
                # Add news with host intro
                headline = await news_service.get_random_headline()
                
                if headline:
                    # News intro by host - AI-generated banter hooking the
                    # listener into the topic, falling back to a plain
                    # headline callout if generation fails
                    intro_text = None
                    try:
                        result = await host_generator(context="news_banter", topic=headline.get("title"))
                        intro_text = result.get("text")
                    except Exception as e:
                        print(f"Host news intro generation failed, using plain headline: {e}")

                    news_intro = Segment(
                        type=SegmentType.NEWS_INTRO,
                        duration_seconds=15,
                        content={
                            "text": intro_text or f"Here's what's happening: {headline.get('title')}",
                            "headline": headline.get("title"),
                            "source": headline.get("source")
                        },
                        host=host_personality
                    )
                    segments.append(news_intro)
                    elapsed += 15
                    
                    # News segment
                    news_seg = Segment(
                        type=SegmentType.NEWS_SEGMENT,
                        duration_seconds=30,
                        content={
                            "title": headline.get("title"),
                            "description": headline.get("description"),
                            "source": headline.get("source"),
                            "url": headline.get("url")
                        }
                    )
                    segments.append(news_seg)
                    elapsed += 30

            elif segment_type == SegmentType.HOST_AD:
                # Generate a fake ad via the AI host, falling back to a
                # placeholder if generation fails (e.g. no API key configured)
                ad_text = "Ad segment placeholder"
                try:
                    result = await host_generator(context="ad_lib")
                    ad_text = result.get("text", ad_text)
                except Exception as e:
                    print(f"Host ad generation failed, using placeholder: {e}")

                ad_segment = Segment(
                    type=SegmentType.HOST_AD,
                    duration_seconds=20,
                    content={"text": ad_text},
                    host=host_personality
                )
                segments.append(ad_segment)
                elapsed += 20

            # Safety valve: if a whole pass through the loop made no
            # progress (e.g. no music tracks AND no news headlines
            # available), don't spin forever waiting on integrations
            # that aren't configured - bail out with what we have.
            if elapsed == before:
                stalled_iterations += 1
                if stalled_iterations >= 20:
                    print("SessionBuilder.build: no content sources available, ending session early")
                    break
            else:
                stalled_iterations = 0

        return segments
    
    def get_session_metadata(self) -> Dict[str, Any]:
        """Get session metadata"""
        return {
            "session_id": self.session_id,
            "created_at": self.session_id,
            "duration_seconds": self.duration_seconds,
            "segment_count": len(self.queue.queue)
        }


class AudioMixer:
    """Mixes audio segments"""
    
    @staticmethod
    async def mix_music_and_voiceover(music_data: bytes, voiceover_data: bytes, fade_music: bool = True) -> bytes:
        """Mix music with voiceover"""
        try:
            from pydub import AudioSegment
            import io
            
            # Load audio
            music = AudioSegment.from_file(io.BytesIO(music_data), format="mp3")
            voiceover = AudioSegment.from_file(io.BytesIO(voiceover_data), format="mp3")
            
            if fade_music:
                # Lower music volume during voiceover
                music_lowered = music - 10  # 10dB quieter
            else:
                music_lowered = music
            
            # Overlay voiceover on music
            mixed = music_lowered.overlay(voiceover, position=0)
            
            # Export to bytes
            output = io.BytesIO()
            mixed.export(output, format="mp3", bitrate="192k")
            return output.getvalue()
        
        except Exception as e:
            print(f"Audio mixing error: {str(e)}")
            # Return original music if mixing fails
            return music_data
