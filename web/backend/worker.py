"""
Background worker — runs the full video generation pipeline and
updates the Supabase job row as it progresses through each stage.
"""

import json
import os
import re
import sys
import traceback
from pathlib import Path

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.planner import plan_scenes  # noqa: E402
from core.research import research_topic  # noqa: E402
from core.codegen import generate_manim_code  # noqa: E402
from core.renderer import render_scene, get_scene_names  # noqa: E402
from core.voice import generate_voice, get_audio_duration  # noqa: E402
from core.assembler import combine_scene, concatenate_scenes, generate_thumbnail  # noqa: E402

from web.backend.supabase_client import get_supabase  # noqa: E402

OUTPUT_ROOT = PROJECT_ROOT / "output"

SITE_URL = os.environ.get("SITE_URL", "https://curiso.app")


def _send_completion_email(user_email: str, video_title: str, video_id: str, thumbnail_url: str | None) -> None:
    """Send an email notification when a video generation completes."""
    resend_key = os.environ.get("RESEND_API_KEY")
    if not resend_key:
        return

    try:
        import resend
        resend.api_key = resend_key

        video_url = f"{SITE_URL}/video/{video_id}"

        html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 20px; color: #37352f;">
          <h1 style="font-size: 24px; font-weight: normal; font-family: Georgia, serif; margin-bottom: 8px;">Curiso</h1>
          <p style="font-size: 13px; color: #9b9a97; margin-bottom: 32px;">Understand anything visually.</p>

          <h2 style="font-size: 18px; font-weight: 500; margin-bottom: 12px;">Your video is ready!</h2>
          <p style="font-size: 14px; line-height: 1.6; color: #37352f; margin-bottom: 24px;">
            Your video <strong>{video_title}</strong> has been generated and is ready to watch.
          </p>

          {"<img src='" + thumbnail_url + "' alt='Video thumbnail' style='width: 100%; border-radius: 8px; margin-bottom: 24px;' />" if thumbnail_url else ""}

          <a href="{video_url}" style="display: inline-block; background: #37352f; color: #ffffff; padding: 12px 28px; border-radius: 8px; text-decoration: none; font-size: 14px; font-weight: 500;">
            Watch Video
          </a>

          <hr style="border: none; border-top: 1px solid #e3e2df; margin: 32px 0;" />
          <p style="font-size: 11px; color: #9b9a97;">
            Curiso — 100% free AI-powered educational video generation<br/>
            <a href="https://curiso.app" style="color: #9b9a97;">curiso.app</a>
          </p>
        </div>
        """

        resend.Emails.send({
            "from": "Curiso <noreply@curiso.app>",
            "to": [user_email],
            "subject": f"Your video is ready: {video_title}",
            "html": html,
        })
    except Exception:
        # Don't fail the pipeline if email fails
        pass


def slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "_", slug).strip("_")[:60]


def url_slugify(text: str) -> str:
    """Convert text to a URL-friendly slug for video URLs."""
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug[:80]


def _generate_tags(plan: dict) -> list[str]:
    """Generate 3-5 topic tags for a video using Claude."""
    try:
        import anthropic
        client = anthropic.Anthropic()
        topic = plan.get("topic", "")
        title = plan.get("title", "")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": f"Generate 3-5 short topic tags for this educational video.\n\nTitle: {title}\nTopic: {topic}\n\nReturn ONLY a JSON array of lowercase strings, e.g. [\"physics\", \"quantum mechanics\", \"particles\"]. Tags should be broad enough to group related videos but specific enough to be useful for filtering."
            }],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(raw)
    except Exception:
        return []


def _update_job(job_id: str, **fields) -> None:
    """Update a generation_jobs row in Supabase."""
    supabase = get_supabase()
    supabase.table("generation_jobs").update(fields).eq("id", job_id).execute()


def run_pipeline(job_id: str) -> None:
    """Execute the full video generation pipeline for a queued job.

    Updates the job row in Supabase as each stage completes so the
    frontend can poll for progress.
    """
    supabase = get_supabase()

    # Fetch job details
    job = (
        supabase.table("generation_jobs")
        .select("*")
        .eq("id", job_id)
        .single()
        .execute()
    ).data

    topic: str = job["topic"]
    duration: str = job.get("duration_profile", "short")
    user_id: str = job["user_id"]
    use_research: bool = job.get("use_research", False)

    try:
        # ── Stage 1: Research + Planning ─────────────────────────────
        research_context = ""
        research_sources = None

        if use_research:
            _update_job(job_id, status="planning", progress_message="Researching topic...")
            research = research_topic(topic)
            if research.needed:
                research_context = research.context
                research_sources = research.sources
        else:
            _update_job(job_id, status="planning", progress_message="Planning scenes...")

        _update_job(job_id, progress_message="Planning scenes...")
        plan = plan_scenes(
            topic,
            duration=duration,
            research_context=research_context,
            research_sources=research_sources,
        )

        topic_slug = slugify(plan["topic"])
        out_dir = OUTPUT_ROOT / f"web_{job_id}_{topic_slug}"
        out_dir.mkdir(parents=True, exist_ok=True)

        plan_path = out_dir / "plan.json"
        plan_path.write_text(json.dumps(plan, indent=2))

        num_scenes = len(plan["scenes"])

        # ── Stage 2: Voiceover (audio-first for timing) ──────────────
        _update_job(
            job_id,
            status="voiceover",
            progress_message="Generating voiceover audio...",
        )

        audio_files: list[Path] = []
        durations: list[float] = []

        for idx, scene in enumerate(plan["scenes"], start=1):
            _update_job(
                job_id,
                progress_message=f"Generating voiceover for scene {idx} of {num_scenes}...",
            )
            audio_path = out_dir / f"scene_{idx:02d}.mp3"
            generate_voice(scene["narration"], audio_path)
            dur = get_audio_duration(audio_path)
            audio_files.append(audio_path)
            durations.append(dur)

        # ── Stage 3: Code generation (with exact audio durations) ───
        _update_job(
            job_id,
            status="generating",
            progress_message=f"Generating animation code for {num_scenes} scenes...",
        )
        code = generate_manim_code(plan, scene_durations=durations)
        code_path = out_dir / "scenes.py"
        code_path.write_text(code)

        scene_names = get_scene_names(code)
        if not scene_names:
            raise RuntimeError("No Scene classes found in generated code")

        # ── Stage 4: Rendering ──────────────────────────────────────
        _update_job(
            job_id,
            status="rendering",
            progress_message=f"Rendering scene 1 of {len(scene_names)}...",
        )

        rendered_videos: list[Path] = []
        current_code = code

        for idx, scene_name in enumerate(scene_names, start=1):
            _update_job(
                job_id,
                progress_message=f"Rendering scene {idx} of {len(scene_names)}...",
            )
            video_path, current_code = render_scene(
                code=current_code,
                scene_name=scene_name,
                output_dir=out_dir,
                code_path=code_path,
                preview=False,
            )
            if video_path:
                rendered_videos.append(video_path)

        if not rendered_videos:
            raise RuntimeError("No scenes rendered successfully")

        # Fail if less than half the scenes rendered — don't publish a broken video
        if len(rendered_videos) < len(scene_names) / 2:
            raise RuntimeError(
                f"Only {len(rendered_videos)} of {len(scene_names)} scenes rendered. "
                f"Aborting to avoid publishing an incomplete video."
            )

        # Save final (possibly patched) code
        code_path.write_text(current_code)

        # ── Stage 5: Assembly ────────────────────────────────────────
        _update_job(
            job_id,
            status="assembling",
            progress_message="Assembling final video...",
        )

        combined_scenes: list[Path] = []
        for idx, (video, audio) in enumerate(
            zip(rendered_videos, audio_files), start=1
        ):
            _update_job(
                job_id,
                progress_message=f"Combining scene {idx} video and audio...",
            )
            combined_path = out_dir / f"combined_{idx:02d}.mp4"
            combine_scene(video, audio, combined_path)
            combined_scenes.append(combined_path)

        final_path = out_dir / "final.mp4"
        if len(combined_scenes) == 1:
            combined_scenes[0].rename(final_path)
        else:
            concatenate_scenes(combined_scenes, final_path)

        # ── Generate thumbnail ──────────────────────────────────────
        thumbnail_path = out_dir / "thumbnail.jpg"
        generate_thumbnail(final_path, thumbnail_path)

        # ── Generate vertical (9:16) version for Reels/TikTok ─────
        _update_job(
            job_id,
            progress_message="Creating vertical version for Reels...",
        )
        vertical_path = out_dir / "vertical.mp4"
        import subprocess as _sp
        _sp.run(
            [
                "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(final_path),
                "-filter_complex",
                "[0:v]scale=1080:-2[scaled];color=c=black:s=1080x1920:d=999[bg];[bg][scaled]overlay=0:(1920-h)/2[out]",
                "-map", "[out]", "-map", "0:a", "-c:a", "copy",
                "-shortest", "-pix_fmt", "yuv420p",
                str(vertical_path),
            ],
            capture_output=True, text=True, timeout=600,
        )

        # ── Upload to Supabase Storage ───────────────────────────────
        _update_job(
            job_id,
            progress_message="Uploading video...",
        )

        storage_path = f"videos/{job_id}/final.mp4"
        with open(final_path, "rb") as f:
            supabase.storage.from_("generated_videos").upload(
                storage_path,
                f,
                file_options={"content-type": "video/mp4"},
            )

        video_url = supabase.storage.from_("generated_videos").get_public_url(storage_path)

        # Upload vertical version
        vertical_video_url = None
        if vertical_path.exists():
            vert_storage_path = f"videos/{job_id}/vertical.mp4"
            with open(vertical_path, "rb") as f:
                supabase.storage.from_("generated_videos").upload(
                    vert_storage_path,
                    f,
                    file_options={"content-type": "video/mp4"},
                )
            vertical_video_url = supabase.storage.from_("generated_videos").get_public_url(vert_storage_path)

        # Upload thumbnail
        thumb_storage_path = f"videos/{job_id}/thumbnail.jpg"
        with open(thumbnail_path, "rb") as f:
            supabase.storage.from_("generated_videos").upload(
                thumb_storage_path,
                f,
                file_options={"content-type": "image/jpeg"},
            )

        thumbnail_url = supabase.storage.from_("generated_videos").get_public_url(thumb_storage_path)

        # Compute video duration from assembled durations
        total_duration = sum(durations)

        # Build narration text for the video record
        successful_scenes = plan["scenes"][:len(rendered_videos)]
        full_narration = "\n\n".join(
            scene["narration"] for scene in successful_scenes
        )

        # ── Create videos row ────────────────────────────────────────
        video_row = {
            "user_id": user_id,
            "topic": topic,
            "title": plan.get("title", topic),
            "duration_profile": duration,
            "aha_moment": plan.get("aha_moment"),
            "narration_text": full_narration,
            "video_url": video_url,
            "vertical_video_url": vertical_video_url,
            "thumbnail_url": thumbnail_url,
            "video_duration_seconds": total_duration,
            "view_count": 0,
        }

        # Generate URL slug and tags
        slug = url_slugify(plan.get("title", topic))
        video_row["slug"] = slug

        tags = _generate_tags(plan)
        if tags:
            video_row["tags"] = tags

        # Include research sources if web search was used
        if use_research and research_sources:
            video_row["sources"] = research_sources

        # Handle slug collisions by appending a random suffix
        import uuid
        try:
            video_insert = supabase.table("videos").insert(video_row).execute()
        except Exception:
            video_row["slug"] = f"{slug[:70]}-{uuid.uuid4().hex[:8]}"
            video_insert = supabase.table("videos").insert(video_row).execute()
        video_id: str = video_insert.data[0]["id"]

        # ── Mark job complete ────────────────────────────────────────
        _update_job(
            job_id,
            status="completed",
            progress_message="Video ready!",
            video_id=video_id,
        )

        # ── Send completion email ─────────────────────────────────────
        try:
            user_resp = supabase.auth.admin.get_user_by_id(user_id)
            if user_resp and user_resp.user and user_resp.user.email:
                _send_completion_email(
                    user_email=user_resp.user.email,
                    video_title=plan.get("title", topic),
                    video_id=video_id,
                    thumbnail_url=thumbnail_url,
                )
        except Exception:
            pass  # Don't fail the pipeline if email fails

    except Exception:
        _update_job(
            job_id,
            status="failed",
            error_message=traceback.format_exc(),
            progress_message="Generation failed",
        )
