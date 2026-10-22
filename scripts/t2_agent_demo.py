import asyncio
import os

from app.services.agent import build_llm_messages, run_agent
from app.services.tools import TextStatsResult


async def main():
    messages = build_llm_messages([])
    messages.append({
        "role": "user",
        "content": "请调用 text_stats 工具统计原文‘你好世界’的 Unicode 码点数，原文不含引号。",
    })
    answer, trace = await run_agent(messages)
    print("宿主 PID:", os.getpid())
    call_ids: set[str] = set()
    verified = False
    for message in trace:
        print(message)  # 展示 assistant 申请单、tool 结果和最终回答。
        for call in message.get("tool_calls") or []:
            if call["function"]["name"] == "text_stats":
                call_ids.add(call["id"])
        if message["role"] == "tool" and message.get("tool_call_id") in call_ids:
            result = TextStatsResult.model_validate_json(message.get("content") or "")
            assert result.characters == 4
            assert result.pid != os.getpid()
            verified = True
    assert verified, "没有找到匹配的 CLI 工具结果；答对数字也不算调用成功"
    print("最终回答:", answer)


if __name__ == "__main__":
    asyncio.run(main())