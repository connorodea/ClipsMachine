"""
Base platform interface for multi-platform social media uploads.
All platform implementations inherit from this base class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional
from pathlib import Path


@dataclass
class PlatformConfig:
    """Configuration for a social media platform."""

    # Video specifications
    max_duration: int  # seconds
    min_duration: int  # seconds
    aspect_ratio: str  # e.g., "9:16", "1:1", "16:9"
    max_file_size: int  # bytes
    supported_formats: list[str]  # e.g., ["mp4", "mov"]

    # Content specifications
    max_title_length: int
    max_description_length: int
    max_tags: int
    max_hashtags: int

    # API specifications
    requires_auth: bool
    rate_limit_per_day: Optional[int] = None
    rate_limit_per_hour: Optional[int] = None


@dataclass
class UploadResult:
    """Result of a platform upload."""

    success: bool
    platform: str
    video_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        if self.success:
            return f"✅ {self.platform}: {self.url}"
        return f"❌ {self.platform}: {self.error}"


class Platform(ABC):
    """Abstract base class for all social media platforms."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize platform with optional config file path.

        Args:
            config_path: Path to platform-specific config/credentials
        """
        self.config_path = config_path
        self._authenticated = False

    @property
    @abstractmethod
    def name(self) -> str:
        """Platform name (e.g., 'youtube', 'instagram')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable platform name (e.g., 'YouTube Shorts', 'Instagram Reels')."""
        pass

    @property
    @abstractmethod
    def config(self) -> PlatformConfig:
        """Platform configuration and specifications."""
        pass

    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the platform API.

        Returns:
            True if authentication successful, False otherwise
        """
        pass

    @abstractmethod
    def upload(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: Optional[list[str]] = None,
        **kwargs
    ) -> UploadResult:
        """
        Upload a video to the platform.

        Args:
            video_path: Path to video file
            title: Video title
            description: Video description
            tags: List of tags/hashtags
            **kwargs: Platform-specific options

        Returns:
            UploadResult with success status and details
        """
        pass

    def validate_video(self, video_path: str) -> tuple[bool, Optional[str]]:
        """
        Validate video meets platform requirements.

        Args:
            video_path: Path to video file

        Returns:
            Tuple of (is_valid, error_message)
        """
        path = Path(video_path)

        # Check file exists
        if not path.exists():
            return False, f"Video file not found: {video_path}"

        # Check file size
        file_size = path.stat().st_size
        if file_size > self.config.max_file_size:
            max_mb = self.config.max_file_size / (1024 * 1024)
            actual_mb = file_size / (1024 * 1024)
            return False, f"File too large: {actual_mb:.1f}MB (max: {max_mb:.1f}MB)"

        # Check format
        extension = path.suffix.lstrip('.').lower()
        if extension not in self.config.supported_formats:
            formats = ", ".join(self.config.supported_formats)
            return False, f"Unsupported format: {extension} (supported: {formats})"

        return True, None

    def validate_metadata(
        self,
        title: str,
        description: str,
        tags: Optional[list[str]] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate metadata meets platform requirements.

        Args:
            title: Video title
            description: Video description
            tags: List of tags

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate title
        if len(title) > self.config.max_title_length:
            return False, f"Title too long: {len(title)} chars (max: {self.config.max_title_length})"

        # Validate description
        if len(description) > self.config.max_description_length:
            return False, f"Description too long: {len(description)} chars (max: {self.config.max_description_length})"

        # Validate tags
        if tags and len(tags) > self.config.max_tags:
            return False, f"Too many tags: {len(tags)} (max: {self.config.max_tags})"

        return True, None

    def format_hashtags(self, tags: list[str]) -> str:
        """
        Format tags as hashtags for platform.

        Args:
            tags: List of tag strings

        Returns:
            Formatted hashtag string
        """
        # Remove existing # symbols and spaces
        clean_tags = [tag.strip().lstrip('#').replace(' ', '') for tag in tags]

        # Take only max allowed hashtags
        clean_tags = clean_tags[:self.config.max_hashtags]

        # Format as hashtags
        return ' '.join(f'#{tag}' for tag in clean_tags)

    def is_authenticated(self) -> bool:
        """Check if platform is authenticated."""
        return self._authenticated
