FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./
COPY README.md ./

# Install dependencies first (for better caching)
RUN pip install --no-cache-dir \
    click>=8.1.0 \
    rich>=13.0.0 \
    openai>=1.0.0 \
    python-dotenv>=1.0.0 \
    pydantic>=2.0.0 \
    httpx>=0.25.0 \
    prompt-toolkit>=3.0.0 \
    xgraph

# Copy application code
COPY . /app/

# Install xcode in editable mode
RUN pip install --no-cache-dir -e .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV XCODE_AGENT_URL=http://xcode-agent:8000

# Default command: interactive mode
CMD ["xcode", "-i"]
