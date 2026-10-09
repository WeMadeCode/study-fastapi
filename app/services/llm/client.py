import httpx
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam
from pydantic import BaseModel

from app.config.config import settings


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
