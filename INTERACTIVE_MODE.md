# xCode Interactive Mode 🚀

## What's New

xCode now supports **interactive mode** - a Claude Code-like conversational experience for continuous coding assistance!

## Quick Start

### Start Interactive Mode

```bash
# Start interactive mode (no task argument)
xcode

# Or explicitly
xcode -i
xcode --interactive

# Skip graph building for faster startup
xcode --no-build-graph -i
```

### Single-Shot Mode (Original Behavior)

```bash
# Still works as before
xcode "add type hints to all functions"
xcode --path /path/to/repo "fix the bug"
```

## Features

### ✅ Interactive REPL
- Continuous conversation with the agent
- Maintains context between messages
- Real-time streaming output
- Command history (use Up/Down arrows)
- Reverse search with `Ctrl+R`

### ✅ Built-in Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help and available commands |
| `/clear` | Clear conversation history and start fresh |
| `/history` | Show conversation history |
| `/model <name>` | Switch LLM model |
| `/verbose` | Toggle verbose output |
| `/exit` or `/quit` | Exit interactive mode |

### ✅ Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Up/Down` | Navigate command history |
| `Ctrl+R` | Reverse search history |
| `Ctrl+C` | Cancel current input |
| `Ctrl+D` | Exit (same as /exit) |
| `Ctrl+L` | Clear screen |
| `\` + `Enter` | Multi-line input |

### ✅ Conversation History
- Automatically saved to `~/.xcode/history.txt`
- Context maintained between messages
- Last 5 messages included in agent context

## Example Session

```bash
$ xcode --no-build-graph -i

╭──────────────────────────────────────────────────────╮
│ Welcome to xCode Interactive Mode                    │
│                                                      │
│ Type your coding task and press Enter.              │
│ Available commands:                                  │
│ - /help - Show this help                            │
│ - /clear - Clear conversation history               │
│ - /history - Show conversation history              │
│ - /model <name> - Switch LLM model                  │
│ - /verbose - Toggle verbose output                  │
│ - /exit or /quit - Exit interactive mode            │
│ - Ctrl+D - Exit                                     │
│ - Ctrl+R - Search command history                   │
│                                                      │
│ Press \ then Enter for multi-line input.            │
╰──────────────────────────────────────────────────────╯

xcode> add a hello function to utils.py

🤖 Connecting to la-factoria agent...
✓ Connected to agent

[Agent streams response here...]

✓ Task completed

xcode> now add tests for it

[Agent uses previous context...]

xcode> /history

╭──────────────────────────────────────────────────────╮
│ Conversation History                                 │
├──────────────────────────────────────────────────────┤
│ User: add a hello function to utils.py             │
│ User: now add tests for it                          │
╰──────────────────────────────────────────────────────╯

xcode> /exit

Goodbye! 👋
```

## Multi-line Input

For long prompts or code blocks:

```bash
xcode> Here's the bug I'm seeing: \
... The authentication fails when
... the token expires. Can you
... investigate and fix it?
```

Or just paste multiple lines directly - xCode will detect it.

## Configuration

### Default Model

Set via environment variable:

```bash
export XCODE_MODEL=gpt-4o-mini
xcode -i
```

Or switch during session:

```bash
xcode> /model gpt-4o
✓ Switched to model: gpt-4o
```

### Verbose Mode

Toggle detailed output:

```bash
xcode> /verbose
✓ Verbose mode enabled

xcode> /verbose  
✓ Verbose mode disabled
```

## Comparison: Interactive vs Single-Shot

| Feature | Interactive Mode | Single-Shot Mode |
|---------|-----------------|------------------|
| **Usage** | `xcode` or `xcode -i` | `xcode "task"` |
| **Context** | ✅ Maintains conversation | ❌ One-off execution |
| **Commands** | ✅ Built-in commands | ❌ Not available |
| **History** | ✅ Saved & searchable | ❌ Not applicable |
| **Streaming** | ✅ Real-time output | ✅ Real-time output |
| **Use Case** | Exploratory work, multiple tasks | CI/CD, scripts, one task |

## Tips

1. **Start with `/help`** to see available commands
2. **Use `Ctrl+R`** to search previous commands
3. **Use `/clear`** to start fresh when context gets too long
4. **Use `/history`** to review what you've asked
5. **Use `\` for multi-line input** when explaining complex problems

## What's Coming Next

See [CLAUDE_CODE_ENHANCEMENT_PLAN.md](CLAUDE_CODE_ENHANCEMENT_PLAN.md) for the full roadmap:

- [ ] Session persistence (resume conversations)
- [ ] Permission modes (Auto-Accept, Plan Mode)
- [ ] Checkpointing (rewind changes with Esc+Esc)
- [ ] Bash mode (! prefix for shell commands)
- [ ] Task tracking
- [ ] Context management
- [ ] And much more!

## Architecture

```
xcode/
├── cli.py              # Updated: detects interactive vs single-shot
├── interactive.py      # NEW: Interactive session manager
├── agent_runner.py     # Updated: accepts conversation context
└── ...
```

## Troubleshooting

### "xcode command not found"
```bash
pip install -e .
```

### History not working
```bash
# History is stored in ~/.xcode/history.txt
# If it doesn't exist, it will be created on first use
ls -la ~/.xcode/
```

### Agent not responding
Make sure la-factoria is running:
```bash
# Check if it's running
curl http://localhost:8000/health

# If not, start it
cd /path/to/la-factoria
python -m app.main
```

## Feedback

This is a minimal but functional interactive mode! Try it out and let us know what works well and what needs improvement.
