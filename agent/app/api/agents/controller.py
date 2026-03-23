from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi.responses import StreamingResponse

from app.api.agents.models import (
    AgentCompletionResponse,
    AgentResumeRequest,
    AgentRunRequest,
    AgentSessionListResponse,
    AgentSessionResponse,
    ErrorEvent,
    StreamEvent,
)
from app.api.agents.service import AgentService
from app.core.errors.custom_errors import AppError
from app.core.logger import get_logger

logger = get_logger()


class AgentController:
    def __init__(self):
        self.service = AgentService()

    async def run_agent_streaming(self, request: AgentRunRequest) -> StreamingResponse:
        return self._create_sse_stream(
            event_generator=self.service.run_agent_streaming(
                query=request.query,
                agent_name=request.agent_name,
                session_id=request.session_id if request.session_id else None,
            )
        )

    async def resume_agent_streaming(self, request: AgentResumeRequest) -> StreamingResponse:
        return self._create_sse_stream(
            event_generator=self.service.resume_agent_streaming(
                agent_session_id=request.session_id,
                command=request.command,
            )
        )

    async def get_agent_session(self, agent_session_id: int) -> AgentSessionResponse:
        return await self.service.get_agent_session(agent_session_id)

    async def list_agent_sessions(self, limit: int = 100, offset: int = 0) -> AgentSessionListResponse:
        return await self.service.list_agent_sessions(limit=limit, offset=offset)

    async def run_agent_completion(self, request: AgentRunRequest) -> AgentCompletionResponse:
        return await self.service.run_agent_completion(
            query=request.query,
            agent_name=request.agent_name,
            session_id=request.session_id if request.session_id else None,
        )

    def _create_sse_stream(self, event_generator: AsyncGenerator[StreamEvent, None]) -> StreamingResponse:
        async def generate_sse_stream():
            try:
                async for event in event_generator:
                    yield f"data: {event.model_dump_json()}\n\n"

            except AppError as app_error:
                logger.error("streaming_app_error", error_code=app_error.error_code, message=app_error.message)
                error_event = ErrorEvent(content=app_error.message, timestamp=datetime.now(timezone.utc).isoformat())
                yield f"data: {error_event.model_dump_json()}\n\n"

            except Exception as e:
                logger.error("unexpected_streaming_error", error=str(e), exc_info=True)
                error_event = ErrorEvent(
                    content="An unexpected error occurred while streaming",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
                yield f"data: {error_event.model_dump_json()}\n\n"

        return StreamingResponse(
            generate_sse_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
