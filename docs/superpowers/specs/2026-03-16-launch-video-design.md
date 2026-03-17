# Curiso Launch Video — Design Spec

## Overview

Create two 50-60 second launch/teaser videos for Curiso using the existing Manim-based pipeline. Each video follows the same narrative arc but with a different vibe: **cinematic (hype)** vs **minimal (sleek)**. No pipeline code changes — just hand-tuned plan JSONs run through `--from-plan`.

## Approach

Write a dedicated Claude prompt for each vibe that generates a plan JSON in the existing planner output format. Save the generated plans, hand-edit if needed, then render via `python generate.py --from-plan <plan.json>`.

## Directory Structure

```
launch_video/
├── plan_cinematic.json       # 4-scene cinematic plan (Vibe A)
├── plan_minimal.json         # 3-scene minimal plan (Vibe B)
├── prompts/
│   ├── cinematic.md          # Prompt used to generate cinematic plan
│   └── minimal.md            # Prompt used to generate minimal plan
└── output/                   # Videos moved here after rendering
```

## Narrative Arc (Shared)

Both plans follow a 4-beat structure totaling ~55 seconds (the Minimal vibe combines beats 1-2 into a single scene):

| Beat | Purpose | Duration |
|------|---------|----------|
| Hook | Provocative question that creates curiosity | 8-10s |
| The Magic | Show the transformation — text prompt becomes animated video | 15-18s |
| Proof | Flash examples of what Curiso produces — equations, diagrams, visual explanations | 15-18s |
| CTA | Product name, tagline, call to action | 8-10s |

The hook does not mention the product name. It opens with the desire: the gap between wanting to understand something and seeing it click visually.

The magic beat is the meta moment — Manim animating the concept of "prompt to video." Text appears, transforms into scenes, scenes come alive.

The proof beat shows breadth — math, physics, CS — quick flashes of the kind of content Curiso generates.

The CTA is clean: product name, tagline, URL or "try it now."

## Vibe A — Cinematic / Hype

**Tone:** Dramatic narrator, deliberate pacing, building energy. Short punchy sentences with breathing room. ~60-70 words of narration total.

**Scenes (4):**

1. **Hook (8-10s):** Single question appears word-by-word with Write() animation. Long pause. Narrator asks it slowly. "What if you could see any idea... come alive?"

2. **The Magic (15-18s):** A prompt types itself on screen (typewriter effect), then the text transforms/dissolves into an actual Manim animation — an equation, a graph. The transition is the point.

3. **Proof (15-18s):** Quick succession of animations — a derivative being computed, a neural network diagram lighting up, a physics vector field — each fading in/out with ~3s each. Narrator: "Mathematics. Science. Computer Science. Anything."

4. **CTA (8-10s):** Everything fades to black. Product name fades in large. Tagline below. Beat of silence, then narrator delivers the tagline.

## Vibe B — Minimal / Sleek

**Tone:** Fully silent — no narration at all. Let the visuals speak. Pure text on screen with animations doing the talking. Rendered with `--no-voice`.

**Scenes (3):**

1. **Hook + Magic (15-18s):** Bold text appears: "Learn anything." Holds 2 seconds. Then: "See everything." A topic word (e.g., "Calculus") appears, then morphs into an animated derivative graph being drawn. Duration controlled via `self.wait()` calls in animation description.

2. **Proof (20-22s):** Rapid montage — 4-5 quick Manim animations crossfading, each ~3s. Visuals show range and quality across math, physics, CS. Duration controlled via `self.wait()` calls.

3. **CTA (10-12s):** Clean fade to product name. Single text line tagline. Text only — "Curiso. Try it now." Duration controlled via `self.wait()` calls.

## Plan JSON Format

Uses the existing planner output format:

```json
{
  "topic": "Curiso Launch Teaser",
  "title": "Curiso — See Any Idea Come Alive",
  "aha_moment": "Any concept can become a beautiful visual explanation instantly",
  "scenes": [
    {
      "id": 1,
      "narration": "exact words the narrator says",
      "animation_description": "detailed Manim instructions for codegen"
    }
  ]
}
```

## Technical Constraints

- 2D only, no imported images or videos — everything is Manim-generated
- 4-5 objects max on screen at once
- Safe layout zone: x=[-6, 6], y=[-3.2, 3.2]
- All text uses `font="Avenir"`, math uses `MathTex`
- Color palette: black background (#000000), white text, yellow emphasis (#FFFF00), blue (#58C4DD), green (#83C167), red (#FC6255)
- Codegen retry loop (max 3 attempts) handles render failures automatically
- Target resolution: 1080p (Manim default `-qm`). Use `--preview` (`-ql`) for fast iteration.

## Duration Control

Scene duration is controlled differently depending on the vibe:

- **Cinematic (narrated):** Narration word count drives duration. The assembler time-stretches the animation to match audio length. Target ~2.5 words/second. Per-scene word counts:
  - Hook: ~20-25 words
  - Magic: ~35-45 words
  - Proof: ~35-45 words
  - CTA: ~20-25 words
- **Minimal (silent):** Explicit `self.wait()` calls in the animation description are the only duration control. Animation descriptions must include specific wait durations.

## Codegen Nondeterminism

The animation descriptions are sent to Claude for Manim code generation, which means each render pass may produce slightly different code. For a polished launch video:

1. Run the first render pass to generate `output/<slug>/scenes.py`
2. Review and hand-edit the generated Manim code if needed
3. Re-render from the edited code directly (re-run `manim render` on the fixed `scenes.py`)

## Rendering

```bash
# Cinematic (full narration)
python generate.py --from-plan launch_video/plan_cinematic.json

# Minimal (fully silent, no voice)
python generate.py --from-plan launch_video/plan_minimal.json --no-voice
```

Output is generated under `output/<topic_slug>/` by default. Move to `launch_video/output/` after rendering.

## Deliverables

1. `launch_video/prompts/cinematic.md` — Claude prompt for generating the cinematic plan
2. `launch_video/prompts/minimal.md` — Claude prompt for generating the minimal plan
3. `launch_video/plan_cinematic.json` — 4-scene cinematic plan (generated + hand-edited)
4. `launch_video/plan_minimal.json` — 3-scene minimal plan (generated + hand-edited)
5. `launch_video/output/` — empty directory for rendered video output

## Out of Scope

- No changes to the existing pipeline code
- No new CLI flags (output moved manually)
- No screen recordings or Remotion — pure Manim
- No background music (not currently supported in pipeline)
