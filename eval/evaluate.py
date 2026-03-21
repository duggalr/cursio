#!/usr/bin/env python3
"""
Evaluation framework for Curiso video generation quality.

Generates videos for test topics and uses an LLM as an expert evaluator
to score accuracy, pedagogy, and visual quality.

Usage:
    python eval/evaluate.py                          # Evaluate all categories
    python eval/evaluate.py --category basic         # Evaluate one category
    python eval/evaluate.py --plan-only              # Only generate plans (no rendering)
    python eval/evaluate.py --eval-plan path/to/plan.json  # Evaluate an existing plan
"""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT))

import anthropic

EVAL_DIR = Path(__file__).parent
TEST_TOPICS = EVAL_DIR / "test_topics.json"


def evaluate_plan(plan: dict, topic: str, had_research: bool, research_context: str = "") -> dict:
    """Use an LLM as an expert evaluator to score a video plan.

    Scores:
        - accuracy (1-10): Are the facts correct? Any errors or misleading claims?
        - depth (1-10): Does it go beyond surface-level? Does it build real understanding?
        - pedagogy (1-10): Is the teaching approach effective? Good hook, clear progression, aha moment?
        - visual_design (1-10): Are the animation descriptions well-suited to the content?
        - engagement (1-10): Would a viewer watch the whole thing? Is it genuinely interesting?

    Returns a dict with scores and detailed feedback.
    """
    client = anthropic.Anthropic()

    scenes_text = ""
    for scene in plan.get("scenes", []):
        scenes_text += f"\n### Scene {scene['id']}\n"
        scenes_text += f"**Narration:** {scene['narration']}\n"
        scenes_text += f"**Animation:** {scene['animation_description']}\n"

    research_note = ""
    if had_research and research_context:
        research_note = f"""

## Research Context Used
The following web research was provided to the planner:
{research_context[:2000]}
"""

    prompt = f"""You are an expert educator and content reviewer. Evaluate this educational video plan
for accuracy, teaching quality, and engagement.

## Topic
{topic}

## Video Plan
**Title:** {plan.get('title', 'N/A')}
**Aha Moment:** {plan.get('aha_moment', 'N/A')}

{scenes_text}
{research_note}

## Evaluation Criteria

Score each criterion from 1-10 and provide specific feedback:

1. **Accuracy (1-10):** Are all facts, numbers, and explanations correct? Flag any errors.
2. **Depth (1-10):** Does it build genuine understanding beyond surface-level? Does it explain the "why" not just the "what"?
3. **Pedagogy (1-10):** Is the teaching approach effective? Does it hook the viewer, build progressively, and deliver an aha moment?
4. **Visual Design (1-10):** Are the animation descriptions appropriate? Would the visuals help understanding?
5. **Engagement (1-10):** Would someone watch the full video? Is the narration conversational and interesting?

Also provide:
- **Factual errors:** List any specific inaccuracies (or "None found")
- **Suggestions:** 2-3 specific improvements
- **Overall assessment:** One paragraph summary

Respond with ONLY valid JSON:
{{
    "accuracy": 8,
    "depth": 7,
    "pedagogy": 9,
    "visual_design": 7,
    "engagement": 8,
    "overall_score": 7.8,
    "factual_errors": ["error 1"] or [],
    "suggestions": ["suggestion 1", "suggestion 2"],
    "overall_assessment": "paragraph here"
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    return json.loads(raw)


def run_evaluation(category: str | None = None, plan_only: bool = False):
    """Run evaluation across test topics."""
    from core.research import research_topic
    from core.planner import plan_scenes

    topics_data = json.loads(TEST_TOPICS.read_text())
    results = []

    categories = [category] if category else list(topics_data.keys())

    for cat in categories:
        cat_data = topics_data[cat]
        print(f"\n{'='*60}")
        print(f"Category: {cat.upper()} - {cat_data['description']}")
        print(f"{'='*60}")

        for topic in cat_data["topics"]:
            print(f"\n--- Evaluating: {topic} ---")

            # Research
            print("  Researching...")
            research = research_topic(topic)

            # Plan
            print("  Planning...")
            plan = plan_scenes(
                topic,
                duration="short",
                research_context=research.context if research.needed else "",
                research_sources=research.sources if research.needed else None,
            )

            print(f"  Title: {plan.get('title', 'N/A')}")
            print(f"  Scenes: {len(plan.get('scenes', []))}")
            print(f"  Research used: {research.needed}")
            if research.sources:
                print(f"  Sources: {len(research.sources)}")

            # Evaluate
            print("  Evaluating with LLM...")
            eval_result = evaluate_plan(
                plan=plan,
                topic=topic,
                had_research=research.needed,
                research_context=research.context,
            )

            result = {
                "category": cat,
                "topic": topic,
                "title": plan.get("title"),
                "research_needed": research.needed,
                "num_sources": len(research.sources) if research.sources else 0,
                "scores": {
                    "accuracy": eval_result["accuracy"],
                    "depth": eval_result["depth"],
                    "pedagogy": eval_result["pedagogy"],
                    "visual_design": eval_result["visual_design"],
                    "engagement": eval_result["engagement"],
                    "overall": eval_result["overall_score"],
                },
                "factual_errors": eval_result.get("factual_errors", []),
                "suggestions": eval_result.get("suggestions", []),
                "assessment": eval_result.get("overall_assessment", ""),
            }

            results.append(result)

            # Print summary
            scores = result["scores"]
            print(f"  Scores: accuracy={scores['accuracy']}, depth={scores['depth']}, "
                  f"pedagogy={scores['pedagogy']}, visual={scores['visual_design']}, "
                  f"engagement={scores['engagement']}, overall={scores['overall']}")
            if result["factual_errors"]:
                print(f"  ERRORS: {result['factual_errors']}")

    # Save results
    output_path = EVAL_DIR / "results.json"
    output_path.write_text(json.dumps(results, indent=2))
    print(f"\n\nResults saved to: {output_path}")

    # Print summary table
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"{'Category':<15} {'Topic':<45} {'Overall':<8} {'Accuracy':<8} {'Errors'}")
    print("-" * 90)
    for r in results:
        errors = len(r["factual_errors"])
        error_str = f"{errors} errors" if errors > 0 else "clean"
        print(f"{r['category']:<15} {r['topic'][:43]:<45} {r['scores']['overall']:<8} {r['scores']['accuracy']:<8} {error_str}")

    # Category averages
    print(f"\n{'Category':<15} {'Avg Overall':<12} {'Avg Accuracy':<12} {'Topics Researched'}")
    print("-" * 60)
    for cat in categories:
        cat_results = [r for r in results if r["category"] == cat]
        avg_overall = sum(r["scores"]["overall"] for r in cat_results) / len(cat_results)
        avg_accuracy = sum(r["scores"]["accuracy"] for r in cat_results) / len(cat_results)
        researched = sum(1 for r in cat_results if r["research_needed"])
        print(f"{cat:<15} {avg_overall:<12.1f} {avg_accuracy:<12.1f} {researched}/{len(cat_results)}")


def eval_existing_plan(plan_path: str):
    """Evaluate a single existing plan file."""
    plan = json.loads(Path(plan_path).read_text())
    topic = plan.get("topic", "Unknown topic")

    print(f"Evaluating plan: {plan.get('title', 'N/A')}")
    print(f"Topic: {topic}")

    result = evaluate_plan(plan=plan, topic=topic, had_research=False)

    scores = result
    print(f"\nScores:")
    print(f"  Accuracy:     {scores['accuracy']}/10")
    print(f"  Depth:        {scores['depth']}/10")
    print(f"  Pedagogy:     {scores['pedagogy']}/10")
    print(f"  Visual Design:{scores['visual_design']}/10")
    print(f"  Engagement:   {scores['engagement']}/10")
    print(f"  Overall:      {scores['overall_score']}/10")
    print(f"\nFactual errors: {scores.get('factual_errors', [])}")
    print(f"\nSuggestions:")
    for s in scores.get("suggestions", []):
        print(f"  - {s}")
    print(f"\nAssessment: {scores.get('overall_assessment', '')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Curiso video generation quality")
    parser.add_argument("--category", type=str, help="Evaluate only this category")
    parser.add_argument("--plan-only", action="store_true", help="Only generate plans, no rendering")
    parser.add_argument("--eval-plan", type=str, help="Evaluate an existing plan.json file")
    args = parser.parse_args()

    if args.eval_plan:
        eval_existing_plan(args.eval_plan)
    else:
        run_evaluation(category=args.category, plan_only=args.plan_only)
