# LLM Wiki 部署指南

**版本**: 1.0.0
**更新日期**: 2026-06-22

---

## 目录

1. [系统要求](#系统要求)
2. [安装步骤](#安装步骤)
3. [配置说明](#配置说明)
4. [数据库设置](#数据库设置)
5. [启动服务](#启动服务)
6. [生产部署](#生产部署)
7. [监控与维护](#监控与维护)

---

## 系统要求

### 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 2 核 | 4 核+ |
| 内存 | 4 GB | 8 GB+ |
| 存储 | 20 GB | 100 GB+ |

### 软件要求

- **操作系统**: Linux (Ubuntu 20.04+), macOS 11+, Windows 10+
- **Python**: 3.11+
- **数据库**: PostgreSQL 14+（企业版）或 SQLite 3.35+（个人版）

---

## 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/your-org/llm-wiki.git
cd llm-wiki
```

### 2. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
# 安装核心依赖
pip install -e .

# 安装开发工具（可选）
pip install -e ".[dev]"

# 安装 PostgreSQL 支持（企业版）
pip install -e ".[postgres]"

# 安装向量搜索支持（可选）
pip install -e ".[vector]"
```

### 4. 验证安装

```bash
python -c "import lib; print('Installation successful!')"
```

---

## 配置说明

### 环境变量配置

创建 `.env` 文件：

```bash
# 存储模式：file 或 db
LLM_WIKI_STORAGE_MODE=db

# PostgreSQL 配置（企业版）
LLM_WIKI_POSTGRES_URL=postgresql://user:password@localhost:5432/llmwiki

# 连接池配置
LLM_WIKI_POOL_SIZE=10
LLM_WIKI_MAX_OVERFLOW=20

# 日志级别
LOG_LEVEL=INFO

# API 配置
API_HOST=0.0.0.0
API_PORT=5000

# 认证配置
SECRET_KEY=your-secret-key-here
TOKEN_EXPIRY=3600
```

### YAML 配置文件

复制示例配置：

```bash
cp config/storage.example.yaml config/storage.yaml
```

编辑 `config/storage.yaml`：

```yaml
storage:
  # 存储模式：file | db
  type: db

  # PostgreSQL 配置
  db:
    host: ${DB_HOST:localhost}
    port: ${DB_PORT:5432}
    database: ${DB_NAME:llmwiki}
    user: ${DB_USER:llmwiki}
    password: ${DB_PASSWORD:}

    # 连接池
    pool:
      min_size: 5
      max_size: 20
      max_overflow: 10

# 多级知识库配置
hierarchy:
  levels:
    - personal
    - department
    - project
    - company

# 权限系统配置
permissions:
  default_role: viewer
```

---

## 数据库设置

### SQLite（个人版）

无需额外配置，自动创建数据库文件。

### PostgreSQL（企业版）

#### 1. 安装 PostgreSQL

**Ubuntu/Debian**:
```bash
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
```

**macOS**:
```bash
brew install postgresql@14
brew services start postgresql@14
```

#### 2. 创建数据库和用户

```bash
# 切换到 postgres 用户
sudo -u postgres psql

# 创建用户
CREATE USER llmwiki WITH PASSWORD 'your-password';

# 创建数据库
CREATE DATABASE llmwiki OWNER llmwiki;

# 授予权限
GRANT ALL PRIVILEGES ON DATABASE llmwiki TO llmwiki;

# 退出
\q
```

#### 3. 初始化 Schema

```bash
# 执行 SQL 脚本
psql -U llmwiki -d llmwiki -f lib/db/schema.sql
psql -U llmwiki -d llmwiki -f lib/db/indexes.sql
psql -U llmwiki -d llmwiki -f lib/db/functions.sql
psql -U llmwiki -d llmwiki -f lib/db/rls.sql
```

#### 4. 启用扩展

```sql
-- 连接到数据库
\c llmwiki

-- 启用 pgvector（向量搜索）
CREATE EXTENSION IF NOT EXISTS vector;

-- 启用 pgcrypto（加密）
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 启用 uuid-ossp（UUID 生成）
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

---

## 启动服务

### 开发模式

```bash
# 启动 Web 服务器
python llm-wiki.py web --kb ./knowledge-bases

# 启动 API 服务器
python llm-wiki.py api --host 0.0.0.0 --port 5000
```

### 生产模式

#### 使用 Gunicorn

```bash
# 安装 Gunicorn
pip install gunicorn

# 启动服务
gunicorn -w 4 -b 0.0.0.0:5000 lib.web_server:app
```

#### 使用 uWSGI

```bash
# 安装 uWSGI
pip install uwsgi

# 创建配置文件 uwsgi.ini
[uwsgi]
module = lib.web_server:app
master = true
processes = 4
socket = 0.0.0.0:5000
chmod-socket = 660
vacuum = true
die-on-term = true

# 启动
uwsgi --ini uwsgi.ini
```

---

## 生产部署

### Docker 部署

#### 1. 创建 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "lib.web_server:app"]
```

#### 2. 构建镜像

```bash
docker build -t llm-wiki:1.0.0 .
```

#### 3. 运行容器

```bash
docker run -d \
  --name llm-wiki \
  -p 5000:5000 \
  -e LLM_WIKI_STORAGE_MODE=db \
  -e LLM_WIKI_POSTGRES_URL=postgresql://user:pass@db:5432/llmwiki \
  llm-wiki:1.0.0
```

### Docker Compose 部署

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  db:
    image: postgres:14
    environment:
      POSTGRES_USER: llmwiki
      POSTGRES_PASSWORD: your-password
      POSTGRES_DB: llmwiki
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./lib/db:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"

  app:
    image: llm-wiki:1.0.0
    environment:
      LLM_WIKI_STORAGE_MODE: db
      LLM_WIKI_POSTGRES_URL: postgresql://llmwiki:your-password@db:5432/llmwiki
    ports:
      - "5000:5000"
    depends_on:
      - db

volumes:
  postgres-data:
```

启动：

```bash
docker-compose up -d
```

### Nginx 反向代理

创建 `/etc/nginx/sites-available/llm-wiki`：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/llm-wiki/static;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/llm-wiki /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 监控与维护

### 日志管理

日志文件位置：
- 应用日志: `/var/log/llm-wiki/app.log`
- 访问日志: `/var/log/llm-wiki/access.log`

日志轮转配置（`/etc/logrotate.d/llm-wiki`）：

```
/var/log/llm-wiki/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 www-data www-data
}
```

### 数据备份

#### SQLite 备份

```bash
# 备份数据库文件
cp data/llmwiki.db backups/llmwiki-$(date +%Y%m%d).db
```

#### PostgreSQL 备份

```bash
# 完整备份
pg_dump -U llmwiki -d llmwiki > backups/llmwiki-$(date +%Y%m%d).sql

# 恢复备份
psql -U llmwiki -d llmwiki < backups/llmwiki-20260622.sql
```

### 性能监控

#### 启用性能指标

```bash
# 安装监控工具
pip install prometheus-client

# 在配置中启用
ENABLE_METRICS=true
METRICS_PORT=9090
```

#### Prometheus 配置

```yaml
scrape_configs:
  - job_name: 'llm-wiki'
    static_configs:
      - targets: ['localhost:9090']
```

### 健康检查

```bash
# 检查服务状态
curl http://localhost:5000/api/health

# 检查数据库连接
python -c "from lib.core import create_manager; import asyncio; asyncio.run(create_manager())"
```

---

## 故障排除

### 常见问题

**1. 数据库连接失败**

```bash
# 检查 PostgreSQL 服务状态
sudo systemctl status postgresql

# 检查连接配置
echo $LLM_WIKI_POSTGRES_URL

# 测试连接
psql -U llmwiki -d llmwiki -c "SELECT 1"
```

**2. 权限错误**

```bash
# 检查文件权限
ls -la data/

# 修复权限
chmod 755 data/
chmod 644 data/*.db
```

**3. 端口占用**

```bash
# 查看端口占用
lsof -i :5000

# 终止进程
kill -9 <PID>
```

---

## 升级指南

### 从旧版本升级

```bash
# 备份数据
pg_dump -U llmwiki -d llmwiki > backup.sql

# 拉取最新代码
git pull origin main

# 更新依赖
pip install -e ".[dev]"

# 执行数据库迁移
python llm-wiki.py migrate --dry-run
python llm-wiki.py migrate

# 重启服务
sudo systemctl restart llm-wiki
```

---

**最后更新**: 2026-06-22
**维护团队**: LLM Wiki Team