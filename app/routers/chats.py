import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.crud import chats
from app.database.pgsql_client import AsyncSessionLocal
from app.schemas.chats import ChatCreate
from app.services.agent import build_llm_messages, run_agent
from app.services.llm.client import llm_client

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/stream")
async def stream_chat(payload: ChatCreate):

    # 1. body 阶段：短会话，此时还没发出任何响应头，可以正常抛404
    async with AsyncSessionLocal() as db:
        if payload.conversation_id is None:
            conversation = await chats.create_conversation(db)
        else:
            conversation = await chats.get_conversation(db, payload.conversation_id)
            if conversation is None:
                raise HTTPException(status_code=404, detail="会话不存在")
    conversation_id = conversation.id

    # 2. 流阶段：独立的新会话，生命周期与响应流等长
    async def event_generator():
        async with AsyncSessionLocal() as db:
            conversation = await chats.get_conversation(db, conversation_id)
            if conversation is None:
                raise HTTPException(status_code=404, detail="会话不存在")
            await chats.append_message(db, conversation, "user", payload.message)
            history = await chats.get_conversation_messages(db, conversation)
            llm_messages = build_llm_messages([chats.message_to_dict(m) for m in history])
            yield f"data: {json.dumps({'conversation_id': conversation.id}, ensure_ascii=False)}\n\n"

            reply_parts: list[str] = []
            async for delta in llm_client.stream_chat(llm_messages):
                reply_parts.append(delta)
                data = json.dumps({"content": delta}, ensure_ascii=False)
                yield f"data: {data}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/agent")
async def agent_chat(payload: ChatCreate) -> dict[str, str | int]:
    # 1. body 阶段：新建/查询会话（与/stream 同款）
    async with AsyncSessionLocal() as db:
        if payload.conversation_id is None:
            conversation = await chats.create_conversation(db)
        else:
            conversation = await chats.get_conversation(db, payload.conversation_id)
            if conversation is None:
                raise HTTPException(status_code=404, detail="会话不存在")
    conversation_id = conversation.id

    # 2. 装载历史：存user -> 读全量会话
    async with AsyncSessionLocal() as db:
        conversation = await chats.get_conversation(db, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="会话不存在")
        await chats.append_message(db, conversation, "user", payload.message)
        history = await chats.get_conversation_messages(db, conversation)

    llm_messages = build_llm_messages([chats.message_to_dict(m) for m in history])
    reply, new_stored = await run_agent(llm_messages)

    # 3. loop 收敛后一次性写轨迹
    async with AsyncSessionLocal() as db:
        conversation = await chats.get_conversation(db, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="会话不存在")
        for m in new_stored:
            await chats.append_message(
                db, conversation, m["role"], m["content"], tool_call_id=m["tool_call_id"], tool_calls=m["tool_calls"]
            )

    return {"reply": reply, "conversation_id": conversation_id}
