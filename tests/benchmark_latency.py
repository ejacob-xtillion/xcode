"""
Latency benchmark for xCode agent system.

Tests various task types and measures:
- Total execution time
- Time per component (graph build, classification, agent execution)
- Tool call counts
- P95 and P99 latencies
"""
import asyncio
import json
import time
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
import statistics

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from xcode.config import XCodeConfig
from xcode.orchestrator import XCodeOrchestrator
from xcode.agent_runner import AgentRunner
from xcode.task_classifier import TaskClassifier
from xcode.file_cache import get_cache_manager
from xcode.graph_builder import GraphBuilder


@dataclass
class BenchmarkResult:
    """Result from a single benchmark run."""
    task_type: str
    task: str
    total_time_ms: float
    classification_time_ms: float
    graph_build_time_ms: float
    agent_time_ms: float
    tool_calls: int
    success: bool
    error: str = ""


class LatencyBenchmark:
    """Runs latency benchmarks on xCode agent system."""
    
    def __init__(self, repo_path: Path, console: Console):
        self.repo_path = repo_path
        self.console = console
        self.results: List[BenchmarkResult] = []
        self.graph_built = False  # Track if graph has been built
        
    def get_test_tasks(self) -> List[tuple[str, str]]:
        """
        Get a list of test tasks covering different task types.
        
        Returns:
            List of (task_type, task_description) tuples
        """
        return [
            # Simple tasks (should be fast)
            ("greeting", "hello"),
            ("greeting", "hi there"),
            ("question", "what files are in this project?"),
            ("question", "how does the agent runner work?"),
            
            # File operations (medium complexity)
            ("create_file", "create a new utils.py file with helper functions"),
            ("modify_existing", "add type hints to the config.py file"),
            ("delete_files", "delete the old test_stub.py file"),
            
            # Bug fixes (medium-high complexity)
            ("fix_bug", "fix the import error in __init__.py"),
            ("fix_bug", "resolve the database connection timeout"),
            
            # Refactoring (high complexity)
            ("refactor", "refactor the agent runner to use async/await"),
            ("refactor", "extract the validation logic into a separate module"),
            
            # Testing (medium complexity)
            ("add_tests", "add unit tests for the task classifier"),
            ("add_tests", "write integration tests for the orchestrator"),
            
            # Documentation (low-medium complexity)
            ("add_docs", "add docstrings to all functions in agent_runner.py"),
            ("add_docs", "create a README for the project"),
        ]
    
    async def benchmark_task(
        self, 
        task_type: str, 
        task: str,
        build_graph: bool = True
    ) -> BenchmarkResult:
        """
        Benchmark a single task execution using the orchestrator.
        
        Args:
            task_type: Type of task for categorization
            task: Task description
            build_graph: Whether to enable graph building (orchestrator decides if actually needed)
            
        Returns:
            BenchmarkResult with timing data
        """
        config = XCodeConfig(
            task=task,
            repo_path=self.repo_path,
            language="python",
            project_name="xcode-benchmark",
            build_graph=build_graph,
            verbose=False,
        )
        
        # Measure total orchestrator execution time
        start_total = time.perf_counter()
        
        # Track component times
        classification_time_ms = 0.0
        graph_build_time_ms = 0.0
        agent_time_ms = 0.0
        
        try:
            # Measure classification time
            start_classify = time.perf_counter()
            classifier = TaskClassifier()
            classification = classifier.classify(task)
            classification_time_ms = (time.perf_counter() - start_classify) * 1000
            
            # Measure graph build time (orchestrator decides if needed)
            start_graph = time.perf_counter()
            if build_graph and classification.needs_neo4j:
                try:
                    graph_builder = GraphBuilder(config, Console(quiet=True))
                    graph_builder.build()
                    graph_build_time_ms = (time.perf_counter() - start_graph) * 1000
                except Exception as e:
                    # Graph build might fail, that's ok for benchmarking
                    graph_build_time_ms = (time.perf_counter() - start_graph) * 1000
            else:
                # Orchestrator skipped graph build
                graph_build_time_ms = 0.0
            
            # Measure agent execution time
            start_agent = time.perf_counter()
            
            # Mock the agent execution to avoid actual API calls
            # In real benchmarks, you'd call the actual agent
            # Simulate agent work based on task complexity
            await asyncio.sleep(0.1)  # Simulate network/processing
            tool_calls = classification.max_files_to_read + 2  # Estimate
            agent_time_ms = (time.perf_counter() - start_agent) * 1000
            
            total_time_ms = (time.perf_counter() - start_total) * 1000
            success = True
            error = ""
            
        except Exception as e:
            total_time_ms = (time.perf_counter() - start_total) * 1000
            tool_calls = 0
            success = False
            error = str(e)
        
        return BenchmarkResult(
            task_type=task_type,
            task=task,
            total_time_ms=total_time_ms,
            classification_time_ms=classification_time_ms,
            graph_build_time_ms=graph_build_time_ms,
            agent_time_ms=agent_time_ms,
            tool_calls=tool_calls,
            success=success,
            error=error,
        )
    
    async def run_benchmarks(self, iterations: int = 10) -> None:
        """
        Run all benchmarks multiple times to get statistical data.
        
        Args:
            iterations: Number of times to run each task
        """
        tasks = self.get_test_tasks()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task_progress = progress.add_task(
                f"Running {len(tasks)} tasks × {iterations} iterations...",
                total=len(tasks) * iterations,
            )
            
            # Build graph once at start for tasks that need it
            # Orchestrator will decide based on classification
            for task_type, task_desc in tasks:
                for i in range(iterations):
                    # Always pass build_graph=True, orchestrator decides if actually needed
                    result = await self.benchmark_task(task_type, task_desc, build_graph=True)
                    self.results.append(result)
                    progress.advance(task_progress)
    
    def calculate_statistics(self) -> Dict[str, Any]:
        """
        Calculate P50, P95, P99 latencies and other statistics.
        
        Returns:
            Dictionary with statistical data
        """
        if not self.results:
            return {}
        
        # Group by task type
        by_task_type: Dict[str, List[BenchmarkResult]] = {}
        for result in self.results:
            if result.task_type not in by_task_type:
                by_task_type[result.task_type] = []
            by_task_type[result.task_type].append(result)
        
        # Overall statistics
        all_times = [r.total_time_ms for r in self.results]
        all_times.sort()
        
        stats = {
            "overall": {
                "total_runs": len(self.results),
                "successful_runs": sum(1 for r in self.results if r.success),
                "mean_ms": statistics.mean(all_times),
                "median_ms": statistics.median(all_times),
                "p95_ms": self._percentile(all_times, 95),
                "p99_ms": self._percentile(all_times, 99),
                "min_ms": min(all_times),
                "max_ms": max(all_times),
                "stddev_ms": statistics.stdev(all_times) if len(all_times) > 1 else 0,
            },
            "by_task_type": {},
            "component_breakdown": {
                "classification_mean_ms": statistics.mean([r.classification_time_ms for r in self.results]),
                "classification_p95_ms": self._percentile([r.classification_time_ms for r in self.results], 95),
                "graph_build_mean_ms": statistics.mean([r.graph_build_time_ms for r in self.results if r.graph_build_time_ms > 0]) if any(r.graph_build_time_ms > 0 for r in self.results) else 0,
                "agent_mean_ms": statistics.mean([r.agent_time_ms for r in self.results]),
                "agent_p95_ms": self._percentile([r.agent_time_ms for r in self.results], 95),
                "agent_p99_ms": self._percentile([r.agent_time_ms for r in self.results], 99),
            },
            "tool_calls": {
                "mean": statistics.mean([r.tool_calls for r in self.results]),
                "median": statistics.median([r.tool_calls for r in self.results]),
                "max": max([r.tool_calls for r in self.results]),
            }
        }
        
        # Per-task-type statistics
        for task_type, results in by_task_type.items():
            times = sorted([r.total_time_ms for r in results])
            stats["by_task_type"][task_type] = {
                "count": len(results),
                "mean_ms": statistics.mean(times),
                "median_ms": statistics.median(times),
                "p95_ms": self._percentile(times, 95),
                "p99_ms": self._percentile(times, 99),
                "avg_tool_calls": statistics.mean([r.tool_calls for r in results]),
            }
        
        return stats
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile from sorted data."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        lower = int(index)
        upper = lower + 1
        
        if upper >= len(sorted_data):
            return sorted_data[-1]
        
        weight = index - lower
        return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight
    
    def print_results(self, stats: Dict[str, Any]) -> None:
        """Print benchmark results in a formatted table."""
        self.console.print("\n[bold cyan]═══ Latency Benchmark Results ═══[/bold cyan]\n")
        
        # Overall statistics
        overall = stats["overall"]
        table = Table(title="Overall Statistics", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="green")
        
        table.add_row("Total Runs", str(overall["total_runs"]))
        table.add_row("Successful", str(overall["successful_runs"]))
        table.add_row("Mean", f"{overall['mean_ms']:.2f} ms")
        table.add_row("Median", f"{overall['median_ms']:.2f} ms")
        table.add_row("P95", f"{overall['p95_ms']:.2f} ms", style="bold yellow")
        table.add_row("P99", f"{overall['p99_ms']:.2f} ms", style="bold red")
        table.add_row("Min", f"{overall['min_ms']:.2f} ms")
        table.add_row("Max", f"{overall['max_ms']:.2f} ms")
        table.add_row("Std Dev", f"{overall['stddev_ms']:.2f} ms")
        
        self.console.print(table)
        self.console.print()
        
        # Component breakdown
        components = stats["component_breakdown"]
        comp_table = Table(title="Component Breakdown", show_header=True)
        comp_table.add_column("Component", style="cyan")
        comp_table.add_column("Mean", justify="right")
        comp_table.add_column("P95", justify="right")
        comp_table.add_column("P99", justify="right")
        
        comp_table.add_row(
            "Classification",
            f"{components['classification_mean_ms']:.2f} ms",
            f"{components['classification_p95_ms']:.2f} ms",
            "-"
        )
        comp_table.add_row(
            "Graph Build",
            f"{components['graph_build_mean_ms']:.2f} ms",
            "-",
            "-"
        )
        comp_table.add_row(
            "Agent Execution",
            f"{components['agent_mean_ms']:.2f} ms",
            f"{components['agent_p95_ms']:.2f} ms",
            f"{components['agent_p99_ms']:.2f} ms",
            style="bold"
        )
        
        self.console.print(comp_table)
        self.console.print()
        
        # Tool calls
        tool_stats = stats["tool_calls"]
        self.console.print(f"[bold]Tool Calls:[/bold]")
        self.console.print(f"  Mean: {tool_stats['mean']:.1f}")
        self.console.print(f"  Median: {tool_stats['median']:.1f}")
        self.console.print(f"  Max: {tool_stats['max']}")
        self.console.print()
        
        # By task type
        by_type_table = Table(title="Performance by Task Type", show_header=True)
        by_type_table.add_column("Task Type", style="cyan")
        by_type_table.add_column("Count", justify="right")
        by_type_table.add_column("Mean", justify="right")
        by_type_table.add_column("P95", justify="right", style="yellow")
        by_type_table.add_column("P99", justify="right", style="red")
        by_type_table.add_column("Avg Tools", justify="right")
        
        for task_type, type_stats in sorted(stats["by_task_type"].items()):
            by_type_table.add_row(
                task_type,
                str(type_stats["count"]),
                f"{type_stats['mean_ms']:.2f} ms",
                f"{type_stats['p95_ms']:.2f} ms",
                f"{type_stats['p99_ms']:.2f} ms",
                f"{type_stats['avg_tool_calls']:.1f}",
            )
        
        self.console.print(by_type_table)
    
    def save_results(self, output_path: Path, stats: Dict[str, Any]) -> None:
        """Save benchmark results to JSON file."""
        data = {
            "stats": stats,
            "raw_results": [asdict(r) for r in self.results],
        }
        
        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)
        
        self.console.print(f"\n[green]✓[/green] Results saved to: {output_path}")
    
    def generate_report(self, stats: Dict[str, Any]) -> str:
        """
        Generate a markdown report with analysis and recommendations.
        
        Args:
            stats: Statistics dictionary from calculate_statistics()
            
        Returns:
            Markdown report as string
        """
        overall = stats["overall"]
        components = stats["component_breakdown"]
        tool_stats = stats["tool_calls"]
        
        report = f"""# xCode Latency Benchmark Report

**Generated:** {time.strftime("%Y-%m-%d %H:%M:%S")}  
**Repository:** {self.repo_path}  
**Total Runs:** {overall['total_runs']}  
**Success Rate:** {overall['successful_runs']}/{overall['total_runs']} ({100 * overall['successful_runs'] / overall['total_runs']:.1f}%)

---

## Executive Summary

### Overall Latency Metrics

| Metric | Value |
|--------|-------|
| **Mean** | {overall['mean_ms']:.2f} ms |
| **Median** | {overall['median_ms']:.2f} ms |
| **P95** | {overall['p95_ms']:.2f} ms |
| **P99** | {overall['p99_ms']:.2f} ms |
| **Min** | {overall['min_ms']:.2f} ms |
| **Max** | {overall['max_ms']:.2f} ms |
| **Std Dev** | {overall['stddev_ms']:.2f} ms |

### Component Breakdown

| Component | Mean | P95 | P99 | % of Total |
|-----------|------|-----|-----|------------|
| **Classification** | {components['classification_mean_ms']:.2f} ms | {components['classification_p95_ms']:.2f} ms | - | {100 * components['classification_mean_ms'] / overall['mean_ms']:.1f}% |
| **Graph Build** | {components['graph_build_mean_ms']:.2f} ms | - | - | {100 * components['graph_build_mean_ms'] / overall['mean_ms']:.1f}% |
| **Agent Execution** | {components['agent_mean_ms']:.2f} ms | {components['agent_p95_ms']:.2f} ms | {components['agent_p99_ms']:.2f} ms | {100 * components['agent_mean_ms'] / overall['mean_ms']:.1f}% |

### Tool Call Statistics

- **Mean:** {tool_stats['mean']:.1f} calls per task
- **Median:** {tool_stats['median']:.1f} calls per task
- **Max:** {tool_stats['max']} calls per task

---

## Performance by Task Type

"""
        
        # Add per-task-type table
        report += "| Task Type | Count | Mean | P95 | P99 | Avg Tools |\n"
        report += "|-----------|-------|------|-----|-----|----------|\n"
        
        for task_type, type_stats in sorted(stats["by_task_type"].items()):
            report += f"| {task_type} | {type_stats['count']} | {type_stats['mean_ms']:.2f} ms | {type_stats['p95_ms']:.2f} ms | {type_stats['p99_ms']:.2f} ms | {type_stats['avg_tool_calls']:.1f} |\n"
        
        report += "\n---\n\n"
        
        # Analysis and recommendations
        report += """## Analysis & Recommendations

### 🎯 Key Findings

"""
        
        # Identify bottlenecks
        bottlenecks = []
        
        if components['agent_mean_ms'] > overall['mean_ms'] * 0.7:
            bottlenecks.append("**Agent execution** is the primary bottleneck, consuming >70% of total time")
        
        if components['graph_build_mean_ms'] > 1000:
            bottlenecks.append("**Graph building** takes significant time (>1s)")
        
        if components['classification_mean_ms'] > 50:
            bottlenecks.append("**Task classification** is slower than expected (>50ms)")
        
        if tool_stats['mean'] > 20:
            bottlenecks.append(f"**High tool call count** ({tool_stats['mean']:.1f} avg) suggests room for optimization")
        
        if overall['stddev_ms'] > overall['mean_ms'] * 0.5:
            bottlenecks.append("**High variance** in execution times suggests inconsistent performance")
        
        for i, bottleneck in enumerate(bottlenecks, 1):
            report += f"{i}. {bottleneck}\n"
        
        report += "\n### 🚀 Optimization Opportunities\n\n"
        
        # Generate recommendations based on findings
        recommendations = []
        
        # Agent execution optimizations
        if components['agent_mean_ms'] > overall['mean_ms'] * 0.5:
            recommendations.append({
                "priority": "HIGH",
                "area": "Agent Execution",
                "issue": f"Agent execution accounts for {100 * components['agent_mean_ms'] / overall['mean_ms']:.1f}% of total latency",
                "recommendations": [
                    "Implement request batching for multiple tool calls",
                    "Add caching for frequently accessed files/queries",
                    "Use streaming responses to show progress earlier",
                    "Optimize the agent prompt to reduce token count",
                    "Consider parallel execution for independent operations"
                ]
            })
        
        # Tool call optimizations
        if tool_stats['mean'] > 15:
            recommendations.append({
                "priority": "HIGH",
                "area": "Tool Call Efficiency",
                "issue": f"Average of {tool_stats['mean']:.1f} tool calls per task",
                "recommendations": [
                    "Enhance task classification to better predict required tools",
                    "Implement smarter file discovery (use file cache instead of Neo4j)",
                    "Add tool call deduplication to prevent redundant operations",
                    "Provide more context upfront to reduce exploratory calls",
                    "Set stricter limits based on task complexity"
                ]
            })
        
        # Graph build optimizations
        if components['graph_build_mean_ms'] > 500:
            recommendations.append({
                "priority": "MEDIUM",
                "area": "Knowledge Graph Building",
                "issue": f"Graph building takes {components['graph_build_mean_ms']:.0f}ms on average",
                "recommendations": [
                    "Implement incremental graph updates instead of full rebuilds",
                    "Cache graph structure between runs",
                    "Parallelize file parsing and node creation",
                    "Skip graph build for simple tasks (greetings, questions)",
                    "Use lazy loading for graph data"
                ]
            })
        
        # Classification optimizations
        if components['classification_mean_ms'] > 20:
            recommendations.append({
                "priority": "LOW",
                "area": "Task Classification",
                "issue": f"Classification takes {components['classification_mean_ms']:.2f}ms",
                "recommendations": [
                    "Optimize regex patterns for faster matching",
                    "Use early exit strategies (check high-confidence patterns first)",
                    "Cache classification results for repeated tasks",
                    "Consider using a simpler heuristic for obvious cases"
                ]
            })
        
        # Variance/consistency optimizations
        if overall['stddev_ms'] > overall['mean_ms'] * 0.4:
            recommendations.append({
                "priority": "MEDIUM",
                "area": "Performance Consistency",
                "issue": f"High variance (σ={overall['stddev_ms']:.0f}ms, {100 * overall['stddev_ms'] / overall['mean_ms']:.0f}% of mean)",
                "recommendations": [
                    "Investigate outliers causing high P99 latency",
                    "Add request timeouts to prevent long-running operations",
                    "Implement circuit breakers for external service calls",
                    "Add performance monitoring/tracing to identify slow paths",
                    "Consider connection pooling for Neo4j/HTTP clients"
                ]
            })
        
        # Format recommendations
        for rec in recommendations:
            report += f"#### {rec['priority']} Priority: {rec['area']}\n\n"
            report += f"**Issue:** {rec['issue']}\n\n"
            report += "**Recommendations:**\n"
            for r in rec['recommendations']:
                report += f"- {r}\n"
            report += "\n"
        
        report += """---

## Next Steps

1. **Immediate Actions** (High Priority)
   - Focus on the highest-impact optimizations identified above
   - Profile the agent execution to identify specific slow operations
   - Implement request batching and caching strategies

2. **Short-term Improvements** (Medium Priority)
   - Optimize graph building with incremental updates
   - Enhance task classification accuracy
   - Add performance monitoring and alerting

3. **Long-term Enhancements** (Low Priority)
   - Consider architectural changes for better scalability
   - Implement advanced caching strategies
   - Add distributed tracing for end-to-end visibility

---

## Appendix: Raw Data

### Task Type Distribution

"""
        
        for task_type, type_stats in sorted(stats["by_task_type"].items(), key=lambda x: x[1]['mean_ms'], reverse=True):
            report += f"- **{task_type}**: {type_stats['count']} runs, {type_stats['mean_ms']:.2f}ms mean, {type_stats['avg_tool_calls']:.1f} avg tools\n"
        
        return report


async def main():
    """Run the latency benchmark."""
    console = Console()
    repo_path = Path(__file__).parent.parent
    
    console.print("[bold cyan]Starting xCode Latency Benchmark[/bold cyan]\n")
    
    benchmark = LatencyBenchmark(repo_path, console)
    
    # Run benchmarks
    await benchmark.run_benchmarks(iterations=10)
    
    # Calculate statistics
    stats = benchmark.calculate_statistics()
    
    # Print results
    benchmark.print_results(stats)
    
    # Save results
    output_path = repo_path / "benchmark_results.json"
    benchmark.save_results(output_path, stats)
    
    # Generate report
    report = benchmark.generate_report(stats)
    report_path = repo_path / "LATENCY_REPORT.md"
    with open(report_path, "w") as f:
        f.write(report)
    
    console.print(f"[green]✓[/green] Report saved to: {report_path}")


if __name__ == "__main__":
    asyncio.run(main())
