"""Main orchestration logic coordinating agents and tools."""
from __future__ import annotations

import logging
from typing import List

from agents.archive_agent import ArchiveDepthAgent
from agents.formatter import FormatterAgent
from agents.realtime_agent import RealTimeEnrichmentAgent
from services.state import (
    Article,
    HandoffContext,
    QueryEnvelope,
    ResultNormalizer,
    ResultStore,
    generate_task_id,
)

logger = logging.getLogger(__name__)


class AgenticNewsroomOrchestrator:
    def __init__(
        self,
        realtime_agent: RealTimeEnrichmentAgent | None = None,
        archive_agent: ArchiveDepthAgent | None = None,
        formatter: FormatterAgent | None = None,
        normalizer: ResultNormalizer | None = None,
        store: ResultStore | None = None,
    ) -> None:
        self.realtime_agent = realtime_agent or RealTimeEnrichmentAgent()
        self.archive_agent = archive_agent or ArchiveDepthAgent()
        self.formatter = formatter or FormatterAgent()
        self.normalizer = normalizer or ResultNormalizer()
        self.store = store or ResultStore()

    def handle_user_query(self, envelope: QueryEnvelope) -> str:
        logger.info("Handling query", extra={"conversation_id": envelope.conversation_id})
        realtime_articles = self._dispatch_realtime(envelope)
        archive_articles = self._dispatch_archive(envelope, realtime_articles)
        merged = self._merge_results(realtime_articles, archive_articles)
        normalized = self.normalizer.normalize(merged)
        response = self.formatter.format(query=envelope.query, articles=normalized)
        self.store.set(envelope.conversation_id, "last_response", response)
        return response

    def _dispatch_realtime(self, envelope: QueryEnvelope) -> List[Article]:
        context = HandoffContext(
            task_id=generate_task_id("realtime"),
            conversation_id=envelope.conversation_id,
            role="realtime",
            query=envelope.query,
            constraints={"min_results": 5},
        )
        try:
            articles = self.realtime_agent.gather(context)
            logger.info(
                "Realtime agent returned %s articles", len(articles), extra={"task_id": context.task_id}
            )
            return articles
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.exception("Realtime agent failed: %s", exc)
            return []

    def _dispatch_archive(self, envelope: QueryEnvelope, partial: List[Article]) -> List[Article]:
        context = HandoffContext(
            task_id=generate_task_id("archive"),
            conversation_id=envelope.conversation_id,
            role="archive",
            query=envelope.query,
            constraints={"min_archive_results": 3},
            partial_results=partial,
        )
        try:
            articles = self.archive_agent.gather(context)
            logger.info(
                "Archive agent returned %s articles", len(articles), extra={"task_id": context.task_id}
            )
            return articles
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.exception("Archive agent failed: %s", exc)
            return []

    def _merge_results(self, realtime: List[Article], archive: List[Article]) -> List[Article]:
        logger.debug("Merging %s realtime and %s archive articles", len(realtime), len(archive))
        return realtime + archive
