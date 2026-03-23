"""
Research module — determines if a topic needs web search augmentation
and fetches relevant context to improve video accuracy.
"""

import os
from dataclasses import dataclass, field

import anthropic


@dataclass
class ResearchResult:
    """Container for research context to feed into the planner."""
    needed: bool
    query: str = ""
    context: str = ""
    sources: list[dict] = field(default_factory=list)


def needs_research(topic: str, model: str = "claude-sonnet-4-20250514") -> dict:
    """Determine if a topic needs web search augmentation.

    Returns a dict with:
        - needed (bool): whether research is recommended
        - reason (str): why research is/isn't needed
        - search_queries (list[str]): suggested search queries if needed
    """
    client = anthropic.Anthropic()

    response = client.messages.create(
        model=model,
        max_tokens=512,
        system="""You assess whether an educational video topic needs web search augmentation
or if an LLM's training knowledge is sufficient.

Topics that DO need research:
- Recent events, discoveries, or papers (after 2024)
- Highly specific technical details (exact algorithms, specific implementations)
- Niche subjects with limited training data
- Topics where getting facts wrong would be harmful (medical, legal, financial specifics)
- Rapidly evolving fields (AI/ML latest models, current politics, recent scientific breakthroughs)

Topics that DO NOT need research:
- Fundamental science (gravity, thermodynamics, optics)
- Core math concepts (calculus, linear algebra, probability)
- Well-established CS concepts (sorting algorithms, data structures, networking basics)
- Classic explanations (why sky is blue, how encryption works conceptually)
- Historical topics with settled facts

Respond with ONLY valid JSON:
{
    "needed": true/false,
    "reason": "brief explanation",
    "search_queries": ["query 1", "query 2"] // only if needed=true, max 3 queries
}""",
        messages=[
            {"role": "user", "content": f"Topic: {topic}"}
        ],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

    import json
    return json.loads(raw)


def search_web(queries: list[str]) -> ResearchResult:
    """Search the web using Tavily and return structured research context.

    Args:
        queries: List of search queries to run.

    Returns:
        ResearchResult with context and sources.
    """
    tavily_key = os.environ.get("TAVILY_API_KEY")
    if not tavily_key:
        return ResearchResult(needed=True, context="", sources=[])

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=tavily_key)
    except ImportError:
        return ResearchResult(needed=True, context="", sources=[])

    all_results = []
    seen_urls = set()

    for query in queries[:3]:
        try:
            response = client.search(
                query=query,
                search_depth="basic",
                max_results=3,
                include_answer=True,
            )

            if response.get("answer"):
                all_results.append({
                    "type": "answer",
                    "query": query,
                    "content": response["answer"],
                })

            for result in response.get("results", []):
                url = result.get("url", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                all_results.append({
                    "type": "source",
                    "title": result.get("title", ""),
                    "url": url,
                    "content": result.get("content", "")[:500],
                })
        except Exception:
            continue

    # Build context string for the planner
    context_parts = []
    sources = []

    for r in all_results:
        if r["type"] == "answer":
            context_parts.append(f"Summary for '{r['query']}':\n{r['content']}")
        elif r["type"] == "source":
            context_parts.append(f"From {r['title']}:\n{r['content']}")
            sources.append({"title": r["title"], "url": r["url"]})

    return ResearchResult(
        needed=True,
        query=", ".join(queries),
        context="\n\n".join(context_parts),
        sources=sources,
    )


def research_topic(topic: str) -> ResearchResult:
    """Full research pipeline: detect if needed, search if so.

    Args:
        topic: The educational video topic.

    Returns:
        ResearchResult with context (may be empty if research wasn't needed).
    """
    # Step 1: Check if research is needed
    try:
        assessment = needs_research(topic)
    except Exception:
        return ResearchResult(needed=False)

    if not assessment.get("needed", False):
        print(f"  Research not needed: {assessment.get('reason', '')}")
        return ResearchResult(needed=False)

    print(f"  Research needed: {assessment.get('reason', '')}")
    queries = assessment.get("search_queries", [topic])

    # Step 2: Search the web
    result = search_web(queries)
    if result.sources:
        print(f"  Found {len(result.sources)} sources")
    else:
        print(f"  No sources found (Tavily API key may not be set)")

    return result
