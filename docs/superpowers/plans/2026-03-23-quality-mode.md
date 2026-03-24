# Quality Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Quality Mode" toggle to Curiso that generates higher-quality videos by splitting scenes into individual files, visually inspecting each rendered scene, iterating on failures, and generating audio last to match animation timing.

**Architecture:** New `core/quality_pipeline.py` module implements the enhanced pipeline: per-scene codegen → render preview → extract frames → Claude evaluates quality → fix and re-render if needed → final render → adjust narration to match durations → voice → assemble. The existing `run_pipeline` in `worker.py` branches on `quality_mode` flag. Frontend adds a toggle. Eval script compares quality mode vs baseline on the same 5 topics.

**Tech Stack:** Python, FastAPI, Anthropic Claude API, Manim, FFmpeg, Next.js/React

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `core/quality_pipeline.py` | Create | Per-scene codegen, render, inspect, iterate loop + narration adjustment |
| `core/codegen.py` | Modify | Add `generate_single_scene_code()` for one scene at a time |
| `core/planner.py` | Modify | Add `adjust_narration_for_duration()` to rewrite narration to target duration |
| `web/backend/models.py` | Modify | Add `quality_mode` to `GenerateRequest` |
| `web/backend/routes/generate.py` | Modify | Pass `quality_mode` to job row |
| `web/backend/worker.py` | Modify | Branch on `quality_mode` flag to call quality pipeline |
| `web/frontend/app/page.tsx` | Modify | Add quality mode toggle |
| `web/frontend/lib/api.ts` | Modify | Pass `quality_mode` param |
| `generate.py` | Modify | Add `--quality` CLI flag |
| `eval/run_quality_ab.py` | Create | A/B eval: baseline vs quality mode on same 5 topics |
| `tests/test_quality_pipeline.py` | Create | Unit tests for quality pipeline functions |

---

### Task 1: Per-Scene Code Generation

**Files:**
- Modify: `core/codegen.py`
- Test: `tests/test_quality_pipeline.py`

- [ ] **Step 1: Add `generate_single_scene_code()` to codegen.py**

Add a function that generates Manim code for ONE scene as a standalone file. This is different from the existing `generate_manim_code()` which generates all scenes in one file.

```python
def generate_single_scene_code(
    plan: dict,
    scene_index: int,
    model: str = "claude-sonnet-4-20250514",
) -> str:
    """Generate standalone Manim code for a single scene.

    Returns a complete Python file with one Scene class that can be
    rendered independently.
    """
```

The function:
- Takes the full plan (for context) but generates code for only `plan["scenes"][scene_index]`
- Uses the same `CODEGEN_SYSTEM_PROMPT` and `DESIGN_SYSTEM`
- Does NOT include timing constraints (visuals-first approach)
- Tells Claude: "Make the animation feel natural. Use generous pacing."
- Returns a standalone file: `from manim import *\n\nclass Scene01(Scene): ...`

- [ ] **Step 2: Write test for single scene codegen**

```python
# tests/test_quality_pipeline.py
def test_generate_single_scene_code_returns_standalone():
    """Single scene codegen returns a complete standalone Python file."""
    # Mock the Claude API call
    ...
```

- [ ] **Step 3: Commit**

```bash
git add core/codegen.py tests/test_quality_pipeline.py
git commit -m "feat: add per-scene code generation for quality mode"
```

---

### Task 2: Visual Quality Inspector

**Files:**
- Create: `core/quality_pipeline.py`
- Test: `tests/test_quality_pipeline.py`

- [ ] **Step 1: Create `core/quality_pipeline.py` with `inspect_scene_quality()`**

This function takes a rendered video, extracts frames, sends them to Claude, and gets a quality assessment back.

```python
def inspect_scene_quality(
    video_path: Path,
    scene_plan: dict,
) -> dict:
    """Inspect rendered scene quality using Claude vision.

    Extracts 3-4 frames from the video and asks Claude to evaluate:
    - Text readability (no cut-off, no overlap)
    - Visual clarity (clean layout, no empty screens)
    - Animation presence (not just static text)
    - Overall quality score (1-10)

    Returns:
        {
            "score": 7,
            "pass": True,  # score >= 6
            "issues": ["Text overlaps at 0:15", ...],
            "suggestions": ["Add more visual elements", ...]
        }
    """
```

- [ ] **Step 2: Add `generate_and_inspect_scene()` — the core quality loop**

This orchestrates: codegen → render → inspect → fix → re-render for a single scene.

```python
def generate_and_inspect_scene(
    plan: dict,
    scene_index: int,
    output_dir: Path,
    max_iterations: int = 3,
    quality_threshold: int = 6,
) -> tuple[Path | None, str, float]:
    """Generate, render, and iterate on a single scene until quality passes.

    Returns:
        (video_path, final_code, duration) or (None, code, 0) if all attempts fail.
    """
```

The loop:
1. `generate_single_scene_code()` → write to `scene_XX.py`
2. `render_scene()` with preview quality
3. `inspect_scene_quality()` on the rendered video
4. If score < threshold and iterations left: send issues back to Claude via `fix_manim_code()` with the visual feedback
5. If passes: do final quality render (`-qm`)
6. Return video path and its actual duration

- [ ] **Step 3: Add `adjust_narration_for_duration()` to planner.py**

After all scenes are rendered, we know exact durations. This function rewrites narration to match.

```python
def adjust_narration_for_duration(
    original_narration: str,
    target_duration: float,
    topic_context: str = "",
    model: str = "claude-sonnet-4-20250514",
) -> str:
    """Rewrite narration to match a target audio duration.

    At ~2.5 words/second, calculates target word count and asks Claude
    to expand or trim the narration to fit while preserving meaning.
    """
```

- [ ] **Step 4: Add `run_quality_pipeline()` — the full orchestrator**

```python
def run_quality_pipeline(
    plan: dict,
    output_dir: Path,
    on_progress: callable | None = None,
) -> dict:
    """Run the full quality mode pipeline.

    Steps:
    1. Generate + inspect each scene (with quality loop)
    2. Get actual durations from rendered videos
    3. Adjust narrations to match durations
    4. Generate voice audio
    5. Assemble final video

    Returns:
        {
            "scene_videos": [Path, ...],
            "scene_durations": [float, ...],
            "narrations": [str, ...],  # adjusted
            "final_path": Path,
        }
    """
```

- [ ] **Step 5: Write tests**

Test `inspect_scene_quality` returns correct structure, `adjust_narration_for_duration` calculates word count correctly, etc.

- [ ] **Step 6: Commit**

```bash
git add core/quality_pipeline.py core/planner.py tests/test_quality_pipeline.py
git commit -m "feat: add quality pipeline with visual inspection loop"
```

---

### Task 3: Backend Integration

**Files:**
- Modify: `web/backend/models.py`
- Modify: `web/backend/routes/generate.py`
- Modify: `web/backend/worker.py`

- [ ] **Step 1: Add `quality_mode` to GenerateRequest and job row**

In `models.py`:
```python
class GenerateRequest(BaseModel):
    topic: str
    duration: DurationProfile = DurationProfile.short
    use_research: bool = False
    quality_mode: bool = False
```

In `routes/generate.py`, add `"quality_mode": body.quality_mode` to `job_row`.

- [ ] **Step 2: Branch worker on quality_mode**

In `worker.py`, after fetching job details:
```python
quality_mode: bool = job.get("quality_mode", False)
```

After planning, if `quality_mode`:
```python
if quality_mode:
    from core.quality_pipeline import run_quality_pipeline
    result = run_quality_pipeline(plan, out_dir, on_progress=lambda msg: _update_job(job_id, progress_message=msg))
    # result contains scene_videos, narrations, final_path, etc.
    # Skip to voice + assembly using result data
else:
    # existing pipeline (unchanged)
```

- [ ] **Step 3: Commit**

```bash
git add web/backend/models.py web/backend/routes/generate.py web/backend/worker.py
git commit -m "feat: integrate quality pipeline into backend worker"
```

---

### Task 4: Frontend Toggle

**Files:**
- Modify: `web/frontend/lib/api.ts`
- Modify: `web/frontend/app/page.tsx`

- [ ] **Step 1: Add `qualityMode` param to API client**

In `api.ts`, update `generateVideo()`:
```typescript
export async function generateVideo(
  topic: string,
  duration: string,
  token: string,
  useResearch: boolean = false,
  qualityMode: boolean = false,
): Promise<{ job_id: string }> {
  // ...
  body: JSON.stringify({ topic, duration, use_research: useResearch, quality_mode: qualityMode }),
```

- [ ] **Step 2: Add quality mode toggle to homepage**

Add state: `const [qualityMode, setQualityMode] = useState(false);`

Add toggle next to the web search toggle (similar style):
```tsx
<button type="button" onClick={() => setQualityMode(!qualityMode)} ...>
  <span>toggle switch</span>
  Quality mode
  <span>(slower, higher quality)</span>
</button>
```

Pass to `generateVideo()`: `generateVideo(topic, duration, session.access_token, useResearch, qualityMode)`

- [ ] **Step 3: Commit**

```bash
git add web/frontend/lib/api.ts web/frontend/app/page.tsx
git commit -m "feat: add quality mode toggle to frontend"
```

---

### Task 5: CLI Support

**Files:**
- Modify: `generate.py`

- [ ] **Step 1: Add `--quality` flag to CLI**

```python
parser.add_argument("--quality", action="store_true", help="Use quality mode (per-scene iteration, visuals-first)")
```

When `args.quality`:
```python
from core.quality_pipeline import run_quality_pipeline
result = run_quality_pipeline(plan, out_dir)
```

- [ ] **Step 2: Commit**

```bash
git add generate.py
git commit -m "feat: add --quality flag to CLI"
```

---

### Task 6: Evaluation Script

**Files:**
- Create: `eval/run_quality_ab.py`

- [ ] **Step 1: Create A/B eval comparing baseline vs quality mode**

Uses the same 5 `BASELINE_TOPICS` from `run_baseline.py`. For each topic:
1. Generate with baseline (existing pipeline, no-voice)
2. Generate with quality mode (new pipeline, no-voice)
3. Evaluate both with multimodal scorer
4. Print side-by-side comparison

Output structure:
```
eval/runs/quality_ab_YYYY-MM-DD/
  <topic_slug>/
    baseline/   (plan, scenes, video, frames, eval)
    quality/    (plan, per-scene files, video, frames, eval)
  summary.json
```

- [ ] **Step 2: Commit**

```bash
git add eval/run_quality_ab.py
git commit -m "feat: add quality mode A/B evaluation script"
```

---

### Task 7: DB Migration + Tests

**Files:**
- Create: `docs/add_quality_mode_column.sql`
- Modify: `tests/test_api.py`

- [ ] **Step 1: Create SQL migration**

```sql
ALTER TABLE generation_jobs ADD COLUMN IF NOT EXISTS quality_mode boolean DEFAULT false;
```

- [ ] **Step 2: Add tests for quality_mode in API**

```python
def test_generate_with_quality_mode(client, mock_auth, mock_supabase):
    """POST /api/generate accepts quality_mode flag."""
    ...

def test_generate_request_quality_mode_default():
    """GenerateRequest defaults quality_mode to False."""
    from web.backend.models import GenerateRequest
    r = GenerateRequest(topic="test")
    assert r.quality_mode is False
```

- [ ] **Step 3: Commit**

```bash
git add docs/add_quality_mode_column.sql tests/test_api.py
git commit -m "feat: add quality_mode DB migration and API tests"
```
