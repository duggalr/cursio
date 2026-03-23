#!/usr/bin/env python3
"""
A/B evaluation: baseline (no research) vs research-augmented (Tavily search).

Picks 5 topics likely to benefit from web search, generates each topic TWICE:
  A) Baseline — research step forced OFF
  B) Research-augmented — research step ON (uses Tavily)

Evaluates both and produces a side-by-side comparison.

Directory structure:
  eval/runs/<run_name>/
    topics.json
    summary.json
    <topic_slug>/
      baseline/           # Variant A
        plan.json, scenes.py, scene*.mp4, final.mp4
        eval_plan.json, eval_video.json, frames/
      research/            # Variant B
        plan.json, scenes.py, scene*.mp4, final.mp4
        eval_plan.json, eval_video.json, frames/

Usage:
    python eval/run_research_ab.py
    python eval/run_research_ab.py --run-name my_test
    python eval/run_research_ab.py --topic-index 2    # Just one topic
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
from core.research import research_topic, needs_research, search_web
from core.codegen import generate_manim_code
from core.renderer import render_scene, get_scene_names
from core.assembler import concatenate_scenes
from eval.evaluate import evaluate_plan, evaluate_video

EVAL_DIR = Path(__file__).parent
RUNS_DIR = EVAL_DIR / "runs"

# ─── 5 topics that should benefit from web search ────────────────────
# Mix of cutting-edge science and topics where current data matters

AB_TOPICS = [
    {
        "topic": "What is the current state of brain-computer interfaces and what can they actually do today?",
        "category": "cutting_edge_science",
        "duration": "short",
    },
    {
        "topic": "How are researchers using AI to discover new drugs and what breakthroughs have happened?",
        "category": "cutting_edge_science",
        "duration": "short",
    },
    {
        "topic": "What are the latest approaches to making quantum computers error-corrected and practical?",
        "category": "cutting_edge_science",
        "duration": "short",
    },
    {
        "topic": "How close are we to reversing aging at the cellular level and what has been proven so far?",
        "category": "cutting_edge_science",
        "duration": "short",
    },
    {
        "topic": "What do we currently know about dark matter and dark energy and what are the leading theories?",
        "category": "cutting_edge_science",
        "duration": "short",
    },
]


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "_", slug).strip("_")[:60]


def save_frames(video_path: Path, frames_dir: Path, interval: float = 5.0):
    """Extract frames from video and save as JPGs."""
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


def generate_variant(
    topic: str,
    duration: str,
    variant_dir: Path,
    use_research: bool,
) -> dict:
    """Generate and evaluate a single variant (baseline or research).

    Returns result dict with scores and metadata.
    """
    variant_dir.mkdir(parents=True, exist_ok=True)
    label = "RESEARCH" if use_research else "BASELINE"

    result = {
        "status": "pending",
        "used_search": False,
        "search_queries": [],
        "num_sources": 0,
        "plan_scores": None,
        "video_scores": None,
        "render_stats": {},
    }

    # ── Research + Plan ──
    t0 = time.time()

    research_context = ""
    research_sources = None

    if use_research:
        print(f"  [{label}] Running research pipeline...")
        try:
            assessment = needs_research(topic)
            result["research_assessment"] = assessment

            if assessment.get("needed", False):
                print(f"  [{label}] Research needed: {assessment.get('reason', '')}")
                queries = assessment.get("search_queries", [topic])
                result["search_queries"] = queries

                from core.research import search_web
                research_result = search_web(queries)
                research_context = research_result.context
                research_sources = research_result.sources
                result["used_search"] = True
                result["num_sources"] = len(research_result.sources)
                print(f"  [{label}] Found {len(research_result.sources)} sources")
            else:
                print(f"  [{label}] Research NOT triggered: {assessment.get('reason', '')}")
        except Exception as e:
            print(f"  [{label}] Research failed: {e}")
    else:
        print(f"  [{label}] Research skipped (baseline)")

    print(f"  [{label}] Planning scenes...")
    plan = plan_scenes(
        topic,
        duration=duration,
        research_context=research_context,
        research_sources=research_sources,
    )
    plan_time = time.time() - t0
    result["render_stats"]["plan_time"] = round(plan_time, 1)

    plan_path = variant_dir / "plan.json"
    plan_path.write_text(json.dumps(plan, indent=2))
    print(f"  [{label}] Title: {plan['title']} ({len(plan['scenes'])} scenes)")

    # ── Evaluate plan ──
    print(f"  [{label}] Evaluating plan...")
    try:
        plan_eval = evaluate_plan(plan, topic)
        result["plan_scores"] = plan_eval
        (variant_dir / "eval_plan.json").write_text(json.dumps(plan_eval, indent=2))
        print(f"  [{label}] Plan score: {plan_eval.get('overall_score', 'N/A')}")
    except Exception as e:
        print(f"  [{label}] Plan eval failed: {e}")
        result["plan_scores"] = {"error": str(e)}

    # ── Codegen + Render (no voice) ──
    print(f"  [{label}] Generating code + rendering...")

    durations = []
    for scene in plan["scenes"]:
        word_count = len(scene["narration"].split())
        durations.append(word_count / 2.5)

    t0 = time.time()
    code = generate_manim_code(plan, scene_durations=durations)
    codegen_time = time.time() - t0
    result["render_stats"]["codegen_time"] = round(codegen_time, 1)

    code_path = variant_dir / "scenes.py"
    code_path.write_text(code)

    scene_names = get_scene_names(code)
    if not scene_names:
        print(f"  [{label}] ERROR: No scene classes found")
        result["status"] = "codegen_failed"
        return result

    rendered_videos = []
    current_code = code
    t0 = time.time()

    for scene_name in scene_names:
        print(f"  [{label}]   Rendering {scene_name}...")
        video_path, current_code = render_scene(
            code=current_code,
            scene_name=scene_name,
            output_dir=variant_dir,
            code_path=code_path,
            preview=False,
        )
        if video_path:
            rendered_videos.append(video_path)
        else:
            print(f"  [{label}]   FAILED: {scene_name}")

    render_time = time.time() - t0
    result["render_stats"]["render_time"] = round(render_time, 1)
    result["render_stats"]["scenes_total"] = len(scene_names)
    result["render_stats"]["scenes_rendered"] = len(rendered_videos)

    code_path.write_text(current_code)

    if not rendered_videos:
        result["status"] = "render_failed"
        return result

    # Concatenate
    final_path = variant_dir / "final.mp4"
    if len(rendered_videos) == 1:
        shutil.copy2(rendered_videos[0], final_path)
    else:
        concatenate_scenes(rendered_videos, final_path)

    try:
        dur_str = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(final_path)],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        result["render_stats"]["final_duration"] = round(float(dur_str), 1)
    except Exception:
        pass

    # ── Evaluate video ──
    print(f"  [{label}] Evaluating video...")
    frames_dir = variant_dir / "frames"
    save_frames(final_path, frames_dir)

    narration = "\n\n".join(
        f"Scene {s['id']}: {s['narration']}"
        for s in plan.get("scenes", [])
    )

    try:
        video_eval = evaluate_video(final_path, topic, narration)
        result["video_scores"] = video_eval
        (variant_dir / "eval_video.json").write_text(json.dumps(video_eval, indent=2))
        print(f"  [{label}] Video score: {video_eval.get('video_overall_score', 'N/A')}")
    except Exception as e:
        print(f"  [{label}] Video eval failed: {e}")
        result["video_scores"] = {"error": str(e)}

    result["status"] = "completed"
    return result


def get_score(scores: dict | None, key: str) -> float | str:
    if scores and "error" not in scores:
        return scores.get(key, 0)
    return "-"


def print_comparison(results: list[dict]):
    """Print side-by-side A/B comparison."""
    print(f"\n{'#'*80}")
    print(f"RESEARCH A/B COMPARISON")
    print(f"{'#'*80}")

    # Overview table
    print(f"\n{'Topic':<35} {'Base':>5} {'Rsrch':>5} {'Delta':>6} {'Used':>6} {'Srcs':>5}")
    print(f"{'':35} {'Plan':>5} {'Plan':>5} {'':>6} {'Srch?':>6} {'':>5}")
    print("-" * 70)

    plan_deltas = []
    for r in results:
        t = r["topic"][:33]
        bp = get_score(r["baseline"]["plan_scores"], "overall_score")
        rp = get_score(r["research"]["plan_scores"], "overall_score")
        used = "YES" if r["research"]["used_search"] else "no"
        srcs = r["research"]["num_sources"]

        if isinstance(bp, (int, float)) and isinstance(rp, (int, float)):
            delta = rp - bp
            plan_deltas.append(delta)
            delta_str = f"{delta:+.1f}"
        else:
            delta_str = "-"

        bp_str = f"{bp:.1f}" if isinstance(bp, (int, float)) else str(bp)
        rp_str = f"{rp:.1f}" if isinstance(rp, (int, float)) else str(rp)
        print(f"  {t:<35} {bp_str:>5} {rp_str:>5} {delta_str:>6} {used:>6} {srcs:>5}")

    if plan_deltas:
        avg_delta = sum(plan_deltas) / len(plan_deltas)
        print(f"\n  {'AVG PLAN DELTA':<35} {'':>5} {'':>5} {avg_delta:>+6.1f}")

    # Video scores
    print(f"\n{'Topic':<35} {'Base':>5} {'Rsrch':>5} {'Delta':>6}")
    print(f"{'':35} {'Video':>5} {'Video':>5} {'':>6}")
    print("-" * 55)

    video_deltas = []
    for r in results:
        t = r["topic"][:33]
        bv = get_score(r["baseline"]["video_scores"], "video_overall_score")
        rv = get_score(r["research"]["video_scores"], "video_overall_score")

        if isinstance(bv, (int, float)) and isinstance(rv, (int, float)):
            delta = rv - bv
            video_deltas.append(delta)
            delta_str = f"{delta:+.1f}"
        else:
            delta_str = "-"

        bv_str = f"{bv:.1f}" if isinstance(bv, (int, float)) else str(bv)
        rv_str = f"{rv:.1f}" if isinstance(rv, (int, float)) else str(rv)
        print(f"  {t:<35} {bv_str:>5} {rv_str:>5} {delta_str:>6}")

    if video_deltas:
        avg_delta = sum(video_deltas) / len(video_deltas)
        print(f"\n  {'AVG VIDEO DELTA':<35} {'':>5} {'':>5} {avg_delta:>+6.1f}")

    # Detailed plan criteria comparison
    print(f"\n{'─'*80}")
    print("PLAN CRITERIA: BASELINE vs RESEARCH (delta)")
    print(f"{'─'*80}")

    criteria = ["accuracy", "depth", "hook_quality", "narrative_flow",
                "analogy_clarity", "visual_narration_fit", "shareability"]

    header = f"{'Criterion':<25}" + "".join(f"{'T'+str(i+1):>12}" for i in range(len(results))) + f"{'Avg':>10}"
    print(header)
    print("-" * (25 + 12 * len(results) + 10))

    for c in criteria:
        row = f"  {c:<23}"
        deltas = []
        for r in results:
            bp = get_score(r["baseline"]["plan_scores"], c)
            rp = get_score(r["research"]["plan_scores"], c)
            if isinstance(bp, (int, float)) and isinstance(rp, (int, float)):
                d = rp - bp
                deltas.append(d)
                row += f"{d:>+12.1f}"
            else:
                row += f"{'--':>12}"
        if deltas:
            row += f"{sum(deltas)/len(deltas):>+10.1f}"
        print(row)

    # Factual errors comparison
    print(f"\n{'─'*80}")
    print("FACTUAL ERRORS")
    print(f"{'─'*80}")
    for i, r in enumerate(results):
        t = r["topic"][:60]
        be = r["baseline"]["plan_scores"].get("factual_errors", []) if r["baseline"]["plan_scores"] and "error" not in r["baseline"]["plan_scores"] else []
        re_ = r["research"]["plan_scores"].get("factual_errors", []) if r["research"]["plan_scores"] and "error" not in r["research"]["plan_scores"] else []
        print(f"\nT{i+1}: {t}")
        print(f"  Baseline errors ({len(be)}): {be if be else 'none'}")
        print(f"  Research errors ({len(re_)}): {re_ if re_ else 'none'}")
        print(f"  Search used: {'YES' if r['research']['used_search'] else 'NO'} | Sources: {r['research']['num_sources']}")
        if r["research"].get("search_queries"):
            print(f"  Queries: {r['research']['search_queries']}")


def main():
    parser = argparse.ArgumentParser(description="A/B evaluation: baseline vs research-augmented")
    parser.add_argument("--run-name", type=str, default="research_ab_2026-03-22",
                        help="Name for this evaluation run")
    parser.add_argument("--topic-index", type=int, default=None,
                        help="Run only a specific topic by index (0-4)")
    args = parser.parse_args()

    run_dir = RUNS_DIR / args.run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    topics = [AB_TOPICS[args.topic_index]] if args.topic_index is not None else AB_TOPICS
    (run_dir / "topics.json").write_text(json.dumps(topics, indent=2))

    print(f"\n{'#'*80}")
    print(f"RESEARCH A/B EVALUATION: {args.run_name}")
    print(f"Topics: {len(topics)} | Each topic generates 2 videos (baseline + research)")
    print(f"Output: {run_dir}")
    print(f"Mode: no-voice")
    print(f"{'#'*80}")

    for i, t in enumerate(topics):
        print(f"  [{i}] {t['topic'][:65]} ({t['category']})")

    total_start = time.time()
    results = []

    for i, topic_info in enumerate(topics):
        topic = topic_info["topic"]
        slug = slugify(topic)
        topic_dir = run_dir / slug

        print(f"\n\n{'*'*80}")
        print(f"TOPIC {i+1}/{len(topics)}: {topic[:65]}")
        print(f"{'*'*80}")

        topic_result = {
            "topic": topic,
            "category": topic_info["category"],
            "slug": slug,
        }

        # ── Variant A: Baseline (no research) ──
        print(f"\n── VARIANT A: BASELINE ──")
        topic_result["baseline"] = generate_variant(
            topic, topic_info["duration"],
            topic_dir / "baseline",
            use_research=False,
        )

        # ── Variant B: Research-augmented ──
        print(f"\n── VARIANT B: RESEARCH ──")
        topic_result["research"] = generate_variant(
            topic, topic_info["duration"],
            topic_dir / "research",
            use_research=True,
        )

        results.append(topic_result)

        # Save incremental
        (run_dir / "summary.json").write_text(json.dumps({
            "run_name": args.run_name,
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
        "run_name": args.run_name,
        "total_topics": len(topics),
        "completed": len(results),
        "total_time": round(total_time, 1),
        "results": results,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nFull results: {run_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
