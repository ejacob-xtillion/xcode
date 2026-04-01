"""
Interleave LangGraph astream_events with shell stdout/stderr queue chunks for SSE.
"""

from __future__ import annotations

import asyncio
import queue
from datetime import datetime, timezone

from app.api.agents.models import ToolCallEvent, ToolOutputChunkEvent, ToolResultEvent
from app.engine.stream_processor import AgentStreamProcessor


async def iter_graph_events(agent, input_data, config: dict, processor: AgentStreamProcessor):
    """Yield typed stream events from LangGraph astream_events (no shell queue)."""
    async for raw_event in agent.astream_events(input_data, config=config):
        for ev in processor.process_event(raw_event):
            yield ev


def is_shell_tool_name(tool: str) -> bool:
    leaf = (tool or "").split(".")[-1]
    return leaf in ("run_shell_command", "run_shell", "execute_command")


async def _queue_get_timeout(q: queue.Queue, timeout: float):
    loop = asyncio.get_running_loop()

    def _get():
        try:
            return q.get(timeout=timeout)
        except queue.Empty:
            return None

    return await loop.run_in_executor(None, _get)


async def multiplex_astream_with_shell_queue(
    agent,
    input_data,
    config: dict,
    shell_q: queue.Queue | None,
    processor: AgentStreamProcessor,
):
    """
    Yield StreamEvent instances from the graph, plus ToolOutputChunkEvent from shell_q
    while a shell command is running.
    """
    active_shell_tool_call_id = ""
    agen = agent.astream_events(input_data, config=config).__aiter__()
    graph_task = asyncio.create_task(agen.__anext__())

    try:
        while True:
            shell_task = None
            if shell_q is not None:
                shell_task = asyncio.create_task(_queue_get_timeout(shell_q, 0.05))
            wait_set = {graph_task}
            if shell_task is not None:
                wait_set.add(shell_task)

            done, _ = await asyncio.wait(wait_set, return_when=asyncio.FIRST_COMPLETED)

            if shell_task is not None:
                if shell_task in done:
                    try:
                        item = shell_task.result()
                    except Exception:
                        item = None
                    if item is not None:
                        stream_name, text = item
                        if stream_name not in ("stdout", "stderr"):
                            stream_name = "stdout"
                        yield ToolOutputChunkEvent(
                            role="tool",
                            tool_call_id=active_shell_tool_call_id,
                            stream=stream_name,
                            content=text,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                        )
                else:
                    shell_task.cancel()
                    try:
                        await shell_task
                    except asyncio.CancelledError:
                        pass

            if graph_task in done:
                try:
                    raw_event = graph_task.result()
                except StopAsyncIteration:
                    if shell_q is not None:
                        while True:
                            try:
                                item = shell_q.get_nowait()
                            except queue.Empty:
                                break
                            stream_name, text = item
                            if stream_name not in ("stdout", "stderr"):
                                stream_name = "stdout"
                            yield ToolOutputChunkEvent(
                                role="tool",
                                tool_call_id=active_shell_tool_call_id,
                                stream=stream_name,
                                content=text,
                                timestamp=datetime.now(timezone.utc).isoformat(),
                            )
                    break

                for event in processor.process_event(raw_event):
                    if isinstance(event, ToolCallEvent) and is_shell_tool_name(event.tool):
                        active_shell_tool_call_id = event.tool_call_id or ""
                    elif isinstance(event, ToolResultEvent):
                        active_shell_tool_call_id = ""
                    yield event

                graph_task = asyncio.create_task(agen.__anext__())
    finally:
        if not graph_task.done():
            graph_task.cancel()
            try:
                await graph_task
            except asyncio.CancelledError:
                pass
