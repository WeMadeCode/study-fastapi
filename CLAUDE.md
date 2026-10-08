# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目性质: 教学项目,不要替用户写代码

这是用户系统性学习 FastAPI 的项目。**最重要的规则:绝不写/改/删项目源码文件**，即使是在帮用户修报错时,也只诊断、讲解、给代码片段,所有操作由用户亲手完成(用户明确说过「我在学习不要帮我做」)。

- 全程中文交流。讲解与操作分离:小段代码 + 重点讲解 + 验证命令 + 下一步预告。
- 报错分析:带用户读 traceback(从下往上、只看自己文件的帧),让用户自己改。
- 用户常见手滑:拼写错误(contet/emial/DATATBASE_URL)、重写文件时丢掉之前修过的内容、跳过验证步骤——提醒自查,不要直接动手改。
- 注意项目架构规范、代码规范，需要按照官方标准。
- 重点注意Python的类型安全问题。

## 架构

app 布局 + uv,Python 3.13。请求链路:`main.py` 注册 routers → routers/(接口层,只做校验和 404/409 转换)→ crud/(所有数据库操作,接收 AsyncSession)→ models / schemas。

- **异步全链路**:`database/pgsql_client.py` 的 `create_async_engine`(psycopg 异步驱动)+ `async_sessionmaker(expire_on_commit=False)`;`get_async_db` 作为依赖注入 AsyncSession,routers/crud 均为 async。
- **Base 基类**:`pgsql_client.py` 里的 `Base` 自带 `create_at`/`update_at` 时间戳列,所有模型自动继承。
- **模型注册**:新增模型必须在 `models/__init__.py` 显式导入,否则 Alembic autogenerate 检测不到;`alembic/env.py` 从 `.env` 读 `DATABASE_URL` 并挂 `Base.metadata`。
- **schemas 约定**:Pydantic v2,`*Create`(入参)/`*Update`(可选字段,crud 用 `exclude_unset=True`)/`*Public`(出参,`from_attributes=True`)三件套。
- **配置**:`config/config.py` 用 pydantic-settings 读根目录 `.env`(`.env.example` 是模板,`.env` 不进仓库);`DATABASE_URL` 为空时启动即报错。
- **Docker 拓扑**:compose 起 4 个服务——app(容器内 `uv run uvicorn`)、db(postgres:18,容器名 study-pgsql)、mysql(备用练习)、redis;app 的 `DATABASE_URL` 指向 `db` 服务,带 healthcheck + `depends_on: service_healthy`。
- **Agent 分层(services/)**:`services/llm/client.py` 封装 SDK(AsyncOpenAI 单例,读 settings 的 ark_* 配置)、`services/tools.py` 工具注册表(TOOL_REGISTRY/TOOLS_SCHEMA/execute_tool,error-as-data:失败返回 error JSON 不抛异常)、`services/agent.py` agentic loop(`run_agent` 收完整 messages,返回最终文本 + 存储格式轨迹)。**边界约定:openai 的 import 只允许出现在 `services/llm/` 与 `services/agent.py`**,routers/crud/models/schemas 一律不沾 SDK 类型;历史装载统一走 `agent.py` 的 `build_llm_messages`。
- **会话模型**:conversations/messages 两表;messages 的 role 是 String(20),带 tool_call_id / tool_calls(JSONB)列。采用方案 B 全量存 agent 轨迹(含中间 tool 消息,loop 收敛后一次性写入)。crud 的 `StoredToolCall` TypedDict 是 tool_calls JSONB 的形状合同,写入侧(`_tool_call_to_stored`)与装载侧(`build_llm_messages` 的 cast)共同遵守。
- **类型规范(用户拍板,不要按 mypy strict 要求)**:哲学"能推导则不写"——参数必须标(推不出 = 隐式 Any 失明),返回类型省略;ruff select 含 ANN、ignore ANN2;mypy 仅对 `app.services.llm.*` 和 `scripts.*` 开 overrides(check_untyped_defs / disallow_any_generics / no_implicit_optional / warn_return_any / warn_unused_ignores),其余模块默认检查。

## 当前状态(2026-10-08)

- 2026-09-20 起主线转向 Agent 开发:目标类 GPT/豆包网页版聊天**后端**,教学路线 L1 调模型 API → L2 SSE 流式 → L3 会话持久化 → L4 function calling → L5 agentic loop,裸写优先,不引入 LangChain 等框架(阶段 2 结束前);每课产物练习脚本在 scripts/。
- **L1~L5 已结业(2026-10-08)**。现有接口:`POST /chat/stream`(SSE + 会话持久化)、`POST /chat/agent`(agentic loop,MAX_ROUNDS=8,方案 B 全量持久化:tool_calls/tool 中间消息入 messages 表,loop 收敛后一次性写入);验收达成:第二轮对话能复述工具调用过程。
- 可选加固(未做):agent 轨迹写库改单事务一次 commit(append_message 现在每条 commit);/agent 流式化。
- news 模块(models: news/category/favorite/history,crud/news.py 已有)接口仍搁置,规划为 L6 RAG 的知识库素材。
- **下一课 L6:RAG(pgvector)**——需把 compose 的 db 镜像换成 pgvector/pgvector 对应版本并启用扩展;embedding 走火山方舟 API。之后 L7 MCP。
- pytest/JWT 仍暂缓;旧 pydantic[email,emial] 手滑已修(现为 pydantic[email])。
