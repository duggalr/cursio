"""
Quality Mode Pipeline — audio-first timing with per-scene visual inspection.

Flow:
1. Generate voice audio from original narration (get exact durations)
2. For each scene: codegen targeting exact audio duration → render → inspect → fix
3. Assemble video + audio

This gives us BOTH precise audio-visual sync (audio-first) AND visual quality
iteration (inspect + fix loop). Best of both approaches.
"""

import base64
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import anthropic

from .codegen import generate_single_scene_code, fix_manim_code
from .renderer import render_scene, get_scene_names
from .voice import generate_voice, get_audio_duration
from .assembler import combine_scene, concatenate_scenes


def _extract_frames(video_path: Path, count: int = 4) -> list[str]:
    """Extract evenly-spaced frames from a video as base64 JPEGs."""
    try:
        duration = float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
            capture_output=True, text=True, timeout=10,
        ).stdout.strip() or "0")
    except (ValueError, subprocess.TimeoutExpired):
        return []

    if duration <= 0:
        return []

    frames = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
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

Look at these {len(frames)} frames and evaluate:
1. Text readability: is ALL text fully visible? Any cut-off at edges, any overlap between elements?
2. Layout: proper spacing between objects? Nothing too close to screen edges (top/bottom/sides)?
3. Visual richness: actual diagrams/shapes/animations, not just text on black background?
4. Clarity: would a viewer understand what's being shown?

IMPORTANT: Be strict about layout issues. Text cut off at the bottom or overlapping other elements is an automatic fail (score 4 or below).

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
    target_duration: float | None = None,
    max_iterations: int = 3,
    on_progress: callable = None,
) -> tuple[Path | None, str, float]:
    """Generate, render, and iterate on a single scene until quality passes.

    Args:
        target_duration: Exact audio duration to target (audio-first mode).

    Returns:
        (video_path, final_code, duration) or (None, code, 0) on failure.
    """
    scene = plan["scenes"][scene_index]
    scene_num = scene_index + 1
    scene_name = f"Scene{scene_num:02d}"
    code_path = output_dir / f"scene_{scene_num:02d}.py"

    if on_progress:
        on_progress(f"Generating code for scene {scene_num}...")

    # Generate initial code with optional timing target
    code = generate_single_scene_code(
        plan, scene_index, target_duration=target_duration,
    )

    for iteration in range(max_iterations):
        if on_progress:
            on_progress(f"Rendering scene {scene_num} (attempt {iteration + 1}/{max_iterations})...")

        # Render (preview for early iterations, final quality on last or when passing)
        video_path, code = render_scene(
            code=code,
            scene_name=scene_name,
            output_dir=output_dir,
            code_path=code_path,
            preview=(iteration < max_iterations - 1),
        )

        if not video_path:
            if iteration < max_iterations - 1:
                if on_progress:
                    on_progress(f"Scene {scene_num} render failed, regenerating...")
                code = generate_single_scene_code(
                    plan, scene_index, target_duration=target_duration,
                )
                continue
            else:
                return None, code, 0

        # Get actual duration
        try:
            dur = float(subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
                capture_output=True, text=True, timeout=10,
            ).stdout.strip())
        except (ValueError, subprocess.TimeoutExpired):
            dur = 0

        # On last iteration, use what we have
        if iteration == max_iterations - 1:
            return video_path, code, dur

        # Inspect quality
        if on_progress:
            on_progress(f"Inspecting scene {scene_num} quality...")

        quality = inspect_scene_quality(video_path, scene)
        print(f"    Scene {scene_num} quality: {quality['score']}/10 ({'PASS' if quality['pass'] else 'FAIL'})")

        if quality["pass"]:
            # Re-render at final quality
            if on_progress:
                on_progress(f"Scene {scene_num} passed, rendering final quality...")
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

        # Fix based on feedback
        if on_progress:
            on_progress(f"Scene {scene_num} quality {quality['score']}/10, fixing...")

        issues_text = "\n".join(f"- {issue}" for issue in quality.get("issues", []))
        suggestions_text = "\n".join(f"- {s}" for s in quality.get("suggestions", []))

        code = fix_manim_code(
            code,
            f"Visual quality inspection found these issues:\n{issues_text}\n\n"
            f"Suggestions:\n{suggestions_text}\n\n"
            f"Fix these visual issues in {scene_name}. Ensure all text is fully visible "
            f"within the safe zone (y between -3.0 and 3.0, x between -6.0 and 6.0). "
            f"No overlapping elements. Use buff=0.7 minimum for all positioning."
        )

    return None, code, 0


def run_quality_pipeline(
    plan: dict,
    output_dir: Path,
    no_voice: bool = False,
    on_progress: callable = None,
) -> dict:
    """Run the quality mode pipeline with audio-first timing.

    Flow:
    1. Generate voice audio from original narrations (get exact durations)
    2. Per-scene: codegen targeting exact duration -> render -> inspect -> fix
    3. Combine each scene video + audio
    4. Concatenate into final video

    This gives precise audio-visual sync AND visual quality iteration.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    num_scenes = len(plan["scenes"])

    # -- Step 1: Generate voice audio first (unless no_voice) --
    audio_files = []
    audio_durations = []

    if not no_voice:
        for i, scene in enumerate(plan["scenes"]):
            if on_progress:
                on_progress(f"Generating voiceover for scene {i+1}/{num_scenes}...")
            audio_path = output_dir / f"scene_{i+1:02d}.mp3"
            generate_voice(scene["narration"], audio_path)
            dur = get_audio_duration(audio_path)
            audio_files.append(audio_path)
            audio_durations.append(dur)
            print(f"  Scene {i+1} audio: {dur:.1f}s")
    else:
        # Estimate durations from word count
        for scene in plan["scenes"]:
            word_count = len(scene["narration"].split())
            audio_durations.append(word_count / 2.5)

    # -- Step 2: Generate + inspect each scene with exact timing --
    scene_videos = []
    scene_codes = []

    for i in range(num_scenes):
        if on_progress:
            on_progress(f"Quality mode: scene {i+1}/{num_scenes} (target {audio_durations[i]:.1f}s)")

        video_path, code, duration = generate_and_inspect_scene(
            plan=plan,
            scene_index=i,
            output_dir=output_dir,
            target_duration=audio_durations[i],
            on_progress=on_progress,
        )

        if video_path:
            scene_videos.append(video_path)
            scene_codes.append(code)
            diff = duration - audio_durations[i]
            print(f"  Scene {i+1}: {duration:.1f}s (target {audio_durations[i]:.1f}s, diff {diff:+.1f}s)")
        else:
            print(f"  Scene {i+1}: FAILED (skipping)")

    if not scene_videos:
        raise RuntimeError("No scenes rendered successfully in quality mode")

    # -- Step 3: Assemble --
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
            shutil.copy2(combined[0], final_path)
        else:
            concatenate_scenes(combined, final_path)
    else:
        final_path = output_dir / "final.mp4"
        if len(scene_videos) == 1:
            shutil.copy2(scene_videos[0], final_path)
        else:
            concatenate_scenes(scene_videos, final_path)

    # Build narration text for video record
    narrations = [s["narration"] for s in plan["scenes"][:len(scene_videos)]]

    return {
        "scene_videos": scene_videos,
        "scene_durations": audio_durations[:len(scene_videos)],
        "narrations": narrations,
        "audio_files": audio_files,
        "final_path": final_path,
    }
