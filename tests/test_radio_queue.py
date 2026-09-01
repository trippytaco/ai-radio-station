"""
RadioQueue / SessionBuilder unit tests.

Regression coverage for the bugs found/fixed on 2026-08-31:
- host_generator was accepted but never called (HOST_AD / NEWS_INTRO had
  no real AI-generated content)
- infinite loop when no music tracks AND no news headlines are available
"""
import asyncio

import pytest

from radio_queue import RadioQueue, SegmentType, SessionBuilder


# ---------------------------------------------------------------------------
# RadioQueue weighting
# ---------------------------------------------------------------------------

def test_decide_next_segment_type_respects_zero_total():
    queue = RadioQueue(music_weight=0, news_weight=0, ad_weight=0)
    assert queue.decide_next_segment_type() == SegmentType.MUSIC


def test_decide_next_segment_type_all_music(monkeypatch):
    queue = RadioQueue(music_weight=1, news_weight=0, ad_weight=0)
    monkeypatch.setattr("random.random", lambda: 0.999)
    assert queue.decide_next_segment_type() == SegmentType.MUSIC


def test_queue_fifo_order():
    from radio_queue import Segment

    queue = RadioQueue()
    a = Segment(type=SegmentType.MUSIC, duration_seconds=1, content={})
    b = Segment(type=SegmentType.MUSIC, duration_seconds=1, content={})
    queue.add_segment(a)
    queue.add_segment(b)

    assert queue.peek_next() is a
    assert queue.get_next_segment() is a
    assert queue.get_next_segment() is b
    assert queue.get_next_segment() is None
    assert queue.queue_length() == 0


# ---------------------------------------------------------------------------
# SessionBuilder.build
# ---------------------------------------------------------------------------

class FakeNewsService:
    """Always has a headline available."""
    async def get_random_headline(self, enabled_sources=None):
        return {"title": "Big news", "source": "BBC News", "description": "d", "url": "u"}


class NoNewsService:
    """Never has a headline (e.g. no news API keys configured)."""
    async def get_random_headline(self, enabled_sources=None):
        return None


async def fake_host_generator(context=None, topic=None):
    return {"text": f"[{context}] generated banter about {topic}"}


async def failing_host_generator(context=None, topic=None):
    raise RuntimeError("ANTHROPIC_API_KEY not configured")


MUSIC_TRACKS = [{"artist": "A", "title": "T", "album": "Al", "duration": 30, "stream_url": "u"}]


async def test_build_uses_host_generator_for_ads(monkeypatch):
    # Force every non-intro segment to be an ad, deterministically.
    monkeypatch.setattr("random.random", lambda: 0.99)  # music_prob(~0.55) < 0.99 < ... -> ad bucket
    builder = SessionBuilder(duration_minutes=1)

    segments = await builder.build(
        music_tracks=[],
        host_generator=fake_host_generator,
        news_service=NoNewsService(),
        host_personality="alex",
    )

    ad_segments = [s for s in segments if s.type == SegmentType.HOST_AD]
    assert ad_segments, "expected at least one ad segment"
    assert "generated banter" in ad_segments[0].content["text"]


async def test_build_falls_back_to_placeholder_when_generator_fails(monkeypatch):
    monkeypatch.setattr("random.random", lambda: 0.99)
    builder = SessionBuilder(duration_minutes=1)

    segments = await builder.build(
        music_tracks=[],
        host_generator=failing_host_generator,
        news_service=NoNewsService(),
        host_personality="alex",
    )

    ad_segments = [s for s in segments if s.type == SegmentType.HOST_AD]
    assert ad_segments
    assert ad_segments[0].content["text"] == "Ad segment placeholder"


async def test_build_news_intro_uses_host_generator(monkeypatch):
    monkeypatch.setattr("random.random", lambda: 0.6)  # lands in the news bucket
    builder = SessionBuilder(duration_minutes=1)

    segments = await builder.build(
        music_tracks=[],
        host_generator=fake_host_generator,
        news_service=FakeNewsService(),
        host_personality="alex",
    )

    intros = [s for s in segments if s.type == SegmentType.NEWS_INTRO]
    assert intros
    assert "generated banter about Big news" in intros[0].content["text"]


async def test_build_terminates_when_no_content_sources_available():
    """
    Regression test: previously, if music_tracks was empty AND the news
    service never returned a headline, the while loop made zero progress
    per iteration and never terminated. Ad segments always succeed
    regardless of source availability (host_generator failure just falls
    back to placeholder text), so to deterministically hit the true
    zero-progress case, ad_weight is also set to 0 - only music/news are
    ever selected, and both are unavailable here.
    """
    builder = SessionBuilder(duration_minutes=60)
    builder.queue.update_weights(music_weight=0.5, news_weight=0.5, ad_weight=0)

    segments = await asyncio.wait_for(
        builder.build(
            music_tracks=[],
            host_generator=failing_host_generator,
            news_service=NoNewsService(),
            host_personality="alex",
        ),
        timeout=5,
    )

    # Only the fixed opening intro segment should exist - no infinite spin.
    assert len(segments) == 1
    assert segments[0].type == SegmentType.HOST_INTRO


async def test_build_with_only_music_available_terminates(monkeypatch):
    monkeypatch.setattr("random.random", lambda: 0.1)  # always music bucket
    builder = SessionBuilder(duration_minutes=2)

    segments = await asyncio.wait_for(
        builder.build(
            music_tracks=MUSIC_TRACKS,
            host_generator=failing_host_generator,
            news_service=NoNewsService(),
            host_personality="alex",
        ),
        timeout=5,
    )

    assert any(s.type == SegmentType.MUSIC for s in segments)
