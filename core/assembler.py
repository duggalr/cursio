"""
Assembler — stitches together rendered animations, voiceover audio,
and subtitles into a final video using FFmpeg.
"""

import subprocess
import sys
from pathlib import Path


def combine_scene(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
) -> Path:
    """Combine a video and audio track for a single scene.

    The video is stretched/trimmed to match audio duration so narration
    and animation stay in sync.

    Args:
        video_path: Path to the scene animation .mp4.
        audio_path: Path to the scene voiceover .mp3.
        output_path: Where to save the combined .mp4.

    Returns:
        Path to the combined file.
    """
    # Get audio duration
    audio_dur = _get_duration(audio_path)
    video_dur = _get_duration(video_path)

    # Speed up or slow down video to match audio duration
    speed_factor = video_dur / audio_dur if audio_dur > 0 else 1.0

    _run_ffmpeg([
        "-i", str(video_path),
        "-i", str(audio_path),
        "-filter_complex",
        f"[0:v]setpts={1/speed_factor}*PTS[v]",
        "-map", "[v]",
        "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ])

    return output_path


def concatenate_scenes(scene_paths: list[Path], output_path: Path) -> Path:
    """Concatenate multiple scene videos into one.

    Args:
        scene_paths: List of paths to combined scene .mp4 files.
        output_path: Where to save the concatenated video.

    Returns:
        Path to the concatenated file.
    """
    concat_list = output_path.parent / "concat.txt"
    with open(concat_list, "w") as f:
        for p in scene_paths:
            f.write(f"file '{p.resolve()}'\n")

    _run_ffmpeg([
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path),
    ])

    concat_list.unlink(missing_ok=True)
    return output_path


def burn_subtitles(video_path: Path, srt_path: Path, output_path: Path) -> Path:
    """Burn subtitles into the video.

    Args:
        video_path: Path to the video without subtitles.
        srt_path: Path to the .srt subtitle file.
        output_path: Where to save the final video.

    Returns:
        Path to the final video with subtitles.
    """
    # Copy SRT to a simple filename to avoid FFmpeg path escaping issues
    import shutil
    safe_srt = srt_path.parent / "subs.srt"
    shutil.copy2(srt_path, safe_srt)

    # Build the filter command as a single string passed to ffmpeg_filter
    # Using -filter_complex with the subtitles filter to avoid escaping issues
    cmd = [
        "-i", str(video_path),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path),
    ]
    # Insert the subtitles filter via shell to handle quoting correctly
    full_cmd = (
        f'ffmpeg -y -hide_banner -loglevel error '
        f'-i "{video_path}" '
        f"-vf \"subtitles=subs.srt:force_style='FontSize=16,PrimaryColour=&H00FFFFFF,"
        f"OutlineColour=&H00000000,BackColour=&H80000000,"
        f"BorderStyle=4,Outline=1,Shadow=0,MarginV=10,Alignment=2'\" "
        f'-c:v libx264 -preset fast -crf 18 '
        f'-c:a copy -pix_fmt yuv420p -movflags +faststart '
        f'"{output_path}"'
    )
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, cwd=srt_path.parent)
    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr}", file=sys.stderr)
        raise RuntimeError(f"FFmpeg failed: {result.stderr[:500]}")

    return output_path


def _get_duration(path: Path) -> float:
    """Get media file duration in seconds."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def generate_thumbnail(video_path: Path, output_path: Path, timestamp: float = 5.0) -> Path:
    """Extract a frame from the video as a thumbnail.

    Args:
        video_path: Path to the video file.
        output_path: Where to save the thumbnail .jpg.
        timestamp: Time in seconds to capture the frame.

    Returns:
        Path to the thumbnail file.
    """
    # Get video duration and grab a frame from ~40% in,
    # past the hook question into the visual explanation
    dur = _get_duration(video_path)
    t = dur * 0.4 if dur > 0 else timestamp

    _run_ffmpeg([
        "-ss", str(t),
        "-i", str(video_path),
        "-vframes", "1",
        "-q:v", "2",
        str(output_path),
    ])

    return output_path


def _run_ffmpeg(args: list[str], cwd: Path | None = None):
    """Run an ffmpeg command, exit on failure."""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr}", file=sys.stderr)
        raise RuntimeError(f"FFmpeg failed: {result.stderr[:500]}")
