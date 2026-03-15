"""
Job status polling endpoint.
"""

from fastapi import APIRouter, HTTPException

from web.backend.models import JobStatus
from web.backend.supabase_client import get_supabase

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


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
