"""LinkedIn platform implementation."""
import os
import json
from typing import Optional
from .base import Platform, PlatformConfig, UploadResult


class LinkedInPlatform(Platform):
    """LinkedIn video posting implementation."""

    def __init__(self, config_path: Optional[str] = None):
        super().__init__(config_path)
        self.config_file = config_path or "linkedin_config.json"

    @property
    def name(self) -> str:
        return "linkedin"

    @property
    def display_name(self) -> str:
        return "LinkedIn"

    @property
    def config(self) -> PlatformConfig:
        return PlatformConfig(
            max_duration=600,  # 10 minutes
            min_duration=3,
            aspect_ratio="16:9",
            max_file_size=200 * 1024 * 1024,
            supported_formats=["mp4", "mov"],
            max_title_length=200,
            max_description_length=3000,
            max_tags=30,
            max_hashtags=30,
            requires_auth=True,
        )

    def authenticate(self) -> bool:
        """Authenticate with LinkedIn API."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    if config.get("access_token"):
                        self._authenticated = True
                        return True
            print("[LinkedIn] Config file needed. See: https://docs.microsoft.com/en-us/linkedin/")
            return False
        except:
            return False

    def upload(self, video_path: str, title: str, description: str, tags: Optional[list[str]] = None, **kwargs) -> UploadResult:
        """Upload video to LinkedIn."""
        if not self.is_authenticated() and not self.authenticate():
            return UploadResult(success=False, platform=self.display_name, error="Auth failed")

        valid, error = self.validate_video(video_path)
        if not valid:
            return UploadResult(success=False, platform=self.display_name, error=error)

        print(f"[LinkedIn] Ready to upload: {title[:50]}...")
        return UploadResult(
            success=False,
            platform=self.display_name,
            error="LinkedIn API requires approved app and OAuth. See: https://learn.microsoft.com/en-us/linkedin/marketing/integrations/community-management/shares/ugc-post-api"
        )
