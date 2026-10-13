import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.crud import chats
from app.database.pgsql_client import AsyncSessionLocal
from app.database.redis_client import redis_client
from app.schemas.chats import ChatCreate, MessageDict
from app.services.agent import build_llm_messages, run_agent, run_agent_stream, trim_history
from app.services.llm.client import llm_client

# 锁 key 模板:业务前缀 chat: + 语义 busy: + 会话 id。
# 前缀分级是为了 keys/排查时一眼看出归属;TTL 是崩溃兜底,取远大于 agent 最坏执行时长
_BUSY_KEY = "chat:busy:{conversation_id}"
_BUSY_TTL_SECONDS = 600

_llm_semaphore = asyncio.Semaphore(8)


async def claim_conversation(conversation_id: int):
    ok = await redis_client.set(_BUSY_KEY.format(conversation_id=conversation_id), "1", nx=True, ex=_BUSY_TTL_SECONDS)

    if not ok:
        raise HTTPException(status_code=409, detail="该会话正在处理中,请等上一轮完成")


async def release_conversation(conversation_id: int):
    await redis_client.delete(_BUSY_KEY.format(conversation_id=conversation_id))


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

    await claim_conversation(conversation_id)

    # 2. 流阶段
    async def event_generator():
        try:
            # ① 短会话:存 user + 装载历史,立刻归还连接
            async with AsyncSessionLocal() as db:
                conversation = await chats.get_conversation(db, conversation_id)
                if conversation is None:
                    raise HTTPException(status_code=404, detail="会话不存在")
                await chats.append_message(db, conversation, "user", payload.message)
                rows = await chats.get_conversation_messages(db, conversation)
            history = trim_history([chats.message_to_dict(m) for m in rows])
            llm_messages = build_llm_messages(history)
            yield f"data: {json.dumps({'conversation_id': conversation_id}, ensure_ascii=False)}\n\n"

            # ② LLM 流式:全程零 DB 连接
            reply_parts: list[str] = []

            async with _llm_semaphore:
                async for delta in llm_client.stream_chat(llm_messages):
                    reply_parts.append(delta)
                    data = json.dumps({"content": delta}, ensure_ascii=False)
                    yield f"data: {data}\n\n"

            # ③ 回收:新短会话写 assistant(A1 那行的新家)
            async with AsyncSessionLocal() as db:
                conversation = await chats.get_conversation(db, conversation_id)
                if conversation is None:
                    raise HTTPException(status_code=404, detail="会话不存在")
                await chats.append_message(db, conversation, "assistant", "".join(reply_parts))
        finally:
            await release_conversation(conversation_id)

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
    await claim_conversation(conversation_id)

    try:
        # 2. 装载历史：存user -> 读全量会话
        async with AsyncSessionLocal() as db:
            conversation = await chats.get_conversation(db, conversation_id)
            if conversation is None:
                raise HTTPException(status_code=404, detail="会话不存在")
            await chats.append_message(db, conversation, "user", payload.message)
            rows = await chats.get_conversation_messages(db, conversation)

        history = trim_history([chats.message_to_dict(m) for m in rows])
        llm_messages = build_llm_messages(history)
        async with _llm_semaphore:
            reply, new_stored = await run_agent(llm_messages)

        # 3. loop 收敛后一次性写轨迹
        async with AsyncSessionLocal() as db:
            conversation = await chats.get_conversation(db, conversation_id)
            if conversation is None:
                raise HTTPException(status_code=404, detail="会话不存在")
            await chats.append_messages(db, conversation, new_stored)
    finally:
        await release_conversation(conversation_id)

    return {"reply": reply, "conversation_id": conversation_id}


@router.post("/agent/stream")
async def agent_stream(payload: ChatCreate):
    # 1. body 阶段:与 /agent 同款
    async with AsyncSessionLocal() as db:
        if payload.conversation_id is None:
            conversation = await chats.create_conversation(db)
        else:
            conversation = await chats.get_conversation(db, payload.conversation_id)
            if conversation is None:
                raise HTTPException(status_code=404, detail="会话不存在")
    conversation_id = conversation.id

    await claim_conversation(conversation_id)

    async def event_generator():
        try:
            # 2. 存 user → 读全量 → 跑流式 loop
            async with AsyncSessionLocal() as db:
                conversation = await chats.get_conversation(db, conversation_id)
                if conversation is None:
                    raise HTTPException(status_code=404, detail="会话不存在")
                await chats.append_message(db, conversation, "user", payload.message)
                rows = await chats.get_conversation_messages(db, conversation)

            history = trim_history([chats.message_to_dict(m) for m in rows])
            llm_messages = build_llm_messages(history)
            new_stored: list[MessageDict] = []
            async with _llm_semaphore:
                async for event in run_agent_stream(llm_messages, new_stored):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

            # 3. 轨迹收敛后单事务写入——方案 B 不变
            async with AsyncSessionLocal() as db:
                conversation = await chats.get_conversation(db, conversation_id)
                if conversation is None:
                    raise HTTPException(status_code=404, detail="会话不存在")
                await chats.append_messages(db, conversation, new_stored)
        finally:
            await release_conversation(conversation_id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
