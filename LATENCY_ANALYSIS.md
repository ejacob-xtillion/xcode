# xCode Latency Analysis & Improvement Plan

**Generated:** 2026-03-17 00:37:26  
**Repository:** /Users/elijahgjacob/xcode  
**Benchmark:** 150 runs across 9 task types (10 iterations each)

---

## 📊 Executive Summary

### Critical Findings

🔴 **P95 Latency: 7.26 seconds** - Unacceptably high for interactive use  
🔴 **P99 Latency: 7.75 seconds** - Worst-case scenarios take >7s  
🟡 **Median Latency: 101ms** - Fast path is good, but inconsistent  
🟢 **Classification: 0.16ms** - Task classification is highly optimized  

### The Problem: Bimodal Distribution

The data reveals a **bimodal performance pattern**:
- **Fast path (90% of runs)**: ~101ms (excellent)
- **Slow path (10% of runs)**: 7-11 seconds (critical issue)

The slow path is dominated by **graph building** which takes **7.48 seconds on average** - accounting for 880% of mean latency (indicating it only runs on some iterations).

---

## 🎯 Key Metrics

### Overall Latency

| Metric | Value | Assessment |
|--------|-------|------------|
| **Mean** | 849.46 ms | ⚠️ Skewed by graph builds |
| **Median** | 101.35 ms | ✅ Good for cached runs |
| **P95** | 7264.07 ms | 🔴 Critical - too slow |
| **P99** | 7745.21 ms | 🔴 Critical - too slow |
| **Min** | 100.34 ms | ✅ Excellent baseline |
| **Max** | 11056.88 ms | 🔴 Worst case >11s |
| **Std Dev** | 2272.31 ms | 🔴 High variance (267% of mean) |

### Component Breakdown

| Component | Mean | P95 | P99 | % of Total | Assessment |
|-----------|------|-----|-----|------------|------------|
| **Classification** | 0.16 ms | 0.28 ms | - | 0.02% | ✅ Excellent |
| **Graph Build** | 7481.36 ms | - | - | 880.7% | 🔴 **PRIMARY BOTTLENECK** |
| **Agent Execution** | 101.17 ms | 101.42 ms | 101.79 ms | 11.9% | ✅ Good |

### Tool Call Statistics

- **Mean:** 13.3 calls per task
- **Median:** 17.0 calls per task  
- **Max:** 32 calls per task
- **Assessment:** ⚠️ Moderate - room for optimization

---

## 📈 Performance by Task Type

| Task Type | Count | Mean | P95 | P99 | Avg Tools | Notes |
|-----------|-------|------|-----|-----|-----------|-------|
| **greeting** | 20 | 1017.73 ms | 7650.08 ms | 10375.52 ms | 2.0 | 🔴 Slowest despite simplicity |
| **delete_files** | 10 | 869.97 ms | 4329.34 ms | 7096.77 ms | 2.0 | ⚠️ Should be instant |
| **fix_bug** | 20 | 833.36 ms | 7173.65 ms | 7594.75 ms | 17.0 | ⚠️ High tool usage |
| **refactor** | 20 | 832.28 ms | 7258.66 ms | 7516.78 ms | 24.5 | 🔴 Highest tool usage |
| **add_docs** | 20 | 825.68 ms | 7120.88 ms | 7498.57 ms | 14.5 | ⚠️ Moderate |
| **question** | 20 | 821.12 ms | 7284.00 ms | 7308.55 ms | 7.0 | ✅ Good tool efficiency |
| **create_file** | 10 | 813.23 ms | 4016.36 ms | 6578.59 ms | 17.0 | ⚠️ High tool usage |
| **modify_existing** | 10 | 808.07 ms | 3988.85 ms | 6533.23 ms | 17.0 | ⚠️ High tool usage |
| **add_tests** | 20 | 795.18 ms | 7003.56 ms | 7065.53 ms | 17.0 | ⚠️ High tool usage |

### Key Observations

1. **Greetings are slowest** - Simple tasks like "hello" shouldn't trigger graph builds or take >1s
2. **Refactoring uses most tools** - 24.5 avg tool calls suggests inefficient exploration
3. **Delete operations are slow** - Should be near-instant but take 870ms average
4. **P95/P99 are consistently high** - All task types suffer from the graph build penalty

---

## 🚨 Critical Issues Identified

### Issue #1: Graph Building Dominates Latency (CRITICAL)

**Impact:** 7.48 seconds average, 880% of total mean latency  
**Frequency:** Appears to run on first iteration of each task type  
**Root Cause:** Full graph rebuild for every new project/task context

**Evidence:**
- Graph build: 7481ms vs Agent execution: 101ms (74x slower)
- Median is 101ms (no graph build) vs P95 is 7264ms (with graph build)
- The 880% ratio indicates graph builds only happen on ~10% of runs (first iteration)

**Why This Matters:**
- Users experience 7+ second delays on cold starts
- Interactive sessions feel sluggish on first command
- Simple tasks (greetings, questions) shouldn't need graph builds

### Issue #2: High Variance / Inconsistent Performance (HIGH)

**Impact:** Std dev of 2272ms (267% of mean)  
**Root Cause:** Bimodal distribution (fast cached vs slow graph build)

**Evidence:**
- Min: 100ms, Max: 11056ms (110x difference)
- Median: 101ms, Mean: 849ms (8.4x difference)
- P99: 7745ms vs Median: 101ms (76x difference)

**Why This Matters:**
- Unpredictable user experience
- Cannot reliably estimate task completion time
- Some users will experience consistently poor performance

### Issue #3: Simple Tasks Trigger Full Pipeline (MEDIUM)

**Impact:** Greetings take 1017ms average, 10375ms P99  
**Root Cause:** All tasks go through full orchestration (graph + agent)

**Evidence:**
- "hello" triggers graph build (7.5s) + agent (100ms)
- Delete operations use 2 tool calls but take 870ms
- Questions use 7 tool calls but take 821ms

**Why This Matters:**
- Poor first impression for new users
- Wastes resources on trivial tasks
- Classification exists but isn't preventing graph builds

### Issue #4: Tool Call Inefficiency (MEDIUM)

**Impact:** 13.3 avg, 32 max tool calls per task  
**Root Cause:** Exploratory behavior, redundant queries

**Evidence:**
- Refactoring: 24.5 avg tool calls
- Most file operations: 17 tool calls
- Even greetings: 2 tool calls (should be 0)

**Why This Matters:**
- Each tool call adds latency (network, processing)
- Increases API costs for la-factoria
- Suggests agent is exploring rather than executing directly

---

## 🔧 Detailed Improvement Recommendations

### Priority 1: Eliminate Graph Build Penalty (CRITICAL)

**Goal:** Reduce P95 from 7264ms to <500ms

#### 1.1 Skip Graph Build for Simple Tasks
```python
# In orchestrator.py
def run(self) -> XCodeResult:
    # Use classification to skip graph build
    if self.task_classification and not self.task_classification.needs_neo4j:
        self.console.print("[dim]Skipping graph build (not needed for this task)[/dim]")
    elif self.config.build_graph:
        self._ensure_knowledge_graph()
```

**Expected Impact:**
- Greetings: 1017ms → 101ms (90% reduction)
- Questions: 821ms → 101ms (88% reduction)
- Delete operations: 870ms → 101ms (88% reduction)
- **Overall P95: 7264ms → ~500ms (93% reduction)**

#### 1.2 Implement Persistent Graph Cache
```python
# Cache graph in SQLite or file system
# Only rebuild when files change (use mtime tracking)
class GraphCache:
    def get_or_build(self, project: str, repo_path: Path) -> Graph:
        cache_file = Path.home() / ".xcode" / "graphs" / f"{project}.db"
        if cache_file.exists() and not self._needs_rebuild(repo_path):
            return self._load_from_cache(cache_file)
        return self._build_and_cache(repo_path, cache_file)
```

**Expected Impact:**
- First run: 7481ms (unchanged)
- Subsequent runs: 7481ms → 50ms (99% reduction)
- **Overall mean: 849ms → 150ms (82% reduction)**

#### 1.3 Incremental Graph Updates
```python
# Only re-parse changed files
def incremental_update(self, changed_files: List[Path]):
    for file in changed_files:
        self._remove_file_nodes(file)
        self._parse_and_add_file(file)
```

**Expected Impact:**
- Updates: 7481ms → 200ms (97% reduction)
- Reduces cache invalidation frequency

### Priority 2: Optimize Tool Call Efficiency (HIGH)

**Goal:** Reduce avg tool calls from 13.3 to <8

#### 2.1 Provide More Context Upfront
```python
# In agent_runner.py _build_agent_query
# Include file tree in initial prompt for file operations
if self.task_classification.task_type in [CREATE_NEW_FILE, MODIFY_EXISTING]:
    file_tree = self._get_file_cache().get_tree_view()
    query_parts.append(f"Available files:\n{file_tree}")
```

**Expected Impact:**
- Reduces exploratory "list files" calls
- File operations: 17 → 10 tool calls (41% reduction)
- **Overall mean: 13.3 → 9.5 tool calls (29% reduction)**

#### 2.2 Implement Tool Call Batching
```python
# Allow agent to request multiple files in one call
# Instead of: read(file1), read(file2), read(file3)
# Use: read_multiple([file1, file2, file3])
```

**Expected Impact:**
- Reduces network round-trips
- Refactoring: 24.5 → 15 tool calls (39% reduction)

#### 2.3 Add Smart File Suggestions
```python
# Based on task classification, suggest likely files
if classification.task_type == FIX_BUG and "import" in task.lower():
    suggestions = ["__init__.py", "setup.py", "requirements.txt"]
```

**Expected Impact:**
- Reduces "find file" exploration
- Bug fixes: 17 → 12 tool calls (29% reduction)

### Priority 3: Reduce Variance (MEDIUM)

**Goal:** Reduce std dev from 2272ms to <500ms

#### 3.1 Implement Request Timeouts
```python
# In agent_runner.py
async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
    response = await client.post(...)
```

**Expected Impact:**
- Prevents hanging requests
- Caps max latency at timeout value
- **Max: 11056ms → 30000ms (controlled ceiling)**

#### 3.2 Add Connection Pooling
```python
# Reuse Neo4j connections
from neo4j import GraphDatabase

class GraphCache:
    def __init__(self):
        self.driver = GraphDatabase.driver(uri, auth=auth)
    
    def query(self, cypher: str):
        with self.driver.session() as session:
            return session.run(cypher)
```

**Expected Impact:**
- Reduces connection overhead
- More consistent query times
- **Std dev: 2272ms → 1500ms (34% reduction)**

#### 3.3 Implement Circuit Breaker
```python
# Skip graph queries if Neo4j is slow/unavailable
class CircuitBreaker:
    def __init__(self, threshold_ms: float = 1000):
        self.failures = 0
        self.threshold = threshold_ms
    
    def should_skip(self) -> bool:
        return self.failures > 3
```

**Expected Impact:**
- Graceful degradation when Neo4j is slow
- Prevents cascading failures

### Priority 4: Optimize Agent Execution (LOW)

**Goal:** Reduce agent execution from 101ms to <80ms

#### 4.1 Optimize Prompt Size
- Current prompts may be verbose
- Reduce token count by 20-30%
- Use more concise instructions

**Expected Impact:**
- Agent: 101ms → 80ms (21% reduction)
- Reduces API costs

#### 4.2 Use Streaming for Faster Perceived Performance
```python
# Already implemented, but ensure it's used everywhere
async for chunk in response.aiter_text():
    self.console.print(chunk, end="")
```

**Expected Impact:**
- No latency reduction, but better UX
- Users see progress immediately

---

## 🎯 Recommended Implementation Order

### Phase 1: Quick Wins (1-2 days)

1. **Skip graph build for simple tasks** ✅ Already have classification
   - Modify `orchestrator.py` to check `needs_neo4j` flag
   - **Impact:** P95: 7264ms → 500ms (93% reduction)
   - **Effort:** 1 hour

2. **Add request timeouts**
   - Set 30s timeout on all HTTP calls
   - **Impact:** Caps max latency, prevents hangs
   - **Effort:** 30 minutes

3. **Provide file tree in initial prompt**
   - Use existing file cache
   - **Impact:** Tool calls: 13.3 → 10 (25% reduction)
   - **Effort:** 2 hours

### Phase 2: Medium-term Improvements (3-5 days)

4. **Implement persistent graph cache**
   - Use SQLite or pickle to cache graph
   - Track file mtimes for invalidation
   - **Impact:** Mean: 849ms → 150ms (82% reduction)
   - **Effort:** 1 day

5. **Add connection pooling for Neo4j**
   - Reuse connections across queries
   - **Impact:** Std dev: 2272ms → 1500ms (34% reduction)
   - **Effort:** 4 hours

6. **Implement tool call batching**
   - Add `read_multiple_files` tool to la-factoria
   - **Impact:** Tool calls: 13.3 → 9 (32% reduction)
   - **Effort:** 1 day

### Phase 3: Long-term Optimizations (1-2 weeks)

7. **Incremental graph updates**
   - Only re-parse changed files
   - **Impact:** Updates: 7481ms → 200ms (97% reduction)
   - **Effort:** 3 days

8. **Implement circuit breaker**
   - Graceful degradation when services are slow
   - **Impact:** Improved reliability
   - **Effort:** 1 day

9. **Add performance monitoring/tracing**
   - OpenTelemetry integration
   - Identify slow paths in production
   - **Impact:** Visibility for future optimizations
   - **Effort:** 2 days

---

## 📊 Projected Impact

### After Phase 1 (Quick Wins)

| Metric | Current | After Phase 1 | Improvement |
|--------|---------|---------------|-------------|
| **P95** | 7264 ms | 500 ms | 93% ↓ |
| **P99** | 7745 ms | 800 ms | 90% ↓ |
| **Mean** | 849 ms | 200 ms | 76% ↓ |
| **Tool Calls** | 13.3 | 10.0 | 25% ↓ |

### After Phase 2 (Medium-term)

| Metric | Current | After Phase 2 | Improvement |
|--------|---------|---------------|-------------|
| **P95** | 7264 ms | 300 ms | 96% ↓ |
| **P99** | 7745 ms | 500 ms | 94% ↓ |
| **Mean** | 849 ms | 120 ms | 86% ↓ |
| **Std Dev** | 2272 ms | 150 ms | 93% ↓ |
| **Tool Calls** | 13.3 | 8.5 | 36% ↓ |

### After Phase 3 (Long-term)

| Metric | Current | After Phase 3 | Improvement |
|--------|---------|---------------|-------------|
| **P95** | 7264 ms | 200 ms | 97% ↓ |
| **P99** | 7745 ms | 300 ms | 96% ↓ |
| **Mean** | 849 ms | 90 ms | 89% ↓ |
| **Std Dev** | 2272 ms | 50 ms | 98% ↓ |

---

## 🔍 Deep Dive: Task Type Analysis

### Greetings (CRITICAL ISSUE)

**Current:** 1017ms mean, 10375ms P99  
**Expected:** <50ms (no computation needed)  
**Problem:** Triggering full pipeline for trivial tasks

**Root Cause:**
```python
# orchestrator.py currently always builds graph
if self.config.build_graph:
    self._ensure_knowledge_graph()  # 7.5s penalty
```

**Fix:**
```python
# Check if task needs graph
if self.config.build_graph and self.task_classification.needs_neo4j:
    self._ensure_knowledge_graph()
```

**Impact:** Greetings: 1017ms → 101ms (90% reduction)

### Refactoring (HIGH TOOL USAGE)

**Current:** 24.5 avg tool calls  
**Expected:** <15 tool calls  
**Problem:** Too much exploration, not enough direct action

**Root Cause:**
- Agent doesn't know file structure upfront
- Makes multiple "find file" queries
- Reads files incrementally instead of in batch

**Fix:**
1. Provide file tree in initial prompt
2. Suggest likely files based on task keywords
3. Enable batch file reading

**Impact:** Refactoring: 24.5 → 15 tool calls (39% reduction)

### Delete Operations (UNEXPECTED SLOWNESS)

**Current:** 870ms mean, only 2 tool calls  
**Expected:** <100ms  
**Problem:** Graph build overhead for simple operation

**Root Cause:**
- Classification correctly identifies as simple (2 tool calls)
- But orchestrator still builds graph
- No fast path for destructive operations

**Fix:**
```python
# Skip graph for delete operations
if classification.task_type == TaskType.DELETE_FILES:
    config.build_graph = False
```

**Impact:** Delete: 870ms → 101ms (88% reduction)

---

## 💡 Additional Optimization Ideas

### 1. Lazy Graph Loading
Instead of building entire graph upfront, load on-demand:
- Parse only requested files
- Build relationships as needed
- Cache parsed results

**Benefit:** Eliminates upfront cost, spreads work across execution

### 2. Pre-warm Cache
Run graph build in background on startup:
```bash
xcode --warmup  # Builds graph, exits
```

**Benefit:** First interactive command is fast

### 3. Parallel Graph Building
Use multiprocessing to parse files in parallel:
```python
from multiprocessing import Pool
with Pool(cpu_count()) as pool:
    results = pool.map(parse_file, files)
```

**Benefit:** Graph build: 7481ms → 2000ms (73% reduction)

### 4. Smart File Discovery
Use file cache + heuristics instead of Neo4j:
```python
def find_files_for_task(task: str, classification: TaskClassification):
    # Extract keywords from task
    keywords = extract_keywords(task)
    # Search file cache by name/path
    return file_cache.search(keywords)
```

**Benefit:** Eliminates Neo4j dependency for most tasks

### 5. Response Caching
Cache agent responses for identical tasks:
```python
cache_key = hash(task + repo_state)
if cache_key in response_cache:
    return response_cache[cache_key]
```

**Benefit:** Repeated tasks: 849ms → <10ms (99% reduction)

---

## 📋 Action Items

### Immediate (This Week)

- [ ] **Modify orchestrator to skip graph build when `needs_neo4j=False`**
  - File: `xcode/orchestrator.py`
  - Lines: 33-36
  - Expected: P95 reduction from 7264ms → 500ms

- [ ] **Add HTTP timeouts to agent runner**
  - File: `xcode/agent_runner.py`
  - Add: `httpx.Timeout(30.0)` to all requests
  - Expected: Caps max latency at 30s

- [ ] **Include file tree in agent prompt for file operations**
  - File: `xcode/agent_runner.py`
  - Method: `_build_agent_query`
  - Expected: Tool calls 13.3 → 10

### Short-term (Next 2 Weeks)

- [ ] **Implement persistent graph cache with SQLite**
  - New file: `xcode/graph_cache.py`
  - Track file mtimes for invalidation
  - Expected: Mean 849ms → 150ms

- [ ] **Add Neo4j connection pooling**
  - File: `xcode/graph_builder.py`
  - Use singleton driver instance
  - Expected: Std dev 2272ms → 1500ms

- [ ] **Add batch file reading to la-factoria**
  - External: la-factoria API
  - Add `read_multiple_files` tool
  - Expected: Tool calls 13.3 → 9

### Long-term (Next Month)

- [ ] **Implement incremental graph updates**
  - Track file changes via git/watchdog
  - Only re-parse modified files
  - Expected: Updates 7481ms → 200ms

- [ ] **Add performance monitoring**
  - OpenTelemetry integration
  - Track all component timings
  - Set up alerting for P95 > 1s

- [ ] **Parallel graph building**
  - Use multiprocessing for file parsing
  - Expected: Graph build 7481ms → 2000ms

---

## 🧪 Testing Strategy

### Regression Tests
After each optimization, verify:
1. All 110 existing tests still pass
2. P95 latency improves as expected
3. No functionality is broken

### Performance Tests
Add benchmarks to CI/CD:
```python
# tests/test_performance.py
def test_greeting_latency():
    """Greetings should complete in <200ms."""
    result = run_task("hello")
    assert result.total_time_ms < 200

def test_p95_latency():
    """P95 should be <500ms after optimizations."""
    results = [run_task(task) for task in test_tasks]
    p95 = calculate_p95([r.total_time_ms for r in results])
    assert p95 < 500
```

### Load Tests
Test under realistic conditions:
- 100 concurrent users
- Mix of task types
- Measure throughput and latency under load

---

## 📈 Success Metrics

### Target Metrics (After All Optimizations)

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| **P50** | 101 ms | 90 ms | 11% ↓ |
| **P95** | 7264 ms | 200 ms | 97% ↓ |
| **P99** | 7745 ms | 300 ms | 96% ↓ |
| **Mean** | 849 ms | 90 ms | 89% ↓ |
| **Std Dev** | 2272 ms | 50 ms | 98% ↓ |
| **Tool Calls** | 13.3 | 6.0 | 55% ↓ |

### User Experience Goals

- ✅ Greetings respond instantly (<100ms)
- ✅ Simple tasks complete in <200ms
- ✅ Complex tasks complete in <1s (P95)
- ✅ Worst case <2s (P99)
- ✅ Consistent performance (low variance)

---

## 🔗 Related Files

- **Benchmark Script:** `tests/benchmark_latency.py`
- **Raw Results:** `benchmark_results.json`
- **Original Report:** `LATENCY_REPORT.md`

---

## 📝 Conclusion

The xCode agent system has **excellent baseline performance** (101ms median) but suffers from **severe P95/P99 latency issues** due to graph building overhead. The good news is that:

1. **The fast path is already optimized** - 101ms is excellent
2. **The slow path is well-understood** - graph building is the clear bottleneck
3. **Fixes are straightforward** - skip graph when not needed, cache when needed
4. **High impact potential** - 93-97% reduction in P95/P99 is achievable

**Recommended First Step:** Implement the "skip graph build for simple tasks" optimization. This single change will reduce P95 by 93% and dramatically improve user experience for the most common use cases.
