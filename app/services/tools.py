"""工具注册表:模型可调用的"手"。

边界约定:本模块不 import openai。LLM 协议类型止步于 services/llm,
这里只认纯字符串协议(工具名 + arguments JSON)。

工具合同(泛化后):async fn(args: dict[str, object]) -> str
execute_tool 只负责查表/解 JSON/按 schema 验必填,参数解包下放给每个工具。
"""

import json
from collections.abc import Awaitable, Callable
from typing import Literal, TypedDict, cast

from app.database.pgsql_client import AsyncSessionLocal
from app.services.llm.client import llm_client
from app.services.mcp.client import McpToolMeta  # 顶部 import 区
from app.services.rag import retriever


async def _get_current_weather(args: dict[str, object]):
    city = args["city"]  # 必填参数已由 execute_tool 按 schema 校验过
    return json.dumps({"city": city, "weather": "晴", "temperature": 24}, ensure_ascii=False)


async def _get_city_time(args: dict[str, object]):
    city = args["city"]
    return json.dumps({"city": city, "time": "2026-09-29 14:30"}, ensure_ascii=False)


async def _search_knowledge_base(args: dict[str, object]):
    question = args["question"]
    if not isinstance(question, str):
        return json.dumps({"error": "question 必须是字符串"}, ensure_ascii=False)

    query_vec = (await llm_client.embed([question]))[0]

    async with AsyncSessionLocal() as db:
        hits = await retriever.search_similar_chunks(db, query_vec)

    return json.dumps(
        {
            "result": [
                {"source": title, "content": content, "distance": round(dist, 4)} for title, content, dist in hits
            ]
        },
        ensure_ascii=False,
    )


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
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": """检索站内知识库(新闻/资料)。遇到知识类、事实类问题时先调用它再回答;
            返回 results 为空数组表示知识库中没有相关内容""",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "要检索的问题或关键词,尽量完整保留用户原意"},
                },
                "required": ["question"],
            },
        },
    },
]


# 名字 → 真正干活的函数。模型只报名字,执行靠这张表
ToolFunc = Callable[[dict[str, object]], Awaitable[str]]
# MCP 调用通道:分发器模式——一个函数管全部工具,name 是参数
McpCallFn = Callable[[str, dict[str, object]], Awaitable[str]]
TOOL_REGISTRY: dict[str, ToolFunc] = {
    "get_current_weather": _get_current_weather,
    "get_city_time": _get_city_time,
    "search_knowledge_base": _search_knowledge_base,
}


# MCP 外接工具:name → 简历。启动时由 lifespan 注入,同名覆盖内置(外接视为最新版本,内置兜底)
_mcp_schemas: dict[str, McpToolMeta] = {}
# MCP 调用通道:与 ToolFunc 同形(合同同形),所以执行侧可以统一
_mcp_call: McpCallFn | None = None


def register_mcp_tools(tools: list[McpToolMeta], call_fn: McpCallFn):
    """注入 MCP 工具清单与调用通道(main 的 lifespan 调用)。"""
    global _mcp_call
    for tool in tools:
        _mcp_schemas[tool.name] = tool
    _mcp_call = call_fn


def get_all_tool_schemas() -> list[ToolParam]:
    """给模型的工具简历全量:内置为底,MCP 同名覆盖、独有的追加。"""
    schemas = {t["function"]["name"]: t for t in TOOLS_SCHEMA}
    for name, tool in _mcp_schemas.items():
        # cast 的诚实性:inputSchema 来自自家 server(它就是从 TOOLS_SCHEMA 转换的),同形有保证
        schemas[name] = cast(
            ToolParam,
            {
                "type": "function",
                "function": {"name": tool.name, "description": tool.description, "parameters": tool.inputSchema},
            },
        )
    return list(schemas.values())


def _validate_required(name: str, args: dict[str, object]):
    """按 TOOLS_SCHEMA 校验必填参数。

    schema 是唯一事实源:给模型看的是它,给执行层验参数的也是它,改一处两边同步。
    """
    for tool in TOOLS_SCHEMA:
        if tool["function"]["name"] == name:
            missing = [key for key in tool["function"]["parameters"]["required"] if key not in args]
            if missing:
                return json.dumps({"error": f"缺少必填参数: {', '.join(missing)}"}, ensure_ascii=False)
            return None
    return None


async def execute_tool(name: str, arguments_json: str):
    try:
        args = json.loads(arguments_json)
    except json.JSONDecodeError:
        return json.dumps({"error": "arguments 不是合法 JSON"}, ensure_ascii=False)

    if not isinstance(args, dict):
        return json.dumps({"error": "arguments 必须是 dict 对象"}, ensure_ascii=False)

    args = cast(dict[str, object], args)

    error = _validate_required(name, args)
    if error is not None:
        return error

    if name in _mcp_schemas:
        if _mcp_call is None:
            return json.dumps({"error": "MCP 调用通道未注册"}, ensure_ascii=False)
        return await _mcp_call(name, args)

    fn = TOOL_REGISTRY.get(name)
    if fn is None:
        return json.dumps({"error": f"未知工具: {name}"}, ensure_ascii=False)
    return await fn(args)
