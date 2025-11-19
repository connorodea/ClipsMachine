import argparse
import os

from .pipeline import process_video, extract_video_id
from .metadata import enhance_manifest
from .uploader import upload_clips_for_video
from .config import OUTPUT_ROOT
from .subtitle_styles import get_available_fonts
from .brand_templates import BrandTemplate
from .multi_uploader import MultiPlatformUploader, print_platform_info
from .platforms import get_all_platforms
from .thumbnail_generator import ThumbnailGenerator
from .cloud_storage import CloudStorageManager
from .scheduler import PostScheduler, process_pending_posts
from datetime import datetime, timedelta


def _build_style_config(args: argparse.Namespace) -> dict:
    """Extract subtitle style configuration from CLI arguments."""
    return {
        'font_preset': getattr(args, 'font', 'montserrat'),
        'font_size': getattr(args, 'font_size', 68),
        'text_color': getattr(args, 'text_color', 'white'),
        'outline_color': getattr(args, 'outline_color', 'black'),
        'outline_width': getattr(args, 'outline_width', 7),
        'shadow_depth': getattr(args, 'shadow_depth', 3),
        'glow': getattr(args, 'glow', True),
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


def cmd_post(args: argparse.Namespace) -> None:
    """Post clips to multiple social media platforms."""
    platforms = args.platforms.split(',') if args.platforms else get_all_platforms()
    platforms = [p.strip() for p in platforms]

    uploader = MultiPlatformUploader(platforms)

    uploader.upload_clips_for_video(
        video_id=args.video_id,
        platforms=platforms,
        clips_output_root=OUTPUT_ROOT,
        start_index=args.start_index,
        max_clips=args.max_clips,
        parallel_platforms=not args.sequential,
        privacy_status=getattr(args, 'privacy', 'public'),
    )


def cmd_platforms(args: argparse.Namespace) -> None:
    """List all supported social media platforms."""
    print_platform_info()


def cmd_thumbnails(args: argparse.Namespace) -> None:
    """Generate thumbnails for all clips."""
    generator = ThumbnailGenerator(
        add_logo=args.logo is not None,
        logo_path=args.logo
    )

    generator.generate_thumbnails_for_manifest(
        video_id=args.video_id,
        clips_output_root=OUTPUT_ROOT,
        timestamp_offset=args.timestamp
    )


def cmd_cloud_upload(args: argparse.Namespace) -> None:
    """Upload clips to cloud storage (S3 or Cloudinary)."""
    manager = CloudStorageManager(provider=args.provider)

    urls = manager.upload_clips_for_video(
        video_id=args.video_id,
        clips_output_root=OUTPUT_ROOT,
        start_index=args.start_index,
        max_clips=args.max_clips
    )

    print(f"\n[CloudUpload] Uploaded {len(urls)} clips")
    for clip_idx, url_dict in urls.items():
        print(f"  Clip #{clip_idx}: {url_dict['video']}")


def cmd_schedule(args: argparse.Namespace) -> None:
    """Schedule clips for automated posting."""
    scheduler = PostScheduler()

    # Parse start time
    if args.start_time:
        start_time = datetime.fromisoformat(args.start_time)
    else:
        # Default to 1 hour from now
        start_time = datetime.now() + timedelta(hours=1)

    # Parse platforms
    platforms = args.platforms.split(',') if args.platforms else get_all_platforms()
    platforms = [p.strip() for p in platforms]

    post_ids = scheduler.schedule_batch(
        video_id=args.video_id,
        start_time=start_time,
        interval_hours=args.interval,
        platforms=platforms,
        clips_output_root=OUTPUT_ROOT
    )

    print(f"\n[Schedule] Created {len(post_ids)} scheduled posts")
    print(f"[Schedule] Starting at: {start_time}")
    print(f"[Schedule] Interval: {args.interval} hours")
    print(f"[Schedule] Platforms: {', '.join(platforms)}")


def cmd_schedule_list(args: argparse.Namespace) -> None:
    """List upcoming scheduled posts."""
    scheduler = PostScheduler()
    posts = scheduler.list_upcoming(limit=args.limit)

    if not posts:
        print("[Schedule] No upcoming posts")
        return

    print(f"\n[Schedule] Upcoming posts ({len(posts)}):\n")
    for post in posts:
        print(f"  #{post.id}: Clip {post.clip_index} → {post.platforms}")
        print(f"    Scheduled: {post.scheduled_time}")
        print(f"    Title: {post.title}")
        print()


def cmd_schedule_run(args: argparse.Namespace) -> None:
    """Process pending scheduled posts (run this with cron)."""
    scheduler = PostScheduler()
    stats = process_pending_posts(
        scheduler=scheduler,
        clips_output_root=OUTPUT_ROOT,
        dry_run=args.dry_run
    )

    print(f"\n[Schedule] Posted: {stats['posted']}, Failed: {stats['failed']}")


def cmd_schedule_stats(args: argparse.Namespace) -> None:
    """Show scheduling statistics."""
    scheduler = PostScheduler()
    stats = scheduler.get_stats()

    print("\n[Schedule] Statistics:")
    for status, count in stats.items():
        print(f"  {status}: {count}")
    print()


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
        default=68,
        help="Font size in pixels (default: 68 - optimized for impact and readability).",
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
        default=7,
        help="Outline thickness in pixels (default: 7 - thicker for better pop and contrast).",
    )
    p_run.add_argument(
        "--shadow-depth",
        type=int,
        default=3,
        help="Shadow depth in pixels (default: 3 - deeper for 3D effect).",
    )
    p_run.add_argument(
        "--no-glow",
        action="store_false",
        dest="glow",
        help="Disable glow effect on text (enabled by default for modern aesthetic).",
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
        default=68,
        help="Font size in pixels (default: 68 - optimized for impact and readability).",
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
        default=7,
        help="Outline thickness in pixels (default: 7 - thicker for better pop and contrast).",
    )
    p_clip.add_argument(
        "--shadow-depth",
        type=int,
        default=3,
        help="Shadow depth in pixels (default: 3 - deeper for 3D effect).",
    )
    p_clip.add_argument(
        "--no-glow",
        action="store_false",
        dest="glow",
        help="Disable glow effect on text (enabled by default for modern aesthetic).",
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

    # post - Multi-platform posting
    p_post = subparsers.add_parser(
        "post",
        help="Post clips to multiple social media platforms (YouTube, Instagram, TikTok, etc.)"
    )
    p_post.add_argument("video_id", help="Video ID folder under clips_output/<video_id>/")
    p_post.add_argument(
        "--platforms",
        type=str,
        default=None,
        help="Comma-separated list of platforms: youtube,instagram,tiktok,twitter,linkedin,facebook (default: all)",
    )
    p_post.add_argument(
        "--privacy",
        type=str,
        default="public",
        help="Privacy setting for platforms that support it (default: public).",
    )
    p_post.add_argument(
        "--start-index",
        type=int,
        default=1,
        help="Start from this clip_index (1-based).",
    )
    p_post.add_argument(
        "--max-clips",
        type=int,
        default=None,
        help="Limit number of clips to post.",
    )
    p_post.add_argument(
        "--sequential",
        action="store_true",
        help="Upload to platforms sequentially instead of in parallel.",
    )
    p_post.set_defaults(func=cmd_post)

    # platforms - List supported platforms
    p_platforms = subparsers.add_parser(
        "platforms",
        help="List all supported social media platforms and their status."
    )
    p_platforms.set_defaults(func=cmd_platforms)

    # thumbnails - Generate thumbnails
    p_thumbnails = subparsers.add_parser(
        "thumbnails",
        help="Generate thumbnails for all clips in a video."
    )
    p_thumbnails.add_argument("video_id", help="Video ID folder under clips_output/<video_id>/")
    p_thumbnails.add_argument(
        "--logo",
        type=str,
        default=None,
        help="Path to logo image to add as watermark."
    )
    p_thumbnails.add_argument(
        "--timestamp",
        type=float,
        default=3.0,
        help="Seconds into clip to extract frame (default: 3.0)."
    )
    p_thumbnails.set_defaults(func=cmd_thumbnails)

    # cloud-upload - Upload to cloud storage
    p_cloud = subparsers.add_parser(
        "cloud-upload",
        help="Upload clips to cloud storage (S3 or Cloudinary)."
    )
    p_cloud.add_argument("video_id", help="Video ID folder")
    p_cloud.add_argument(
        "--provider",
        choices=["s3", "cloudinary"],
        default="s3",
        help="Cloud storage provider (default: s3)."
    )
    p_cloud.add_argument(
        "--start-index",
        type=int,
        default=1,
        help="Start from this clip index."
    )
    p_cloud.add_argument(
        "--max-clips",
        type=int,
        default=None,
        help="Maximum clips to upload."
    )
    p_cloud.set_defaults(func=cmd_cloud_upload)

    # schedule - Schedule automated posting
    p_schedule = subparsers.add_parser(
        "schedule",
        help="Schedule clips for automated posting at optimal times."
    )
    p_schedule.add_argument("video_id", help="Video ID folder")
    p_schedule.add_argument(
        "--start-time",
        type=str,
        default=None,
        help="Start time (ISO format: 2024-01-01T12:00:00). Default: 1 hour from now."
    )
    p_schedule.add_argument(
        "--interval",
        type=int,
        default=12,
        help="Hours between posts (default: 12)."
    )
    p_schedule.add_argument(
        "--platforms",
        type=str,
        default=None,
        help="Comma-separated platforms (default: all)."
    )
    p_schedule.set_defaults(func=cmd_schedule)

    # schedule-list - List scheduled posts
    p_schedule_list = subparsers.add_parser(
        "schedule-list",
        help="List upcoming scheduled posts."
    )
    p_schedule_list.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum posts to show (default: 20)."
    )
    p_schedule_list.set_defaults(func=cmd_schedule_list)

    # schedule-run - Process pending posts
    p_schedule_run = subparsers.add_parser(
        "schedule-run",
        help="Process pending scheduled posts (run with cron)."
    )
    p_schedule_run.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be posted without actually posting."
    )
    p_schedule_run.set_defaults(func=cmd_schedule_run)

    # schedule-stats - Show statistics
    p_schedule_stats = subparsers.add_parser(
        "schedule-stats",
        help="Show scheduling statistics."
    )
    p_schedule_stats.set_defaults(func=cmd_schedule_stats)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
