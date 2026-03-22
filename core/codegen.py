"""
Manim Code Generator — takes a scene plan and generates executable Manim
Python code using Claude. Includes a retry loop for render errors.
"""

import anthropic

DESIGN_SYSTEM = """
## Design System — 3Blue1Brown Style (MUST follow these exactly)

Background color: BLACK "#000000" (pure black, exactly like 3Blue1Brown)

Color palette (use these exact hex values):
  - WHITE "#FFFFFF" for regular body text and axis labels
  - YELLOW_3B1B "#FFFF00" for emphasis text, variable names, key terms
  - BLUE_3B1B "#58C4DD" for primary math objects, secondary equations, highlights
  - GREEN_3B1B "#83C167" for curves, graphs, positive results
  - TEAL_3B1B "#5CD0B3" for secondary curves and accents
  - RED_3B1B "#FC6255" for warnings, negative, error states
  - GREY "#888888" for axis lines, grid lines, subtle elements

Typography:
  - Use MathTex for ALL mathematical expressions (renders with LaTeX — beautiful serif math font)
  - Use Text(font="Avenir") for ALL regular text — always specify font="Avenir"
  - Title text: font_size=40, color YELLOW "#FFFF00" (NOT larger — must fit on screen)
  - Body text: font_size=30
  - Label text: font_size=22
  - Axis labels: font_size=18

Animation style:
  - Use Write() for equations appearing (the classic 3B1B "handwriting" effect)
  - Use FadeIn() for text and labels
  - Use Create() for geometric shapes and graphs
  - Use Transform() and ReplacementTransform() for morphing between objects
  - Use rate_func=smooth for most animations
  - CRITICAL PACING: Use self.wait(2) to self.wait(3) between major steps. Animations feel rushed without enough wait time. The narrator needs time to speak while the visual sits on screen.
  - For Write() animations on text, use run_time=2 or run_time=3 so the text appears slowly, matching narration pace
  - Scene transitions: FadeOut(*self.mobjects) then FadeIn new ones
  - Total scene duration should be AT LEAST 20 seconds. Most narrations are 20-35 seconds long. If your animation is shorter than 20s, add more self.wait() calls.

Layout (CRITICAL — nothing must be cut off):
  - NEVER place objects at the very edge of the screen
  - Use buff=0.7 minimum when using .to_edge() or .next_to()
  - Titles: use .to_edge(UP, buff=0.8) — this keeps them well inside the frame, not hugging the top
  - All content must stay within x=[-6.0, 6.0] and y=[-3.2, 3.2] (safe zone with generous margins)
  - For long titles, use font_size=36 or smaller and check width with .width property
  - If a title might be long, scale it: title.scale_to_fit_width(12) to ensure it fits
  - Center important content using .move_to(ORIGIN)
  - Keep scenes uncluttered — max 4-5 objects visible at once
  - Axes should use x_length and y_length to control size, typically x_length=8, y_length=5
  - Leave space for labels — don't let graphs touch the edges
"""

CODEGEN_SYSTEM_PROMPT = f"""You are an expert Manim Community Edition (manimce) programmer. You write clean, working Manim code that renders beautiful 3Blue1Brown-style educational animations.

{DESIGN_SYSTEM}

## Scene 1 — The Hook (MUST follow this pattern)

Scene01 has TWO phases:

**Phase 1 (first 3-5 seconds): The question**
1. Black screen (self.camera.background_color = "#000000")
2. IMMEDIATELY start the hook question via Write() animation (run_time=2-3) — do NOT add self.wait() before this. The narrator begins speaking at t=0, so the text must start appearing at t=0.
3. After the Write() completes, self.wait(1-2) so the viewer reads it
4. FadeOut the question

**Phase 2 (remaining time): Visual explanation begins**
5. Immediately start showing relevant visuals that match what the narrator is saying for the REST of the scene. Use the animation_description to guide what to show.
6. Build diagrams, show objects appearing, animate concepts — do NOT leave a static screen. The narrator is actively explaining and the visuals should match.

The hook question is just the opening few seconds. Then the scene transitions into real visual content. This is how 3Blue1Brown does it — the question hooks you, then the explanation starts immediately.
If the question is long, split it into two lines or use scale_to_fit_width(12).

## Narration-Animation Sync (CRITICAL)

The narration audio starts playing at EXACTLY t=0 of each scene. Your animations must
match this timing:
- The FIRST visual element MUST appear within 0.3 seconds of scene start. NEVER begin
  a scene with self.wait() — the narrator is already talking while the screen is black.
- Text/equations appear on screen AS the narrator mentions them
- Diagrams build up piece by piece in sync with the narration, not all at once
- When the narrator refers to a specific element, that element should be highlighted or animated
- Use self.wait() to create breathing room BETWEEN concepts — not at the start of scenes
- If you want a dramatic pause, place it AFTER the first visual is on screen, not before
- If the animation finishes before the target duration, add self.wait() at the END to fill
  remaining time — never pad the beginning

## Rules

1. Use Manim Community Edition (manimce) syntax — NOT the original 3b1b manim or manimgl
2. Import from `manim import *` at the top
3. Each scene MUST be a class that extends `Scene`
4. Set the background color in construct(): `self.camera.background_color = "#000000"`
5. Every animation MUST call self.play() — never just create objects without animating them
6. Use self.wait() between animations for pacing
7. Keep scenes self-contained — each scene class should work independently
8. Do NOT use any external files, images, SVGs, or sounds
9. Do NOT use 3D scenes (ThreeDScene, ThreeDAxes, etc.)
10. CRITICAL: All objects must fit on screen with margins. Use .scale_to_fit_width(12) for wide text. Never place anything outside x=[-6.5, 6.5] y=[-3.5, 3.5]
11. Test that object positions don't overlap unless intentional
12. Use VGroup() to group related objects for easier animation
13. Always FadeOut remaining objects at the end of each scene
14. For titles, ALWAYS check if the text is too long. If title.width > 12, scale it down with title.scale_to_fit_width(12)
15. Use buff=0.7 with all .to_edge() and .next_to() calls to prevent edge clipping
16. For Text(), ALWAYS pass font="Avenir" as a parameter

When fixing errors:
- Read the error message carefully
- Common issues: wrong argument names, deprecated methods, objects not added to scene
- MathTex uses LaTeX syntax — escape backslashes properly in Python strings
- Axes() in manimce uses x_range=[min, max, step] not x_min/x_max

Respond with ONLY the Python code, no markdown fences, no explanation."""


def generate_manim_code(
    plan: dict,
    scene_durations: list[float] | None = None,
    visual_blueprint: dict | None = None,
    model: str = "claude-sonnet-4-20250514",
) -> str:
    """Generate Manim code for all scenes in the plan.

    Args:
        plan: The scene plan dict from planner.py.
        scene_durations: Optional list of audio durations (seconds) per scene.
            When provided, codegen will target these exact durations.
        visual_blueprint: Optional visual design blueprint from visual_designer.py.
            When provided, codegen follows the detailed animation steps.
        model: The Claude model to use.

    Returns:
        A string of complete, executable Manim Python code.
    """
    client = anthropic.Anthropic()

    # Build the prompt with all scenes
    scenes_text = ""
    for i, scene in enumerate(plan["scenes"]):
        scenes_text += f"\n### Scene {scene['id']}\n"
        if scene_durations and i < len(scene_durations):
            scenes_text += f"**Audio Duration: {scene_durations[i]:.1f} seconds** (your animation MUST be this long)\n"
        scenes_text += f"**Narration:** {scene['narration']}\n"
        scenes_text += f"**Animation:** {scene['animation_description']}\n"

        # Include visual blueprint if available
        if visual_blueprint:
            bp_scenes = visual_blueprint.get("scenes", [])
            for bp in bp_scenes:
                if bp.get("scene_id") == scene["id"]:
                    scenes_text += f"\n**Visual Blueprint (follow these steps closely):**\n"
                    for step in bp.get("steps", []):
                        scenes_text += f"  - [{step.get('time', '?')}s] {step.get('action', '')}\n"
                        scenes_text += f"    Objects: {step.get('manim_objects', '')}\n"
                        scenes_text += f"    Animation: {step.get('animation', '')}\n"
                    break

    timing_instructions = ""
    if scene_durations:
        timing_instructions = """- CRITICAL TIMING: Each scene has an exact audio duration listed. Your animation for that scene MUST match that duration precisely. Add up your self.play(run_time=X) and self.wait(X) calls to hit the target. For example, if a scene is 24.0 seconds, your animation steps should total 24 seconds.
- Distribute self.wait() calls throughout the scene so visuals stay on screen while the narrator speaks about them. Do NOT front-load all animations and then have one long wait at the end.
- For Scene 1 (the hook), the question stays on screen for most of the scene while the narrator reads the full narration. Use a long self.wait() after the Write() animation."""
    else:
        timing_instructions = """- Each scene's narration will be converted to audio. Narration is spoken at ~2.5 words per second. Count the words in each scene's narration, divide by 2.5, and make the animation AT LEAST that many seconds long.
- Use generous self.wait() calls (1.5-3 seconds) between animation steps."""

    prompt = f"""Generate a complete Manim Python file for this educational video.

**Title:** {plan['title']}
**Topic:** {plan['topic']}

## Scenes
{scenes_text}

Requirements:
- Create one Scene class per scene, named Scene01, Scene02, etc.
{timing_instructions}
- Start the file with `from manim import *`
"""

    response = client.messages.create(
        model=model,
        max_tokens=16384,
        system=CODEGEN_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )

    code = response.content[0].text.strip()

    # If output was truncated (hit max_tokens), the code will be incomplete.
    # Detect this by checking the stop reason and warn/retry.
    if response.stop_reason == "max_tokens":
        print("  WARNING: Code generation hit token limit — output was truncated.")
        print("  Requesting continuation...")
        # Ask Claude to continue from where it left off
        continuation = client.messages.create(
            model=model,
            max_tokens=16384,
            system=CODEGEN_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": code},
                {"role": "user", "content": "Your previous response was cut off. Continue EXACTLY from where you stopped. Output ONLY the remaining Python code, no explanation, no repeated code."},
            ],
        )
        remaining = continuation.content[0].text.strip()
        if remaining.startswith("```"):
            remaining = remaining.split("\n", 1)[1]
            remaining = remaining.rsplit("```", 1)[0]
        code = code + "\n" + remaining

    # Strip markdown fences if the model wrapped it
    if code.startswith("```"):
        code = code.split("\n", 1)[1]
        code = code.rsplit("```", 1)[0]

    return code


def fix_manim_code(code: str, error: str, model: str = "claude-sonnet-4-20250514") -> str:
    """Send broken code + error back to Claude for a fix.

    Args:
        code: The Manim code that failed to render.
        error: The error message from manim render.
        model: The Claude model to use.

    Returns:
        Fixed Manim Python code.
    """
    client = anthropic.Anthropic()

    prompt = f"""This Manim code failed to render. Fix it and return the COMPLETE corrected file.

## Code
```python
{code}
```

## Error
```
{error}
```

Return ONLY the fixed Python code, no explanation."""

    response = client.messages.create(
        model=model,
        max_tokens=16384,
        system=CODEGEN_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": prompt}
        ],
    )

    fixed = response.content[0].text.strip()

    if response.stop_reason == "max_tokens":
        continuation = client.messages.create(
            model=model,
            max_tokens=16384,
            system=CODEGEN_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": fixed},
                {"role": "user", "content": "Your previous response was cut off. Continue EXACTLY from where you stopped. Output ONLY the remaining Python code, no explanation, no repeated code."},
            ],
        )
        remaining = continuation.content[0].text.strip()
        if remaining.startswith("```"):
            remaining = remaining.split("\n", 1)[1]
            remaining = remaining.rsplit("```", 1)[0]
        fixed = fixed + "\n" + remaining

    if fixed.startswith("```"):
        fixed = fixed.split("\n", 1)[1]
        fixed = fixed.rsplit("```", 1)[0]

    return fixed
