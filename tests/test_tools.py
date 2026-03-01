from datetime import datetime, timezone

from services.state import Article
from tools.web_search import WebSearchTool
from tools.mcp_archive import ArchiveTool


class StubWebTransport:
    def search(self, query, config):
        return [
            {
                "headline": "Test Headline",
                "source": "Reuters",
                "url": "https://example.com",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "summary": "Summary",
                "confidence": 0.9,
            }
        ]


class StubArchiveTransport:
    def search(self, query, config):
        return {
            "articles": [
                {
                    "headline": "Archive Story",
                    "publication": "Archive Times",
                    "published_on": "2020-01-01",
                    "snippet": "Historic snippet",
                    "pdf_ref": "archive://001",
                }
            ]
        }


def test_web_search_tool_normalizes_results():
    tool = WebSearchTool(transport=StubWebTransport())
    articles = tool.search("economy")
    assert len(articles) == 1
    assert isinstance(articles[0], Article)
    assert articles[0].source_type == "realtime"


def test_archive_tool_normalizes_results():
    tool = ArchiveTool(transport=StubArchiveTransport())
    articles = tool.search("economy")
    assert len(articles) == 1
    assert articles[0].source_type == "archive"
