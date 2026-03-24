#!/usr/bin/env python3
"""
A/B evaluation: baseline vs quality mode pipeline.

Runs same 5 topics through both pipelines (no-voice) and compares
plan scores and video scores side by side.

Usage:
    python eval/run_quality_ab.py
    python eval/run_quality_ab.py --topic-index 0
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import date
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
from core.quality_pipeline import run_quality_pipeline
from eval.evaluate import evaluate_plan, evaluate_video

EVAL_DIR = Path(__file__).parent
RUNS_DIR = EVAL_DIR / "runs"

# ─── Same 5 diverse topics as baseline ──────────────────────────────

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


def run_baseline_variant(plan: dict, topic_dir: Path, durations: list[float]) -> dict:
    """Run the baseline pipeline (codegen + render, no voice)."""
    result = {"variant": "baseline", "status": "pending"}

    variant_dir = topic_dir / "baseline"
    variant_dir.mkdir(parents=True, exist_ok=True)

    # Save plan
    (variant_dir / "plan.json").write_text(json.dumps(plan, indent=2))

    print(f"\n  [BASELINE] Generating Manim code + rendering...")
    t0 = time.time()
    code = generate_manim_code(plan, scene_durations=durations)
    codegen_time = time.time() - t0
    result["codegen_time"] = round(codegen_time, 1)

    code_path = variant_dir / "scenes.py"
    code_path.write_text(code)

    scene_names = get_scene_names(code)
    print(f"  [BASELINE] Scene classes: {scene_names}")

    if not scene_names:
        print("  [BASELINE] ERROR: No Scene classes found")
        result["status"] = "codegen_failed"
        return result

    rendered_videos = []
    current_code = code
    t0 = time.time()

    for scene_name in scene_names:
        print(f"  [BASELINE] Rendering {scene_name}...")
        video_path, current_code = render_scene(
            code=current_code,
            scene_name=scene_name,
            output_dir=variant_dir,
            code_path=code_path,
            preview=False,
        )
        if video_path:
            rendered_videos.append(video_path)
            print(f"    OK: {video_path.name}")
        else:
            print(f"    FAILED: {scene_name}")

    render_time = time.time() - t0
    result["render_time"] = round(render_time, 1)
    result["scenes_total"] = len(scene_names)
    result["scenes_rendered"] = len(rendered_videos)

    code_path.write_text(current_code)

    if not rendered_videos:
        print("  [BASELINE] ERROR: No scenes rendered")
        result["status"] = "render_failed"
        return result

    # Concatenate into final video
    final_path = variant_dir / "final.mp4"
    if len(rendered_videos) == 1:
        shutil.copy2(rendered_videos[0], final_path)
    else:
        concatenate_scenes(rendered_videos, final_path)

    result["final_path"] = str(final_path)
    result["status"] = "completed"

    # Get video duration
    try:
        dur_str = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(final_path)],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        result["final_duration"] = round(float(dur_str), 1)
    except Exception:
        pass

    print(f"  [BASELINE] Final video: {final_path}")
    return result


def run_quality_variant(plan: dict, topic_dir: Path) -> dict:
    """Run the quality mode pipeline (no voice)."""
    result = {"variant": "quality", "status": "pending"}

    variant_dir = topic_dir / "quality"
    variant_dir.mkdir(parents=True, exist_ok=True)

    # Save plan
    (variant_dir / "plan.json").write_text(json.dumps(plan, indent=2))

    print(f"\n  [QUALITY] Running quality pipeline...")
    t0 = time.time()

    try:
        qr = run_quality_pipeline(
            plan=plan,
            output_dir=variant_dir,
            no_voice=True,
        )
        pipeline_time = time.time() - t0
        result["pipeline_time"] = round(pipeline_time, 1)
        result["final_path"] = str(qr["final_path"])
        result["scene_durations"] = qr["scene_durations"]
        result["status"] = "completed"

        # Get video duration
        try:
            dur_str = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(qr["final_path"])],
                capture_output=True, text=True, timeout=10,
            ).stdout.strip()
            result["final_duration"] = round(float(dur_str), 1)
        except Exception:
            pass

        print(f"  [QUALITY] Final video: {qr['final_path']}")
    except Exception as e:
        pipeline_time = time.time() - t0
        result["pipeline_time"] = round(pipeline_time, 1)
        result["status"] = "failed"
        result["error"] = str(e)
        print(f"  [QUALITY] FAILED: {e}")

    return result


def evaluate_variant(variant_result: dict, plan: dict, topic: str, topic_dir: Path) -> dict:
    """Evaluate a variant's video output."""
    variant_name = variant_result["variant"]
    variant_dir = topic_dir / variant_name

    if variant_result["status"] != "completed":
        return {"plan_scores": None, "video_scores": None}

    scores = {}

    # Evaluate plan (same plan for both, but evaluate anyway for completeness)
    print(f"  [{variant_name.upper()}] Evaluating plan...")
    try:
        plan_eval = evaluate_plan(plan, topic)
        scores["plan_scores"] = plan_eval
        (variant_dir / "eval_plan.json").write_text(json.dumps(plan_eval, indent=2))
        print(f"    Plan score: {plan_eval.get('overall_score', 'N/A')}")
    except Exception as e:
        print(f"    Plan evaluation failed: {e}")
        scores["plan_scores"] = {"error": str(e)}

    # Evaluate video
    final_path = Path(variant_result["final_path"])
    print(f"  [{variant_name.upper()}] Evaluating video...")

    frames_dir = variant_dir / "frames"
    save_frames(final_path, frames_dir)

    narration = "\n\n".join(
        f"Scene {s['id']}: {s['narration']}"
        for s in plan.get("scenes", [])
    )

    try:
        video_eval = evaluate_video(final_path, topic, narration)
        scores["video_scores"] = video_eval
        (variant_dir / "eval_video.json").write_text(json.dumps(video_eval, indent=2))
        print(f"    Video score: {video_eval.get('video_overall_score', 'N/A')}")
    except Exception as e:
        print(f"    Video evaluation failed: {e}")
        scores["video_scores"] = {"error": str(e)}

    return scores


def generate_and_compare(topic_info: dict, run_dir: Path) -> dict:
    """Generate a video with both pipelines and compare evaluations."""
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
        "baseline": None,
        "quality": None,
    }

    print(f"\n{'='*70}")
    print(f"TOPIC: {topic}")
    print(f"Category: {category} | Duration: {duration}")
    print(f"Output: {topic_dir}")
    print(f"{'='*70}")

    # ── Step 1: Research + Plan (shared) ──
    print(f"\n[1/5] Researching topic...")
    research = research_topic(topic)

    print(f"[1/5] Planning scenes...")
    plan = plan_scenes(
        topic,
        duration=duration,
        research_context=research.context if research.needed else "",
        research_sources=research.sources if research.needed else None,
    )

    (topic_dir / "plan.json").write_text(json.dumps(plan, indent=2))
    print(f"  Title: {plan['title']}")
    print(f"  Scenes: {len(plan['scenes'])}")

    # Estimate durations from word count (for baseline)
    durations = []
    for scene in plan["scenes"]:
        word_count = len(scene["narration"].split())
        durations.append(word_count / 2.5)

    # ── Step 2: Run baseline variant ──
    print(f"\n[2/5] Running BASELINE variant...")
    baseline_result = run_baseline_variant(plan, topic_dir, durations)
    result["baseline"] = baseline_result

    # ── Step 3: Run quality variant ──
    print(f"\n[3/5] Running QUALITY variant...")
    quality_result = run_quality_variant(plan, topic_dir)
    result["quality"] = quality_result

    # ── Step 4: Evaluate baseline ──
    print(f"\n[4/5] Evaluating BASELINE variant...")
    baseline_scores = evaluate_variant(baseline_result, plan, topic, topic_dir)
    result["baseline"].update(baseline_scores)

    # ── Step 5: Evaluate quality ──
    print(f"\n[5/5] Evaluating QUALITY variant...")
    quality_scores = evaluate_variant(quality_result, plan, topic, topic_dir)
    result["quality"].update(quality_scores)

    return result


def print_comparison(results: list[dict]):
    """Print a side-by-side comparison of baseline vs quality."""
    print(f"\n{'#'*70}")
    print(f"A/B COMPARISON: BASELINE vs QUALITY MODE")
    print(f"{'#'*70}")

    print(f"\n{'Topic':<40} {'Base Plan':>10} {'Qual Plan':>10} {'Base Vid':>10} {'Qual Vid':>10}")
    print("-" * 85)

    base_plan_scores = []
    qual_plan_scores = []
    base_video_scores = []
    qual_video_scores = []

    for r in results:
        topic_short = r["topic"][:38]

        bp = "-"
        qp = "-"
        bv = "-"
        qv = "-"

        if r["baseline"] and r["baseline"].get("plan_scores") and "error" not in r["baseline"]["plan_scores"]:
            bp = r["baseline"]["plan_scores"].get("overall_score", "-")
            if isinstance(bp, (int, float)):
                base_plan_scores.append(bp)

        if r["quality"] and r["quality"].get("plan_scores") and "error" not in r["quality"]["plan_scores"]:
            qp = r["quality"]["plan_scores"].get("overall_score", "-")
            if isinstance(qp, (int, float)):
                qual_plan_scores.append(qp)

        if r["baseline"] and r["baseline"].get("video_scores") and "error" not in r["baseline"]["video_scores"]:
            bv = r["baseline"]["video_scores"].get("video_overall_score", "-")
            if isinstance(bv, (int, float)):
                base_video_scores.append(bv)

        if r["quality"] and r["quality"].get("video_scores") and "error" not in r["quality"]["video_scores"]:
            qv = r["quality"]["video_scores"].get("video_overall_score", "-")
            if isinstance(qv, (int, float)):
                qual_video_scores.append(qv)

        bp_str = f"{bp:.1f}" if isinstance(bp, (int, float)) else str(bp)
        qp_str = f"{qp:.1f}" if isinstance(qp, (int, float)) else str(qp)
        bv_str = f"{bv:.1f}" if isinstance(bv, (int, float)) else str(bv)
        qv_str = f"{qv:.1f}" if isinstance(qv, (int, float)) else str(qv)

        print(f"  {topic_short:<40} {bp_str:>10} {qp_str:>10} {bv_str:>10} {qv_str:>10}")

    print("-" * 85)

    avg_bp = sum(base_plan_scores) / len(base_plan_scores) if base_plan_scores else 0
    avg_qp = sum(qual_plan_scores) / len(qual_plan_scores) if qual_plan_scores else 0
    avg_bv = sum(base_video_scores) / len(base_video_scores) if base_video_scores else 0
    avg_qv = sum(qual_video_scores) / len(qual_video_scores) if qual_video_scores else 0

    print(f"  {'AVERAGE':<40} {avg_bp:>10.1f} {avg_qp:>10.1f} {avg_bv:>10.1f} {avg_qv:>10.1f}")

    if avg_bv and avg_qv:
        diff = avg_qv - avg_bv
        pct = (diff / avg_bv) * 100 if avg_bv else 0
        print(f"\n  Quality mode video score delta: {diff:+.1f} ({pct:+.1f}%)")

    # Timing comparison
    print(f"\n{'─'*70}")
    print("TIMING COMPARISON")
    print(f"{'─'*70}")

    for r in results:
        topic_short = r["topic"][:50]
        base_time = "-"
        qual_time = "-"
        if r["baseline"]:
            bt = r["baseline"].get("render_time", r["baseline"].get("codegen_time", 0))
            if isinstance(bt, (int, float)) and bt > 0:
                base_time = f"{bt:.0f}s"
        if r["quality"]:
            qt = r["quality"].get("pipeline_time", 0)
            if isinstance(qt, (int, float)) and qt > 0:
                qual_time = f"{qt:.0f}s"
        print(f"  {topic_short:<50} baseline={base_time:>8}  quality={qual_time:>8}")


def main():
    parser = argparse.ArgumentParser(description="A/B evaluation: baseline vs quality mode")
    parser.add_argument("--run-name", type=str, default=None,
                        help="Name for this evaluation run")
    parser.add_argument("--topic-index", type=int, default=None,
                        help="Run only a specific topic by index (0-4)")
    args = parser.parse_args()

    run_name = args.run_name or f"quality_ab_{date.today().isoformat()}"
    run_dir = RUNS_DIR / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    # Determine which topics to run
    if args.topic_index is not None:
        topics = [BASELINE_TOPICS[args.topic_index]]
    else:
        topics = BASELINE_TOPICS

    # Save topic list
    (run_dir / "topics.json").write_text(json.dumps(topics, indent=2))

    print(f"\n{'#'*70}")
    print(f"A/B EVALUATION: BASELINE vs QUALITY MODE")
    print(f"Run: {run_name}")
    print(f"Topics: {len(topics)}")
    print(f"Output: {run_dir}")
    print(f"Mode: no-voice (both variants)")
    print(f"{'#'*70}")

    for i, t in enumerate(topics):
        print(f"  [{i}] {t['topic'][:60]} ({t['category']})")

    total_start = time.time()
    results = []

    for i, topic_info in enumerate(topics):
        print(f"\n\n{'*'*70}")
        print(f"TOPIC {i+1}/{len(topics)}")
        print(f"{'*'*70}")

        result = generate_and_compare(topic_info, run_dir)
        results.append(result)

        # Save incremental results
        (run_dir / "summary.json").write_text(json.dumps({
            "run_name": run_name,
            "total_topics": len(topics),
            "completed": len(results),
            "total_time": round(time.time() - total_start, 1),
            "results": results,
        }, indent=2, default=str))

    total_time = time.time() - total_start
    print(f"\n\nTotal time: {total_time:.0f}s ({total_time/60:.1f}m)")

    print_comparison(results)

    # Final save
    summary = {
        "run_name": run_name,
        "total_topics": len(topics),
        "completed": len(results),
        "total_time": round(total_time, 1),
        "results": results,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nFull results saved: {run_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
