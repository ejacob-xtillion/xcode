# Fix: Excessive Tool Calls on Short/Invalid Messages

## Problem

When users entered short or invalid messages like "hi]", the agent would:
1. Make excessive tool calls (11+ `read_text_file`, `read_neo4j_cypher`)
2. Not provide any visible output or answer
3. Appear stuck or unresponsive
4. Waste API tokens and time

### Example of the Problem

```bash
$ xcode --no-build-graph "hi]"

Session created: 12
🔧 Tool: read_neo4j_cypher
🔧 Tool: read_text_file
🔧 Tool: read_text_file
🔧 Tool: read_text_file
🔧 Tool: read_text_file
🔧 Tool: read_text_file
🔧 Tool: read_text_file
🔧 Tool: read_text_file
🔧 Tool: read_text_file
🔧 Tool: read_text_file
🔧 Tool: read_text_file
🔧 Tool: read_text_file
# ... no output, just hangs
```

## Root Cause

The agent prompt instructed it to "**Always query the knowledge graph first**" without first evaluating whether the task was valid or required code inspection. This caused the agent to blindly execute tools even for greetings or invalid inputs.

## Solution

### 1. Client-Side Validation (xcode/agent_runner.py)

Added `_validate_task()` method that checks:
- Minimum length (3 characters)
- Invalid patterns (special characters only, greetings like "hi", "hello", "test")

```python
def _validate_task(self) -> tuple[bool, str]:
    """Validate the task before sending to the agent."""
    import re
    
    task = self.config.task.strip()
    
    # Check minimum length
    if len(task) < 3:
        return False, "Task is too short. Please provide a meaningful coding task."
    
    # Check for common invalid patterns
    invalid_patterns = [
        (r'^[^a-zA-Z0-9\s]+$', "Task contains only special characters"),
        (r'^(hi|hello|hey|test)[\]!.]*$', "Please provide a specific coding task instead of a greeting"),
    ]
    
    for pattern, message in invalid_patterns:
        if re.match(pattern, task, re.IGNORECASE):
            return False, message
    
    return True, ""
```

### 2. Agent Prompt Updates (la-factoria/configs/config_xcode.yaml)

Updated the workflow to emphasize task evaluation:

```yaml
## Your Workflow

1. **Understand the Task**:
   - Parse the user's request carefully
   - Determine if this is a valid coding task or just a greeting/question
   - If it's not a coding task (e.g., "hi", "hello", "test"), respond politely WITHOUT using any tools
   - Identify what needs to be changed and why

2. **Query the Knowledge Graph** (ONLY for coding tasks):
   - Use neo4j_query to understand the codebase structure
   ...
```

Added to guidelines:
- **Evaluate the task first** - if it's not a coding task, respond directly without tools
- **Avoid unnecessary tool calls** - only use tools when the task requires code inspection or modification

### 3. Updated Agent Query Prompt (xcode/agent_runner.py)

Added important guidelines to the query sent to the agent:

```python
**Important Guidelines:**
- If the task is unclear, ambiguous, or not a valid coding request, respond immediately without using tools
- Only use tools when the task requires actual code inspection or modification
- For greetings, questions, or non-coding requests, respond directly
```

## Results

### Before Fix
```bash
$ xcode --no-build-graph "hi]"
Session created: 12
🔧 Tool: read_neo4j_cypher
🔧 Tool: read_text_file
🔧 Tool: read_text_file
... (11+ tool calls, no output)
```

### After Fix
```bash
$ xcode --no-build-graph "hi]"
╭─────────────────────────────╮
│ xCode - AI Coding Assistant │
│ Task: hi]                   │
╰─────────────────────────────╯

Starting agent for task: hi]

⚠ Invalid task: Please provide a specific coding task instead of a greeting
Example: 'Add a function to calculate fibonacci numbers'

✗ Task failed: Please provide a specific coding task instead of a greeting
```

**Result:**
- ✅ Immediate feedback (< 1 second)
- ✅ No unnecessary tool calls
- ✅ Clear error message with example
- ✅ No wasted API tokens

### Valid Tasks Still Work
```bash
$ xcode --no-build-graph "List all Python files in the xcode directory"
╭──────────────────────────── Agent Configuration ─────────────────────────────╮
│ Task: List all Python files in the xcode directory                           │
│ Repository: /Users/elijahgjacob/xcode                                        │
│ ...                                                                          │
╰──────────────────────────────────────────────────────────────────────────────╯

🤖 Connecting to la-factoria agent...
✓ Connected to agent
Session created: 2
# ... agent processes the task normally
```

## Files Changed

### xCode Repository (fix/short-message branch)
- `xcode/agent_runner.py`:
  - Added `_validate_task()` method
  - Updated `_run_agent_async()` to validate before sending to agent
  - Updated `_build_agent_query()` to include task evaluation guidelines
- `xcode/cli.py`:
  - Fixed duplicate `XCodeOrchestrator` import that caused scoping issues

### la-factoria Repository (dev branch)
- `configs/config_xcode.yaml`:
  - Updated workflow to emphasize task evaluation
  - Added "(ONLY for coding tasks)" markers
  - Added guideline to avoid unnecessary tool calls

## Testing

### Test Invalid Inputs
```bash
xcode --no-build-graph "hi"      # Rejected: greeting
xcode --no-build-graph "hi]"     # Rejected: greeting with special char
xcode --no-build-graph "test"    # Rejected: greeting
xcode --no-build-graph "!@#"     # Rejected: special characters only
xcode --no-build-graph "ab"      # Rejected: too short
```

### Test Valid Inputs
```bash
xcode --no-build-graph "List Python files"                    # Accepted
xcode --no-build-graph "Add type hints to functions"          # Accepted
xcode --no-build-graph "Fix the bug in calculate_total()"     # Accepted
```

## Benefits

1. **Better UX**: Users get immediate feedback on invalid inputs
2. **Cost Savings**: No wasted API tokens on invalid requests
3. **Performance**: No unnecessary Neo4j queries or file reads
4. **Clarity**: Clear error messages guide users to provide valid tasks
5. **Agent Intelligence**: Agent now evaluates task validity before acting

## Future Improvements

Consider adding:
- More sophisticated task validation (e.g., detect questions vs. commands)
- Suggestion system for common invalid inputs
- Task history to detect patterns
- Interactive mode to clarify ambiguous tasks
