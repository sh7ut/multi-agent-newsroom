"""Final response formatter enforcing the PLAN.md contract."""
from __future__ import annotations

from typing import List

from formatting.templates import render_brief
from services.state import Article


class FormatterAgent:
    def __init__(self, min_archive_entries: int = 3) -> None:
        self.min_archive_entries = min_archive_entries

    def format(self, query: str, articles: List[Article]) -> str:
        if len(articles) != 10:
            raise ValueError("Formatter expects exactly 10 articles.")
        archive_count = sum(1 for a in articles if "archive" in a.source_type)
        warnings: List[str] = []
        if archive_count < self.min_archive_entries:
            warnings.append("Archive coverage limited")
        return render_brief(query=query, articles=articles, warnings=warnings)
