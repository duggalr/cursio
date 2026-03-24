#!/usr/bin/env python3
"""
A/B eval: baseline vs quality mode on MEDIUM-length topics (no voice).

This is where quality mode should shine — longer videos benefit from
per-scene iteration and narration adjustment.

Usage:
    python eval/run_quality_medium.py
    python eval/run_quality_medium.py --topic-index 0
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
from core.codegen import generate_manim_code
from core.renderer import render_scene, get_scene_names
from core.assembler import concatenate_scenes
from core.quality_pipeline import run_quality_pipeline
from eval.evaluate import evaluate_plan, evaluate_video

EVAL_DIR = Path(__file__).parent
RUNS_DIR = EVAL_DIR / "runs"

# 3 diverse medium topics
MEDIUM_TOPICS = [
    {
        "topic": "How does backpropagation actually compute gradients through a neural network?",
        "category": "deep_learning",
        "duration": "medium",
    },
    {
        "topic": "How does Bayes' theorem update what you believe when you get new evidence?",
        "category": "math_and_equations",
        "duration": "medium",
    },
    {
        "topic": "What is natural selection and how does a species actually evolve over time?",
        "category": "explain_like_im_curious",
        "duration": "medium",
    },
]


def slugify(text):
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "_", slug).strip("_")[:60]


def save_frames(video_path, frames_dir, interval=5.0):
    frames_dir.mkdir(exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-i", str(video_path), "-vf", f"fps=1/{interval}",
         "-q:v", "3", str(frames_dir / "frame_%03d.jpg")],
        capture_output=True, timeout=60,
    )


def run_baseline(plan, topic_dir):
    """Run baseline pipeline (no voice)."""
    out = topic_dir / "baseline"
    out.mkdir(parents=True, exist_ok=True)

    durations = [len(s["narration"].split()) / 2.5 for s in plan["scenes"]]
    code = generate_manim_code(plan, scene_durations=durations)
    code_path = out / "scenes.py"
    code_path.write_text(code)

    scene_names = get_scene_names(code)
    if not scene_names:
        return None

    rendered = []
    current_code = code
    for sn in scene_names:
        vp, current_code = render_scene(current_code, sn, out, code_path, preview=False)
        if vp:
            rendered.append(vp)

    code_path.write_text(current_code)
    if not rendered:
        return None

    final = out / "final.mp4"
    if len(rendered) == 1:
        shutil.copy2(rendered[0], final)
    else:
        concatenate_scenes(rendered, final)

    save_frames(final, out / "frames")
    return final


def run_quality(plan, topic_dir):
    """Run quality mode pipeline (no voice)."""
    out = topic_dir / "quality"
    out.mkdir(parents=True, exist_ok=True)

    result = run_quality_pipeline(plan, out, no_voice=True)
    if result["final_path"] and result["final_path"].exists():
        save_frames(result["final_path"], out / "frames")
        return result["final_path"]
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic-index", type=int, default=None)
    parser.add_argument("--run-name", type=str, default=f"quality_medium_{date.today()}")
    args = parser.parse_args()

    topics = [MEDIUM_TOPICS[args.topic_index]] if args.topic_index is not None else MEDIUM_TOPICS
    run_dir = RUNS_DIR / args.run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "topics.json").write_text(json.dumps(topics, indent=2))

    print(f"\n{'#'*70}")
    print(f"MEDIUM TOPIC EVAL: baseline vs quality mode (no-voice)")
    print(f"Topics: {len(topics)} | Output: {run_dir}")
    print(f"{'#'*70}")
    for i, t in enumerate(topics):
        print(f"  [{i}] {t['topic'][:65]}")

    total_start = time.time()
    results = []

    for i, topic_info in enumerate(topics):
        topic = topic_info["topic"]
        slug = slugify(topic)
        topic_dir = run_dir / slug

        print(f"\n{'*'*70}")
        print(f"TOPIC {i+1}/{len(topics)}: {topic[:65]}")
        print(f"{'*'*70}")

        # Plan (shared)
        print(f"\n[1/5] Planning...")
        plan = plan_scenes(topic, duration=topic_info["duration"])
        (topic_dir / "plan.json").write_text(json.dumps(plan, indent=2)) if topic_dir.exists() else None
        topic_dir.mkdir(parents=True, exist_ok=True)
        (topic_dir / "plan.json").write_text(json.dumps(plan, indent=2))
        print(f"  Title: {plan['title']} ({len(plan['scenes'])} scenes)")

        result = {"topic": topic, "category": topic_info["category"], "duration": topic_info["duration"]}

        # Baseline
        print(f"\n[2/5] Running BASELINE...")
        t0 = time.time()
        baseline_path = run_baseline(plan, topic_dir)
        baseline_time = time.time() - t0
        print(f"  Baseline: {'OK' if baseline_path else 'FAILED'} ({baseline_time:.0f}s)")

        # Quality
        print(f"\n[3/5] Running QUALITY...")
        t0 = time.time()
        quality_path = run_quality(plan, topic_dir)
        quality_time = time.time() - t0
        print(f"  Quality: {'OK' if quality_path else 'FAILED'} ({quality_time:.0f}s)")

        # Evaluate
        narration = "\n\n".join(f"Scene {s['id']}: {s['narration']}" for s in plan["scenes"])

        print(f"\n[4/5] Evaluating BASELINE...")
        result["baseline"] = {"time": round(baseline_time)}
        try:
            result["baseline"]["plan_scores"] = evaluate_plan(plan, topic)
            print(f"  Plan: {result['baseline']['plan_scores'].get('overall_score', '?')}")
        except Exception as e:
            result["baseline"]["plan_scores"] = {"error": str(e)}

        if baseline_path:
            try:
                result["baseline"]["video_scores"] = evaluate_video(baseline_path, topic, narration)
                print(f"  Video: {result['baseline']['video_scores'].get('video_overall_score', '?')}")
            except Exception as e:
                result["baseline"]["video_scores"] = {"error": str(e)}
        else:
            result["baseline"]["video_scores"] = {"error": "no video"}

        print(f"\n[5/5] Evaluating QUALITY...")
        result["quality"] = {"time": round(quality_time)}
        try:
            result["quality"]["plan_scores"] = evaluate_plan(plan, topic)
            print(f"  Plan: {result['quality']['plan_scores'].get('overall_score', '?')}")
        except Exception as e:
            result["quality"]["plan_scores"] = {"error": str(e)}

        if quality_path:
            try:
                result["quality"]["video_scores"] = evaluate_video(quality_path, topic, narration)
                print(f"  Video: {result['quality']['video_scores'].get('video_overall_score', '?')}")
            except Exception as e:
                result["quality"]["video_scores"] = {"error": str(e)}
        else:
            result["quality"]["video_scores"] = {"error": "no video"}

        results.append(result)
        (run_dir / "summary.json").write_text(json.dumps({"results": results, "total_time": round(time.time() - total_start)}, indent=2, default=str))

    # Print comparison
    total_time = time.time() - total_start
    print(f"\n\nTotal time: {total_time:.0f}s ({total_time/60:.1f}m)")

    print(f"\n{'#'*70}")
    print(f"MEDIUM TOPIC COMPARISON: BASELINE vs QUALITY")
    print(f"{'#'*70}")

    print(f"\n{'Topic':<40} {'Base Vid':>9} {'Qual Vid':>9} {'Delta':>7} {'Base t':>7} {'Qual t':>7}")
    print("-" * 80)

    base_scores = []
    qual_scores = []
    for r in results:
        t = r["topic"][:38]
        bv = r["baseline"].get("video_scores", {}).get("video_overall_score", "-")
        qv = r["quality"].get("video_scores", {}).get("video_overall_score", "-")
        bt = r["baseline"].get("time", 0)
        qt = r["quality"].get("time", 0)

        if isinstance(bv, (int, float)):
            base_scores.append(bv)
        if isinstance(qv, (int, float)):
            qual_scores.append(qv)

        delta = f"{qv - bv:+.1f}" if isinstance(bv, (int, float)) and isinstance(qv, (int, float)) else "-"
        bv_s = f"{bv:.1f}" if isinstance(bv, (int, float)) else str(bv)
        qv_s = f"{qv:.1f}" if isinstance(qv, (int, float)) else str(qv)

        print(f"  {t:<40} {bv_s:>9} {qv_s:>9} {delta:>7} {bt:>6}s {qt:>6}s")

    if base_scores and qual_scores:
        avg_b = sum(base_scores) / len(base_scores)
        avg_q = sum(qual_scores) / len(qual_scores)
        print(f"\n  {'AVERAGE':<40} {avg_b:>9.1f} {avg_q:>9.1f} {avg_q-avg_b:>+7.1f}")

    print(f"\nResults: {run_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
