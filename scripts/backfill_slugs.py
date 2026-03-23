#!/usr/bin/env python3
"""
One-off script to generate slugs for all existing videos that don't have slugs.

Usage:
    python scripts/backfill_slugs.py
"""

import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT))

from supabase import create_client


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug[:80]


def main():
    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

    response = sb.table("videos").select("id, title, slug").is_("slug", "null").execute()
    videos = response.data

    if not videos:
        print("All videos already have slugs!")
        return

    # Track used slugs to avoid collisions
    existing = sb.table("videos").select("slug").not_.is_("slug", "null").execute()
    used_slugs = {r["slug"] for r in existing.data if r["slug"]}

    print(f"Found {len(videos)} videos without slugs\n")

    for i, video in enumerate(videos):
        slug = slugify(video["title"])

        # Handle collisions
        if slug in used_slugs:
            counter = 2
            while f"{slug}-{counter}" in used_slugs:
                counter += 1
            slug = f"{slug}-{counter}"

        used_slugs.add(slug)

        print(f"[{i+1}/{len(videos)}] {video['title'][:50]}")
        print(f"  Slug: {slug}")

        sb.table("videos").update({"slug": slug}).eq("id", video["id"]).execute()
        print(f"  Saved!")

    print(f"\nDone! Slugified {len(videos)} videos.")


if __name__ == "__main__":
    main()
