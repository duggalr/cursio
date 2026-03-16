"""
Job status polling endpoint.
"""

from fastapi import APIRouter, Header, HTTPException

from web.backend.models import JobStatus
from web.backend.supabase_client import get_supabase, get_user_from_token

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/active/me", response_model=JobStatus | None)
async def get_active_job(
    authorization: str = Header(..., description="Bearer token"),
):
    """Return the user's currently active (non-terminal) generation job, if any."""
    token = authorization.removeprefix("Bearer ").strip()
    try:
        user = get_user_from_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user_id = user["sub"]
    supabase = get_supabase()

    response = (
        supabase.table("generation_jobs")
        .select("*")
        .eq("user_id", user_id)
        .in_("status", ["queued", "planning", "generating", "rendering", "voiceover", "assembling"])
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    row = response.data[0]
    return JobStatus(
        id=row["id"],
        status=row["status"],
        progress_message=row.get("progress_message"),
        video_id=row.get("video_id"),
        error_message=row.get("error_message"),
        created_at=row["created_at"],
    )


@router.get("/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Return the current status of a generation job."""
    supabase = get_supabase()

    response = (
        supabase.table("generation_jobs")
        .select("*")
        .eq("id", job_id)
        .single()
        .execute()
    )

    if not response.data:
        raise HTTPException(status_code=404, detail="Job not found")

    row = response.data
    return JobStatus(
        id=row["id"],
        status=row["status"],
        progress_message=row.get("progress_message"),
        video_id=row.get("video_id"),
        error_message=row.get("error_message"),
        created_at=row["created_at"],
    )
