"""L7 练习:裸写 MCP client——stdio 子进程 + JSON-RPC 三连(握手/发现/调用)。

类型策略:
- 入参:TypedDict 形状合同,id/params 用 NotRequired 表达"通知可缺"
- 出参:recv 出口 isinstance + cast 收窄一次;深层 result 交给 pydantic 建形状
  (EmbeddingResponse 同款手法:协议响应是 Any,取数据前必须建形状)
- 参数全部标注,返回类型省略(能推导则不写)
"""

import asyncio
import json
from asyncio import StreamReader, StreamWriter
from typing import NotRequired, TypedDict, cast

from pydantic import BaseModel


class JsonRpcRequest(TypedDict):
    """client → server 的请求/通知。通知缺 id,部分方法缺 params——NotRequired 表达。"""

    jsonrpc: str
    method: str
    id: NotRequired[int]
    params: NotRequired[dict[str, object]]


class JsonRpcResponse(TypedDict, total=False):
    """server → client 的响应。result/error 互斥,通知(无 id)也混在 stdout 里。"""

    jsonrpc: str
    id: int | str
    result: dict[str, object]
    error: dict[str, object]


class InitResult(BaseModel):
    protocolVersion: str
    serverInfo: dict[str, str]
    capabilities: dict[str, object]


class McpTool(BaseModel):
    name: str
    description: str = ""
    inputSchema: dict[str, object]


class ToolsListResult(BaseModel):
    tools: list[McpTool]


class ContentBlock(BaseModel):
    """工具结果的块。pydantic 默认忽略多余字段——图片块也能过,type 不认识的留空。"""

    type: str = ""
    text: str = ""


class CallResult(BaseModel):
    isError: bool = False
    content: list[ContentBlock]


SERVER_CMD = ["uvx", "mcp-server-time", "--local-timezone=Asia/Shanghai"]


async def send(writer: StreamWriter, msg: JsonRpcRequest):
    """发一条消息:单行 JSON + 换行。"""
    writer.write((json.dumps(msg, ensure_ascii=False) + "\n").encode())
    await writer.drain()


async def recv(reader: StreamReader, request_id: int):
    """按 id 认领响应:server 可能插播通知,对不上的跳过。"""
    while True:
        line = await reader.readline()
        if not line:
            raise RuntimeError("server 关闭了 stdout,去 stderr 找崩溃日志")
        msg = json.loads(line)
        if not isinstance(msg, dict):
            continue
        resp = cast(JsonRpcResponse, msg)
        if resp.get("id") == request_id:
            return resp
        print(f"  [通知/非目标消息,跳过] {resp}")


async def connect():
    """拉起 server 子进程,返回 (进程, 写管道, 读管道)。

    传了 PIPE 则 stdin/stdout 必非 None,但类型上是 Optional
    """
    proc = await asyncio.create_subprocess_exec(
        *SERVER_CMD,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=None,  # stdout 是协议专线,日志只能走 stderr,直通终端
    )

    if proc.stdin is None or proc.stdout is None:
        raise RuntimeError("stdio 管道未建立")

    return proc, proc.stdin, proc.stdout


async def recv_result(reader: StreamReader, request_id: int):
    """按 id 认领响应,并保证拿到 result。

    JSON-RPC 的 result/error 互斥:成功才有 result,失败只有 error。
    练习脚本不处理 error 分支,遇到直接抛,把错误亮出来。
    """
    resp = await recv(reader, request_id)
    result = resp.get("result")
    if result is None:
        raise RuntimeError(f"请求 {request_id} 收到错误响应:{resp.get('error', resp)}")
    return result


async def main() -> None:
    proc, writer, reader = await connect()

    # 1. initialize:报名字 + 期望协议版本
    await send(
        writer,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "study-mcp", "version": "0.1"},
            },
        },
    )
    init = InitResult.model_validate(await recv_result(reader, 1))
    print("协商后协议版本:", init.protocolVersion)
    print("server:", init.serverInfo)
    print("capabilities:", init.capabilities)

    # 2. 握手完成通知:无 id、无响应,发完就走
    await send(writer, {"jsonrpc": "2.0", "method": "notifications/initialized"})

    # 3. tools/list:工具简历——对照你手写的 TOOLS_SCHEMA,结构同构
    await send(writer, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    listing = ToolsListResult.model_validate(await recv_result(reader, 2))
    for tool in listing.tools:
        print(f"- {tool.name}: {tool.description}")
        print(f"  参数: {json.dumps(tool.inputSchema, ensure_ascii=False)}")

    # 4. tools/call:真调一次
    await send(
        writer,
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "get_current_time", "arguments": {"timezone": "Asia/Shanghai"}},
        },
    )
    call = CallResult.model_validate(await recv_result(reader, 3))
    print("isError:", call.isError)
    for block in call.content:
        print(f"  [{block.type}] {block.text}")

    proc.terminate()


if __name__ == "__main__":
    asyncio.run(main())
