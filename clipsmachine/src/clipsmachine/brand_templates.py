"""
Brand template system for ClipsMachine.

Supports:
- Logo overlays (customizable position and size)
- Intro/outro clips
- Watermarks
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class BrandTemplate:
    """Configuration for brand elements on clips."""
    logo_path: Optional[str] = None
    logo_position: str = "top-right"  # top-left, top-right, bottom-left, bottom-right
    logo_size: int = 15  # Percentage of video width
    logo_opacity: float = 1.0  # 0.0 to 1.0
    intro_path: Optional[str] = None
    outro_path: Optional[str] = None


# Position mappings for logo overlay (x, y coordinates in FFmpeg format)
LOGO_POSITIONS = {
    "top-left": "10:10",
    "top-right": "W-w-10:10",
    "bottom-left": "10:H-h-10",
    "bottom-right": "W-w-10:H-h-10",
    "center": "(W-w)/2:(H-h)/2",
}


def create_logo_overlay_filter(
    logo_path: str,
    position: str = "top-right",
    size_percent: int = 15,
    opacity: float = 1.0,
    video_width: int = 1080,
) -> str:
    """
    Create FFmpeg filter for logo overlay.

    Args:
        logo_path: Path to logo image (PNG with transparency recommended)
        position: Logo position - top-left, top-right, bottom-left, bottom-right, center
        size_percent: Logo size as percentage of video width (default: 15%)
        opacity: Logo opacity 0.0-1.0 (default: 1.0)
        video_width: Target video width for scaling calculation

    Returns:
        FFmpeg filter string for logo overlay
    """
    if not os.path.exists(logo_path):
        raise FileNotFoundError(f"Logo file not found: {logo_path}")

    if position not in LOGO_POSITIONS:
        raise ValueError(f"Invalid position: {position}. Choose from: {list(LOGO_POSITIONS.keys())}")

    # Calculate logo width based on percentage
    logo_width = int(video_width * (size_percent / 100))

    # Get position coordinates
    position_coords = LOGO_POSITIONS[position]

    # Build overlay filter with scaling and opacity
    # Format: [logo][main]overlay=x:y
    overlay_parts = [
        # Scale logo to target width, maintaining aspect ratio
        f"scale={logo_width}:-1",
    ]

    # Add opacity if less than 1.0
    if opacity < 1.0:
        # Use format filter to add alpha channel, then colorchannelmixer to adjust opacity
        overlay_parts.append(f"format=rgba,colorchannelmixer=aa={opacity}")

    # Combine scaling and opacity into logo input filter
    logo_filter = ",".join(overlay_parts)

    return f"[1:v]{logo_filter}[logo];[0:v][logo]overlay={position_coords}"


def requires_concat(template: BrandTemplate) -> bool:
    """
    Check if template requires video concatenation (intro/outro).

    Args:
        template: BrandTemplate configuration

    Returns:
        True if intro or outro is specified
    """
    return bool(template.intro_path or template.outro_path)


def build_concat_file_list(
    main_clip: str,
    template: BrandTemplate,
    temp_dir: str,
) -> str:
    """
    Build FFmpeg concat file list for intro/main/outro assembly.

    Args:
        main_clip: Path to main clip video
        template: BrandTemplate configuration
        temp_dir: Directory for temporary concat file

    Returns:
        Path to concat file list
    """
    concat_file = os.path.join(temp_dir, "concat_list.txt")

    with open(concat_file, "w") as f:
        if template.intro_path and os.path.exists(template.intro_path):
            f.write(f"file '{template.intro_path}'\n")

        f.write(f"file '{main_clip}'\n")

        if template.outro_path and os.path.exists(template.outro_path):
            f.write(f"file '{template.outro_path}'\n")

    return concat_file


def validate_template(template: BrandTemplate) -> None:
    """
    Validate brand template configuration.

    Args:
        template: BrandTemplate to validate

    Raises:
        ValueError: If template configuration is invalid
        FileNotFoundError: If referenced files don't exist
    """
    if template.logo_path and not os.path.exists(template.logo_path):
        raise FileNotFoundError(f"Logo file not found: {template.logo_path}")

    if template.intro_path and not os.path.exists(template.intro_path):
        raise FileNotFoundError(f"Intro video not found: {template.intro_path}")

    if template.outro_path and not os.path.exists(template.outro_path):
        raise FileNotFoundError(f"Outro video not found: {template.outro_path}")

    if template.logo_position not in LOGO_POSITIONS:
        raise ValueError(
            f"Invalid logo position: {template.logo_position}. "
            f"Choose from: {list(LOGO_POSITIONS.keys())}"
        )

    if not 0.0 <= template.logo_opacity <= 1.0:
        raise ValueError(f"Logo opacity must be between 0.0 and 1.0, got: {template.logo_opacity}")

    if not 5 <= template.logo_size <= 50:
        raise ValueError(f"Logo size must be between 5% and 50%, got: {template.logo_size}%")
