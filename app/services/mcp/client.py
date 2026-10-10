"""MCP host 侧 client:管理一个 stdio server 子进程,提供握手/发现/调用。

协议实现来自 l7_mcp_client 练习,正式化为类:生命周期由 main.py 的 lifespan 驱动,
工具清单与调用函数经 tools.register_mcp_tools 注入聚合层——本模块不感知 agent。
"""

import asyncio
import json
import shlex
from asyncio import StreamReader, StreamWriter
from asyncio.subprocess import Process
from typing import NotRequired, TypedDict, cast

from pydantic import BaseModel

from app.config.config import settings


class JsonRpcRequest(TypedDict):
    jsonrpc: str
    method: str
    id: NotRequired[int]
    params: NotRequired[dict[str, object]]


class JsonRpcResponse(TypedDict, total=False):
    jsonrpc: str
    id: int | str
    result: dict[str, object]
    error: dict[str, object]


class McpToolMeta(BaseModel):
    """MCP tools/list 返回的工具简历。inputSchema 保持协议原形,聚合层负责转成 OpenAI 格式。"""

    name: str
    description: str = ""
    inputSchema: dict[str, object]


class ToolsListResult(BaseModel):
    """tools/list 的 result 形状——要迭代它,就先建形状,不在 object 上裸操作。"""

    tools: list[McpToolMeta]


class ContentBlock(BaseModel):
    type: str = ""
    text: str = ""


class CallResult(BaseModel):
    isError: bool = False
    content: list[ContentBlock]


class McpClient:
    def __init__(self, name: str, cmd: list[str]):
        self._name = name
        self._cmd = cmd
        self._proc: Process | None = None
        self._writer: StreamWriter | None = None
        self._reader: StreamReader | None = None
        self._request_id = 0

    async def start(self):
        """拉起子进程 + 三连(握手/通知/发现),返回工具清单。"""
        if not self._cmd:
            raise RuntimeError(f"[mcp:{self._name}] 未配置 server 启动命令")
        proc = await asyncio.create_subprocess_exec(
            *self._cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=None,  # server 日志直通终端
        )
        if proc.stdin is None or proc.stdout is None:
            raise RuntimeError(f"[mcp:{self._name}] stdio 管道未建立")
        self._proc = proc
        self._writer = proc.stdin
        self._reader = proc.stdout

        self._request_id += 1
        await self._send(
            {
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "study-fastapi-host", "version": "0.1"},
                },
            }
        )
        resp = await self._recv(self._request_id)
        print(f"[mcp:{self._name}] 握手完成,协议版本 {resp.get('result', {}).get('protocolVersion')}")

        await self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})

        self._request_id += 1
        await self._send({"jsonrpc": "2.0", "id": self._request_id, "method": "tools/list", "params": {}})
        listing = ToolsListResult.model_validate((await self._recv(self._request_id)).get("result", {}))
        tools = listing.tools
        print(f"[mcp:{self._name}] 发现 {len(tools)} 个工具: {[t.name for t in tools]}")
        return tools

    async def call_tool(self, name: str, arguments: dict[str, object]):
        """执行工具,返回 content 文本块的拼接。

        isError 不单独处理:失败时 text 本身就是 error JSON(server 的 error-as-data
        原样透传),直接喂回模型——合同贯通,模型看到 error 能自我纠正。
        """
        if self._writer is None:
            raise RuntimeError(f"[mcp:{self._name}] 未连接,先 start()")
        print(f"[mcp:{self._name}] tools/call → {name}")
        self._request_id += 1
        await self._send(
            {
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )
        result = CallResult.model_validate((await self._recv(self._request_id)).get("result", {}))
        return "".join(block.text for block in result.content)

    async def stop(self):
        if self._proc is not None:
            self._proc.terminate()
            self._proc = None
            self._writer = None
            self._reader = None
            print(f"[mcp:{self._name}] 已关闭")

    async def _send(self, msg: JsonRpcRequest):
        if self._writer is None:
            raise RuntimeError(f"[mcp:{self._name}] 未连接,先 start()")
        self._writer.write((json.dumps(msg, ensure_ascii=False) + "\n").encode())
        await self._writer.drain()

    async def _recv(self, request_id: int):
        if self._reader is None:
            raise RuntimeError(f"[mcp:{self._name}] 未连接,先 start()")
        while True:
            line = await self._reader.readline()
            if not line:
                raise RuntimeError(f"[mcp:{self._name}] server 关闭了 stdout")
            msg = json.loads(line)
            if not isinstance(msg, dict):
                continue
            resp = cast(JsonRpcResponse, msg)
            if resp.get("id") == request_id:
                return resp
            print(f"[mcp:{self._name}] 跳过通知: {resp.get('method', resp)}")


mcp_client = McpClient("kb", shlex.split(settings.mcp_kb_server_cmd))
