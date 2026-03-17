# Minimal Launch Video Prompt

Use this prompt with Claude to generate `plan_minimal.json`.

## System Prompt

You are a world-class motion designer creating a 50-60 second minimal, sleek launch
teaser for Curiso, an AI-powered educational video generator that creates
3Blue1Brown-style videos from text prompts.

## Tone & Style

- Fully silent — zero narration. The visuals ARE the message.
- Sleek, confident, fast-paced
- Bold text statements on screen replace voiceover
- Let the quality of the Manim animations speak for itself
- Will be rendered with --no-voice flag

## Narrative Arc (3 scenes, ~55 seconds total)

### Scene 1 — Hook + Magic (15-18s)
- Open with bold text: "Learn anything." — appears via FadeIn(), centered, white,
  font_size=44. Hold with self.wait(2).
- Below it: "See everything." — appears via FadeIn(). Hold with self.wait(1.5).
- Both texts FadeOut.
- A topic word appears (e.g., "Calculus" in yellow) — then transforms/morphs into
  an actual Manim animation (e.g., the word dissolves and a derivative graph is
  drawn in its place using Create() and Write())
- This scene must include explicit self.wait() calls totaling 15-18 seconds

### Scene 2 — Proof Montage (20-22s)
- Rapid-fire showcase of 4-5 different Manim animations, each ~3-4 seconds:
  1. A mathematical equation being written (Write() animation)
  2. A coordinate system with a function being plotted (Create() + graph)
  3. A CS diagram — nodes and arrows, data flowing (boxes, arrows, highlights)
  4. A physics visualization — vectors or wave pattern
  5. (Optional) An economics chart or timeline
- Each animation fades in, holds briefly, fades out before the next
- No text labels needed — the visuals speak for themselves
- This scene must include explicit self.wait() calls totaling 20-22 seconds

### Scene 3 — CTA (10-12s)
- Everything fades to black. self.wait(1).
- "Curiso" appears large, centered, white, font_size=48, via FadeIn(). self.wait(2).
- Tagline appears below in smaller text (font_size=28), via FadeIn(). self.wait(1).
- Below tagline: "Try it now." in yellow (#FFFF00), font_size=24. self.wait(1).
- Hold final frame: self.wait(3).
- This scene must include explicit self.wait() calls totaling 10-12 seconds

## Technical Constraints

- All animations must use Manim Community Edition (2D only)
- Color palette: black bg (#000000), white text, yellow emphasis (#FFFF00),
  blue (#58C4DD), green (#83C167), red (#FC6255)
- All Text() must use font="Avenir", math uses MathTex
- Max 4-5 objects on screen at once
- Safe zone: x=[-6, 6], y=[-3.2, 3.2], use buff=0.7 with .to_edge()
- CRITICAL: Every scene must include explicit self.wait() calls with specific
  durations. These are the ONLY way to control scene length (no narration audio
  to drive timing).
- Animation descriptions must specify exact self.wait() durations

## Output Format

Respond with ONLY valid JSON. Since this is a silent video, all narration fields
should contain a brief description of what's happening visually (this text is NOT
spoken aloud — the --no-voice flag skips TTS — but it IS passed to the code
generator as context, so make it descriptive enough to guide the animation code).
Example: "Bold text 'Learn anything' fades in, holds, then morphs into a graph":

```json
{
  "topic": "Curiso Launch Teaser Minimal",
  "title": "a short catchy title",
  "aha_moment": "the core message of this teaser",
  "scenes": [
    {
      "id": 1,
      "narration": "Brief visual description for codegen context (not spoken)",
      "animation_description": "detailed Manim animation instructions with explicit self.wait() durations"
    }
  ]
}
```
