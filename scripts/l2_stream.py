import asyncio

from openai.types.chat import ChatCompletionMessageParam

from app.services.llm.client import llm_client

message: list[ChatCompletionMessageParam] = [
    {"role": "user", "content": "从 1 数到 10，每个数字单独一行"},
]


async def main():

    async for piece in llm_client.stream_chat(message):
        print(piece, end="", flush=True)

    print()


if __name__ == "__main__":
    asyncio.run(main())
