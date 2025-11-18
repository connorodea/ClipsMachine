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
from .virality_score import calculate_virality_score, get_virality_label


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
    # OpenAI SDK automatically uses OPENAI_API_KEY environment variable
    # Verify it's set before attempting to create client
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY environment variable not set.")

    client = OpenAI()  # Uses environment variable automatically

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
    enable_virality_score: bool = True,
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

    # Calculate virality score
    if enable_virality_score:
        full_text = clip.get("text_preview", "")
        duration = clip.get("duration", 0)
        clip_index = clip.get("clip_index", 0)

        print(f"[metadata] Calculating virality score for clip #{clip_index}...")
        virality_data = calculate_virality_score(full_text, duration, clip_index)

        clip["virality_score"] = virality_data["virality_score"]
        clip["virality_label"] = get_virality_label(virality_data["virality_score"])
        clip["virality_breakdown"] = {
            "hook_strength": virality_data["hook_strength"],
            "emotional_impact": virality_data["emotional_impact"],
            "shareability": virality_data["shareability"],
            "insights": virality_data["insights"],
        }

        print(
            f"[metadata] Virality score: {virality_data['virality_score']}/100 "
            f"({get_virality_label(virality_data['virality_score'])})"
        )

    return clip


def enhance_manifest(
    video_id: str,
    channel_positioning: str,
    base_tags: str,
    start_index: int = 1,
    max_clips: int | None = None,
    enable_virality_score: bool = True,
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
        enhanced = enhance_single_clip(clip, channel_positioning, base_tags, enable_virality_score)

        for i, entry in enumerate(manifest):
            if int(entry.get("clip_index", 0)) == idx:
                manifest[i] = enhanced
                break

        time.sleep(LLM_SLEEP_BETWEEN_CALLS)

    save_manifest(video_id, manifest)
