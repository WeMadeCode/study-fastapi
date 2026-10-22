import json
import sys

from pydantic import BaseModel, ConfigDict, Field, ValidationError

VERSION = "2025-06-18"
URI = "study://kb/usage-guide"
TEXT = "检索片段只是证据,需要核对相关性。"


class Request(BaseModel):
    model_config = ConfigDict(strict=True)
    jsonrpc: str
    id: int | str | None = None
    method: str
    params: dict[str, object] = Field(default_factory=dict)


class ToolArgs(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    question: str


class PromptArgs(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    question: str
    result: str


def send(message: dict[str, object]):
    print(json.dumps(message, ensure_ascii=False), flush=True)


def dispatch(req: Request):
    result: dict[str, object]  # 异构字典需要类型提示,返回类型由此推导。
    if req.method == "initialize":
        result = {
            "protocolVersion": VERSION,
            "serverInfo": {"name": "t3-lab", "version": "0.1"},
            "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
        }
        return result
    if req.method == "tools/list":
        result = {
            "tools": [
                {
                    "name": "search_knowledge_base",
                    "description": "离线固定检索样本",
                    "inputSchema": ToolArgs.model_json_schema(),
                }
            ]
        }
        return result
    if req.method == "tools/call":
        if req.params.get("name") != "search_knowledge_base":
            raise ValueError("未知工具")
        args = ToolArgs.model_validate(req.params.get("arguments", {}))
        failed = args.question == "模拟失败"
        text = json.dumps({"error": "模拟检索失败"} if failed else {"result": [{"content": TEXT}]}, ensure_ascii=False)
        result = {"content": [{"type": "text", "text": text}], "isError": failed}
        return result
    if req.method == "resources/list":
        result = {"resources": [{"uri": URI, "name": "kb-guide", "mimeType": "text/plain"}]}
        return result
    if req.method == "resources/read":
        if req.params.get("uri") != URI:
            raise FileNotFoundError("资源不存在")
        result = {"contents": [{"uri": URI, "mimeType": "text/plain", "text": TEXT}]}
        return result
    if req.method == "prompts/list":
        result = {
            "prompts": [
                {
                    "name": "review_retrieval",
                    "description": "分析检索证据",
                    "arguments": [{"name": "question", "required": True}, {"name": "result", "required": True}],
                }
            ]
        }
        return result
    if req.method == "prompts/get":
        if req.params.get("name") != "review_retrieval":
            raise ValueError("未知提示词")
        prompt_args = PromptArgs.model_validate(req.params.get("arguments", {}))
        result = {
            "messages": [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": f"问题:{prompt_args.question}\n证据:{prompt_args.result}\n请解释证据是否足够。",
                    },
                }
            ]
        }
        return result
    raise NotImplementedError("未知方法")


def main():
    initialized = False
    ready = False
    for line in sys.stdin:
        try:
            raw = json.loads(line)
            req = Request.model_validate(raw)
            if req.jsonrpc != "2.0":
                raise ValueError("jsonrpc 必须为 2.0")
        except json.JSONDecodeError:
            send({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "JSON 解析失败"}})
            continue
        except (ValidationError, ValueError):
            send({"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "非法请求"}})
            continue
        if req.id is None:
            if initialized and req.method == "notifications/initialized":
                ready = True
            continue  # 通知不回复;本实验不支持客户端发来的其他通知。
        try:
            if req.method != "initialize" and not ready:
                raise ValueError("尚未完成初始化")
            result = dispatch(req)
            if req.method == "initialize":
                initialized = True
            send({"jsonrpc": "2.0", "id": req.id, "result": result})
        except (ValueError, FileNotFoundError, NotImplementedError) as exc:
            code = (
                -32002
                if isinstance(exc, FileNotFoundError)
                else -32601
                if isinstance(exc, NotImplementedError)
                else -32602
            )
            send({"jsonrpc": "2.0", "id": req.id, "error": {"code": code, "message": str(exc)}})


if __name__ == "__main__":
    main()
