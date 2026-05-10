from datetime import datetime
from enum import Enum
from typing import Optional

from backend.models.base import CamelModel
from pydantic import Field


class MessageRole(str, Enum):
    TEACHER = "teacher"
    AGENT = "agent"
    SYSTEM = "system"
    TOOL_CALL = "tool_call"


class ToolCall(CamelModel):
    name: str
    params: dict = Field(default_factory=dict)
    result: Optional[dict] = None


class ChatMessage(CamelModel):
    id: str
    project_id: str
    role: MessageRole
    content: str
    tool_call: Optional[ToolCall] = None
    evidence: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(CamelModel):
    message: str
    context_node_ids: list[str] = Field(default_factory=list)


class AskRequest(CamelModel):
    question: str
    top_k: int = 5
