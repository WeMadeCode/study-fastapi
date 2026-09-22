from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

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


llm_client = LLMClient()
