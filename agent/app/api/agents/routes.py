from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from app.api.agents.controller import AgentController
from app.api.agents.models import (
    AgentRunRequest,
    AgentResumeRequest,
    AgentSessionResponse,
    AgentSessionListResponse,
    AgentCompletionResponse,
)

router = APIRouter()
controller = AgentController()


@router.post("", response_class=StreamingResponse)
async def run_agent_stream(request: AgentRunRequest) -> StreamingResponse:
    return await controller.run_agent_streaming(request)


@router.post("/completion", response_model=AgentCompletionResponse)
async def run_agent_completion(request: AgentRunRequest) -> AgentCompletionResponse:
    return await controller.run_agent_completion(request)


@router.post("/resume", response_class=StreamingResponse)
async def resume_agent_stream(request: AgentResumeRequest) -> StreamingResponse:
    return await controller.resume_agent_streaming(request)


@router.get("/sessions", response_model=AgentSessionListResponse)
async def list_agent_sessions(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    return await controller.list_agent_sessions(limit=limit, offset=offset)


@router.get("/sessions/{agent_session_id}", response_model=AgentSessionResponse)
async def get_agent_session(agent_session_id: int):
    return await controller.get_agent_session(agent_session_id)
