"""
FastAPI application for the AI Educational Video Generator.

Wraps the core video generation pipeline with a REST API,
using Supabase for persistence and authentication.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Ensure project root is on sys.path so core/ imports work
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from web.backend.routes import generate, jobs, videos  # noqa: E402

app = FastAPI(
    title="AI Educational Video Generator",
    description="Generate 3Blue1Brown-style educational videos from a topic prompt",
    version="0.1.0",
)

# CORS — allow all origins in development; restrict in production via env config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(videos.router)
app.include_router(generate.router)
app.include_router(jobs.router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}
