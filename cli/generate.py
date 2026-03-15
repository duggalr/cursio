#!/usr/bin/env python3
"""
AI Educational Video Generator — CLI entry point.

Generates 3Blue1Brown-style educational videos from a topic prompt.

Usage:
    python cli/generate.py "Explain the derivative"
    python cli/generate.py "Explain the derivative" --duration medium
    python cli/generate.py "How InfiniBand partitioning works" --scenes-only --duration long
    python cli/generate.py --from-plan output/the_derivative/plan.json
    python cli/generate.py "What is recursion" --no-voice --preview
"""

import argparse
import json
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Add project root to path so core/ is importable
sys.path.insert(0, str(PROJECT_ROOT))

from core.planner import plan_scenes
from core.codegen import generate_manim_code
from core.renderer import render_scene, get_scene_names
from core.voice import generate_voice, get_audio_duration
from core.subtitles import generate_subtitles
from core.assembler import combine_scene, concatenate_scenes, burn_subtitles


OUTPUT_ROOT = PROJECT_ROOT / "output"


def slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "_", slug).strip("_")[:60]


def main():
    parser = argparse.ArgumentParser(
        description="Generate 3Blue1Brown-style educational videos from a topic prompt"
    )
    parser.add_argument(
        "topic",
        nargs="?",
        help="The topic to explain (e.g. 'Explain the derivative')",
    )
    parser.add_argument(
        "--scenes-only",
        action="store_true",
        help="Only generate the scene plan, don't render",
    )
    parser.add_argument(
        "--from-plan",
        type=str,
        help="Skip planning, generate from an existing plan.json",
    )
    parser.add_argument(
        "--voice",
        type=str,
        help="ElevenLabs voice ID to use for narration",
    )
    parser.add_argument(
        "--no-voice",
        action="store_true",
        help="Skip voiceover generation (video only)",
    )
    parser.add_argument(
        "--no-captions",
        action="store_true",
        help="Skip subtitle burn-in (audio still included)",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Faster, lower-quality render for previewing",
    )
    parser.add_argument(
        "--duration",
        type=str,
        choices=["short", "medium", "long"],
        default="short",
        help="Video length: short (60-90s), medium (3-5min), long (8-12min)",
    )
    args = parser.parse_args()

    if not args.topic and not args.from_plan:
        parser.error("Provide a topic or --from-plan path")

    # ─── Step 1: Plan ───────────────────────────────────────────────
    if args.from_plan:
        print(f"Loading plan from {args.from_plan}...")
        plan = json.loads(Path(args.from_plan).read_text())
        topic_slug = slugify(plan["topic"])
    else:
        print(f"\n{'='*60}")
        print(f"Step 1/6: Planning scenes for '{args.topic}'")
        print(f"{'='*60}")
        plan = plan_scenes(args.topic, duration=args.duration)
        topic_slug = slugify(plan["topic"])

    # Create output directory
    out_dir = OUTPUT_ROOT / topic_slug
    out_dir.mkdir(parents=True, exist_ok=True)

    # Save plan
    plan_path = out_dir / "plan.json"
    plan_path.write_text(json.dumps(plan, indent=2))
    print(f"\nPlan saved to: {plan_path}")
    print(f"Title: {plan['title']}")
    print(f"Scenes: {len(plan['scenes'])}")
    for scene in plan["scenes"]:
        print(f"  {scene['id']}. {scene['narration'][:80]}...")

    if args.scenes_only:
        print(f"\n--scenes-only: stopping here. Edit {plan_path} and re-run with --from-plan")
        return

    # ─── Step 2: Generate Manim code ────────────────────────────────
    print(f"\n{'='*60}")
    print(f"Step 2/6: Generating Manim code")
    print(f"{'='*60}")
    code = generate_manim_code(plan)
    code_path = out_dir / "scenes.py"
    code_path.write_text(code)
    print(f"Code saved to: {code_path}")

    scene_names = get_scene_names(code)
    print(f"Scene classes found: {scene_names}")

    if not scene_names:
        print("ERROR: No Scene classes found in generated code.")
        sys.exit(1)

    # ─── Step 3: Render each scene ──────────────────────────────────
    print(f"\n{'='*60}")
    print(f"Step 3/6: Rendering {len(scene_names)} scene(s)")
    print(f"{'='*60}")

    rendered_videos = []
    current_code = code

    for scene_name in scene_names:
        print(f"\n  Rendering {scene_name}...")
        video_path, current_code = render_scene(
            code=current_code,
            scene_name=scene_name,
            output_dir=out_dir,
            code_path=code_path,
            preview=args.preview,
        )
        if video_path:
            rendered_videos.append(video_path)
            print(f"  Rendered: {video_path}")
        else:
            print(f"  SKIPPED: {scene_name} failed to render")

    if not rendered_videos:
        print("\nERROR: No scenes rendered successfully.")
        sys.exit(1)

    # Save final code (may have been fixed by retry loop)
    code_path.write_text(current_code)

    # ─── Step 4: Generate voiceover ─────────────────────────────────
    if args.no_voice:
        print("\n--no-voice: skipping voiceover and subtitles")
        # Just concatenate the silent videos
        if len(rendered_videos) == 1:
            final_path = out_dir / "final.mp4"
            rendered_videos[0].rename(final_path)
        else:
            final_path = out_dir / "final.mp4"
            concatenate_scenes(rendered_videos, final_path)
        print(f"\nFinal video: {final_path}")
        return

    print(f"\n{'='*60}")
    print(f"Step 4/6: Generating voiceover")
    print(f"{'='*60}")

    audio_files = []
    durations = []
    # Only process scenes that rendered successfully
    successful_scenes = plan["scenes"][:len(rendered_videos)]

    for i, scene in enumerate(successful_scenes):
        audio_path = out_dir / f"scene_{i+1:02d}.mp3"
        print(f"  Generating voice for scene {i+1}...")
        generate_voice(scene["narration"], audio_path, voice_id=args.voice)
        dur = get_audio_duration(audio_path)
        audio_files.append(audio_path)
        durations.append(dur)
        print(f"  Audio: {audio_path} ({dur:.1f}s)")

    # ─── Step 5: Generate subtitles ─────────────────────────────────
    print(f"\n{'='*60}")
    print(f"Step 5/6: Generating subtitles")
    print(f"{'='*60}")

    srt_path = out_dir / "subtitles.srt"
    generate_subtitles(successful_scenes, durations, srt_path)
    print(f"Subtitles: {srt_path}")

    # ─── Step 6: Assemble final video ───────────────────────────────
    print(f"\n{'='*60}")
    print(f"Step 6/6: Assembling final video")
    print(f"{'='*60}")

    # Combine each scene's video + audio
    combined_scenes = []
    for i, (video, audio) in enumerate(zip(rendered_videos, audio_files)):
        combined_path = out_dir / f"combined_{i+1:02d}.mp4"
        print(f"  Combining scene {i+1} video + audio...")
        combine_scene(video, audio, combined_path)
        combined_scenes.append(combined_path)

    # Concatenate all scenes
    no_subs = out_dir / "no_subtitles.mp4"
    if len(combined_scenes) == 1:
        combined_scenes[0].rename(no_subs)
    else:
        print("  Concatenating all scenes...")
        concatenate_scenes(combined_scenes, no_subs)

    # Burn in subtitles (or skip if --no-captions)
    final_path = out_dir / "final.mp4"
    if args.no_captions:
        print("  --no-captions: skipping subtitle burn-in")
        no_subs.rename(final_path)
    else:
        print("  Burning in subtitles...")
        burn_subtitles(no_subs, srt_path, final_path)

    # ─── Done ───────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"VIDEO COMPLETE!")
    print(f"{'='*60}")
    print(f"Output: {final_path}")
    print(f"All files: {out_dir}/")
    print(f"\nTo preview: open {final_path}")


if __name__ == "__main__":
    main()
