from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import conversations, messages


async def create_conversation(db: AsyncSession, title: str | None = None):
    conversation = conversations.Conversation(title=title)
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def get_conversation(db: AsyncSession, conversation_id: int):
    result = await db.execute(
        select(conversations.Conversation).where(conversations.Conversation.id == conversation_id)
    )
    return result.scalar_one_or_none()


async def append_message(db: AsyncSession, conversation: conversations.Conversation, role: str, content: str):
    message = messages.Message(role=role, content=content, conversation=conversation)
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message


async def get_conversation_messages(db: AsyncSession, conversation: conversations.Conversation):
    stmt = (
        select(messages.Message)
        .where(messages.Message.conversation_id == conversation.id)
        .order_by(messages.Message.id)
    )
    rows = await db.scalars(stmt)
    return list(rows)
