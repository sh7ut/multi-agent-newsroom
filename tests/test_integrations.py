from datetime import datetime, timezone

from agents.archive_agent import ArchiveDepthAgent
from agents.orchestrator import AgenticNewsroomOrchestrator
from agents.realtime_agent import RealTimeEnrichmentAgent
from services.state import QueryEnvelope
from tools.mcp_archive import ArchiveTool
from tools.web_search import WebSearchTool


class WebStub:
    def search(self, payload):
        return [
            {
                "headline": f"Realtime {i}",
                "source": "Reuters",
                "url": f"https://realtime/{i}",
                "published_at": datetime.now(timezone.utc).isoformat(),
                "summary": "Breaking",
                "confidence": 0.8,
            }
            for i in range(6)
        ]


class ArchiveStub:
    def search(self, payload):
        return {
            "articles": [
                {
                    "headline": f"Archive {i}",
                    "publication": "Archive Times",
                    "published_on": "2010-01-0{i+1}",
                    "snippet": "Context",
                    "pdf_ref": f"archive://{i}",
                }
                for i in range(5)
            ]
        }


def test_orchestrator_returns_formatted_response():
    realtime_agent = RealTimeEnrichmentAgent(tool=WebSearchTool(transport=WebStub()))
    archive_agent = ArchiveDepthAgent(tool=ArchiveTool(transport=ArchiveStub()))
    orchestrator = AgenticNewsroomOrchestrator(
        realtime_agent=realtime_agent,
        archive_agent=archive_agent,
    )
    envelope = QueryEnvelope(conversation_id="test", query="interest rates")
    response = orchestrator.handle_user_query(envelope)
    assert "Agentic Newsroom Brief" in response
    assert response.count("\n") > 10
