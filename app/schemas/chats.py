from typing import TypedDict

from pydantic import BaseModel


class ChatCreate(BaseModel):
    message: str
    conversation_id: int | None = None


class StoredToolCall(TypedDict):
    """tool_calls JSONB 列的单元素形状：与SDK param同构，列装时可以直接cast 还原。"""

    id: str
    type: str
    function: dict[str, str]


class MessageDict(TypedDict):
    role: str
    content: str | None
    tool_call_id: str | None
    tool_calls: list[StoredToolCall] | None
