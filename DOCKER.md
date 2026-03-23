# Docker Setup for xCode

This Docker setup orchestrates three services:
1. **Neo4j** - Knowledge graph database
2. **xCode Agent** - AI agent backend (la-factoria generated)
3. **xCode CLI** - Interactive coding assistant

## Prerequisites

- Docker and Docker Compose installed
- La-factoria xcode_agent generated at `/Users/elijahgjacob/la-factoria/output/xcode_agent`

## Quick Start

### Recommended: Use the Startup Script

```bash
# Smart startup with progress indicators (recommended)
./docker-start.sh

# Or using Makefile
make start
```

This script will:
1. Check Docker is running
2. Pull Neo4j image with retry logic
3. Build both xCode services
4. Start services in correct order
5. Wait for health checks
6. Show status and next steps

### Manual Start

```bash
# Start all services (Neo4j, xCode Agent, xCode CLI)
docker-compose up

# Or in detached mode
docker-compose up -d

# View logs
docker-compose logs -f
```

### Start Individual Services

```bash
# Start only Neo4j and xCode Agent (backend services)
docker-compose up -d neo4j xcode-agent

# Then run xCode CLI interactively
docker-compose run --rm xcode
```

## Service Details

### Neo4j (Port 7474, 7687)
- **Purpose**: Knowledge graph database for codebase analysis
- **Access**: http://localhost:7474 (Browser UI)
- **Credentials**: neo4j/password
- **Health Check**: Cypher shell connection test

### xCode Agent (Port 8000)
- **Purpose**: AI agent execution backend
- **Access**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: GET /health endpoint
- **Startup**: ~40 seconds (includes migrations)

### xCode CLI
- **Purpose**: Interactive coding assistant
- **Mode**: Interactive REPL by default
- **Depends On**: xCode Agent and Neo4j must be healthy

## Usage Examples

### Interactive Mode

```bash
# Start xCode in interactive mode
docker-compose run --rm xcode

# With verbose output
docker-compose run --rm xcode xcode -i -v
```

### Single-Shot Mode

```bash
# Execute a single task
docker-compose run --rm xcode xcode "add type hints to functions"

# With custom path
docker-compose run --rm xcode xcode --path /workspace/myproject "fix tests"
```

### Build Knowledge Graph Only

```bash
docker-compose run --rm xcode xcode --path /workspace/myproject "build graph"
```

## Environment Variables

The following environment variables are configured:

- `LA_FACTORIA_URL=http://xcode-agent:8000` - Agent backend URL
- `NEO4J_URI=bolt://neo4j:7687` - Neo4j connection
- `NEO4J_USER=neo4j` - Neo4j username
- `NEO4J_PASSWORD=password` - Neo4j password

Override these in your local `.env` file if needed.

## Volumes

- **neo4j_data**: Persistent Neo4j database
- **neo4j_logs**: Neo4j logs
- **xcode source**: Mounted for live development
- **workspace**: Your code repositories (read-only)

## Troubleshooting

### Service Won't Start

```bash
# Check service status
docker-compose ps

# View logs for specific service
docker-compose logs neo4j
docker-compose logs xcode-agent
docker-compose logs xcode

# Restart services
docker-compose restart
```

### Connection Errors

```bash
# Verify xcode-agent is healthy
curl http://localhost:8000/health

# Check if Neo4j is accessible
docker-compose exec neo4j cypher-shell -u neo4j -p password "RETURN 1"
```

### Clean Restart

```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: deletes Neo4j data)
docker-compose down -v

# Rebuild and start fresh
docker-compose up --build
```

## Development Workflow

### Local Development with Hot Reload

```bash
# Start backend services only
docker-compose up -d neo4j xcode-agent

# Run xCode locally (not in Docker)
cd /Users/elijahgjacob/xcode
xcode -i
```

### Testing Changes

```bash
# Rebuild xcode service after code changes
docker-compose build xcode

# Run tests in container
docker-compose run --rm xcode python -m pytest tests/
```

## Network

All services run on the `xcode-network` bridge network, allowing them to communicate using service names as hostnames.

## Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Stop specific service
docker-compose stop xcode
```
