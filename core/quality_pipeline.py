"""
Quality Mode Pipeline — per-scene iteration with visual inspection.

Instead of generating all scenes at once and hoping for the best,
this pipeline:
1. Generates each scene as a standalone file
2. Renders a preview
3. Inspects the result visually (via Claude vision)
4. Iterates if quality is below threshold
5. Adjusts narrations to match actual animation durations
6. Generates voice audio last
"""

import base64
import json
import subprocess
import tempfile
from pathlib import Path

import anthropic

from .codegen import generate_single_scene_code, fix_manim_code
from .renderer import render_scene, get_scene_names
from .planner import adjust_narration_for_duration
from .voice import generate_voice, get_audio_duration
from .assembler import combine_scene, concatenate_scenes


def _extract_frames(video_path: Path, count: int = 4) -> list[str]:
    """Extract evenly-spaced frames from a video as base64 JPEGs."""
    duration = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        capture_output=True, text=True, timeout=10,
    ).stdout.strip() or "0")

    if duration <= 0:
        return []

    frames = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        # Extract frames at evenly spaced intervals
        interval = max(duration / (count + 1), 0.5)
        for i in range(count):
            t = interval * (i + 1)
            out = tmp / f"frame_{i}.jpg"
            subprocess.run(
                ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                 "-ss", str(t), "-i", str(video_path),
                 "-vframes", "1", "-q:v", "3", str(out)],
                capture_output=True, timeout=10,
            )
            if out.exists():
                with open(out, "rb") as f:
                    frames.append(base64.standard_b64encode(f.read()).decode())

    return frames


def inspect_scene_quality(video_path: Path, scene_plan: dict) -> dict:
    """Inspect rendered scene quality using Claude vision.

    Returns:
        {"score": int, "pass": bool, "issues": list[str], "suggestions": list[str]}
    """
    frames = _extract_frames(video_path, count=4)
    if not frames:
        return {"score": 3, "pass": False, "issues": ["Could not extract frames"], "suggestions": []}

    client = anthropic.Anthropic()

    content = [{
        "type": "text",
        "text": f"""You are inspecting a rendered Manim animation scene. Rate its visual quality.

Scene narration: {scene_plan.get('narration', '')}
Scene description: {scene_plan.get('animation_description', '')}

Look at these {len(frames)} frames extracted from the animation and evaluate:
1. Text readability — is all text fully visible, no cut-off, no overlap?
2. Visual clarity — clean layout, appropriate spacing, no empty/black screens?
3. Animation richness — are there actual visual elements (not just text on black)?
4. Layout — objects positioned well within the frame?

Respond with ONLY valid JSON:
{{"score": 7, "pass": true, "issues": ["specific issue"], "suggestions": ["specific fix"]}}

Score 1-10. Pass threshold is 6."""
    }]

    for i, frame_b64 in enumerate(frames):
        content.append({"type": "text", "text": f"Frame {i+1}/{len(frames)}:"})
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": frame_b64},
        })

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        messages=[{"role": "user", "content": content}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    try:
        result = json.loads(raw)
        result["pass"] = result.get("score", 0) >= 6
        return result
    except (json.JSONDecodeError, KeyError):
        return {"score": 5, "pass": False, "issues": ["Could not parse quality assessment"], "suggestions": []}


def generate_and_inspect_scene(
    plan: dict,
    scene_index: int,
    output_dir: Path,
    max_iterations: int = 3,
    quality_threshold: int = 6,
    on_progress: callable = None,
) -> tuple[Path | None, str, float]:
    """Generate, render, and iterate on a single scene until quality passes.

    Returns:
        (video_path, final_code, duration) or (None, code, 0) if all attempts fail.
    """
    scene = plan["scenes"][scene_index]
    scene_num = scene_index + 1
    scene_name = f"Scene{scene_num:02d}"
    code_path = output_dir / f"scene_{scene_num:02d}.py"

    if on_progress:
        on_progress(f"Generating code for scene {scene_num}...")

    # Generate initial code
    code = generate_single_scene_code(plan, scene_index)

    for iteration in range(max_iterations):
        if on_progress:
            on_progress(f"Rendering scene {scene_num} (attempt {iteration + 1}/{max_iterations})...")

        # Render
        video_path, code = render_scene(
            code=code,
            scene_name=scene_name,
            output_dir=output_dir,
            code_path=code_path,
            preview=(iteration < max_iterations - 1),  # preview for iterations, final quality on last
        )

        if not video_path:
            if iteration < max_iterations - 1:
                # Render failed, regenerate
                if on_progress:
                    on_progress(f"Scene {scene_num} render failed, regenerating...")
                code = generate_single_scene_code(plan, scene_index)
                continue
            else:
                return None, code, 0

        # Get duration
        try:
            dur = float(subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
                capture_output=True, text=True, timeout=10,
            ).stdout.strip())
        except (ValueError, subprocess.TimeoutExpired):
            dur = 0

        # On last iteration, skip quality check — just use what we have
        if iteration == max_iterations - 1:
            return video_path, code, dur

        # Inspect quality
        if on_progress:
            on_progress(f"Inspecting scene {scene_num} quality...")

        quality = inspect_scene_quality(video_path, scene)
        print(f"    Scene {scene_num} quality: {quality['score']}/10 ({'PASS' if quality['pass'] else 'FAIL'})")

        if quality["pass"]:
            # Re-render at final quality if this was a preview
            if on_progress:
                on_progress(f"Scene {scene_num} passed quality check, rendering final...")
            video_path, code = render_scene(
                code=code,
                scene_name=scene_name,
                output_dir=output_dir,
                code_path=code_path,
                preview=False,
            )
            if video_path:
                try:
                    dur = float(subprocess.run(
                        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                         "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
                        capture_output=True, text=True, timeout=10,
                    ).stdout.strip())
                except (ValueError, subprocess.TimeoutExpired):
                    dur = 0
            return video_path, code, dur

        # Quality failed — fix based on feedback
        if on_progress:
            on_progress(f"Scene {scene_num} quality {quality['score']}/10, fixing issues...")

        issues_text = "\n".join(f"- {issue}" for issue in quality.get("issues", []))
        suggestions_text = "\n".join(f"- {s}" for s in quality.get("suggestions", []))

        code = fix_manim_code(
            code,
            f"Visual quality inspection found these issues:\n{issues_text}\n\n"
            f"Suggestions:\n{suggestions_text}\n\n"
            f"Fix these visual issues in {scene_name}. The animation should have clear, "
            f"readable text, good layout, and rich visual elements — not just text on a black screen."
        )

    return None, code, 0


def run_quality_pipeline(
    plan: dict,
    output_dir: Path,
    no_voice: bool = False,
    on_progress: callable = None,
) -> dict:
    """Run the full quality mode pipeline.

    Steps:
    1. Generate + inspect each scene with quality loop
    2. Get actual durations from rendered videos
    3. Adjust narrations to match durations (unless no_voice)
    4. Generate voice audio (unless no_voice)
    5. Assemble final video

    Returns dict with scene_videos, durations, narrations, audio_files, final_path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    num_scenes = len(plan["scenes"])
    scene_videos = []
    scene_durations = []
    scene_codes = []

    # -- Step 1: Generate and inspect each scene --
    for i in range(num_scenes):
        if on_progress:
            on_progress(f"Quality mode: scene {i+1}/{num_scenes}")

        video_path, code, duration = generate_and_inspect_scene(
            plan=plan,
            scene_index=i,
            output_dir=output_dir,
            on_progress=on_progress,
        )

        if video_path:
            scene_videos.append(video_path)
            scene_durations.append(duration)
            scene_codes.append(code)
            print(f"  Scene {i+1}: {duration:.1f}s ({'OK' if video_path else 'FAILED'})")
        else:
            print(f"  Scene {i+1}: FAILED (skipping)")

    if not scene_videos:
        raise RuntimeError("No scenes rendered successfully in quality mode")

    # -- Step 2: Adjust narrations to match actual durations --
    adjusted_narrations = []
    for i, (scene, duration) in enumerate(zip(plan["scenes"][:len(scene_videos)], scene_durations)):
        if no_voice:
            adjusted_narrations.append(scene["narration"])
            continue

        if on_progress:
            on_progress(f"Adjusting narration for scene {i+1}...")

        adjusted = adjust_narration_for_duration(
            original_narration=scene["narration"],
            target_duration=duration,
            topic_context=plan.get("topic", ""),
        )
        adjusted_narrations.append(adjusted)
        word_diff = len(adjusted.split()) - len(scene["narration"].split())
        if word_diff != 0:
            print(f"  Scene {i+1} narration: {len(scene['narration'].split())} -> {len(adjusted.split())} words ({word_diff:+d})")

    # -- Step 3: Generate voice (unless no_voice) --
    audio_files = []
    if not no_voice:
        for i, narration in enumerate(adjusted_narrations):
            if on_progress:
                on_progress(f"Generating voiceover for scene {i+1}...")
            audio_path = output_dir / f"scene_{i+1:02d}.mp3"
            generate_voice(narration, audio_path)
            audio_files.append(audio_path)

    # -- Step 4: Assemble --
    if not no_voice and audio_files:
        if on_progress:
            on_progress("Assembling final video...")

        combined = []
        for i, (video, audio) in enumerate(zip(scene_videos, audio_files)):
            combined_path = output_dir / f"combined_{i+1:02d}.mp4"
            combine_scene(video, audio, combined_path)
            combined.append(combined_path)

        final_path = output_dir / "final.mp4"
        if len(combined) == 1:
            import shutil
            shutil.copy2(combined[0], final_path)
        else:
            concatenate_scenes(combined, final_path)
    else:
        # No voice — just concatenate raw scene videos
        final_path = output_dir / "final.mp4"
        if len(scene_videos) == 1:
            import shutil
            shutil.copy2(scene_videos[0], final_path)
        else:
            concatenate_scenes(scene_videos, final_path)

    return {
        "scene_videos": scene_videos,
        "scene_durations": scene_durations,
        "narrations": adjusted_narrations,
        "audio_files": audio_files,
        "final_path": final_path,
    }
