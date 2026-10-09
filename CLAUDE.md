# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目性质: 教学项目,不要替用户写代码

这是用户系统性学习 FastAPI 的项目。**最重要的规则:绝不写/改/删项目源码文件**，即使是在帮用户修报错时,也只诊断、讲解、给代码片段,所有操作由用户亲手完成(用户明确说过「我在学习不要帮我做」)。

- 全程中文交流。讲解与操作分离:小段代码 + 重点讲解 + 验证命令 + 下一步预告。
- 报错分析:带用户读 traceback(从下往上、只看自己文件的帧),让用户自己改。
- 用户常见手滑:拼写错误(contet/emial/DATATBASE_URL)、重写文件时丢掉之前修过的内容、跳过验证步骤——提醒自查,不要直接动手改。
- 注意项目架构规范、代码规范，需要按照官方标准。
- 重点注意 Python 的类型安全问题(详见下方「类型规范」节)。


## 架构

app 布局 + uv,Python 3.13。请求链路:`main.py` 注册 routers → routers/(接口层,只做校验和 404/409 转换)→ crud/(所有数据库操作,接收 AsyncSession)→ models / schemas。

- **异步全链路**:`database/pgsql_client.py` 的 `create_async_engine`(psycopg 异步驱动)+ `async_sessionmaker(expire_on_commit=False)`;`get_async_db` 作为依赖注入 AsyncSession,routers/crud 均为 async。
- **Base 基类**:`pgsql_client.py` 里的 `Base` 自带 `create_at`/`update_at` 时间戳列,所有模型自动继承。
- **模型注册**:新增模型必须在 `models/__init__.py` 显式导入,否则 Alembic autogenerate 检测不到;`alembic/env.py` 从 `.env` 读 `DATABASE_URL` 并挂 `Base.metadata`。
- **schemas 约定**:Pydantic v2,`*Create`(入参)/`*Update`(可选字段,crud 用 `exclude_unset=True`)/`*Public`(出参,`from_attributes=True`)三件套。
- **配置**:`config/config.py` 用 pydantic-settings 读根目录 `.env`(`.env.example` 是模板,`.env` 不进仓库);`DATABASE_URL` 为空时启动即报错。
- **Docker 拓扑**:compose 实际启用 db(pgvector/pgvector:0.8.7-pg18,容器名 study-pgsql,pgvector 扩展经迁移启用)+ redis;app/mysql 服务已注释,本地 `uv run` 直跑。
- **Agent 分层(services/)**:`services/llm/client.py` 封装 SDK(AsyncOpenAI 单例,读 settings 的 ark_* 配置;`embed()` httpx 裸调方舟 embedding)、`services/tools.py` 工具注册表(TOOL_REGISTRY/TOOLS_SCHEMA/execute_tool,error-as-data:失败返回 error JSON 不抛异常;已注册 get_current_weather / get_city_time / search_knowledge_base)、`services/agent.py` agentic loop(`run_agent` 收完整 messages,返回最终文本 + 存储格式轨迹)。**边界约定:openai 的 import 只允许出现在 `services/llm/` 与 `services/agent.py`**,routers/crud/models/schemas 一律不沾 SDK 类型;历史装载统一走 `agent.py` 的 `build_llm_messages`。
- **RAG 层(services/rag/)**:`chunker.split_text` 切块;`retriever.search_similar_chunks` 收 AsyncSession、只读查询(余弦 top-k + MAX_DISTANCE 阈值过滤;session 生命周期归调用方,约定同 crud)。EmbeddingChunk 表挂 news_id/chunk_index/content/embedding(vector 1024 维)。**embed 实测合同:方舟 `/embeddings/multimodal` 一次请求永远只返回一个向量(input 数组 = 一个样本的多模态片段,多条文本会融合成一个向量),循环单条请求是正确用法**。scripts/l6_* 为各环节练习脚本。
- **会话模型**:conversations/messages 两表;messages 的 role 是 String(20),带 tool_call_id / tool_calls(JSONB)列。采用方案 B 全量存 agent 轨迹。crud 的 `StoredToolCall` TypedDict 是 tool_calls JSONB 的形状合同,写入侧(`_tool_call_to_stored`)与装载侧(`build_llm_messages` 的 cast)共同遵守。轨迹写入用 `append_messages`(复数,整条轨迹一个事务一次 commit,防半截轨迹喂 API 400);`append_message`(单数)留给单条消息——事务边界 = 语义单元。

## 类型规范(重点,用户拍板,不要按 mypy strict 要求)

哲学:**「能推导则不写」——参数必须标,返回类型省略**。

- **参数必须标注**:推不出的类型(子进程返回值、外部回调、json.loads 结果)不标 = 隐式 Any 失明。泛型必须参数化——`dict` / `list` 裸写会被 disallow_any_generics 抓;异构字典字面量被推导退化时,显式 `dict[str, object]`。
- **返回类型省略**:ruff select 含 ANN、ignore ANN2;mypy 仅对 `app.services.llm.*` 和 `scripts.*` 开 overrides(check_untyped_defs / disallow_any_generics / no_implicit_optional / warn_return_any / warn_unused_ignores),其余模块默认检查。
- **Any 必须在边界收窄,禁止链式裸取**:json.loads / HTTP 响应 / 协议消息等 Any 入口——协议/存储层用 `isinstance 防御 + cast` 到 TypedDict 合同,数据层用 pydantic 模型建形状(EmbeddingResponse 模式);`resp["a"]["b"]["c"]` 式链式 Any 取值是违规写法。
- **TypedDict = 形状合同**:StoredToolCall / MessageDict / JsonRpcRequest 同款;同一形状的可选键用 `NotRequired` 表达;`total=False` 的键取值用 `.get()`,不裸下标;合同变更要同步改全所有使用侧。
- **cast 的诚实性**:cast 只收窄「写入侧合同能保证」的形状,不是骗过检查器的工具。

## 当前状态(2026-10-09)

- 2026-09-20 起主线转向 Agent 开发:目标类 GPT/豆包网页版聊天**后端**,教学路线 L1 调模型 API → L2 SSE 流式 → L3 会话持久化 → L4 function calling → L5 agentic loop → L6 RAG → L7 MCP,裸写优先,不引入 LangChain 等框架(阶段 2 结束前);每课产物练习脚本在 scripts/。
- **L1~L6 已结业(L6 于 2026-10-09 验收)**。现有接口:`POST /chat/stream`(SSE + 会话持久化)、`POST /chat/agent`(agentic loop,MAX_ROUNDS=8,方案 B 全量持久化,轨迹收敛后单事务写入)。L6 产物:pgvector + EmbeddingChunk 表、services/rag/(chunker/retriever)、scripts/l6_ingest(切块→embed→幂等入库)、l6_retrieval(检索 + cosine/l2/inner 三算子对比)、l6_rag(RAG 闭环,阈值拦库外问题);search_knowledge_base 已接入 agentic loop。收尾完成:l6_rag.py 复用 retriever;agent 轨迹改单事务(crud.append_messages)。
- **L7 MCP 进行中(2026-10-09)**:裸写优先看穿协议。L7.1 最小 MCP client(scripts/l7_mcp_client.py):stdio 子进程 + JSON-RPC 三连(initialize → notifications/initialized 通知 → tools/list → tools/call),连 `uvx mcp-server-time`。规划:L7.2 把 search_knowledge_base 包成自己的 MCP server(消费方→提供方)→ L7.3 动态接入 agentic loop(启动时 tools/list 动态合成工具清单,loop 不改)。L7 之后 = 阶段 3 生产化(上下文管理/限流并发/部署)。
- 已知遗留(未做):/stream 的 assistant 回复没写库(reply_parts 攒而未存);/agent 流式化;pytest/JWT 暂缓。
- news 模块 CRUD 接口仍搁置;news 内容已在 L6 用作 RAG 素材(EmbeddingChunk.news_id 挂 news 表)。
