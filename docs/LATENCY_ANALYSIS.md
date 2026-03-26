# xCode Latency Analysis & Optimization Plan

**Date:** March 24, 2026  
**Benchmark Results:** Based on live system measurements

---

## Executive Summary

**Total End-to-End Latency:** 13-30 seconds per task  
**Primary Bottleneck:** LLM API latency (98.6% of total time)  
**Secondary Bottleneck:** Tool execution overhead (11-17% of total time)

---

## Detailed Latency Breakdown

### Test 1: Neo4j Query Task
Query: "How many files are in the knowledge graph?"

| Stage | Latency | % of Total | Notes |
|-------|---------|------------|-------|
| HTTP connection | 188ms | 1.3% | FastAPI + Docker networking |
| Session creation | 6ms | 0.04% | DB insert + LangGraph init |
| **First LLM response** | **14,593ms** | **98.6%** | **GPT-5 API call** |
| Tool execution (Neo4j) | 1,623ms | 11.0% | MCP Neo4j query |
| Tool result to answer | 6,621ms | 44.7% | LLM processing tool results |
| Answer to complete | 14ms | 0.1% | Stream finalization |
| **TOTAL** | **14,804ms** | **100%** | **~15 seconds** |

### Test 2: File Read Task
Query: "Read /Users/elijahgjacob/xcode/pyproject.toml"

| Stage | Latency | % of Total | Notes |
|-------|---------|------------|-------|
| HTTP connection | 21ms | 0.2% | FastAPI + Docker networking |
| Session creation | 3ms | 0.02% | DB insert + LangGraph init |
| **First LLM response** | **13,792ms** | **99.6%** | **GPT-5 API call** |
| Tool execution (filesystem) | 2,319ms | 16.8% | MCP filesystem read |
| Tool result to answer | 7,666ms | 55.4% | LLM processing tool results |
| Answer to complete | 12ms | 0.1% | Stream finalization |
| **TOTAL** | **13,841ms** | **100%** | **~14 seconds** |

### Additional Measurements

- **Health endpoint:** 34ms (FastAPI baseline overhead)
- **Agent initialization:** 21ms (session creation + LangGraph setup)
- **Neo4j tool call:** 1,581ms (MCP query execution)
- **File read tool call:** 2,229ms (MCP filesystem operation)

---

## Identified Bottlenecks

### 1. LLM API Latency (CRITICAL - 98-99% of total time)

**Current State:**
- Using GPT-5 model via OpenAI API
- First token latency: 13,792-14,593ms (~14 seconds)
- This dominates all other latency sources combined

**Root Causes:**
- GPT-5 is a reasoning model with high latency
- Cold start / model loading time
- Network round-trip to OpenAI API
- Model inference time

**Impact:** 98.6% of total execution time

---

### 2. Tool Execution Overhead (MEDIUM - 11-17% of total time)

**Current State:**
- Neo4j queries: 1,581-1,623ms
- File reads: 2,229-2,319ms

**Root Causes:**
- MCP protocol overhead (stdio transport with npx/uvx)
- Process spawning for each tool call
- JSON serialization/deserialization
- Docker container networking

**Impact:** 11-17% of total execution time (but only 1-2 seconds absolute)

---

### 3. Multiple LLM Calls Per Task (MEDIUM)

**Current State:**
- Typical task requires 2-3 LLM calls:
  1. Initial reasoning + first tool call (~14s)
  2. Processing tool results + generating answer (~7s)
  3. Potential follow-up calls

**Root Causes:**
- LangGraph agent loop requires LLM call after each tool execution
- No batching of tool calls
- Agent doesn't predict multiple steps ahead

**Impact:** Multiplies the LLM latency by 2-3x

---

### 4. Graph Building Latency (LOW - only on first run)

**Current State:**
- Not measured in this benchmark (skipped with --no-build-graph)
- Estimated: 10-60 seconds depending on codebase size
- Uses xgraph library with LLM for descriptions (if enabled)

**Root Causes:**
- AST parsing of entire codebase
- Multiple LLM calls for generating descriptions (if enabled)
- Neo4j bulk insert operations

**Impact:** One-time cost per codebase or when files change

---

## Optimization Plan

### Phase 1: Quick Wins (Immediate - 50-70% latency reduction)

#### 1.1 Switch to Faster LLM Model
**Current:** GPT-5 (reasoning model, ~14s first token)  
**Proposed:** GPT-4.1-mini or Claude 3.5 Sonnet (~500-2000ms first token)

**Implementation:**
```bash
# In repository root .env
LLM_MODEL=gpt-4.1-mini
# or
LLM_MODEL=claude-3-5-sonnet-20241022
LLM_BASE_URL=https://api.anthropic.com
```

**Expected Impact:**
- First token: 14,000ms → 1,500ms (90% reduction)
- Total task time: 15s → 3-5s (67-80% reduction)

**Trade-offs:**
- GPT-5 has better reasoning for complex tasks
- Consider making model configurable per task type

---

#### 1.2 Enable Tool Call Batching
**Current:** Sequential tool calls with LLM round-trip between each  
**Proposed:** Parallel tool execution where possible

**Implementation:**
- Modify LangGraph agent to support parallel tool calls
- Use LangChain's `ToolNode` with parallel execution
- Agent should predict multiple independent tools in one LLM call

**Expected Impact:**
- Reduce 2-3 LLM calls per task → 1-2 calls
- Save 7-14 seconds per task

---

#### 1.3 Cache Tool Discovery
**Current:** Tool discovery happens on every agent creation (300s TTL)  
**Proposed:** Increase cache TTL and warm cache on startup

**Implementation:**
```python
# In agent/app/engine/mcp_tools.py
class GlobalToolDiscovery:
    def __init__(self, cache_ttl_seconds: int = 3600):  # 1 hour instead of 5 min
```

**Expected Impact:**
- Save 100-500ms on subsequent requests
- Minimal impact on first request

---

### Phase 2: Medium-Term Improvements (30-50% additional reduction)

#### 2.1 Optimize MCP Tool Transport
**Current:** stdio transport spawning npx/uvx processes  
**Proposed:** Long-lived MCP server processes or HTTP transport

**Implementation:**
- Start MCP servers as persistent processes/containers
- Use HTTP or SSE transport instead of stdio
- Reuse connections across tool calls

**Expected Impact:**
- Tool execution: 2,000ms → 200-500ms (75% reduction)
- More significant for tasks with many tool calls

---

#### 2.2 Add Response Streaming Optimization
**Current:** Full LLM response before tool execution  
**Proposed:** Stream tool calls as soon as detected

**Implementation:**
- Parse tool calls from partial LLM responses
- Start tool execution before full response completes
- Pipeline LLM generation with tool execution

**Expected Impact:**
- Reduce perceived latency by 20-30%
- Overlap LLM generation with tool execution

---

#### 2.3 Implement Smart Caching Layer
**Current:** No caching of common queries or file reads  
**Proposed:** Cache frequently accessed data

**Implementation:**
- Cache Neo4j query results (with invalidation on file changes)
- Cache file contents with TTL
- Cache task classifications

**Expected Impact:**
- Repeated queries: 15s → 100ms (99% reduction)
- Only helps for repeated tasks

---

### Phase 3: Advanced Optimizations (Architectural)

#### 3.1 Predictive Tool Pre-fetching
**Current:** Reactive tool execution  
**Proposed:** Predict and pre-fetch likely needed data

**Implementation:**
- Analyze task type and pre-fetch common data
- For "modify file" tasks: pre-fetch file content + related files
- For "understand code" tasks: pre-fetch class hierarchy from Neo4j

**Expected Impact:**
- Eliminate 1-2 tool call round-trips
- Save 5-10 seconds per task

---

#### 3.2 Agent Warm Pool
**Current:** Agent created per request  
**Proposed:** Pool of pre-initialized agents

**Implementation:**
- Maintain 2-3 warm agent instances
- Pre-load tools and connections
- Rotate agents to handle concurrent requests

**Expected Impact:**
- Eliminate session creation overhead
- Save 500-1000ms per request

---

#### 3.3 Local LLM for Simple Tasks
**Current:** All tasks use OpenAI API  
**Proposed:** Route simple tasks to local Ollama

**Implementation:**
- Classify tasks by complexity
- Simple tasks (file reads, list operations) → Ollama (fast, local)
- Complex tasks (refactoring, analysis) → GPT-4/Claude (high quality)

**Expected Impact:**
- Simple tasks: 15s → 2-5s (67-87% reduction)
- No quality loss for simple operations

---

#### 3.4 Incremental Graph Updates
**Current:** Full graph rebuild on changes  
**Proposed:** Incremental updates for modified files

**Implementation:**
- Track file modifications
- Only re-parse and update changed files in Neo4j
- Maintain graph consistency with differential updates

**Expected Impact:**
- Graph updates: 30s → 1-5s (83-97% reduction)
- Faster iteration during development

---

## Recommended Implementation Priority

### Immediate (This Week)
1. **Switch to GPT-4.1-mini** - 5 min change, 70% latency reduction
2. **Increase tool cache TTL** - 2 min change, 5-10% improvement on subsequent calls

### Short-Term (Next Sprint)
3. **Enable parallel tool calls** - 1-2 days, 30-50% reduction
4. **Optimize MCP transport** - 2-3 days, 75% tool execution improvement

### Medium-Term (Next Month)
5. **Implement smart caching** - 3-5 days, 99% improvement for repeated queries
6. **Add response streaming optimization** - 2-3 days, 20-30% perceived latency improvement

### Long-Term (Future)
7. **Predictive pre-fetching** - 1 week, 30-50% improvement
8. **Agent warm pool** - 3-5 days, 10-20% improvement
9. **Local LLM routing** - 1 week, 67-87% for simple tasks
10. **Incremental graph updates** - 1-2 weeks, 83-97% graph update improvement

---

## Expected Results After Optimizations

### After Phase 1 (Quick Wins)
- Simple tasks: 15s → 2-3s (80-87% reduction)
- Complex tasks: 30s → 5-8s (73-83% reduction)

### After Phase 2 (Medium-Term)
- Simple tasks: 2-3s → 0.5-1s (67-83% additional reduction)
- Complex tasks: 5-8s → 2-4s (50-60% additional reduction)

### After Phase 3 (Advanced)
- Simple tasks: 0.5-1s → 0.2-0.5s (60-80% additional reduction)
- Complex tasks: 2-4s → 1-2s (50% additional reduction)

**Final Target:** 0.2-2s for most tasks (90-98% total improvement)

---

## Architecture-Specific Bottlenecks

### Current Flow
```
CLI → Orchestrator → Agent Repository (HTTP/SSE) → Agent API → LangGraph → LLM API
                                                                    ↓
                                                                MCP Tools (Neo4j, Filesystem)
```

### Latency by Component
1. **CLI → Agent API:** ~200ms (HTTP + Docker networking)
2. **Agent API → LangGraph:** ~10ms (session creation)
3. **LangGraph → LLM:** ~14,000ms (GPT-5 inference)
4. **LLM → Tool Call:** ~0ms (immediate)
5. **Tool Execution:** 1,500-2,300ms (MCP overhead)
6. **Tool Result → LLM:** ~7,000ms (second LLM call)
7. **Final Response:** ~10ms (stream finalization)

### Key Observations
- **LLM dominates everything:** 21s out of 15s total (multiple calls)
- **MCP overhead is acceptable:** 1.5-2.3s per tool call
- **Infrastructure is fast:** HTTP/DB/Docker add <250ms total
- **Agent loop is efficient:** LangGraph overhead is negligible

---

## Monitoring Recommendations

### Add Instrumentation
1. **OpenTelemetry spans** for each stage
2. **Prometheus metrics** for latency percentiles
3. **Structured logging** with timing data

### Key Metrics to Track
- LLM first token latency (p50, p95, p99)
- Tool execution time by tool type
- Total task completion time by task type
- Agent loop iterations per task
- Cache hit rates

### Alerting Thresholds
- LLM first token > 20s (critical)
- Tool execution > 5s (warning)
- Total task time > 60s (critical)
- Agent loop > 10 iterations (warning)

---

## Conclusion

The xCode system's latency is primarily driven by LLM API calls (98.6% of time). Switching from GPT-5 to a faster model like GPT-4.1-mini or Claude 3.5 Sonnet would provide immediate 70-80% latency reduction with minimal code changes.

Secondary optimizations around tool execution, caching, and parallel execution can further reduce latency by 50-70%, bringing total task time from 15s to under 2s for most operations.

The infrastructure (FastAPI, Docker, Neo4j, MCP) is well-optimized and not a significant bottleneck.
