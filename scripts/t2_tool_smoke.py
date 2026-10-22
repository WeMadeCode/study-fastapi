import asyncio
import json
import os

from app.services.tools import TextStatsResult, execute_tool


async def main():
    for text in ("你好世界", "", "--help", "你好; echo unsafe"):
        raw = await execute_tool("text_stats", json.dumps({"text": text}, ensure_ascii=False))
        result = TextStatsResult.model_validate_json(raw)
        assert result.characters == len(text)
        assert result.pid != os.getpid()  # 业务结果来自另一个进程。
        print("原文:", repr(text), "宿主 PID:", os.getpid(), "CLI 结果:", raw)
    for args in ({}, {"text": 123}, {"text": "x" * 1001}):
        raw = await execute_tool("text_stats", json.dumps(args))
        assert "error" in raw
        print("预期错误:", raw)


if __name__ == "__main__":
    asyncio.run(main())