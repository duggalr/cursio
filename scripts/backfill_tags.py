#!/usr/bin/env python3
"""
One-off script to generate tags for all existing videos that don't have tags.

Usage:
    python scripts/backfill_tags.py
    python scripts/backfill_tags.py --dry-run    # Preview without writing
"""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT))

import anthropic
from supabase import create_client


def generate_tags(topic: str, title: str) -> list[str]:
    """Generate 3-5 topic tags for a video using Claude."""
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        messages=[{
            "role": "user",
            "content": (
                f"Generate 3-5 short topic tags for this educational video.\n\n"
                f"Title: {title}\nTopic: {topic}\n\n"
                f"Return ONLY a JSON array of lowercase strings, e.g. "
                f'["physics", "quantum mechanics", "particles"]. '
                f"Tags should be broad enough to group related videos but "
                f"specific enough to be useful for filtering."
            ),
        }],
    )
    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
    return json.loads(raw)


def main():
    parser = argparse.ArgumentParser(description="Backfill tags for existing videos")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    # Fetch all videos without tags
    response = sb.table("videos").select("id, topic, title, tags").is_("tags", "null").execute()
    videos = response.data

    if not videos:
        print("All videos already have tags!")
        return

    print(f"Found {len(videos)} videos without tags\n")

    for i, video in enumerate(videos):
        print(f"[{i+1}/{len(videos)}] {video['title'][:60]}")
        try:
            tags = generate_tags(video["topic"], video["title"])
            print(f"  Tags: {tags}")

            if not args.dry_run:
                sb.table("videos").update({"tags": json.dumps(tags)}).eq("id", video["id"]).execute()
                print(f"  Saved!")
            else:
                print(f"  (dry run — not saved)")
        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\nDone! Tagged {len(videos)} videos.")


if __name__ == "__main__":
    main()
