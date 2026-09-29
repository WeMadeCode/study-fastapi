import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from openai.types.chat import ChatCompletionMessageParam

from app.schemas.chat import ChatCreate
from app.services.llm.client import llm_client

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/stream")
async def stream_chat(payload: ChatCreate):
    async def event_generator():
        messages: list[ChatCompletionMessageParam] = [{"role": "user", "content": payload.message}]
        async for delta in llm_client.stream_chat(messages):
            data = json.dumps({"content": delta}, ensure_ascii=False)
            yield f"data: {data}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
