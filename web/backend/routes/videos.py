"""
Video listing, detail, and like endpoints.
"""

import json
import uuid

from fastapi import APIRouter, HTTPException, Header, Query

from web.backend.models import Video, VideoListResponse


def _parse_video_json_fields(row: dict) -> dict:
    """Parse JSON string fields from Supabase into Python objects."""
    for field in ("sources", "tags"):
        value = row.get(field)
        if isinstance(value, str):
            try:
                row[field] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                row[field] = None
    return row


from web.backend.supabase_client import get_supabase, get_user_from_token

router = APIRouter(prefix="/api/videos", tags=["videos"])


def _is_uuid(value: str) -> bool:
    """Check if a string is a valid UUID."""
    try:
        uuid.UUID(value)
        return True
    except ValueError:
        return False


@router.get("", response_model=VideoListResponse)
async def list_videos(
    search: str | None = Query(None, description="Search videos by topic or title"),
    sort: str = Query("recent", description="Sort order: 'recent' or 'most_liked'"),
    tag: str | None = Query(None, description="Filter by tag"),
    featured: bool = Query(False, description="Filter to featured/vetted videos only"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
):
    """List videos with optional search, sorting, tag filtering, and pagination."""
    supabase = get_supabase()
    offset = (page - 1) * limit

    # Build query — include like_count via left join count
    query = supabase.table("videos").select(
        "*, likes(count)", count="exact"
    )

    if featured:
        query = query.eq("is_featured", True)

    if search:
        # Split search into words and match any word in topic or title
        # This way "explain monty hall" matches "The Monty Hall Paradox"
        words = [w.strip() for w in search.split() if w.strip()]
        if words:
            conditions = []
            for word in words:
                conditions.append(f"topic.ilike.%{word}%")
                conditions.append(f"title.ilike.%{word}%")
            query = query.or_(",".join(conditions))

    if tag:
        query = query.contains("tags", json.dumps([tag]))

    # Sorting
    if sort == "most_liked":
        query = query.order("like_count", desc=True)
    elif sort == "most_viewed":
        query = query.order("view_count", desc=True)
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
        _parse_video_json_fields(row)
        videos.append(Video(**row))

    total = response.count if response.count is not None else len(videos)

    return VideoListResponse(videos=videos, total=total)


@router.get("/{slug_or_id}", response_model=Video)
async def get_video(slug_or_id: str):
    """Get a single video by slug or ID."""
    supabase = get_supabase()

    # Try slug lookup first, then fall back to UUID
    if _is_uuid(slug_or_id):
        response = (
            supabase.table("videos")
            .select("*, likes(count)")
            .eq("id", slug_or_id)
            .single()
            .execute()
        )
    else:
        response = (
            supabase.table("videos")
            .select("*, likes(count)")
            .eq("slug", slug_or_id)
            .single()
            .execute()
        )

    if not response.data:
        raise HTTPException(status_code=404, detail="Video not found")

    video_data = response.data
    likes_data = video_data.pop("likes", [])
    video_data["like_count"] = likes_data[0]["count"] if likes_data else 0
    _parse_video_json_fields(video_data)

    return Video(**video_data)


@router.post("/{video_id}/view")
async def record_view(video_id: str):
    """Increment view count for a video."""
    supabase = get_supabase()
    # Use rpc or raw increment — supabase-py doesn't have atomic increment,
    # so we read + write (acceptable for view counts)
    try:
        result = supabase.table("videos").select("view_count").eq("id", video_id).single().execute()
        if result.data:
            current = result.data.get("view_count", 0) or 0
            supabase.table("videos").update({"view_count": current + 1}).eq("id", video_id).execute()
    except Exception:
        pass  # Don't fail on view count errors
    return {"ok": True}


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
