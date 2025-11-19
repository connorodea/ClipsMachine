"""
Automatic thumbnail generation for ClipsMachine.
Extracts best frames and creates eye-catching thumbnails with text overlays.
"""

import os
import subprocess
from typing import Optional, Tuple
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance


class ThumbnailGenerator:
    """Generate thumbnails from video clips with text overlays."""

    def __init__(
        self,
        output_size: Tuple[int, int] = (1280, 720),  # YouTube standard
        font_size: int = 80,
        font_color: str = "white",
        outline_color: str = "black",
        outline_width: int = 3,
        add_logo: bool = False,
        logo_path: Optional[str] = None,
    ):
        """
        Initialize thumbnail generator.

        Args:
            output_size: Thumbnail dimensions (width, height)
            font_size: Text font size
            font_color: Text color
            outline_color: Text outline color
            outline_width: Text outline thickness
            add_logo: Add logo watermark
            logo_path: Path to logo image
        """
        self.output_size = output_size
        self.font_size = font_size
        self.font_color = font_color
        self.outline_color = outline_color
        self.outline_width = outline_width
        self.add_logo = add_logo
        self.logo_path = logo_path

    def extract_best_frame(
        self,
        video_path: str,
        timestamp: Optional[float] = None,
        output_path: Optional[str] = None
    ) -> str:
        """
        Extract a frame from video at specified timestamp.

        Args:
            video_path: Path to video file
            timestamp: Time in seconds to extract frame (default: middle of video)
            output_path: Where to save extracted frame

        Returns:
            Path to extracted frame
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

        # Default to middle of video if no timestamp specified
        if timestamp is None:
            # Get video duration
            duration = self._get_video_duration(video_path)
            timestamp = duration / 2

        # Generate output path if not provided
        if output_path is None:
            video_dir = os.path.dirname(video_path)
            video_name = Path(video_path).stem
            output_path = os.path.join(video_dir, f"{video_name}_frame.jpg")

        # Extract frame using ffmpeg
        cmd = [
            "ffmpeg",
            "-ss", str(timestamp),
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",  # High quality
            "-y",  # Overwrite
            output_path
        ]

        subprocess.run(cmd, capture_output=True, check=True)

        if not os.path.exists(output_path):
            raise RuntimeError(f"Failed to extract frame from {video_path}")

        return output_path

    def _get_video_duration(self, video_path: str) -> float:
        """Get video duration in seconds using ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())

    def add_text_overlay(
        self,
        image_path: str,
        text: str,
        position: str = "bottom",
        max_width_ratio: float = 0.9,
    ) -> Image.Image:
        """
        Add text overlay to image.

        Args:
            image_path: Path to base image
            text: Text to overlay
            position: 'top', 'middle', or 'bottom'
            max_width_ratio: Maximum text width as ratio of image width

        Returns:
            PIL Image with text overlay
        """
        img = Image.open(image_path)

        # Resize to target dimensions
        img = img.resize(self.output_size, Image.Resampling.LANCZOS)

        # Create drawing context
        draw = ImageDraw.Draw(img)

        # Try to load a nice font, fall back to default
        try:
            # Try multiple font locations
            font_paths = [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",  # macOS
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
                "C:\\Windows\\Fonts\\arialbd.ttf",  # Windows
            ]
            font = None
            for font_path in font_paths:
                if os.path.exists(font_path):
                    font = ImageFont.truetype(font_path, self.font_size)
                    break

            if font is None:
                font = ImageFont.load_default()
        except Exception:
            font = ImageFont.load_default()

        # Word wrap text to fit width
        wrapped_text = self._wrap_text(text, font, int(self.output_size[0] * max_width_ratio), draw)

        # Calculate text bounding box
        bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Calculate position
        x = (self.output_size[0] - text_width) // 2

        if position == "top":
            y = 50
        elif position == "middle":
            y = (self.output_size[1] - text_height) // 2
        else:  # bottom
            y = self.output_size[1] - text_height - 50

        # Draw text with outline (for better visibility)
        for offset_x in range(-self.outline_width, self.outline_width + 1):
            for offset_y in range(-self.outline_width, self.outline_width + 1):
                if offset_x != 0 or offset_y != 0:
                    draw.multiline_text(
                        (x + offset_x, y + offset_y),
                        wrapped_text,
                        font=font,
                        fill=self.outline_color,
                        align="center"
                    )

        # Draw main text
        draw.multiline_text(
            (x, y),
            wrapped_text,
            font=font,
            fill=self.font_color,
            align="center"
        )

        return img

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.Draw) -> str:
        """Wrap text to fit within max_width."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            current_line.append(word)
            test_line = ' '.join(current_line)

            bbox = draw.textbbox((0, 0), test_line, font=font)
            width = bbox[2] - bbox[0]

            if width > max_width:
                if len(current_line) == 1:
                    # Single word too long, keep it anyway
                    lines.append(current_line[0])
                    current_line = []
                else:
                    # Remove last word and start new line
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]

        if current_line:
            lines.append(' '.join(current_line))

        return '\n'.join(lines)

    def add_logo_watermark(self, img: Image.Image, logo_path: str, position: str = "bottom-right", size_percent: int = 10) -> Image.Image:
        """
        Add logo watermark to image.

        Args:
            img: PIL Image
            logo_path: Path to logo file
            position: 'top-left', 'top-right', 'bottom-left', 'bottom-right'
            size_percent: Logo size as percentage of image width

        Returns:
            Image with logo watermark
        """
        if not os.path.exists(logo_path):
            print(f"[Thumbnail] Warning: Logo not found at {logo_path}")
            return img

        logo = Image.open(logo_path).convert("RGBA")

        # Resize logo
        logo_width = int(self.output_size[0] * (size_percent / 100))
        logo_aspect = logo.size[1] / logo.size[0]
        logo_height = int(logo_width * logo_aspect)
        logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)

        # Calculate position
        margin = 20
        if position == "top-left":
            pos = (margin, margin)
        elif position == "top-right":
            pos = (self.output_size[0] - logo_width - margin, margin)
        elif position == "bottom-left":
            pos = (margin, self.output_size[1] - logo_height - margin)
        else:  # bottom-right
            pos = (self.output_size[0] - logo_width - margin, self.output_size[1] - logo_height - margin)

        # Paste logo with alpha channel
        img_rgba = img.convert("RGBA")
        img_rgba.paste(logo, pos, logo)
        return img_rgba.convert("RGB")

    def generate_thumbnail(
        self,
        video_path: str,
        title: str,
        output_path: Optional[str] = None,
        timestamp: Optional[float] = None,
        text_position: str = "bottom",
        enhance_brightness: bool = True,
        enhance_saturation: bool = True,
    ) -> str:
        """
        Generate complete thumbnail from video.

        Args:
            video_path: Path to video file
            title: Title text to overlay
            output_path: Where to save thumbnail
            timestamp: Frame timestamp (default: middle)
            text_position: Where to place text
            enhance_brightness: Slightly brighten image
            enhance_saturation: Slightly increase saturation

        Returns:
            Path to generated thumbnail
        """
        # Generate output path if not provided
        if output_path is None:
            video_dir = os.path.dirname(video_path)
            video_name = Path(video_path).stem
            output_path = os.path.join(video_dir, f"{video_name}_thumbnail.jpg")

        # Extract frame
        frame_path = self.extract_best_frame(video_path, timestamp)

        # Add text overlay
        img = self.add_text_overlay(frame_path, title, text_position)

        # Enhance image for better thumbnail appeal
        if enhance_brightness:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.1)  # 10% brighter

        if enhance_saturation:
            enhancer = ImageEnhance.Color(img)
            img = enhancer.enhance(1.2)  # 20% more saturated

        # Add logo if configured
        if self.add_logo and self.logo_path:
            img = self.add_logo_watermark(img, self.logo_path)

        # Save thumbnail
        img.save(output_path, "JPEG", quality=95, optimize=True)

        # Clean up temporary frame
        if os.path.exists(frame_path) and frame_path != output_path:
            os.remove(frame_path)

        print(f"[Thumbnail] Generated: {output_path}")
        return output_path

    def generate_thumbnails_for_manifest(
        self,
        video_id: str,
        clips_output_root: str = "clips_output",
        timestamp_offset: float = 3.0,  # Extract frame 3 seconds into clip
    ) -> dict[int, str]:
        """
        Generate thumbnails for all clips in a manifest.

        Args:
            video_id: Video ID folder
            clips_output_root: Root output directory
            timestamp_offset: Seconds into clip to extract frame

        Returns:
            Dict mapping clip_index to thumbnail path
        """
        import json

        manifest_path = os.path.join(clips_output_root, video_id, "manifest.json")
        if not os.path.exists(manifest_path):
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")

        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        thumbnails_dir = os.path.join(clips_output_root, video_id, "thumbnails")
        os.makedirs(thumbnails_dir, exist_ok=True)

        thumbnail_paths = {}

        for clip in manifest:
            clip_index = int(clip.get("clip_index", 0))
            title = clip.get("title", f"Clip #{clip_index}")
            file_name = clip.get("file_name")
            file_path = os.path.join(clips_output_root, video_id, "clips", file_name)

            if not os.path.exists(file_path):
                print(f"[Thumbnail] Warning: Clip file not found: {file_path}")
                continue

            # Generate thumbnail path
            thumbnail_name = f"thumbnail_{clip_index:02d}.jpg"
            thumbnail_path = os.path.join(thumbnails_dir, thumbnail_name)

            # Generate thumbnail
            try:
                self.generate_thumbnail(
                    video_path=file_path,
                    title=title,
                    output_path=thumbnail_path,
                    timestamp=timestamp_offset,
                )
                thumbnail_paths[clip_index] = thumbnail_path
            except Exception as e:
                print(f"[Thumbnail] Error generating thumbnail for clip {clip_index}: {e}")

        print(f"[Thumbnail] Generated {len(thumbnail_paths)} thumbnails for {video_id}")
        return thumbnail_paths
