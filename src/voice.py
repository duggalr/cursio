"""
Voice Generator — generates narration audio using ElevenLabs TTS.
"""

import os
from pathlib import Path

from elevenlabs import ElevenLabs

# Default to "George" — warm, captivating British storyteller
# Other good options:
#   Daniel  (onwK4e9ZLuTAKqWW03F9) — steady broadcaster, British, educational
#   Max     (Gfpl8Yo74Is0W6cPUWWT) — eLearning, documentary, friendly
#   Alice   (Xb7hH8MSUJpSbSDYk0k2) — clear, engaging educator, British
DEFAULT_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"


def generate_voice(
    text: str,
    output_path: Path,
    voice_id: str | None = None,
) -> Path:
    """Generate voiceover audio for a narration string.

    Args:
        text: The narration text to speak.
        output_path: Where to save the .mp3 file.
        voice_id: ElevenLabs voice ID. Uses ELEVENLABS_VOICE_ID env var or default.

    Returns:
        Path to the saved mp3 file.
    """
    client = ElevenLabs(api_key=os.environ.get("ELEVENLABS_API_KEY"))

    voice = voice_id or os.environ.get("ELEVENLABS_VOICE_ID") or DEFAULT_VOICE_ID

    audio_generator = client.text_to_speech.convert(
        voice_id=voice,
        text=text,
        model_id="eleven_multilingual_v2",
    )

    # audio_generator yields chunks — write them all to file
    with open(output_path, "wb") as f:
        for chunk in audio_generator:
            f.write(chunk)

    return output_path


def get_audio_duration(audio_path: Path) -> float:
    """Get duration of an audio file in seconds using ffprobe."""
    import subprocess

    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())
