# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目性质: 教学项目,不要替用户写代码

这是用户系统性学习 **Agent 开发** 的教学项目(2026-10-13 重新拍板:总目标是深入掌握 Agent 开发,FastAPI 聊天后端只是贯穿全程的练习载体,完整路线见下方「学习路线图」)。**最重要的规则:绝不写/改/删项目源码文件**，即使是在帮用户修报错时,也只诊断、讲解、给代码片段,所有操作由用户亲手完成(用户明确说过「我在学习不要帮我做」)。

**例外(Agent 可直接写,用户拍板 2026-10-13)**:`CLAUDE.md` 本身由 Agent 自动维护更新——项目进展、新约定、新规范随时同步进此文件,无需逐次向用户确认;`doc/` 课件见下方「课件规范」。除此之外的项目源码(app/scripts/配置等)仍然严格由用户亲手改。

- 全程中文交流。讲解与操作分离:小段代码 + 重点讲解 + 验证命令 + 下一步预告。
- 报错分析:带用户读 traceback(从下往上、只看自己文件的帧),让用户自己改。
- 用户常见手滑:拼写错误(contet/emial/DATATBASE_URL)、重写文件时丢掉之前修过的内容、跳过验证步骤——提醒自查,不要直接动手改。
- 注意项目架构规范、代码规范，需要按照官方标准。
- 重点注意 Python 的类型安全问题(详见下方「类型规范」节)。


## 课件规范(2026-10-13 起,用户拍板)

**关键教程(每课/阶段课题)由 Agent 写成 HTML 课件存 `doc/` 目录**——这是用户明确授权 Agent 直接写的产物,不属于上面「不写源码」的约束范围;**项目源码(app/scripts/配置等)仍然严格由用户亲手改**,课件里的代码只是教学内容示例,不构成改源码的授权。

- 命名:**一个课一个目录**:`doc/{课号}/{课号}_{主题}.html`(如 `doc/C1/c1_redis_mutex.html`);后续课程延续 L 序列编号(如 `doc/L8/l8_pytest.html`);**专题插播课用 T 序列、不占 L 序列**(如 `doc/T1/t1_agent_ecosystem.html`,2026-10-14 起)。**拆分粒度按课,一课一份课件**——跨课依赖用篇内背景回顾解决,不合并多课为一份课件(用户 2026-10-13 拍板:曾试过把 C1~C3 合成一份,最终定回按课拆分)。
- 内容结构:本课目标 → 背景回顾 → 原理 → 动手实现(分步,代码块完整可抄、注释详细清晰)→ 思考题(含详解)→ 验证实验 → 对比小结 → 进阶预告。
- **单课完整性(重点)**:一篇课件要能脱离对话上下文独立学习——涉及前课结论时在课件内做背景回顾;所有代码改动在单篇内闭环(不出现「见聊天记录」);验证实验与观察点写全。
- **结合实际代码(重点)**:写课件前先读项目相关代码,保证课件示例与项目实际对齐(命名、结构、既有约定,不凭空发明);对实际代码的点评(风格、手滑、设计取舍)直接融入讲解。不做进度标注/进度看板类元素——课件是教学内容,不是状态追踪。
- 技术约束:纯 HTML + 内嵌 CSS,无外部 CDN 依赖,离线可看;全中文。

## 学习路线图(2026-10-13 重新规划,用户拍板)

**总目标:深入掌握 Agent 开发**。聊天后端是贯穿全程的练习载体,不是终点;课题取舍以 Agent 核心能力为准——**上下文工程、规划、编排、评测、安全**。灵魂知识点的沉淀比「功能做完」重要。原则:裸写优先(不引入 LangChain/LangGraph 等框架,延续到全部后续课);一课一份课件(见「课件规范」);每课沉淀灵魂知识点进本文件。

### 已完成基座

- **阶段 1 对话核心(L1~L3)**:模型 API 调用、SSE 流式、会话持久化
- **阶段 2 Agent 能力(L4~L7)**:function calling、agentic loop、RAG(pgvector)、MCP(裸写 stdio client/server → 正式化 McpClient)
- **阶段 3 生产化(A1/A2/B1/B2 ✅,C1~C3 收尾进行中)**:/agent/stream 流式化(事件合同)、trim 滑动窗口、会话互斥 + 全局信号量、Redis 分布式互斥(C1)→ Docker 部署(C2)→ 结业盘点(C3)

### 阶段 4 — 上下文工程与记忆(L8~L9):Agent 的记忆与注意力管理

- **L8 长期记忆**:memories 表迁移 → 对话后 LLM 结构化提取记忆(JSON → Any 边界收窄入库)→ remember/forget 工具注册 → build_llm_messages 前注入 system;起步全量注入,记忆量大了回接 L6 pgvector 改检索式注入;验收 = 跨会话记得用户偏好
- **L9 上下文工程进阶**:工具结果裁剪(大结果截断/落盘引用)、token 预算、历史摘要压缩(远期摘要 + 近期原文分层);定位 = B1 被动 trim 的主动优化版

### 阶段 5 — 规划与编排(L10~L12):从单体 agent 到 agent 系统

- **L10 规划与反思**:plan-and-execute(先出计划 JSON → 逐步执行 → 对照计划修正/重排)+ reflection 执行后自评;解决「多步任务走偏」问题
- **L11 子 agent 编排**:spawn_subagent 工具(独立 messages 起精简 run_agent,只带结论回主上下文 = 上下文隔离)、递归深度/预算限制
- **L12 并行编排与长任务(机动)**:asyncio fan-out/fan-in 多子 agent(呼应全局 _llm_semaphore)、后台任务与进度流、工具执行前审批(human-in-the-loop)

### 阶段 6 — 评测与可观测(L13~L14):能测量才能掌握

- **L13 可观测性**:分层 tracing(agent/llm/tool 各一层)、token 用量与成本统计、结构化轨迹导出
- **L14 评测**:固定评测集(问题 + 期望行为)、LLM-as-judge 打分脚本、回归跑分(改 prompt/换模型前后对比,防越改越差)

### 阶段 7 — 安全与结业(L15~L16)

- **L15 Agent 安全**:prompt injection 攻防实验(在 RAG/工具结果里埋注入打自家 agent)、工具最小权限、输出护栏
- **L16 结业 capstone**:综合运用记忆 + 规划 + 子 agent + 评测做一个完整场景(如个人知识助手),作为全路线验收

机动专题(不排课,用到再穿插):结构化输出强化、模型分级路由降本、多模态输入、MCP 传输进阶(Streamable HTTP/鉴权)。

**衔接约定**:阶段 4 前置 = C3 结业盘点收完;C3 拍板 /stream 去留时建议砍 /stream 只留 /agent/stream,后续课程全长在 agent 层。此前拍板的「L8 三小节合并 / L9 评测」方向已重新规划为逐课拆分 L8~L16(课件按「课件规范」一个课一个目录 `doc/L{n}/`)。

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

## 当前状态(2026-10-14)

- 2026-09-20 起主线转向 Agent 开发;**总目标已重新拍板(2026-10-13):深入掌握 Agent 开发,类 GPT 聊天后端只是练习载体**,完整路线见上方「学习路线图」;裸写优先,不引入 LangChain/LangGraph 等框架;练习脚本在 scripts/,**课件在 doc/(Agent 写,见「课件规范」)**。
- **L1~L7 已结业**。接口:`POST /chat/stream`(SSE+持久化,三段式连接管理)、`POST /chat/agent`(非流式 agentic loop)、`POST /agent/stream`(流式 agentic loop)。L7 产物:scripts/l7_mcp_client.py(裸写 JSON-RPC 三连)、l7_mcp_server.py(自家 stdio MCP server)、app/services/mcp/client.py(McpClient,main.py lifespan 驱动,.env 的 MCP_KB_SERVER_CMD 配置);tools.py 经 register_mcp_tools 注入 + get_all_tool_schemas 聚合(MCP 同名覆盖内置),agent loop 取简历走 get_all_tool_schemas()。
- **阶段 3 进行中**:A1 ✅ /stream assistant 落库(流收敛后 join 写入);A2 ✅ /agent/stream 流式化(llm 层 stream_chat_with_tools 拼接 tool_calls 碎片→TextEvent/ToolCallsEvent 事件合同;agent 层 run_agent_stream 透传 text/消化工具轮;轨迹仍收敛后单事务写;StoredToolCall ≡ SDK param ≡ 事件载荷三形合一);B1 ✅ trim_history 滑动窗口(切点后移到 user,防裁在轨迹中间致 400;message_to_dict 桥必须在 trim 前);B2 ✅ 会话互斥(claim/release,流式接口 claim 在 handler return 前、release 在 generator finally;同会话并发 409 已验证)+全局 _llm_semaphore(8)。
- **阶段 3 收尾课题进行中(课件:doc/C1/、doc/C2/、doc/C3/)**:C1 代码已完成——claim/release 换 Redis SET NX EX + DEL(_BUSY_KEY / _BUSY_TTL_SECONDS=600),_busy_conversations 已删,6 处调用点全 await,lifespan 补 redis aclose,.env.example 补 REDIS_URL;待做:C1 验证(ruff/mypy → --workers 4 同会话并发 5 遍全稳 409)→ C2 部署 → C3 盘点。
- **专题插播课 T1(2026-10-14,Agent 已写课件,用户尚未学,安排在进 L8 之前)**:Agent 生态地图——CLI / MCP / SKILL / Rules / Hook / 子 Agent / 插件 / CLAUDE.md 概念对照课,每个概念锚定项目代码(TOOLS_SCHEMA 全量常驻 vs SKILL 渐进披露 → L9 伏笔;CLAUDE.md = 人肉长期记忆 → L8 伏笔);动手 = 用户在 `~/.claude/skills/` 写 py-hand-check skill(含 check_typos.sh 脚本,不碰项目源码)。课件 `doc/T1/t1_agent_ecosystem.html`。事实基线:MCP 现行规范 2026-07-28(无状态核心;用户 client 握手仍是 2025-06-18 stdio 形态,知识不过时),Skills 为开放规范(agentskills.io / anthropics-skills 仓库)。
- **连接纪律(硬约定)**:run_agent/stream_chat 等秒级 await 外不得有任何 AsyncSessionLocal 块——连接只陪 DB 干活,不陪 LLM 思考;409 必须在响应头发出前抛,流开始后错误只能走流内事件;try/finally 必须包住 generator 的执行(放体内)而非定义。
- 已知遗留:pytest/JWT 暂缓;news 模块 CRUD 搁置(news 内容已作 RAG 素材);/stream 与 /agent/stream 并存待 C3 决定去留。
