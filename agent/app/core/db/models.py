from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone

Base = declarative_base()


class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id = Column(Integer, primary_key=True, index=True)
    agent_type = Column(String(50), nullable=False, index=True)
    agent_name = Column(String(50), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="pending", index=True)  # pending, running, completed, failed
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    query = Column(Text, nullable=False)
    result = Column(Text, nullable=True)
    messages = Column(JSON, nullable=False, default=list)
    # Agent state/memory - stores agent's working memory, thoughts, observations
    state = Column(JSON, nullable=False, default=dict)
    tool_calls = Column(JSON, nullable=False, default=list)
