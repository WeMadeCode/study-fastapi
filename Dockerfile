# 一切镜像都基于别的镜像。slim 是精简版 Debian，比完整版小几百 MB。这就是 Docker 的“套娃”机制：你的镜像 = 官方 Python 镜像 + 你的东西
FROM python:3.13-slim
# - 相当于 cd /app，之后所有命令都在这个目录执行，且目录会自动创建。
WORKDIR /app
# — 只先把依赖声明拷进去。⚠️ 注意：没有拷 src/，这是故意的，见下面的“层缓存”。
COPY pyproject.toml uv.lock ./
# — 装依赖。--frozen 表示严格按 uv.lock 装（和你本地 uv sync 行为一致）；--no-install-project 表示先不装项目本身（因为代码还没拷进来）。
RUN pip install uv && uv sync --frozen --no-dev --no-install-project
# — 这时候才拷代码并安装项目本身。
COPY src ./src
COPY README.md ./ 
RUN uv sync --frozen --no-dev
#  — 只是声明“本应用监听 8000 端口”，起文档作用，不做实际端口映射。
EXPOSE 8000
# --host 0.0.0.0：必须的！容器里 127.0.0.1 只指容器自己，写 localhost 外面就访问不到了
# uv run：在虚拟环境里执行，不用手动 source .venv/bin/activate
CMD ["uv", "run", "uvicorn", "study_fastapi.main:app", "--host", "0.0.0.0", "--port", "8000"]