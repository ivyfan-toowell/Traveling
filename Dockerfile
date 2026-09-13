# ========== 多阶段构建 ==========

# 阶段1：构建依赖
FROM python:3.12-slim AS builder

WORKDIR /build

# 安装 UV 包管理器
RUN pip install --no-cache-dir \
    --timeout 120 \
    --retries 10 \
    -i https://pypi.tuna.tsinghua.edu.cn/simple \
    uv

# 复制依赖文件
COPY requirements.txt .

# 创建虚拟环境并安装依赖
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV UV_HTTP_TIMEOUT=300 \
    UV_HTTP_RETRIES=10 \
    UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install -r requirements.txt

# 阶段2：运行时镜像
FROM python:3.12-slim

WORKDIR /app

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 复制应用代码
COPY app /app/app
COPY scripts /app/scripts
COPY data /app/data
COPY zhixing.html /app/zhixing.html

# 设置环境变量
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV APP_PORT=14726

# 暴露端口（使用环境变量）
EXPOSE ${APP_PORT}

# 使用 Python 标准库执行健康检查，不依赖 curl/apt 软件包。
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('APP_PORT', '14726') + '/health', timeout=5)"

# 启动命令（使用环境变量）
CMD uvicorn app.main:app --host 0.0.0.0 --port ${APP_PORT}
