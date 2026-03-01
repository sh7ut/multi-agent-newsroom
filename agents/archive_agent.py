"""Archive depth agent backed by MCP."""
from __future__ import annotations

from datetime import date, timedelta
from typing import List

from services.state import Article, HandoffContext
from tools.mcp_archive import ArchiveConfig, ArchiveTool


class ArchiveDepthAgent:
    def __init__(self, tool: ArchiveTool | None = None) -> None:
        self.tool = tool or ArchiveTool()

    def gather(self, context: HandoffContext) -> List[Article]:
        articles = self.tool.search(context.query)
        if len(articles) >= context.constraints.get("min_archive_results", 3):
            return articles
        # widen window and retry once
        config = self.tool.config
        if not config.start_date or not config.end_date:
            today = date.today()
            config.start_date = (today - timedelta(days=365)).isoformat()
            config.end_date = today.isoformat()
        return self.tool.search(context.query)
