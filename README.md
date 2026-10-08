# 项目启动
```sh
uv sync

uv run uvicorn app.main:app --reload 
```

# Docker 常用命令
```sh
# 1. Compose 日常操作
docker compose up -d              # 启动全部服务（首次会自动构建 app）
docker compose up -d --build      # 改了代码后重建 app 并启动
docker compose down               # 停止并删除所有容器（数据卷保留）
docker compose ps                 # 看哪些服务在跑、端口映射
docker compose logs -f app        # 跟踪 app 的日志（Ctrl+C 退出）
docker compose restart app        # 重启某个服务
docker compose stop / start       # 停止 / 启动（不删容器）

# 2.容器操作
docker ps                         # 正在运行的容器
docker ps -a                      # 包括已停止的
docker exec -it study-app sh      # 钻进 app 容器内部（调试神器）
docker exec -it study-pgsql psql -U postgres study_fastapi   # 直接进 psql
docker exec -it study-redis redis-cli -a redis123            # 直接进 redis-cli
docker logs study-app             # 看容器日志
docker logs -f --tail 100 study-app   # 只看最近 100 行并跟踪
docker stop / start / restart study-app   # 单容器控制
docker rm study-app               # 删除已停止的容器

# 3. 镜像操作
docker images                     # 本地有哪些镜像
docker build -t study-fastapi .   # 手动构建镜像
docker rmi <镜像ID>               # 删除镜像
docker pull postgres:18           # 拉取远程镜像

# 4. 数据卷（你的 pgdata / mysqldata / redisdata）
docker volume ls                  # 列出所有卷
docker volume inspect pgdata      # 看卷详情
docker volume rm pgdata           # 删除卷 ⚠️ 数据库数据会没
docker compose down -v            # down 时连数据卷一起删 ⚠️

# 5. 排查问题
docker inspect study-app          # 容器完整信息（IP、挂载、环境变量）
docker stats                      # 实时 CPU / 内存占用
docker system df                  # Docker 磁盘占用总览

# 6. 清理（磁盘满了再用）
docker system prune               # 清理停掉的容器、无用网络、悬空镜像
docker system prune -a            # 连没用到的镜像一起清（更彻底）
docker volume prune               # 清理无主数据卷 ⚠️ 会删数据

```

# 初始化建表：标准流程

```python
# 1. 生成迁移脚本(对比"模型图纸"和"数据库现状",自动写 DDL)
uv run alembic revision --autogenerate -m "init tables"

# 2. 【最重要的一步】打开 alembic/versions/ 里生成的那个 py 文件,逐行读
#    确认是 6 个 op.create_table + gender 的 Enum 创建,且没有任何 op.drop_table

# 3. 执行
uv run alembic upgrade head

# 4. 验证
# 打开 IntelliJ IDEA 验证
```

# Lint 检查
```
# 格式化（缩进、空行、引号风格）
uv run ruff format app scripts

# Lint 检查（代码规范，如未使用的 import、ANN 参数标注缺失）
uv run ruff check app scripts

# 类型检查app、scripts两个目录
uv run mypy app scripts
```


# 跑测试代码
```
uv run python scripts/xxx.py
```