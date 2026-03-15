# Feedback Round 1 — March 14, 2026

## User Feedback

### 1. Intro scene should feel more welcoming — start with a question on screen
The first scene should open with a compelling question that is visually typed/written
on screen. Not just narrated — the text of the question should appear as the hook.
Think of it like a title card that draws you in. The viewer should read the question
and immediately want to know the answer.

**Example:** For public key cryptography, the screen should show something like:
"How do two strangers share a secret... when everyone is listening?"
written out with a Write() animation, before any diagrams or shapes appear.

**Action:** Update the codegen system prompt to instruct that Scene01 should always
open with the hook question displayed on screen via Write() animation, centered,
before any other visuals appear.

### 2. Text/animations should match narration more precisely
Currently ~98% match, but there are small cases where the visual doesn't quite
sync with what's being said. The animation description in the plan needs to be
more explicit about WHEN things appear relative to the narration.

**Action:** Strengthen the planner prompt to require explicit timing cues like
"As the narrator says X, show Y on screen" and update the codegen prompt to
emphasize that every narrated concept must have a corresponding visual appearing
at the same time.

### 3. How do we compare to existing AI+Manim projects? What can we learn?

---

## Competitive Landscape Analysis

### Existing Projects Reviewed

| Project | Approach | Key Technique |
|---------|----------|---------------|
| **Generative Manim** (marcelo-earth) | Multiple LLM engines, A/B tested | Embeds full Manim docs in system prompt; real-time preview via function calling |
| **TheoremExplainAgent** (TIGER-AI-Lab) | Two-agent (Planner + Coder), academic paper | RAG over Manim docs to prevent API hallucination; formal benchmark (240 theorems) |
| **Manimator** (HyperCluster-Tech) | Three-stage pipeline, ICML 2025 paper | Separate "understanding" and "coding" LLM calls; accepts PDF/arXiv input |
| **manim-shorts** (xtechsouthie) | LangGraph multi-agent state machine | Dual RAG pipelines; multi-model coordination (GPT + Claude) |
| **manim-video-gen** (KrishKrosh) | Straightforward pipeline | Parallel scene rendering via subprocessing |
| **manim-generator** (makefinks) | Writer/reviewer feedback loop | Code review pattern with execution logs |
| **manim-trainer** (SuienS) | Fine-tuning with RL | Visual reward signal — compares rendered frames against expected output |
| **Math-To-Manim** (HarleyCoops) | Claude Code MCP integration | Six-agent workflow; recursive prerequisite discovery |

### Where We Currently Stand

**What we already do well:**
- Clean planner → codegen → render → voice → assemble pipeline (similar to most)
- Retry loop with error feedback (standard across all projects)
- 3B1B design system baked into prompts (unique — most projects don't enforce a visual style)
- Duration control (short/medium/long) — not seen in other projects
- Rich pedagogical prompt with 3B1B teaching philosophy — most projects have generic prompts
- Full end-to-end with voice + subtitles (manim-shorts does this, most others don't)

**What we're missing / could improve:**

#### A. RAG over Manim Documentation (High Impact)
Multiple projects (TheoremExplainAgent, manim-shorts) use RAG over the actual Manim CE
docs to prevent the LLM from hallucinating non-existent API calls. This is the #1 cause
of render failures. We could either:
- Embed key Manim API reference snippets directly in the codegen system prompt (simpler, like Generative Manim does)
- Build a small RAG pipeline that retrieves relevant Manim docs based on the animation description (more robust)

**Recommendation:** Start with embedding a Manim API cheat sheet in the codegen prompt.
This is simpler and avoids retrieval failures. Only move to RAG if we still see API
hallucination issues.

#### B. Parallel Scene Rendering (Medium Impact)
We currently render scenes sequentially. manim-video-gen renders them in parallel via
subprocessing. Since each scene is independent, this is a free speedup — especially for
medium/long videos with 7-14 scenes.

**Recommendation:** Use Python's `concurrent.futures.ProcessPoolExecutor` to render
scenes in parallel. Easy win.

#### C. Visual Preview / Iteration Loop (Medium Impact)
Generative Manim uses function calling to let the LLM preview rendered output and
iterate. We could add a step where after rendering, we send a screenshot of each
scene back to Claude (vision) to verify it looks correct and matches the plan.

**Recommendation:** Post-V1 feature. Nice to have but adds complexity and API cost.

#### D. Separate Models for Planning vs Coding (Low-Medium Impact)
Manimator and manim-shorts use different models optimized for different tasks (e.g.,
GPT for planning, DeepSeek/Claude for code). Our pipeline already separates planning
from coding, so we could experiment with using a stronger model (Opus) for planning
and a faster model (Sonnet) for code generation.

**Recommendation:** Easy to test — just add `--plan-model` and `--code-model` flags.

#### E. Manim API Cheat Sheet in Codegen Prompt (High Impact)
Rather than RAG, embed a concise reference of commonly used Manim CE classes and
methods directly in the codegen system prompt. This prevents the most common failures:
- Wrong argument names (e.g., `x_min` vs `x_range`)
- Deprecated methods
- Non-existent classes
- Wrong import paths

**Recommendation:** Create a curated Manim CE cheat sheet covering: Axes, NumberLine,
MathTex, Text, Arrow, VGroup, common animations (Write, FadeIn, Create, Transform),
and embed it in the codegen prompt. This is what Generative Manim does and it works.

#### F. Better Error Recovery (Medium Impact)
Our retry loop sends the error back to Claude, but TheoremExplainAgent specifically
parses the Python stack trace and provides structured error context. We could improve
our error feedback by:
- Extracting the specific exception type and line number
- Including only the relevant code section around the error
- Adding common fix patterns for known error types

### What Makes Us Different (Potential Advantages)

1. **Pedagogical depth** — Our enriched planner prompt with 3B1B teaching philosophy
   (hook, aha moment, concrete-before-abstract) is more sophisticated than any project
   we found. Most projects focus on code generation quality, not teaching quality.

2. **Full production pipeline** — Voice + subtitles + assembly in one CLI. Most
   projects stop at rendering Manim and don't produce a complete video.

3. **Topic flexibility** — Our prompt explicitly handles non-math topics (networking,
   economics, history) with visual vocabulary guidance. Most projects are math-only.

4. **Duration control** — No other project offers short/medium/long duration profiles.

5. **Design system enforcement** — Consistent visual style across all generated
   videos. Most projects produce visually inconsistent output.

### Priority Improvements (Ordered)

1. **Fix intro scene** (feedback #1) — Easy prompt tweak, big UX impact
2. **Tighten narration-animation sync** (feedback #2) — Prompt refinement
3. **Embed Manim API cheat sheet** in codegen prompt — Reduces render failures
4. **Parallel scene rendering** — Free speedup
5. **Visual verification step** (post-render Claude Vision check) — Future
6. **RAG over Manim docs** — Future, if cheat sheet isn't enough
