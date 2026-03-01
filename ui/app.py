"""Optional FastAPI UI stub for manual exploration."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agents.orchestrator import AgenticNewsroomOrchestrator
from services.state import QueryEnvelope

app = FastAPI(title="Agentic Newsroom Demo")
orchestrator = AgenticNewsroomOrchestrator()


class QueryRequest(BaseModel):
    query: str
    conversation_id: str | None = None


@app.post("/brief")
def generate_brief(payload: QueryRequest):
    if not payload.query:
        raise HTTPException(status_code=400, detail="Query is required")
    envelope = QueryEnvelope(
        conversation_id=payload.conversation_id or "ui-" + payload.query.replace(" ", "-"),
        query=payload.query,
    )
    response = orchestrator.handle_user_query(envelope)
    return {"brief": response}
