"""Facebook Reels platform implementation."""
import os
import json
from typing import Optional
from .base import Platform, PlatformConfig, UploadResult


class FacebookReelsPlatform(Platform):
    """Facebook Reels implementation."""

    def __init__(self, config_path: Optional[str] = None):
        super().__init__(config_path)
        self.config_file = config_path or "facebook_config.json"

    @property
    def name(self) -> str:
        return "facebook"

    @property
    def display_name(self) -> str:
        return "Facebook Reels"

    @property
    def config(self) -> PlatformConfig:
        return PlatformConfig(
            max_duration=90,
            min_duration=3,
            aspect_ratio="9:16",
            max_file_size=1024 * 1024 * 1024,  # 1 GB
            supported_formats=["mp4", "mov"],
            max_title_length=0,
            max_description_length=2200,
            max_tags=30,
            max_hashtags=30,
            requires_auth=True,
        )

    def authenticate(self) -> bool:
        """Authenticate with Facebook Graph API."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    if config.get("access_token"):
                        self._authenticated = True
                        return True
            print("[Facebook] Config file needed. See: https://developers.facebook.com/")
            return False
        except:
            return False

    def upload(self, video_path: str, title: str, description: str, tags: Optional[list[str]] = None, **kwargs) -> UploadResult:
        """Upload video as Facebook Reel."""
        if not self.is_authenticated() and not self.authenticate():
            return UploadResult(success=False, platform=self.display_name, error="Auth failed")

        valid, error = self.validate_video(video_path)
        if not valid:
            return UploadResult(success=False, platform=self.display_name, error=error)

        caption = description
        if tags:
            caption = f"{description}\n\n{self.format_hashtags(tags)}"

        print(f"[Facebook] Ready to upload: {caption[:50]}...")
        return UploadResult(
            success=False,
            platform=self.display_name,
            error="Facebook Graph API requires app approval and video URL. See: https://developers.facebook.com/docs/video-api/"
        )
