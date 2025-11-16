#!/usr/bin/env bash
set -e

PROJECT_ROOT="clipsmachine"

echo "[*] Creating project structure in ./${PROJECT_ROOT}"

mkdir -p "${PROJECT_ROOT}/src/clipsmachine"
cd "${PROJECT_ROOT}"

############################
# pyproject.toml
############################
cat <<'EOF' > pyproject.toml
[project]
name = "clipsmachine"
version = "0.1.0"
description = "Automated YouTube clips generator + uploader"
readme = "README.md"
requires-python = ">=3.10"
authors = [
  { name = "Connor", email = "you@example.com" }
]

dependencies = [
  "yt-dlp",
  "youtube-transcript-api",
  "tqdm",
  "google-api-python-client",
  "google-auth-oauthlib",
  "google-auth-httplib2",
  "openai>=1.0.0",
]

[project.scripts]
clipsmachine = "clipsmachine.cli:main"

[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"
EOF

############################
# README.md
############################
cat <<'EOF' > README.md
# clipsmachine

Automated YouTube clips generator + uploader.

## Requirements

- Python 3.10+
- ffmpeg installed and on PATH
- Google Cloud project with YouTube Data API v3 enabled
- OAuth client secrets JSON saved as `client_secret.json` in project root
- OPENAI_API_KEY environment variable set

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

export OPENAI_API_KEY="sk-..."  # set your key
# place client_secret.json in this directory

clipsmachine run "https://www.youtube.com/watch?v=VIDEO_ID" --privacy public
```
EOF

############################
# src/clipsmachine/__init__.py
############################
cat <<'EOF' > src/clipsmachine/__init__.py
__all__ = [
    "config",
    "pipeline",
    "metadata",
    "uploader",
    "cli",
]
EOF

############################
# src/clipsmachine/config.py
############################
cat <<'EOF' > src/clipsmachine/config.py
import os

# Root for all generated assets
OUTPUT_ROOT = os.getenv("CLIPSMACHINE_OUTPUT_ROOT", "clips_output")

# Clip length settings (in seconds)
MIN_CLIP_SEC = int(os.getenv("CLIPSMACHINE_MIN_CLIP_SEC", "40"))
TARGET_CLIP_SEC = int(os.getenv("CLIPSMACHINE_TARGET_CLIP_SEC", "90"))
MAX_CLIP_SEC = int(os.getenv("CLIPSMACHINE_MAX_CLIP_SEC", "180"))
MAX_CLIPS_PER_VIDEO = int(os.getenv("CLIPSMACHINE_MAX_CLIPS_PER_VIDEO", "20"))

# YouTube upload defaults
DEFAULT_PRIVACY = os.getenv("CLIPSMACHINE_DEFAULT_PRIVACY", "unlisted")  # public/unlisted/private
CATEGORY_ID = os.getenv("CLIPSMACHINE_CATEGORY_ID", "27")  # 27 = Education, 24 = Entertainment

# OAuth files
CLIENT_SECRET_FILE = os.getenv("CLIPSMACHINE_CLIENT_SECRET_FILE", "client_secret.json")
TOKEN_FILE = os.getenv("CLIPSMACHINE_TOKEN_FILE", "token.json")

# LLM
OPENAI_MODEL = os.getenv("CLIPSMACHINE_OPENAI_MODEL", "gpt-4o-mini")
MAX_LLM_RETRIES = int(os.getenv("CLIPSMACHINE_MAX_LLM_RETRIES", "3"))
LLM_SLEEP_BETWEEN_CALLS = float(os.getenv("CLIPSMACHINE_LLM_SLEEP_BETWEEN", "1"))
EOF

############################
# src/clipsmachine/pipeline.py
############################
cat <<'EOF' > src/clipsmachine/pipeline.py
import os
import re
import json
import subprocess
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

from tqdm import tqdm
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
import yt_dlp

from .config import (
    OUTPUT_ROOT,
    MIN_CLIP_SEC,
    TARGET_CLIP_SEC,
    MAX_CLIP_SEC,
    MAX_CLIPS_PER_VIDEO,
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
        return YouTubeTranscriptApi.get_transcript(
            video_id,
            languages=["en", "en-US", "en-GB"],
        )
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
    current_end = None

    for entry in transcript:
        start = entry["start"]
        duration = entry["duration"]
        text = entry["text"].replace("\n", " ").strip()

        if current_start is None:
            current_start = start
            current_text = []

        current_text.append(text)
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
                }
            )
            current_start = None
            current_text = []
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
) -> None:
    duration = max(end - start, 1.0)
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start),
        "-i",
        input_video,
        "-t",
        str(duration),
        "-c",
        "copy",
        output_path,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def process_video(url: str) -> List[ClipInfo]:
    video_id = extract_video_id(url)
    video_dir = os.path.join(OUTPUT_ROOT, video_id)
    raw_dir = os.path.join(video_dir, "raw")
    clips_dir = os.path.join(video_dir, "clips")

    ensure_dir(raw_dir)
    ensure_dir(clips_dir)

    print(f"[pipeline] Downloading video: {url}")
    video_path = download_video(url, raw_dir)

    print("[pipeline] Fetching transcript…")
    transcript = get_transcript(video_id)

    print("[pipeline] Building clip segments…")
    segments = build_clips_from_transcript(transcript)
    if not segments:
        raise RuntimeError("No segments generated – adjust clip settings.")

    print(f"[pipeline] Generated {len(segments)} potential clips.")
    clips: List[ClipInfo] = []

    print("[pipeline] Cutting clips with ffmpeg…")
    for idx, seg in enumerate(tqdm(segments, desc="Clipping", unit="clip"), start=1):
        start = seg["start"]
        end = seg["end"]
        text = seg["text"]
        duration = end - start

        file_name = f"{video_id}_clip_{idx:02d}.mp4"
        output_path = os.path.join(clips_dir, file_name)

        cut_clip_ffmpeg(video_path, start, end, output_path)

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

    manifest_path = os.path.join(video_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump([asdict(c) for c in clips], f, indent=2, ensure_ascii=False)

    print(f"[pipeline] Clips:   {clips_dir}")
    print(f"[pipeline] Manifest:{manifest_path}")
    return clips
EOF

############################
# src/clipsmachine/metadata.py
############################
cat <<'EOF' > src/clipsmachine/metadata.py
import os
import json
import time
from typing import List, Dict, Any

from openai import OpenAI

from .config import (
    OUTPUT_ROOT,
    OPENAI_MODEL,
    MAX_LLM_RETRIES,
    LLM_SLEEP_BETWEEN_CALLS,
)


def _manifest_path(video_id: str) -> str:
    return os.path.join(OUTPUT_ROOT, video_id, "manifest.json")


def load_manifest(video_id: str) -> List[Dict[str, Any]]:
    path = _manifest_path(video_id)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Manifest not found at {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_manifest(video_id: str, manifest: List[Dict[str, Any]]) -> None:
    path = _manifest_path(video_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    print(f"[metadata] Updated manifest saved to {path}")


def call_llm(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable not set.")

    client = OpenAI(api_key=api_key)

    last_exc: Exception | None = None
    for attempt in range(1, MAX_LLM_RETRIES + 1):
        try:
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert YouTube title and description writer "
                            "for a clips channel. You ONLY reply with strict JSON."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )
            return resp.choices[0].message.content
        except Exception as e:
            last_exc = e
            print(f"[metadata] LLM call failed (attempt {attempt}): {e}")
            time.sleep(2 * attempt)

    assert last_exc is not None
    raise last_exc


def enhance_single_clip(
    clip: Dict[str, Any],
    channel_positioning: str,
    base_tags: str,
) -> Dict[str, Any]:
    text_preview = clip.get("text_preview", "") or clip.get("description", "")[:300]
    original_title = clip.get("title", "")
    original_description = clip.get("description", "")

    prompt = f"""
You are optimizing metadata for a YouTube clips channel.

CHANNEL POSITIONING:
{channel_positioning}

BASE TAGS (context only, do NOT output them as a list):
{base_tags}

CLIP CONTEXT:
    •    Original title: {original_title}
    •    Original description (truncated): {original_description[:400]}
    •    Transcript excerpt (up to ~300 chars):
{text_preview}

TASK:
    1.    Create a punchy, curiosity-driven YouTube title (max 90 characters).
    •    Specific and honest.
    •    No emojis, no quotes.
    2.    Write a short description that:
    •    Hooks in the first line.
    •    Summarizes what the viewer will learn or feel.
    •    States that this is a clip from a longer conversation.
    •    Includes a light call to action (subscribe / watch more).
    •    Stays under 900 characters.

OUTPUT:
Return STRICT JSON:
{{
  "title": "<new_title>",
  "description": "<new_description>"
}}
No extra commentary.
"""

    raw = call_llm(prompt)
    cleaned = raw.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        print("[metadata] WARNING: JSON parse failed; using fallback.")
        data = {
            "title": original_title,
            "description": raw.strip(),
        }

    new_title = data.get("title", original_title).strip()
    new_description = data.get("description", original_description).strip()

    clip["title"] = new_title
    clip["description"] = new_description
    return clip


def enhance_manifest(
    video_id: str,
    channel_positioning: str,
    base_tags: str,
    start_index: int = 1,
    max_clips: int | None = None,
) -> None:
    manifest = load_manifest(video_id)
    if not manifest:
        raise RuntimeError("Manifest is empty.")

    manifest.sort(key=lambda c: int(c.get("clip_index", 0)))

    to_update = [
        c for c in manifest if int(c.get("clip_index", 0)) >= start_index
    ]
    if max_clips is not None:
        to_update = to_update[:max_clips]

    print(f"[metadata] Enhancing {len(to_update)} clips for video {video_id}.")

    for clip in to_update:
        idx = int(clip.get("clip_index", 0))
        print(f"[metadata] Enhancing clip #{idx}…")
        enhanced = enhance_single_clip(clip, channel_positioning, base_tags)

        for i, entry in enumerate(manifest):
            if int(entry.get("clip_index", 0)) == idx:
                manifest[i] = enhanced
                break

        time.sleep(LLM_SLEEP_BETWEEN_CALLS)

    save_manifest(video_id, manifest)
EOF

############################
# src/clipsmachine/uploader.py
############################
cat <<'EOF' > src/clipsmachine/uploader.py
import os
import time
from typing import List, Dict, Any

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from .config import (
    OUTPUT_ROOT,
    DEFAULT_PRIVACY,
    CATEGORY_ID,
    CLIENT_SECRET_FILE,
    TOKEN_FILE,
)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_youtube_client():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRET_FILE):
                raise FileNotFoundError(
                    f"{CLIENT_SECRET_FILE} not found. "
                    "Download OAuth client secrets JSON from Google Cloud and save it here."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def _manifest_path(video_id: str) -> str:
    return os.path.join(OUTPUT_ROOT, video_id, "manifest.json")


def _load_manifest(video_id: str) -> List[Dict[str, Any]]:
    path = _manifest_path(video_id)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Manifest not found at {path}")
    import json

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def upload_single_clip(
    youtube,
    video_path: str,
    title: str,
    description: str,
    privacy_status: str = DEFAULT_PRIVACY,
    tags: List[str] | None = None,
) -> str:
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Clip file not found: {video_path}")

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "categoryId": CATEGORY_ID,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False,
        },
    }
    if tags:
        body["snippet"]["tags"] = tags[:20]

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"  Upload progress: {int(status.progress() * 100)}%")

    video_id = response.get("id")
    print(f"  Uploaded: https://www.youtube.com/watch?v={video_id}")
    return video_id


def upload_clips_for_video(
    video_id: str,
    privacy_status: str = DEFAULT_PRIVACY,
    start_index: int = 1,
    max_clips: int | None = None,
    sleep_between: int = 5,
) -> None:
    clips_root = os.path.join(OUTPUT_ROOT, video_id, "clips")
    if not os.path.isdir(clips_root):
        raise FileNotFoundError(f"Clips directory not found: {clips_root}")

    manifest = _load_manifest(video_id)
    if not manifest:
        raise RuntimeError("Manifest is empty.")

    manifest.sort(key=lambda c: int(c.get("clip_index", 0)))
    if start_index > 1:
        manifest = [
            c for c in manifest if int(c.get("clip_index", 0)) >= start_index
        ]
    if max_clips is not None:
        manifest = manifest[:max_clips]

    print(f"[uploader] Found {len(manifest)} clips to upload for {video_id}.")

    youtube = get_youtube_client()

    for clip in manifest:
        idx = int(clip.get("clip_index", 0))
        title = clip.get("title", f"Clip #{idx}")
        description = clip.get("description", "")
        file_name = clip.get("file_name")
        file_path = os.path.join(clips_root, file_name)

        tags = [
            "clips",
            "podcast",
            "short clips",
            "highlights",
        ]

        print(f"\n[uploader] Uploading clip #{idx}: {title}")
        try:
            upload_single_clip(
                youtube=youtube,
                video_path=file_path,
                title=title,
                description=description,
                privacy_status=privacy_status,
                tags=tags,
            )
        except HttpError as e:
            print(f"  ERROR uploading clip #{idx}: {e}")
        except Exception as e:
            print(f"  Unexpected error on clip #{idx}: {e}")

        if sleep_between > 0:
            time.sleep(sleep_between)
EOF

############################
# src/clipsmachine/cli.py
############################
cat <<'EOF' > src/clipsmachine/cli.py
import argparse
import os

from .pipeline import process_video, extract_video_id
from .metadata import enhance_manifest
from .uploader import upload_clips_for_video
from .config import OUTPUT_ROOT


def cmd_run(args: argparse.Namespace) -> None:
    url = args.youtube_url
    video_id = extract_video_id(url)

    print(f"[run] Source: {url}")
    print(f"[run] Video ID: {video_id}")
    os.makedirs(OUTPUT_ROOT, exist_ok=True)

    print("\n[1/3] Generating clips…")
    clips = process_video(url)
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
    process_video(url)


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
        "--sleep-between-uploads",
        type=int,
        default=5,
        help="Seconds between uploads (default: 5).",
    )
    p_run.set_defaults(func=cmd_run)

    # clip
    p_clip = subparsers.add_parser(
        "clip", help="Only download and generate clips + manifest."
    )
    p_clip.add_argument("youtube_url", help="YouTube URL of long-form video.")
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
EOF

############################
# Create virtualenv + install
############################
echo "[*] Creating virtualenv .venv and installing package (editable)…"
python3 -m venv .venv

# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -e .

echo
echo "[*] Setup complete."
echo "Next steps:"
echo "  cd ${PROJECT_ROOT}"
echo "  source .venv/bin/activate"
echo '  export OPENAI_API_KEY="sk-…"'
echo "  # Place client_secret.json in ${PROJECT_ROOT}/"
echo '  clipsmachine run "https://www.youtube.com/watch?v=VIDEO_ID" --privacy public'
