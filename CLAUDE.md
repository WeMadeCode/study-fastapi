# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目性质: 教学项目,不要替用户写代码

这是用户系统性学习 FastAPI 的项目。**最重要的规则:绝不写/改/删项目源码文件**，即使是在帮用户修报错时,也只诊断、讲解、给代码片段,所有操作由用户亲手完成(用户明确说过「我在学习不要帮我做」)。

- 全程中文交流。讲解与操作分离:小段代码 + 重点讲解 + 验证命令 + 下一步预告。
- 报错分析:带用户读 traceback(从下往上、只看自己文件的帧),让用户自己改。
- 用户常见手滑:拼写错误(contet/emial/DATATBASE_URL)、重写文件时丢掉之前修过的内容、跳过验证步骤——提醒自查,不要直接动手改。
- 注意项目架构规范、代码规范，需要按照官方标准。

## 架构

src 布局 + uv,Python 3.13。请求链路:`main.py` 注册 routers → routers(接口层,只做校验和 404/409 转换)→ `crud.py`(所有数据库操作,接收 AsyncSession)→ models / schemas。

- **异步全链路**:`database/pgsql_client.py` 的 `create_async_engine`(psycopg 异步驱动)+ `async_sessionmaker(expire_on_commit=False)`;`get_async_db` 作为依赖注入 AsyncSession,routers/crud 均为 async。
- **Base 基类**:`pgsql_client.py` 里的 `Base` 自带 `create_at`/`update_at` 时间戳列,所有模型自动继承。
- **模型注册**:新增模型必须在 `models/__init__.py` 显式导入,否则 Alembic autogenerate 检测不到;`alembic/env.py` 从 `.env` 读 `DATABASE_URL` 并挂 `Base.metadata`。
- **schemas 约定**:Pydantic v2,`*Create`(入参)/`*Update`(可选字段,crud 用 `exclude_unset=True`)/`*Public`(出参,`from_attributes=True`)三件套。
- **配置**:`config/config.py` 用 pydantic-settings 读根目录 `.env`(`.env.example` 是模板,`.env` 不进仓库);`DATABASE_URL` 为空时启动即报错。
- **Docker 拓扑**:compose 起 4 个服务——app(容器内 `uv run uvicorn`)、db(postgres:18,容器名 study-pgsql)、mysql(备用练习)、redis;app 的 `DATABASE_URL` 指向 `db` 服务,带 healthcheck + `depends_on: service_healthy`。

## 当前状态(2026-09-21)

- 主线已完成:异步改造、Docker/Compose、Alembic 迁移链;pytest/JWT 暂缓。
- 进行中:schemas 从单文件 `schemas.py` 拆成 `schemas/` 包——目前两套并存,包里还没有 `__init__.py`,实际生效的是 `schemas.py`。
- news 模块(models 已建:news/category/favorite/history)接口未开工;`news.py` 是半成品草稿。
- 下一课 L1:裸写 OpenAI 兼容 SDK 调火山方舟模型 API(非流式、独立脚本、先不碰 FastAPI),Key 存 `.env`。
