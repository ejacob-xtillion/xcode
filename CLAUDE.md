# CLAUDE.md — xCode Project Guide

## Project Overview

xCode is a CLI tool that:
1. Builds a **Neo4j knowledge graph** of a codebase (via `xgraph`)
2. Spawns an **AI coding agent** (via `la-factoria` at `http://localhost:8000`)
3. Runs a **verification loop** (tests/linters) until task succeeds

Supports local LLMs (Ollama at `localhost:11434`) and cloud APIs.

---

## Architecture (Clean Architecture)

```
CLI / Interactive (cli.py, interactive.py)
    ↓
Orchestrator (orchestrator.py)
    ↓
Services (xcode/services/)          ← business logic
    ↓
Repositories (xcode/repositories/)  ← external adapters
    ↓
Infrastructure (xcode/infrastructure/) ← low-level clients
    ↓
Domain (xcode/domain/)              ← models & interfaces
```

### Key Files

| File | Role |
|------|------|
| `xcode/cli.py` | Click CLI entry point, all flags |
| `xcode/orchestrator.py` | Main orchestrator (active, not the `_new` version) |
| `xcode/services/agent_service.py` | Logs "Starting agent for task", calls agent repo |
| `xcode/repositories/agent_repository.py` | La-factoria HTTP client — **see known bug below** |
| `xcode/agent_runner.py` | Legacy runner — uses correct `/agents` endpoint |
| `xcode/models/config.py` | `XCodeConfig`, `get_llm_config()` |
| `xcode/infrastructure/llm_client.py` | LLM HTTP client (`/chat/completions`) |

---

## Known Bug: La-Factoria Endpoint Mismatch

**Symptom:**
```
Starting agent for task: your task here
✗ Task failed: Agent API error: 404
{"detail":"Not Found"}
```

**Root cause:**
- `xcode/repositories/agent_repository.py:63` calls `POST /agent/stream`
- La-factoria server only exposes `POST /agents`
- FastAPI returns `{"detail":"Not Found"}` for missing routes

**The two endpoints and their payloads:**

| File | Endpoint | Payload |
|------|----------|---------|
| `agent_repository.py` (broken) | `POST /agent/stream` | `{agent_name, system_prompt, user_message, config}` |
| `agent_runner.py` (working) | `POST /agents` | `{agent_name, query}` |

**Fix needed:** Update `agent_repository.py` to call `/agents` with `{agent_name, query}` payload, combining `system_prompt` + `user_message` into `query`. Also update `_handle_event` to match the different event types (`session_created`, `token`, `answer`, `complete` vs `message`).

Note: `/agents` does not accept LLM config — la-factoria uses its own configured LLM. The `--local`/`--llm-endpoint` flags affect the graph-building LLM (xgraph), not the agent LLM.

---

## La-Factoria Integration

- Server: `http://localhost:8000` (hardcoded)
- Agent name: `xcode_coding_agent`
- Correct endpoint: `POST /agents`
- Request: `{"agent_name": "xcode_coding_agent", "query": "<combined prompt>"}`
- Response: Server-Sent Events (SSE), line-by-line `data: {...}`
- Event types: `session_created`, `token`, `tool_call`, `tool_result`, `answer`, `error`, `interrupt`, `complete`

---

## Local LLM (Ollama)

- Default endpoint: `http://localhost:11434`
- LLM config passed via `XCodeConfig.get_llm_config()` → `{"model": ..., "base_url": ...}`
- Only affects graph building (xgraph), NOT the la-factoria agent
- CLI flags: `--local` (Ollama default) or `--llm-endpoint <url> --model <name>`

---

## Running

```bash
# With Ollama
xcode --local "your task here"

# With custom endpoint
xcode --llm-endpoint http://localhost:11434/v1 --model llama3.2 "your task"

# Skip graph rebuild
xcode --no-build-graph "your task"

# Verbose
xcode --verbose --local "your task"
```

## Tests & Code Quality

```bash
pytest                          # run all tests (121 tests, ~46% coverage)
pytest tests/test_config.py -v
pytest --cov=xcode --cov-report=html

black xcode tests               # format
ruff check xcode tests          # lint
mypy xcode                      # type check
```

---

## Environment Variables

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
XCODE_MODEL=llama3.2
XCODE_LLM_ENDPOINT=http://localhost:11434
XGRAPH_ENABLE_DESCRIPTIONS=false
```

---

## Dual Orchestrator Status

- `orchestrator.py` — **active** (used by CLI)
- `orchestrator_new.py` — in-progress migration, not yet wired up
- `agent_runner.py` — legacy, has correct endpoint logic; reference it when fixing `agent_repository.py`
