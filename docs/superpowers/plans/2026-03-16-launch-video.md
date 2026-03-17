# Curiso Launch Video Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create two 50-60 second launch teaser videos for Curiso (cinematic + minimal vibes) using the existing Manim pipeline with hand-crafted plan JSONs.

**Architecture:** No pipeline code changes. Write two Claude prompts (one per vibe) that generate plan JSONs in the existing planner format. Run them through `python generate.py --from-plan` to produce the videos.

**Tech Stack:** Existing Manim pipeline, Claude API (for plan generation), ElevenLabs (cinematic vibe only), FFmpeg (assembly)

**Spec:** `docs/superpowers/specs/2026-03-16-launch-video-design.md`

---

## File Structure

```
launch_video/                          # New directory at repo root
├── prompts/
│   ├── cinematic.md                   # Claude prompt for cinematic plan generation
│   └── minimal.md                     # Claude prompt for minimal plan generation
├── plan_cinematic.json                # Generated + hand-edited cinematic plan
├── plan_minimal.json                  # Generated + hand-edited minimal plan
└── output/                            # Rendered video output (gitignored)
```

No existing files are modified.

---

### Task 1: Create Directory Structure

**Files:**
- Create: `launch_video/prompts/` (directory)
- Create: `launch_video/output/.gitkeep`

- [ ] **Step 1: Create the directory structure**

```bash
mkdir -p launch_video/prompts launch_video/output
touch launch_video/output/.gitkeep
```

- [ ] **Step 2: Add output to .gitignore**

Append to the existing `.gitignore`:

```
# Launch video rendered output
launch_video/output/*
!launch_video/output/.gitkeep
```

- [ ] **Step 3: Commit**

```bash
git add launch_video/ .gitignore
git commit -m "chore: create launch_video directory structure"
```

---

### Task 2: Write Cinematic Prompt

**Files:**
- Create: `launch_video/prompts/cinematic.md`

This prompt will be used with Claude to generate the cinematic plan JSON. It must instruct Claude to output JSON in the exact format that `generate.py --from-plan` expects (matching `core/planner.py` output: `topic`, `title`, `aha_moment`, `scenes[]` with `id`, `narration`, `animation_description`).

- [ ] **Step 1: Write the cinematic prompt**

Create `launch_video/prompts/cinematic.md` with the following content:

```markdown
# Cinematic Launch Video Prompt

Use this prompt with Claude to generate `plan_cinematic.json`.

## System Prompt

You are a world-class video producer creating a 50-60 second cinematic launch teaser
for Curiso, an AI-powered educational video generator that creates 3Blue1Brown-style
videos from text prompts.

## Tone & Style

- Dramatic, deliberate pacing with building energy
- Short, punchy narrator sentences with breathing room between them
- Think Apple keynote trailer meets 3Blue1Brown
- Total narration: ~110-140 words (~2.5 words/second, ~44-56s of audio)
- The video itself is made with Manim — so it's meta: the product's own technology
  showcases itself

## Narrative Arc (4 scenes, ~55 seconds total)

### Scene 1 — Hook (8-10s, ~20-25 words narration)
- Open with a provocative question about learning/understanding
- Text appears word-by-word via Write() animation in yellow (#FFFF00), centered
- Slow, dramatic delivery. Long pause after the question lands.
- Do NOT mention the product name yet
- Example: "What if you could see any idea... come alive?"

### Scene 2 — The Magic (15-18s, ~35-45 words narration)
- Show the transformation: a text prompt appearing on screen (typewriter style)
- The prompt text then transforms/dissolves into an actual Manim animation
  (e.g., an equation being written, a graph being drawn)
- This is the "wow" moment — the viewer sees input become output
- Narration explains what's happening: turning ideas into visual explanations

### Scene 3 — Proof (15-18s, ~35-45 words narration)
- Rapid succession of 3-4 different Manim animations showing breadth:
  - A calculus derivative or integral being computed
  - A CS concept (neural network diagram, binary tree, etc.)
  - A physics concept (vectors, wave, force diagram)
- Each animation fades in, holds ~3s, fades out
- Narrator lists the domains: "Mathematics. Science. Computer Science. Anything."

### Scene 4 — CTA (8-10s, ~20-25 words narration)
- Everything fades to black
- Product name "Curiso" fades in large, centered, in white
- Tagline appears below in smaller text
- Beat of silence, then narrator delivers the tagline
- End with a brief self.wait(2) hold

## Technical Constraints

- All animations must use Manim Community Edition (2D only)
- Color palette: black bg (#000000), white text, yellow emphasis (#FFFF00),
  blue (#58C4DD), green (#83C167), red (#FC6255)
- All Text() must use font="Avenir", math uses MathTex
- Max 4-5 objects on screen at once
- Safe zone: x=[-6, 6], y=[-3.2, 3.2], use buff=0.7 with .to_edge()
- Animation descriptions must be detailed enough for Manim codegen
  (specify exact animations: Write(), FadeIn(), Transform(), etc.)

## Output Format

Respond with ONLY valid JSON:

```json
{
  "topic": "Curiso Launch Teaser",
  "title": "a short catchy title",
  "aha_moment": "the core message of this teaser",
  "scenes": [
    {
      "id": 1,
      "narration": "exact words the narrator says",
      "animation_description": "detailed Manim animation instructions"
    }
  ]
}
```
```

- [ ] **Step 2: Commit**

```bash
git add launch_video/prompts/cinematic.md
git commit -m "feat: add cinematic launch video prompt"
```

---

### Task 3: Write Minimal Prompt

**Files:**
- Create: `launch_video/prompts/minimal.md`

Similar to cinematic but for the silent/visual-forward vibe. Key differences: no narration (empty strings), duration controlled by explicit `self.wait()` in animation descriptions, 3 scenes instead of 4.

- [ ] **Step 1: Write the minimal prompt**

Create `launch_video/prompts/minimal.md` with the following content:

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add launch_video/prompts/minimal.md
git commit -m "feat: add minimal launch video prompt"
```

---

### Task 4: Generate Cinematic Plan JSON

**Files:**
- Create: `launch_video/plan_cinematic.json`

**Dependencies:** Task 2 (cinematic prompt must exist)

- [ ] **Step 1: Generate the plan using Claude**

Use the prompt from `launch_video/prompts/cinematic.md` to call Claude (Opus recommended for creative quality). This can be done via:
- The Anthropic API directly
- Or by pasting the prompt into a Claude conversation

The output must be valid JSON matching the planner format.

- [ ] **Step 2: Save the generated JSON**

Save the Claude output to `launch_video/plan_cinematic.json`. Verify it has:
- `topic`: string
- `title`: string
- `aha_moment`: string
- `scenes`: array of 4 objects, each with `id` (number), `narration` (string), `animation_description` (string)

- [ ] **Step 3: Validate narration word counts**

Check each scene's narration word count against targets:
- Scene 1 (Hook): ~20-25 words
- Scene 2 (Magic): ~35-45 words
- Scene 3 (Proof): ~35-45 words
- Scene 4 (CTA): ~20-25 words
- Total: ~110-140 words (at 2.5 words/sec ≈ 44-56s of narration — the assembler time-stretches animation to match audio)

Hand-edit narration if word counts are significantly off.

- [ ] **Step 4: Validate animation descriptions**

Review each `animation_description` and verify:
- Uses only valid Manim CE constructs (Write, FadeIn, FadeOut, Transform, Create, MathTex, Text, Axes, etc.)
- No 3D scenes, no external files, no images
- References correct color hex values
- Specifies font="Avenir" for Text()
- Includes self.wait() calls for pacing
- Scene 1 opens with Write() for the hook question in yellow

Hand-edit descriptions if they use unsupported features.

- [ ] **Step 5: Commit**

```bash
git add launch_video/plan_cinematic.json
git commit -m "feat: add cinematic launch video plan"
```

---

### Task 5: Generate Minimal Plan JSON

**Files:**
- Create: `launch_video/plan_minimal.json`

**Dependencies:** Task 3 (minimal prompt must exist)

- [ ] **Step 1: Generate the plan using Claude**

Use the prompt from `launch_video/prompts/minimal.md` to call Claude. The output must be valid JSON matching the planner format.

- [ ] **Step 2: Save the generated JSON**

Save the Claude output to `launch_video/plan_minimal.json`. Verify it has:
- `topic`: string
- `title`: string
- `aha_moment`: string
- `scenes`: array of 3 objects, each with `id` (number), `narration` (string — descriptive placeholder for codegen context, not spoken), `animation_description` (string)

- [ ] **Step 3: Validate self.wait() durations**

Since this is a silent video, duration is entirely controlled by `self.wait()` calls. Check each scene's animation description:
- Scene 1 (Hook + Magic): self.wait() calls should total 15-18 seconds
- Scene 2 (Proof): self.wait() calls should total 20-22 seconds
- Scene 3 (CTA): self.wait() calls should total 10-12 seconds
- Overall total: ~50-55 seconds

Hand-edit if durations are off.

- [ ] **Step 4: Validate animation descriptions**

Same checks as Task 4 Step 4, plus:
- Every scene MUST have explicit self.wait() calls with specific numeric durations
- No references to narration timing (there is none)

- [ ] **Step 5: Handle the narration field for --no-voice**

Verify the pipeline handles `--no-voice` correctly with the narration field populated. Looking at `generate.py:169-179`, when `--no-voice` is set, the pipeline skips voice generation and subtitle burn entirely, just concatenating rendered videos. The narration field is only read during voice generation (step 4), which is skipped. So any placeholder text in narration is fine.

- [ ] **Step 6: Commit**

```bash
git add launch_video/plan_minimal.json
git commit -m "feat: add minimal launch video plan"
```

---

### Task 6: Test Render — Cinematic (Preview Quality)

**Dependencies:** Task 4 (cinematic plan must exist)

- [ ] **Step 1: Run preview render (animation only, no voice)**

```bash
cd /Users/rahul/Documents/projects/new_projects_one/ai_educational_video_generation
python generate.py --from-plan launch_video/plan_cinematic.json --preview --no-voice
```

First pass uses `--no-voice` to skip ElevenLabs (saves API credits during iteration).
This renders codegen → render → concatenate only.
The actual output directory slug depends on `slugify(plan["topic"])` — check the
console output for the exact path.

> **Note:** With `--no-voice` and a single rendered scene, the pipeline uses
> `Path.rename()` which moves (not copies) the scene file. If you need to re-render,
> you'll need to run the full pipeline again.

- [ ] **Step 2: Verify output**

Check the console output for the actual output directory path, then verify:
- All 4 scenes rendered (no skipped scenes)
- `output/<slug>/final.mp4` exists and plays
- Animations look correct (voice will be added in production render)

- [ ] **Step 3: Review generated Manim code**

Open `output/<slug>/scenes.py` and review. If animations need tweaking:
1. Edit `scenes.py` directly
2. Re-render individual scenes: `manim render -ql output/<slug>/scenes.py SceneXX`
3. Re-run assembly steps manually if needed

- [ ] **Step 4: Copy output to launch_video/output/**

Check the actual slug from the console output, then copy:

```bash
# Replace <slug> with the actual directory name from console output
cp -r output/<slug>/ launch_video/output/cinematic/
```

---

### Task 7: Test Render — Minimal (Preview Quality)

**Dependencies:** Task 5 (minimal plan must exist)

- [ ] **Step 1: Run preview render**

```bash
cd /Users/rahul/Documents/projects/new_projects_one/ai_educational_video_generation
python generate.py --from-plan launch_video/plan_minimal.json --preview --no-voice
```

This skips voice and subtitles, just renders and concatenates.
The actual output directory slug depends on `slugify(plan["topic"])` — check the
console output for the exact path.

> **Note:** Same `rename()` caveat as Task 6 applies here.

- [ ] **Step 2: Verify output**

Check that:
- All 3 scenes rendered (no skipped scenes)
- `output/<slug>/final.mp4` exists and plays
- Video is approximately 50-55 seconds (controlled by self.wait() calls)
- No audio (silent video)

- [ ] **Step 3: Review and iterate**

Same as Task 6 Step 3. For the minimal video, pay special attention to:
- Timing feels right without narration (not too fast, not too slow)
- Text is legible and well-positioned
- Animation montage in Scene 2 flows smoothly between subjects

- [ ] **Step 4: Copy output to launch_video/output/**

```bash
# Replace <slug> with the actual directory name from console output
cp -r output/<slug>/ launch_video/output/minimal/
```

---

### Task 8: Final Render (Production Quality)

**Dependencies:** Tasks 6 and 7 (preview renders reviewed and plans adjusted)

Only proceed with this task once you're happy with the preview renders. This produces 720p output (Manim `-qm` default). For 1080p, you would need to modify `core/renderer.py` to use `-qh`, which is out of scope for now.

- [ ] **Step 1: Clean up previous render output**

```bash
# Remove previous preview output to avoid stale files
rm -rf output/curiso_launch_teaser*
```

- [ ] **Step 2: Render cinematic at full quality (with voice)**

```bash
python generate.py --from-plan launch_video/plan_cinematic.json
```

This time voice and subtitles are included. Check console for output directory.

- [ ] **Step 3: Render minimal at full quality**

```bash
python generate.py --from-plan launch_video/plan_minimal.json --no-voice
```

- [ ] **Step 4: Copy final outputs**

```bash
# Replace <slug> with actual directory names from console output
cp -r output/<cinematic-slug>/ launch_video/output/cinematic_final/
cp -r output/<minimal-slug>/ launch_video/output/minimal_final/
```

- [ ] **Step 4: Final commit**

```bash
git add launch_video/
git commit -m "feat: complete launch video plans and prompts"
```
