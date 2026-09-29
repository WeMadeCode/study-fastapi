"""Agent 编排层:模型 ↔ 工具的 agentic loop。

边界约定:openai 的 import 只允许出现在 services/llm/ 与本文件,
routers/crud/models/schemas 一律不沾 SDK 类型。
"""

from typing import cast

from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam

from app.services.llm.client import llm_client
from app.services.tools import TOOLS_SCHEMA, execute_tool

MAX_ROUNDS = 8

_TOOL_PARAMS = cast(list[ChatCompletionToolParam], TOOLS_SCHEMA)


async def run_agent(user_message: str):
    """跑一个完整的 agentic loop,返回最终文本回答。

    自主性归模型(调什么、调几轮),控制权在我们(工具集、轮数上限、error-as-data)。
    """
    messages: list[ChatCompletionMessageParam] = [{"role": "user", "content": user_message}]

    for _ in range(1, MAX_ROUNDS + 1):
        response = await llm_client.chat_with_tools(messages, _TOOL_PARAMS)
        assistant_msg = response.choices[0].message

        # 唯一出口：没有申请单 = 最终回答
        if response.choices[0].finish_reason != "tool_calls" or assistant_msg.tool_calls is None:
            content = assistant_msg.content
            if content is None:
                raise RuntimeError("模型最终未返回文本内容")
            return content

        messages.append(cast(ChatCompletionMessageParam, assistant_msg))

        for tool_call in assistant_msg.tool_calls:
            if tool_call.type != "function":
                raise RuntimeError("收到 custom 工具调用,暂不支持")

            result = execute_tool(tool_call.function.name, tool_call.function.arguments)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )
    raise RuntimeError(f"Agent 达到最大轮数 {MAX_ROUNDS} 仍未收敛")
