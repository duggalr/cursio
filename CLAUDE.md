# Curiso — AI Educational Video Generator

## Project Overview

Curiso generates 3Blue1Brown-style educational videos from natural language prompts. It combines Claude AI for planning/code generation, Manim for mathematical animations, ElevenLabs for narration, and FFmpeg for video assembly.

## Architecture

Three layers:

- **Core Pipeline** (`core/`): 6-stage video generation — planner, codegen, renderer, voice, subtitles, assembler
- **CLI** (`generate.py`): Command-line wrapper around the core pipeline
- **Web App** (`web/`): Next.js frontend + FastAPI backend with Supabase for auth/db/storage

### Pipeline Stages

1. `core/planner.py` — Claude breaks topic into scenes with narration + animation descriptions
2. `core/codegen.py` — Claude writes Manim Python code; includes retry loop on render errors (max 3)
3. `core/renderer.py` — Executes `manim render` via subprocess, produces MP4 per scene
4. `core/voice.py` — ElevenLabs TTS converts narration to MP3
5. `core/subtitles.py` — Generates timed SRT captions
6. `core/assembler.py` — FFmpeg syncs video/audio, concatenates scenes, burns subtitles

### Data Flow

```
Frontend (Next.js) → POST /api/generate → Backend (FastAPI)
  → Creates generation_jobs row → Background worker runs core pipeline
  → Uploads to Supabase Storage → Creates videos row
Frontend polls GET /api/jobs/:id every 3s for progress
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4, Motion (Framer Motion) |
| Backend | FastAPI, Uvicorn, Python 3.11+ |
| Database | Supabase (Postgres) |
| Storage | Supabase Storage (S3-compatible) |
| Auth | Supabase Auth (JWT) |
| AI | Anthropic Claude (Opus for planning, Sonnet for coding) |
| Animation | Manim Community Edition |
| TTS | ElevenLabs |
| Video | FFmpeg |

## Key Directories

```
core/               # Shared pipeline modules (Python)
web/backend/        # FastAPI app, worker, routes, models
web/frontend/       # Next.js app (App Router)
  app/              # Pages (home gallery, video/[id])
  components/       # React components (AuthModal, Navbar, VideoCard, etc.)
  lib/              # API client (api.ts), Supabase client (supabase.ts)
docs/               # Design docs, implementation plan, business plan
output/             # Generated video artifacts (gitignored)
```

## API Endpoints

- `POST /api/generate` — Submit video generation (auth required, 5/day rate limit)
- `GET /api/jobs/{job_id}` — Poll job status (queued → planning → generating → rendering → voiceover → assembling → completed/failed)
- `GET /api/videos` — List videos (search, sort, pagination)
- `GET /api/videos/{id}` — Single video metadata + like count
- `POST/DELETE /api/videos/{id}/like` — Like/unlike (auth required)
- `GET /api/health` — Health check

## Database Tables

- `videos` — id, user_id, topic, title, video_url, thumbnail_url, duration, view_count, etc.
- `generation_jobs` — id, user_id, topic, status, progress_message, video_id, error_message
- `likes` — id, video_id, user_id (unique constraint on video_id + user_id)

## Environment Variables

Required in `.env`:
- `ANTHROPIC_API_KEY` — Claude API access
- `ELEVENLABS_API_KEY` — TTS generation
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_KEY` — Supabase anon key
- `SUPABASE_JWT_SECRET` — JWT validation

Optional:
- `ELEVENLABS_VOICE_ID` — Override default voice

## Common Commands

```bash
# CLI usage
python generate.py "Explain the derivative"
python generate.py "Topic" --scenes-only          # Plan only
python generate.py --from-plan output/topic/plan.json  # Resume from plan
python generate.py "Topic" --no-voice --preview    # Fast preview, no audio

# Backend
cd web/backend && uvicorn app:app --reload --port 8000

# Frontend
cd web/frontend && npm run dev                     # Dev server (port 3000)
cd web/frontend && npm run build                   # Production build

# Dependencies
pip install -r requirements.txt                    # Core + CLI
pip install -r web/backend/requirements.txt        # Backend extras
cd web/frontend && npm install                     # Frontend
```

## Design System (Baked into Manim Codegen)

- Background: `#1C1C2E`
- Text: `#FFFFFF`
- Accents: Yellow `#FFFF00`, Blue `#58C4DD`, Green `#83C167`, Red `#FC6255`
- Fonts: CMU Serif (math), Source Sans Pro (text)

## Key Design Decisions

- Polling (3s intervals) over WebSockets for job progress — simpler, sufficient for this use case
- Denormalized like counts on videos table for query performance
- Background worker processes jobs sequentially (no Celery/Redis — Supabase-backed queue)
- Output directories are self-contained per generation run (`output/web_{job_id}_{slug}/`)
- Codegen includes a retry loop: if Manim render fails, error is sent back to Claude for fix (max 3 attempts)
