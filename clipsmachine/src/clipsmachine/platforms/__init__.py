"""
Multi-platform social media upload support for ClipsMachine.
Supports YouTube Shorts, Instagram Reels, TikTok, Twitter/X, LinkedIn, and Facebook.
"""

from .base import Platform, UploadResult
from .youtube_shorts import YouTubeShortsplatform
from .instagram import InstagramReelsplatform
from .tiktok import TikTokPlatform
from .twitter import TwitterPlatform
from .linkedin import LinkedInPlatform
from .facebook import FacebookReelsPlatform

__all__ = [
    "Platform",
    "UploadResult",
    "YouTubeShortsplatform",
    "InstagramReelsplatform",
    "TikTokPlatform",
    "TwitterPlatform",
    "LinkedInPlatform",
    "FacebookReelsPlatform",
    "get_platform",
    "get_all_platforms",
]


# Platform registry
PLATFORMS = {
    "youtube": YouTubeShortsplatform,
    "instagram": InstagramReelsplatform,
    "tiktok": TikTokPlatform,
    "twitter": TwitterPlatform,
    "linkedin": LinkedInPlatform,
    "facebook": FacebookReelsPlatform,
}


def get_platform(name: str) -> type[Platform]:
    """Get platform class by name."""
    name = name.lower()
    if name not in PLATFORMS:
        available = ", ".join(PLATFORMS.keys())
        raise ValueError(f"Unknown platform '{name}'. Available: {available}")
    return PLATFORMS[name]


def get_all_platforms() -> list[str]:
    """Get list of all supported platform names."""
    return list(PLATFORMS.keys())
