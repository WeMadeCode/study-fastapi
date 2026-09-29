from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam

from app.config.config import settings


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


llm_client = LLMClient()
