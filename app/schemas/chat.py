from pydantic import BaseModel


class ChatCreate(BaseModel):
    message: str
