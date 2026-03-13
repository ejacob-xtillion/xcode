# Claude Code Enhancement Plan for xCode

## Executive Summary

This plan outlines how to transform xCode from a single-shot task runner into a Claude Code-like interactive coding assistant with streaming, session management, keyboard shortcuts, and advanced features.

## Current State Analysis

### What We Have
- ✅ Basic CLI with task execution (`xcode "task"`)
- ✅ Knowledge graph integration (Neo4j + xgraph)
- ✅ La-factoria agent integration with HTTP streaming
- ✅ Rich terminal output
- ✅ Basic configuration management
- ✅ Single-shot task execution

### What We're Missing (Claude Code Features)
- ❌ Interactive session mode
- ❌ Conversational interface with history
- ❌ Session persistence and resumption
- ❌ Keyboard shortcuts (Ctrl+R, Shift+Tab, etc.)
- ❌ Permission modes (Auto-Accept, Plan Mode, Normal)
- ❌ Background task management
- ❌ Checkpointing/rewinding (Esc+Esc)
- ❌ Subagent delegation
- ❌ Side questions (/btw)
- ❌ Task list tracking
- ❌ Context window management
- ❌ Bash mode (! prefix)
- ❌ Skills system (/ commands)
- ❌ Vim mode
- ❌ Multi-line input

---

## Phase 1: Interactive Mode Foundation

### 1.1 Interactive REPL
**Goal**: Enable continuous conversation mode instead of single-shot execution

**Implementation**:
- Add `--interactive` / `-i` flag (make default if no task provided)
- Use `prompt_toolkit` for rich terminal input with:
  - Command history (Up/Down arrows)
  - Multi-line input (Shift+Enter or `\` + Enter)
  - Tab completion for file paths (@mentions)
  - Syntax highlighting for code blocks
- Create `InteractiveSession` class to manage conversation state
- Stream responses from la-factoria in real-time

**Files to Create/Modify**:
- `xcode/interactive.py` - New interactive session manager
- `xcode/cli.py` - Add interactive mode entry point
- Update `agent_runner.py` - Support conversational context

**Example Usage**:
```bash
# Start interactive mode
xcode
xcode --interactive
xcode -i

# Or single-shot (existing behavior)
xcode "fix the bug"
```

### 1.2 Session Management
**Goal**: Persist conversations and enable resumption

**Implementation**:
- Store sessions in `~/.xcode/sessions/`
- JSON format: `{session_id}.json` with:
  - Conversation history (messages, tool calls, results)
  - Metadata (created, last_modified, project_path)
  - Git context (branch, uncommitted changes)
- Implement session lifecycle:
  - Create new session on start
  - Auto-save after each turn
  - List sessions with `--list-sessions`
  - Resume with `--continue` / `-c` or `--resume <id>`
  - Fork with `--fork-session`

**Files to Create**:
- `xcode/session.py` - Session storage/retrieval
- `xcode/session_manager.py` - Session lifecycle management

**Example Usage**:
```bash
xcode -c                    # Continue last session
xcode --resume abc123       # Resume specific session
xcode -c --fork-session     # Fork from last session
xcode --list-sessions       # Show all sessions
```

---

## Phase 2: Advanced Input & Controls

### 2.1 Keyboard Shortcuts
**Goal**: Match Claude Code's keyboard shortcuts using `prompt_toolkit`

**Core Shortcuts to Implement**:
| Shortcut | Function | Priority |
|----------|----------|----------|
| `Ctrl+C` | Cancel/Interrupt | HIGH |
| `Ctrl+D` | Exit session | HIGH |
| `Ctrl+L` | Clear screen | HIGH |
| `Shift+Tab` | Toggle permission mode | HIGH |
| `Ctrl+R` | Reverse search history | MEDIUM |
| `Esc` + `Esc` | Rewind/checkpoint | HIGH |
| `Ctrl+G` | Open in $EDITOR | MEDIUM |
| `Ctrl+O` | Toggle verbose | LOW |
| `Up/Down` | Navigate history | HIGH |

**Implementation**:
- Use `prompt_toolkit.key_binding` for custom bindings
- Create `KeyBindingManager` class
- Store preferences in `~/.xcode/config.json`

**Files to Create**:
- `xcode/keybindings.py` - Keyboard shortcut definitions
- Update `xcode/interactive.py` - Integrate bindings

### 2.2 Multi-line Input
**Goal**: Support code blocks and long prompts

**Implementation**:
- Default: `\` + Enter for continuation
- Optional: `Shift+Enter` (needs terminal support)
- Auto-detect pasted code blocks
- Syntax highlighting for code in prompts

**Already handled by `prompt_toolkit` if configured correctly**

### 2.3 Command System (/ prefix)
**Goal**: Built-in commands like Claude Code

**Core Commands**:
| Command | Function | Priority |
|---------|----------|----------|
| `/help` | Show help | HIGH |
| `/clear` | Clear context, start fresh | HIGH |
| `/history` | Show session history | MEDIUM |
| `/model <name>` | Switch model | HIGH |
| `/context` | Show context usage | MEDIUM |
| `/rewind` | Rewind to checkpoint | HIGH |
| `/btw <question>` | Side question | LOW |
| `/config` | Edit configuration | MEDIUM |
| `/doctor` | Diagnose issues | LOW |
| `/verbose` | Toggle verbose mode | LOW |

**Implementation**:
- Command registry pattern
- Each command is a plugin
- Tab completion for commands

**Files to Create**:
- `xcode/commands/` - Directory for command implementations
- `xcode/commands/base.py` - Base command class
- `xcode/commands/registry.py` - Command discovery/dispatch

---

## Phase 3: Permission System & Safety

### 3.1 Permission Modes
**Goal**: Control what agent can do without asking

**Three Modes**:
1. **Normal Mode** (default): Ask before file edits and shell commands
2. **Auto-Accept Mode**: Auto-approve file edits (still ask for commands)
3. **Plan Mode**: Read-only, creates plan instead of executing

**Implementation**:
- Add `PermissionManager` class
- Store mode in session state
- Toggle with `Shift+Tab` keyboard shortcut
- Show current mode in prompt/status bar
- Integrate with la-factoria agent (pass permission mode in request)

**Files to Create**:
- `xcode/permissions.py` - Permission system
- Update `agent_runner.py` - Pass permission context

**UI Indicator**:
```bash
[AUTO-ACCEPT] xcode>    # Auto-accept mode (file edits allowed)
[PLAN] xcode>          # Plan mode (read-only)
xcode>                 # Normal mode
```

### 3.2 Checkpointing System
**Goal**: Rewind file changes like Claude Code (Esc+Esc)

**Implementation**:
- Before any file edit, create checkpoint:
  - Store original file content
  - Store file hash
  - Track in session metadata
- Implement rewind:
  - Show checkpoint list
  - Allow selection
  - Restore files to checkpoint state
- Store checkpoints in `~/.xcode/sessions/{session_id}/checkpoints/`

**Files to Create**:
- `xcode/checkpoint.py` - Checkpoint management
- Update `agent_runner.py` - Create checkpoints before edits

**Example**:
```bash
# User presses Esc+Esc
[Checkpoints]
1. Initial state (5 minutes ago)
2. After adding auth module (2 minutes ago)
3. After fixing tests (1 minute ago)

Select checkpoint to rewind to: _
```

---

## Phase 4: Advanced Features

### 4.1 Bash Mode (! prefix)
**Goal**: Run shell commands directly

**Implementation**:
- Detect `!` prefix at start of input
- Execute command in subprocess
- Stream output to console
- Add command output to conversation context
- Support `Ctrl+B` to background long-running commands

**Files to Update**:
- `xcode/interactive.py` - Detect and handle `!` prefix
- `xcode/shell_executor.py` - New file for shell execution

**Example**:
```bash
xcode> ! npm test
xcode> ! git status
xcode> ! ls -la
```

### 4.2 Task List
**Goal**: Track multi-step work progress

**Implementation**:
- Agent creates tasks when working on complex problems
- Store in session state
- Display in status bar or footer
- Commands: `/tasks`, `/clear-tasks`
- Support `XCODE_TASK_LIST_ID` env var for shared task lists

**Files to Create**:
- `xcode/task_list.py` - Task tracking
- Update `agent_runner.py` - Parse task events from la-factoria

**UI Example**:
```bash
[Tasks: 2/5 complete]
✓ 1. Understand authentication flow
✓ 2. Locate session handling code
⧗ 3. Implement OAuth support
☐ 4. Write tests
☐ 5. Update documentation
```

### 4.3 Context Management
**Goal**: Monitor and manage context window usage

**Implementation**:
- Track tokens used in conversation
- Show context usage with `/context` command
- Auto-compact when approaching limit:
  - Remove old tool outputs
  - Summarize early conversation
  - Preserve key instructions
- Support compact instructions in `XCODE.md`

**Files to Create**:
- `xcode/context_manager.py` - Context tracking and compaction

### 4.4 Side Questions (/btw)
**Goal**: Ask quick questions without affecting main conversation

**Implementation**:
- Use la-factoria's prompt cache for efficiency
- Create ephemeral conversation branch
- Display in overlay (dismissible)
- No tools available (context-only answers)
- Works even while agent is processing

**Lower priority - depends on la-factoria supporting this pattern**

### 4.5 Subagent Delegation
**Goal**: Spawn parallel agents for focused work

**Implementation**:
- Integrate with la-factoria's subagent system
- Allow up to 10 parallel subagents
- Each gets fresh context
- Return summary to main conversation
- Use for: exploration, testing, parallel work

**Lower priority - depends on la-factoria subagent API**

---

## Phase 5: Enhanced UX

### 5.1 Status Bar / Footer
**Goal**: Show session info persistently

**Information to Display**:
- Current session ID (short form)
- Permission mode indicator
- Active branch (from git)
- Task count (if any)
- Context usage percentage
- Model name

**Implementation**:
- Use `rich.live.Live` with custom status layout
- Update in real-time during agent work

**Example**:
```bash
╭──────────────────────────────────────────────────────────╮
│ Session: abc123 │ main │ [AUTO] │ Tasks: 2/5 │ GPT-4 │ 45% │
╰──────────────────────────────────────────────────────────╯
xcode> _
```

### 5.2 Rich Output Formatting
**Goal**: Better visualization of agent work

**Features**:
- Syntax highlighted code blocks in responses
- Collapsible tool calls (expand with click/key)
- Progress indicators for long operations
- Diff view for file changes
- Tree view for file structure

**Implementation**:
- Use `rich.syntax.Syntax` for code
- Use `rich.tree.Tree` for structure
- Use `rich.panel.Panel` for sections

### 5.3 Vim Mode (Optional)
**Goal**: Vim keybindings for power users

**Implementation**:
- `prompt_toolkit` has built-in vim mode
- Enable with `/vim` command or config
- Store preference in `~/.xcode/config.json`

**Lower priority**

---

## Phase 6: Memory & Learning

### 6.1 XCODE.md (like CLAUDE.md)
**Goal**: Persistent project instructions

**Implementation**:
- Check for `XCODE.md` in repo root
- Load first 200 lines at session start
- Support sections:
  - Project overview
  - Coding conventions
  - Common workflows
  - Compact instructions (for context management)
- Command: `/init` to create template

**Files to Create**:
- `xcode/memory.py` - XCODE.md loading/management
- Template: `xcode/templates/XCODE.md`

**Example XCODE.md**:
```markdown
# xCode Project Memory

## Project Overview
This is a Python CLI tool for AI-powered coding with knowledge graphs.

## Coding Conventions
- Use type hints for all functions
- Follow Black formatting
- Write docstrings in Google style
- Tests go in tests/ directory

## Common Workflows
- Run tests: `pytest tests/`
- Format code: `black .`
- Build graph: `xgraph analyze`

## Compact Instructions
When compacting context, preserve:
- Knowledge graph schema
- Neo4j connection details
- La-factoria integration patterns
```

### 6.2 Auto Memory (Optional)
**Goal**: Agent learns preferences over time

**Implementation**:
- Store learnings in `~/.xcode/memory/`
- Categories: preferences, patterns, decisions
- Load relevant memories at session start
- Command: `/memory` to view/edit

**Lower priority**

---

## Phase 7: Integration Enhancements

### 7.1 Enhanced La-factoria Integration
**Goal**: Leverage all la-factoria capabilities

**Enhancements**:
- Stream all event types (tokens, tool_calls, tool_results, etc.)
- Support streaming interrupts (allow user to stop/redirect mid-execution)
- Pass session context (history, checkpoints, permissions)
- Support subagent spawning
- Handle tool approval requests

**Files to Update**:
- `xcode/agent_runner.py` - Enhanced streaming and event handling

### 7.2 Neo4j Query Tool Integration
**Goal**: Let user query knowledge graph directly

**Implementation**:
- Command: `/graph <cypher-query>`
- Command: `/explore <entity-name>` - Navigate graph visually
- Show results in rich table format
- Cache common queries

**Files to Create**:
- `xcode/graph_query.py` - Interactive graph querying

---

## Implementation Priority

### Sprint 1: Core Interactive Experience (2-3 weeks)
1. ✅ Basic interactive REPL with prompt_toolkit
2. ✅ Session management (create, save, resume)
3. ✅ Command system foundation (/help, /clear, /history)
4. ✅ Conversational context in la-factoria

### Sprint 2: Controls & Safety (1-2 weeks)
5. ✅ Keyboard shortcuts (Ctrl+C, Ctrl+D, Shift+Tab, Esc+Esc)
6. ✅ Permission modes (Normal, Auto-Accept, Plan)
7. ✅ Checkpointing system
8. ✅ Multi-line input

### Sprint 3: Advanced Input (1-2 weeks)
9. ✅ Bash mode (! prefix)
10. ✅ Command history with Ctrl+R
11. ✅ Model switching (/model)
12. ✅ Context monitoring (/context)

### Sprint 4: Enhanced UX (1-2 weeks)
13. ✅ Status bar with session info
14. ✅ Task list tracking
15. ✅ Rich output formatting
16. ✅ XCODE.md support

### Sprint 5: Advanced Features (2-3 weeks)
17. ⏳ Context management and compaction
18. ⏳ Graph querying commands
19. ⏳ Side questions (/btw)
20. ⏳ Subagent delegation

### Sprint 6: Polish & Optional Features (1-2 weeks)
21. ⏳ Vim mode
22. ⏳ Auto memory
23. ⏳ Additional commands
24. ⏳ Performance optimization

---

## Technical Architecture

### New Component Structure

```
xcode/
├── cli.py                  # Entry point (enhanced)
├── interactive.py          # NEW: Interactive REPL manager
├── session.py             # NEW: Session storage/retrieval
├── session_manager.py     # NEW: Session lifecycle
├── keybindings.py         # NEW: Keyboard shortcuts
├── permissions.py         # NEW: Permission system
├── checkpoint.py          # NEW: Checkpoint management
├── context_manager.py     # NEW: Context tracking
├── task_list.py           # NEW: Task tracking
├── memory.py              # NEW: XCODE.md loading
├── shell_executor.py      # NEW: Shell command execution
├── graph_query.py         # NEW: Interactive graph queries
├── commands/              # NEW: Command implementations
│   ├── base.py
│   ├── registry.py
│   ├── help.py
│   ├── clear.py
│   ├── history.py
│   ├── model.py
│   └── ...
├── templates/             # NEW: Templates for XCODE.md etc.
│   └── XCODE.md
├── ui/                    # NEW: UI components
│   ├── status_bar.py
│   ├── formatters.py
│   └── themes.py
├── agent_runner.py        # UPDATED: Enhanced la-factoria integration
├── orchestrator.py        # UPDATED: Support interactive mode
├── config.py              # UPDATED: Interactive mode config
└── ...
```

### Data Storage

```
~/.xcode/
├── sessions/              # Session storage
│   ├── {session-id}.json
│   └── {session-id}/
│       └── checkpoints/
│           ├── checkpoint-1.json
│           └── files/
├── memory/                # Auto memory (optional)
│   └── learnings.json
├── config.json            # User preferences
└── history.txt            # Command history
```

---

## Dependencies to Add

### Core
- `prompt_toolkit` - Rich terminal input with history, completion, keybindings
- `rich` (already have) - Terminal formatting
- `click` (already have) - CLI framework

### Optional
- `watchdog` - File watching for hot reload
- `gitpython` - Enhanced git integration
- `pygments` (comes with rich) - Syntax highlighting

### Installation
```bash
pip install prompt_toolkit watchdog gitpython
```

---

## Configuration

### New Config Options (`~/.xcode/config.json`)

```json
{
  "interactive": {
    "default_mode": "interactive",
    "auto_save_sessions": true,
    "max_history": 1000,
    "enable_vim_mode": false,
    "multiline_key": "shift-enter"
  },
  "permissions": {
    "default_mode": "normal",
    "auto_approve_commands": ["git status", "npm test", "pytest"],
    "require_approval_for_rm": true
  },
  "ui": {
    "show_status_bar": true,
    "show_task_list": true,
    "theme": "monokai",
    "syntax_highlighting": true
  },
  "context": {
    "auto_compact": true,
    "compact_threshold": 0.8,
    "preserve_messages": 10
  },
  "agent": {
    "default_model": "gpt-4",
    "stream_output": true,
    "verbose": false
  }
}
```

---

## Testing Strategy

### Unit Tests
- Test each new component in isolation
- Mock la-factoria responses
- Test session serialization/deserialization
- Test checkpoint creation/restoration

### Integration Tests
- Test full interactive sessions
- Test session resumption
- Test permission mode switching
- Test command execution

### Manual Testing
- Create comprehensive test scenarios document
- Test keyboard shortcuts on different terminals
- Test with different la-factoria agent behaviors
- Test with large contexts

---

## Breaking Changes & Migration

### For Users
- **No breaking changes** - existing single-shot usage still works
- Interactive mode is opt-in (or default if no task provided)
- Existing scripts/CI workflows unaffected

### For Developers
- Some internal APIs will change (agent_runner, orchestrator)
- Session format is new - old "results" may not be compatible
- Configuration file location: `~/.xcode/` instead of just `.env`

---

## Success Metrics

### Feature Completeness
- [ ] Interactive mode works
- [ ] Session persistence works
- [ ] All keyboard shortcuts work
- [ ] Permission modes work
- [ ] Checkpointing works
- [ ] Task tracking works
- [ ] Context management works

### User Experience
- [ ] Startup time < 2 seconds
- [ ] Response streaming feels immediate
- [ ] Keyboard shortcuts feel native
- [ ] Commands are discoverable
- [ ] Error messages are helpful

### Compatibility
- [ ] Works on macOS, Linux, Windows
- [ ] Works in VS Code terminal, iTerm2, Terminal.app
- [ ] Works with different shells (bash, zsh, fish)

---

## Future Enhancements (Post-MVP)

1. **Remote Control**: Start session on server, control from browser
2. **Cloud Execution**: Run agents in cloud VMs
3. **IDE Integrations**: VS Code extension, JetBrains plugin
4. **Web UI**: Browser-based interface
5. **MCP Integration**: Connect to external services
6. **Skills System**: Custom workflows and templates
7. **Hooks**: Automation and CI/CD integration
8. **Multi-project Sessions**: Work across multiple repos
9. **Team Features**: Shared sessions, collaborative editing
10. **Analytics**: Usage tracking, performance monitoring

---

## Questions & Decisions

### 1. Should interactive mode be default?
**Proposal**: Yes, if no task provided. Single-shot with task argument.
```bash
xcode              # Interactive (new)
xcode "fix bug"    # Single-shot (existing)
```

### 2. How to handle long-running la-factoria responses?
**Proposal**: Stream with ability to interrupt (Ctrl+C), checkpoint automatically.

### 3. Should we fork la-factoria or integrate as-is?
**Proposal**: Integrate as-is via HTTP API. La-factoria is separate service.

### 4. How to handle multiple concurrent sessions?
**Proposal**: Each session is independent. Use `--session-id` or auto-detect from pwd.

### 5. Vim mode priority?
**Proposal**: Low priority. Most users prefer standard keybindings.

---

## Resources & References

### Claude Code Documentation
- [How Claude Code Works](https://code.claude.com/docs/en/how-claude-code-works)
- [Interactive Mode](https://docs.anthropic.com/en/docs/claude-code/interactive-mode)
- [CLI Reference](https://docs.anthropic.com/en/docs/claude-code/cli-usage)

### Libraries
- [prompt_toolkit documentation](https://python-prompt-toolkit.readthedocs.io/)
- [rich documentation](https://rich.readthedocs.io/)

### Similar Projects
- [aider](https://aider.chat/) - AI pair programming
- [continue.dev](https://continue.dev/) - VS Code AI assistant

---

## Timeline Estimate

- **Phase 1-2 (Core + Safety)**: 4-5 weeks
- **Phase 3-4 (Advanced Features + UX)**: 3-4 weeks
- **Phase 5-6 (Memory + Integration)**: 3-4 weeks
- **Testing & Polish**: 2 weeks

**Total**: ~12-15 weeks for full feature parity with Claude Code

---

## Next Steps

1. **Review this plan** with team/stakeholders
2. **Prototype interactive REPL** (1-2 days) to validate approach
3. **Set up project board** with tasks from this plan
4. **Begin Sprint 1** implementation
5. **Iterate based on user feedback**

---

## Appendix: Claude Code Feature Comparison

| Feature | Claude Code | xCode Current | xCode Target |
|---------|-------------|---------------|--------------|
| Interactive mode | ✅ | ❌ | 🎯 Sprint 1 |
| Session persistence | ✅ | ❌ | 🎯 Sprint 1 |
| Keyboard shortcuts | ✅ | ❌ | 🎯 Sprint 2 |
| Permission modes | ✅ | ❌ | 🎯 Sprint 2 |
| Checkpointing | ✅ | ❌ | 🎯 Sprint 2 |
| Command system | ✅ | ❌ | 🎯 Sprint 1 |
| Bash mode | ✅ | ❌ | 🎯 Sprint 3 |
| Task tracking | ✅ | ❌ | 🎯 Sprint 4 |
| Context management | ✅ | ⚠️ | 🎯 Sprint 5 |
| Memory (XCODE.md) | ✅ | ❌ | 🎯 Sprint 4 |
| Streaming | ✅ | ✅ | ✅ Have it |
| Knowledge graph | ❌ | ✅ | ✅ Unique! |
| Neo4j integration | ❌ | ✅ | ✅ Unique! |
| Model switching | ✅ | ⚠️ | 🎯 Sprint 3 |
| Subagents | ✅ | ❌ | 🎯 Sprint 5 |
| Side questions | ✅ | ❌ | 🎯 Sprint 5 |
| Vim mode | ✅ | ❌ | 🎯 Sprint 6 |

Legend:
- ✅ Fully supported
- ⚠️ Partially supported
- ❌ Not supported
- 🎯 Planned implementation
