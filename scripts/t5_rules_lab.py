"""T5：对比同一个 Agent 加载 Rules 前后的回答。"""

import asyncio
from pathlib import Path

from app.services.agent import build_llm_messages, run_agent

RULES_FILE = Path(__file__).with_name("t5_rules.md")
QUESTION = "什么是 Agent？"


async def ask(use_rules: bool):
    # 每次创建新上下文，保留项目已有的 Skill system 消息。
    messages = build_llm_messages([])
    rules = RULES_FILE.read_text(encoding="utf-8") if use_rules else ""
    if rules:
        messages.insert(0, {"role": "system", "content": rules})

    messages.append({"role": "user", "content": QUESTION})
    print("\n=== 加载 Rules ===" if use_rules else "\n=== 不加载 Rules ===")
    print("本次额外规则：", rules or "无")
    answer, _ = await run_agent(messages)
    print(answer)


async def main():
    await ask(False)
    await ask(True)


if __name__ == "__main__":
    asyncio.run(main())
