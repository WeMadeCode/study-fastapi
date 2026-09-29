import asyncio
import json
from typing import cast

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam

from app.config.config import settings

client = AsyncOpenAI(api_key=settings.ark_api_key, base_url=settings.ark_base_url)

tools: list[ChatCompletionToolParam] = [
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "获取指定城市当前的实时天气",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名,如:北京"},
                },
                "required": ["city"],
            },
        },
    }
]


def get_current_weather(city: str):
    print("我被调用了！！！")
    return json.dumps({"city": city, "weather": "晴", "temperature": 0}, ensure_ascii=False)


async def main():
    messages: list[ChatCompletionMessageParam] = [{"role": "user", "content": "北京今天天气怎么样?适合跑步吗?"}]

    # 第一轮：模型决定“调研申请”
    first = await client.chat.completions.create(model=settings.ark_model, messages=messages, tools=tools)

    assistant_msg = first.choices[0].message
    print("第一轮 finish_reason:", first.choices[0].finish_reason)
    print("第一轮 tool_calls:", assistant_msg.tool_calls)

    # 收窄 1:模型可以不调用工具(tool_calls 是 Optional)
    if first.choices[0].finish_reason != "tool_calls" or assistant_msg.tool_calls is None:
        print("模型没调用工具，直接回答：", assistant_msg.content)
        return

    messages.append(cast(ChatCompletionMessageParam, assistant_msg))

    tool_call = assistant_msg.tool_calls[0]

    # 收窄 2:tool_calls 元素是联合类型(function | custom),用判别字段分派
    if tool_call.type != "function":
        raise RuntimeError("本课只支持 function 工具,收到了 custom 工具调用")
    args = json.loads(tool_call.function.arguments)
    result = get_current_weather(args["city"])

    messages.append(
        {
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": result,
        }
    )

    # 第二轮：模型消化结果，说人话
    second = await client.chat.completions.create(model=settings.ark_model, messages=messages)
    print("第二轮 finish_reason:", second.choices[0].finish_reason)
    print("最终回答:", second.choices[0].message.content)


if __name__ == "__main__":
    asyncio.run(main())
