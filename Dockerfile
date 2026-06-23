FROM python:3.12-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[postgres,search,ocr,preview]" 2>/dev/null || \
    pip install --no-cache-dir -e .

# 应用代码
COPY . .

# 创建知识库目录
RUN mkdir -p /app/knowledge-bases

# 环境变量默认值
ENV LLM_WIKI_STORAGE_MODE=db \
    LLM_WIKI_HOST=0.0.0.0 \
    LLM_WIKI_PORT=8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" || exit 1

# 启动入口
CMD ["python", "-m", "lib.cli", "serve", "--host", "0.0.0.0", "--port", "8000"]
