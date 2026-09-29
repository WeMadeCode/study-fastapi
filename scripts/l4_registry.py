import asyncio
from typing import cast

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam

from app.config.config import settings
from app.services.tools import TOOLS_SCHEMA, execute_tool

client = AsyncOpenAI(api_key=settings.ark_api_key, base_url=settings.ark_base_url)


async def main():
    messages: list[ChatCompletionMessageParam] = [{"role": "user", "content": "北京现在几点了"}]

    tool_params = cast(list[ChatCompletionToolParam], TOOLS_SCHEMA)

    first = await client.chat.completions.create(model=settings.ark_model, messages=messages, tools=tool_params)
    assistant_msg = first.choices[0].message
    print("第一轮 finish_reason:", first.choices[0].finish_reason)
    print("第一轮 tool_calls:", assistant_msg.tool_calls)

    if first.choices[0].finish_reason != "tool_calls" or assistant_msg.tool_calls is None:
        print("模型没调用工具,直接回答:", assistant_msg.content)
        return

    messages.append(cast(ChatCompletionMessageParam, assistant_msg))

    # for 循环处理"这一批"申请单——可能是 1 张,也可能是 2 张!
    for tool_call in assistant_msg.tool_calls:
        if tool_call.type != "function":
            raise RuntimeError("收到 custom 工具调用,本课不支持")

        print("执行:", tool_call.function.name, tool_call.function.arguments)
        result = execute_tool(tool_call.function.name, tool_call.function.arguments)

        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            }
        )

    second = await client.chat.completions.create(model=settings.ark_model, messages=messages)
    print("第二轮 finish_reason:", second.choices[0].finish_reason)

    print("最终回答:", second.choices[0].message.content)


if __name__ == "__main__":
    asyncio.run(main())
