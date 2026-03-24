"""
Video generation endpoint — validates auth, enforces rate limits,
creates a job, and kicks off the background pipeline.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException, File, UploadFile, Form

from web.backend.models import GenerateRequest, GenerateResponse
from web.backend.supabase_client import get_supabase, get_user_from_token
from web.backend.worker import run_pipeline

router = APIRouter(prefix="/api", tags=["generate"])

# MONTHLY_RATE_LIMIT = 8  # Temporarily disabled — unlimited generations


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

    # --- Rate limit: temporarily disabled (unlimited generations) ---
    # TODO: Re-enable when ready
    # now = datetime.now(timezone.utc)
    # month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    # recent_jobs = (
    #     supabase.table("generation_jobs")
    #     .select("id", count="exact")
    #     .eq("user_id", user_id)
    #     .gte("created_at", month_start)
    #     .execute()
    # )
    # job_count = recent_jobs.count if recent_jobs.count is not None else len(recent_jobs.data)
    # if job_count >= MONTHLY_RATE_LIMIT:
    #     raise HTTPException(
    #         status_code=429,
    #         detail=f"Rate limit exceeded — maximum {MONTHLY_RATE_LIMIT} free videos per month",
    #     )

    # --- Create job row ---
    job_row = {
        "user_id": user_id,
        "topic": body.topic,
        "duration_profile": body.duration.value,
        "use_research": body.use_research,
        "quality_mode": body.quality_mode,
        "status": "queued",
        "progress_message": "Waiting in queue...",
    }
    insert_response = supabase.table("generation_jobs").insert(job_row).execute()
    job_id: str = insert_response.data[0]["id"]

    # --- Kick off background work ---
    background_tasks.add_task(run_pipeline, job_id)

    return GenerateResponse(job_id=job_id)


@router.post("/generate-from-paper", response_model=GenerateResponse)
async def generate_from_paper(
    background_tasks: BackgroundTasks,
    authorization: str = Header(..., description="Bearer token"),
    file: UploadFile = File(..., description="PDF file"),
    duration: str = Form("medium", description="Video duration: short, medium, long"),
):
    """Generate a video from an uploaded research paper PDF.

    Extracts text from the PDF, creates a paper-specific plan,
    and runs the quality mode pipeline.
    """
    # Auth
    token = _extract_token(authorization)
    try:
        user = get_user_from_token(token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    user_id = user["sub"]
    user_email = user.get("email", "")

    # Paper upload is currently restricted to allowed users
    PAPER_ALLOWED_EMAILS = {"duggalr42@gmail.com"}
    if user_email not in PAPER_ALLOWED_EMAILS:
        raise HTTPException(status_code=403, detail="Research paper upload is coming soon")

    # Validate file
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Read file content
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:  # 20MB limit
        raise HTTPException(status_code=400, detail="File too large (max 20MB)")

    # Save temporarily and extract text
    import tempfile
    from pathlib import Path
    from core.paper import extract_paper_text

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        paper = extract_paper_text(tmp_path)
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Could not read PDF: {str(exc)}")
    finally:
        tmp_path.unlink(missing_ok=True)

    supabase = get_supabase()

    # Create job with paper text stored
    job_row = {
        "user_id": user_id,
        "topic": paper["title"][:500] or file.filename,
        "duration_profile": duration,
        "use_research": False,
        "quality_mode": True,  # Always quality mode for papers
        "paper_text": paper["text"],
        "paper_title": paper["title"],
        "status": "queued",
        "progress_message": "Waiting in queue...",
    }
    insert_response = supabase.table("generation_jobs").insert(job_row).execute()
    job_id = insert_response.data[0]["id"]

    background_tasks.add_task(run_pipeline, job_id)

    return GenerateResponse(job_id=job_id)
