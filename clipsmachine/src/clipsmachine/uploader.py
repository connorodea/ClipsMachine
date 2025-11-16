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
