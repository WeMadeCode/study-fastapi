"""Agent 编排层:模型 ↔ 工具的 agentic loop。

边界约定:openai 的 import 只允许出现在 services/llm/ 与本文件,
routers/crud/models/schemas 一律不沾 SDK 类型。
"""

from typing import cast

from openai.types.chat import (
    ChatCompletionMessageFunctionToolCallParam,
    ChatCompletionMessageParam,
    ChatCompletionMessageToolCallUnion,
    ChatCompletionToolParam,
)

from app.schemas.chats import MessageDict, StoredToolCall
from app.services.llm.client import llm_client
from app.services.tools import execute_tool, get_all_tool_schemas

MAX_ROUNDS = 8


def _tool_call_to_stored(tool_calls: list[ChatCompletionMessageToolCallUnion]) -> list[StoredToolCall]:
    """SDK 工具申请单 → JSONB 存储格式。id/type/name/arguments 逐字段拆平,不传对象。"""
    stored: list[StoredToolCall] = []

    for tc in tool_calls:
        if tc.type != "function":
            raise RuntimeError("收到 custom 工具调用,暂不支持")
        stored.append(
            {"id": tc.id, "type": tc.type, "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
        )
    return stored


async def run_agent(messages: list[ChatCompletionMessageParam]):
    """跑一个完整的 agentic loop,返回最终文本回答。

    入参：路由层装载好的完整prompt（本函数视为工作副本，会向其追加）。
    返回：最终文本，本轮新增消息的存储格式轨迹 -- 轨迹由路由写库。
    """
    new_stored: list[MessageDict] = []

    for _ in range(1, MAX_ROUNDS + 1):
        tool_params = cast(list[ChatCompletionToolParam], get_all_tool_schemas())
        response = await llm_client.chat_with_tools(messages, tool_params)
        assistant_msg = response.choices[0].message

        # 唯一出口:没有申请单 = 最终回答
        if response.choices[0].finish_reason != "tool_calls" or assistant_msg.tool_calls is None:
            content = assistant_msg.content
            if content is None:
                raise RuntimeError("模型最终未返回文本内容")
            new_stored.append({"role": "assistant", "content": content, "tool_call_id": None, "tool_calls": None})
            return content, new_stored

        messages.append(cast(ChatCompletionMessageParam, assistant_msg))
        new_stored.append(
            {
                "role": "assistant",
                "content": assistant_msg.content,
                "tool_call_id": None,
                "tool_calls": _tool_call_to_stored(assistant_msg.tool_calls),
            }
        )

        for tool_call in assistant_msg.tool_calls:
            if tool_call.type != "function":
                raise RuntimeError("收到 custom 工具调用,暂不支持")

            result = await execute_tool(tool_call.function.name, tool_call.function.arguments)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )
            new_stored.append({"role": "tool", "content": result, "tool_call_id": tool_call.id, "tool_calls": None})

    raise RuntimeError(f"Agent 达到最大轮数 {MAX_ROUNDS} 仍未收敛")


def build_llm_messages(history: list[MessageDict]) -> list[ChatCompletionMessageParam]:
    """存储格式 → SDK 消息。user/assistant/tool 三种角色逐条还原。"""
    llm_messages: list[ChatCompletionMessageParam] = []

    for m in history:
        if m["role"] == "user":
            # 存储侧保证非空,or "" 只为把 str | None 收窄成 str
            llm_messages.append({"role": "user", "content": m["content"] or ""})
        elif m["role"] == "tool":
            llm_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": m["tool_call_id"] or "",
                    "content": m["content"] or "",
                }
            )
        elif m["tool_calls"]:
            llm_messages.append(
                {
                    "role": "assistant",
                    "content": m["content"],
                    "tool_calls": cast(list[ChatCompletionMessageFunctionToolCallParam], m["tool_calls"]),
                }
            )
        elif m["content"] is not None:
            llm_messages.append({"role": "assistant", "content": m["content"]})

    return llm_messages
