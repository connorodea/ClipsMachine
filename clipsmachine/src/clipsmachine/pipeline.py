import os
import re
import json
import subprocess
import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

from tqdm import tqdm
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import yt_dlp

from .progress import (
    console,
    print_header,
    print_step,
    print_success,
    print_warning,
    print_info,
    create_progress_bar,
    print_summary_table,
    print_completion_message,
)

from .config import (
    OUTPUT_ROOT,
    MIN_CLIP_SEC,
    TARGET_CLIP_SEC,
    MAX_CLIP_SEC,
    MAX_CLIPS_PER_VIDEO,
)
from .subtitles import generate_subtitles_for_clip
from .whisper_transcribe import generate_whisper_subtitles_for_clip
from .subtitle_styles import create_subtitle_style, style_to_force_style
from .brand_templates import (
    BrandTemplate,
    create_logo_overlay_filter,
    requires_concat,
    build_concat_file_list,
    validate_template,
)

YDL_OPTS = {
    "format": "mp4/bestaudio/best",
    "outtmpl": "%(id)s.%(ext)s",
    "quiet": True,
    "no_warnings": True,
}


@dataclass
class ClipInfo:
    clip_index: int
    start: float
    end: float
    duration: float
    title: str
    description: str
    text_preview: str
    file_name: str
    original_video_url: str


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def extract_video_id(url: str) -> str:
    patterns = [
        r"v=([^&]+)",
        r"youtu.be/([^?&]+)",
        r"shorts/([^?&]+)",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return url.rstrip("/").split("/")[-1]


def human_time(seconds: float) -> str:
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def download_video(url: str, workdir: str) -> str:
    ensure_dir(workdir)
    video_id = extract_video_id(url)
    output_template = os.path.join(workdir, f"{video_id}.%(ext)s")

    ydl_opts = dict(YDL_OPTS)
    ydl_opts["outtmpl"] = output_template

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        ext = info.get("ext", "mp4")

    return os.path.join(workdir, f"{video_id}.{ext}")


def get_transcript(video_id: str) -> List[Dict[str, Any]]:
    try:
        api = YouTubeTranscriptApi()
        transcript_objects = api.fetch(
            video_id,
            languages=["en", "en-US", "en-GB"],
        )
        # Convert transcript objects to dictionaries
        return [
            {
                "start": entry.start,
                "duration": entry.duration,
                "text": entry.text,
            }
            for entry in transcript_objects
        ]
    except (TranscriptsDisabled, NoTranscriptFound) as e:
        raise RuntimeError("No transcript available for this video.") from e


def build_clips_from_transcript(
    transcript: List[Dict[str, Any]],
    min_len: int = MIN_CLIP_SEC,
    target_len: int = TARGET_CLIP_SEC,
    max_len: int = MAX_CLIP_SEC,
    max_clips: int = MAX_CLIPS_PER_VIDEO,
) -> List[Dict[str, Any]]:
    segments: List[Dict[str, Any]] = []
    current_start = None
    current_text: List[str] = []
    current_transcript_entries: List[Dict[str, Any]] = []
    current_end = None

    for entry in transcript:
        start = entry["start"]
        duration = entry["duration"]
        text = entry["text"].replace("\n", " ").strip()

        if current_start is None:
            current_start = start
            current_text = []
            current_transcript_entries = []

        current_text.append(text)
        current_transcript_entries.append(entry)
        current_end = start + duration
        current_duration = current_end - current_start

        if current_duration >= target_len:
            if current_duration > max_len:
                current_end = current_start + max_len
                current_duration = max_len

            segments.append(
                {
                    "start": current_start,
                    "end": current_end,
                    "text": " ".join(current_text).strip(),
                    "transcript_entries": current_transcript_entries,
                }
            )
            current_start = None
            current_text = []
            current_transcript_entries = []
            current_end = None

        if len(segments) >= max_clips:
            break

    if current_start is not None and current_end is not None:
        tail_duration = current_end - current_start
        if tail_duration >= min_len and len(segments) < max_clips:
            segments.append(
                {
                    "start": current_start,
                    "end": current_end,
                    "text": " ".join(current_text).strip(),
                    "transcript_entries": current_transcript_entries,
                }
            )

    return segments


def generate_title(clip_text: str, index: int) -> str:
    cleaned = clip_text.replace("\n", " ").strip()
    if not cleaned:
        return f"Clip #{index}"

    ends = [cleaned.find(sep) for sep in [".", "!", "?"]]
    ends = [i for i in ends if i != -1]
    if ends:
        first_sentence_end = min(ends)
    else:
        first_sentence_end = min(len(cleaned), 80)

    base = cleaned[:first_sentence_end].strip()
    if len(base) < 20:
        base = cleaned[: min(len(cleaned), 90)].strip()

    return base.rstrip(".!?")[:95]


def generate_description(
    original_url: str,
    start: float,
    end: float,
    clip_text: str,
) -> str:
    lines = [
        f"Clip from: {original_url}",
        f"Original segment: {human_time(start)} – {human_time(end)}",
        "",
        "Context of this clip:",
        clip_text[:1000],
        "",
        "All credit to the original creator. "
        "This channel curates the best short moments from long-form conversations.",
    ]
    return "\n".join(lines)


def cut_clip_ffmpeg(
    input_video: str,
    start: float,
    end: float,
    output_path: str,
    subtitle_file: str | None = None,
    style_config: Dict[str, Any] | None = None,
    aspect_ratio: str = "9:16",
    brand_template: BrandTemplate | None = None,
) -> None:
    """
    Cut a clip from the input video, convert to specified aspect ratio, and optionally burn in subtitles and branding.

    Supported aspect ratios:
    - 9:16 (1080x1920) - YouTube Shorts, Instagram Reels, TikTok (default)
    - 1:1 (1080x1080) - Instagram posts
    - 16:9 (1920x1080) - Traditional YouTube videos

    Args:
        input_video: Path to source video
        start: Start time in seconds
        end: End time in seconds
        output_path: Where to save the clip
        subtitle_file: Optional path to ASS subtitle file to burn in
        style_config: Optional style configuration dict for subtitle styling
        aspect_ratio: Output aspect ratio (default: "9:16")
        brand_template: Optional BrandTemplate for logo overlays and intro/outro
    """
    duration = max(end - start, 1.0)

    # Define target dimensions based on aspect ratio
    aspect_configs = {
        "9:16": {"width": 1080, "height": 1920, "ratio": 9/16},  # Vertical (Shorts/Reels/TikTok)
        "1:1": {"width": 1080, "height": 1080, "ratio": 1},      # Square (Instagram)
        "16:9": {"width": 1920, "height": 1080, "ratio": 16/9},  # Horizontal (YouTube)
    }

    if aspect_ratio not in aspect_configs:
        raise ValueError(f"Unsupported aspect ratio: {aspect_ratio}. Choose from: {list(aspect_configs.keys())}")

    config = aspect_configs[aspect_ratio]
    target_width = config["width"]
    target_height = config["height"]
    target_ratio = config["ratio"]

    # Build video filter for aspect ratio conversion
    # Strategy: Scale and crop to target dimensions while maintaining center focus
    video_filters = [
        # Scale to fit within target dimensions, maintaining aspect ratio
        f"scale='if(gt(iw/ih,{target_ratio}),{target_width},-2)':'if(gt(iw/ih,{target_ratio}),-2,{target_height})'",
        # Pad to exactly target dimensions if needed (center the content)
        f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:black",
        # If source is wider than target, crop instead
        f"crop='if(gt(iw/ih,{target_ratio}),ih*{target_ratio},iw)':'if(gt(iw/ih,{target_ratio}),ih,iw/{target_ratio})'",
        # Final scale to ensure exact dimensions
        f"scale={target_width}:{target_height}",
    ]

    # Add subtitles filter if provided
    if subtitle_file and os.path.exists(subtitle_file):
        # Create style from config for force_style parameter
        if style_config is None:
            style_config = {}

        subtitle_style = create_subtitle_style(**style_config)
        force_style = style_to_force_style(subtitle_style)

        video_filters.append(
            f"subtitles={subtitle_file}:force_style='{force_style}'"
        )

    # Build FFmpeg command
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start),
        "-i",
        input_video,
    ]

    # Add logo input if brand template with logo is provided
    use_filter_complex = False
    if brand_template and brand_template.logo_path:
        validate_template(brand_template)
        cmd.extend(["-i", brand_template.logo_path])
        use_filter_complex = True

    cmd.extend(["-t", str(duration)])

    # Build filter string (either -vf or -filter_complex)
    if use_filter_complex:
        # Use filter_complex for logo overlay
        # First apply aspect ratio conversion, then overlay logo
        vf_base = ",".join(video_filters)

        # Create logo overlay filter
        logo_filter = create_logo_overlay_filter(
            brand_template.logo_path,
            brand_template.logo_position,
            brand_template.logo_size,
            brand_template.logo_opacity,
            target_width,
        )

        # Combine: [0:v] aspect conversion [out]; [out][1:v overlay with logo]
        filter_complex = f"[0:v]{vf_base}[base];{logo_filter}"

        cmd.extend(["-filter_complex", filter_complex])
    else:
        # Use simple -vf for aspect ratio conversion and subtitles
        vf_string = ",".join(video_filters)
        cmd.extend(["-vf", vf_string])

    # Add encoding options
    cmd.extend([
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "23",
        "-profile:v",
        "high",
        "-level",
        "4.2",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ar",
        "44100",
        output_path,
    ])

    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def process_video(
    url: str,
    enable_subtitles: bool = True,
    subtitle_type: str = "transcription",
    style_config: Dict[str, Any] | None = None,
    aspect_ratio: str = "9:16",
    brand_template: BrandTemplate | None = None,
) -> List[ClipInfo]:
    """
    Process a YouTube video: download, generate clips, and optionally add subtitles and branding.

    Args:
        url: YouTube video URL
        enable_subtitles: Whether to generate and burn in text overlays (default: True)
        subtitle_type: Type of subtitles - "keywords", "transcription", or "both"
        style_config: Optional style configuration dict for subtitle styling
        aspect_ratio: Output aspect ratio - "9:16" (Shorts), "1:1" (Instagram), "16:9" (YouTube) (default: "9:16")
        brand_template: Optional BrandTemplate for logo overlays and intro/outro

    Returns:
        List of ClipInfo objects
    """
    if style_config is None:
        style_config = {}
    start_time = time.time()
    video_id = extract_video_id(url)
    video_dir = os.path.join(OUTPUT_ROOT, video_id)
    raw_dir = os.path.join(video_dir, "raw")
    clips_dir = os.path.join(video_dir, "clips")
    subtitles_dir = os.path.join(video_dir, "subtitles")

    ensure_dir(raw_dir)
    ensure_dir(clips_dir)
    if enable_subtitles:
        ensure_dir(subtitles_dir)

    # Header
    print_header("ClipsMachine", f"Processing: {url}")

    # Download video
    print_info(f"Video ID: {video_id}")
    print_info(f"Subtitle Type: {subtitle_type if enable_subtitles else 'None'}")
    print_info(f"Aspect Ratio: {aspect_ratio}")
    console.print()

    with console.status("[bold cyan]Downloading video...", spinner="dots"):
        video_path = download_video(url, raw_dir)
    print_success(f"Downloaded video")

    # Fetch transcript
    with console.status("[bold cyan]Fetching transcript...", spinner="dots"):
        transcript = get_transcript(video_id)
    print_success(f"Fetched transcript ({len(transcript)} entries)")

    # Build segments
    with console.status("[bold cyan]Building clip segments...", spinner="dots"):
        segments = build_clips_from_transcript(transcript)
    if not segments:
        raise RuntimeError("No segments generated – adjust clip settings.")

    print_success(f"Generated {len(segments)} clip segments")
    console.print()
    clips: List[ClipInfo] = []

    # Process clips with progress bar
    print_info("Processing clips...")
    with create_progress_bar() as progress:
        task = progress.add_task("[cyan]Generating clips...", total=len(segments))

        for idx, seg in enumerate(segments, start=1):
            start = seg["start"]
            end = seg["end"]
            text = seg["text"]
            duration = end - start
            transcript_entries = seg.get("transcript_entries", [])

            file_name = f"{video_id}_clip_{idx:02d}.mp4"
            output_path = os.path.join(clips_dir, file_name)

            progress.update(task, description=f"[cyan]Processing clip #{idx}/{len(segments)}...")

            # Generate subtitles if enabled
            subtitle_file = None
            if enable_subtitles:
                try:
                    if subtitle_type == "keywords" and transcript_entries:
                        # Key word overlays using LLM
                        adjusted_entries = []
                        for entry in transcript_entries:
                            adjusted_entry = entry.copy()
                            adjusted_entry["start"] = max(0, entry["start"] - start)
                            adjusted_entries.append(adjusted_entry)

                        subtitle_file = generate_subtitles_for_clip(
                            transcript_segment=adjusted_entries,
                            full_text=text,
                            output_dir=subtitles_dir,
                            clip_index=idx,
                        )
                    elif subtitle_type == "transcription":
                        # Full transcription using Whisper
                        # Need to cut the clip first, then transcribe it
                        temp_clip_path = os.path.join(clips_dir, f"temp_{file_name}")
                        cut_clip_ffmpeg(video_path, start, end, temp_clip_path, subtitle_file=None, style_config=style_config, aspect_ratio=aspect_ratio, brand_template=brand_template)

                        subtitle_file = generate_whisper_subtitles_for_clip(
                            video_path=temp_clip_path,
                            output_dir=subtitles_dir,
                            clip_index=idx,
                            subtitle_format="ass",
                            style_config=style_config,
                        )

                        # Remove temp clip, will regenerate with subtitles
                        os.remove(temp_clip_path)

                    elif subtitle_type == "both":
                        # Generate both types - this is advanced, for now just use transcription
                        print(f"[pipeline] 'both' subtitle type not fully implemented yet, using transcription")
                        temp_clip_path = os.path.join(clips_dir, f"temp_{file_name}")
                        cut_clip_ffmpeg(video_path, start, end, temp_clip_path, subtitle_file=None, style_config=style_config, aspect_ratio=aspect_ratio, brand_template=brand_template)

                        subtitle_file = generate_whisper_subtitles_for_clip(
                            video_path=temp_clip_path,
                            output_dir=subtitles_dir,
                            clip_index=idx,
                            subtitle_format="ass",
                            style_config=style_config,
                        )

                        os.remove(temp_clip_path)

                except Exception as e:
                    print(f"[pipeline] Warning: Subtitle generation failed for clip #{idx}: {e}")
                    subtitle_file = None

            # Cut the clip with optional subtitles
            # For transcription, we already cut a temp clip above, so only cut with subtitles
            if subtitle_type == "transcription" or subtitle_type == "both":
                if subtitle_file and os.path.exists(subtitle_file):
                    cut_clip_ffmpeg(video_path, start, end, output_path, subtitle_file, style_config=style_config, aspect_ratio=aspect_ratio, brand_template=brand_template)
                else:
                    cut_clip_ffmpeg(video_path, start, end, output_path, subtitle_file=None, style_config=style_config, aspect_ratio=aspect_ratio, brand_template=brand_template)
            else:
                # For keywords or no subtitles
                cut_clip_ffmpeg(video_path, start, end, output_path, subtitle_file, style_config=style_config, aspect_ratio=aspect_ratio, brand_template=brand_template)

            title = generate_title(text, idx)
            description = generate_description(url, start, end, text)

            clip_info = ClipInfo(
                clip_index=idx,
                start=start,
                end=end,
                duration=duration,
                title=title,
                description=description,
                text_preview=text[:300],
                file_name=file_name,
                original_video_url=url,
            )
            clips.append(clip_info)

            progress.advance(task)

    # Save manifest
    manifest_path = os.path.join(video_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump([asdict(c) for c in clips], f, indent=2, ensure_ascii=False)

    # Print summary
    elapsed_time = time.time() - start_time
    console.print()
    print_success(f"All clips processed!")
    print_summary_table([asdict(c) for c in clips], subtitle_type if enable_subtitles else None)
    print_completion_message(video_id, len(clips), elapsed_time)

    print_info(f"Output: {clips_dir}")
    print_info(f"Manifest: {manifest_path}")

    return clips
