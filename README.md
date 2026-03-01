# Agentic Newsroom Demo

This repo contains a Python-based multi-agent newsroom workflow built on Mistral Agents. Follow `PLAN.md` for architecture, testing, and implementation details.

## Quickstart
1. Create and populate an `env` file with your credentials. For example:
   ```bash
   export MISTRAL_API_KEY=your-key-here
   ```
2. Load the environment variables before running anything:
   ```bash
   source ./env
   ```
3. Start the local MCP File Archive server by pointing `MCP_ARCHIVE_CMD` to the helper script:
   ```bash
   export MCP_ARCHIVE_CMD="python mcp_servers/archive_server.py"
   ```
4. The code **never hardcodes secrets**. Whenever the Mistral client is needed, use this snippet:
   ```python
   import os
   from mistralai import Mistral as MistralClient

   api_key = os.getenv("MISTRAL_API_KEY")
   if not api_key:
       raise ValueError("MISTRAL_API_KEY environment variable not set. Please set it before running.")

   client = MistralClient(api_key=api_key)
   print("\u2713 Mistral client initialized")
   ```

Implementation is in progress—see `PLAN.md` for the intended modules and behaviors.
