"""L7.2 练习:裸写 MCP server——stdio + JSON-RPC,把 search_knowledge_base 提供给任何 MCP host。

工具 = 业务(检索),协议 = 皮:agentic loop 是进程内的皮,MCP server 是跨进程的皮,
两张皮下是同一个 execute_tool。协议行为是 l7_mcp_client 的镜像:读一行 → 分发 → 写一行。
"""

import asyncio
import json
import sys
from typing import TypedDict, cast

from app.services.tools import TOOLS_SCHEMA, ToolParam, execute_tool


class Incoming(TypedDict, total=False):
    """client → server 的消息。与 l7_mcp_client.JsonRpcRequest 同形——跨脚本不共享合同,靠协议保证。"""

    jsonrpc: str
    id: int | str
    method: str
    params: dict[str, object]


PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "study-kb-server", "version": "0.1"}


def send(msg: dict[str, object]):
    """往 stdout 写一行协议消息。flush 是生死线:管道模式下 stdout 全缓冲,不 flush client 永远等不到。"""
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _to_mcp_tool(entry: ToolParam) -> dict[str, object]:
    """OpenAI function 格式 → MCP tool 格式。schema 单一事实源仍是 TOOLS_SCHEMA,这里只做形状转换。"""
    fn = entry["function"]
    return {"name": fn["name"], "description": fn["description"], "inputSchema": fn["parameters"]}


async def call_search_kb(arguments: dict[str, object]) -> dict[str, object]:
    """执行 search_knowledge_base,实现零重复——直接调 tools.py 的 execute_tool。

    execute_tool 的合同是「JSON 字符串进,JSON 字符串出」(模型的 tool_call.arguments
    本来就是字符串);MCP 的 arguments 是结构化 dict——两个协议的翻译就是这一对 dumps/loads。
    error-as-data 的 {"error": ...} 翻译成 MCP 的 isError: true。
    """
    raw = await execute_tool("search_knowledge_base", json.dumps(arguments, ensure_ascii=False))
    payload = json.loads(raw)
    is_error = isinstance(payload, dict) and "error" in payload
    return {"content": [{"type": "text", "text": raw}], "isError": is_error}


async def handle(line: str) -> None:
    """读一行 → 分发 → 写响应。三种结局:回 result / 回 error / 通知静默。"""
    msg = json.loads(line)
    if not isinstance(msg, dict):
        return
    req = cast(Incoming, msg)

    request_id = req.get("id")
    if request_id is None:
        return  # 通知(如 notifications/initialized):单向,只收不回

    method = req.get("method")
    if method == "initialize":
        send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": SERVER_INFO,
                },
            }
        )
    elif method == "tools/list":
        tools = [_to_mcp_tool(t) for t in TOOLS_SCHEMA if t["function"]["name"] == "search_knowledge_base"]
        send({"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}})
    elif method == "tools/call":
        params = req.get("params", {})
        name = params.get("name")
        arguments = params.get("arguments", {})
        if name == "search_knowledge_base" and isinstance(arguments, dict):
            result = await call_search_kb(cast(dict[str, object], arguments))
            send({"jsonrpc": "2.0", "id": request_id, "result": result})
        else:
            send({"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": f"未知工具: {name}"}})
    else:
        # 协议级错误走 JSON-RPC error;-32601 是标准「Method not found」
        send({"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method not found: {method}"}})


async def main():
    while True:
        line = await asyncio.to_thread(sys.stdin.readline)  # stdin 是阻塞句柄,丢线程池读,不卡事件循环
        if not line:  # EOF:client 关了 stdin → server 退出
            break
        line = line.strip()
        if line:
            await handle(line)


if __name__ == "__main__":
    asyncio.run(main())
