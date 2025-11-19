"""
YouTube Shorts platform implementation.
Uploads videos as YouTube Shorts (<60s vertical videos).
"""

import os
from typing import Optional
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from .base import Platform, PlatformConfig, UploadResult


class YouTubeShortsplatform(Platform):
    """YouTube Shorts platform implementation."""

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize YouTube Shorts platform.

        Args:
            config_path: Path to OAuth client secrets JSON file
        """
        super().__init__(config_path)
        self.client_secret_file = config_path or "client_secret.json"
        self.token_file = "youtube_token.json"
        self.youtube_client = None

    @property
    def name(self) -> str:
        return "youtube"

    @property
    def display_name(self) -> str:
        return "YouTube Shorts"

    @property
    def config(self) -> PlatformConfig:
        return PlatformConfig(
            max_duration=60,  # Shorts are <60 seconds
            min_duration=1,
            aspect_ratio="9:16",  # Vertical
            max_file_size=256 * 1024 * 1024,  # 256 MB
            supported_formats=["mp4", "mov", "avi", "wmv", "flv", "3gp", "webm"],
            max_title_length=100,
            max_description_length=5000,
            max_tags=500,  # Total character limit
            max_hashtags=15,
            requires_auth=True,
            rate_limit_per_day=50,  # Conservative estimate
        )

    def authenticate(self) -> bool:
        """Authenticate with YouTube API using OAuth 2.0."""
        try:
            creds = None

            # Load existing token
            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(
                    self.token_file, self.SCOPES
                )

            # Refresh or get new credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(self.client_secret_file):
                        print(f"[YouTube] Error: {self.client_secret_file} not found")
                        print("[YouTube] Download OAuth client secrets from Google Cloud Console")
                        return False

                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.client_secret_file, self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Save credentials
                with open(self.token_file, "w") as token:
                    token.write(creds.to_json())
                os.chmod(self.token_file, 0o600)

            # Build YouTube client
            self.youtube_client = build("youtube", "v3", credentials=creds)
            self._authenticated = True
            return True

        except Exception as e:
            print(f"[YouTube] Authentication failed: {e}")
            return False

    def upload(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: Optional[list[str]] = None,
        privacy_status: str = "public",
        category_id: str = "22",  # People & Blogs
        **kwargs
    ) -> UploadResult:
        """
        Upload video as YouTube Short.

        Args:
            video_path: Path to video file
            title: Video title (max 100 chars)
            description: Video description (will add #Shorts automatically)
            tags: List of tags
            privacy_status: 'public', 'private', or 'unlisted'
            category_id: YouTube category ID
            **kwargs: Additional options

        Returns:
            UploadResult with success status and video URL
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

        # Ensure #Shorts hashtag is in description for YouTube to recognize it
        if "#Shorts" not in description and "#shorts" not in description:
            description = f"{description}\n\n#Shorts"

        # Add other hashtags if provided
        if tags:
            hashtags = self.format_hashtags(tags[:self.config.max_hashtags])
            description = f"{description}\n\n{hashtags}"

        # Truncate to max lengths
        title = title[:self.config.max_title_length]
        description = description[:self.config.max_description_length]

        # Validate metadata
        valid, error = self.validate_metadata(title, description, tags)
        if not valid:
            return UploadResult(
                success=False,
                platform=self.display_name,
                error=error
            )

        # Prepare upload
        try:
            body = {
                "snippet": {
                    "title": title,
                    "description": description,
                    "categoryId": category_id,
                },
                "status": {
                    "privacyStatus": privacy_status,
                    "selfDeclaredMadeForKids": False,
                },
            }

            if tags:
                # Tags are separate from hashtags in description
                body["snippet"]["tags"] = tags[:30]  # Max 30 tags

            media = MediaFileUpload(
                video_path,
                chunksize=-1,
                resumable=True,
                mimetype="video/*"
            )

            request = self.youtube_client.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            # Execute upload with progress
            response = None
            print(f"[YouTube] Uploading {os.path.basename(video_path)}...")
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    print(f"[YouTube] Upload progress: {progress}%", end='\r')

            print()  # New line after progress

            video_id = response.get("id")
            url = f"https://www.youtube.com/shorts/{video_id}"

            return UploadResult(
                success=True,
                platform=self.display_name,
                video_id=video_id,
                url=url,
                metadata={
                    "privacy_status": privacy_status,
                    "category_id": category_id,
                }
            )

        except HttpError as e:
            error_msg = f"HTTP {e.resp.status}: {e.error_details}"
            return UploadResult(
                success=False,
                platform=self.display_name,
                error=error_msg
            )
        except Exception as e:
            return UploadResult(
                success=False,
                platform=self.display_name,
                error=str(e)
            )
