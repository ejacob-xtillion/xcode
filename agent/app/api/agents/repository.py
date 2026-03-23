from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.core.db.models import AgentSession
from app.core.errors.custom_errors import NotFoundError, DatabaseError, AppError
from app.api.agents.models import AgentEvent, ToolCallRecord
from datetime import datetime, timezone
from typing import Optional
from inspect import Parameter


class AgentRepository:
    """Repository for agent session persistence. Supports both database and in-memory storage."""

    def __init__(self):
        # In-memory storage for when database is not configured
        self._in_memory_sessions: dict[int, AgentSession] = {}
        self._next_id = 1

    async def create_agent_session(
        self,
        db_session: Optional[AsyncSession],
        query: str,
        agent_name: str,
        agent_type: str,
        status: str = "pending",
        messages: list[AgentEvent] | None = None,
        state: dict | None = None,
        tool_calls: list[ToolCallRecord] | None = None,
    ) -> AgentSession:
        try:
            agent_session = AgentSession(
                query=query,
                agent_name=agent_name,
                agent_type=agent_type,
                status=status,
                messages=[msg.model_dump() for msg in messages] if messages else [],
                state=state if state else {},
                tool_calls=[tc.model_dump() for tc in tool_calls] if tool_calls else [],
            )

            if db_session:
                # Database mode: persist to DB
                db_session.add(agent_session)
                await db_session.flush()
                await db_session.refresh(agent_session)
            else:
                # In-memory mode: store locally
                agent_session.id = self._next_id
                agent_session.created_at = datetime.now(timezone.utc)
                agent_session.updated_at = datetime.now(timezone.utc)
                self._in_memory_sessions[self._next_id] = agent_session
                self._next_id += 1

            return agent_session

        except Exception:
            raise DatabaseError(message=f"Failed to create agent session")

    async def get_agent_session_by_id(self, db_session: Optional[AsyncSession], agent_session_id: int) -> AgentSession:
        try:
            if db_session:
                # Database mode
                result = await db_session.execute(select(AgentSession).where(AgentSession.id == agent_session_id))
                agent_session = result.scalar_one_or_none()
            else:
                # In-memory mode
                agent_session = self._in_memory_sessions.get(agent_session_id)

            if not agent_session:
                raise NotFoundError(message="Agent session not found")

            return agent_session

        except AppError:
            raise
        except Exception:
            raise DatabaseError(message="Failed to retrieve agent session")

    async def list_agent_sessions(
        self, db_session: Optional[AsyncSession], limit: int = 100, offset: int = 0
    ) -> tuple[list[AgentSession], int]:
        try:
            if db_session:
                # Database mode
                count_result = await db_session.execute(select(AgentSession))
                total = len(count_result.all())

                result = await db_session.execute(
                    select(AgentSession).order_by(desc(AgentSession.created_at)).limit(limit).offset(offset)
                )
                agent_sessions = result.scalars().all()
            else:
                # In-memory mode
                all_sessions = sorted(self._in_memory_sessions.values(), key=lambda s: s.created_at, reverse=True)
                total = len(all_sessions)
                agent_sessions = all_sessions[offset : offset + limit]

            return list(agent_sessions), total

        except Exception:
            raise DatabaseError(message="Failed to list agent sessions")

    async def update_agent_session(
        self,
        db_session: Optional[AsyncSession],
        agent_session_id: int,
        status: str | None = None,
        query: str | None = None,
        result: str | None = Parameter.empty,
        messages: list[AgentEvent] | None = None,
        state: dict | None = None,
        tool_calls: list[ToolCallRecord] | None = None,
    ) -> AgentSession:
        try:
            agent_session = await self.get_agent_session_by_id(db_session, agent_session_id)

            if status is not None:
                agent_session.status = status
            if query is not None:
                agent_session.query = query
            if result is not Parameter.empty:
                agent_session.result = result
            if messages is not None:
                agent_session.messages = agent_session.messages + [msg.model_dump() for msg in messages]
            if state is not None:
                agent_session.state = state
            if tool_calls is not None:
                agent_session.tool_calls = agent_session.tool_calls + [tc.model_dump() for tc in tool_calls]

            if db_session:
                # Database mode
                await db_session.flush()
                await db_session.refresh(agent_session)
            else:
                # In-memory mode: update timestamp
                agent_session.updated_at = datetime.now(timezone.utc)

            return agent_session

        except AppError:
            raise
        except Exception:
            raise DatabaseError(message="Failed to update agent session")

    async def delete_agent_session(self, db_session: Optional[AsyncSession], agent_session_id: int) -> None:
        try:
            agent_session = await self.get_agent_session_by_id(db_session, agent_session_id)

            if db_session:
                # Database mode
                await db_session.delete(agent_session)
            else:
                # In-memory mode
                if agent_session_id in self._in_memory_sessions:
                    del self._in_memory_sessions[agent_session_id]

        except AppError:
            raise
        except Exception:
            raise DatabaseError(message="Failed to delete agent session")
