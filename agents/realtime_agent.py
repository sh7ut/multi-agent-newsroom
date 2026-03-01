"""Real-time enrichment agent."""
from __future__ import annotations

from typing import List

from services.state import Article, HandoffContext
from tools.web_search import WebSearchTool


class RealTimeEnrichmentAgent:
    def __init__(self, tool: WebSearchTool | None = None) -> None:
        self.tool = tool or WebSearchTool()

    def gather(self, context: HandoffContext) -> List[Article]:
        results = self.tool.search(context.query)
        required = context.constraints.get("min_results", 5)
        if len(results) < required:
            # simple retry with no source whitelist by instantiating new tool config
            self.tool.config.source_whitelist = None
            results = self.tool.search(context.query)
        return results
