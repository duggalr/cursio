"""
Blog Post Extraction -- fetches a URL and extracts article content
using Jina AI Reader (r.jina.ai) which handles JS-rendered pages,
diverse layouts, and returns clean markdown.
"""

import httpx


def extract_blogpost(url: str, timeout: float = 30.0) -> dict:
    """Fetch a blog post URL and extract its content via Jina Reader.

    Returns:
        {"title": str, "text": str, "url": str, "word_count": int}
    """
    response = httpx.get(
        f"https://r.jina.ai/{url}",
        headers={"Accept": "application/json"},
        timeout=timeout,
        follow_redirects=True,
    )
    response.raise_for_status()

    data = response.json()

    title = data.get("data", {}).get("title", "") or ""
    text = data.get("data", {}).get("content", "") or ""

    if not text or len(text.strip()) < 100:
        raise ValueError("Could not extract meaningful content from this URL")

    # Truncate to ~50k chars to fit in Claude context
    if len(text) > 50000:
        text = text[:50000] + "\n\n[Article truncated]"

    return {
        "title": title,
        "text": text,
        "url": url,
        "word_count": len(text.split()),
    }
