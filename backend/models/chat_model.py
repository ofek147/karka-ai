from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, ForeignKey
from uuid import uuid4
from datetime import datetime
from ..db import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, nullable=True, index=True)
    title = Column(String, default="שיחה חדשה")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("chat_sessions.id"), index=True)
    role = Column(String)  # "user" | "assistant"
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class LeadScore(Base):
    __tablename__ = "lead_scores"

    user_id = Column(String, primary_key=True)
    score = Column(Integer, default=0)
    signals = Column(JSON, default=dict)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
