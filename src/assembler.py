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
    # Style: smaller text pinned to very bottom with dark background box
    # MarginV=10 pushes it to the bottom edge, BorderStyle=4 adds a
    # semi-transparent background box so it never obscures the animations
    subtitle_filter = (
        f"subtitles={str(srt_path)}:force_style='"
        f"FontName=Source Sans Pro,"
        f"FontSize=16,"
        f"PrimaryColour=&H00FFFFFF,"
        f"OutlineColour=&H00000000,"
        f"BackColour=&H80000000,"
        f"BorderStyle=4,"
        f"Outline=1,"
        f"Shadow=0,"
        f"MarginV=10,"
        f"Alignment=2"
        f"'"
    )

    _run_ffmpeg([
        "-i", str(video_path),
        "-vf", subtitle_filter,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path),
    ])

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
    # Get video duration to ensure timestamp is valid
    dur = _get_duration(video_path)
    # Use 30% into the video if timestamp exceeds duration
    t = min(timestamp, dur * 0.3) if dur > 0 else 0

    _run_ffmpeg([
        "-ss", str(t),
        "-i", str(video_path),
        "-vframes", "1",
        "-q:v", "2",
        str(output_path),
    ])

    return output_path


def _run_ffmpeg(args: list[str]):
    """Run an ffmpeg command, exit on failure."""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr}", file=sys.stderr)
        raise RuntimeError(f"FFmpeg failed: {result.stderr[:500]}")
