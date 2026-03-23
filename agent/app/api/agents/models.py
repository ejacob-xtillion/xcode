from datetime import datetime
from pydantic import BaseModel, Field
from typing import Union, Literal, Any

# AgentName represents the agent name (config key), not the agent type
# This will be dynamically generated based on the config
AgentName = Literal["xcode_coding_agent"]
SessionStatus = Literal["running", "completed", "interrupted", "failed"]


class AgentRunRequest(BaseModel):
    query: str = Field(..., description="Query to send to the agent")
    agent_name: AgentName = Field(
        "xcode_coding_agent",
        description="Agent name (config key), e.g., 'cocktail_expert', 'research_assistant'",
    )
    session_id: int | None = Field(None, description="Session ID to reuse an existing session")


class DecisionEdit(BaseModel):
    name: str = Field(..., description="Tool name")
    args: dict[str, Any] = Field(..., description="Modified tool arguments")


class Decision(BaseModel):
    type: Literal["approve", "edit", "reject"] = Field(..., description="Decision type")
    edited_action: DecisionEdit | None = Field(None, description="Required when type='edit'")
    message: str | None = Field(None, description="Feedback message (typically for 'reject')")


class ResumeCommand(BaseModel):
    decisions: list[Decision] | None = Field(None, description="List of decisions for HumanInTheLoopMiddleware")


class AgentResumeRequest(BaseModel):
    session_id: int = Field(..., description="Session ID to resume")
    command: ResumeCommand = Field(..., description="Command to resume interrupted execution")


class AgentSessionResponse(BaseModel):
    id: int
    agent_name: str = Field(..., description="Agent name (config key)")
    query: str
    result: str | None = None
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    messages: list[dict] = Field(default_factory=list)
    state: dict = Field(default_factory=dict)
    tool_calls: list[dict] = Field(default_factory=list)

    class Config:
        from_attributes = True
        populate_by_name = True  # Allow both field name and alias


class AgentSessionListResponse(BaseModel):
    sessions: list[AgentSessionResponse]
    total: int


class ToolCallRecord(BaseModel):
    tool_name: str = Field(..., description="Name of the tool that was called")
    params: str = Field(..., description="Parameters passed to the tool")
    timestamp: str = Field(..., description="ISO 8601 timestamp when the tool was called")
    result: str | None = Field(None, description="Result returned from the tool execution")


class SessionCreatedEvent(BaseModel):
    type: Literal["session_created"] = "session_created"
    session_id: int = Field(..., description="Unique identifier for the agent session")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the event")

class SessionRetrievedEvent(BaseModel):
    type: Literal["session_retrieved"] = "session_retrieved"
    session_id: int = Field(..., description="Unique identifier for the agent session")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the event")

class TokenEvent(BaseModel):
    role: Literal["assistant"] = "assistant"
    type: Literal["token"] = "token"
    content: str = Field(..., description="Individual token from the agent's streaming response")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the event")


class ToolCallEvent(BaseModel):
    role: Literal["assistant"] = "assistant"
    type: Literal["tool_call"] = "tool_call"
    tool_call_id: str = Field(..., description="Unique identifier for the tool call")
    tool: str = Field(..., description="Name of the tool being called")
    args: dict = Field(default_factory=dict, description="Arguments for the tool call")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the event")


class ToolResultEvent(BaseModel):
    role: Literal["tool"] = "tool"
    type: Literal["tool_result"] = "tool_result"
    tool_call_id: str = Field(..., description="ID of the tool call this result corresponds to")
    content: str = Field(..., description="Result or output from tool execution")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the event")


class ReasoningEvent(BaseModel):
    role: Literal["assistant"] = "assistant"
    type: Literal["reasoning"] = "reasoning"
    content: str = Field(..., description="Reasoning or thinking trace from the model")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the event")


class CitationEvent(BaseModel):
    role: Literal["assistant"] = "assistant"
    type: Literal["citation"] = "citation"
    content: str = Field(..., description="Citation or reference content")
    source: str | None = Field(None, description="Source of the citation")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the event")


class MediaEvent(BaseModel):
    role: Literal["assistant"] = "assistant"
    type: Literal["media"] = "media"
    media_type: Literal["image", "audio", "video", "file"] = Field(..., description="Type of media content")
    url: str | None = Field(None, description="URL to the media content")
    data: str | None = Field(None, description="Base64-encoded media data")
    mime_type: str | None = Field(None, description="MIME type of the media")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the event")


class AnswerEvent(BaseModel):
    role: Literal["assistant"] = "assistant"
    type: Literal["answer"] = "answer"
    content: str = Field(..., description="Final answer from the agent")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the event")


class InvalidToolCallEvent(BaseModel):
    role: Literal["assistant"] = "assistant"
    type: Literal["invalid_tool_call"] = "invalid_tool_call"
    tool_call_id: str | None = Field(None, description="Tool call identifier if available")
    error: str = Field(..., description="Error message describing why the tool call is invalid")
    raw_content: str | None = Field(None, description="Raw content that failed to parse")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the event")


class InterruptEvent(BaseModel):
    role: Literal["assistant"] = "assistant"
    type: Literal["interrupt"] = "interrupt"
    options: list[str] | None = Field(None, description="Available options for user to choose from")
    prompt: str = Field(..., description="Prompt or question for the user")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the event")


class ErrorEvent(BaseModel):
    role: Literal["assistant"] = "assistant"
    type: Literal["error"] = "error"
    content: str = Field(..., description="Error message")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the event")


class CompleteEvent(BaseModel):
    type: Literal["complete"] = "complete"
    session_id: int = Field(..., description="Unique identifier for the agent session")
    status: SessionStatus
    execution_time_ms: int = Field(..., description="Total execution time in milliseconds")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the event")


class AgentCompletionResponse(BaseModel):
    session_id: int = Field(..., description="Unique identifier for the agent session")
    status: SessionStatus = Field(..., description="Final status of the agent execution")
    result: str | None = Field(None, description="Final result/answer from the agent")
    execution_time_ms: int = Field(..., description="Total execution time in milliseconds")
    timestamp: str = Field(..., description="ISO 8601 timestamp when execution completed")
    tool_calls: list[ToolCallRecord] = Field(
        default_factory=list, description="List of tool calls made during execution"
    )

class QueryResultPair(BaseModel):
    query: str = Field(..., description="Initial query sent to the agent for this turn")
    result: str = Field(..., description="Final result/answer from the agent")

StreamEvent = Union[
    SessionCreatedEvent,
    SessionRetrievedEvent,
    TokenEvent,
    ToolCallEvent,
    ToolResultEvent,
    AnswerEvent,
    ErrorEvent,
    InterruptEvent,
    ReasoningEvent,
    CitationEvent,
    MediaEvent,
    InvalidToolCallEvent,
    CompleteEvent,
]

AgentEvent = Union[
    TokenEvent,
    ToolCallEvent,
    ToolResultEvent,
    AnswerEvent,
    ErrorEvent,
    InterruptEvent,
    ReasoningEvent,
    CitationEvent,
    MediaEvent,
    InvalidToolCallEvent,
]