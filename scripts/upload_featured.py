#!/usr/bin/env python3
"""
Upload locally-generated videos to Supabase as featured Curiso Picks.

Uploads the 16:9 final.mp4 (no CTA) and thumbnail to Supabase Storage,
creates a videos row with is_featured=true.

Usage:
    .venv/bin/python scripts/upload_featured.py
"""

import json
import re
import time
import uuid
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from supabase import create_client
import os
import anthropic


SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
BUCKET = "generated_videos"
OUTPUT_ROOT = Path(__file__).resolve().parent.parent / "output"


def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def url_slugify(text: str) -> str:
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:80]


def generate_tags(topic: str, title: str) -> list[str]:
    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": f"Generate 3-5 short topic tags for this educational video.\n\nTitle: {title}\nTopic: {topic}\n\nReturn ONLY a JSON array of lowercase strings, e.g. [\"physics\", \"quantum mechanics\", \"particles\"]. Tags should be broad enough to group related videos but specific enough to be useful for filtering."
            }],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(raw)
    except Exception as e:
        print(f"  Warning: tag generation failed: {e}")
        return []


def upload_file(supabase, storage_path: str, local_path: Path, content_type: str, max_retries: int = 3) -> str:
    for attempt in range(max_retries):
        try:
            with open(local_path, "rb") as f:
                supabase.storage.from_(BUCKET).upload(
                    storage_path, f,
                    file_options={"content-type": content_type},
                )
            return supabase.storage.from_(BUCKET).get_public_url(storage_path)
        except Exception as exc:
            if "already exists" in str(exc).lower() or "Duplicate" in str(exc):
                # Already uploaded, just get the URL
                return supabase.storage.from_(BUCKET).get_public_url(storage_path)
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"  Upload failed (attempt {attempt + 1}): {exc}")
                print(f"  Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


def get_duration(path: Path) -> float:
    import subprocess
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True,
    )
    return float(result.stdout.strip())


def get_narration(plan: dict) -> str:
    return "\n\n".join(scene["narration"] for scene in plan.get("scenes", []))


# Videos to upload — directory name, topic, title (from plan.json)
VIDEOS = [
    "how_does_chatgpt_actually_work_under_the_hood",
    "what_is_a_neural_network_and_how_does_it_learn_from_data",
    "why_quantum_computing_is_faster_than_regular_computers",
    "why_does_dividing_by_zero_break_mathematics",
    "why_cant_anything_travel_faster_than_the_speed_of_light",
    "how_does_your_brain_store_and_retrieve_memories",
    "monty_hall_problem",
    "how_does_compound_interest_turn_100_dollars_into_1_million_d",
    "why_pi_is_so_important_and_where_it_shows_up_in_nature",
    "what_makes_prime_numbers_the_building_blocks_of_all_math",
    "what_actually_happens_inside_a_black_hole",
]


def main():
    supabase = get_supabase()

    for dirname in VIDEOS:
        video_dir = OUTPUT_ROOT / dirname
        final_mp4 = video_dir / "final.mp4"
        plan_json = video_dir / "plan.json"
        thumb_jpg = video_dir / "thumbnail.jpg"

        if not final_mp4.exists():
            print(f"SKIP: {dirname} — no final.mp4")
            continue
        if not plan_json.exists():
            print(f"SKIP: {dirname} — no plan.json")
            continue

        plan = json.loads(plan_json.read_text())
        topic = plan.get("topic", dirname.replace("_", " "))
        title = plan.get("title", topic)
        slug = url_slugify(title)

        # Check if already uploaded
        existing = supabase.table("videos").select("id").eq("slug", slug).execute()
        if existing.data:
            print(f"ALREADY EXISTS: {title} (slug: {slug}) — updating is_featured")
            supabase.table("videos").update({"is_featured": True}).eq("slug", slug).execute()
            continue

        print(f"\nUploading: {title}")
        upload_id = uuid.uuid4().hex[:12]

        # Upload video
        print("  Uploading video...")
        video_url = upload_file(
            supabase,
            f"videos/featured_{upload_id}/final.mp4",
            final_mp4,
            "video/mp4",
        )

        # Generate thumbnail from video if not already present
        if not thumb_jpg.exists():
            print("  Generating thumbnail...")
            import subprocess
            dur = get_duration(final_mp4)
            t = dur * 0.4  # Grab frame at 40% in
            subprocess.run(
                ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                 "-ss", str(t), "-i", str(final_mp4),
                 "-vframes", "1", "-q:v", "2", str(thumb_jpg)],
                capture_output=True, text=True,
            )

        # Upload thumbnail
        print("  Uploading thumbnail...")
        thumbnail_url = upload_file(
            supabase,
            f"videos/featured_{upload_id}/thumbnail.jpg",
            thumb_jpg,
            "image/jpeg",
        )

        # Get duration
        duration_secs = get_duration(final_mp4)

        # Get narration
        narration = get_narration(plan)

        # Generate tags
        print("  Generating tags...")
        tags = generate_tags(topic, title)

        # Create video row
        video_row = {
            "topic": topic,
            "title": title,
            "duration_profile": "short",
            "aha_moment": plan.get("aha_moment"),
            "narration_text": narration,
            "video_url": video_url,
            "thumbnail_url": thumbnail_url,
            "video_duration_seconds": duration_secs,
            "view_count": 0,
            "is_featured": True,
            "slug": slug,
        }
        if tags:
            video_row["tags"] = tags

        print("  Creating database row...")
        try:
            result = supabase.table("videos").insert(video_row).execute()
            video_id = result.data[0]["id"]
            print(f"  Done! ID: {video_id}, slug: {slug}")
        except Exception as e:
            # Slug collision — add random suffix
            video_row["slug"] = f"{slug[:70]}-{uuid.uuid4().hex[:8]}"
            result = supabase.table("videos").insert(video_row).execute()
            video_id = result.data[0]["id"]
            print(f"  Done! ID: {video_id}, slug: {video_row['slug']}")

    print("\nAll done! Featured videos are now in the Curiso Picks tab.")


if __name__ == "__main__":
    main()
