"""
Video generation endpoint — validates auth, enforces rate limits,
creates a job, and kicks off the background pipeline.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException

from web.backend.models import GenerateRequest, GenerateResponse
from web.backend.supabase_client import get_supabase, get_user_from_token
from web.backend.worker import run_pipeline

router = APIRouter(prefix="/api", tags=["generate"])

DAILY_RATE_LIMIT = 5


def _extract_token(authorization: str) -> str:
    """Pull the raw JWT from an 'Authorization: Bearer <token>' header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    return authorization[len("Bearer "):]


@router.post("/generate", response_model=GenerateResponse)
async def generate_video(
    body: GenerateRequest,
    background_tasks: BackgroundTasks,
    authorization: str = Header(..., description="Bearer token"),
):
    """Start generating a video from a topic prompt.

    Requires a valid Supabase auth token. Enforces a per-user daily rate
    limit and queues the heavy work as a background task.
    """
    # --- Auth ---
    token = _extract_token(authorization)
    try:
        user = get_user_from_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user_id: str = user["sub"]
    supabase = get_supabase()

    # --- Rate limit: max N jobs in the last 24 hours ---
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    recent_jobs = (
        supabase.table("generation_jobs")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .gte("created_at", since)
        .execute()
    )
    job_count = recent_jobs.count if recent_jobs.count is not None else len(recent_jobs.data)
    if job_count >= DAILY_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded — maximum {DAILY_RATE_LIMIT} videos per day",
        )

    # --- Create job row ---
    job_row = {
        "user_id": user_id,
        "topic": body.topic,
        "duration_profile": body.duration.value,
        "status": "queued",
        "progress_message": "Waiting in queue...",
    }
    insert_response = supabase.table("generation_jobs").insert(job_row).execute()
    job_id: str = insert_response.data[0]["id"]

    # --- Kick off background work ---
    background_tasks.add_task(run_pipeline, job_id)

    return GenerateResponse(job_id=job_id)
