from typing import AsyncGenerator, Dict, List, Optional
from datetime import datetime, timezone
import uuid

from app.api.agents.shell_stream_multiplex import (
    iter_graph_events,
    multiplex_astream_with_shell_queue,
)
from langchain.messages import HumanMessage, AIMessage
from langgraph.types import Command
from langchain_core.tools import BaseTool
from app.core.db.connection import get_session
from app.api.agents.repository import AgentRepository
from app.api.agents.models import (
    AgentSessionResponse,
    AgentSessionListResponse,
    AgentCompletionResponse,
    StreamEvent,
    SessionCreatedEvent,
    SessionRetrievedEvent,
    AgentEvent,
    TokenEvent,
    ToolCallEvent,
    ToolResultEvent,
    ToolOutputChunkEvent,
    AnswerEvent,
    ErrorEvent,
    CompleteEvent,
    InterruptEvent,
    ToolCallRecord,
    ResumeCommand,
    QueryResultPair,
)

from app.engine.agent_tool_config import XCODE_CODING_AGENT_MCP_SERVERS
from app.engine.xcode_coding_agent.agent import create_agent_instance as create_xcode_coding_agent_instance

from app.engine.stream_processor import AgentStreamProcessor
from app.core.errors.custom_errors import BadRequestError, NotFoundError, AppError
from app.core.settings import get_settings
from app.engine.mcp_tools import get_tool_discovery, build_agent_tool_map
from app.core.middleware.mcp_headers import get_mcp_headers
from fastapi import Request
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.core.logger import get_logger

logger = get_logger()


class AgentService:
    def __init__(self):
        self.repository = AgentRepository()
        # Initialize checkpointer attributes (lazy initialization in _create_agent)
        self.memory_checkpointer = None
        self._checkpointer_context = None
        # Agent configurations for tool mapping
        # Format: {"agent_name": {"mcpServers": [...], "tools": [...]}}
        self.agent_configs = {
            
            "xcode_coding_agent": {
                "agent_type": "simple_agent",
                "mcpServers": list(XCODE_CODING_AGENT_MCP_SERVERS),
                "tools": 
                    {
                    
                    },
            },
            
        }
        
    async def _create_agent(
        self, 
        agent_name: str, 
        agent_session_id: int | None = None,
        headers: Optional[Dict[str, str]] = None,
        request: Optional[Request] = None,
        tools: Optional[List[BaseTool]] = None,
    ):
        """
        Create an agent instance by agent name (config key).

        Args:
            agent_name: Agent name from config (e.g., 'cocktail_expert', 'research_assistant')
            agent_session_id: Optional session ID for agents that require checkpointing
            headers: Optional headers to forward to MCP servers (auth, tenant, correlation id)
            request: Optional FastAPI request object for building per-server headers
            tools: Optional list of tools to pass to the agent factory
        """
        settings = get_settings()
        
        if self.memory_checkpointer is None:
            if settings.database_url is None:
                self.memory_checkpointer = InMemorySaver()
                logger.info("checkpointer_initialized", type="InMemorySaver")
            else:
                # AsyncPostgresSaver.from_conn_string returns an async context manager
                self._checkpointer_context = AsyncPostgresSaver.from_conn_string(settings.database_url)
                self.memory_checkpointer = await self._checkpointer_context.__aenter__()
                await self.memory_checkpointer.setup()
                logger.info("checkpointer_initialized", type="AsyncPostgresSaver")
        
        checkpointer = self.memory_checkpointer

        
        
        if agent_name == "xcode_coding_agent":
            return await create_xcode_coding_agent_instance(
                settings, 
                checkpointer=checkpointer,
                headers=headers,
                request=request,
                tools=tools,
                agent_session_id=agent_session_id, 
            )
        
        
        else:
            raise BadRequestError(f"Unsupported agent name: {agent_name}")

    async def cleanup(self):
        """Cleanup checkpointer resources."""
        if self._checkpointer_context is not None:
            await self._checkpointer_context.__aexit__(None, None, None)
            logger.info("checkpointer_cleanup_complete")

    def _requires_checkpointing(self, agent_name: str) -> bool:
        """Check if an agent requires checkpointing based on its type."""
        # Get the agent_type for this agent_name
        agent_config = self.agent_configs.get(agent_name)
        if not agent_config:
            return False
        
        agent_type = agent_config.get("agent_type", "")
        
        # Agent types that require checkpointing
        CHECKPOINT_AGENT_TYPES = {
            "hitl_agent",
            "supervisor_agent"
        }
        
        return agent_type in CHECKPOINT_AGENT_TYPES

    async def _extract_mcp_headers(self, request: Optional[Request]) -> Optional[Dict[str, str]]:
        """Extract MCP headers from request if available."""
        if request:
            return get_mcp_headers(request)
        return None

    async def _discover_agent_tools(self, agent_name: str, headers: Optional[Dict[str, str]]) -> List[BaseTool]:
        """Discover and return tools for a specific agent."""
        agent_config = self.agent_configs.get(agent_name)
        if not agent_config:
            return []
        
        if agent_config.get("agent_type") == "supervisor_agent":
            return []
        
        mcp_servers = agent_config.get("mcpServers", [])
        if not mcp_servers:
            return []
        
        discovery = get_tool_discovery()
        all_tools_by_server = {}
        for server_name in mcp_servers:
            tools = await discovery.discover_server_tools(server_name, headers=headers)
            all_tools_by_server[server_name] = tools
        
        agent_tool_map = build_agent_tool_map(
            agent_configs={agent_name: agent_config},
            all_tools_by_server=all_tools_by_server,
        )
        return agent_tool_map.get(agent_name, [])

    async def _prepare_agent_execution(
        self,
        agent_name: str,
        agent_session_id: int | None,
        headers: Optional[Dict[str, str]],
        request: Optional[Request],
        tools: List[BaseTool],
    ) -> tuple:
        """Prepare agent and config for execution."""
        thread_id = str(agent_session_id) if agent_session_id else f"ephemeral_{uuid.uuid4().hex}"
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": 100,  # Increase from default 25 for complex coding tasks
        }
        
        agent = await self._create_agent(
            agent_name,
            agent_session_id=agent_session_id,
            headers=headers,
            request=request,
            tools=tools,
        )
        
        return agent, config

   
    async def run_agent_streaming(self, query: str, agent_name: str, session_id: int | None = None, request: Optional[Request] = None) -> AsyncGenerator[StreamEvent, None]:
        if not query or not query.strip():
            raise BadRequestError("Query cannot be empty")

        async with get_session() as db_session:
            if session_id:
                agent_session = await self.repository.get_agent_session_by_id(db_session, session_id)
                if agent_session.agent_name != agent_name:
                    raise BadRequestError(f"Agent session {session_id} was created with agent '{agent_session.agent_name}', cannot use with '{agent_name}'")
                agent_session_id = session_id
                logger.info("agent_session_retrieved", agent_session_id=agent_session_id, agent_name=agent_name)
                yield SessionRetrievedEvent(session_id=agent_session_id, timestamp=datetime.now(timezone.utc).isoformat())
                await self.repository.update_agent_session(db_session, agent_session_id, status="running", query=query, result=None)
            else:
                # Create new agent session with agent_name and agent_type
                agent_type = self.agent_configs[agent_name]["agent_type"]
                agent_session = await self.repository.create_agent_session(
                    db_session, query=query, agent_name=agent_name, agent_type=agent_type, status="running"
                )
                agent_session_id = agent_session.id
                logger.info("agent_session_created", agent_session_id=agent_session_id, agent_name=agent_name)
                yield SessionCreatedEvent(session_id=agent_session_id, timestamp=datetime.now(timezone.utc).isoformat())


        # Extract headers and prepare agent execution
        headers = await self._extract_mcp_headers(request)
        agent_tools = await self._discover_agent_tools(agent_name, headers)
        agent, config = await self._prepare_agent_execution(
            agent_name, agent_session_id, headers, request, agent_tools
        )

        input_data = {"messages": [HumanMessage(content=query)]}

        async for event in self._stream_agent_execution(agent, input_data, config, agent_session_id):
            yield event

    async def resume_agent_streaming(
        self, agent_session_id: int, command: ResumeCommand, request: Optional[Request] = None
    ) -> AsyncGenerator[StreamEvent, None]:
        async with get_session() as db_session:
            agent_session = await self.repository.get_agent_session_by_id(db_session, agent_session_id)
            if not agent_session:
                raise NotFoundError(f"Agent session {agent_session_id} not found")

            # Read agent_name from DB column
            agent_name = agent_session.agent_name

        logger.info("agent_session_resumed", agent_session_id=agent_session_id, agent_name=agent_name)

        # Extract headers and prepare agent execution
        headers = await self._extract_mcp_headers(request)
        
        # For supervisor agents, check if any subagent is interrupted
        # If so, resume the subagent directly with the user's decisions
        agent_config = self.agent_configs.get(agent_name, {})
        if agent_config.get("agent_type") == "supervisor_agent":
            subagent_names = agent_config.get("tools", {}).get("subagents", [])
            
            # Check each subagent for interrupted state
            for subagent_name in subagent_names:
                subagent_thread_id = f"{agent_session_id}:{subagent_name}"
                try:
                    # Create agent with minimal tools just to check state
                    subagent, subagent_config = await self._prepare_agent_execution(
                        subagent_name, None, headers, request, []  # Empty tools list for state check
                    )
                    subagent_config = {"configurable": {"thread_id": subagent_thread_id}}
                    subagent_state = await subagent.aget_state(subagent_config)
                    
                    if subagent_state.next:
                        # Found interrupted subagent - NOW discover tools for actual resume
                        logger.info("resuming_interrupted_subagent", 
                                  subagent_name=subagent_name, 
                                  subagent_thread_id=subagent_thread_id,
                                  has_decisions=command.decisions is not None)
                        
                        # Recreate agent with full tools for resume execution
                        subagent_tools = await self._discover_agent_tools(subagent_name, headers)
                        subagent, subagent_config = await self._prepare_agent_execution(
                            subagent_name, None, headers, request, subagent_tools
                        )
                        subagent_config = {"configurable": {"thread_id": subagent_thread_id}}
                        
                        # Resume the subagent with the command containing decisions
                        input_data = Command(resume=command.model_dump(exclude_none=True))
                        
                        # Resume the subagent and collect final result
                        final_answer = None
                        async for event in self._stream_agent_execution(subagent, input_data, subagent_config, agent_session_id):
                            yield event
                            # Capture answer events to get final result
                            if isinstance(event, AnswerEvent):
                                final_answer = event.content
                        
                        # Now notify the supervisor that the subagent completed
                        logger.info("notifying_supervisor_of_completion", 
                                  supervisor_name=agent_name,
                                  subagent_name=subagent_name)
                        
                        try:
                            from langchain_core.messages import HumanMessage
                            supervisor_tools = await self._discover_agent_tools(agent_name, headers)
                            supervisor_agent, supervisor_config = await self._prepare_agent_execution(
                                agent_name, agent_session_id, headers, request, supervisor_tools
                            )
                            
                            # Send completion notification to supervisor
                            notification = f"The {subagent_name} subagent has completed the task you delegated."
                            if final_answer:
                                notification += f"\n\nResult: {final_answer}"
                            
                            notification_input = {"messages": [HumanMessage(content=notification)]}
                            
                            # The tool wrapper will clean up any corrupted state before processing
                            async for event in self._stream_agent_execution(supervisor_agent, notification_input, supervisor_config, agent_session_id):
                                yield event
                        except Exception as e:
                            logger.error("supervisor_notification_failed", error=str(e), exc_info=True)
                        
                        return
                except Exception as e:
                    logger.debug("subagent_check_failed", subagent_name=subagent_name, error=str(e))
                    continue
        
        # No interrupted subagent found - resume the main agent
        agent_tools = await self._discover_agent_tools(agent_name, headers)
        agent, config = await self._prepare_agent_execution(
            agent_name, agent_session_id, headers, request, agent_tools
        )

        input_data = Command(resume=command.model_dump(exclude_none=True))

        async for event in self._stream_agent_execution(agent, input_data, config, agent_session_id):
            yield event

    async def _stream_agent_execution(
        self, agent, input_data, config: dict, agent_session_id: int
    ) -> AsyncGenerator[StreamEvent, None]:
        start_time = datetime.now(timezone.utc)
        final_status = "completed"
        query = None
        final_result = None
        all_messages: list[AgentEvent] = []
        all_tool_calls: list[ToolCallRecord] = []
        processor = AgentStreamProcessor()
        
        async with get_session() as db_session:
            agent_session = await self.repository.get_agent_session_by_id(db_session, agent_session_id)
            query = agent_session.query

        settings = get_settings()
        thread_id = config.get("configurable", {}).get("thread_id")
        shell_q = None
        if (
            thread_id
            and settings.shell_stream_output_to_client
            and settings.shell_stream_queue_max_chunks > 0
        ):
            from app.engine.xcode_coding_agent.shell_stream_registry import (
                register_shell_stream_queue,
            )

            shell_q = register_shell_stream_queue(
                str(thread_id), settings.shell_stream_queue_max_chunks
            )

        try:
            event_source = (
                multiplex_astream_with_shell_queue(
                    agent, input_data, config, shell_q, processor
                )
                if shell_q is not None
                else iter_graph_events(agent, input_data, config, processor)
            )

            async for event in event_source:
                if isinstance(event, InterruptEvent):
                    final_status = "interrupted"
                elif isinstance(event, ErrorEvent):
                    final_status = "failed"
                elif isinstance(event, AnswerEvent):
                    if final_result is None:
                        final_result = event.content
                    all_messages.append(event)
                elif isinstance(event, TokenEvent):
                    all_messages.append(event)
                elif isinstance(event, ToolCallEvent):
                    all_messages.append(event)
                    all_tool_calls.append(
                        ToolCallRecord(
                            tool_name=event.tool,
                            params=str(event.args),
                            timestamp=event.timestamp,
                        )
                    )
                elif isinstance(event, ToolResultEvent):
                    all_messages.append(event)
                elif isinstance(event, ToolOutputChunkEvent):
                    pass

                yield event

            end_time = datetime.now(timezone.utc)
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            if final_status == "completed" and final_result is not None:
                query_result_pair = [QueryResultPair(query=query, result=final_result)]
            else:
                query_result_pair = []

            async with get_session() as db_session:
                await self.repository.update_agent_session(
                    db_session,
                    agent_session_id=agent_session_id,
                    status=final_status,
                    result=final_result,
                    messages=query_result_pair,
                    tool_calls=all_tool_calls,
                )
            logger.info("agent_execution_completed", agent_session_id=agent_session_id, status=final_status)

            yield CompleteEvent(
                session_id=agent_session_id,
                status=final_status,
                execution_time_ms=execution_time_ms,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

        except AppError:
            raise
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Include actual error message for debugging
            error_message = f"An error occurred during processing: {str(e)}"

            logger.error("agent_execution_failed", agent_session_id=agent_session_id, error=str(e), exc_info=True)

            # Persist failed status to DB
            async with get_session() as db_session:
                await self.repository.update_agent_session(
                    db_session,
                    agent_session_id=agent_session_id,
                    status="failed"
                )

            yield ErrorEvent(content=error_message, timestamp=datetime.now(timezone.utc).isoformat())

            yield CompleteEvent(
                session_id=agent_session_id,
                status="failed",
                execution_time_ms=execution_time_ms,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        finally:
            if thread_id:
                from app.engine.xcode_coding_agent.shell_stream_registry import (
                    unregister_shell_stream_queue,
                )

                unregister_shell_stream_queue(str(thread_id))

    async def get_agent_session(self, agent_session_id: int) -> AgentSessionResponse:
        async with get_session() as db_session:
            agent_session = await self.repository.get_agent_session_by_id(db_session, agent_session_id)
            return AgentSessionResponse.model_validate(agent_session)

    async def list_agent_sessions(self, limit: int = 100, offset: int = 0) -> AgentSessionListResponse:
        if limit < 1 or limit > 1000:
            raise BadRequestError("Limit must be between 1 and 1000")

        if offset < 0:
            raise BadRequestError("Offset must be non-negative")

        async with get_session() as db_session:
            agent_sessions, total = await self.repository.list_agent_sessions(db_session, limit=limit, offset=offset)

        return AgentSessionListResponse(
            sessions=[AgentSessionResponse.model_validate(s) for s in agent_sessions],
            total=total,
        )

    async def run_agent_completion(self, query: str, agent_name: str, request: Optional[Request] = None, session_id: int | None = None) -> AgentCompletionResponse:
        if not query or not query.strip():
            raise BadRequestError("Query cannot be empty")
        
        async with get_session() as db_session:
            if session_id:
                agent_session = await self.repository.get_agent_session_by_id(db_session, session_id)
                if agent_session.agent_name != agent_name:
                    raise BadRequestError(f"Agent session {session_id} was created with agent '{agent_session.agent_name}', cannot use with '{agent_name}'")
                agent_session_id = session_id
                await self.repository.update_agent_session(db_session, agent_session_id, status="running", query=query, result=None)
            else:
                # Create new agent session with agent_name and agent_type
                agent_type = self.agent_configs[agent_name]["agent_type"]
                agent_session = await self.repository.create_agent_session(
                    db_session, query=query, agent_name=agent_name, agent_type=agent_type, status="running"
                )
                agent_session_id = agent_session.id

        logger.info("agent_session_created", agent_session_id=agent_session_id, agent_name=agent_name)

        headers = await self._extract_mcp_headers(request)
        agent_tools = await self._discover_agent_tools(agent_name, headers)

        # Determine if checkpointing/DB persistence is needed
        requires_checkpointing = self._requires_checkpointing(agent_name)

        # Create DB session and agent_session if checkpointing is required
        if requires_checkpointing:
            async with get_session() as db_session:
                agent_type = self.agent_configs[agent_name]["agent_type"]
                agent_session = await self.repository.create_agent_session(
                    db_session, query=query, agent_name=agent_name, agent_type=agent_type, status="running"
                )
                agent_session_id = agent_session.id
            logger.info("agent_session_created", agent_session_id=agent_session_id, agent_name=agent_name)
        
        # Prepare agent execution (creates agent and config)
        agent, config = await self._prepare_agent_execution(
            agent_name, agent_session_id, headers, request, agent_tools
        )

        input_data = {"messages": [HumanMessage(content=query)]}

        return await self._run_agent_completion_execution(
            agent, input_data, config, agent_session_id, agent_name
        )

        
    def _extract_text_from_content(self, content, timestamp: str) -> tuple[str, list[ToolCallRecord], list[AgentEvent]]:
        """
        Extract text content from AIMessage content which can be:
        - A string (simple case)
        - A list of content blocks (Bedrock format: [{"type": "text", "text": "..."}, ...])
        
        Returns:
            tuple: (text_content, tool_calls, events)
        """
        tool_calls = []
        events = []
        
        if isinstance(content, str):
            return content, tool_calls, events
        
        if not isinstance(content, list):
            return str(content), tool_calls, events
        
        # Handle content blocks (Bedrock format)
        text_parts = []
        for block in content:
            if isinstance(block, dict):
                block_type = block.get("type")
                if block_type == "text":
                    text_parts.append(str(block.get("text", "")))
                elif block_type == "tool_use":
                    # Extract tool call information
                    tool_name = block.get("name", "")
                    tool_args = block.get("input", {})
                    tool_call_id = block.get("id", "")
                    tool_calls.append(ToolCallRecord(tool_name=tool_name, params=str(tool_args), timestamp=timestamp))
                    events.append(ToolCallEvent(tool_call_id=tool_call_id, tool=tool_name, args=tool_args, timestamp=timestamp))
            elif isinstance(block, str):
                text_parts.append(block)
        
        return " ".join(text_parts).strip(), tool_calls, events

    async def _run_agent_completion_execution(
        self, agent, input_data, config: dict, agent_session_id: int | None, agent_name: str
    ) -> AgentCompletionResponse:
        start_time = datetime.now(timezone.utc)
        all_tool_calls: list[ToolCallRecord] = []
        all_messages: list[AgentEvent] = []
        query = None
        final_result = None
        final_status = "completed"

        try:
            query = input_data.get("messages", [])[0].content if input_data.get("messages") else None
            
            if agent_session_id:
                thread_id = config.get("configurable", {}).get("thread_id")
                logger.info(
                    "agent_invocation_starting",
                    agent_session_id=agent_session_id,
                    thread_id=thread_id,
                    new_message=query
                )
            
            result = await agent.ainvoke(input_data, config=config)
            messages = result.get("messages", [])
            timestamp = datetime.now(timezone.utc).isoformat()
            
            message_types = [type(msg).__name__ if hasattr(msg, '__class__') else type(msg).__name__ if isinstance(msg, dict) else str(type(msg)) for msg in messages]
            logger.info(
                "agent_invocation_complete",
                agent_session_id=agent_session_id,
                total_messages_in_result=len(messages),
                thread_id=config.get("configurable", {}).get("thread_id"),
                message_types=message_types[:5]  # Log first 5 message types
            )

            # Parse messages to extract result, tool calls, and events
            for message in messages:
                if isinstance(message, AIMessage):
                    if hasattr(message, "content") and message.content:
                        # Extract text and tool calls from content (handles Bedrock content blocks)
                        content, tool_calls_from_content, events_from_content = self._extract_text_from_content(message.content, timestamp)
                        all_tool_calls.extend(tool_calls_from_content)
                        all_messages.extend(events_from_content)
                        
                        if content:
                            final_result = content
                            all_messages.append(AnswerEvent(content=content, timestamp=timestamp))
                    if hasattr(message, "tool_calls") and message.tool_calls:
                        for tool_call in message.tool_calls:
                            tool_name = tool_call.get("name", "") if isinstance(tool_call, dict) else getattr(tool_call, "name", "")
                            tool_args = tool_call.get("args", {}) if isinstance(tool_call, dict) else getattr(tool_call, "args", {})
                            tool_call_id = tool_call.get("id", "") if isinstance(tool_call, dict) else getattr(tool_call, "id", "")
                            all_tool_calls.append(ToolCallRecord(tool_name=tool_name, params=str(tool_args), timestamp=timestamp))
                            all_messages.append(ToolCallEvent(tool_call_id=tool_call_id, tool=tool_name, args=tool_args, timestamp=timestamp))
                elif isinstance(message, dict):
                    if "content" in message and message.get("content"):
                        # Extract text and tool calls from content (handles Bedrock content blocks)
                        content, tool_calls_from_content, events_from_content = self._extract_text_from_content(message.get("content", ""), timestamp)
                        all_tool_calls.extend(tool_calls_from_content)
                        all_messages.extend(events_from_content)
                        
                        if content:
                            final_result = content
                            all_messages.append(AnswerEvent(content=content, timestamp=timestamp))
                    if "tool_calls" in message:
                        for tool_call in message["tool_calls"]:
                            tool_call_id = tool_call.get("id", "")
                            all_tool_calls.append(ToolCallRecord(
                                tool_name=tool_call.get("name", ""),
                                params=str(tool_call.get("args", {})),
                                timestamp=timestamp
                            ))
                            all_messages.append(ToolCallEvent(
                                tool_call_id=tool_call_id,
                                tool=tool_call.get("name", ""),
                                args=tool_call.get("args", {}),
                                timestamp=timestamp
                            ))

            # Get result from last message if not found
            if final_result is None and messages:
                last_message = messages[-1]
                if isinstance(last_message, AIMessage) and hasattr(last_message, "content"):
                    final_result, _, _ = self._extract_text_from_content(last_message.content, timestamp)
                elif isinstance(last_message, dict) and "content" in last_message:
                    final_result, _, _ = self._extract_text_from_content(last_message.get("content", ""), timestamp)

            end_time = datetime.now(timezone.utc)
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)

            if final_status == "completed" and final_result is not None:
                query_result_pair = [QueryResultPair(query=query, result=final_result)]
            else:
                query_result_pair = []

            # Persist results to DB if session_id exists
            if agent_session_id:
                async with get_session() as db_session:
                    await self.repository.update_agent_session(
                        db_session, agent_session_id=agent_session_id, status=final_status,
                        result=final_result, messages=query_result_pair, tool_calls=all_tool_calls
                    )
                logger.info("agent_execution_completed", agent_session_id=agent_session_id, agent_name=agent_name, status=final_status)
            else:
                logger.info("agent_execution_completed", agent_name=agent_name, status=final_status)

            return AgentCompletionResponse(
                session_id=agent_session_id if agent_session_id else 0,
                status=final_status,
                result=final_result,
                execution_time_ms=execution_time_ms,
                timestamp=datetime.now(timezone.utc).isoformat(),
                tool_calls=all_tool_calls,
            )

        except AppError:
            raise
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            final_status = "failed"
            error_result = f"An error occurred during processing: {str(e)}"

            # Persist error to DB if session_id exists
            if agent_session_id:
                async with get_session() as db_session:
                    await self.repository.update_agent_session(
                        db_session, agent_session_id=agent_session_id, status=final_status,
                        result=error_result, messages=all_messages, tool_calls=all_tool_calls
                    )
                logger.error("agent_execution_failed", agent_session_id=agent_session_id, agent_name=agent_name, error=str(e), exc_info=True)
            else:
                logger.error("agent_execution_failed", agent_name=agent_name, error=str(e), exc_info=True)

            return AgentCompletionResponse(
                session_id=agent_session_id if agent_session_id else 0,
                status=final_status,
                result=error_result,
                execution_time_ms=execution_time_ms,
                timestamp=datetime.now(timezone.utc).isoformat(),
                tool_calls=all_tool_calls,
            )
