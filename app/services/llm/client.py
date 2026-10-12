from typing import Literal, TypedDict

import httpx
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam
from pydantic import BaseModel

from app.config.config import settings
from app.schemas.chats import StoredToolCall


class TextEvent(TypedDict):
    """流式事件:文本增量。"""

    type: Literal["text"]
    text: str


class ToolCallsEvent(TypedDict):
    """流式事件:工具申请单(流收完时一次性发出)。形状即 StoredToolCall,可直接入轨迹。"""

    type: Literal["tool_calls"]
    tool_calls: list[StoredToolCall]


class EmbeddingData(BaseModel):
    embedding: list[float]
    object: str


class EmbeddingResponse(BaseModel):
    data: EmbeddingData


class LLMClient:
    def __init__(self):
        self._client = AsyncOpenAI(
            api_key=settings.ark_api_key,
            base_url=settings.ark_base_url,
            timeout=settings.ark_timeout,
        )

        self._model = settings.ark_model

    async def chat(self, messages: list[ChatCompletionMessageParam]):
        response = await self._client.chat.completions.create(model=self._model, messages=messages)

        content = response.choices[0].message.content
        if content is None:
            raise RuntimeError("模型未返回文本内容")
        return content

    async def stream_chat(self, messages: list[ChatCompletionMessageParam]):
        stream = await self._client.chat.completions.create(model=self._model, messages=messages, stream=True)

        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta is not None:
                yield delta

    async def stream_chat_with_tools(
        self, messages: list[ChatCompletionMessageParam], tools: list[ChatCompletionToolParam]
    ):
        stream = await self._client.chat.completions.create(
            model=self._model, messages=messages, tools=tools, stream=True
        )
        acc: dict[int, dict[str, str]] = {}

        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield TextEvent(type="text", text=delta.content)
            for tc in delta.tool_calls or []:
                slot = acc.setdefault(tc.index, {"id": "", "name": "", "arguments": ""})
                if tc.id:
                    slot["id"] = tc.id
                if tc.function and tc.function.name:
                    slot["name"] += tc.function.name
                if tc.function and tc.function.arguments:
                    slot["arguments"] += tc.function.arguments

        if acc:
            yield ToolCallsEvent(
                type="tool_calls",
                tool_calls=[
                    StoredToolCall(
                        id=slot["id"],
                        type="function",
                        function={"name": slot["name"], "arguments": slot["arguments"]},
                    )
                    for slot in (acc[i] for i in sorted(acc))
                ],
            )

    async def chat_with_tools(
        self,
        messages: list[ChatCompletionMessageParam],
        tools: list[ChatCompletionToolParam],
    ):
        return await self._client.chat.completions.create(model=self._model, messages=messages, tools=tools)

    async def embed(self, texts: list[str]):
        """向量化"""
        url = f"{settings.ark_base_url.rstrip('/')}/embeddings/multimodal"
        headers = {"Authorization": f"Bearer {settings.ark_api_key}"}
        vectors: list[list[float]] = []

        async with httpx.AsyncClient(timeout=settings.ark_timeout) as http:
            for t in texts:
                body: dict[str, object] = {
                    "model": settings.ark_embedding_model,
                    "input": [{"type": "text", "text": t}],
                    "dimensions": 1024,
                    "encoding_format": "float",
                }
                resp = await http.post(url, json=body, headers=headers)
                resp.raise_for_status()
                parsed = EmbeddingResponse.model_validate(resp.json())
                vectors.append(parsed.data.embedding)

        return vectors


llm_client = LLMClient()
