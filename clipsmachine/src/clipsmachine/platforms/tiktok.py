"""
TikTok platform implementation.
Uploads videos to TikTok using TikTok API v2.
"""

import os
import json
import requests
from typing import Optional

from .base import Platform, PlatformConfig, UploadResult


class TikTokPlatform(Platform):
    """TikTok platform implementation."""

    API_VERSION = "v2"
    BASE_URL = "https://open.tiktokapis.com"

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize TikTok platform.

        Args:
            config_path: Path to TikTok config JSON with access_token
        """
        super().__init__(config_path)
        self.config_file = config_path or "tiktok_config.json"
        self.access_token = None

    @property
    def name(self) -> str:
        return "tiktok"

    @property
    def display_name(self) -> str:
        return "TikTok"

    @property
    def config(self) -> PlatformConfig:
        return PlatformConfig(
            max_duration=600,  # TikTok allows up to 10 minutes
            min_duration=1,
            aspect_ratio="9:16",  # Vertical preferred
            max_file_size=500 * 1024 * 1024,  # 500 MB max (varies by account)
            supported_formats=["mp4", "mov", "webm"],
            max_title_length=150,  # Caption length
            max_description_length=2200,
            max_tags=30,
            max_hashtags=30,
            requires_auth=True,
            rate_limit_per_day=None,  # Varies by account type
        )

    def authenticate(self) -> bool:
        """
        Authenticate with TikTok API.

        Requires config file with:
        {
            "access_token": "YOUR_TIKTOK_ACCESS_TOKEN",
            "client_key": "YOUR_CLIENT_KEY",
            "client_secret": "YOUR_CLIENT_SECRET"
        }

        Get these from: https://developers.tiktok.com/
        """
        try:
            if not os.path.exists(self.config_file):
                print(f"[TikTok] Error: {self.config_file} not found")
                print("[TikTok] Create config file with access_token")
                print("[TikTok] See: https://developers.tiktok.com/doc/content-posting-api-get-started/")
                return False

            with open(self.config_file, 'r') as f:
                config = json.load(f)

            self.access_token = config.get("access_token")
            self.client_key = config.get("client_key")
            self.client_secret = config.get("client_secret")

            if not self.access_token:
                print("[TikTok] Error: access_token required in config")
                return False

            # Verify token (simplified check)
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            # Test with user info endpoint
            url = f"{self.BASE_URL}/{self.API_VERSION}/user/info/"
            response = requests.get(url, headers=headers)

            if response.status_code not in [200, 201]:
                print(f"[TikTok] Token validation failed: {response.text}")
                print("[TikTok] Note: TikTok API access requires approved developer account")
                return False

            self._authenticated = True
            return True

        except Exception as e:
            print(f"[TikTok] Authentication failed: {e}")
            return False

    def upload(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: Optional[list[str]] = None,
        privacy_level: str = "PUBLIC_TO_EVERYONE",
        disable_duet: bool = False,
        disable_comment: bool = False,
        disable_stitch: bool = False,
        **kwargs
    ) -> UploadResult:
        """
        Upload video to TikTok.

        TikTok Content Posting API process:
        1. Initialize upload session
        2. Upload video chunks
        3. Publish video with metadata

        Args:
            video_path: Path to video file
            title: Video caption
            description: Extended description (optional)
            tags: List of hashtags
            privacy_level: PUBLIC_TO_EVERYONE, MUTUAL_FOLLOW_FRIENDS, SELF_ONLY
            disable_duet: Disable duet feature
            disable_comment: Disable comments
            disable_stitch: Disable stitch feature
            **kwargs: Additional options

        Returns:
            UploadResult with success status
        """
        # Authenticate if not already
        if not self.is_authenticated():
            if not self.authenticate():
                return UploadResult(
                    success=False,
                    platform=self.display_name,
                    error="Authentication failed. TikTok requires approved developer access."
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
        caption = title if title else description
        if tags:
            hashtags = self.format_hashtags(tags[:self.config.max_hashtags])
            caption = f"{caption} {hashtags}"

        caption = caption[:self.config.max_title_length]

        try:
            print("[TikTok] Note: TikTok Content Posting API requires:")
            print("  1. Approved TikTok Developer account")
            print("  2. OAuth 2.0 authentication flow")
            print("  3. User consent for content posting")
            print(f"  4. Caption ready: {caption[:50]}...")

            return UploadResult(
                success=False,
                platform=self.display_name,
                error="TikTok API requires approved developer account and OAuth flow. See: https://developers.tiktok.com/doc/content-posting-api-get-started/"
            )

            # NOTE: Below is the correct API flow once you have OAuth access:
            #
            # headers = {
            #     "Authorization": f"Bearer {self.access_token}",
            #     "Content-Type": "application/json"
            # }
            #
            # # Step 1: Initialize video upload
            # init_url = f"{self.BASE_URL}/{self.API_VERSION}/post/publish/video/init/"
            # init_body = {
            #     "post_info": {
            #         "title": caption,
            #         "privacy_level": privacy_level,
            #         "disable_duet": disable_duet,
            #         "disable_comment": disable_comment,
            #         "disable_stitch": disable_stitch,
            #         "video_cover_timestamp_ms": 1000,  # Frame at 1 second for thumbnail
            #     },
            #     "source_info": {
            #         "source": "FILE_UPLOAD",
            #         "video_size": os.path.getsize(video_path),
            #         "chunk_size": 5 * 1024 * 1024,  # 5 MB chunks
            #         "total_chunk_count": (os.path.getsize(video_path) // (5 * 1024 * 1024)) + 1
            #     }
            # }
            #
            # init_response = requests.post(init_url, headers=headers, json=init_body)
            # if init_response.status_code != 200:
            #     return UploadResult(
            #         success=False,
            #         platform=self.display_name,
            #         error=f"Upload initialization failed: {init_response.text}"
            #     )
            #
            # upload_data = init_response.json().get("data", {})
            # upload_id = upload_data.get("upload_id")
            # upload_url = upload_data.get("upload_url")
            #
            # # Step 2: Upload video chunks
            # with open(video_path, 'rb') as video_file:
            #     chunk_size = 5 * 1024 * 1024
            #     chunk_number = 0
            #
            #     while True:
            #         chunk = video_file.read(chunk_size)
            #         if not chunk:
            #             break
            #
            #         chunk_headers = {
            #             "Content-Type": "video/mp4",
            #             "Content-Range": f"bytes {chunk_number * chunk_size}-{chunk_number * chunk_size + len(chunk) - 1}/{os.path.getsize(video_path)}"
            #         }
            #
            #         chunk_response = requests.put(upload_url, headers=chunk_headers, data=chunk)
            #         if chunk_response.status_code not in [200, 201]:
            #             return UploadResult(
            #                 success=False,
            #                 platform=self.display_name,
            #                 error=f"Chunk upload failed: {chunk_response.text}"
            #             )
            #
            #         chunk_number += 1
            #         print(f"[TikTok] Uploaded chunk {chunk_number}", end='\r')
            #
            # # Step 3: Publish video
            # publish_url = f"{self.BASE_URL}/{self.API_VERSION}/post/publish/status/fetch/"
            # publish_params = {"publish_id": upload_id}
            # publish_response = requests.post(publish_url, headers=headers, json=publish_params)
            #
            # if publish_response.status_code != 200:
            #     return UploadResult(
            #         success=False,
            #         platform=self.display_name,
            #         error=f"Publish failed: {publish_response.text}"
            #     )
            #
            # result = publish_response.json().get("data", {})
            # return UploadResult(
            #     success=True,
            #     platform=self.display_name,
            #     video_id=result.get("publish_id"),
            #     url=f"https://www.tiktok.com/@{result.get('share_url', '')}",
            #     metadata={"privacy_level": privacy_level}
            # )

        except Exception as e:
            return UploadResult(
                success=False,
                platform=self.display_name,
                error=str(e)
            )
