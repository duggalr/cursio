"""
Renderer — runs Manim on generated code and handles the retry loop
for render failures.
"""

import subprocess
import re
import shutil
import sys
from pathlib import Path

from .codegen import fix_manim_code


def render_scene(
    code: str,
    scene_name: str,
    output_dir: Path,
    code_path: Path,
    preview: bool = False,
    max_retries: int = 3,
) -> tuple[Path | None, str]:
    """Render a single Manim scene with retry loop.

    Args:
        code: The full Manim Python source code.
        scene_name: The Scene class name to render (e.g. "Scene01").
        output_dir: Where to save the rendered mp4.
        code_path: Where to write the .py file.
        preview: If True, render at lower quality for speed.
        max_retries: Max number of fix attempts on failure.

    Returns:
        Tuple of (path to rendered mp4 or None, final code).
    """
    current_code = code

    for attempt in range(max_retries + 1):
        # Write current code to file
        code_path.write_text(current_code)

        # Build manim command — resolve manim binary from same environment
        manim_bin = shutil.which("manim") or str(Path(sys.executable).parent / "manim")
        quality = "-ql" if preview else "-qm"  # low vs medium quality
        cmd = [
            manim_bin, "render",
            quality,
            "--format", "mp4",
            "--media_dir", str(output_dir / "media"),
            str(code_path),
            scene_name,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            print(f"    Render timed out for {scene_name} (attempt {attempt + 1}/{max_retries + 1})")
            if attempt < max_retries:
                print(f"    Asking Claude to simplify the animation...")
                current_code = fix_manim_code(
                    current_code,
                    f"Scene {scene_name} timed out after 300 seconds. The animation is too complex. "
                    f"Simplify {scene_name}: use fewer objects, simpler animations, remove any loops that create many objects. "
                    f"Keep the same educational content but make the visuals simpler and faster to render."
                )
                continue
            else:
                print(f"    Skipping {scene_name} after timeout on all attempts.")
                return None, current_code

        if result.returncode == 0:
            # Find the rendered file
            mp4_path = _find_rendered_file(output_dir / "media", scene_name)
            if mp4_path:
                # Move to output dir with clean name
                final_path = output_dir / f"{scene_name.lower()}.mp4"
                mp4_path.rename(final_path)
                return final_path, current_code
            else:
                print(f"    WARNING: Render succeeded but mp4 not found for {scene_name}")
                return None, current_code

        # Render failed
        error = result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr
        if not error:
            error = result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout

        if attempt < max_retries:
            print(f"    Render failed (attempt {attempt + 1}/{max_retries + 1}), asking Claude to fix...")
            current_code = fix_manim_code(current_code, error)
        else:
            print(f"    Render failed after {max_retries + 1} attempts.")
            print(f"    Last error: {error[:500]}")
            return None, current_code

    return None, current_code


def _find_rendered_file(media_dir: Path, scene_name: str) -> Path | None:
    """Search the manim media directory for the rendered mp4."""
    if not media_dir.exists():
        return None

    # Manim outputs to media/videos/<filename>/<quality>/<SceneName>.mp4
    for mp4 in media_dir.rglob(f"{scene_name}.mp4"):
        return mp4

    # Fallback: any mp4 in the media dir
    for mp4 in media_dir.rglob("*.mp4"):
        if scene_name.lower() in mp4.name.lower():
            return mp4

    return None


def get_scene_names(code: str) -> list[str]:
    """Extract Scene class names from Manim code."""
    pattern = r"class\s+(\w+)\s*\(\s*Scene\s*\)"
    return re.findall(pattern, code)
