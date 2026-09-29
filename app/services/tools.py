"""工具注册表:模型可调用的"手"。

边界约定:本模块不 import openai。LLM 协议类型止步于 services/llm,
这里只认纯字符串协议(工具名 + arguments JSON)。
"""

import json
from collections.abc import Callable
from typing import Literal, TypedDict


def _get_current_weather(city: str):
    return json.dumps({"city": city, "weather": "晴", "temperature": 24}, ensure_ascii=False)


def _get_city_time(city: str):
    return json.dumps({"city": city, "time": "2026-09-29 14:30"}, ensure_ascii=False)


class _ParamsSchema(TypedDict):
    type: Literal["object"]
    properties: dict[str, dict[str, str]]
    required: list[str]


class _FunctionDef(TypedDict):
    name: str
    description: str
    parameters: _ParamsSchema


class ToolParam(TypedDict):
    type: Literal["function"]
    function: _FunctionDef


# 给模型看的"简历",JSON Schema 形状
TOOLS_SCHEMA: list[ToolParam] = [
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
    },
    {
        "type": "function",
        "function": {
            "name": "get_city_time",
            "description": "获取指定城市当前的时间",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名,如:北京"},
                },
                "required": ["city"],
            },
        },
    },
]


# 名字 → 真正干活的函数。模型只报名字,执行靠这张表
TOOL_REGISTRY: dict[str, Callable[[str], str]] = {
    "get_current_weather": _get_current_weather,
    "get_city_time": _get_city_time,
}


def execute_tool(name: str, arguments_json: str):
    """执行一张"申请单":查注册表 → 解参数 → 调函数。

    关键设计:任何失败都返回 error JSON,而不是抛异常——
    因为工具结果是要喂回模型的,错误信息也是信息(模型看到 error 能自我纠正)。
    """
    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        return json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False)

    try:
        args = json.loads(arguments_json)
    except json.JSONDecodeError:
        return json.dumps({"error": "arguments 不是合法 JSON"}, ensure_ascii=False)

    try:
        city = args["city"]
    except KeyError:
        return json.dumps({"error": "缺少必填参数：city"}, ensure_ascii=False)

    return fn(city)
