"""
Research Paper Processing — extracts text from PDFs and creates
paper-specific scene plans for educational video generation.
"""

import json
from pathlib import Path

import anthropic


def extract_paper_text(pdf_path: Path, max_pages: int = 30) -> dict:
    """Extract text and metadata from a research paper PDF.

    Returns:
        {"title": str, "text": str, "num_pages": int}
    """
    import pdfplumber

    pages_text = []
    title = ""

    with pdfplumber.open(pdf_path) as pdf:
        num_pages = min(len(pdf.pages), max_pages)
        for i, page in enumerate(pdf.pages[:max_pages]):
            text = page.extract_text() or ""
            pages_text.append(text)

            # Use first page's first line as title guess
            if i == 0 and text.strip():
                lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
                if lines:
                    title = lines[0][:200]

    full_text = "\n\n".join(pages_text)

    # Truncate to ~50k chars to fit in Claude context
    if len(full_text) > 50000:
        full_text = full_text[:50000] + "\n\n[Paper truncated — remaining pages omitted]"

    return {
        "title": title,
        "text": full_text,
        "num_pages": num_pages,
    }


PAPER_PLANNER_PROMPT = """You are a world-class technical educator who creates \
in-depth animated video explanations of research papers. Your audience is \
technical: researchers, engineers, and graduate students who understand the \
fundamentals but want a clear visual walkthrough of this specific paper.

## Your Approach

You do NOT dumb things down. You preserve technical depth while making the \
paper's contribution crystal clear through structured visual explanation. \
Think of your videos as "the talk the authors should have given" at a top \
conference -- rigorous, visual, and compelling.

## Video Structure (follow this framework)

### Opening (1-2 scenes)
- Hook: What real-world problem does this paper address? Why now?
- Context: What was the state of the art before this paper? What were the \
  limitations of previous approaches? Name specific prior work if mentioned.

### Core Contribution (2-3 scenes)
- Key Insight: What is the fundamental idea? Explain it precisely.
- Architecture/Method: Walk through the method step by step with detailed \
  diagrams. If there's a model architecture, show each component. If there's \
  an algorithm, animate it. Show the actual equations with MathTex and explain \
  each term.
- What Makes It Different: Direct visual comparison to the baseline approach. \
  Show exactly what changed and why it matters.

### Technical Details (2-4 scenes)
- Training/Optimization: How is the model trained? What loss function? \
  What are the key hyperparameters or design choices?
- Key Equations: Show the important mathematical formulations. Animate each \
  term appearing with its explanation. Use color coding for different terms.
- Ablations/Design Choices: What did the authors try? What worked and didn't? \
  Show this as a comparison table or chart.

### Results (2-3 scenes)
- Quantitative Results: Show actual numbers from the paper. Animate bar charts \
  or tables comparing to baselines. Use specific dataset names and metrics.
- Qualitative Results: If applicable, show examples of inputs/outputs.
- Surprising Findings: Anything unexpected in the results?

### Closing (1-2 scenes)
- Limitations: What doesn't this approach handle? Be honest.
- Impact: What does this enable? What research directions does it open?
- Key Takeaway: One sentence the viewer will remember.

## Narration Style
- Technical but clear. Use proper terminology.
- "The authors propose..." / "This architecture uses..." / "The key insight is..."
- Include specific numbers: "achieving 94.3% accuracy, a 7.2 point improvement"
- Reference specific sections of the paper when relevant
- Each scene narration should be 4-6 sentences for depth

## Animation Style
- Architecture diagrams with labeled components
- Equation build-ups showing each term with color coding
- Bar charts and comparison tables with actual paper numbers
- Flow diagrams showing data/information flow
- Before/after comparisons with prior methods
- Use arrows, highlights, and annotations extensively"""


def plan_paper_video(
    paper_text: str,
    paper_title: str = "",
    duration: str = "long",
    max_scenes: int | None = None,
    model: str = "claude-sonnet-4-20250514",
) -> dict:
    """Create a video scene plan from a research paper.

    Produces a technically deep video plan targeting researchers and engineers.
    Default duration is "long" (10-14 scenes, 8-12 minutes).

    Args:
        max_scenes: Cap the number of scenes (useful for testing).
    """
    client = anthropic.Anthropic()

    duration_configs = {
        "short": {"scenes": "4-5", "time": "2-3 minutes"},
        "medium": {"scenes": "6-8", "time": "5-7 minutes"},
        "long": {"scenes": "10-14", "time": "8-12 minutes"},
    }
    config = duration_configs.get(duration, duration_configs["long"])

    prompt = f"""Create a scene plan for a {config['time']}, {config['scenes']} scene technical video \
explaining this research paper.

## Paper Title
{paper_title}

## Paper Content
{paper_text}

## Requirements
- Follow the video structure framework from your instructions precisely
- Target {config['scenes']} scenes, each 30-60 seconds of narration (4-6 sentences each)
- Include actual numbers, metrics, and dataset names from the paper
- Show key equations using MathTex with term-by-term explanation
- Animate architecture diagrams with labeled components
- Include quantitative comparison charts with baselines

Respond with ONLY valid JSON:
{{
  "topic": "paper title or core topic",
  "title": "A compelling video title that conveys the contribution",
  "aha_moment": "The key technical insight viewers will remember",
  "scenes": [
    {{
      "id": 1,
      "narration": "Detailed narration text (4-6 sentences)",
      "animation_description": "Detailed Manim animation description with specific visual elements"
    }}
  ]
}}"""

    response = client.messages.create(
        model=model,
        max_tokens=16384,
        system=PAPER_PLANNER_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    plan = json.loads(raw)

    # Cap scenes if max_scenes is set (useful for local testing)
    if max_scenes and len(plan.get("scenes", [])) > max_scenes:
        plan["scenes"] = plan["scenes"][:max_scenes]

    return plan
