"""
Multi-platform uploader for ClipsMachine.
Upload clips to multiple social media platforms simultaneously.
"""

import os
import json
import time
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from .platforms import (
    get_platform,
    get_all_platforms,
    Platform,
    UploadResult,
)


class MultiPlatformUploader:
    """Upload videos to multiple social media platforms."""

    def __init__(self, platforms: Optional[List[str]] = None):
        """
        Initialize multi-platform uploader.

        Args:
            platforms: List of platform names to use (e.g., ['youtube', 'tiktok'])
                      If None, all platforms will be available
        """
        self.platform_names = platforms or get_all_platforms()
        self.platforms: Dict[str, Platform] = {}

        # Initialize platforms
        for name in self.platform_names:
            try:
                platform_class = get_platform(name)
                self.platforms[name] = platform_class()
            except Exception as e:
                print(f"[MultiUploader] Warning: Failed to initialize {name}: {e}")

    def upload_single(
        self,
        platform_name: str,
        video_path: str,
        title: str,
        description: str,
        tags: Optional[List[str]] = None,
        **kwargs
    ) -> UploadResult:
        """
        Upload to a single platform.

        Args:
            platform_name: Name of platform (e.g., 'youtube', 'instagram')
            video_path: Path to video file
            title: Video title
            description: Video description
            tags: List of tags/hashtags
            **kwargs: Platform-specific options

        Returns:
            UploadResult
        """
        if platform_name not in self.platforms:
            return UploadResult(
                success=False,
                platform=platform_name,
                error=f"Platform '{platform_name}' not initialized"
            )

        platform = self.platforms[platform_name]

        # Authenticate if needed
        if not platform.is_authenticated():
            print(f"\n[{platform.display_name}] Authenticating...")
            if not platform.authenticate():
                return UploadResult(
                    success=False,
                    platform=platform.display_name,
                    error="Authentication failed"
                )

        # Upload
        print(f"\n[{platform.display_name}] Uploading {os.path.basename(video_path)}...")
        try:
            result = platform.upload(
                video_path=video_path,
                title=title,
                description=description,
                tags=tags,
                **kwargs
            )
            return result
        except Exception as e:
            return UploadResult(
                success=False,
                platform=platform.display_name,
                error=str(e)
            )

    def upload_multi(
        self,
        platforms: List[str],
        video_path: str,
        title: str,
        description: str,
        tags: Optional[List[str]] = None,
        parallel: bool = True,
        **kwargs
    ) -> List[UploadResult]:
        """
        Upload to multiple platforms.

        Args:
            platforms: List of platform names to upload to
            video_path: Path to video file
            title: Video title
            description: Video description
            tags: List of tags/hashtags
            parallel: Upload to platforms in parallel (faster)
            **kwargs: Platform-specific options

        Returns:
            List of UploadResults
        """
        if not os.path.exists(video_path):
            error_result = UploadResult(
                success=False,
                platform="All",
                error=f"Video file not found: {video_path}"
            )
            return [error_result] * len(platforms)

        results = []

        if parallel:
            # Upload in parallel using thread pool
            with ThreadPoolExecutor(max_workers=len(platforms)) as executor:
                future_to_platform = {
                    executor.submit(
                        self.upload_single,
                        platform,
                        video_path,
                        title,
                        description,
                        tags,
                        **kwargs
                    ): platform
                    for platform in platforms
                }

                for future in as_completed(future_to_platform):
                    platform = future_to_platform[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        results.append(UploadResult(
                            success=False,
                            platform=platform,
                            error=str(e)
                        ))
        else:
            # Upload sequentially
            for platform in platforms:
                result = self.upload_single(
                    platform,
                    video_path,
                    title,
                    description,
                    tags,
                    **kwargs
                )
                results.append(result)
                time.sleep(1)  # Small delay between uploads

        return results

    def upload_clips_for_video(
        self,
        video_id: str,
        platforms: List[str],
        clips_output_root: str = "clips_output",
        start_index: int = 1,
        max_clips: Optional[int] = None,
        parallel_platforms: bool = True,
        **kwargs
    ) -> Dict[str, List[UploadResult]]:
        """
        Upload all clips from a video to multiple platforms.

        Args:
            video_id: Video ID (folder name in clips_output)
            platforms: List of platform names
            clips_output_root: Root directory for clips output
            start_index: Start from this clip index
            max_clips: Maximum number of clips to upload
            parallel_platforms: Upload to platforms in parallel
            **kwargs: Platform-specific options

        Returns:
            Dict mapping clip_index to list of UploadResults
        """
        # Load manifest
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

        print(f"\n[MultiUploader] Uploading {len(clips_to_upload)} clips to {len(platforms)} platforms")
        print(f"[MultiUploader] Platforms: {', '.join(platforms)}")

        results_by_clip = {}

        for clip in clips_to_upload:
            clip_index = int(clip.get("clip_index", 0))
            title = clip.get("title", f"Clip #{clip_index}")
            description = clip.get("description", "")
            file_name = clip.get("file_name")
            file_path = os.path.join(clips_output_root, video_id, "clips", file_name)

            # Extract hashtags from description if present
            tags = []
            if "#" in description:
                words = description.split()
                tags = [word.lstrip('#') for word in words if word.startswith('#')]

            print(f"\n{'='*60}")
            print(f"[MultiUploader] Clip #{clip_index}: {title[:50]}")
            print(f"{'='*60}")

            results = self.upload_multi(
                platforms=platforms,
                video_path=file_path,
                title=title,
                description=description,
                tags=tags,
                parallel=parallel_platforms,
                **kwargs
            )

            results_by_clip[clip_index] = results

            # Print results
            for result in results:
                print(f"  {result}")

            # Small delay between clips
            time.sleep(2)

        return results_by_clip

    def list_platforms(self) -> List[Dict[str, Any]]:
        """
        Get information about all available platforms.

        Returns:
            List of platform info dicts
        """
        platforms_info = []

        for name, platform in self.platforms.items():
            platforms_info.append({
                "name": name,
                "display_name": platform.display_name,
                "authenticated": platform.is_authenticated(),
                "max_duration": platform.config.max_duration,
                "aspect_ratio": platform.config.aspect_ratio,
                "max_file_size_mb": platform.config.max_file_size / (1024 * 1024),
            })

        return platforms_info


def print_platform_info():
    """Print information about all supported platforms."""
    uploader = MultiPlatformUploader()
    platforms = uploader.list_platforms()

    print("\n" + "="*70)
    print(" ClipsMachine - Supported Social Media Platforms")
    print("="*70)

    for p in platforms:
        auth_status = "✅ Authenticated" if p["authenticated"] else "⚠️  Not authenticated"
        print(f"\n📱 {p['display_name']} ({p['name']})")
        print(f"   Status: {auth_status}")
        print(f"   Max Duration: {p['max_duration']}s")
        print(f"   Aspect Ratio: {p['aspect_ratio']}")
        print(f"   Max File Size: {p['max_file_size_mb']:.0f} MB")

    print("\n" + "="*70)
    print("\nTo authenticate platforms, place config files in the project root:")
    print("  • youtube: client_secret.json (Google Cloud OAuth)")
    print("  • instagram: instagram_config.json")
    print("  • tiktok: tiktok_config.json")
    print("  • twitter: twitter_config.json")
    print("  • linkedin: linkedin_config.json")
    print("  • facebook: facebook_config.json")
    print("\nSee platform documentation for setup instructions.")
    print("="*70 + "\n")
