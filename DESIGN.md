# AI Educational Video Generator — V1 Design

## Overview

A CLI tool that takes a topic prompt (e.g. "explain the derivative") and outputs a polished 3Blue1Brown-style educational video with voiceover and subtitles.

## Pipeline Architecture

```
"Explain the derivative"
        ↓
┌─── 1. PLANNER (Claude) ───────────────────────────────┐
│  Takes your topic, asks Claude to write a 3-5 scene   │
│  script with narration text + animation descriptions   │
│  Output: plan.json                                     │
└────────────────────────────────────────────────────────┘
        ↓
┌─── 2. CODE GENERATOR (Claude) ────────────────────────┐
│  Takes the plan, asks Claude to write Manim Python     │
│  code for each scene (with the 3B1B design system      │
│  baked into the prompt — colors, fonts, animation      │
│  style). If code fails to render, sends the error      │
│  back to Claude for a fix (up to 3 retries).           │
│  Output: scenes.py                                     │
└────────────────────────────────────────────────────────┘
        ↓
┌─── 3. RENDERER (Manim) ──────────────────────────────-┐
│  Runs `manim render` on the generated Python code.     │
│  Manim is the actual animation engine 3Blue1Brown      │
│  uses — it renders pixel-perfect math animations,      │
│  equations, graphs, geometric shapes into video.       │
│  Output: scene_01.mp4, scene_02.mp4, ...               │
└────────────────────────────────────────────────────────┘
        ↓
┌─── 4. VOICE (ElevenLabs) ────────────────────────────-┐
│  Sends each scene's narration text to ElevenLabs TTS.  │
│  Returns natural-sounding spoken audio.                │
│  Output: scene_01.mp3, scene_02.mp3, ...               │
└────────────────────────────────────────────────────────┘
        ↓
┌─── 5. SUBTITLES ─────────────────────────────────────-┐
│  Takes narration text + audio durations, generates     │
│  timed .srt captions with word wrapping.               │
│  Output: subtitles.srt                                 │
└────────────────────────────────────────────────────────┘
        ↓
┌─── 6. ASSEMBLER (FFmpeg) ────────────────────────────-┐
│  - Syncs each animation to its voiceover (stretches/   │
│    compresses video to match audio duration)            │
│  - Concatenates all scenes into one video               │
│  - Burns subtitles into the video                       │
│  Output: final.mp4                                     │
└────────────────────────────────────────────────────────┘
```

The key insight is that we're **not** using AI to generate video pixels — we're using AI (Claude) to **write code**, and then Manim (a real animation engine) renders that code into pixel-perfect animations. That's why the math, equations, and text are always crisp and correct.

## Components

### 1. Scene Planner (`planner.py`)

- Takes a topic prompt, sends it to Claude with a system prompt that says "break this into 3-5 scenes, each with narration text and a description of what the animation should show"
- Output: JSON with scenes array, each containing `narration` and `animation_description`
- This is the "script" — separated from code generation so we can review/edit it before rendering

### 2. Manim Code Generator (`codegen.py`)

- Takes the scene plan, sends each scene to Claude with a system prompt containing Manim best practices, the design system (colors, fonts, animation style), and examples
- Includes a **retry loop**: if Manim fails to render, sends the error back to Claude for a fix (max 3 retries)
- Output: A single `.py` file with Manim Scene classes

### 3. Renderer (`renderer.py`)

- Runs `manim render` on the generated code
- Captures stderr for error feedback to the retry loop
- Output: `.mp4` per scene

### 4. Voice Generator (`voice.py`)

- Sends each scene's narration to ElevenLabs TTS API
- Configurable voice ID (default: a clear, professional narrator voice)
- Output: `.mp3` per scene

### 5. Subtitle Generator (`subtitles.py`)

- Takes narration text + audio duration per scene
- Generates `.srt` file with timed captions
- Word-wraps at sensible lengths

### 6. Assembler (`assembler.py`)

- FFmpeg: combines animation + voiceover per scene, then concatenates all scenes
- Burns in subtitles (using FFmpeg `ass`/`srt` filter with styled font)
- Output: `final.mp4`

### 7. CLI Entry Point (`generate.py`)

```bash
# Full pipeline
python generate.py "Explain the derivative"

# Just output the scene plan for review
python generate.py --topic "InfiniBand partitioning" --scenes-only

# Skip planning, generate from an existing/edited plan
python generate.py --from-plan scenes.json

# Pick an ElevenLabs voice
python generate.py "Explain recursion" --voice "Adam"

# Video only, no voiceover
python generate.py "Explain recursion" --no-voice

# Faster, lower-quality render for previewing
python generate.py "Explain recursion" --preview
```

## Design System

Baked into the Claude system prompt for Manim code generation.

| Element | Value |
|---------|-------|
| Background | `#1C1C2E` (dark blue-gray, classic 3B1B) |
| Primary text | `#FFFFFF` (white) |
| Yellow accent | `#FFFF00` (emphasis, highlights) |
| Blue accent | `#58C4DD` (3B1B signature blue) |
| Green accent | `#83C167` (positive, correct) |
| Red accent | `#FC6255` (negative, warning) |
| Math font | CMU Serif (via LaTeX / MathTex) |
| Text font | Source Sans Pro |
| Animations | `Write`, `FadeIn`, `Transform` with `smooth` / `ease_in_out_cubic` rate functions |
| Equation rendering | LaTeX via `MathTex` with consistent sizing |
| Scene transitions | `FadeOut` all → `FadeIn` next (clean, not flashy) |

## Tech Stack

| Dependency | Purpose |
|------------|---------|
| Python 3.11+ | Runtime |
| Manim Community Edition (`manimce`) | Animation rendering |
| Anthropic SDK (`anthropic`) | Scene planning + code generation (Claude) |
| ElevenLabs SDK (`elevenlabs`) | Text-to-speech narration |
| FFmpeg | Final assembly (video + audio + subtitles) |
| python-dotenv | API key management |

## Configuration

### `.env`

```
ANTHROPIC_API_KEY=your-key
ELEVENLABS_API_KEY=your-key
ELEVENLABS_VOICE_ID=optional-override
```

## Output Structure

Each generation run produces a self-contained directory:

```
output/
  {topic_slug}/
    plan.json          # Scene plan (editable, re-runnable)
    scene_01.py        # Generated Manim code
    scene_01.mp4       # Rendered animation
    scene_01.mp3       # Voiceover audio
    scene_02.py
    scene_02.mp4
    scene_02.mp3
    ...
    subtitles.srt      # Timed captions
    final.mp4          # Full assembled video
```

## Error Handling

- **Manim render failures**: Retry loop sends error output back to Claude for code fix (max 3 attempts per scene). If all retries fail, skip the scene and warn the user.
- **TTS failures**: Retry with exponential backoff. If TTS fails, output video without voiceover and warn.
- **FFmpeg failures**: Log the error and leave intermediate files in the output directory for manual recovery.

## Future (Post-V1)

Not in scope for V1, but noted for later:

- Web UI for prompt input and preview
- Multiple design themes (modern dark, minimal white, etc.)
- Background music bed (royalty-free, auto-mixed under voiceover)
- Longer-form videos with chapter markers
- Interactive editing of individual scenes without regenerating the whole video
- Support for additional LLMs (GPT-4o, Gemini) as code generators
- Support for additional TTS providers (Google, OpenAI)
