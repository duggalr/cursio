#!/usr/bin/env python3
"""
Evaluation pipeline for Curiso video generation quality.

End-to-end A/B evaluation:
  1. Generate two plans per topic (baseline vs research-augmented)
  2. Score plans blind on 7 criteria
  3. Generate videos for plans scoring > 6
  4. Score videos multimodally (frames + transcript)
  5. Produce comparison report

Usage:
    python eval/evaluate.py --topic "Why does hot air rise?"                  # Single topic
    python eval/evaluate.py --category fundamental_science                    # Full category
    python eval/evaluate.py --category deep_learning --plan-only             # Plans only, no video
    python eval/evaluate.py --eval-video output/some_topic/final.mp4         # Evaluate existing video
    python eval/evaluate.py --eval-plan output/some_topic/plan.json          # Evaluate existing plan
"""

import argparse
import base64
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT))

import anthropic

EVAL_DIR = Path(__file__).parent
TEST_TOPICS = EVAL_DIR / "test_topics.json"
RESULTS_DIR = EVAL_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)


# ─── Plan Evaluation ────────────────────────────────────────────────────

PLAN_EVAL_PROMPT = """You are an expert educator, content strategist, and video producer reviewing an educational video script. Evaluate this plan as if you were deciding whether to greenlight production.

## Topic
{topic}

## Video Plan
**Title:** {title}
**Aha Moment:** {aha_moment}

{scenes_text}

## Score each criterion from 1-10 with specific justification:

1. **Accuracy (1-10):** Are all facts, numbers, equations, and explanations correct? Would an expert find errors?
   - 10: Flawless, expert-level precision
   - 7: Mostly correct, minor imprecisions
   - 4: Several errors that could confuse learners
   - 1: Fundamentally wrong

2. **Depth (1-10):** Does it explain the "why" behind the "what"? Could the viewer explain this to someone else after watching?
   - 10: Builds a complete mental model
   - 7: Good understanding of the core mechanism
   - 4: States facts without explaining why
   - 1: Superficial summary

3. **Hook Quality (1-10):** Does the opening grab attention in the first 5 seconds? Would someone scrolling stop to watch?
   - 10: Irresistible, makes you need to know the answer
   - 7: Interesting enough to keep watching
   - 4: Generic "today we'll learn about X"
   - 1: Would scroll past

4. **Narrative Flow (1-10):** Does each scene build naturally on the previous one? Does it feel like a story with a payoff?
   - 10: Every scene flows perfectly, feels like a journey
   - 7: Good progression with minor jumps
   - 4: Feels like a list of facts
   - 1: Disjointed

5. **Clarity of Analogies (1-10):** Are metaphors creative, memorable, and accurate? Do they make the concept click?
   - 10: Brilliant analogy that creates instant understanding
   - 7: Solid analogy that helps
   - 4: Generic or slightly confusing
   - 1: No analogies or misleading ones

6. **Visual-Narration Fit (1-10):** Do the described animations support understanding? Would visuals and narration enhance each other?
   - 10: Inseparable, each enhances the other
   - 7: Visuals generally support narration
   - 4: Visuals are decorative
   - 1: Visuals contradict narration

7. **Shareability (1-10):** Would someone send this to a friend? Does it make you feel smarter?
   - 10: Immediately shareable, "you have to see this"
   - 7: Worth recommending
   - 4: Informative but not exciting
   - 1: Forgettable

Respond with ONLY valid JSON:
{{
    "accuracy": 8,
    "depth": 7,
    "hook_quality": 9,
    "narrative_flow": 8,
    "analogy_clarity": 7,
    "visual_narration_fit": 8,
    "shareability": 7,
    "overall_score": 7.7,
    "factual_errors": [],
    "best_moment": "description of strongest part",
    "weakest_moment": "description of part needing most work",
    "suggestions": ["suggestion 1", "suggestion 2"]
}}"""


def evaluate_plan(plan: dict, topic: str) -> dict:
    """Score a video plan on 7 criteria."""
    client = anthropic.Anthropic()

    scenes_text = ""
    for scene in plan.get("scenes", []):
        scenes_text += f"\n### Scene {scene['id']}\n"
        scenes_text += f"**Narration:** {scene['narration']}\n"
        scenes_text += f"**Animation:** {scene['animation_description']}\n"

    prompt = PLAN_EVAL_PROMPT.format(
        topic=topic,
        title=plan.get("title", "N/A"),
        aha_moment=plan.get("aha_moment", "N/A"),
        scenes_text=scenes_text,
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    return json.loads(raw)


# ─── Video Evaluation (Multimodal) ──────────────────────────────────────

VIDEO_EVAL_PROMPT = """You are watching an AI-generated educational video. I'm showing you frames extracted every 5 seconds along with the full narration script. Evaluate the actual viewing experience.

## Topic
{topic}

## Narration Script
{narration}

## What you're seeing
The images are frames from the video, extracted every 5 seconds in chronological order. Together with the narration, this represents what a viewer would experience.

## Score each criterion from 1-10:

1. **Visual Clarity (1-10):** Is text readable? Are diagrams clean? Any overlapping objects, cut-off text, or visual clutter?
   - 10: Crystal clear, everything perfectly placed
   - 7: Mostly clean, minor issues
   - 4: Several readability problems
   - 1: Messy, can't read key text

2. **Animation Quality (1-10):** Do the visuals look intentional and professional? Or do they feel broken/janky?
   - 10: Smooth, polished, 3Blue1Brown quality
   - 7: Good quality, minor rough edges
   - 4: Noticeable rendering issues
   - 1: Broken or ugly

3. **Audio-Visual Sync (1-10):** Based on the frames and narration timing, does what you see match what the narrator would be saying at each moment?
   - 10: Perfect sync, visuals illustrate exactly what's being said
   - 7: Mostly in sync with minor gaps
   - 4: Frequent mismatches
   - 1: Visuals and narration seem unrelated

4. **Pacing (1-10):** Based on the density of visual changes across frames, does it feel rushed, dragging, or just right?
   - 10: Perfect rhythm, enough time to absorb each concept
   - 7: Generally good pacing
   - 4: Too fast or too slow in several places
   - 1: Unwatchable pacing

5. **Watch-Through Rate (1-10):** Looking at these frames and the narration, would you actually watch this entire video without skipping?
   - 10: Captivating start to finish
   - 7: Would watch most of it
   - 4: Would skip ahead
   - 1: Would close immediately

Respond with ONLY valid JSON:
{{
    "visual_clarity": 8,
    "animation_quality": 7,
    "audio_visual_sync": 8,
    "pacing": 7,
    "watch_through": 8,
    "video_overall_score": 7.6,
    "visual_issues": ["specific issue 1"],
    "best_visual_moment": "description",
    "worst_visual_moment": "description",
    "suggestions": ["suggestion 1", "suggestion 2"]
}}"""


def extract_frames(video_path: Path, interval: float = 5.0) -> list[str]:
    """Extract frames from video every N seconds, return as base64 strings."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        subprocess.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(video_path),
                "-vf", f"fps=1/{interval}",
                "-q:v", "3",
                str(tmp / "frame_%03d.jpg"),
            ],
            capture_output=True, timeout=60,
        )

        frames = []
        for frame_path in sorted(tmp.glob("frame_*.jpg")):
            with open(frame_path, "rb") as f:
                frames.append(base64.standard_b64encode(f.read()).decode())

    return frames


def evaluate_video(video_path: Path, topic: str, narration: str) -> dict:
    """Score a video multimodally using extracted frames."""
    client = anthropic.Anthropic()

    frames = extract_frames(video_path)
    if not frames:
        return {"error": "Could not extract frames"}

    # Build multimodal message with frames
    content = []
    content.append({
        "type": "text",
        "text": VIDEO_EVAL_PROMPT.format(topic=topic, narration=narration),
    })

    for i, frame_b64 in enumerate(frames):
        content.append({
            "type": "text",
            "text": f"\nFrame at {i * 5}s:",
        })
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": frame_b64,
            },
        })

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[{"role": "user", "content": content}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    return json.loads(raw)


# ─── Full Pipeline ──────────────────────────────────────────────────────

def generate_plan(topic: str, duration: str, use_research: bool) -> tuple[dict, str]:
    """Generate a plan, optionally with research. Returns (plan, research_context)."""
    from core.planner import plan_scenes
    from core.research import research_topic

    research_context = ""
    research_sources = None

    if use_research:
        research = research_topic(topic)
        if research.needed:
            research_context = research.context
            research_sources = research.sources

    plan = plan_scenes(
        topic,
        duration=duration,
        research_context=research_context,
        research_sources=research_sources,
    )

    return plan, research_context


def generate_video(topic: str, duration: str, plan: dict) -> Path | None:
    """Generate a full video from a plan. Returns path to final.mp4."""
    import re
    from core.codegen import generate_manim_code
    from core.renderer import render_scene, get_scene_names
    from core.voice import generate_voice, get_audio_duration
    from core.assembler import combine_scene, concatenate_scenes

    def slugify(text: str) -> str:
        slug = re.sub(r"[^\w\s-]", "", text.lower())
        return re.sub(r"[-\s]+", "_", slug).strip("_")[:60]

    out_dir = PROJECT_ROOT / "output" / f"eval_{slugify(plan['topic'])}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Save plan
    (out_dir / "plan.json").write_text(json.dumps(plan, indent=2))

    # Voice first
    audio_files = []
    durations = []
    for i, scene in enumerate(plan["scenes"]):
        audio_path = out_dir / f"scene_{i+1:02d}.mp3"
        generate_voice(scene["narration"], audio_path)
        dur = get_audio_duration(audio_path)
        audio_files.append(audio_path)
        durations.append(dur)

    # Codegen with durations
    code = generate_manim_code(plan, scene_durations=durations)
    code_path = out_dir / "scenes.py"
    code_path.write_text(code)

    scene_names = get_scene_names(code)
    if not scene_names:
        return None

    # Render
    rendered = []
    current_code = code
    for scene_name in scene_names:
        video_path, current_code = render_scene(
            code=current_code,
            scene_name=scene_name,
            output_dir=out_dir,
            code_path=code_path,
            preview=False,
        )
        if video_path:
            rendered.append(video_path)

    if not rendered:
        return None

    code_path.write_text(current_code)

    # Assemble
    combined = []
    for i, (video, audio) in enumerate(zip(rendered, audio_files)):
        combined_path = out_dir / f"combined_{i+1:02d}.mp4"
        combine_scene(video, audio, combined_path)
        combined.append(combined_path)

    final_path = out_dir / "final.mp4"
    if len(combined) == 1:
        combined[0].rename(final_path)
    else:
        concatenate_scenes(combined, final_path)

    return final_path


def run_single_topic(topic: str, duration: str = "short", plan_only: bool = False):
    """Run full A/B evaluation on a single topic."""
    print(f"\n{'='*70}")
    print(f"EVALUATING: {topic}")
    print(f"Duration: {duration}")
    print(f"{'='*70}")

    # ── Plan A: Baseline (no research) ──
    print(f"\n[A] Generating BASELINE plan...")
    plan_a, _ = generate_plan(topic, duration, use_research=False)
    print(f"    Title: {plan_a.get('title')}")
    print(f"    Scenes: {len(plan_a.get('scenes', []))}")

    print(f"[A] Evaluating plan...")
    eval_a_plan = evaluate_plan(plan_a, topic)
    print(f"    Plan score: {eval_a_plan['overall_score']}")

    # ── Plan B: Research-augmented ──
    print(f"\n[B] Generating RESEARCH-AUGMENTED plan...")
    plan_b, research_ctx = generate_plan(topic, duration, use_research=True)
    print(f"    Title: {plan_b.get('title')}")
    print(f"    Scenes: {len(plan_b.get('scenes', []))}")
    print(f"    Research context: {'yes' if research_ctx else 'no (not needed)'}")

    print(f"[B] Evaluating plan...")
    eval_b_plan = evaluate_plan(plan_b, topic)
    print(f"    Plan score: {eval_b_plan['overall_score']}")

    result = {
        "topic": topic,
        "duration": duration,
        "baseline": {
            "plan": plan_a,
            "plan_scores": eval_a_plan,
        },
        "research": {
            "plan": plan_b,
            "plan_scores": eval_b_plan,
            "had_research_context": bool(research_ctx),
        },
    }

    # ── Generate and evaluate videos ──
    if not plan_only:
        for variant, label, plan, plan_score in [
            ("baseline", "A", plan_a, eval_a_plan),
            ("research", "B", plan_b, eval_b_plan),
        ]:
            if plan_score["overall_score"] < 5.0:
                print(f"\n[{label}] Skipping video generation (plan score {plan_score['overall_score']} < 5.0)")
                continue

            print(f"\n[{label}] Generating video...")
            video_path = generate_video(topic, duration, plan)

            if video_path and video_path.exists():
                print(f"[{label}] Video: {video_path}")
                result[variant]["video_path"] = str(video_path)

                # Build narration for video eval
                narration = "\n\n".join(
                    f"Scene {s['id']}: {s['narration']}"
                    for s in plan.get("scenes", [])
                )

                print(f"[{label}] Evaluating video (multimodal)...")
                eval_video = evaluate_video(video_path, topic, narration)
                result[variant]["video_scores"] = eval_video
                print(f"    Video score: {eval_video.get('video_overall_score', 'N/A')}")
            else:
                print(f"[{label}] Video generation failed")
                result[variant]["video_path"] = None
                result[variant]["video_scores"] = {"error": "generation failed"}

    # ── Print comparison ──
    print(f"\n{'='*70}")
    print(f"COMPARISON: {topic}")
    print(f"{'='*70}")

    print(f"\n{'Criterion':<25} {'Baseline':>10} {'Research':>10} {'Delta':>10}")
    print("-" * 55)

    plan_criteria = [
        "accuracy", "depth", "hook_quality", "narrative_flow",
        "analogy_clarity", "visual_narration_fit", "shareability", "overall_score",
    ]
    for c in plan_criteria:
        a_val = eval_a_plan.get(c, 0)
        b_val = eval_b_plan.get(c, 0)
        delta = b_val - a_val
        delta_str = f"+{delta:.1f}" if delta > 0 else f"{delta:.1f}"
        marker = " ***" if abs(delta) >= 2 else ""
        print(f"  {c:<23} {a_val:>10.1f} {b_val:>10.1f} {delta_str:>10}{marker}")

    if not plan_only:
        video_criteria = [
            "visual_clarity", "animation_quality", "audio_visual_sync",
            "pacing", "watch_through", "video_overall_score",
        ]
        a_vid = result["baseline"].get("video_scores", {})
        b_vid = result["research"].get("video_scores", {})
        if a_vid and b_vid and "error" not in a_vid and "error" not in b_vid:
            print(f"\n{'Video Criterion':<25} {'Baseline':>10} {'Research':>10} {'Delta':>10}")
            print("-" * 55)
            for c in video_criteria:
                a_val = a_vid.get(c, 0)
                b_val = b_vid.get(c, 0)
                delta = b_val - a_val
                delta_str = f"+{delta:.1f}" if delta > 0 else f"{delta:.1f}"
                print(f"  {c:<23} {a_val:>10.1f} {b_val:>10.1f} {delta_str:>10}")

    # Errors comparison
    a_errors = eval_a_plan.get("factual_errors", [])
    b_errors = eval_b_plan.get("factual_errors", [])
    print(f"\nFactual errors:  Baseline={len(a_errors)}, Research={len(b_errors)}")
    if a_errors:
        print(f"  Baseline errors: {a_errors}")
    if b_errors:
        print(f"  Research errors: {b_errors}")

    # Save result
    import re
    slug = re.sub(r"[^\w\s-]", "", topic.lower())
    slug = re.sub(r"[-\s]+", "_", slug).strip("_")[:60]
    result_path = RESULTS_DIR / f"{slug}.json"
    result_path.write_text(json.dumps(result, indent=2, default=str))
    print(f"\nResult saved: {result_path}")

    return result


def run_category(category: str, plan_only: bool = False):
    """Run A/B evaluation for all topics in a category."""
    topics_data = json.loads(TEST_TOPICS.read_text())

    if category not in topics_data:
        print(f"Unknown category: {category}")
        print(f"Available: {', '.join(topics_data.keys())}")
        return

    cat_data = topics_data[category]
    print(f"\n{'#'*70}")
    print(f"CATEGORY: {category.upper()}")
    print(f"{cat_data['description']}")
    print(f"{'#'*70}")

    results = []
    for item in cat_data["topics"]:
        topic = item["topic"] if isinstance(item, dict) else item
        duration = item.get("duration", "short") if isinstance(item, dict) else "short"

        result = run_single_topic(topic, duration, plan_only)
        results.append(result)

    # Category summary
    print(f"\n{'#'*70}")
    print(f"CATEGORY SUMMARY: {category.upper()}")
    print(f"{'#'*70}")

    print(f"\n{'Topic':<50} {'Base':>6} {'Rsrch':>6} {'Delta':>6}")
    print("-" * 70)
    for r in results:
        base = r["baseline"]["plan_scores"]["overall_score"]
        rsrch = r["research"]["plan_scores"]["overall_score"]
        delta = rsrch - base
        delta_str = f"+{delta:.1f}" if delta > 0 else f"{delta:.1f}"
        print(f"  {r['topic'][:48]:<50} {base:>6.1f} {rsrch:>6.1f} {delta_str:>6}")

    avg_base = sum(r["baseline"]["plan_scores"]["overall_score"] for r in results) / len(results)
    avg_rsrch = sum(r["research"]["plan_scores"]["overall_score"] for r in results) / len(results)
    avg_delta = avg_rsrch - avg_base
    print(f"\n  {'AVERAGE':<50} {avg_base:>6.1f} {avg_rsrch:>6.1f} {avg_delta:>+6.1f}")


def eval_existing_plan(plan_path: str):
    """Evaluate a single existing plan file."""
    plan = json.loads(Path(plan_path).read_text())
    topic = plan.get("topic", "Unknown topic")

    print(f"Evaluating plan: {plan.get('title', 'N/A')}")
    result = evaluate_plan(plan, topic)

    print(f"\n{'Criterion':<25} {'Score':>6}")
    print("-" * 35)
    for key in ["accuracy", "depth", "hook_quality", "narrative_flow",
                "analogy_clarity", "visual_narration_fit", "shareability", "overall_score"]:
        print(f"  {key:<23} {result.get(key, 0):>6.1f}")
    print(f"\nFactual errors: {result.get('factual_errors', [])}")
    print(f"Best moment: {result.get('best_moment', '')}")
    print(f"Weakest moment: {result.get('weakest_moment', '')}")
    for s in result.get("suggestions", []):
        print(f"  - {s}")


def eval_existing_video(video_path: str):
    """Evaluate an existing video file multimodally."""
    video_path = Path(video_path)
    if not video_path.exists():
        print(f"Video not found: {video_path}")
        return

    # Try to load plan for narration
    plan_path = video_path.parent / "plan.json"
    narration = ""
    topic = "Unknown"
    if plan_path.exists():
        plan = json.loads(plan_path.read_text())
        topic = plan.get("topic", "Unknown")
        narration = "\n\n".join(
            f"Scene {s['id']}: {s['narration']}"
            for s in plan.get("scenes", [])
        )

    print(f"Evaluating video: {video_path}")
    print(f"Topic: {topic}")
    print(f"Extracting frames...")

    result = evaluate_video(video_path, topic, narration)

    if "error" in result:
        print(f"Error: {result['error']}")
        return

    print(f"\n{'Criterion':<25} {'Score':>6}")
    print("-" * 35)
    for key in ["visual_clarity", "animation_quality", "audio_visual_sync",
                "pacing", "watch_through", "video_overall_score"]:
        print(f"  {key:<23} {result.get(key, 0):>6.1f}")
    print(f"\nVisual issues: {result.get('visual_issues', [])}")
    print(f"Best moment: {result.get('best_visual_moment', '')}")
    print(f"Worst moment: {result.get('worst_visual_moment', '')}")
    for s in result.get("suggestions", []):
        print(f"  - {s}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Curiso video generation quality")
    parser.add_argument("--topic", type=str, help="Evaluate a single topic")
    parser.add_argument("--duration", type=str, default="short", help="Duration for single topic")
    parser.add_argument("--category", type=str, help="Evaluate all topics in a category")
    parser.add_argument("--plan-only", action="store_true", help="Only evaluate plans, skip video generation")
    parser.add_argument("--eval-plan", type=str, help="Evaluate an existing plan.json")
    parser.add_argument("--eval-video", type=str, help="Evaluate an existing video file")
    args = parser.parse_args()

    if args.eval_plan:
        eval_existing_plan(args.eval_plan)
    elif args.eval_video:
        eval_existing_video(args.eval_video)
    elif args.topic:
        run_single_topic(args.topic, args.duration, args.plan_only)
    elif args.category:
        run_category(args.category, args.plan_only)
    else:
        print("Provide --topic, --category, --eval-plan, or --eval-video")
        print("Example: python eval/evaluate.py --topic 'Why does hot air rise?' --plan-only")
