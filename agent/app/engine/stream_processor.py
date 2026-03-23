"""
AgentStreamProcessor - Converts LangChain agent events to typed StreamEvent objects.

This utility class acts as an adapter between LangChain's raw event format
(from astream_events) and the application's typed StreamEvent models used
by the API layer for SSE streaming.
"""

from datetime import datetime, timezone
from app.api.agents.models import (
    StreamEvent,
    TokenEvent,
    ToolCallEvent,
    ToolResultEvent,
    AnswerEvent,
    ReasoningEvent,
    CitationEvent,
    MediaEvent,
    InvalidToolCallEvent,
    InterruptEvent,
)
from app.core.logger import get_logger

logger = get_logger()


class AgentStreamProcessor:

    def _get_timestamp(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _process_content_block(self, block: dict) -> StreamEvent | None:
        block_type = block.get("type")

        if block_type == "text":
            text_content = block.get("text", "")
            if text_content and text_content.strip():
                return TokenEvent(content=text_content, timestamp=self._get_timestamp())

        elif block_type == "reasoning":
            reasoning_content = block.get("reasoning", "")
            if reasoning_content and reasoning_content.strip():
                return ReasoningEvent(content=reasoning_content, timestamp=self._get_timestamp())

        elif block_type == "citation":
            citation_content = block.get("text", "")
            citation_source = block.get("source")
            if citation_content:
                return CitationEvent(content=citation_content, source=citation_source, timestamp=self._get_timestamp())

        elif block_type == "tool_call":
            tool_call_id = block.get("id", "")
            tool_name = block.get("name", "")
            tool_args = block.get("args", {})
            return ToolCallEvent(
                tool_call_id=tool_call_id, tool=tool_name, args=tool_args, timestamp=self._get_timestamp()
            )

        elif block_type == "invalid_tool_call":
            tool_call_id = block.get("id")
            error_message = block.get("error", "Invalid tool call")
            raw_content = block.get("raw", "")
            return InvalidToolCallEvent(
                tool_call_id=tool_call_id,
                error=error_message,
                raw_content=raw_content,
                timestamp=self._get_timestamp(),
            )

        elif block_type in ("image", "audio", "video", "file"):
            url = block.get("url")
            data = block.get("data")
            mime_type = block.get("mime_type")
            return MediaEvent(
                media_type=block_type,
                url=url,
                data=data,
                mime_type=mime_type,
                timestamp=self._get_timestamp(),
            )

        return None

    def _process_content_blocks(self, message) -> list[StreamEvent]:
        events = []
        if message and hasattr(message, "content_blocks"):
            for block in message.content_blocks:
                if typed_event := self._process_content_block(block):
                    events.append(typed_event)
        return events

    def process_event(self, event: dict) -> list[StreamEvent]:
        event_type = event.get("event")

        if event_type == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            return self._process_content_blocks(chunk)

        elif event_type == "on_chat_model_end":
            output = event.get("data", {}).get("output")
            if not output:
                return []

            if not hasattr(output, "content_blocks"):
                return []

            events = []
            text_block = next((block for block in output.content_blocks if block.get("type") == "text"), None)

            if text_block:
                complete_answer = text_block.get("text", "").strip()
                if complete_answer:
                    events.append(AnswerEvent(content=complete_answer, timestamp=self._get_timestamp()))
            else:
                events.extend(self._process_content_blocks(output))

            return events

        elif event_type == "on_tool_start":
            # Emit tool call event when tool starts
            data = event.get("data", {})
            tool_input = data.get("input", {})
            run_id = event.get("run_id", "")
            name = event.get("name", "unknown_tool")
            
            return [
                ToolCallEvent(
                    tool_call_id=run_id,
                    tool=name,
                    args=tool_input if isinstance(tool_input, dict) else {"input": tool_input},
                    timestamp=self._get_timestamp(),
                )
            ]

        elif event_type == "on_tool_end":
            # Emit tool result event when tool completes
            data = event.get("data", {})
            output = data.get("output", "")
            run_id = event.get("run_id", "")
            
            # Check if it's an error result
            is_error = False
            content = str(output) if output else ""
            
            if hasattr(output, "content"):
                content = output.content
            elif isinstance(output, dict):
                content = output.get("content", str(output))
                is_error = output.get("is_error", False)
            
            # Detect errors in content
            if "error" in content.lower() or "exception" in content.lower():
                is_error = True
            
            return [
                ToolResultEvent(
                    tool_call_id=run_id,
                    content=content,
                    is_error=is_error,
                    timestamp=self._get_timestamp(),
                )
            ]

        elif event_type == "on_chain_stream":
            chunk = event.get("data", {}).get("chunk", {})
            if isinstance(chunk, dict) and "__interrupt__" in chunk:
                interrupt_obj = chunk["__interrupt__"][0]
                value = interrupt_obj.value if hasattr(interrupt_obj, "value") else {}

                if "action_requests" in value:
                    # Handles streaming for HumanInTheLoopMiddleware version of interrupt
                    action = value.get("action_requests", [{}])[0]
                    config = value.get("review_configs", [{}])[0]
                    return [
                        InterruptEvent(
                            prompt=action.get("description", "Tool call pending approval"),
                            options=config.get("allowed_decisions"),
                            timestamp=self._get_timestamp(),
                        )
                    ]
                else:
                    # Handles traditional interrupt() function
                    return [
                        InterruptEvent(
                            prompt=value.get("prompt", "Agent paused for input"),
                            options=value.get("options"),
                            timestamp=self._get_timestamp(),
                        )
                    ]
        return []
