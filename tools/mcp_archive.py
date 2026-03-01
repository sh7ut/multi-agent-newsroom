"""Archive connector backed by a local MCP server mediated via the Mistral API."""
from __future__ import annotations

import json
import os
import shlex
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Callable

import anyio
from mcp import StdioServerParameters
from mistralai import Mistral
from mistralai.extra.mcp.stdio import MCPClientSTDIO
from mistralai.extra.run.context import RunContext
from mistralai.models import FunctionResultEntry

from services.state import Article


def init_mistral_client() -> Mistral:
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError(
            "MISTRAL_API_KEY environment variable not set. Please set it before running."
        )
    client = Mistral(api_key=api_key)
    print("\u2713 Mistral client initialized")
    return client


@dataclass
class ArchiveConfig:
    start_date: str | None = None
    end_date: str | None = None
    section: str | None = None
    limit: int = 5
    model: str = "mistral-small-latest"
    mcp_command: str | None = "python mcp_servers/archive_server.py"


class ArchiveTransport:
    def search(self, query: str, config: ArchiveConfig) -> Dict[str, Any]:  # pragma: no cover - interface only
        raise NotImplementedError


class DefaultArchiveTransport(ArchiveTransport):
    """Executes `search_archive` through a local MCP server using Conversations run."""

    def __init__(self, client_factory: Callable[[], Mistral] | None = None) -> None:
        self._client_factory = client_factory or init_mistral_client

    def search(self, query: str, config: ArchiveConfig) -> Dict[str, Any]:
        command = config.mcp_command or os.getenv("MCP_ARCHIVE_CMD")
        if not command:
            raise ValueError(
                "MCP_ARCHIVE_CMD environment variable not set. Configure it with the MCP server command."
            )
        args = shlex.split(command)
        if not args:
            raise ValueError("MCP archive command is empty")
        params = StdioServerParameters(
            command=args[0],
            args=args[1:],
            env=os.environ.copy(),
            cwd=os.getcwd(),
        )
        payload = {
            "query": query,
            "limit": config.limit,
        }
        if config.start_date:
            payload["start_date"] = config.start_date
        if config.end_date:
            payload["end_date"] = config.end_date
        if config.section:
            payload["section"] = config.section

        prompt = self._build_prompt(query=query, config=config, arguments=payload)
        return anyio.run(
            self._execute_conversation,
            prompt,
            params,
            config.model,
        )

    async def _execute_conversation(
        self,
        prompt: str,
        params: StdioServerParameters,
        model: str,
    ) -> Dict[str, Any]:
        client = self._client_factory()
        mcp_client = MCPClientSTDIO(params, name="file-archive")
        try:
            async with RunContext(model=model) as run_ctx:
                await run_ctx.register_mcp_client(mcp_client)
                run_result = await client.beta.conversations.run_async(
                    run_ctx=run_ctx,
                    inputs=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    instructions=(
                        "You have access to a File Archive MCP tool named 'search_archive'. "
                        "Whenever you need historical coverage you must call that tool with the JSON arguments provided. "
                        "Respond strictly as JSON with key 'articles' listing headline, publication, published_on, snippet, pdf_ref, page."
                    ),
                )
        finally:
            await _close_mistral_client(client)
        return _extract_json_from_run(run_result)

    @staticmethod
    def _build_prompt(query: str, config: ArchiveConfig, arguments: Dict[str, Any]) -> str:
        constraints: List[str] = []
        if config.start_date:
            constraints.append(f"start_date: {config.start_date}")
        if config.end_date:
            constraints.append(f"end_date: {config.end_date}")
        if config.section:
            constraints.append(f"section: {config.section}")
        constraint_text = ", ".join(constraints) or "no extra constraints"
        arguments_json = json.dumps(arguments)
        return (
            "You are the Archive Depth agent. "
            "Call the MCP tool named 'search_archive' exactly once using the provided JSON arguments. "
            f"Arguments JSON: {arguments_json}. "
            "If the tool succeeds, summarize the returned articles and output JSON with key 'articles' only. "
            f"Query focus: {query}. Constraints: {constraint_text}. Return at most {config.limit} articles."
        )


class ArchiveTool:
    def __init__(
        self,
        transport: ArchiveTransport | None = None,
        config: ArchiveConfig | None = None,
    ) -> None:
        self.config = config or ArchiveConfig()
        self.transport = transport or DefaultArchiveTransport()

    def search(self, query: str) -> List[Article]:
        raw = self.transport.search(query, self.config)
        if isinstance(raw, list):
            articles = raw
        elif isinstance(raw, dict):
            articles = raw.get("articles", [])
        else:
            raise ValueError("archive response payload is neither dict nor list")
        if not isinstance(articles, list):
            raise ValueError("archive response missing 'articles'")
        return [self._normalize_item(item) for item in articles]

    @staticmethod
    def _normalize_item(item: Dict[str, Any]) -> Article:
        return Article(
            headline=item.get("headline", "Unknown"),
            source=item.get("publication", "Unknown Archive"),
            source_type="archive",
            url=item.get("pdf_ref", ""),
            published_at=_to_datetime(item.get("published_on")),
            summary=item.get("snippet", ""),
            evidence=[
                f"archive:{item.get('publication', 'unknown')}@{item.get('published_on', 'unknown')}"
            ],
            confidence=0.4,
        )


def _to_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            pass
    return datetime.now(tz=timezone.utc)


def _extract_json_from_run(run_result) -> Dict[str, Any]:
    for entry in reversed(run_result.output_entries):
        if isinstance(entry, FunctionResultEntry):
            try:
                return json.loads(entry.result)
            except json.JSONDecodeError:
                continue
    text = run_result.output_as_text
    cleaned = text.strip().strip("`")
    return json.loads(cleaned)


async def _close_mistral_client(client: Mistral) -> None:
    async_client = getattr(client.sdk_configuration, "async_client", None)
    http_client = getattr(client.sdk_configuration, "client", None)
    if async_client is not None:
        await async_client.aclose()
    if http_client is not None:
        http_client.close()
