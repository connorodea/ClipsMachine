"""
Twitter/X platform implementation for video posts.
"""

import os
import json
import requests
from typing import Optional
from .base import Platform, PlatformConfig, UploadResult


class TwitterPlatform(Platform):
    """Twitter/X platform implementation."""

    def __init__(self, config_path: Optional[str] = None):
        super().__init__(config_path)
        self.config_file = config_path or "twitter_config.json"
        self.bearer_token = None

    @property
    def name(self) -> str:
        return "twitter"

    @property
    def display_name(self) -> str:
        return "Twitter/X"

    @property
    def config(self) -> PlatformConfig:
        return PlatformConfig(
            max_duration=140,  # 2 minutes 20 seconds
            min_duration=0.5,
            aspect_ratio="16:9",  # Landscape preferred
            max_file_size=512 * 1024 * 1024,  # 512 MB
            supported_formats=["mp4", "mov"],
            max_title_length=280,  # Tweet character limit
            max_description_length=280,
            max_tags=10,
            max_hashtags=10,
            requires_auth=True,
            rate_limit_per_day=300,
        )

    def authenticate(self) -> bool:
        """Authenticate with Twitter API v2."""
        try:
            if not os.path.exists(self.config_file):
                print(f"[Twitter] Error: {self.config_file} not found")
                print("[Twitter] See: https://developer.twitter.com/en/docs/twitter-api")
                return False

            with open(self.config_file, 'r') as f:
                config = json.load(f)

            self.bearer_token = config.get("bearer_token")
            if not self.bearer_token:
                print("[Twitter] Error: bearer_token required")
                return False

            self._authenticated = True
            return True
        except Exception as e:
            print(f"[Twitter] Auth failed: {e}")
            return False

    def upload(self, video_path: str, title: str, description: str, tags: Optional[list[str]] = None, **kwargs) -> UploadResult:
        """Upload video to Twitter/X."""
        if not self.is_authenticated() and not self.authenticate():
            return UploadResult(success=False, platform=self.display_name, error="Auth failed")

        valid, error = self.validate_video(video_path)
        if not valid:
            return UploadResult(success=False, platform=self.display_name, error=error)

        tweet_text = f"{title}\n\n{description}" if description else title
        if tags:
            tweet_text = f"{tweet_text}\n\n{self.format_hashtags(tags)}"
        tweet_text = tweet_text[:280]

        print(f"[Twitter] Ready to upload. Tweet: {tweet_text[:50]}...")
        return UploadResult(
            success=False,
            platform=self.display_name,
            error="Twitter API requires tweepy library and OAuth. Install: pip install tweepy"
        )
