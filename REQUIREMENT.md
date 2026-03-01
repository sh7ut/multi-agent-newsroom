## Problem Statement

The Agentic Newsroom 
You are a Partner Solutions Architect working for Mistral AI. You get the following request from a partner. 

**Partner Request**: "We are seeing massive demand from our enterprise media and financial clients to move beyond basic RAG and into fully autonomous agentic workflows. Our clients require systems that do not merely answer questions but proactively research, cross-reference, and synthesize reports from disparate data sources.
Can you demonstrate how to architect a robust, multi-agent system using Mistral Agents? We need a solution that accepts a broad user query regarding a current event and returns a curated list of the 10 most relevant articles in a clean text format. Critically, the solution must orchestrate between two specific capabilities:
1.	Real-time Enrichment: Use the `web_search_premium` connector to retrieve high-fidelity data from verified news agencies.
2.	Archive Depth: Use an MCP server to query a local 'File Archive' of historical newspapers.

Please walk us through the agent handoff logic, the tool-calling schemas, and your strategy for ensuring the final output remains strictly formatted and grounded in both sources.” 
Your architecture should rely on Mistral’s native Agentic features (Handoffs, Tools, Conversations etc). For simplicity, use Python to build the demo. 

## Check the latest Docs for Mistral Agents 

#### Main link
[What are AI agents?](https://docs.mistral.ai/agents/introduction) - check out the other links from this page that lead to "Agents & COnversations", "Tools", "Built-in", "Websearch", "Code Interpreter", "Function Calling", "MCP" and "Handoffs"

#### Other important links related to this excercise
[Agents & Conversations](https://docs.mistral.ai/agents/agents)
[Tools](https://docs.mistral.ai/agents/tools)
[Websearch](https://docs.mistral.ai/agents/tools/built-in/websearch)
[MCP](https://docs.mistral.ai/agents/tools/mcp)
[Generic MCP Documentation](https://modelcontextprotocol.io/docs/getting-started/intro)
[Handoffs](https://docs.mistral.ai/agents/handoffs)

## Others 
- Think about stateful agents or conversation preservation as well as orchestration. [Temporal](https://temporal.io/code-exchange/durable-stateful-agents-with-mistral-temporal-mcp) might be a tool worth looking into but I also want to keep this demo as simple as possible. Discuss with me about the trade-offs and complexity, to decide whether to implement this for our demo. 

