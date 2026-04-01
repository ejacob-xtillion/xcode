---
name: xcode-docker-stack
description: >-
  Starts and operates the xCode monorepo Docker Compose stack (Neo4j, Postgres,
  xcode-agent API, optional xcode CLI container). Use when the user asks to spin
  up Docker, start xCode services, run the agent in containers, fix compose health,
  or verify neo4j/postgres/agent connectivity for this repository.
---

# xCode Docker stack

## When to use

- User wants local services running for xCode (graph, agent API, CLI in Docker).
- Agent unhealthy, `postgres` DNS errors, or compose dependencies failing.
- Need correct URLs and exec patterns for containerized workflows.

## Prerequisites

- Repository root: directory that contains [`docker-compose.yml`](docker-compose.yml) (this monorepo).
- `.env` at repo root (Compose marks it required for several services). See [`.env.example`](.env.example) if present.
- Docker Desktop (or equivalent) running.

## Start the stack

From the **repository root**:

```bash
docker compose up -d
```

Wait until `xcode-agent` is **healthy** (healthcheck: `GET http://localhost:8000/health`). `xcode-cli` starts after the agent is healthy.

### Optional LiteLLM proxy

```bash
docker compose --profile llm-proxy up -d
```

Configure `.env` per [CLAUDE.md](CLAUDE.md) / docs for `LLM_PROVIDER=openai_proxy` and gateway URL.

## Services (default)

| Service       | Container      | Host ports | Role                          |
|---------------|----------------|------------|-------------------------------|
| neo4j         | xcode-neo4j    | 7474, 7687 | Knowledge graph               |
| postgres      | xcode-postgres | (internal) | Agent sessions / checkpointer |
| xcode-agent   | xcode-agent    | 8000       | FastAPI + LangGraph agent     |
| xcode         | xcode-cli      | —          | CLI (optional use)            |

Compose network: `xcode-network`. Agent uses `bolt://neo4j:7687` and `postgres` hostnames **inside** the stack.

## Verify

```bash
docker compose ps
curl -sf http://localhost:8000/health && echo OK
```

Neo4j Browser: `http://localhost:7474` (default auth from compose: `neo4j` / `password` unless overridden).

## Run tasks from the CLI container

```bash
docker compose exec xcode xcode "your task description"
docker compose exec -it xcode xcode -i
```

Host `xcode` with `--local` or `XCODE_AGENT_URL=http://localhost:8000` targets the agent on the host; inside the `xcode` service, `XCODE_AGENT_URL=http://xcode-agent:8000` is set in compose.

## Filesystem MCP note

Compose mounts a host path for MCP filesystem access (see `docker-compose.yml` under `xcode-agent` / `xcode`). On a different machine, update the bind mount to match the developer’s home or allowed roots so the agent can read/write the intended repos.

## Stop / reset

```bash
docker compose down          # stop, keep volumes
docker compose down -v       # stop and remove named volumes (wipes neo4j/postgres data)
```

## Troubleshooting

1. **`xcode-agent` unhealthy** — `docker logs xcode-agent --tail 80`
   - **Postgres `could not translate host name "postgres"`** — Often a stale or detached network after edits. Run `docker compose down` then `docker compose up -d` from repo root so all services recreate on `xcode-network`.
   - **Alembic / migration errors** — Ensure `postgres` is healthy before agent starts; compose `depends_on` with `condition: service_healthy` should enforce this.

2. **`.env` missing** — Compose may refuse to start services that declare `env_file: required: true`. Add a root `.env` (copy from example docs).

3. **Platform** — `xcode-agent` may set `platform: linux/amd64` for compatibility; on Apple Silicon, builds run under emulation unless you change the compose file.

## Related docs

- [CLAUDE.md](CLAUDE.md) — architecture, env vars, MCP, verification loop
- [docs/DOCKER.md](docs/DOCKER.md) — deeper Docker notes if present
