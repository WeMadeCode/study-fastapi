import asyncio

from openai.types.chat import ChatCompletionMessageParam

from app.services.llm.client import llm_client


async def main():
    message: list[ChatCompletionMessageParam] = [
        {"role": "system", "content": "你是一个简洁的中文编程助教,回答不超过三句话。"},
        # {"role": "user", "content": "用一句话解释什么是 API。"},
        {"role": "user", "content": "我最喜欢的数字是 7,记住它。"},
        {"role": "assistant", "content": "好的,你最喜欢 7。"},
        {"role": "user", "content": "我最喜欢什么数字?"},
    ]

    reply = await llm_client.chat(message)

    print(reply)


if __name__ == "__main__":
    asyncio.run(main())
