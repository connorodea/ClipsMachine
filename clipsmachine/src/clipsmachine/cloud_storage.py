"""
Cloud storage integration for ClipsMachine.
Upload videos to S3, Cloudinary, or other cloud storage for Instagram/TikTok posting.
"""

import os
import json
from typing import Optional, Dict, Any
from pathlib import Path
from abc import ABC, abstractmethod


class CloudStorage(ABC):
    """Abstract base class for cloud storage providers."""

    @abstractmethod
    def upload(self, file_path: str, public: bool = True) -> str:
        """
        Upload file to cloud storage.

        Args:
            file_path: Path to file to upload
            public: Make file publicly accessible

        Returns:
            Public URL of uploaded file
        """
        pass

    @abstractmethod
    def delete(self, url: str) -> bool:
        """
        Delete file from cloud storage.

        Args:
            url: URL of file to delete

        Returns:
            True if successful
        """
        pass


class S3Storage(CloudStorage):
    """AWS S3 storage implementation."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize S3 storage.

        Requires config file with:
        {
            "aws_access_key_id": "YOUR_KEY",
            "aws_secret_access_key": "YOUR_SECRET",
            "bucket_name": "your-bucket",
            "region": "us-east-1"
        }
        """
        self.config_file = config_path or "s3_config.json"
        self.s3_client = None
        self.bucket_name = None

        if os.path.exists(self.config_file):
            self._initialize()

    def _initialize(self):
        """Initialize S3 client."""
        try:
            import boto3

            with open(self.config_file, 'r') as f:
                config = json.load(f)

            self.bucket_name = config.get("bucket_name")

            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=config.get("aws_access_key_id"),
                aws_secret_access_key=config.get("aws_secret_access_key"),
                region_name=config.get("region", "us-east-1")
            )

            print(f"[S3] Initialized with bucket: {self.bucket_name}")

        except ImportError:
            print("[S3] boto3 not installed. Install: pip install boto3")
            raise
        except Exception as e:
            print(f"[S3] Initialization failed: {e}")
            raise

    def upload(self, file_path: str, public: bool = True, folder: str = "clips") -> str:
        """
        Upload file to S3.

        Args:
            file_path: Path to file
            public: Make file publicly accessible
            folder: Folder in bucket

        Returns:
            Public URL
        """
        if not self.s3_client:
            raise RuntimeError("S3 not initialized. Check config file.")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Generate S3 key (path in bucket)
        file_name = Path(file_path).name
        s3_key = f"{folder}/{file_name}"

        # Upload with public-read ACL if public
        extra_args = {}
        if public:
            extra_args['ACL'] = 'public-read'

        print(f"[S3] Uploading {file_name} to s3://{self.bucket_name}/{s3_key}")

        try:
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )

            # Generate public URL
            region = self.s3_client.meta.region_name
            url = f"https://{self.bucket_name}.s3.{region}.amazonaws.com/{s3_key}"

            print(f"[S3] Uploaded: {url}")
            return url

        except Exception as e:
            print(f"[S3] Upload failed: {e}")
            raise

    def delete(self, url: str) -> bool:
        """Delete file from S3."""
        if not self.s3_client:
            return False

        try:
            # Extract key from URL
            # URL format: https://bucket.s3.region.amazonaws.com/key
            key = url.split(f"{self.bucket_name}.s3.")[-1].split('/', 1)[-1]

            self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            print(f"[S3] Deleted: {key}")
            return True

        except Exception as e:
            print(f"[S3] Delete failed: {e}")
            return False


class CloudinaryStorage(CloudStorage):
    """Cloudinary storage implementation."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize Cloudinary storage.

        Requires config file with:
        {
            "cloud_name": "your-cloud",
            "api_key": "YOUR_KEY",
            "api_secret": "YOUR_SECRET"
        }
        """
        self.config_file = config_path or "cloudinary_config.json"
        self.cloudinary = None

        if os.path.exists(self.config_file):
            self._initialize()

    def _initialize(self):
        """Initialize Cloudinary."""
        try:
            import cloudinary
            import cloudinary.uploader

            with open(self.config_file, 'r') as f:
                config = json.load(f)

            cloudinary.config(
                cloud_name=config.get("cloud_name"),
                api_key=config.get("api_key"),
                api_secret=config.get("api_secret")
            )

            self.cloudinary = cloudinary
            print(f"[Cloudinary] Initialized")

        except ImportError:
            print("[Cloudinary] cloudinary not installed. Install: pip install cloudinary")
            raise
        except Exception as e:
            print(f"[Cloudinary] Initialization failed: {e}")
            raise

    def upload(self, file_path: str, public: bool = True, folder: str = "clips") -> str:
        """
        Upload file to Cloudinary.

        Args:
            file_path: Path to file
            public: Make file publicly accessible
            folder: Folder in Cloudinary

        Returns:
            Public URL
        """
        if not self.cloudinary:
            raise RuntimeError("Cloudinary not initialized. Check config file.")

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        file_name = Path(file_path).stem
        print(f"[Cloudinary] Uploading {file_name}...")

        try:
            result = self.cloudinary.uploader.upload(
                file_path,
                resource_type="video",
                folder=folder,
                public_id=file_name,
                overwrite=True,
            )

            url = result.get("secure_url")
            print(f"[Cloudinary] Uploaded: {url}")
            return url

        except Exception as e:
            print(f"[Cloudinary] Upload failed: {e}")
            raise

    def delete(self, url: str) -> bool:
        """Delete file from Cloudinary."""
        if not self.cloudinary:
            return False

        try:
            # Extract public_id from URL
            # URL format: https://res.cloudinary.com/cloud/video/upload/v123/folder/file.mp4
            parts = url.split('/upload/')[-1].split('/')
            public_id = '/'.join(parts[1:]).rsplit('.', 1)[0]

            self.cloudinary.uploader.destroy(public_id, resource_type="video")
            print(f"[Cloudinary] Deleted: {public_id}")
            return True

        except Exception as e:
            print(f"[Cloudinary] Delete failed: {e}")
            return False


class CloudStorageManager:
    """Manage multiple cloud storage providers."""

    def __init__(self, provider: str = "s3"):
        """
        Initialize cloud storage manager.

        Args:
            provider: 's3' or 'cloudinary'
        """
        self.provider = provider.lower()

        if self.provider == "s3":
            self.storage = S3Storage()
        elif self.provider == "cloudinary":
            self.storage = CloudinaryStorage()
        else:
            raise ValueError(f"Unknown provider: {provider}. Use 's3' or 'cloudinary'")

    def upload_clip(self, video_path: str) -> str:
        """Upload video clip and return public URL."""
        return self.storage.upload(video_path)

    def upload_thumbnail(self, thumbnail_path: str) -> str:
        """Upload thumbnail and return public URL."""
        return self.storage.upload(thumbnail_path, folder="thumbnails")

    def upload_clips_for_video(
        self,
        video_id: str,
        clips_output_root: str = "clips_output",
        start_index: int = 1,
        max_clips: Optional[int] = None,
    ) -> Dict[int, Dict[str, str]]:
        """
        Upload all clips and thumbnails for a video.

        Args:
            video_id: Video ID
            clips_output_root: Root output directory
            start_index: Start from this clip index
            max_clips: Maximum clips to upload

        Returns:
            Dict mapping clip_index to URLs dict with 'video' and 'thumbnail' keys
        """
        manifest_path = os.path.join(clips_output_root, video_id, "manifest.json")
        if not os.path.exists(manifest_path):
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")

        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        # Filter clips
        manifest.sort(key=lambda c: int(c.get("clip_index", 0)))
        clips_to_upload = [
            c for c in manifest
            if int(c.get("clip_index", 0)) >= start_index
        ]

        if max_clips:
            clips_to_upload = clips_to_upload[:max_clips]

        print(f"\n[CloudStorage] Uploading {len(clips_to_upload)} clips to {self.provider.upper()}")

        uploaded_urls = {}

        for clip in clips_to_upload:
            clip_index = int(clip.get("clip_index", 0))
            file_name = clip.get("file_name")
            file_path = os.path.join(clips_output_root, video_id, "clips", file_name)

            if not os.path.exists(file_path):
                print(f"[CloudStorage] Warning: Clip not found: {file_path}")
                continue

            try:
                # Upload video
                video_url = self.upload_clip(file_path)

                # Upload thumbnail if exists
                thumbnail_path = os.path.join(
                    clips_output_root,
                    video_id,
                    "thumbnails",
                    f"thumbnail_{clip_index:02d}.jpg"
                )

                thumbnail_url = None
                if os.path.exists(thumbnail_path):
                    thumbnail_url = self.upload_thumbnail(thumbnail_path)

                uploaded_urls[clip_index] = {
                    "video": video_url,
                    "thumbnail": thumbnail_url
                }

                print(f"[CloudStorage] ✅ Clip #{clip_index} uploaded")

            except Exception as e:
                print(f"[CloudStorage] ❌ Clip #{clip_index} failed: {e}")

        return uploaded_urls

    def cleanup(self, urls: Dict[int, Dict[str, str]]) -> None:
        """Delete uploaded files from cloud storage."""
        for clip_index, url_dict in urls.items():
            try:
                if url_dict.get("video"):
                    self.storage.delete(url_dict["video"])
                if url_dict.get("thumbnail"):
                    self.storage.delete(url_dict["thumbnail"])
            except Exception as e:
                print(f"[CloudStorage] Cleanup failed for clip {clip_index}: {e}")
