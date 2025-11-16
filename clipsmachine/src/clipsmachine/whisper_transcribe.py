import os
import subprocess
from typing import List, Dict, Any, Optional
from pathlib import Path

from openai import OpenAI
from .subtitle_styles import create_subtitle_style, style_to_ass_format


def extract_audio_from_clip(video_path: str, output_dir: str) -> str:
    """
    Extract audio from a video clip for Whisper transcription.

    Args:
        video_path: Path to the video clip
        output_dir: Directory to save the audio file

    Returns:
        Path to the extracted audio file
    """
    os.makedirs(output_dir, exist_ok=True)

    video_name = Path(video_path).stem
    audio_path = os.path.join(output_dir, f"{video_name}.mp3")

    # Extract audio using ffmpeg
    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-vn",  # No video
        "-acodec", "libmp3lame",
        "-b:a", "192k",
        audio_path,
    ]

    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return audio_path


def transcribe_with_whisper(audio_path: str) -> Any:
    """
    Transcribe audio using OpenAI's Whisper API with word-level timestamps.

    Args:
        audio_path: Path to the audio file

    Returns:
        Transcription result object with word-level timestamps
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable not set.")

    client = OpenAI(api_key=api_key)

    print(f"[whisper] Transcribing audio: {audio_path}")

    with open(audio_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="verbose_json",
            timestamp_granularities=["word", "segment"],
            language="en",  # Improves accuracy
        )

    return transcript


def format_srt_time(seconds: float) -> str:
    """Convert seconds to SRT subtitle time format: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"


def format_ass_time(seconds: float) -> str:
    """Convert seconds to ASS subtitle time format: H:MM:SS.CS"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centisecs = int((seconds % 1) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"


def generate_word_by_word_subtitles_srt(
    transcript: Any,
    output_path: str,
    words_per_line: int = 3,
) -> str:
    """
    Generate SRT subtitle file with word-by-word captions.

    Args:
        transcript: Whisper transcription result object
        output_path: Path to save the SRT file
        words_per_line: Number of words to show per subtitle line

    Returns:
        Path to the generated SRT file
    """
    # Access words as attribute, not dict key
    words = getattr(transcript, "words", [])
    if not words:
        # Fallback: create from full text
        print("[whisper] WARNING: No word-level timestamps, using full text")
        text = getattr(transcript, "text", "")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("1\n")
            f.write("00:00:00,000 --> 00:00:05,000\n")
            f.write(f"{text}\n\n")
        return output_path

    srt_content = []
    subtitle_index = 1

    i = 0
    while i < len(words):
        # Group words into chunks
        chunk = words[i:i + words_per_line]

        # Access word attributes, not dict keys
        start_time = getattr(chunk[0], "start", 0)
        end_time = getattr(chunk[-1], "end", start_time + 2)

        # Build the text for this subtitle
        text = " ".join([getattr(w, "word", "").strip() for w in chunk])

        # SRT format
        srt_content.append(f"{subtitle_index}")
        srt_content.append(f"{format_srt_time(start_time)} --> {format_srt_time(end_time)}")
        srt_content.append(text.upper())  # All caps for impact
        srt_content.append("")  # Blank line between subtitles

        subtitle_index += 1
        i += words_per_line

    # Write SRT file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(srt_content))

    return output_path


def generate_word_by_word_subtitles_ass(
    transcript: Any,
    output_path: str,
    words_per_line: int = 3,
    video_width: int = 1080,
    video_height: int = 1920,
    style_config: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate ASS subtitle file with word-by-word captions.
    Styled for short-form vertical video with modern appearance.

    Args:
        transcript: Whisper transcription result object
        output_path: Path to save the ASS file
        words_per_line: Number of words to show per subtitle line
        video_width: Video width in pixels
        video_height: Video height in pixels
        style_config: Optional style configuration dict

    Returns:
        Path to the generated ASS file
    """
    # Access words as attribute, not dict key
    words = getattr(transcript, "words", [])
    if not words:
        print("[whisper] WARNING: No word-level timestamps")
        return output_path

    # Create subtitle style from config
    if style_config is None:
        style_config = {}

    subtitle_style = create_subtitle_style(**style_config)
    style_line = style_to_ass_format(subtitle_style)

    # ASS file header with customizable styling
    ass_content = f"""[Script Info]
Title: Whisper Transcription
ScriptType: v4.00+
PlayResX: {video_width}
PlayResY: {video_height}
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style_line}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    dialogue_lines = []
    i = 0

    while i < len(words):
        # Group words into chunks
        chunk = words[i:i + words_per_line]

        # Access word attributes, not dict keys
        start_time = getattr(chunk[0], "start", 0)
        end_time = getattr(chunk[-1], "end", start_time + 2)

        # Build the text for this subtitle
        text = " ".join([getattr(w, "word", "").strip() for w in chunk])

        # ASS dialogue line
        dialogue_lines.append(
            f"Dialogue: 0,{format_ass_time(start_time)},{format_ass_time(end_time)},Default,,0,0,0,,{text.upper()}"
        )

        i += words_per_line

    ass_content += "\n".join(dialogue_lines) + "\n"

    # Write ASS file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    return output_path


def generate_whisper_subtitles_for_clip(
    video_path: str,
    output_dir: str,
    clip_index: int,
    subtitle_format: str = "ass",
    words_per_line: int = 3,
    style_config: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Complete pipeline: extract audio, transcribe with Whisper, generate subtitles.

    Args:
        video_path: Path to the video clip
        output_dir: Directory to save files
        clip_index: Clip number (for naming)
        subtitle_format: "srt" or "ass"
        words_per_line: Words to display per subtitle line
        style_config: Optional style configuration dict

    Returns:
        Path to the generated subtitle file
    """
    print(f"[whisper] Processing clip #{clip_index} for transcription...")

    # Extract audio
    audio_dir = os.path.join(output_dir, "audio_temp")
    audio_path = extract_audio_from_clip(video_path, audio_dir)

    # Transcribe with Whisper
    transcript = transcribe_with_whisper(audio_path)

    # Generate subtitle file
    subtitle_ext = subtitle_format.lower()
    subtitle_path = os.path.join(output_dir, f"clip_{clip_index:02d}_whisper.{subtitle_ext}")

    if subtitle_format == "ass":
        generate_word_by_word_subtitles_ass(
            transcript, subtitle_path, words_per_line, style_config=style_config
        )
    else:
        generate_word_by_word_subtitles_srt(transcript, subtitle_path, words_per_line)

    print(f"[whisper] Generated subtitle file: {subtitle_path}")

    # Clean up audio file
    try:
        os.remove(audio_path)
    except:
        pass

    return subtitle_path
