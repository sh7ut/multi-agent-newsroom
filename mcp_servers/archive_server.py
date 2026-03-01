"""Sample MCP server that simulates a historical newspaper archive."""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import List, Optional

from mcp.server.fastmcp import FastMCP

server = FastMCP(
    name="file-archive",
    instructions="Provides historical news snippets from a curated local archive.",
)

_ARCHIVE_DATA = [
    {
        "headline": "Federal Reserve Signals Patience Amid Inflation Concerns",
        "publication": "Archive Times",
        "published_on": "2015-09-17",
        "section": "business",
        "snippet": "Officials opted to hold rates steady while monitoring labor improvements.",
        "pdf_ref": "archive://2015/ft/001",
        "page": "B1",
    },
    {
        "headline": "Global Markets Rally After Surprise Rate Cut",
        "publication": "Financial Herald",
        "published_on": "2012-07-05",
        "section": "markets",
        "snippet": "Central bankers coordinated to ease credit strains.",
        "pdf_ref": "archive://2012/fh/007",
        "page": "A3",
    },
    {
        "headline": "Historic Climate Accord Reached in Paris",
        "publication": "World Courier",
        "published_on": "2015-12-13",
        "section": "world",
        "snippet": "Nearly 200 nations agreed to binding reporting standards.",
        "pdf_ref": "archive://2015/wc/021",
        "page": "A1",
    },
    {
        "headline": "Semiconductor Boom Fueled by Mobile Demand",
        "publication": "Tech Chronicle",
        "published_on": "2010-03-22",
        "section": "technology",
        "snippet": "Chipmakers reported double-digit growth as smartphones surged.",
        "pdf_ref": "archive://2010/tc/004",
        "page": "C2",
    },
    {
        "headline": "Banking Giants Face New Liquidity Rules",
        "publication": "Finance Journal",
        "published_on": "2014-01-10",
        "section": "regulation",
        "snippet": "Supervisors detailed phased capital buffers for SIFIs.",
        "pdf_ref": "archive://2014/fj/011",
        "page": "B4",
    },
]


def _within_range(article_date: str, start_date: Optional[str], end_date: Optional[str]) -> bool:
    value = datetime.fromisoformat(article_date).date()
    if start_date:
        if value < datetime.fromisoformat(start_date).date():
            return False
    if end_date:
        if value > datetime.fromisoformat(end_date).date():
            return False
    return True


def _matches_section(article_section: str, requested_section: Optional[str]) -> bool:
    if not requested_section:
        return True
    return article_section.lower() == requested_section.lower()


def _score(query: str, headline: str, snippet: str) -> int:
    q = query.lower()
    return int(q in headline.lower()) * 2 + int(q in snippet.lower())


@server.tool(name="search_archive", description="Search the historical archive for relevant articles.")
def search_archive(
    query: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    section: Optional[str] = None,
    limit: int = 5,
) -> str:
    """Return a JSON string containing up to `limit` matching articles."""
    scored: List[tuple[int, dict]] = []
    for entry in _ARCHIVE_DATA:
        if not _within_range(entry["published_on"], start_date, end_date):
            continue
        if not _matches_section(entry["section"], section):
            continue
        scored.append((_score(query, entry["headline"], entry["snippet"]), entry))
    scored.sort(key=lambda item: item[0], reverse=True)
    matches = [item[1] for item in scored[: max(1, limit)]]
    return json.dumps({"articles": matches})


if __name__ == "__main__":
    server.run("stdio")
