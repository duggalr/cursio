# Web App Implementation Plan

## Overview

Turn the CLI educational video generator into a web app where anyone can browse
AI-generated educational videos and authenticated users can generate their own.

## Architecture

```
User (browser)
    │
    ▼
┌─── Frontend (Next.js) ──────────────────────────────┐
│  Home/Gallery  │  Generate Page  │  Video Page       │
│  (public)      │  (auth required)│  (public)         │
└──────────────────────────────────────────────────────┘
    │
    ▼
┌─── Backend (FastAPI) ────────────────────────────────┐
│  /api/videos        GET    — list/search videos      │
│  /api/videos/:id    GET    — get video + metadata     │
│  /api/generate      POST   — submit generation job   │
│  /api/jobs/:id      GET    — poll job status          │
└──────────────────────────────────────────────────────┘
    │                          │
    ▼                          ▼
┌─── Supabase ───┐    ┌─── Background Worker ─────────┐
│  Auth (users)  │    │  Picks up jobs from queue      │
│  DB (Postgres) │    │  Runs core/ pipeline           │
│  Storage (S3)  │    │  Updates job status in DB      │
│                │    │  Uploads video to storage      │
└────────────────┘    └────────────────────────────────┘
                              │
                              ▼
                      ┌─── core/ ─────────────────────┐
                      │  planner.py                    │
                      │  codegen.py                    │
                      │  renderer.py                   │
                      │  voice.py                      │
                      │  subtitles.py                  │
                      │  assembler.py                  │
                      └────────────────────────────────┘
```

## Project Directory Structure

```
ai_educational_video_generation/
├── core/                       # Shared pipeline logic
│   ├── __init__.py
│   ├── planner.py
│   ├── codegen.py
│   ├── renderer.py
│   ├── voice.py
│   ├── subtitles.py
│   └── assembler.py
├── cli/                        # CLI tool (thin wrapper around core/)
│   ├── generate.py
│   └── requirements.txt
├── web/
│   ├── backend/
│   │   ├── app.py              # FastAPI app
│   │   ├── worker.py           # Background job processor
│   │   ├── models.py           # Pydantic models + DB schema
│   │   ├── routes/
│   │   │   ├── videos.py       # /api/videos endpoints
│   │   │   ├── generate.py     # /api/generate endpoint
│   │   │   └── jobs.py         # /api/jobs endpoints
│   │   ├── supabase_client.py  # Supabase SDK wrapper
│   │   └── requirements.txt
│   └── frontend/
│       ├── package.json
│       ├── app/                # Next.js app router
│       │   ├── page.tsx        # Home / Gallery
│       │   ├── generate/
│       │   │   └── page.tsx    # Generate form + progress
│       │   ├── video/
│       │   │   └── [id]/
│       │   │       └── page.tsx # Individual video page
│       │   └── layout.tsx
│       ├── components/
│       │   ├── VideoCard.tsx
│       │   ├── VideoPlayer.tsx
│       │   ├── GenerateForm.tsx
│       │   ├── ProgressTracker.tsx
│       │   └── Navbar.tsx
│       └── lib/
│           ├── supabase.ts     # Supabase client (auth + data)
│           └── api.ts          # Backend API client
├── docs/
│   ├── web_app_implementation_plan.md
│   └── business_plan.md
├── .env
└── README.md
```

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | Next.js (App Router) | SSR for SEO (gallery pages need to rank), React ecosystem |
| Backend | FastAPI | Async, lightweight, great Python ecosystem for AI/ML |
| Auth | Supabase Auth | Simple, handles email/password + OAuth, free tier generous |
| Database | Supabase (Postgres) | Managed, generous free tier, real-time subscriptions |
| Storage | Supabase Storage (S3) | Co-located with DB, simple SDK |
| Worker | Celery + Redis | Battle-tested job queue; could start with simple asyncio |
| Hosting | Vercel (frontend) + Railway/Fly.io (backend + worker) | Easy deployment, reasonable pricing |

## Database Schema (Supabase/Postgres)

```sql
-- Users managed by Supabase Auth (auth.users)

create table videos (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id),
    topic text not null,
    title text not null,
    duration_profile text not null,       -- 'short', 'medium', 'long'
    aha_moment text,
    plan jsonb,                           -- full scene plan
    narration_text text,                  -- full narration (for SEO)
    video_url text,                       -- Supabase Storage URL
    thumbnail_url text,
    video_duration_seconds float,
    status text default 'completed',
    view_count int default 0,
    created_at timestamptz default now()
);

create table generation_jobs (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references auth.users(id),
    topic text not null,
    duration_profile text not null,
    status text default 'queued',         -- queued, planning, generating, rendering, voiceover, assembling, completed, failed
    progress_message text,                -- "Rendering scene 3 of 7..."
    video_id uuid references videos(id),  -- set when complete
    error_message text,                   -- set on failure
    created_at timestamptz default now(),
    completed_at timestamptz
);

-- Index for gallery browsing
create index idx_videos_created on videos(created_at desc);
create index idx_videos_topic on videos using gin(to_tsvector('english', topic || ' ' || title));

-- Rate limiting: count user's videos today
create or replace function user_videos_today(uid uuid)
returns int as $$
    select count(*)::int from generation_jobs
    where user_id = uid
    and created_at > now() - interval '24 hours'
    and status != 'failed';
$$ language sql;
```

## Key Implementation Details

### Video Generation Flow

1. User submits topic + duration on frontend
2. Frontend calls `POST /api/generate` with Supabase auth token
3. Backend:
   - Validates auth token via Supabase
   - Checks rate limit (5 videos/day)
   - Creates a `generation_jobs` row (status: `queued`)
   - Enqueues the job for the background worker
   - Returns job ID
4. Frontend polls `GET /api/jobs/:id` every 3 seconds, shows progress
5. Worker picks up job, runs pipeline:
   - Updates status to `planning` → calls `core/planner.py`
   - Updates status to `generating` → calls `core/codegen.py`
   - Updates status to `rendering` → calls `core/renderer.py` (per scene)
   - Updates status to `voiceover` → calls `core/voice.py`
   - Updates status to `assembling` → calls `core/assembler.py`
   - Uploads final.mp4 + thumbnail to Supabase Storage
   - Creates `videos` row, updates job to `completed`
6. Frontend detects completion, redirects to video page

### Gallery / Home Page

- Grid of VideoCards showing thumbnail, title, duration badge
- Full-text search on topic + title
- Sort by: Recent, Popular (view_count)
- Infinite scroll or pagination
- SSR for SEO — each video page is server-rendered with meta tags

### Video Page

- Video player (HTML5 <video> or a lightweight player)
- Title, topic, duration, created date
- Full narration text below (good for SEO + accessibility)
- Share button (copy link, Twitter, etc.)
- "Generate your own" CTA

### Auth Flow

- "Sign up" / "Log in" buttons in navbar
- Supabase Auth with email/password (add Google OAuth later)
- Unauthenticated users can browse gallery and watch videos
- Generating requires auth — show sign-up modal if unauthenticated user clicks "Generate"

## Implementation Phases

### Phase 1: Core extraction + backend MVP
- Extract `src/` into `core/` module
- Set up FastAPI with generate + videos + jobs endpoints
- Set up Supabase project (auth, DB, storage)
- Background worker with simple queue
- Test: can submit a job via API and get a video back

### Phase 2: Frontend MVP
- Next.js app with 3 pages (home, generate, video)
- Supabase Auth integration
- Job progress polling UI
- Basic gallery grid
- Test: full flow from browser

### Phase 3: Polish
- Search + filtering on gallery
- Thumbnail generation (screenshot from video at 5s mark)
- SEO meta tags + sitemap
- Rate limit enforcement
- Error states and retry UI
- Mobile responsive

### Phase 4: Deploy
- Deploy frontend to Vercel
- Deploy backend + worker to Railway or Fly.io
- Set up production Supabase project
- Domain + SSL
- Seed gallery with 30+ pre-generated videos
