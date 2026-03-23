FROM python:3.13-slim

WORKDIR /app

# System packages (add more as needed)
RUN apt-get update \
    && apt-get install -y \
        curl \
        nodejs \
        npm \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Enable bytecode compilation for faster startup and copy mode for Docker
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Copy dependency files and README (needed by hatchling build)
COPY pyproject.toml uv.lock README.md ./

# Install dependencies only (without project code) for better layer caching
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY . /app/

# Install the project itself (reuses cached dependencies)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# Create symbolic links for MCP filesystem access from working directory
RUN ln -s /demo /app/demo && ln -s /output /app/output

# Make startup script executable
RUN chmod +x /app/start.sh

# Use bash explicitly to avoid permission issues with volume mounts
CMD ["bash", "/app/start.sh"]