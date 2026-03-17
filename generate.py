#!/usr/bin/env python3
"""
AI Educational Video Generator — CLI entry point.

Generates 3Blue1Brown-style educational videos from a topic prompt.

Usage:
    python generate.py "Explain the derivative"
    python generate.py "Explain the derivative" --duration medium
    python generate.py "How InfiniBand partitioning works" --scenes-only --duration long
    python generate.py --from-plan output/the_derivative/plan.json
    python generate.py "What is recursion" --no-voice --preview
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from core.planner import plan_scenes
from core.codegen import generate_manim_code
from core.renderer import render_scene, get_scene_names
from core.voice import generate_voice, get_audio_duration
from core.assembler import combine_scene, concatenate_scenes


OUTPUT_ROOT = Path(__file__).parent / "output"


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

    # ─── Step 2: Generate voiceover (audio-first for timing) ────────
    if args.no_voice:
        print("\n--no-voice: skipping voiceover, using estimated durations")
        audio_files = []
        durations = []
        # Estimate durations from word count (~2.5 words/sec)
        for scene in plan["scenes"]:
            word_count = len(scene["narration"].split())
            durations.append(word_count / 2.5)
    else:
        print(f"\n{'='*60}")
        print(f"Step 2/6: Generating voiceover (audio-first)")
        print(f"{'='*60}")

        audio_files = []
        durations = []
        for i, scene in enumerate(plan["scenes"]):
            audio_path = out_dir / f"scene_{i+1:02d}.mp3"
            print(f"  Generating voice for scene {i+1}...")
            generate_voice(scene["narration"], audio_path, voice_id=args.voice)
            dur = get_audio_duration(audio_path)
            audio_files.append(audio_path)
            durations.append(dur)
            print(f"  Audio: {audio_path} ({dur:.1f}s)")

    # ─── Step 3: Generate Manim code (with exact durations) ──────────
    print(f"\n{'='*60}")
    print(f"Step 3/6: Generating Manim code (targeting audio durations)")
    print(f"{'='*60}")
    for i, dur in enumerate(durations):
        print(f"  Scene {i+1}: {dur:.1f}s target")

    code = generate_manim_code(plan, scene_durations=durations)
    code_path = out_dir / "scenes.py"
    code_path.write_text(code)
    print(f"Code saved to: {code_path}")

    scene_names = get_scene_names(code)
    print(f"Scene classes found: {scene_names}")

    if not scene_names:
        print("ERROR: No Scene classes found in generated code.")
        sys.exit(1)

    # ─── Step 4: Render each scene ──────────────────────────────────
    print(f"\n{'='*60}")
    print(f"Step 4/6: Rendering {len(scene_names)} scene(s)")
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

    # Print timing comparison
    print(f"\n  Timing comparison (animation vs audio):")
    for i, vid in enumerate(rendered_videos):
        vid_dur = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(vid)],
            capture_output=True, text=True).stdout.strip())
        target = durations[i] if i < len(durations) else 0
        diff = vid_dur - target
        print(f"  Scene {i+1}: animation={vid_dur:.1f}s, audio={target:.1f}s, diff={diff:+.1f}s")

    if args.no_voice:
        print("\n--no-voice: skipping assembly")
        if len(rendered_videos) == 1:
            final_path = out_dir / "final.mp4"
            rendered_videos[0].rename(final_path)
        else:
            final_path = out_dir / "final.mp4"
            concatenate_scenes(rendered_videos, final_path)
        print(f"\nFinal video: {final_path}")
        return

    # ─── Step 5: Assemble final video ───────────────────────────────
    print(f"\n{'='*60}")
    print(f"Step 5/6: Assembling final video")
    print(f"{'='*60}")

    # Combine each scene's video + audio
    successful_scenes = plan["scenes"][:len(rendered_videos)]
    combined_scenes = []
    for i, (video, audio) in enumerate(zip(rendered_videos, audio_files)):
        combined_path = out_dir / f"combined_{i+1:02d}.mp4"
        print(f"  Combining scene {i+1} video + audio...")
        combine_scene(video, audio, combined_path)
        combined_scenes.append(combined_path)

    # Concatenate all scenes
    final_path = out_dir / "final.mp4"
    if len(combined_scenes) == 1:
        combined_scenes[0].rename(final_path)
    else:
        print("  Concatenating all scenes...")
        concatenate_scenes(combined_scenes, final_path)

    # ─── Done ───────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"VIDEO COMPLETE!")
    print(f"{'='*60}")
    print(f"Output: {final_path}")
    print(f"All files: {out_dir}/")
    print(f"\nTo preview: open {final_path}")


if __name__ == "__main__":
    main()
