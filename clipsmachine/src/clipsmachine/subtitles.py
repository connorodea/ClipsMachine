import os
import json
import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

from .metadata import call_llm


@dataclass
class SubtitleWord:
    """Represents a single word to highlight in the video."""
    word: str
    start_time: float
    end_time: float


def extract_key_words_with_llm(
    transcript_segment: List[Dict[str, Any]],
    full_text: str,
    max_words: int = 8,
) -> List[str]:
    """
    Use LLM to identify the most impactful words/phrases to highlight.

    Args:
        transcript_segment: Raw transcript entries with timing
        full_text: The full text of the clip
        max_words: Maximum number of words to highlight

    Returns:
        List of key words/phrases to highlight
    """
    prompt = f"""
You are analyzing a short video clip transcript to identify the MOST IMPACTFUL words or short phrases (1-3 words max) to display as large text overlays.

These overlays should:
• Highlight the most emotionally charged or meaningful words
• Capture key concepts, actions, or feelings
• Be visually engaging and easy to read
• Work well as standalone text (like "HEART", "SUCCESS", "NEVER GIVE UP")

TRANSCRIPT:
{full_text}

TASK:
Extract {max_words} key words or short phrases (1-3 words each) that would make compelling text overlays.
Focus on nouns, verbs, and emotional words - avoid filler words like "the", "and", "is", etc.

OUTPUT:
Return STRICT JSON array of strings:
["WORD1", "PHRASE TWO", "WORD3", ...]

No extra commentary. All caps preferred for impact.
"""

    raw = call_llm(prompt)
    cleaned = raw.strip()

    # Remove markdown code blocks if present
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    try:
        key_words = json.loads(cleaned)
        if isinstance(key_words, list):
            return [str(w).upper().strip() for w in key_words[:max_words]]
    except json.JSONDecodeError:
        print(f"[subtitles] WARNING: JSON parse failed. Raw: {raw[:100]}")

    # Fallback: extract words from text
    words = full_text.upper().split()
    return [w.strip(".,!?;:\"'") for w in words[:max_words] if len(w) > 4]


def find_word_timings(
    key_words: List[str],
    transcript_segment: List[Dict[str, Any]],
) -> List[SubtitleWord]:
    """
    Find the timing for each key word in the transcript.

    Args:
        key_words: List of words/phrases to find
        transcript_segment: Transcript entries with 'text', 'start', 'duration'

    Returns:
        List of SubtitleWord objects with timing information
    """
    subtitle_words: List[SubtitleWord] = []

    for key_word in key_words:
        # Normalize the key word for matching
        key_word_normalized = key_word.lower().strip()
        key_word_parts = key_word_normalized.split()

        for i, entry in enumerate(transcript_segment):
            text = entry["text"].lower()

            # Check if the key word appears in this entry
            if key_word_normalized in text or any(part in text for part in key_word_parts):
                start = entry["start"]
                duration = entry["duration"]
                end = start + duration

                # For multi-word phrases, try to extend timing
                if len(key_word_parts) > 1:
                    # Look ahead to capture full phrase timing
                    for j in range(i + 1, min(i + 3, len(transcript_segment))):
                        next_entry = transcript_segment[j]
                        next_text = next_entry["text"].lower()
                        if any(part in next_text for part in key_word_parts):
                            end = next_entry["start"] + next_entry["duration"]

                subtitle_words.append(SubtitleWord(
                    word=key_word,
                    start_time=start,
                    end_time=end,
                ))
                break  # Found this word, move to next

    return subtitle_words


def format_ass_time(seconds: float) -> str:
    """Convert seconds to ASS subtitle time format: H:MM:SS.CS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centisecs = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"


def generate_ass_subtitle_file(
    subtitle_words: List[SubtitleWord],
    output_path: str,
    video_width: int = 1080,
    video_height: int = 1920,
) -> str:
    """
    Generate an ASS subtitle file with styled text overlays.

    The style matches viral short-form content:
    - Large, bold, white text
    - Black outline/shadow for readability
    - Centered on screen
    - High impact positioning

    Args:
        subtitle_words: List of words with timing
        output_path: Path to save the .ass file
        video_width: Video width in pixels (default 1080 for vertical video)
        video_height: Video height in pixels (default 1920 for vertical video)

    Returns:
        Path to the generated subtitle file
    """
    # ASS file header
    ass_content = f"""[Script Info]
Title: Auto-generated subtitles
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,120,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,8,4,2,10,10,850,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    # Add each subtitle word as an event
    for sub_word in subtitle_words:
        start = format_ass_time(sub_word.start_time)
        end = format_ass_time(sub_word.end_time)
        text = sub_word.word.upper()

        # ASS dialogue line
        ass_content += f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n"

    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    return output_path


def generate_subtitles_for_clip(
    transcript_segment: List[Dict[str, Any]],
    full_text: str,
    output_dir: str,
    clip_index: int,
    max_words: int = 8,
) -> str:
    """
    Complete pipeline: extract key words, find timings, generate ASS file.

    Args:
        transcript_segment: Transcript entries for this clip
        full_text: Full text of the clip
        output_dir: Directory to save subtitle file
        clip_index: Clip number (for naming)
        max_words: Maximum words to highlight

    Returns:
        Path to the generated subtitle file
    """
    print(f"[subtitles] Extracting key words for clip #{clip_index}...")
    key_words = extract_key_words_with_llm(transcript_segment, full_text, max_words)
    print(f"[subtitles] Key words: {key_words}")

    print(f"[subtitles] Finding word timings...")
    subtitle_words = find_word_timings(key_words, transcript_segment)
    print(f"[subtitles] Found {len(subtitle_words)} words with timing.")

    subtitle_file = os.path.join(output_dir, f"clip_{clip_index:02d}_subtitles.ass")
    print(f"[subtitles] Generating ASS file: {subtitle_file}")
    generate_ass_subtitle_file(subtitle_words, subtitle_file)

    return subtitle_file
