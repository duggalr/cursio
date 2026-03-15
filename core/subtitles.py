"""
Subtitle Generator — creates .srt subtitle files from narration text
and audio durations.
"""

import textwrap
from pathlib import Path


def generate_subtitles(
    scenes: list[dict],
    durations: list[float],
    output_path: Path,
    chars_per_line: int = 42,
) -> Path:
    """Generate an SRT subtitle file from scene narrations and audio durations.

    Args:
        scenes: List of scene dicts with 'narration' key.
        durations: Audio duration in seconds for each scene.
        output_path: Where to write the .srt file.
        chars_per_line: Max characters per subtitle line.

    Returns:
        Path to the saved .srt file.
    """
    srt_entries = []
    subtitle_index = 1
    cumulative_time = 0.0

    for scene, duration in zip(scenes, durations):
        narration = scene["narration"]
        sentences = _split_sentences(narration)

        if not sentences:
            cumulative_time += duration
            continue

        # Distribute time across sentences proportionally by character count
        total_chars = sum(len(s) for s in sentences)
        if total_chars == 0:
            cumulative_time += duration
            continue

        for sentence in sentences:
            sentence_duration = (len(sentence) / total_chars) * duration
            start_time = cumulative_time
            end_time = cumulative_time + sentence_duration

            # Word-wrap long sentences
            wrapped = textwrap.fill(sentence.strip(), width=chars_per_line)

            srt_entries.append(
                f"{subtitle_index}\n"
                f"{_format_timestamp(start_time)} --> {_format_timestamp(end_time)}\n"
                f"{wrapped}\n"
            )
            subtitle_index += 1
            cumulative_time = end_time

    output_path.write_text("\n".join(srt_entries), encoding="utf-8")
    return output_path


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences at punctuation boundaries."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if s.strip()]


def _format_timestamp(seconds: float) -> str:
    """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
