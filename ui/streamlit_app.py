"""Streamlit UI for the Agentic Newsroom demo."""
from __future__ import annotations

import os
import uuid

import streamlit as st

from agents.orchestrator import AgenticNewsroomOrchestrator
from services.state import QueryEnvelope

st.set_page_config(page_title="Agentic Newsroom", page_icon="🗞️", layout="wide")
st.title("Agentic Newsroom Demo")
st.write(
    "Enter a current-events question and the orchestrator will fetch real-time coverage plus "
    "archive insights using Mistral Agents."
)

api_key_present = bool(os.getenv("MISTRAL_API_KEY"))
if not api_key_present:
    st.warning("`MISTRAL_API_KEY` is not set. Real-time searches will fail unless you provide mocks.")

if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = AgenticNewsroomOrchestrator()

query = st.text_area("Question", placeholder="e.g., Why did the US and Israel attack Iran?", height=120)
submit = st.button("Generate Brief", type="primary")

if submit and query.strip():
    conversation_id = str(uuid.uuid4())
    envelope = QueryEnvelope(conversation_id=conversation_id, query=query.strip(), filters=None)
    try:
        with st.spinner("Researching..."):
            response = st.session_state.orchestrator.handle_user_query(envelope)
        st.session_state.last_response = response
        st.session_state.last_conversation = conversation_id
    except Exception as exc:  # pylint: disable=broad-exception-caught
        st.error(f"Pipeline failed: {exc}")

if st.session_state.get("last_response"):
    st.subheader("Agentic Newsroom Brief")
    st.code(st.session_state.last_response, language="markdown")
    st.caption(f"Conversation ID: {st.session_state.get('last_conversation')}")
else:
    st.info("Submit a question to see the 10-article brief here.")
