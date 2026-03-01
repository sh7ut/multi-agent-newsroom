"""Helpers for deterministic output rendering."""
from __future__ import annotations

from datetime import datetime
from typing import Iterable, List

from services.state import Article


def render_brief(query: str, articles: Iterable[Article], warnings: List[str] | None = None) -> str:
    timestamp = datetime.utcnow().isoformat()
    lines = [f"## Agentic Newsroom Brief — {timestamp}", f'Query: "{query}"', ""]
    for idx, article in enumerate(articles, start=1):
        evidence = ", ".join(article.evidence)
        lines.extend(
            [
                f"{idx}. {article.headline} — {article.source} [{article.source_type}]",
                f"   Link: {article.url}",
                f"   Summary: {article.summary}",
                f"   Evidence: [{evidence}]",
                "",
            ]
        )
    lines.append("Provenance: Real-time data via web_search_premium; archival context via File Archive MCP.")
    if warnings:
        lines.append("Warnings: " + "; ".join(warnings))
    return "\n".join(lines)
