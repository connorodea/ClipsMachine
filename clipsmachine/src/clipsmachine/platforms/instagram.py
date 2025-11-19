"""
Instagram Reels platform implementation.
Uploads videos as Instagram Reels using Instagram Graph API.
"""

import os
import json
import time
import requests
from typing import Optional

from .base import Platform, PlatformConfig, UploadResult


class InstagramReelsplatform(Platform):
    """Instagram Reels platform implementation."""

    API_VERSION = "v18.0"
    BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize Instagram Reels platform.

        Args:
            config_path: Path to Instagram config JSON file with access_token and instagram_account_id
        """
        super().__init__(config_path)
        self.config_file = config_path or "instagram_config.json"
        self.access_token = None
        self.instagram_account_id = None

    @property
    def name(self) -> str:
        return "instagram"

    @property
    def display_name(self) -> str:
        return "Instagram Reels"

    @property
    def config(self) -> PlatformConfig:
        return PlatformConfig(
            max_duration=90,  # Instagram Reels max 90 seconds
            min_duration=1,
            aspect_ratio="9:16",  # Vertical
            max_file_size=100 * 1024 * 1024,  # 100 MB recommended
            supported_formats=["mp4", "mov"],
            max_title_length=0,  # Reels don't have titles
            max_description_length=2200,  # Caption limit
            max_tags=30,
            max_hashtags=30,
            requires_auth=True,
            rate_limit_per_day=25,  # Instagram has strict limits
        )

    def authenticate(self) -> bool:
        """
        Authenticate with Instagram Graph API.

        Requires config file with:
        {
            "access_token": "YOUR_INSTAGRAM_ACCESS_TOKEN",
            "instagram_account_id": "YOUR_INSTAGRAM_BUSINESS_ACCOUNT_ID"
        }

        Get these from: https://developers.facebook.com/apps/
        """
        try:
            if not os.path.exists(self.config_file):
                print(f"[Instagram] Error: {self.config_file} not found")
                print("[Instagram] Create config file with access_token and instagram_account_id")
                print("[Instagram] See: https://developers.facebook.com/docs/instagram-api/getting-started")
                return False

            with open(self.config_file, 'r') as f:
                config = json.load(f)

            self.access_token = config.get("access_token")
            self.instagram_account_id = config.get("instagram_account_id")

            if not self.access_token or not self.instagram_account_id:
                print("[Instagram] Error: access_token and instagram_account_id required in config")
                return False

            # Verify token is valid
            url = f"{self.BASE_URL}/me"
            params = {"access_token": self.access_token}
            response = requests.get(url, params=params)

            if response.status_code != 200:
                print(f"[Instagram] Token validation failed: {response.text}")
                return False

            self._authenticated = True
            return True

        except Exception as e:
            print(f"[Instagram] Authentication failed: {e}")
            return False

    def upload(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: Optional[list[str]] = None,
        cover_url: Optional[str] = None,
        share_to_feed: bool = True,
        **kwargs
    ) -> UploadResult:
        """
        Upload video as Instagram Reel.

        Instagram API requires a 2-step process:
        1. Create media container (upload video to Instagram servers)
        2. Publish the container

        Args:
            video_path: Path to video file
            title: Not used for Instagram (Reels don't have titles)
            description: Caption text with hashtags
            tags: List of hashtags (will be added to caption)
            cover_url: URL to cover image (optional)
            share_to_feed: Share Reel to main feed
            **kwargs: Additional options

        Returns:
            UploadResult with success status and Reel URL
        """
        # Authenticate if not already
        if not self.is_authenticated():
            if not self.authenticate():
                return UploadResult(
                    success=False,
                    platform=self.display_name,
                    error="Authentication failed"
                )

        # Validate video
        valid, error = self.validate_video(video_path)
        if not valid:
            return UploadResult(
                success=False,
                platform=self.display_name,
                error=error
            )

        # Format caption with hashtags
        caption = description
        if tags:
            hashtags = self.format_hashtags(tags[:self.config.max_hashtags])
            caption = f"{description}\n\n{hashtags}"

        caption = caption[:self.config.max_description_length]

        try:
            # Instagram API requires video to be publicly accessible via URL
            # For now, we'll return instructions for manual upload
            # In production, you'd upload to a hosting service first

            print("[Instagram] Note: Instagram API requires video URL (not local file)")
            print("[Instagram] Implementation requires:")
            print("  1. Upload video to public URL (AWS S3, Cloudinary, etc.)")
            print("  2. Use that URL with Instagram Graph API")
            print(f"  3. Caption ready: {caption[:50]}...")

            return UploadResult(
                success=False,
                platform=self.display_name,
                error="Instagram requires video URL. Upload video to public hosting first, then use Instagram Graph API directly."
            )

            # NOTE: Below is the correct API flow once you have a public video URL:
            #
            # Step 1: Create media container
            # create_url = f"{self.BASE_URL}/{self.instagram_account_id}/media"
            # create_params = {
            #     "access_token": self.access_token,
            #     "video_url": video_url,  # Your publicly accessible video URL
            #     "media_type": "REELS",
            #     "caption": caption,
            #     "share_to_feed": share_to_feed,
            # }
            # if cover_url:
            #     create_params["cover_url"] = cover_url
            #
            # create_response = requests.post(create_url, params=create_params)
            # if create_response.status_code != 200:
            #     return UploadResult(
            #         success=False,
            #         platform=self.display_name,
            #         error=f"Container creation failed: {create_response.text}"
            #     )
            #
            # container_id = create_response.json().get("id")
            #
            # # Step 2: Wait for processing (poll status)
            # for _ in range(60):  # Max 5 minutes
            #     status_url = f"{self.BASE_URL}/{container_id}"
            #     status_params = {
            #         "access_token": self.access_token,
            #         "fields": "status_code"
            #     }
            #     status_response = requests.get(status_url, params=status_params)
            #     status_code = status_response.json().get("status_code")
            #
            #     if status_code == "FINISHED":
            #         break
            #     elif status_code == "ERROR":
            #         return UploadResult(
            #             success=False,
            #             platform=self.display_name,
            #             error="Video processing failed"
            #         )
            #     time.sleep(5)
            #
            # # Step 3: Publish container
            # publish_url = f"{self.BASE_URL}/{self.instagram_account_id}/media_publish"
            # publish_params = {
            #     "access_token": self.access_token,
            #     "creation_id": container_id,
            # }
            # publish_response = requests.post(publish_url, params=publish_params)
            #
            # if publish_response.status_code != 200:
            #     return UploadResult(
            #         success=False,
            #         platform=self.display_name,
            #         error=f"Publish failed: {publish_response.text}"
            #     )
            #
            # media_id = publish_response.json().get("id")
            # url = f"https://www.instagram.com/reel/{media_id}"
            #
            # return UploadResult(
            #     success=True,
            #     platform=self.display_name,
            #     video_id=media_id,
            #     url=url,
            #     metadata={"share_to_feed": share_to_feed}
            # )

        except Exception as e:
            return UploadResult(
                success=False,
                platform=self.display_name,
                error=str(e)
            )
