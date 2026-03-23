"""
Shared test fixtures for Curiso backend tests.

Uses FastAPI's TestClient with mocked Supabase calls so tests
run without a real database or API keys.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set dummy env vars before importing app (prevents KeyError on import)
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("ELEVENLABS_API_KEY", "test-key")


@pytest.fixture
def mock_supabase():
    """Mock the Supabase client so no real DB calls are made."""
    mock_client = MagicMock()

    # Default: table().select().execute() returns empty data
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.select.return_value = mock_table
    mock_table.insert.return_value = mock_table
    mock_table.update.return_value = mock_table
    mock_table.delete.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.in_.return_value = mock_table
    mock_table.or_.return_value = mock_table
    mock_table.contains.return_value = mock_table
    mock_table.not_.return_value = mock_table
    mock_table.is_.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.range.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.single.return_value = mock_table

    mock_response = MagicMock()
    mock_response.data = []
    mock_response.count = 0
    mock_table.execute.return_value = mock_response

    with patch("web.backend.supabase_client.create_client", return_value=mock_client):
        with patch("web.backend.supabase_client.get_supabase", return_value=mock_client):
            yield mock_client


@pytest.fixture
def client(mock_supabase):
    """Return a FastAPI TestClient with mocked Supabase."""
    from web.backend.app import app
    return TestClient(app)


@pytest.fixture
def mock_auth(mock_supabase):
    """Mock auth to return a fake user for authenticated endpoints."""
    with patch(
        "web.backend.supabase_client.get_user_from_token",
        return_value={"sub": "test-user-id", "email": "test@example.com"},
    ):
        yield
