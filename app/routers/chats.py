import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from openai.types.chat import (
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageParam,
    ChatCompletionUserMessageParam,
)

from app.crud import chats
from app.database.pgsql_client import AsyncSessionLocal
from app.schemas.chats import ChatCreate
from app.services.agent import run_agent
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
            llm_messages: list[ChatCompletionMessageParam] = []

            for m in history:
                if m.role == "user" and m.content is not None:
                    llm_messages.append(ChatCompletionUserMessageParam(role="user", content=m.content))
                elif m.role == "assistant" and m.content is not None:
                    llm_messages.append(ChatCompletionAssistantMessageParam(role="assistant", content=m.content))

            yield f"data: {json.dumps({'conversation_id': conversation.id}, ensure_ascii=False)}\n\n"

            reply_parts: list[str] = []
            async for delta in llm_client.stream_chat(llm_messages):
                reply_parts.append(delta)
                data = json.dumps({"content": delta}, ensure_ascii=False)
                yield f"data: {data}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/agent")
async def agent_chat(payload: ChatCreate):
    replay = await run_agent(payload.message)
    return {"reply": replay}
