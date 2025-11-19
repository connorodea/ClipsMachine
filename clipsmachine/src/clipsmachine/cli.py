import argparse
import os

from .pipeline import process_video, extract_video_id
from .metadata import enhance_manifest
from .uploader import upload_clips_for_video
from .config import OUTPUT_ROOT
from .subtitle_styles import get_available_fonts
from .brand_templates import BrandTemplate


def _build_style_config(args: argparse.Namespace) -> dict:
    """Extract subtitle style configuration from CLI arguments."""
    return {
        'font_preset': getattr(args, 'font', 'arial'),
        'font_size': getattr(args, 'font_size', 80),
        'text_color': getattr(args, 'text_color', 'white'),
        'outline_color': getattr(args, 'outline_color', 'black'),
        'outline_width': getattr(args, 'outline_width', 6),
        'shadow_depth': getattr(args, 'shadow_depth', 3),
        'glow': getattr(args, 'glow', False),
    }


def _build_brand_template(args: argparse.Namespace) -> BrandTemplate | None:
    """Extract brand template configuration from CLI arguments."""
    if not getattr(args, 'logo', None):
        return None

    return BrandTemplate(
        logo_path=args.logo,
        logo_position=getattr(args, 'logo_position', 'top-right'),
        logo_size=getattr(args, 'logo_size', 15),
        logo_opacity=getattr(args, 'logo_opacity', 1.0),
        intro_path=getattr(args, 'intro', None),
        outro_path=getattr(args, 'outro', None),
    )


def cmd_run(args: argparse.Namespace) -> None:
    url = args.youtube_url
    video_id = extract_video_id(url)

    print(f"[run] Source: {url}")
    print(f"[run] Video ID: {video_id}")
    os.makedirs(OUTPUT_ROOT, exist_ok=True)

    print("\n[1/3] Generating clips…")
    enable_subtitles = not args.skip_subtitles
    subtitle_type = args.subtitle_type if hasattr(args, 'subtitle_type') else "transcription"

    # Build configuration from CLI arguments
    style_config = _build_style_config(args)
    aspect_ratio = getattr(args, 'aspect_ratio', '9:16')
    brand_template = _build_brand_template(args)

    clips = process_video(
        url,
        enable_subtitles=enable_subtitles,
        subtitle_type=subtitle_type,
        style_config=style_config,
        aspect_ratio=aspect_ratio,
        brand_template=brand_template
    )
    print(f"[1/3] Generated {len(clips)} clips.")

    if not args.skip_llm:
        print("\n[2/3] Enhancing metadata with LLM…")
        enhance_manifest(
            video_id=video_id,
            channel_positioning=args.positioning,
            base_tags=args.tags,
            start_index=args.start_index,
            max_clips=args.max_clips,
        )
        print("[2/3] Metadata enhancement complete.")
    else:
        print("\n[2/3] Skipping LLM metadata (per --skip-llm).")

    if not args.skip_upload:
        print("\n[3/3] Uploading to YouTube…")
        upload_clips_for_video(
            video_id=video_id,
            privacy_status=args.privacy,
            start_index=args.start_index,
            max_clips=args.max_clips,
            sleep_between=args.sleep_between_uploads,
        )
        print("[3/3] Uploads complete.")
    else:
        print("\n[3/3] Skipping upload (per --skip-upload).")

    print("\n[run] Done.")


def cmd_clip_only(args: argparse.Namespace) -> None:
    url = args.youtube_url
    os.makedirs(OUTPUT_ROOT, exist_ok=True)
    enable_subtitles = not args.skip_subtitles
    subtitle_type = args.subtitle_type if hasattr(args, 'subtitle_type') else "transcription"

    # Build configuration from CLI arguments
    style_config = _build_style_config(args)
    aspect_ratio = getattr(args, 'aspect_ratio', '9:16')
    brand_template = _build_brand_template(args)

    process_video(
        url,
        enable_subtitles=enable_subtitles,
        subtitle_type=subtitle_type,
        style_config=style_config,
        aspect_ratio=aspect_ratio,
        brand_template=brand_template
    )


def cmd_enhance(args: argparse.Namespace) -> None:
    enhance_manifest(
        video_id=args.video_id,
        channel_positioning=args.positioning,
        base_tags=args.tags,
        start_index=args.start_index,
        max_clips=args.max_clips,
    )


def cmd_upload(args: argparse.Namespace) -> None:
    upload_clips_for_video(
        video_id=args.video_id,
        privacy_status=args.privacy,
        start_index=args.start_index,
        max_clips=args.max_clips,
        sleep_between=args.sleep_between_uploads,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="clipsmachine",
        description="Automated YouTube clips generator/uploader.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = subparsers.add_parser(
        "run", help="Download → clip → LLM metadata → upload."
    )
    p_run.add_argument("youtube_url", help="YouTube URL of long-form video.")
    p_run.add_argument(
        "--privacy",
        choices=["public", "unlisted", "private"],
        default="unlisted",
        help="YouTube privacy for uploads (default: unlisted).",
    )
    p_run.add_argument(
        "--max-clips",
        type=int,
        default=None,
        help="Limit number of clips to process/upload.",
    )
    p_run.add_argument(
        "--start-index",
        type=int,
        default=1,
        help="Start from this clip_index (1-based).",
    )
    p_run.add_argument(
        "--positioning",
        type=str,
        default=(
            "We run a clips channel that curates short, high-impact moments "
            "from long-form conversations about business, psychology, performance, and self-improvement."
        ),
        help="Channel positioning string for LLM prompts.",
    )
    p_run.add_argument(
        "--tags",
        type=str,
        default="clips,podcast,business,mindset,self improvement",
        help="Comma-separated base tags (LLM context only).",
    )
    p_run.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip LLM metadata enhancement.",
    )
    p_run.add_argument(
        "--skip-upload",
        action="store_true",
        help="Skip YouTube upload.",
    )
    p_run.add_argument(
        "--skip-subtitles",
        action="store_true",
        help="Skip text overlay generation (faster but less engaging).",
    )
    p_run.add_argument(
        "--subtitle-type",
        choices=["keywords", "transcription", "both"],
        default="transcription",
        help="Type of subtitles: 'keywords' (LLM-selected key words), 'transcription' (full Whisper AI captions), or 'both' (default: transcription).",
    )
    p_run.add_argument(
        "--sleep-between-uploads",
        type=int,
        default=5,
        help="Seconds between uploads (default: 5).",
    )
    # Font and styling options
    p_run.add_argument(
        "--font",
        choices=list(get_available_fonts().keys()),
        default="montserrat",
        help="Font preset: impact, arial, montserrat, bebas, bangers, oswald, roboto, poppins (default: montserrat).",
    )
    p_run.add_argument(
        "--font-size",
        type=int,
        default=65,
        help="Font size in pixels (default: 65 - optimized for readability).",
    )
    p_run.add_argument(
        "--text-color",
        type=str,
        default="white",
        help="Text color: white, black, red, blue, yellow, green, cyan, magenta, orange, purple (default: white).",
    )
    p_run.add_argument(
        "--outline-color",
        type=str,
        default="black",
        help="Outline/border color (default: black).",
    )
    p_run.add_argument(
        "--outline-width",
        type=int,
        default=5,
        help="Outline thickness in pixels (default: 5 - balanced for clarity).",
    )
    p_run.add_argument(
        "--shadow-depth",
        type=int,
        default=2,
        help="Shadow depth in pixels (default: 2 - subtle modern look).",
    )
    p_run.add_argument(
        "--glow",
        action="store_true",
        help="Enable glow effect on text (adds blur).",
    )
    p_run.add_argument(
        "--aspect-ratio",
        choices=["9:16", "1:1", "16:9"],
        default="9:16",
        help="Output aspect ratio: 9:16 (Shorts/Reels/TikTok), 1:1 (Instagram), 16:9 (YouTube) (default: 9:16).",
    )
    # Brand template options
    p_run.add_argument(
        "--logo",
        type=str,
        default=None,
        help="Path to logo image file (PNG with transparency recommended).",
    )
    p_run.add_argument(
        "--logo-position",
        choices=["top-left", "top-right", "bottom-left", "bottom-right", "center"],
        default="top-right",
        help="Logo position on video (default: top-right).",
    )
    p_run.add_argument(
        "--logo-size",
        type=int,
        default=15,
        help="Logo size as percentage of video width, 5-50 (default: 15).",
    )
    p_run.add_argument(
        "--logo-opacity",
        type=float,
        default=1.0,
        help="Logo opacity, 0.0-1.0 (default: 1.0).",
    )
    p_run.add_argument(
        "--intro",
        type=str,
        default=None,
        help="Path to intro video clip (will be prepended to each clip).",
    )
    p_run.add_argument(
        "--outro",
        type=str,
        default=None,
        help="Path to outro video clip (will be appended to each clip).",
    )
    p_run.set_defaults(func=cmd_run)

    # clip
    p_clip = subparsers.add_parser(
        "clip", help="Only download and generate clips + manifest."
    )
    p_clip.add_argument("youtube_url", help="YouTube URL of long-form video.")
    p_clip.add_argument(
        "--skip-subtitles",
        action="store_true",
        help="Skip text overlay generation.",
    )
    p_clip.add_argument(
        "--subtitle-type",
        choices=["keywords", "transcription", "both"],
        default="transcription",
        help="Type of subtitles (default: transcription).",
    )
    # Font and styling options
    p_clip.add_argument(
        "--font",
        choices=list(get_available_fonts().keys()),
        default="montserrat",
        help="Font preset: impact, arial, montserrat, bebas, bangers, oswald, roboto, poppins (default: montserrat).",
    )
    p_clip.add_argument(
        "--font-size",
        type=int,
        default=65,
        help="Font size in pixels (default: 65 - optimized for readability).",
    )
    p_clip.add_argument(
        "--text-color",
        type=str,
        default="white",
        help="Text color: white, black, red, blue, yellow, green, cyan, magenta, orange, purple (default: white).",
    )
    p_clip.add_argument(
        "--outline-color",
        type=str,
        default="black",
        help="Outline/border color (default: black).",
    )
    p_clip.add_argument(
        "--outline-width",
        type=int,
        default=5,
        help="Outline thickness in pixels (default: 5 - balanced for clarity).",
    )
    p_clip.add_argument(
        "--shadow-depth",
        type=int,
        default=2,
        help="Shadow depth in pixels (default: 2 - subtle modern look).",
    )
    p_clip.add_argument(
        "--glow",
        action="store_true",
        help="Enable glow effect on text (adds blur).",
    )
    p_clip.add_argument(
        "--aspect-ratio",
        choices=["9:16", "1:1", "16:9"],
        default="9:16",
        help="Output aspect ratio: 9:16 (Shorts/Reels/TikTok), 1:1 (Instagram), 16:9 (YouTube) (default: 9:16).",
    )
    # Brand template options
    p_clip.add_argument(
        "--logo",
        type=str,
        default=None,
        help="Path to logo image file (PNG with transparency recommended).",
    )
    p_clip.add_argument(
        "--logo-position",
        choices=["top-left", "top-right", "bottom-left", "bottom-right", "center"],
        default="top-right",
        help="Logo position on video (default: top-right).",
    )
    p_clip.add_argument(
        "--logo-size",
        type=int,
        default=15,
        help="Logo size as percentage of video width, 5-50 (default: 15).",
    )
    p_clip.add_argument(
        "--logo-opacity",
        type=float,
        default=1.0,
        help="Logo opacity, 0.0-1.0 (default: 1.0).",
    )
    p_clip.add_argument(
        "--intro",
        type=str,
        default=None,
        help="Path to intro video clip (will be prepended to each clip).",
    )
    p_clip.add_argument(
        "--outro",
        type=str,
        default=None,
        help="Path to outro video clip (will be appended to each clip).",
    )
    p_clip.set_defaults(func=cmd_clip_only)

    # enhance
    p_enhance = subparsers.add_parser(
        "enhance", help="Only run LLM metadata enhancement on existing manifest."
    )
    p_enhance.add_argument("video_id", help="Video ID folder under clips_output/<video_id>/")
    p_enhance.add_argument(
        "--positioning",
        type=str,
        default=(
            "We run a clips channel that curates short, high-impact moments "
            "from long-form conversations about business, psychology, performance, and self-improvement."
        ),
        help="Channel positioning string for LLM prompts.",
    )
    p_enhance.add_argument(
        "--tags",
        type=str,
        default="clips,podcast,business,mindset,self improvement",
        help="Comma-separated base tags (LLM context only).",
    )
    p_enhance.add_argument(
        "--start-index",
        type=int,
        default=1,
        help="Start from this clip_index (1-based).",
    )
    p_enhance.add_argument(
        "--max-clips",
        type=int,
        default=None,
        help="Limit number of clips to enhance.",
    )
    p_enhance.set_defaults(func=cmd_enhance)

    # upload
    p_upload = subparsers.add_parser(
        "upload", help="Only upload existing clips using manifest."
    )
    p_upload.add_argument("video_id", help="Video ID folder under clips_output/<video_id>/")
    p_upload.add_argument(
        "--privacy",
        choices=["public", "unlisted", "private"],
        default="unlisted",
        help="YouTube privacy for uploads (default: unlisted).",
    )
    p_upload.add_argument(
        "--start-index",
        type=int,
        default=1,
        help="Start from this clip_index (1-based).",
    )
    p_upload.add_argument(
        "--max-clips",
        type=int,
        default=None,
        help="Limit number of clips to upload.",
    )
    p_upload.add_argument(
        "--sleep-between-uploads",
        type=int,
        default=5,
        help="Seconds between uploads (default: 5).",
    )
    p_upload.set_defaults(func=cmd_upload)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
