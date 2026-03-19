"""
Video listing, detail, and like endpoints.
"""

import subprocess
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Header, Query
from fastapi.responses import FileResponse

from web.backend.models import Video, VideoListResponse
from web.backend.supabase_client import get_supabase, get_user_from_token

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.get("", response_model=VideoListResponse)
async def list_videos(
    search: str | None = Query(None, description="Search videos by topic or title"),
    sort: str = Query("recent", description="Sort order: 'recent' or 'most_liked'"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
):
    """List videos with optional search, sorting, and pagination."""
    supabase = get_supabase()
    offset = (page - 1) * limit

    # Build query — include like_count via left join count
    query = supabase.table("videos").select(
        "*, likes(count)", count="exact"
    )

    if search:
        query = query.or_(f"topic.ilike.%{search}%,title.ilike.%{search}%")

    # Sorting
    if sort == "most_liked":
        query = query.order("like_count", desc=True)
    else:
        query = query.order("created_at", desc=True)

    query = query.range(offset, offset + limit - 1)

    response = query.execute()

    videos = []
    for row in response.data:
        # Extract like count from the joined likes aggregate
        likes_data = row.pop("likes", [])
        like_count = likes_data[0]["count"] if likes_data else 0
        row["like_count"] = like_count
        videos.append(Video(**row))

    total = response.count if response.count is not None else len(videos)

    return VideoListResponse(videos=videos, total=total)


@router.get("/{video_id}", response_model=Video)
async def get_video(video_id: str):
    """Get a single video by ID."""
    supabase = get_supabase()

    response = (
        supabase.table("videos")
        .select("*, likes(count)")
        .eq("id", video_id)
        .single()
        .execute()
    )

    if not response.data:
        raise HTTPException(status_code=404, detail="Video not found")

    video_data = response.data
    likes_data = video_data.pop("likes", [])
    video_data["like_count"] = likes_data[0]["count"] if likes_data else 0

    return Video(**video_data)


@router.get("/{video_id}/vertical")
async def get_vertical_video(video_id: str):
    """Download a 9:16 vertical version of the video for Reels/TikTok/Shorts."""
    supabase = get_supabase()

    response = (
        supabase.table("videos")
        .select("video_url, title")
        .eq("id", video_id)
        .single()
        .execute()
    )

    if not response.data or not response.data.get("video_url"):
        raise HTTPException(status_code=404, detail="Video not found")

    video_url = response.data["video_url"]
    title = response.data.get("title", "video")

    # Download the original video to a temp file
    tmp_dir = tempfile.mkdtemp()
    input_path = Path(tmp_dir) / "input.mp4"
    output_path = Path(tmp_dir) / "vertical.mp4"

    dl = subprocess.run(
        ["curl", "-sL", "-o", str(input_path), video_url],
        capture_output=True, timeout=60,
    )
    if dl.returncode != 0 or not input_path.exists():
        raise HTTPException(status_code=500, detail="Failed to download video")

    # Convert to 9:16 with black padding
    result = subprocess.run(
        [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(input_path),
            "-filter_complex",
            "[0:v]scale=1080:-2[scaled];color=c=black:s=1080x1920:d=999[bg];[bg][scaled]overlay=0:(1920-h)/2[out]",
            "-map", "[out]", "-map", "0:a", "-c:a", "copy",
            "-shortest", "-pix_fmt", "yuv420p",
            str(output_path),
        ],
        capture_output=True, text=True, timeout=120,
    )

    if result.returncode != 0 or not output_path.exists():
        raise HTTPException(status_code=500, detail="Failed to convert video")

    # Clean filename
    safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title).strip()
    filename = f"{safe_title} - Vertical.mp4"

    return FileResponse(
        str(output_path),
        media_type="video/mp4",
        filename=filename,
    )


@router.get("/{video_id}/like")
async def check_like(
    video_id: str,
    authorization: str = Header(...),
):
    """Check if the current user has liked a video."""
    token = authorization.replace("Bearer ", "")
    try:
        user = get_user_from_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

    supabase = get_supabase()
    result = (
        supabase.table("likes")
        .select("id")
        .eq("video_id", video_id)
        .eq("user_id", user["sub"])
        .execute()
    )

    return {"liked": len(result.data) > 0}


@router.post("/{video_id}/like")
async def like_video(
    video_id: str,
    authorization: str = Header(...),
):
    """Like a video. Requires authentication."""
    token = authorization.replace("Bearer ", "")
    try:
        user = get_user_from_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

    supabase = get_supabase()

    # Check if already liked
    existing = (
        supabase.table("likes")
        .select("id")
        .eq("video_id", video_id)
        .eq("user_id", user["sub"])
        .execute()
    )

    if existing.data:
        return {"message": "Already liked"}

    # Insert like
    supabase.table("likes").insert({
        "video_id": video_id,
        "user_id": user["sub"],
    }).execute()

    # Update denormalized count
    count_result = (
        supabase.table("likes")
        .select("id", count="exact")
        .eq("video_id", video_id)
        .execute()
    )
    new_count = count_result.count or 0
    supabase.table("videos").update({"like_count": new_count}).eq("id", video_id).execute()

    return {"message": "Liked", "like_count": new_count}


@router.delete("/{video_id}/like")
async def unlike_video(
    video_id: str,
    authorization: str = Header(...),
):
    """Unlike a video. Requires authentication."""
    token = authorization.replace("Bearer ", "")
    try:
        user = get_user_from_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")

    supabase = get_supabase()

    # Delete the like
    supabase.table("likes").delete().eq(
        "video_id", video_id
    ).eq("user_id", user["sub"]).execute()

    # Update denormalized count
    count_result = (
        supabase.table("likes")
        .select("id", count="exact")
        .eq("video_id", video_id)
        .execute()
    )
    new_count = count_result.count or 0
    supabase.table("videos").update({"like_count": new_count}).eq("id", video_id).execute()

    return {"message": "Unliked", "like_count": new_count}
