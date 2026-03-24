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


def plan_paper_video(
    paper_text: str,
    paper_title: str = "",
    duration: str = "medium",
    max_scenes: int | None = None,
    model: str = "claude-sonnet-4-20250514",
) -> dict:
    """Create a video scene plan from a research paper.

    Unlike topic-based planning where Claude creates content from scratch,
    this extracts and restructures existing paper content into an engaging
    educational video format.

    Args:
        max_scenes: Cap the number of scenes (useful for testing).
    """
    client = anthropic.Anthropic()

    duration_configs = {
        "short": {"scenes": "4-5", "time": "2-3 minutes"},
        "medium": {"scenes": "6-8", "time": "5-7 minutes"},
        "long": {"scenes": "10-14", "time": "8-12 minutes"},
    }
    config = duration_configs.get(duration, duration_configs["medium"])

    prompt = f"""Create a scene plan for a {config['time']}, {config['scenes']} scene educational video
explaining this research paper to a broad audience.

## Paper Title
{paper_title}

## Paper Content
{paper_text}

## Your Task

Transform this paper into an engaging educational video that:
1. Opens with a compelling hook — what problem does this paper solve? Why should anyone care?
2. Explains the key insight at an intuitive level — no jargon without explanation
3. Walks through the methodology using visual analogies
4. Presents key results with clear visual representations
5. Ends with implications — what does this mean for the field and the world?

DO NOT just summarize section by section. Restructure for maximum educational impact.
Make a curious non-expert understand and care about this research.

Respond with ONLY valid JSON:
{{
  "topic": "paper title or core topic",
  "title": "A catchy, accessible video title (NOT the paper's academic title)",
  "aha_moment": "The one key insight viewers will remember",
  "scenes": [
    {{
      "id": 1,
      "narration": "Exact narration text",
      "animation_description": "Detailed Manim animation description"
    }}
  ]
}}"""

    response = client.messages.create(
        model=model,
        max_tokens=8192,
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
