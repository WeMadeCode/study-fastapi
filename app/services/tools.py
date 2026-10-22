"""工具注册表:模型可调用的"手"。

边界约定:本模块不 import openai。LLM 协议类型止步于 services/llm,
这里只认纯字符串协议(工具名 + arguments JSON)。

工具合同(泛化后):async fn(args: dict[str, object]) -> str
execute_tool 只负责查表/解 JSON/按 schema 验必填,参数解包下放给每个工具。
"""

import asyncio
import json
import sys
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Literal, TypedDict, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.database.pgsql_client import AsyncSessionLocal
from app.services.cli import run_cli
from app.services.llm.client import llm_client
from app.services.mcp.client import McpToolMeta  # 顶部 import 区
from app.services.rag import retriever
from app.services.skills import SkillCard, build_index, load_skill, read_reference, scan_skills

_skill_cards: dict[str, SkillCard] = {}


def initialize_skills(root: Path):
    global _skill_cards
    _skill_cards = scan_skills(root)


def get_skill_index():
    return build_index(_skill_cards)


async def _load_skill(args: dict[str, object]):
    name = args.get("name")
    if not isinstance(name, str):
        return json.dumps({"error": "name 必须是字符串"}, ensure_ascii=False)
    try:
        body = await asyncio.to_thread(load_skill, _skill_cards, name)
        return json.dumps({"name": name, "body": body}, ensure_ascii=False)
    except (ValueError, OSError) as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


async def _read_skill_reference(args: dict[str, object]):
    name, relative = args.get("name"), args.get("relative")
    if not isinstance(name, str) or not isinstance(relative, str):
        return json.dumps({"error": "name/relative 必须是字符串"}, ensure_ascii=False)
    try:
        body = await asyncio.to_thread(read_reference, _skill_cards, name, relative)
        return json.dumps({"name": name, "reference": relative, "body": body}, ensure_ascii=False)
    except (ValueError, OSError) as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


class TextStatsResult(BaseModel):
    # stdout 是外部数据：既检查 JSON，也检查字段类型与范围。
    model_config = ConfigDict(strict=True, extra="forbid")
    characters: int = Field(ge=0)
    pid: int = Field(gt=0)


async def _text_stats(args: dict[str, object]):
    text = args.get("text")
    if not isinstance(text, str):
        return json.dumps({"error": "text 必须是字符串"}, ensure_ascii=False)
    if len(text) > 1000:
        return json.dumps({"error": "本实验最多接受 1000 个码点"}, ensure_ascii=False)

    # tools.py 位于 app/services/；parents[2] 是项目根目录。
    root = Path(__file__).resolve().parents[2]
    script = root / "scripts" / "text_stats_cli.py"
    # 模型只提供 text；程序、脚本位置与超时由宿主固定。
    result = await run_cli([sys.executable, str(script), "--", text], root)
    if result.error is not None:
        return json.dumps({"error": result.error}, ensure_ascii=False)
    if result.returncode != 0:
        return json.dumps(
            {"error": "CLI 非零退出", "returncode": result.returncode, "stderr": result.stderr},
            ensure_ascii=False,
        )
    if result.truncated:
        return json.dumps({"error": "CLI 输出被截断，不能作为完整结果"}, ensure_ascii=False)
    try:
        parsed = TextStatsResult.model_validate_json(result.stdout)
    except ValidationError:
        return json.dumps({"error": "CLI 输出不符合统计结果合同"}, ensure_ascii=False)
    return parsed.model_dump_json()


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
TOOL_REGISTRY["text_stats"] = _text_stats
TOOLS_SCHEMA.append(
    {
        "type": "function",
        "function": {
            "name": "text_stats",
            "description": "通过独立 CLI 精确统计原文的 Unicode 码点数，最多 1000 个码点。",
            "parameters": {
                "type": "object",
                "properties": {"text": {"type": "string", "description": "原文，不要改写"}},
                "required": ["text"],
            },
        },
    }
)

# 加在现有 TOOL_REGISTRY 与 TOOLS_SCHEMA 初始化之后。
TOOL_REGISTRY.update({"load_skill": _load_skill, "read_skill_reference": _read_skill_reference})
TOOLS_SCHEMA.extend(
    [
        {
            "type": "function",
            "function": {
                "name": "load_skill",
                "description": "读取可用 Skill 索引中的操作手册。先加载手册再按步骤执行。",
                "parameters": {
                    "type": "object",
                    "properties": {"name": {"type": "string", "description": "索引中的 Skill 名称"}},
                    "required": ["name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_skill_reference",
                "description": "读取已发现 Skill 的 references 文档。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Skill 名称"},
                        "relative": {"type": "string", "description": "如 references/types.md"},
                    },
                    "required": ["name", "relative"],
                },
            },
        },
    ]
)
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
