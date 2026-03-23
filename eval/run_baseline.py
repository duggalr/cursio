#!/usr/bin/env python3
"""
Baseline evaluation runner — generates videos and evaluates them for a set of topics.

Outputs everything into eval/runs/<run_name>/<topic_slug>/:
  - plan.json         (scene plan)
  - scenes.py         (generated Manim code)
  - scene01.mp4 ...   (individual scene renders)
  - final.mp4         (concatenated video)
  - eval_plan.json    (plan evaluation scores)
  - eval_video.json   (video evaluation scores)
  - frames/           (extracted frames used for video eval)

Also produces eval/runs/<run_name>/summary.json with aggregate results.

Usage:
    python eval/run_baseline.py                         # Run all 5 baseline topics
    python eval/run_baseline.py --run-name my_test      # Custom run name
    python eval/run_baseline.py --topic-index 0         # Run just topic 0
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT))

from core.planner import plan_scenes
from core.research import research_topic
from core.codegen import generate_manim_code
from core.renderer import render_scene, get_scene_names
from core.assembler import concatenate_scenes
from eval.evaluate import evaluate_plan, evaluate_video

EVAL_DIR = Path(__file__).parent
RUNS_DIR = EVAL_DIR / "runs"

# ─── Selected topics (5 diverse shorts, including 1 DL) ──────────────

BASELINE_TOPICS = [
    {
        "topic": "Why do neural networks need activation functions and what would happen without them?",
        "category": "deep_learning",
        "duration": "short",
    },
    {
        "topic": "Why does salt dissolve in water but oil doesn't?",
        "category": "fundamental_science",
        "duration": "short",
    },
    {
        "topic": "Is glass actually a liquid that flows very slowly over time?",
        "category": "common_misconceptions",
        "duration": "short",
    },
    {
        "topic": "How do computers generate random numbers if they only follow instructions?",
        "category": "explain_like_im_curious",
        "duration": "short",
    },
    {
        "topic": "How much information can the human brain actually store and is there a limit?",
        "category": "human_limits",
        "duration": "short",
    },
]


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "_", slug).strip("_")[:60]


def save_frames(video_path: Path, frames_dir: Path, interval: float = 5.0):
    """Extract frames from video and save as JPGs for review."""
    frames_dir.mkdir(exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(video_path),
            "-vf", f"fps=1/{interval}",
            "-q:v", "3",
            str(frames_dir / "frame_%03d.jpg"),
        ],
        capture_output=True, timeout=60,
    )


def generate_and_evaluate(topic_info: dict, run_dir: Path) -> dict:
    """Generate a video and evaluate it. Returns result dict."""
    topic = topic_info["topic"]
    duration = topic_info["duration"]
    category = topic_info["category"]
    slug = slugify(topic)

    topic_dir = run_dir / slug
    topic_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "topic": topic,
        "category": category,
        "duration": duration,
        "slug": slug,
        "status": "pending",
        "plan_scores": None,
        "video_scores": None,
        "render_stats": {},
    }

    print(f"\n{'='*70}")
    print(f"TOPIC: {topic}")
    print(f"Category: {category} | Duration: {duration}")
    print(f"Output: {topic_dir}")
    print(f"{'='*70}")

    # ── Step 1: Research + Plan ──
    print(f"\n[1/4] Researching topic...")
    t0 = time.time()
    research = research_topic(topic)
    research_time = time.time() - t0
    result["render_stats"]["research_time"] = round(research_time, 1)

    print(f"[1/4] Planning scenes...")
    t0 = time.time()
    plan = plan_scenes(
        topic,
        duration=duration,
        research_context=research.context if research.needed else "",
        research_sources=research.sources if research.needed else None,
    )
    plan_time = time.time() - t0
    result["render_stats"]["plan_time"] = round(plan_time, 1)

    plan_path = topic_dir / "plan.json"
    plan_path.write_text(json.dumps(plan, indent=2))
    print(f"  Title: {plan['title']}")
    print(f"  Scenes: {len(plan['scenes'])}")

    # ── Step 2: Evaluate plan ──
    print(f"\n[2/4] Evaluating plan...")
    try:
        plan_eval = evaluate_plan(plan, topic)
        result["plan_scores"] = plan_eval
        (topic_dir / "eval_plan.json").write_text(json.dumps(plan_eval, indent=2))
        print(f"  Plan score: {plan_eval.get('overall_score', 'N/A')}")
    except Exception as e:
        print(f"  Plan evaluation failed: {e}")
        result["plan_scores"] = {"error": str(e)}

    # ── Step 3: Generate code + render (no voice) ──
    print(f"\n[3/4] Generating Manim code + rendering...")

    # Estimate durations from word count
    durations = []
    for scene in plan["scenes"]:
        word_count = len(scene["narration"].split())
        durations.append(word_count / 2.5)

    t0 = time.time()
    code = generate_manim_code(plan, scene_durations=durations)
    codegen_time = time.time() - t0
    result["render_stats"]["codegen_time"] = round(codegen_time, 1)

    code_path = topic_dir / "scenes.py"
    code_path.write_text(code)

    scene_names = get_scene_names(code)
    print(f"  Scene classes: {scene_names}")

    if not scene_names:
        print("  ERROR: No Scene classes found")
        result["status"] = "codegen_failed"
        return result

    rendered_videos = []
    current_code = code
    t0 = time.time()

    for scene_name in scene_names:
        print(f"  Rendering {scene_name}...")
        video_path, current_code = render_scene(
            code=current_code,
            scene_name=scene_name,
            output_dir=topic_dir,
            code_path=code_path,
            preview=False,
        )
        if video_path:
            rendered_videos.append(video_path)
            print(f"    OK: {video_path.name}")
        else:
            print(f"    FAILED: {scene_name}")

    render_time = time.time() - t0
    result["render_stats"]["render_time"] = round(render_time, 1)
    result["render_stats"]["scenes_total"] = len(scene_names)
    result["render_stats"]["scenes_rendered"] = len(rendered_videos)

    # Save final code
    code_path.write_text(current_code)

    if not rendered_videos:
        print("  ERROR: No scenes rendered")
        result["status"] = "render_failed"
        return result

    # Concatenate into final video
    final_path = topic_dir / "final.mp4"
    if len(rendered_videos) == 1:
        shutil.copy2(rendered_videos[0], final_path)
    else:
        concatenate_scenes(rendered_videos, final_path)

    # Get video duration
    try:
        dur_str = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(final_path)],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        result["render_stats"]["final_duration"] = round(float(dur_str), 1)
    except Exception:
        pass

    print(f"  Final video: {final_path}")

    # ── Step 4: Evaluate video (multimodal) ──
    print(f"\n[4/4] Evaluating video (multimodal)...")

    # Save frames for manual review too
    frames_dir = topic_dir / "frames"
    save_frames(final_path, frames_dir)
    frame_count = len(list(frames_dir.glob("*.jpg")))
    print(f"  Extracted {frame_count} frames for review")

    narration = "\n\n".join(
        f"Scene {s['id']}: {s['narration']}"
        for s in plan.get("scenes", [])
    )

    try:
        video_eval = evaluate_video(final_path, topic, narration)
        result["video_scores"] = video_eval
        (topic_dir / "eval_video.json").write_text(json.dumps(video_eval, indent=2))
        print(f"  Video score: {video_eval.get('video_overall_score', 'N/A')}")
    except Exception as e:
        print(f"  Video evaluation failed: {e}")
        result["video_scores"] = {"error": str(e)}

    result["status"] = "completed"
    return result


def print_summary(results: list[dict]):
    """Print a formatted summary table."""
    print(f"\n{'#'*70}")
    print(f"BASELINE EVALUATION SUMMARY")
    print(f"{'#'*70}")

    # Plan scores
    print(f"\n{'Topic':<45} {'Plan':>6} {'Video':>6} {'Scenes':>8} {'Status':>10}")
    print("-" * 80)

    plan_scores = []
    video_scores = []

    for r in results:
        topic_short = r["topic"][:43]
        plan_score = r["plan_scores"].get("overall_score", "-") if r["plan_scores"] and "error" not in r["plan_scores"] else "-"
        video_score = r["video_scores"].get("video_overall_score", "-") if r["video_scores"] and "error" not in r["video_scores"] else "-"
        scenes = f"{r['render_stats'].get('scenes_rendered', 0)}/{r['render_stats'].get('scenes_total', 0)}"
        status = r["status"]

        if isinstance(plan_score, (int, float)):
            plan_scores.append(plan_score)
        if isinstance(video_score, (int, float)):
            video_scores.append(video_score)

        plan_str = f"{plan_score:.1f}" if isinstance(plan_score, (int, float)) else str(plan_score)
        video_str = f"{video_score:.1f}" if isinstance(video_score, (int, float)) else str(video_score)

        print(f"  {topic_short:<45} {plan_str:>6} {video_str:>6} {scenes:>8} {status:>10}")

    if plan_scores:
        avg_plan = sum(plan_scores) / len(plan_scores)
        avg_video = sum(video_scores) / len(video_scores) if video_scores else 0
        print(f"\n  {'AVERAGE':<45} {avg_plan:>6.1f} {avg_video:>6.1f}")

    # Detailed breakdown
    print(f"\n{'─'*70}")
    print("PLAN CRITERIA BREAKDOWN")
    print(f"{'─'*70}")

    plan_criteria = ["accuracy", "depth", "hook_quality", "narrative_flow",
                     "analogy_clarity", "visual_narration_fit", "shareability"]
    header = f"{'Criterion':<25}" + "".join(f"{'T'+str(i+1):>8}" for i in range(len(results))) + f"{'Avg':>8}"
    print(header)
    print("-" * (25 + 8 * (len(results) + 1)))

    for criterion in plan_criteria:
        vals = []
        row = f"  {criterion:<23}"
        for r in results:
            if r["plan_scores"] and "error" not in r["plan_scores"]:
                v = r["plan_scores"].get(criterion, 0)
                vals.append(v)
                row += f"{v:>8.1f}"
            else:
                row += f"{'--':>8}"
        if vals:
            row += f"{sum(vals)/len(vals):>8.1f}"
        print(row)

    print(f"\n{'─'*70}")
    print("VIDEO CRITERIA BREAKDOWN")
    print(f"{'─'*70}")

    video_criteria = ["visual_clarity", "animation_quality", "audio_visual_sync",
                      "pacing", "watch_through"]
    header = f"{'Criterion':<25}" + "".join(f"{'T'+str(i+1):>8}" for i in range(len(results))) + f"{'Avg':>8}"
    print(header)
    print("-" * (25 + 8 * (len(results) + 1)))

    for criterion in video_criteria:
        vals = []
        row = f"  {criterion:<23}"
        for r in results:
            if r["video_scores"] and "error" not in r["video_scores"]:
                v = r["video_scores"].get(criterion, 0)
                vals.append(v)
                row += f"{v:>8.1f}"
            else:
                row += f"{'--':>8}"
        if vals:
            row += f"{sum(vals)/len(vals):>8.1f}"
        print(row)

    # Common issues
    print(f"\n{'─'*70}")
    print("COMMON ISSUES")
    print(f"{'─'*70}")
    for i, r in enumerate(results):
        print(f"\nT{i+1}: {r['topic'][:60]}")
        if r["plan_scores"] and "error" not in r["plan_scores"]:
            print(f"  Plan weakest: {r['plan_scores'].get('weakest_moment', 'N/A')}")
        if r["video_scores"] and "error" not in r["video_scores"]:
            issues = r["video_scores"].get("visual_issues", [])
            print(f"  Visual issues: {issues}")
            print(f"  Worst moment: {r['video_scores'].get('worst_visual_moment', 'N/A')}")
            for s in r["video_scores"].get("suggestions", []):
                print(f"    - {s}")


def main():
    parser = argparse.ArgumentParser(description="Run baseline video generation evaluation")
    parser.add_argument("--run-name", type=str, default="baseline_2026-03-22",
                        help="Name for this evaluation run")
    parser.add_argument("--topic-index", type=int, default=None,
                        help="Run only a specific topic by index (0-4)")
    args = parser.parse_args()

    run_dir = RUNS_DIR / args.run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    # Determine which topics to run
    if args.topic_index is not None:
        topics = [BASELINE_TOPICS[args.topic_index]]
    else:
        topics = BASELINE_TOPICS

    # Save topic list
    (run_dir / "topics.json").write_text(json.dumps(topics, indent=2))

    print(f"\n{'#'*70}")
    print(f"BASELINE EVALUATION RUN: {args.run_name}")
    print(f"Topics: {len(topics)}")
    print(f"Output: {run_dir}")
    print(f"Mode: no-voice (estimated durations)")
    print(f"{'#'*70}")

    for i, t in enumerate(topics):
        print(f"  [{i}] {t['topic'][:60]} ({t['category']})")

    total_start = time.time()
    results = []

    for i, topic_info in enumerate(topics):
        print(f"\n\n{'*'*70}")
        print(f"TOPIC {i+1}/{len(topics)}")
        print(f"{'*'*70}")

        result = generate_and_evaluate(topic_info, run_dir)
        results.append(result)

        # Save incremental results
        (run_dir / "summary.json").write_text(json.dumps({
            "run_name": args.run_name,
            "total_topics": len(topics),
            "completed": len(results),
            "total_time": round(time.time() - total_start, 1),
            "results": results,
        }, indent=2, default=str))

    total_time = time.time() - total_start
    print(f"\n\nTotal time: {total_time:.0f}s ({total_time/60:.1f}m)")

    print_summary(results)

    # Final save
    summary = {
        "run_name": args.run_name,
        "total_topics": len(topics),
        "completed": len(results),
        "total_time": round(total_time, 1),
        "results": results,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nFull results saved: {run_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
