import asyncio
import json
from typing import cast

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam

from app.config.config import settings
from app.services.tools import TOOLS_SCHEMA, execute_tool

client = AsyncOpenAI(api_key=settings.ark_api_key, base_url=settings.ark_base_url)

MAX_ROUNDS = 8  # 轮数上限:真实 Agent 的保命线,防模型死循环烧钱


async def main():
    messages: list[ChatCompletionMessageParam] = [
        {"role": "user", "content": "北京现在几点了？天气怎么样？"},
    ]
    # 协议海关:TOOLS_SCHEMA 推断为 dict[str, object],跨进 SDK 边界需要一次 cast
    tool_params = cast(list[ChatCompletionToolParam], TOOLS_SCHEMA)

    for round_no in range(1, MAX_ROUNDS + 1):
        response = await client.chat.completions.create(model=settings.ark_model, messages=messages, tools=tool_params)
        assistant_msg = response.choices[0].message
        print(f"── 第 {round_no} 轮 finish_reason: {response.choices[0].finish_reason}")

        # 唯一出口:模型没递申请单 = 它认为信息够了,给出最终回答
        if response.choices[0].finish_reason != "tool_calls" or assistant_msg.tool_calls is None:
            print("最终回答:", assistant_msg.content)
            return

        # 中间轮的 assistant 消息(带 tool_calls)也是历史,必须原样入列
        messages.append(cast(ChatCompletionMessageParam, assistant_msg))

        # 内层 for:处理"这一批"申请单(1 张或多张)
        for tool_call in assistant_msg.tool_calls:
            if tool_call.type != "function":
                raise RuntimeError("收到 custom 工具调用,本课不支持")

            print("  执行:", tool_call.function.name, tool_call.function.arguments)
            result = execute_tool(tool_call.function.name, tool_call.function.arguments)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )

    print(f"达到最大轮数 {MAX_ROUNDS},强制中止——防模型死循环烧钱")


if __name__ == "__main__":
    asyncio.run(main())
