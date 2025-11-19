"""
Subtitle styling configuration for clipsmachine.
Provides font presets, color schemes, and effect configurations for ASS subtitles.
"""

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass
class SubtitleStyle:
    """Configuration for ASS subtitle styling."""
    font_name: str
    font_size: int
    primary_color: str  # &HAABBGGRR format (ASS uses BGR not RGB)
    outline_color: str
    shadow_color: str
    bold: int  # -1 for true, 0 for false
    italic: int
    outline_width: int
    shadow_depth: int
    blur: int  # Blur/glow effect (0-100)
    alignment: int  # 1-9 (numpad layout): 1-3=bottom, 4-6=middle, 7-9=top; 2=bottom-center, 5=middle-center
    margin_v: int  # Vertical margin: distance from bottom for bottom alignments, from center for middle


# Predefined font presets - optimized for short-form vertical video
# Ordered by popularity and readability on mobile devices
FONT_PRESETS = {
    "montserrat": {
        "name": "Montserrat",
        "description": "🏆 Modern, clean font - perfect for business/tech content (DEFAULT - most popular)",
        "font_name": "Montserrat",
        "bold": -1,
    },
    "poppins": {
        "name": "Poppins",
        "description": "😊 Friendly, rounded font - great for lifestyle, wellness, casual content",
        "font_name": "Poppins",
        "bold": -1,
    },
    "impact": {
        "name": "Impact",
        "description": "💥 Bold, high-impact - perfect for motivational, fitness, sports content",
        "font_name": "Impact",
        "bold": -1,
    },
    "bebas": {
        "name": "Bebas Neue",
        "description": "📰 Tall, condensed - excellent for news, headlines, dramatic content",
        "font_name": "Bebas Neue",
        "bold": -1,
    },
    "roboto": {
        "name": "Roboto",
        "description": "🤖 Ultra-clean, modern - ideal for tech, science, education content",
        "font_name": "Roboto",
        "bold": -1,
    },
    "oswald": {
        "name": "Oswald",
        "description": "⚡ Bold, condensed - great for action, gaming, high-energy content",
        "font_name": "Oswald",
        "bold": -1,
    },
    "arial": {
        "name": "Arial Black",
        "description": "📺 Classic, reliable - universal readability, traditional content",
        "font_name": "Arial Black",
        "bold": -1,
    },
    "bangers": {
        "name": "Bangers",
        "description": "🎮 Comic-style, playful - perfect for gaming, entertainment, memes",
        "font_name": "Bangers",
        "bold": 0,
    },
}


# Color presets (ASS format: &HAABBGGRR where AA=alpha, BB=blue, GG=green, RR=red)
COLOR_PRESETS = {
    "white": "&H00FFFFFF",
    "black": "&H00000000",
    "red": "&H000000FF",
    "blue": "&H00FF0000",
    "yellow": "&H0000FFFF",
    "green": "&H0000FF00",
    "cyan": "&H00FFFF00",
    "magenta": "&H00FF00FF",
    "orange": "&H000080FF",
    "purple": "&H00800080",
}


def rgb_to_ass_color(r: int, g: int, b: int, alpha: int = 0) -> str:
    """
    Convert RGB color to ASS color format (&HAABBGGRR).

    Args:
        r: Red (0-255)
        g: Green (0-255)
        b: Blue (0-255)
        alpha: Alpha/transparency (0-255, 0=opaque)

    Returns:
        ASS color string
    """
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"


def create_subtitle_style(
    font_preset: str = "montserrat",  # Modern, clean default font
    font_size: int = 65,  # Reduced from 80 for better readability
    text_color: str = "white",
    outline_color: str = "black",
    shadow_color: str = "black",
    outline_width: int = 5,  # Slightly reduced for cleaner look
    shadow_depth: int = 2,  # Reduced shadow for modern aesthetic
    blur: int = 0,
    glow: bool = False,
    alignment: int = 2,  # 2 = bottom-center, positioned up with margin_v
    margin_v: int = 850,   # Distance from bottom to center the subtitles (for 1920px height)
) -> SubtitleStyle:
    """
    Create a SubtitleStyle configuration.

    Args:
        font_preset: Font preset key (see FONT_PRESETS)
        font_size: Font size in pixels
        text_color: Text color (preset name or ASS color code)
        outline_color: Outline color
        shadow_color: Shadow color
        outline_width: Outline thickness (0-10)
        shadow_depth: Shadow depth (0-10)
        blur: Blur amount for glow effect (0-10)
        glow: Enable glow effect (adds blur + shadow)
        alignment: Text alignment (1-9: numpad layout, where 2 is bottom-center, 5 is middle-center)
        margin_v: Vertical margin from edge (distance from bottom for bottom alignments)

    Returns:
        SubtitleStyle object
    """
    # Get font configuration
    font_config = FONT_PRESETS.get(font_preset, FONT_PRESETS["arial"])
    font_name = font_config["font_name"]
    bold = font_config["bold"]

    # Resolve colors
    primary_color = COLOR_PRESETS.get(text_color, text_color)
    outline_col = COLOR_PRESETS.get(outline_color, outline_color)
    shadow_col = COLOR_PRESETS.get(shadow_color, shadow_color)

    # Apply glow effect if enabled
    if glow:
        blur = max(blur, 2)  # Minimum blur for glow
        shadow_depth = max(shadow_depth, 2)

    return SubtitleStyle(
        font_name=font_name,
        font_size=font_size,
        primary_color=primary_color,
        outline_color=outline_col,
        shadow_color=shadow_col,
        bold=bold,
        italic=0,
        outline_width=outline_width,
        shadow_depth=shadow_depth,
        blur=blur,
        alignment=alignment,
        margin_v=margin_v,
    )


def style_to_ass_format(style: SubtitleStyle) -> str:
    """
    Convert SubtitleStyle to ASS format style definition.

    Args:
        style: SubtitleStyle object

    Returns:
        ASS style format string
    """
    return (
        f"Style: Default,{style.font_name},{style.font_size},"
        f"{style.primary_color},&H000000FF,{style.outline_color},{style.shadow_color},"
        f"{style.bold},0,0,0,100,100,0,0,1,{style.outline_width},{style.shadow_depth},"
        f"{style.alignment},10,10,{style.margin_v},1"
    )


def style_to_force_style(style: SubtitleStyle) -> str:
    """
    Convert SubtitleStyle to FFmpeg force_style parameter.

    Args:
        style: SubtitleStyle object

    Returns:
        FFmpeg force_style string
    """
    parts = [
        f"FontName={style.font_name}",
        f"FontSize={style.font_size}",
        f"Bold={'1' if style.bold == -1 else '0'}",
        f"PrimaryColour={style.primary_color}",
        f"OutlineColour={style.outline_color}",
        f"BorderStyle=1",
        f"Outline={style.outline_width}",
        f"Shadow={style.shadow_depth}",
        f"Alignment={style.alignment}",
        f"MarginV={style.margin_v}",
    ]

    if style.blur > 0:
        parts.append(f"Blur={style.blur}")

    return ",".join(parts)


def get_available_fonts() -> Dict[str, str]:
    """
    Get list of available font presets with descriptions.

    Returns:
        Dict mapping font preset keys to descriptions
    """
    return {
        key: f"{config['name']} - {config['description']}"
        for key, config in FONT_PRESETS.items()
    }
