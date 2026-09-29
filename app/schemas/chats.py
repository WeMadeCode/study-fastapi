from pydantic import BaseModel


class ChatCreate(BaseModel):
    message: str
    conversation_id: int | None = None
