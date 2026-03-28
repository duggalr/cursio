"""
Core API endpoint tests for the Curiso backend.

Tests run against FastAPI TestClient with mocked Supabase — no real
database, no API keys needed. Validates request/response contracts,
status codes, and error handling.
"""

from unittest.mock import MagicMock, patch


# ─── Health ─────────────────────────────────────────────────────────


def test_health_check(client):
    """GET /api/health returns 200 with status ok."""
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


# ─── Videos: List ───────────────────────────────────────────────────


def test_list_videos_empty(client, mock_supabase):
    """GET /api/videos returns empty list when no videos exist."""
    res = client.get("/api/videos")
    assert res.status_code == 200
    data = res.json()
    assert data["videos"] == []
    assert data["total"] == 0


def test_list_videos_search_param(client, mock_supabase):
    """GET /api/videos?search=gravity passes search to query."""
    res = client.get("/api/videos?search=gravity")
    assert res.status_code == 200


def test_list_videos_tag_filter(client, mock_supabase):
    """GET /api/videos?tag=physics passes tag filter."""
    res = client.get("/api/videos?tag=physics")
    assert res.status_code == 200


def test_list_videos_sort_options(client, mock_supabase):
    """GET /api/videos accepts both sort options."""
    assert client.get("/api/videos?sort=recent").status_code == 200
    assert client.get("/api/videos?sort=most_liked").status_code == 200


def test_list_videos_pagination(client, mock_supabase):
    """GET /api/videos accepts pagination params."""
    res = client.get("/api/videos?page=2&limit=10")
    assert res.status_code == 200


# ─── Videos: Like/Unlike ───────────────────────────────────────────


def test_like_requires_auth(client):
    """POST /api/videos/{id}/like requires auth header."""
    res = client.post("/api/videos/abc-123/like")
    assert res.status_code == 422  # Missing header


def test_like_with_auth(client, mock_auth, mock_supabase):
    """POST /api/videos/{id}/like with valid auth succeeds."""
    # Mock: not already liked
    mock_existing = MagicMock()
    mock_existing.data = []
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = mock_existing

    # Mock: count after like
    mock_count = MagicMock()
    mock_count.count = 1
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = mock_count

    res = client.post(
        "/api/videos/abc-123/like",
        headers={"Authorization": "Bearer fake-token"},
    )
    assert res.status_code == 200


def test_unlike_requires_auth(client):
    """DELETE /api/videos/{id}/like requires auth header."""
    res = client.delete("/api/videos/abc-123/like")
    assert res.status_code == 422


# ─── Generate ───────────────────────────────────────────────────────


def test_generate_requires_auth(client):
    """POST /api/generate requires auth header."""
    res = client.post("/api/generate", json={"topic": "test"})
    assert res.status_code == 422  # Missing header


def test_generate_requires_topic(client, mock_auth):
    """POST /api/generate requires topic field."""
    res = client.post(
        "/api/generate",
        json={},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert res.status_code == 422  # Missing required field


def test_generate_invalid_duration(client, mock_auth):
    """POST /api/generate rejects invalid duration."""
    res = client.post(
        "/api/generate",
        json={"topic": "test", "duration": "invalid"},
        headers={"Authorization": "Bearer fake-token"},
    )
    assert res.status_code == 422


def test_generate_valid_request(mock_auth):
    """POST /api/generate with valid input creates a job."""
    mock_insert_response = MagicMock()
    mock_insert_response.data = [{"id": "job-123"}]

    mock_sb = MagicMock()
    mock_sb.table.return_value.insert.return_value.execute.return_value = mock_insert_response

    with patch("web.backend.routes.generate.get_supabase", return_value=mock_sb):
        with patch("web.backend.routes.generate.run_pipeline"):
            from web.backend.app import app
            from fastapi.testclient import TestClient
            c = TestClient(app)
            res = c.post(
                "/api/generate",
                json={"topic": "How gravity works", "duration": "short"},
                headers={"Authorization": "Bearer fake-token"},
            )
    assert res.status_code == 200
    assert res.json()["job_id"] == "job-123"


def test_generate_with_research_flag(mock_auth):
    """POST /api/generate accepts use_research flag."""
    mock_insert_response = MagicMock()
    mock_insert_response.data = [{"id": "job-456"}]

    mock_sb = MagicMock()
    mock_sb.table.return_value.insert.return_value.execute.return_value = mock_insert_response

    with patch("web.backend.routes.generate.get_supabase", return_value=mock_sb):
        with patch("web.backend.routes.generate.run_pipeline"):
            from web.backend.app import app
            from fastapi.testclient import TestClient
            c = TestClient(app)
            res = c.post(
                "/api/generate",
                json={"topic": "Latest quantum computing", "use_research": True},
                headers={"Authorization": "Bearer fake-token"},
            )
    assert res.status_code == 200
    assert res.json()["job_id"] == "job-456"


# ─── Tags ───────────────────────────────────────────────────────────


def test_list_tags_empty(client, mock_supabase):
    """GET /api/tags returns empty when no tags exist."""
    res = client.get("/api/tags")
    assert res.status_code == 200
    assert res.json()["tags"] == []


# ─── Views ──────────────────────────────────────────────────────────


def test_record_view(client, mock_supabase):
    """POST /api/videos/{id}/view increments view count."""
    mock_result = MagicMock()
    mock_result.data = {"view_count": 5}
    mock_supabase.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_result

    res = client.post("/api/videos/abc-123/view")
    assert res.status_code == 200
    assert res.json()["ok"] is True


def test_list_videos_most_viewed_sort(client, mock_supabase):
    """GET /api/videos?sort=most_viewed accepts most_viewed sort."""
    res = client.get("/api/videos?sort=most_viewed")
    assert res.status_code == 200


# ─── Models ─────────────────────────────────────────────────────────


def test_video_model_with_tags():
    """Video model accepts tags as list."""
    from web.backend.models import Video
    v = Video(
        id="1", topic="t", title="t", duration_profile="short",
        created_at="2024-01-01", tags=["physics", "math"],
    )
    assert v.tags == ["physics", "math"]


def test_video_model_without_optional_fields():
    """Video model works with minimal required fields."""
    from web.backend.models import Video
    v = Video(id="1", topic="t", title="t", duration_profile="short", created_at="2024-01-01")
    assert v.slug is None
    assert v.tags is None
    assert v.sources is None


def test_generate_request_defaults():
    """GenerateRequest has correct defaults."""
    from web.backend.models import GenerateRequest
    r = GenerateRequest(topic="test")
    assert r.duration.value == "short"
    assert r.use_research is False


def test_generate_request_with_research():
    """GenerateRequest accepts use_research flag."""
    from web.backend.models import GenerateRequest
    r = GenerateRequest(topic="test", use_research=True)
    assert r.use_research is True


def test_generate_request_quality_mode_default():
    """GenerateRequest defaults quality_mode to False."""
    from web.backend.models import GenerateRequest
    r = GenerateRequest(topic="test")
    assert r.quality_mode is False


def test_generate_request_quality_mode_true():
    """GenerateRequest accepts quality_mode=True."""
    from web.backend.models import GenerateRequest
    r = GenerateRequest(topic="test", quality_mode=True)
    assert r.quality_mode is True


# ─── Paper Upload ───────────────────────────────────────────────────


def test_paper_upload_requires_auth(client):
    """POST /api/generate-from-paper requires auth header."""
    res = client.post("/api/generate-from-paper")
    assert res.status_code == 422


def test_paper_upload_blocked_for_non_allowed_user(client):
    """POST /api/generate-from-paper returns 403 for non-allowed users."""
    import io
    with patch(
        "web.backend.routes.generate.get_user_from_token",
        return_value={"sub": "user-123", "email": "someone@example.com"},
    ):
        from web.backend.app import app
        from fastapi.testclient import TestClient
        c = TestClient(app)
        res = c.post(
            "/api/generate-from-paper",
            headers={"Authorization": "Bearer fake-token"},
            files={"file": ("paper.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf")},
            data={"duration": "medium"},
        )
    assert res.status_code == 403
    assert "coming soon" in res.json()["detail"]


def test_paper_upload_allowed_for_admin(client, mock_supabase):
    """POST /api/generate-from-paper works for allowed email."""
    import io
    mock_insert = MagicMock()
    mock_insert.data = [{"id": "paper-job-1"}]

    mock_sb = MagicMock()
    mock_sb.table.return_value.insert.return_value.execute.return_value = mock_insert

    with patch(
        "web.backend.routes.generate.get_user_from_token",
        return_value={"sub": "admin-user", "email": "duggalr42@gmail.com"},
    ):
        with patch("web.backend.routes.generate.get_supabase", return_value=mock_sb):
            with patch("web.backend.routes.generate.run_pipeline"):
                with patch("core.paper.extract_paper_text", return_value={"title": "Test Paper", "text": "content", "num_pages": 5}):
                    from web.backend.app import app
                    from fastapi.testclient import TestClient
                    c = TestClient(app)
                    res = c.post(
                        "/api/generate-from-paper",
                        headers={"Authorization": "Bearer fake-token"},
                        files={"file": ("paper.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf")},
                        data={"duration": "medium"},
                    )
    assert res.status_code == 200
    assert res.json()["job_id"] == "paper-job-1"


def test_paper_upload_rejects_non_pdf(client):
    """POST /api/generate-from-paper rejects non-PDF files."""
    import io
    with patch(
        "web.backend.routes.generate.get_user_from_token",
        return_value={"sub": "admin-user", "email": "duggalr42@gmail.com"},
    ):
        from web.backend.app import app
        from fastapi.testclient import TestClient
        c = TestClient(app)
        res = c.post(
            "/api/generate-from-paper",
            headers={"Authorization": "Bearer fake-token"},
            files={"file": ("doc.txt", io.BytesIO(b"hello"), "text/plain")},
            data={"duration": "medium"},
        )
    assert res.status_code == 400
    assert "PDF" in res.json()["detail"]


# ─── Blog Post URL ──────────────────────────────────────────────────


def test_url_generate_requires_auth(client):
    """POST /api/generate-from-url requires auth header."""
    res = client.post("/api/generate-from-url", json={"url": "https://example.com"})
    assert res.status_code == 422


def test_url_generate_blocked_for_non_allowed_user(client):
    """POST /api/generate-from-url returns 403 for non-allowed users."""
    with patch(
        "web.backend.routes.generate.get_user_from_token",
        return_value={"sub": "user-123", "email": "someone@example.com"},
    ):
        from web.backend.app import app
        from fastapi.testclient import TestClient
        c = TestClient(app)
        res = c.post(
            "/api/generate-from-url",
            json={"url": "https://example.com/post"},
            headers={"Authorization": "Bearer fake-token"},
        )
    assert res.status_code == 403
    assert "coming soon" in res.json()["detail"]


def test_url_generate_rejects_invalid_url(client):
    """POST /api/generate-from-url rejects non-http URLs."""
    with patch(
        "web.backend.routes.generate.get_user_from_token",
        return_value={"sub": "admin-user", "email": "duggalr42@gmail.com"},
    ):
        from web.backend.app import app
        from fastapi.testclient import TestClient
        c = TestClient(app)
        res = c.post(
            "/api/generate-from-url",
            json={"url": "not-a-url"},
            headers={"Authorization": "Bearer fake-token"},
        )
    assert res.status_code == 400
    assert "valid URL" in res.json()["detail"]


def test_url_generate_allowed_for_admin(client, mock_supabase):
    """POST /api/generate-from-url works for allowed email."""
    mock_insert = MagicMock()
    mock_insert.data = [{"id": "url-job-1"}]

    mock_sb = MagicMock()
    mock_sb.table.return_value.insert.return_value.execute.return_value = mock_insert

    with patch(
        "web.backend.routes.generate.get_user_from_token",
        return_value={"sub": "admin-user", "email": "duggalr42@gmail.com"},
    ):
        with patch("web.backend.routes.generate.get_supabase", return_value=mock_sb):
            with patch("web.backend.routes.generate.run_pipeline"):
                with patch("core.blogpost.extract_blogpost", return_value={"title": "Test Post", "text": "content " * 50, "url": "https://example.com/post", "word_count": 50}):
                    from web.backend.app import app
                    from fastapi.testclient import TestClient
                    c = TestClient(app)
                    res = c.post(
                        "/api/generate-from-url",
                        json={"url": "https://example.com/post"},
                        headers={"Authorization": "Bearer fake-token"},
                    )
    assert res.status_code == 200
    assert res.json()["job_id"] == "url-job-1"
