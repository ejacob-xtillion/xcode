# Enhanced Tool Logging - Visual Guide

## What Changed

The agent runner now displays **much better logging** for tool calls and results, making it easy to understand what the agent is doing at each step.

## New Features

### 1. ✅ Numbered Tool Calls
Each tool call is now numbered and displayed in a clear panel:

```
╭─────────────────────────────────────────────╮
│ 🔧 Tool Call #1                            │
│ Tool: neo4j_query                          │
│ ID: call_abc123                            │
│                                            │
│ Arguments:                                 │
│ {                                          │
│   "query": "MATCH (f:Function) RETURN f", │
│   "project": "xcode"                       │
│ }                                          │
╰─────────────────────────────────────────────╯
```

### 2. ✅ Syntax-Highlighted Arguments
JSON arguments are displayed with syntax highlighting for readability:
- Uses the Monokai theme
- Properly indented
- Colored keys, values, and strings

### 3. ✅ Smart Truncation
Large arguments and results are intelligently truncated in normal mode:
- Shows first 500 chars
- Indicates how much more there is
- Suggests `--verbose` to see everything

Example:
```
╭─────────────────────────────────────────────╮
│ 🔧 Tool Call #2                            │
│ Tool: read_file                            │
│                                            │
│ Arguments:                                 │
│   path, encoding                           │
│   (use --verbose to see full args)        │
╰─────────────────────────────────────────────╯
```

### 4. ✅ Clear Tool Results
Results are displayed with clear success/error indicators:

**Success:**
```
╭─────────────────────────────────────────────╮
│ ✓ Tool Result                              │
│ ID: call_abc123                            │
│                                            │
│ Output:                                    │
│ {                                          │
│   "functions": [                           │
│     {"name": "hello", "lines": 5}         │
│   ]                                        │
│ }                                          │
╰─────────────────────────────────────────────╯
```

**Error:**
```
╭─────────────────────────────────────────────╮
│ ❌ Tool Error                              │
│ ID: call_xyz789                            │
│                                            │
│ Output:                                    │
│ File not found: utils.py                   │
╰─────────────────────────────────────────────╯
```

### 5. ✅ Tool Call Summary (Verbose Mode)
At the end of execution, see a tree view of all tool calls:

```
🔧 Tool Call Summary
├── neo4j_query (3 calls)
│   ├── Call 1: query=MATCH (f:Function) RETURN f, project=xcode
│   ├── Call 2: query=MATCH (c:Class) WHERE c.name='Age...
│   └── Call 3: query=MATCH (f:Function)-[:CALLS]->()...
├── read_file (2 calls)
│   ├── Call 1: path=/Users/elijahgjacob/xcode/xcode/...
│   └── Call 2: path=/Users/elijahgjacob/xcode/tests/...
└── write_file (1 calls)
    └── Call 1: path=/Users/elijahgjacob/xcode/xcode/...
```

### 6. ✅ Execution Summary
Shows clear summary at the end:
```
Agent execution completed
Execution time: 12.45s
Session ID: abc123xyz
Total tool calls: 6
```

## Example: Full Execution Flow

Here's what you'll see when running a task:

```bash
$ xcode "add a hello function to main.py"

╭──────────────────────── Agent Configuration ────────────────────────╮
│ Task: add a hello function to main.py                              │
│ Repository: /Users/elijahgjacob/xcode                             │
│ Project: xcode                                                      │
│ Language: python                                                    │
│ Agent: xcode_coding_agent                                          │
│ LF API: http://localhost:8000                                      │
│ LLM Model: gpt-4                                                   │
│ Neo4j: bolt://localhost:7687                                       │
╰─────────────────────────────────────────────────────────────────────╯

🤖 Connecting to la-factoria agent...
✓ Connected to agent

Session created: 123


╭─────────────────────────────────────────────────────────────────╮
│ 🔧 Tool Call #1                                                 │
│ Tool: neo4j_query                                               │
│                                                                 │
│ Arguments:                                                      │
│ {                                                               │
│   "query": "MATCH (f:File) WHERE f.path CONTAINS 'main.py'",  │
│   "project": "xcode"                                           │
│ }                                                               │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ ✓ Tool Result                                                   │
│                                                                 │
│ Output:                                                         │
│ {                                                               │
│   "results": [                                                  │
│     {"f": {"path": "/Users/elijahgjacob/xcode/main.py"}}      │
│   ]                                                             │
│ }                                                               │
╰─────────────────────────────────────────────────────────────────╯


╭─────────────────────────────────────────────────────────────────╮
│ 🔧 Tool Call #2                                                 │
│ Tool: read_file                                                 │
│                                                                 │
│ Arguments:                                                      │
│ {                                                               │
│   "path": "/Users/elijahgjacob/xcode/main.py"                 │
│ }                                                               │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ ✓ Tool Result                                                   │
│                                                                 │
│ Output:                                                         │
│ def main():                                                     │
│     print("Hello from main")                                    │
╰─────────────────────────────────────────────────────────────────╯


╭─────────────────────────────────────────────────────────────────╮
│ 🔧 Tool Call #3                                                 │
│ Tool: write_file                                                │
│                                                                 │
│ Arguments:                                                      │
│ {                                                               │
│   "path": "/Users/elijahgjacob/xcode/main.py",                │
│   "content": "def hello():\n    return 'Hello!'\n\ndef..."    │
│   (use --verbose to see full content)                          │
│ }                                                               │
╰─────────────────────────────────────────────────────────────────╯

╭─────────────────────────────────────────────────────────────────╮
│ ✓ Tool Result                                                   │
│                                                                 │
│ Output:                                                         │
│ File written successfully                                       │
╰─────────────────────────────────────────────────────────────────╮


✓ Agent Response:
I've added a hello function to main.py. The function returns 'Hello!'
and I've updated the main function to call it.

Agent execution completed
Execution time: 8.34s
Session ID: 123
Total tool calls: 3
```

## Verbose Mode

With `--verbose` flag, you get even more detail:

```bash
$ xcode --verbose "add hello function"
```

Additional information shown:
- ✅ Full arguments (no truncation)
- ✅ Full results (no truncation)
- ✅ Tool call IDs
- ✅ Tool call summary tree at the end

## Comparison: Before vs After

### Before (Old Logging)
```
🔧 Tool: neo4j_query
Args: {"query": "MATCH (f:Function) RETURN f", ...}
Result: {"results": [{"f": {...}}]}
```

❌ Hard to read
❌ No visual separation
❌ JSON not formatted
❌ No success/error indicators
❌ No tool call numbers

### After (New Logging)
```
╭─────────────────────────────────────────────╮
│ 🔧 Tool Call #1                            │
│ Tool: neo4j_query                          │
│                                            │
│ Arguments:                                 │
│ {                                          │
│   "query": "MATCH (f:Function) RETURN f"  │
│ }                                          │
╰─────────────────────────────────────────────╯

╭─────────────────────────────────────────────╮
│ ✓ Tool Result                              │
│                                            │
│ Output:                                    │
│ {                                          │
│   "results": [...]                         │
│ }                                          │
╰─────────────────────────────────────────────╯
```

✅ Easy to scan
✅ Clear visual separation
✅ Syntax highlighted JSON
✅ Clear success indicators
✅ Numbered for tracking

## Benefits

1. **Better Debugging** - See exactly what the agent is doing
2. **Easy to Follow** - Numbered steps show the flow
3. **Professional Output** - Looks polished and organized
4. **Smart Defaults** - Shows enough detail without overwhelming
5. **Verbose Mode** - Deep dive when needed

## Technical Details

### New Imports
```python
from rich.syntax import Syntax
from rich.tree import Tree
from rich.table import Table
```

### Key Features
- **Rich Panels** - Visual containers for each tool call/result
- **Syntax Highlighting** - JSON is colorized and formatted
- **Smart Truncation** - Long content is shortened intelligently
- **Tree Views** - Summary shows hierarchy of tool calls
- **Counter** - Each tool call is numbered sequentially

### Event Types Handled
- `session_created` - Shows session ID
- `token` - Streams agent thinking/responses
- `tool_call` - Shows tool invocation with args
- `tool_result` - Shows tool output
- `answer` - Shows final agent response
- `error` - Shows errors with red styling
- `interrupt` - Shows interrupts with yellow styling
- `complete` - Shows execution summary

## Usage

### Normal Mode (Default)
```bash
xcode "task"
xcode -i  # Interactive mode
```
Shows:
- Tool names
- Key arguments (truncated if large)
- Results (truncated if large)
- Success/error indicators

### Verbose Mode
```bash
xcode --verbose "task"
xcode -v "task"
xcode -v -i  # Interactive + verbose
```
Shows everything above PLUS:
- Full arguments (no truncation)
- Full results (no truncation)
- Tool call IDs
- Tool call summary tree
- Additional debug info

## Try It!

```bash
# Test with a simple task
xcode --no-build-graph "create a hello function in demo/utils.py"

# See more detail
xcode --no-build-graph --verbose "create a hello function"

# In interactive mode
xcode -i
xcode> add a greeting function
xcode> /verbose
xcode> now add tests for it
```

You'll see much clearer output showing exactly what the agent is doing! 🎉
