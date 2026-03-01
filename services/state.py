"""State management and normalization utilities for the Agentic Newsroom demo."""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence


@dataclass
class Article:
    """Normalized article representation used across agents."""

    headline: str
    source: str
    source_type: str  # realtime | archive | both
    url: str
    published_at: datetime
    summary: str
    evidence: List[str]
    confidence: float = 0.5

    def dedupe_key(self) -> str:
        """Compute a stable hash for deduplication."""
        key = self.url or "".join(self.evidence)
        return hashlib.sha256(key.encode("utf-8")).hexdigest()


@dataclass
class QueryEnvelope:
    conversation_id: str
    query: str
    filters: Optional[Dict] = None


@dataclass
class HandoffContext:
    task_id: str
    conversation_id: str
    role: str
    query: str
    constraints: Dict
    partial_results: List[Article] = field(default_factory=list)


class ResultStore:
    """Minimal in-memory cache keyed by conversation ID."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, object]] = {}

    def get(self, conversation_id: str, key: str, default=None):
        return self._store.get(conversation_id, {}).get(key, default)

    def set(self, conversation_id: str, key: str, value) -> None:
        self._store.setdefault(conversation_id, {})[key] = value


class ResultNormalizer:
    """Dedupe, score, and ensure we always return exactly 10 articles."""

    def __init__(self, freshness_weight: float = 0.6, authority_weight: float = 0.3, coverage_weight: float = 0.1):
        self.freshness_weight = freshness_weight
        self.authority_weight = authority_weight
        self.coverage_weight = coverage_weight

    def normalize(self, articles: Sequence[Article]) -> List[Article]:
        # Dedupe by URL hash while keeping strongest confidence.
        deduped: Dict[str, Article] = {}
        for article in articles:
            key = article.dedupe_key()
            if key in deduped:
                existing = deduped[key]
                if article.confidence > existing.confidence:
                    deduped[key] = article
                    continue
                existing.evidence = sorted(set(existing.evidence + article.evidence))
                if article.source_type != existing.source_type:
                    existing.source_type = "both"
            else:
                deduped[key] = article

        scored = sorted(
            deduped.values(),
            key=lambda a: self._score_article(a),
            reverse=True,
        )

        if len(scored) >= 10:
            return scored[:10]

        # Pad with placeholders if needed so formatter can enforce template.
        placeholders = 10 - len(scored)
        now = datetime.now(timezone.utc)
        for i in range(placeholders):
            scored.append(
                Article(
                    headline=f"Placeholder insight {i + 1}",
                    source="Agentic Newsroom",
                    source_type="realtime",
                    url=f"https://placeholder.local/{i}",
                    published_at=now,
                    summary="Awaiting additional data",
                    evidence=["realtime:placeholder@" + now.isoformat()],
                    confidence=0.0,
                )
            )
        return scored

    def _score_article(self, article: Article) -> float:
        freshness = max(0.0, min(1.0, self._freshness_score(article)))
        authority = 1.0 if article.source.lower() in {"reuters", "ap", "bloomberg"} else 0.5
        coverage = 1.0 if "archive" in article.source_type else 0.5
        return (
            freshness * self.freshness_weight
            + authority * self.authority_weight
            + coverage * self.coverage_weight
            + article.confidence * 0.1
        )

    @staticmethod
    def _freshness_score(article: Article) -> float:
        delta = datetime.now(timezone.utc) - article.published_at
        hours = max(delta.total_seconds(), 1) / 3600
        return max(0.0, 1.0 - (hours / 72))


def serialize_articles(articles: Sequence[Article]) -> str:
    """Helper for logging or persistence."""
    return json.dumps(
        [
            {
                "headline": a.headline,
                "source": a.source,
                "source_type": a.source_type,
                "url": a.url,
                "published_at": a.published_at.isoformat(),
                "summary": a.summary,
                "evidence": a.evidence,
                "confidence": a.confidence,
            }
            for a in articles
        ],
        indent=2,
    )


def conversation_timestamp() -> str:
    return datetime.utcnow().isoformat()


def generate_task_id(prefix: str) -> str:
    return f"{prefix}-{int(time.time() * 1000)}"
