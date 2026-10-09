
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import conversations, messages
from app.schemas.chats import MessageDict, StoredToolCall


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


"""
keyword-only: * 之后的参数必须用关键字传（tool_call_id="call_1"）
为什么这么设计——tool_call_id 和 tool_calls 是罕见字段，
如果按位置传，append_message(db, conv, "tool", "call_1", ...) 
这种错位手滑编译器查不出来，关键字传参一眼就能看出传错了。
"""


async def append_message(
    db: AsyncSession,
    conversation: conversations.Conversation,
    role: str,
    content: str | None = None,
    *,
    tool_call_id: str | None = None,
    tool_calls: list[StoredToolCall] | None = None,
):
    message = messages.Message(
        role=role, content=content, conversation=conversation, tool_call_id=tool_call_id, tool_calls=tool_calls
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)
    return message

async def append_messages(db: AsyncSession, conversation: conversations.Conversation, msgs: list[MessageDict]):
    """整条轨迹一个事务写入。

    轨迹 = assistant(tool_calls) → tool → … → assistant(最终回答)的完整序列,
    必须原子生效:写到一半挂掉会留下"有申请单没下文"的半截轨迹,
    下次装载喂给 API 直接 400。所以循环里只 add,循环外一次 commit。
    """
    db.add_all(
        messages.Message(
            role=m["role"],
            content=m["content"],
            conversation=conversation,
            tool_call_id=m["tool_call_id"],
            tool_calls=m["tool_calls"],
        )
        for m in msgs
    )
    await db.commit()

async def get_conversation_messages(db: AsyncSession, conversation: conversations.Conversation):
    stmt = (
        select(messages.Message)
        .where(messages.Message.conversation_id == conversation.id)
        .order_by(messages.Message.id)
    )
    rows = await db.scalars(stmt)
    return list(rows)


def message_to_dict(m: messages.Message) -> MessageDict:
    return {
        "role": m.role, 
        "content": m.content, 
        "tool_call_id": m.tool_call_id,
        "tool_calls": m.tool_calls
    }
