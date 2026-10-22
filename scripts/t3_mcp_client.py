import asyncio
import json
import sys
from asyncio.subprocess import Process
from contextlib import suppress
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RpcError(BaseModel):
    code: int
    message: str


class Envelope(BaseModel):
    model_config = ConfigDict(strict=True)
    jsonrpc: Literal["2.0"]
    id: int | str | None = None
    method: str | None = None
    result: dict[str, object] | None = None
    error: RpcError | None = None


class InitResult(BaseModel):
    protocolVersion: str
    capabilities: dict[str, dict[str, object]]


class TextBlock(BaseModel):
    type: Literal["text"]  # 本练习只支持文本,遇到其他类型明确验证失败。
    text: str


class CallResult(BaseModel):
    content: list[TextBlock]
    isError: bool = False


class ResourceContent(BaseModel):
    uri: str
    text: str


class ReadResult(BaseModel):
    contents: list[ResourceContent]


class PromptMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: TextBlock


class PromptResult(BaseModel):
    messages: list[PromptMessage]


class ToolMeta(BaseModel):
    name: str
    inputSchema: dict[str, object]


class ToolList(BaseModel):
    tools: list[ToolMeta]
    nextCursor: str | None = None


class ResourceMeta(BaseModel):
    uri: str
    name: str


class ResourceList(BaseModel):
    resources: list[ResourceMeta]
    nextCursor: str | None = None


class PromptMeta(BaseModel):
    name: str
    arguments: list[dict[str, object]] = Field(default_factory=list[dict[str, object]])


class PromptList(BaseModel):
    prompts: list[PromptMeta]
    nextCursor: str | None = None


class RemoteError(RuntimeError):
    def __init__(self, error: RpcError):
        super().__init__(f"{error.code}: {error.message}")
        self.code = error.code


class LabClient:
    def __init__(self):
        self.proc: Process | None = None
        self.next_id = 0
        self.lock = asyncio.Lock()
        self.capabilities: dict[str, dict[str, object]] = {}

    async def start(self, server: Path):
        self.proc = await asyncio.create_subprocess_exec(
            sys.executable,
            str(server),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=None,
        )
        try:
            raw = await self.request(
                "initialize",
                {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "t3-host", "version": "0.1"},
                },
            )
            init = InitResult.model_validate(raw)
            if init.protocolVersion != "2025-06-18":
                raise RuntimeError("本实验只实现 2025-06-18,拒绝未知版本")
            self.capabilities = init.capabilities
            await self.send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        except BaseException:
            await self.close()
            raise

    async def send(self, payload: dict[str, object]):
        if self.proc is None or self.proc.stdin is None:
            raise RuntimeError("未连接")
        self.proc.stdin.write((json.dumps(payload, ensure_ascii=False) + "\n").encode())
        await self.proc.stdin.drain()

    async def request(self, method: str, params: dict[str, object]):
        capability = method.split("/", 1)[0]
        if capability in {"tools", "resources", "prompts"} and capability not in self.capabilities:
            raise RuntimeError(f"server 未声明 {capability}")
        # 必须覆盖“取 id → 写 → 读”全程,只锁写入无法防止两个 readline 争抢。
        async with self.lock:
            if self.proc is None or self.proc.stdout is None:
                raise RuntimeError("未连接")
            self.next_id += 1
            request_id = self.next_id
            try:
                async with asyncio.timeout(2):
                    await self.send({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
                    while True:
                        line = await self.proc.stdout.readline()
                        if not line:
                            raise RuntimeError("server 提前关闭 stdout")
                        response = Envelope.model_validate_json(line)
                        if "id" not in response.model_fields_set:
                            if not response.method:
                                raise RuntimeError("非法通知")
                            # 最小版只观察通知;不能在这里悄悄实现 server→client 请求。
                            print("通知:", response.method)
                            continue
                        if response.id != request_id:
                            raise RuntimeError("响应 id 不匹配,串行连接已失去同步")
                        if (response.result is None) == (response.error is None):
                            raise RuntimeError("result/error 必须恰好有一个")
                        break
            except BaseException:
                # 超时/取消后关闭连接,不能把迟到响应误分给下一次请求。
                await self.close()
                raise
            if response.error is not None:
                raise RemoteError(response.error)
            assert response.result is not None
            return response.result

    async def close(self):
        proc = self.proc
        self.proc = None
        self.capabilities = {}
        if proc is None:
            return
        if proc.stdin is not None:
            proc.stdin.close()  # stdio 生命周期:EOF 先给 server 正常退出机会。
        try:
            await asyncio.wait_for(proc.wait(), 0.5)
        except TimeoutError:
            if proc.returncode is None:
                with suppress(ProcessLookupError):
                    proc.kill()
            await proc.wait()


async def main():
    client = LabClient()
    try:
        await client.start(Path(__file__).with_name("t3_mcp_server.py"))
        tools = ToolList.model_validate(await client.request("tools/list", {}))
        resources = ResourceList.model_validate(await client.request("resources/list", {}))
        prompts = PromptList.model_validate(await client.request("prompts/list", {}))
        assert tools.nextCursor is resources.nextCursor is prompts.nextCursor is None
        assert tools.tools[0].name == "search_knowledge_base"
        uri = resources.resources[0].uri
        read = ReadResult.model_validate(await client.request("resources/read", {"uri": uri}))
        prompt = PromptResult.model_validate(
            await client.request(
                "prompts/get",
                {
                    "name": prompts.prompts[0].name,
                    "arguments": {"question": "怎样判断证据?", "result": read.contents[0].text},
                },
            )
        )
        assert prompt.messages[0].role == "user"
        succeeded = CallResult.model_validate(
            await client.request(
                "tools/call",
                {"name": "search_knowledge_base", "arguments": {"question": "怎样判断证据?"}},
            )
        )
        assert not succeeded.isError and succeeded.content[0].text
        failed = CallResult.model_validate(
            await client.request(
                "tools/call",
                {
                    "name": "search_knowledge_base",
                    "arguments": {"question": "模拟失败"},
                },
            )
        )
        assert failed.isError
        error_cases: list[tuple[str, dict[str, object], int]] = [
            ("resources/read", {"uri": "study://missing"}, -32002),
            ("prompts/get", {"name": "review_retrieval", "arguments": {}}, -32602),
        ]
        for method, params, expected in error_cases:
            try:
                await client.request(method, params)
            except RemoteError as exc:
                assert exc.code == expected
            else:
                raise AssertionError("应该返回协议错误")
        # gather 并发进入,锁保证底层按一次完整 RPC 串行完成。
        results = await asyncio.gather(*[client.request("resources/read", {"uri": uri}) for _ in range(3)])
        assert len(results) == 3
        print("T3:三原语、业务错误、协议错误、并发进入串行完成均通过")
        print("准备交给模型的 prompt:", prompt.messages[0].content.text)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
