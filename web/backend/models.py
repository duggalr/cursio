"""
Pydantic models for request/response validation.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class DurationProfile(str, Enum):
    short = "short"
    medium = "medium"
    long = "long"


class GenerateRequest(BaseModel):
    topic: str
    duration: DurationProfile = DurationProfile.short
    use_research: bool = False
    quality_mode: bool = False


class GenerateResponse(BaseModel):
    job_id: str


class JobStatus(BaseModel):
    id: str
    status: str
    progress_message: str | None = None
    video_id: str | None = None
    error_message: str | None = None
    created_at: str


class Video(BaseModel):
    id: str
    user_id: str | None = None
    topic: str
    title: str
    duration_profile: str
    aha_moment: str | None = None
    narration_text: str | None = None
    video_url: str | None = None
    vertical_video_url: str | None = None
    thumbnail_url: str | None = None
    video_duration_seconds: float | None = None
    view_count: int = 0
    like_count: int = 0
    slug: str | None = None
    source_url: str | None = None
    sources: list[dict] | None = None
    tags: list[str] | None = None
    created_at: str


class VideoListResponse(BaseModel):
    videos: list[Video]
    total: int
