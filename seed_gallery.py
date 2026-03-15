#!/usr/bin/env python3
"""
Seed the gallery — uploads existing CLI-generated videos to Supabase
Storage and creates corresponding rows in the videos table.

Usage:
    python seed_gallery.py
"""

import json
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from supabase import create_client
import os

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

OUTPUT_DIR = Path(__file__).parent / "output"
BUCKET = "generated_videos"


def main():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    output_dirs = sorted(OUTPUT_DIR.iterdir())
    seeded = 0
    skipped = 0

    for out_dir in output_dirs:
        if not out_dir.is_dir():
            continue

        plan_path = out_dir / "plan.json"
        final_path = out_dir / "final.mp4"

        if not plan_path.exists():
            print(f"  SKIP {out_dir.name}: no plan.json")
            skipped += 1
            continue

        if not final_path.exists():
            print(f"  SKIP {out_dir.name}: no final.mp4")
            skipped += 1
            continue

        # Load the plan
        plan = json.loads(plan_path.read_text())
        title = plan.get("title", plan.get("topic", out_dir.name))
        topic = plan.get("topic", out_dir.name)
        aha_moment = plan.get("aha_moment")

        # Build narration text from scenes
        narration = "\n\n".join(
            scene.get("narration", "") for scene in plan.get("scenes", [])
        )

        # Determine duration profile from scene count
        num_scenes = len(plan.get("scenes", []))
        if num_scenes <= 4:
            duration_profile = "short"
        elif num_scenes <= 7:
            duration_profile = "medium"
        else:
            duration_profile = "long"

        # Check if already seeded (by topic match)
        existing = (
            supabase.table("videos")
            .select("id")
            .eq("topic", topic)
            .execute()
        )
        if existing.data:
            print(f"  SKIP {out_dir.name}: already in database")
            skipped += 1
            continue

        # Upload video to Supabase Storage
        storage_path = f"seeded/{out_dir.name}/final.mp4"
        print(f"  Uploading {out_dir.name} ({final_path.stat().st_size / 1024 / 1024:.1f} MB)...")

        with open(final_path, "rb") as f:
            supabase.storage.from_(BUCKET).upload(
                storage_path,
                f,
                file_options={"content-type": "video/mp4"},
            )

        video_url = supabase.storage.from_(BUCKET).get_public_url(storage_path)

        # Generate thumbnail
        thumbnail_path = out_dir / "thumbnail.jpg"
        try:
            # Get duration to pick a good frame
            dur_result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(final_path)],
                capture_output=True, text=True,
            )
            vid_dur = float(dur_result.stdout.strip())
            timestamp = min(5.0, vid_dur * 0.3)

            subprocess.run(
                ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                 "-ss", str(timestamp), "-i", str(final_path),
                 "-vframes", "1", "-q:v", "2", str(thumbnail_path)],
                capture_output=True, text=True,
            )
        except Exception:
            thumbnail_path = None

        # Upload thumbnail if generated
        thumbnail_url = None
        if thumbnail_path and thumbnail_path.exists():
            thumb_storage_path = f"seeded/{out_dir.name}/thumbnail.jpg"
            with open(thumbnail_path, "rb") as f:
                supabase.storage.from_(BUCKET).upload(
                    thumb_storage_path,
                    f,
                    file_options={"content-type": "image/jpeg"},
                )
            thumbnail_url = supabase.storage.from_(BUCKET).get_public_url(thumb_storage_path)

        # Get video duration via ffprobe
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(final_path),
                ],
                capture_output=True,
                text=True,
            )
            video_duration = float(result.stdout.strip())
        except Exception:
            video_duration = None

        # Insert into videos table (no user_id — these are system-seeded)
        video_row = {
            "topic": topic,
            "title": title,
            "duration_profile": duration_profile,
            "aha_moment": aha_moment,
            "plan": plan,
            "narration_text": narration,
            "video_url": video_url,
            "thumbnail_url": thumbnail_url,
            "video_duration_seconds": video_duration,
            "view_count": 0,
        }

        supabase.table("videos").insert(video_row).execute()
        seeded += 1
        print(f"  SEEDED: {title}")

    print(f"\nDone! Seeded {seeded} videos, skipped {skipped}.")


if __name__ == "__main__":
    main()
