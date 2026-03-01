"""CLI entrypoint for the Agentic Newsroom demo."""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import uuid

from agents.orchestrator import AgenticNewsroomOrchestrator
from services.state import QueryEnvelope

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agentic Newsroom Demo")
    parser.add_argument("query", help="User query to research")
    parser.add_argument("--conversation-id", default=str(uuid.uuid4()))
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in mock mode (bypasses real connectors; expects injected transports in code).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not os.getenv("MISTRAL_API_KEY"):
        logging.warning("MISTRAL_API_KEY not set; ensure transports rely on mocks or set the env var via source ./env")

    orchestrator = AgenticNewsroomOrchestrator()
    envelope = QueryEnvelope(conversation_id=args.conversation_id, query=args.query, filters=None)
    try:
        response = orchestrator.handle_user_query(envelope)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logging.exception("Pipeline failed: %s", exc)
        return 1

    print(response)
    logging.info("Completed conversation %s", envelope.conversation_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
