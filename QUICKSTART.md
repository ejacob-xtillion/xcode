# Quick Start Guide - xCode

## Installation (Already Done!)

xCode is now installed and ready to use via the `xcode` command.

## How to Run xCode

### 1. Basic Usage

```bash
# Run with a task (uses current directory)
xcode "add type hints to all functions"

# Specify a repository path
xcode --path /path/to/your/repo "refactor database client"
```

### 2. Before First Run - Setup Neo4j & xgraph

xCode needs two things to work:

#### A. Install xgraph (Knowledge Graph Builder)
```bash
# From the xgraph repository
cd /Users/elijahgjacob/xgraph/xgraph
pip install -e .
```

#### B. Start Neo4j
```bash
# Option 1: Docker (easiest)
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest

# Option 2: Or install Neo4j Desktop from neo4j.com/download
```

### 3. Configure Environment Variables

Create a `.env` file in your project or set these:

```bash
# Neo4j Configuration (required)
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=password

# Optional: LLM Configuration
export XCODE_MODEL=gpt-4o-mini
export OPENAI_API_KEY=your-api-key-here  # For cloud LLMs
```

Or create `.env` file:
```bash
cd /Users/elijahgjacob/xcode
cat > .env << 'EOF'
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
EOF
```

### 4. Run Your First Task

#### With Cloud LLM (OpenAI)
```bash
# Set your OpenAI API key
export OPENAI_API_KEY=sk-...

# Run a task
xcode "add docstrings to all functions in xcode/config.py"
```

#### With Local LLM (Ollama)
```bash
# Install Ollama
brew install ollama

# Pull a model
ollama pull llama3.2

# Run xCode with local LLM
xcode --local "add docstrings to all functions"
```

### 5. Common Commands

```bash
# Run with verbose output (see what's happening)
xcode --verbose "your task"

# Use a specific model
xcode --model llama3.2 "your task"

# Skip rebuilding the knowledge graph (faster)
xcode --no-build-graph "your task"

# Test with the xcode repository itself
cd /Users/elijahgjacob/xcode
xcode "add docstrings to xcode/cli.py"
```

### 6. Example: Running on xCode Repository

```bash
cd /Users/elijahgjacob/xcode

# With cloud LLM
xcode --verbose "review and add docstrings to cli.py"

# With local LLM
xcode --local --model llama3.2 "review and add docstrings to cli.py"

# On a different repo
xcode --path ~/my-project "fix all type errors"
```

## Current Status

✅ **Installed**: xcode CLI is ready
⚠️ **Needs Setup**: 
  1. Install xgraph: `cd /Users/elijahgjacob/xgraph/xgraph && pip install -e .`
  2. Start Neo4j: `docker run -d -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j`
  3. Set environment variables (see above)

## Troubleshooting

### Error: "xgraph not found"
```bash
cd /Users/elijahgjacob/xgraph/xgraph
pip install -e .
```

### Error: "Neo4j connection failed"
```bash
# Check Neo4j is running
docker ps | grep neo4j

# Start Neo4j if not running
docker start neo4j

# Or create new container
docker run -d --name neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j
```

### Error: "OpenAI API key not found"
```bash
export OPENAI_API_KEY=sk-your-key-here
```

Or use local LLM:
```bash
xcode --local "your task"
```

## What Happens When You Run xCode?

1. **Build Knowledge Graph**: Analyzes your codebase and creates a graph in Neo4j
2. **Spawn Agent**: Creates an AI agent with context about your code
3. **Execute Task**: Agent completes the task using graph knowledge
4. **Verify**: Runs tests and linters to verify success
5. **Iterate**: Re-runs if needed until success or max iterations

## Help & Options

```bash
# See all options
xcode --help

# Check version
python -c "import xcode; print(xcode.__version__)"
```

## Next Steps

1. **Install prerequisites** (xgraph, Neo4j)
2. **Set environment variables**
3. **Try a simple task**: `xcode --verbose "add a print statement to cli.py"`
4. **Experiment with local LLMs**: Install Ollama and try `xcode --local`

For full documentation, see `/Users/elijahgjacob/xcode/README.md`
