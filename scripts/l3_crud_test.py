import asyncio

from sqlalchemy import func, select

from app.crud import chats
from app.database.pgsql_client import AsyncSessionLocal
from app.models import messages


async def main():
    async with AsyncSessionLocal() as db:
        # 1. 建立会话
        conversation = await chats.create_conversation(db)
        print("会话：", conversation.id, conversation.title)

        # 2. 两条消息
        await chats.append_message(db, conversation, "user", "我最喜欢的数字是 7")
        await chats.append_message(db, conversation, "assistant", "好的，你最喜欢 7")

        # 3. 装载历史，验证顺序
        history = await chats.get_conversation_messages(db, conversation)
        print("历史：", [(m.role, m.content) for m in history])

        # 4. 删会话，消息一并消失
        await db.delete(conversation)
        await db.commit()
        count = await db.scalar(
            select(func.count())
            .select_from(messages.Message)
            .where(messages.Message.conversation_id == conversation.id)
        )

        print("删除后剩余消息数:", count)


if __name__ == "__main__":
    asyncio.run(main())
