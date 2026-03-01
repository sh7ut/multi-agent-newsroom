"""Concrete transport for the `web_search_premium` connector via the Mistral API."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Sequence

from mistralai import Mistral
from mistralai.models import MessageOutputEntry

from services.state import Article

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def init_mistral_client() -> Mistral:
    """Create a configured SDK client while enforcing secret handling policy."""
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError(
            "MISTRAL_API_KEY environment variable not set. Please set it before running."
        )
    client = Mistral(api_key=api_key)
    print("\u2713 Mistral client initialized")
    return client


@dataclass
class WebSearchConfig:
    recency_days: int = 3
    limit: int = 10
    language: str = "en"
    model: str = "mistral-large-latest"


class WebSearchTransport:
    def search(self, query: str, config: WebSearchConfig) -> List[Dict[str, Any]]:  # pragma: no cover - interface only
        raise NotImplementedError


class DefaultWebSearchTransport(WebSearchTransport):
    """Calls `beta.conversations.start` with the `web_search_premium` tool."""

    def __init__(self, client: Mistral | None = None) -> None:
        self.client = client or init_mistral_client()

    def search(self, query: str, config: WebSearchConfig) -> List[Dict[str, Any]]:
        prompt = self._build_prompt(query=query, config=config)
        response = self.client.beta.conversations.start(
            model=config.model,
            tools=[{"type": "web_search_premium"}],
            inputs=[{"role": "user", "content": prompt}],
            store=False,
        )
        return self._parse_response(response.outputs, config.limit)

    @staticmethod
    def _build_prompt(query: str, config: WebSearchConfig) -> str:
        return (
            "You are the Real-Time Enrichment agent. "
            "Use only the web_search_premium connector to gather verified articles. "
            f"Return a JSON object with key 'results' containing at most {config.limit} entries. "
            "Each entry must include headline, url, source, summary, published_at (ISO 8601),"
            " and confidence (0-1). Focus on reports no older than "
            f"{config.recency_days} days and respond in {config.language}. Query: {query}"
        )

    @staticmethod
    def _parse_response(outputs: Sequence[Any], limit: int) -> List[Dict[str, Any]]:
        """Extract the JSON payload from the assistant output."""
        message_chunks: List[str] = []
        for entry in outputs:
            if isinstance(entry, MessageOutputEntry):
                message_chunks.append(_content_to_text(entry.content))
        if not message_chunks:
            raise RuntimeError("web_search_premium conversation returned no assistant output")
        raw_text = "\n".join(message_chunks)
        cleaned = _strip_code_fences(raw_text)
        payload = _load_json_payload(cleaned)
        results = payload.get("results", [])
        if not isinstance(results, list):
            raise ValueError("web_search_premium response missing 'results' list")
        return results[:limit]


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = _CODE_FENCE_RE.sub("", stripped).strip()
    return stripped


def _load_json_payload(text: str) -> Dict[str, Any]:
    if not text:
        raise ValueError("Empty response from web_search_premium conversation")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError as err:
                raise ValueError("Unable to parse JSON from web_search_premium output") from err
        raise


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    parts: List[str] = []
    for chunk in content or []:
        text = getattr(chunk, "text", None)
        if text:
            parts.append(text)
    return "".join(parts)


class WebSearchTool:
    def __init__(
        self,
        transport: WebSearchTransport | None = None,
        config: WebSearchConfig | None = None,
    ) -> None:
        self.config = config or WebSearchConfig()
        self.transport = transport or DefaultWebSearchTransport()

    def search(self, query: str) -> List[Article]:
        raw_results = self.transport.search(query, self.config)
        return [self._normalize_item(item) for item in raw_results]

    @staticmethod
    def _normalize_item(item: Dict[str, Any]) -> Article:
        return Article(
            headline=item.get("headline", "Unknown"),
            source=item.get("source", "Unknown"),
            source_type="realtime",
            url=item.get("url", ""),
            published_at=_to_datetime(item.get("published_at")),
            summary=item.get("summary", ""),
            evidence=[
                f"realtime:{item.get('source', 'unknown')}@{item.get('published_at', 'unknown')}"
            ],
            confidence=float(item.get("confidence", 0.5)),
        )


def _to_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            pass
    return datetime.now(tz=timezone.utc)
