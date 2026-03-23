# Generated FastAPI Agent Application

This is a **generated FastAPI agent repository** created by [La Factoria](https://github.com/xtillion/la-factoria) - a CLI tool that generates production-ready agent applications from YAML configuration files.

## What You Have

This repository contains a **complete, working FastAPI application** with:
- ✅ Custom AI agents configured from your YAML specification
- ✅ Production-ready infrastructure (database, logging, telemetry)
- ✅ Streaming API endpoints with Server-Sent Events (SSE)
- ✅ Session management and persistence
- ✅ Docker support for easy deployment
- ✅ OpenTelemetry observability integration


## Your Agents

This repository contains the agents you specified in your configuration. Each agent is located in `app/engine/<agent_name>/` and can be accessed via the API.

### Agent Patterns

Your repository may contain one or more of the following agent patterns:

| Pattern | Type Value | Use Case | Key Features |
|---------|------------|----------|--------------|
| **Simple Agent** | `simple_agent` | Single agent tasks | Single agent with customizable prompts, models, and tools |
| **Supervisor Pattern** | `supervisor_agent` | Multi-agent coordination | Supervisor delegates to specialized sub-agents |
| **Human-In-The-Loop** | `hitl_agent` | High-stakes operations | Pauses execution for human approval before tool execution |

**Documentation:**
- [Simple Agent Guide](SIMPLE_AGENT.md) - Using simple agents with MCP servers and custom tools
- [Supervisor Pattern Guide](SUPERVISOR.md) - Coordinating multiple sub-agents
- [Human-In-The-Loop Guide](HITL_USAGE.md) - Adding human oversight to agent operations

To see which agents are available, check the `app/engine/` directory or look at the API documentation at `http://localhost:8000/docs` once the server is running.

## Quick Start

### Prerequisites

- Python 3.13+
- [UV](https://docs.astral.sh/uv/) package manager (recommended) or pip
- PostgreSQL (optional - for production persistence, can run in-memory mode)
- LLM API key (configured in `.env` file)

### Installation

```bash
# Install dependencies
uv sync

# Or with pip
pip install -e .

# The .env file should already be included from generation
# If not, copy .env.example to .env and configure your API keys
```

### Run the Application

**Option 1: Local Development**

```bash
# Run with uvicorn
python -m app.main

# Or with uv
uv run uvicorn app.main:app --reload

# Server runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

**Option 2: Docker Compose (Recommended for Production)**

The easiest way to start the application with Docker Compose:

```bash
# Start application (stops existing containers, rebuilds, and starts)
bash local-environment.sh

# Application will be available at http://localhost:8000
# Database migrations run automatically
```

This script will:
- Stop any existing containers
- Rebuild and start all services (PostgreSQL + API)
- Run database migrations automatically
- Start the application in detached mode

**Note:** Database configuration is optional. If no `DATABASE_URL` is specified, the app will run in in-memory mode and data will not persist between restarts.

### Test Your Agents

**Completion Response (Non-Streaming):**

```bash
# Replace <agent_name> with your actual agent name from the config
curl -X POST http://localhost:8000/agents \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "<agent_name>",
    "query": "Your question here"
  }'
```

The response will include:
- `response`: The agent's complete response text
- `session_id`: Session ID for maintaining conversation context
- `execution_time_ms`: Time taken to process the request

**Streaming Response:**

The API supports Server-Sent Events (SSE) for streaming responses:

```bash
curl -X POST http://localhost:8000/agents/stream \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "agent_name": "<agent_name>",
    "query": "Your question here"
  }'
```

Streaming responses include events for:
- `message`: Agent messages as they're generated
- `tool_call`: Tool invocations
- `interrupt`: Human-in-the-loop interruption points (for HITL agents)
- `complete`: Final completion status with session_id

**Session Persistence:**

To test memory persistence, specify the agent session_id in subsequent questions:

```bash
curl -X POST http://localhost:8000/agents \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "<agent_name>",
    "query": "Your follow-up question here",
    "session_id": <agent_session_id>
  }'
```

For more details, check the API documentation at `http://localhost:8000/docs`.

## Architecture

```
app/
├── api/agents/          # FastAPI routes, controllers, services
│   ├── routes.py        # API endpoints
│   ├── service.py        # Business logic and agent orchestration
│   └── repository.py    # Database operations
├── core/                # Core infrastructure
│   ├── settings.py      # Application settings (from .env)
│   ├── db/              # Database connection and models
│   ├── logger.py         # Structured logging
│   └── telemetry/        # OpenTelemetry observability
└── engine/              # Your generated agents
    └── <agent_name>/     # Each agent you configured
        └── agent.py      # Agent implementation
```

**Key Components:**

- **API Layer** - RESTful endpoints with Server-Sent Events (SSE) streaming
- **Stream Processor** - Converts LangChain events to typed StreamEvent objects
- **Agent Engine** - Your custom agents, each self-contained
- **Core Infrastructure** - Database (async SQLAlchemy), observability (OpenTelemetry), structured logging

## Customization

### Modifying Your Agents

Your agents are located in `app/engine/<agent_name>/agent.py`. You can:

- **Update prompts** - Modify the system prompts in the agent code
- **Add custom tools** - Add Python functions directly to your agent (see [Custom Tools Guide](CUSTOM_TOOLS.md))
- **Add MCP tools** - Integrate tools from MCP servers for shared functionality
- **Change models** - Update the model configuration in agent code or via `.env`
- **Adjust temperature** - Modify LLM parameters in the agent implementation

### Agent Pattern-Specific Guides

- **[Simple Agent Guide](SIMPLE_AGENT.md)** - Learn how to use simple agents, configure MCP servers, and add custom tools
- **[Supervisor Pattern Guide](SUPERVISOR.md)** - Understand how supervisor agents coordinate sub-agents and delegate tasks
- **[Human-In-The-Loop Guide](HITL_USAGE.md)** - Configure human oversight for high-stakes operations

### Adding Tools to Your Agent

There are two ways to add capabilities to your agent:

**Option 1: Custom Tools (Agent-Specific)**
- Add Python functions directly to your agent for simple, agent-specific logic
- **Best for:** Simple utilities (calculators, formatters, validators), agent-specific business logic, rapid prototyping
- See the [Custom Tools Guide](CUSTOM_TOOLS.md) for detailed instructions

**Option 2: MCP Servers (Shared Tools)**
- Connect to MCP servers for standardized, reusable tools across multiple agents
- **Best for:** Complex integrations (databases, APIs, external services), tools shared across multiple agents
- Tools from MCP servers are automatically discovered at runtime and made available to your agent
- **Note:** For MCP servers based on npx, uncomment the Node and npm installation in the Dockerfile. 

**Combining Both Approaches:**
You can use both custom tools and MCP tools in the same agent. The generated agent code automatically combines tools from both sources.

### Environment Configuration

All configuration is managed via the `.env` file:

```bash
# LLM Configuration
LLM_API_KEY=your-api-key-here
LLM_BASE_URL=  # Optional, for custom endpoints
LLM_MODEL=gpt-4o-mini  # Optional, defaults in settings
LLM_TEMPERATURE=0.0  # Optional

# Database Configuration (Optional)
# If no DATABASE_URL is specified, the app will run in in-memory mode
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Observability (Optional)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your-langsmith-key
```

### Using Agents Programmatically

You can use your agents directly in Python code without the API:

```python
from app.engine.<agent_name>.agent import create_agent_instance
from app.core.settings import AppSettings

settings = AppSettings()
agent = await create_agent_instance(settings)
result = await agent.ainvoke({"messages": [HumanMessage(content="Your query")]})
```

## API Documentation

Once the server is running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Docker Deployment

### Using Docker Compose

```bash
# Build and start all services
# Note: Database migrations run automatically on container startup
docker-compose up --build

# Run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

**Automatic Migrations**: When using Docker Compose, database migrations are automatically applied when the container starts. No manual migration step is required.

### Using Docker Only

**Database Configuration (Optional):** The API container can run with or without a PostgreSQL database. You can either:
- Use Docker Compose (includes PostgreSQL automatically - see above)
- Provide a `DATABASE_URL` environment variable pointing to an external PostgreSQL instance
- Run without a database (in-memory mode - data won't persist)

If you only want to run the API container (without the PostgreSQL service from docker-compose):

```bash
# Build the image
docker build -t my-agent-app .

# Run the container
docker run -p 8000:8000 --env-file .env my-agent-app

# Or with custom environment variables
docker run -p 8000:8000 \
  -e LLM_API_KEY=your-key-here \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  my-agent-app
```

See the Dockerfile and docker-compose.yml for configuration details.

## Development

### Development Commands

```bash
# Install dependencies
uv sync --extra dev

# Run the application (development mode with auto-reload)
uv run uvicorn app.main:app --reload

# Format code (Black)
uv run black --line-length 120 ./app

# Run database migrations (for local development without Docker)
# Note: Migrations run automatically when using Docker Compose
uv run alembic upgrade head

# Create new migration
uv run alembic revision --autogenerate -m "description"
```

### Adding New Agents

To add additional agents to this repository:

1. Create directory: `app/engine/<new_agent_name>/`
2. Implement `agent.py` with a `create_agent_instance()` function
3. Register in `app/api/agents/service.py` (add to `_create_agent()` method)
4. Test via API at `http://localhost:8000/docs`

## Generated By

This repository was generated by **[La Factoria](https://github.com/xtillion/la-factoria)** - a CLI tool for generating production-ready FastAPI agent applications.

To regenerate or modify this repository, use La Factoria with your original YAML configuration file.