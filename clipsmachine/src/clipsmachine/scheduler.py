"""
Scheduled posting system for ClipsMachine.
Queue posts and automatically publish at optimal times.
"""

import os
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import time


@dataclass
class ScheduledPost:
    """Scheduled post entry."""
    id: Optional[int]
    video_id: str
    clip_index: int
    platforms: str  # Comma-separated
    scheduled_time: str  # ISO format
    status: str  # 'pending', 'posted', 'failed'
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    result: Optional[str] = None  # JSON of upload results
    created_at: Optional[str] = None
    posted_at: Optional[str] = None


class PostScheduler:
    """Manage scheduled posts with SQLite database."""

    def __init__(self, db_path: str = "clipsmachine_scheduler.db"):
        """
        Initialize post scheduler.

        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Create database tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL,
                clip_index INTEGER NOT NULL,
                platforms TEXT NOT NULL,
                scheduled_time TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                video_url TEXT,
                thumbnail_url TEXT,
                title TEXT,
                description TEXT,
                result TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                posted_at TEXT
            )
        """)

        # Index for efficient queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_scheduled_time
            ON scheduled_posts(scheduled_time, status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_video_clip
            ON scheduled_posts(video_id, clip_index)
        """)

        conn.commit()
        conn.close()

        print(f"[Scheduler] Database initialized: {self.db_path}")

    def schedule_post(
        self,
        video_id: str,
        clip_index: int,
        platforms: List[str],
        scheduled_time: datetime,
        video_url: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> int:
        """
        Schedule a post.

        Args:
            video_id: Video ID
            clip_index: Clip index
            platforms: List of platform names
            scheduled_time: When to post
            video_url: Cloud storage URL of video
            thumbnail_url: Cloud storage URL of thumbnail
            title: Post title
            description: Post description

        Returns:
            Post ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        platforms_str = ','.join(platforms)
        scheduled_time_str = scheduled_time.isoformat()

        cursor.execute("""
            INSERT INTO scheduled_posts
            (video_id, clip_index, platforms, scheduled_time, video_url, thumbnail_url, title, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (video_id, clip_index, platforms_str, scheduled_time_str, video_url, thumbnail_url, title, description))

        post_id = cursor.lastrowid
        conn.commit()
        conn.close()

        print(f"[Scheduler] Scheduled post #{post_id}: clip {clip_index} to {platforms_str} at {scheduled_time_str}")
        return post_id

    def schedule_batch(
        self,
        video_id: str,
        start_time: datetime,
        interval_hours: int = 12,
        platforms: Optional[List[str]] = None,
        clips_output_root: str = "clips_output",
    ) -> List[int]:
        """
        Schedule all clips from a video with staggered timing.

        Args:
            video_id: Video ID
            start_time: When to start posting
            interval_hours: Hours between posts
            platforms: List of platforms (default: all)
            clips_output_root: Root output directory

        Returns:
            List of post IDs
        """
        # Load manifest
        manifest_path = os.path.join(clips_output_root, video_id, "manifest.json")
        if not os.path.exists(manifest_path):
            raise FileNotFoundError(f"Manifest not found: {manifest_path}")

        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        if platforms is None:
            from .platforms import get_all_platforms
            platforms = get_all_platforms()

        manifest.sort(key=lambda c: int(c.get("clip_index", 0)))

        post_ids = []
        current_time = start_time

        for clip in manifest:
            clip_index = int(clip.get("clip_index", 0))
            title = clip.get("title", f"Clip #{clip_index}")
            description = clip.get("description", "")

            post_id = self.schedule_post(
                video_id=video_id,
                clip_index=clip_index,
                platforms=platforms,
                scheduled_time=current_time,
                title=title,
                description=description,
            )

            post_ids.append(post_id)
            current_time += timedelta(hours=interval_hours)

        print(f"[Scheduler] Scheduled {len(post_ids)} posts from {start_time} to {current_time}")
        return post_ids

    def get_pending_posts(self, before: Optional[datetime] = None) -> List[ScheduledPost]:
        """
        Get all pending posts that should be posted.

        Args:
            before: Get posts scheduled before this time (default: now)

        Returns:
            List of ScheduledPost objects
        """
        if before is None:
            before = datetime.now()

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM scheduled_posts
            WHERE status = 'pending'
            AND scheduled_time <= ?
            ORDER BY scheduled_time ASC
        """, (before.isoformat(),))

        rows = cursor.fetchall()
        conn.close()

        posts = []
        for row in rows:
            post = ScheduledPost(
                id=row['id'],
                video_id=row['video_id'],
                clip_index=row['clip_index'],
                platforms=row['platforms'],
                scheduled_time=row['scheduled_time'],
                status=row['status'],
                video_url=row['video_url'],
                thumbnail_url=row['thumbnail_url'],
                title=row['title'],
                description=row['description'],
                result=row['result'],
                created_at=row['created_at'],
                posted_at=row['posted_at'],
            )
            posts.append(post)

        return posts

    def mark_posted(self, post_id: int, result: Any) -> None:
        """
        Mark post as successfully posted.

        Args:
            post_id: Post ID
            result: Upload result object (will be JSON serialized)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        result_json = json.dumps(result) if result else None

        cursor.execute("""
            UPDATE scheduled_posts
            SET status = 'posted',
                result = ?,
                posted_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (result_json, post_id))

        conn.commit()
        conn.close()

        print(f"[Scheduler] Marked post #{post_id} as posted")

    def mark_failed(self, post_id: int, error: str) -> None:
        """
        Mark post as failed.

        Args:
            post_id: Post ID
            error: Error message
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        result_json = json.dumps({"error": error})

        cursor.execute("""
            UPDATE scheduled_posts
            SET status = 'failed',
                result = ?,
                posted_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (result_json, post_id))

        conn.commit()
        conn.close()

        print(f"[Scheduler] Marked post #{post_id} as failed: {error}")

    def get_stats(self) -> Dict[str, int]:
        """Get posting statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                status,
                COUNT(*) as count
            FROM scheduled_posts
            GROUP BY status
        """)

        stats = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()

        return stats

    def list_upcoming(self, limit: int = 10) -> List[ScheduledPost]:
        """List upcoming scheduled posts."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM scheduled_posts
            WHERE status = 'pending'
            ORDER BY scheduled_time ASC
            LIMIT ?
        """, (limit,))

        rows = cursor.fetchall()
        conn.close()

        posts = []
        for row in rows:
            post = ScheduledPost(
                id=row['id'],
                video_id=row['video_id'],
                clip_index=row['clip_index'],
                platforms=row['platforms'],
                scheduled_time=row['scheduled_time'],
                status=row['status'],
                video_url=row['video_url'],
                thumbnail_url=row['thumbnail_url'],
                title=row['title'],
                description=row['description'],
                result=row['result'],
                created_at=row['created_at'],
                posted_at=row['posted_at'],
            )
            posts.append(post)

        return posts

    def cancel_post(self, post_id: int) -> bool:
        """Cancel a scheduled post."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM scheduled_posts
            WHERE id = ? AND status = 'pending'
        """, (post_id,))

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        if deleted:
            print(f"[Scheduler] Cancelled post #{post_id}")
        return deleted


def process_pending_posts(
    scheduler: PostScheduler,
    clips_output_root: str = "clips_output",
    dry_run: bool = False
) -> Dict[str, int]:
    """
    Process all pending posts that are due.

    Args:
        scheduler: PostScheduler instance
        clips_output_root: Root output directory
        dry_run: Don't actually post, just show what would be posted

    Returns:
        Dict with 'posted' and 'failed' counts
    """
    from .multi_uploader import MultiPlatformUploader

    pending = scheduler.get_pending_posts()

    if not pending:
        print("[Scheduler] No pending posts to process")
        return {"posted": 0, "failed": 0}

    print(f"\n[Scheduler] Processing {len(pending)} pending posts...")

    stats = {"posted": 0, "failed": 0}

    for post in pending:
        print(f"\n{'='*60}")
        print(f"[Scheduler] Post #{post.id}: Clip {post.clip_index} → {post.platforms}")
        print(f"[Scheduler] Scheduled for: {post.scheduled_time}")
        print(f"[Scheduler] Title: {post.title}")
        print(f"{'='*60}")

        if dry_run:
            print("[Scheduler] DRY RUN - Would post now")
            continue

        try:
            # Get clip file path
            manifest_path = os.path.join(clips_output_root, post.video_id, "manifest.json")
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            clip = next((c for c in manifest if int(c.get("clip_index", 0)) == post.clip_index), None)
            if not clip:
                raise ValueError(f"Clip {post.clip_index} not found in manifest")

            file_name = clip.get("file_name")
            file_path = os.path.join(clips_output_root, post.video_id, "clips", file_name)

            # Upload to platforms
            platforms = post.platforms.split(',')
            uploader = MultiPlatformUploader(platforms)

            results = uploader.upload_multi(
                platforms=platforms,
                video_path=post.video_url or file_path,  # Use cloud URL if available
                title=post.title or clip.get("title", ""),
                description=post.description or clip.get("description", ""),
                parallel=True
            )

            # Check if any succeeded
            if any(r.success for r in results):
                scheduler.mark_posted(post.id, [asdict(r) for r in results])
                stats["posted"] += 1
                print(f"[Scheduler] ✅ Post #{post.id} completed successfully")
            else:
                error_msg = "; ".join(r.error for r in results if r.error)
                scheduler.mark_failed(post.id, error_msg)
                stats["failed"] += 1
                print(f"[Scheduler] ❌ Post #{post.id} failed: {error_msg}")

        except Exception as e:
            scheduler.mark_failed(post.id, str(e))
            stats["failed"] += 1
            print(f"[Scheduler] ❌ Post #{post.id} error: {e}")

        # Small delay between posts
        time.sleep(2)

    print(f"\n[Scheduler] Completed: {stats['posted']} posted, {stats['failed']} failed")
    return stats
