# PLAN.md — Agentic Newsroom Demo

## 1. Requirements Digest
- **Partner goals**: Demonstrate a Python-based, multi-agent newsroom workflow using Mistral Agents that handles broad current-event queries and returns 10 curated, grounded articles. System must showcase handoffs, tool invocation, grounding to both real-time web data (`web_search_premium`) and a local MCP File Archive, and deliver strictly formatted output. If time permits, optionally expose the workflow through a lightweight UI/front-end to visualize the final brief.
- **Success criteria**:
  - Always produce exactly 10 articles that include attribution to both real-time and archive sources.
  - Each article must include structured fields (headline, outlet, URL, summary, evidence tags) with provenance text grounded in cited sources.
  - Document orchestration logic (handoffs, routing, error handling) and include testing + operational guidance.
- **Non-goals**: Building a production ingestion pipeline, full-fledged frontend (only an optional lightweight demo UI), Temporal orchestration implementation (only a trade-off discussion), or deploying real connectors.

## 2. Architecture Overview
- **Agents**:
  1. `OrchestratorGovernor` (system/gateway): parses user prompt, creates task graph, enforces policies, and coordinates handoffs.
  2. `RealTimeEnrichmentAgent`: optimized for `web_search_premium` queries targeting verified news agencies and financial feeds.
  3. `ArchiveDepthAgent`: interfaces with MCP "File Archive" server to surface historic context and background articles.
  4. `FormatterAgent` (lightweight worker or Orchestrator mode) that validates and formats final output.
- **Flow**:
  1. User query enters Orchestrator with metadata (query text, optional filters).
  2. Orchestrator crafts shared context payload, sends handoff to Real-Time agent; agent calls `web_search_premium` until it accumulates ≥10 unique contemporary candidates tagged `source_type="realtime"`.
  3. Parallel or sequential handoff to Archive agent with same payload plus real-time hints; Archive agent queries MCP archive for historical coverage, returning results tagged `source_type="archive"`.
  4. Orchestrator merges responses, dedupes via URL/hash, scores by freshness + authority, and ensures every final entry has at least one grounding snippet and indicates which source(s) informed it.
  5. Formatter enforces template, ensures citation compliance, fills metadata (timestamp, provenance note) before returning to user.
- **Handoffs & routing**:
  - Handoff triggers when Orchestrator detects missing source type, insufficient count, or stale timestamps.
  - Shared payload includes `conversation_id`, `task_id`, `query`, `constraints`, `partial_results`, `grounding_requirements`.
  - Fallback loops: if `web_search_premium` returns <5 items, Orchestrator retries with relaxed filters; if MCP archive empty, run fallback query (wider date range) then degrade gracefully with warning field.

## 3. Tool Schemas & Connectors
- **`web_search_premium`**:
  - *Input schema*:
    ```json
    {
      "type": "object",
      "properties": {
        "query": {"type": "string"},
        "recency_days": {"type": "integer", "minimum": 0, "maximum": 30},
        "source_whitelist": {"type": "array", "items": {"type": "string"}},
        "language": {"type": "string", "enum": ["en"]},
        "limit": {"type": "integer", "minimum": 1, "maximum": 20}
      },
      "required": ["query"],
      "additionalProperties": false
    }
    ```
  - *Output schema*:
    ```json
    {
      "type": "object",
      "properties": {
        "results": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "headline": {"type": "string"},
              "url": {"type": "string", "format": "uri"},
              "source": {"type": "string"},
              "published_at": {"type": "string", "format": "date-time"},
              "summary": {"type": "string"},
              "confidence": {"type": "number", "minimum": 0, "maximum": 1}
            },
            "required": ["headline", "url", "source", "published_at"]
          }
        }
      },
      "required": ["results"],
      "additionalProperties": false
    }
    ```
  - *Operational notes*: store API credentials via env vars (`WEB_SEARCH_API_KEY`), throttle to ≤5 calls/min per session, exponential backoff on HTTP 429.
- **MCP File Archive connector**:
  - *Manifest excerpt* (`mcp.json`):
    ```json
    {
      "name": "file-archive",
      "description": "Local historical newspaper archive",
      "version": "0.1.0",
      "commands": [{
        "name": "search_archive",
        "input_schema": {
          "type": "object",
          "properties": {
            "query": {"type": "string"},
            "start_date": {"type": "string", "format": "date"},
            "end_date": {"type": "string", "format": "date"},
            "section": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 20}
          },
          "required": ["query"],
          "additionalProperties": false
        }
      }]
    }
    ```
  - *Response contract*:
    ```json
    {
      "articles": [
        {
          "headline": "string",
          "publication": "string",
          "published_on": "YYYY-MM-DD",
          "snippet": "string",
          "pdf_ref": "string",
          "page": "string"
        }
      ],
      "metadata": {"archive_version": "string", "query_time_ms": "number"}
    }
    ```
  - Auth handled via local MCP token file; rate limit 10 queries/min; log command invocations for audit.

## 4. Conversation & State Management
- Use conversation IDs (UUID) to persist context in Redis-like store or in-memory dict for demo.
- Store `UserTurn` objects containing query, constraints, and derived intents. Maintain `ResultStore` keyed by `conversation_id` with cached article list, dedupe hashes (SHA256 of URL or pdf_ref), and rationale text.
- Normalization pipeline:
  1. Combine real-time and archive arrays.
  2. Deduplicate by canonical URL/hash.
  3. Score with weighted sum: `freshness_weight=0.6`, `authority_weight=0.3`, `coverage_weight=0.1` (coverage derived from archive relevance).
  4. Generate rationale sentences referencing both source types when available.

## 5. Formatting & Output Contract
- Response template:
  ```text
  ## Agentic Newsroom Brief — <ISO timestamp>
  Query: "<user query>"

  1. <Headline> — <Source> [<source_type(s)>]
     Link: <URL>
     Summary: <2-sentence synthesis grounded in cited snippets>
     Evidence: [<source_type>:<source_name>@<published_at>, ...]

  ... up to 10 entries ...

  Provenance: Real-time data via web_search_premium; archival context via File Archive MCP.
  ```
- Validation rules:
  - Reject output if <10 entries or if any entry lacks `headline`, `summary`, or `evidence`.
  - Ensure at least 3 entries contain `archive` grounding; otherwise flag "Archive coverage limited" warning appended after provenance.

## 6. Implementation Steps (Python)
1. **Project layout**
   ```
   ./
   ├── agents/
   │   ├── orchestrator.py
   │   ├── realtime_agent.py
   │   ├── archive_agent.py
   │   └── formatter.py
   ├── tools/
   │   ├── web_search.py
   │   └── mcp_archive.py
   ├── services/
   │   └── state.py
   ├── formatting/
   │   └── templates.py
   ├── tests/
   │   ├── test_tools.py
   │   ├── test_formatter.py
   │   └── test_integrations.py
   ├── cli.py
   └── README.md
   ```
2. **Dependencies**: `mistralai[agents]`, `pydantic`, `requests`, `rich` (CLI output), `pytest`.
3. **agents/orchestrator.py**: define `AgenticNewsroomOrchestrator` class with methods `handle_user_query`, `dispatch_realtime`, `dispatch_archive`, `merge_results`, `format_response`. Implement error-handling (retry up to 2 times per tool) and logging.
4. **agents/realtime_agent.py**: configure Mistral Agent with system prompt focusing on breaking news reliability. Bind `web_search_premium` tool. Provide helper `collect_realtime_results` returning normalized dicts.
5. **agents/archive_agent.py**: similar structure but calling MCP client; include logic to widen date range if fewer than 3 results.
6. **agents/formatter.py & formatting/templates.py**: implement template rendering + validation; raise exception if constraints violated.
7. **tools/web_search.py**: wrapper around connector SDK with schema validation using `pydantic` models; includes throttling helper.
8. **tools/mcp_archive.py**: MCP client wrapper that manages session, executes `search_archive`, and normalizes responses.
9. **services/state.py**: implement simple cache/dedupe utilities; include `ResultNormalizer` class for scoring + rationales.
10. **cli.py**: entry script that instantiates orchestrator, loads env vars (e.g., `source ./env`), reads query from CLI argument, prints formatted brief. When initializing any Mistral client, rely on the provided snippet to avoid hardcoding secrets:
    ```python
    import os
    from mistralai.client import MistralClient

    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise ValueError("MISTRAL_API_KEY environment variable not set. Please set it before running.")

    client = MistralClient(api_key=api_key)
    print("✓ Mistral client initialized")
    ```
11. **Optional UI** (`ui/` directory if pursued): minimal FastAPI + HTMX or Streamlit frontend that calls the CLI/service via API. Treat as optional; prioritize backend completion before implementation.

## 7. Testing & Verification
- **Unit tests** (`tests/test_tools.py`, `tests/test_formatter.py`): validate schema enforcement, dedupe scoring, and formatter template compliance using fixture data.
- **Integration test** (`tests/test_integrations.py`): mock tool wrappers to return canned data; assert orchestrator returns 10 entries, correct warnings, and provenance text.
- **Dry-run script**: `python cli.py "Fed rate decision" --mock` to exercise pipeline with sample payloads; document in README.

## 8. Operational Considerations
- **Logging/Observability**: structured JSON logs per handoff (`conversation_id`, `task_id`, agent name, latency, success/failure). Optionally integrate OpenTelemetry exporter.
- **Configuration**: `.env` variables for API keys, MCP socket path, rate-limit overrides.
- **Deployment**: package as CLI or container (`Dockerfile` with Python 3.11 slim). Provide `make run` and `make test` targets. Document that secrets come from environment (`source ./env`) and must never be embedded in code or config.
- **Limitations**: No Temporal orchestration; mention in README with trade-off (Temporal adds durability + retries but increases setup complexity). No real UI; connectors mocked for demo.
- **Future work**: add Temporal or workflow engine, extend to multilingual queries, attach vector store for cache hits.

## 9. Interfaces / API Notes
- **User query envelope**:
  ```json
  {
    "conversation_id": "uuid",
    "query": "string",
    "filters": {
      "topic": "string",
      "regions": ["string"],
      "date_range": {"start": "date", "end": "date"}
    }
  }
  ```
- **Handoff context**:
  ```json
  {
    "task_id": "uuid",
    "conversation_id": "uuid",
    "role": "realtime|archive",
    "query": "string",
    "constraints": {"min_results": 5, "require_grounding": true},
    "partial_results": [ ... normalized article dicts ... ]
  }
  ```
- **Normalized tool output item**:
  ```json
  {
    "headline": "string",
    "source": "string",
    "source_type": "realtime|archive|both",
    "url": "string",
    "published_at": "date-time",
    "summary": "string",
    "evidence": ["realtime:Reuters@2026-02-28T12:00Z"]
  }
  ```

## 10. Test Scenarios
1. `test_dual_source_merge`: feed overlapping entries; expect dedupe keeps higher confidence and retains both evidence tags.
2. `test_archive_gap`: archive returns zero twice → Orchestrator surfaces warning and still outputs 10 items with note about limited archive data.
3. `test_format_contract`: intentionally break template (9 items) to ensure formatter raises.
4. `test_tool_failure`: simulate MCP downtime; orchestrator logs failure, returns structured error with remediation tips.

## 11. Assumptions
- Using Python 3.11 with access to Mistral Agents SDK, MCP client libraries, and necessary credentials.
- Temporal orchestration explicitly out of scope for implementation; a short trade-off note will explain potential benefits.
- Demo operates via CLI/SDK by default; optional lightweight UI can be added only if time permits.
