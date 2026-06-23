"""
通用测试共享 fixtures

提供所有测试模块共用的 Mock 对象、临时目录、测试数据工厂等。
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ============================================================================
# 路径配置
# ============================================================================

@pytest.fixture(autouse=True)
def _setup_path():
    """确保 lib/ 在 sys.path 中，使 from lib.xxx 导入正常工作。"""
    project_root = Path(__file__).resolve().parent.parent
    lib_dir = str(project_root / "lib")
    if lib_dir not in sys.path:
        sys.path.insert(0, lib_dir)
    yield
    # 清理：移除添加的路径
    if lib_dir in sys.path:
        sys.path.remove(lib_dir)


# ============================================================================
# 临时目录 fixtures
# ============================================================================

@pytest.fixture
def tmp_kb_dir(tmp_path):
    """创建一个模拟的知识库目录结构。"""
    kb_dir = tmp_path / "test_kb"
    kb_dir.mkdir()
    # 创建标准目录结构
    (kb_dir / "facts").mkdir()
    (kb_dir / "opinions").mkdir()
    (kb_dir / "definitions").mkdir()
    (kb_dir / "methods").mkdir()
    (kb_dir / "data").mkdir()
    (kb_dir / "questions").mkdir()
    (kb_dir / "references").mkdir()
    # 创建 .llm-wiki 元数据目录
    meta_dir = kb_dir / ".llm-wiki"
    meta_dir.mkdir()
    return kb_dir


@pytest.fixture
def tmp_storage_dir(tmp_path):
    """创建一个临时存储目录（用于文件模式测试）。"""
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    return storage_dir


# ============================================================================
# Mock 数据库 fixtures
# ============================================================================

@pytest.fixture
def mock_db_connection():
    """Mock asyncpg 数据库连接。"""
    conn = AsyncMock()
    conn.execute = AsyncMock(return_value=None)
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=None)
    conn.close = AsyncMock()
    return conn


@pytest.fixture
def mock_db_pool(mock_db_connection):
    """Mock asyncpg 连接池。"""
    pool = AsyncMock()
    pool.acquire = AsyncMock(return_value=mock_db_connection)
    pool.release = AsyncMock()
    pool.close = AsyncMock()
    return pool


@pytest.fixture
def mock_sqlite_conn():
    """Mock sqlite3 数据库连接。"""
    conn = MagicMock()
    conn.execute = MagicMock(return_value=MagicMock())
    conn.fetchone = MagicMock(return_value=None)
    conn.fetchall = MagicMock(return_value=[])
    conn.commit = MagicMock()
    conn.close = MagicMock()
    return conn


# ============================================================================
# Mock Redis fixtures
# ============================================================================

@pytest.fixture
def mock_redis():
    """Mock Redis 客户端。"""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.exists = AsyncMock(return_value=0)
    redis.keys = AsyncMock(return_value=[])
    redis.incr = AsyncMock(return_value=1)
    redis.ttl = AsyncMock(return_value=-1)
    return redis


# ============================================================================
# Mock HTTP fixtures
# ============================================================================

@pytest.fixture
def mock_http_response():
    """创建 Mock HTTP 响应对象。"""
    def _make_response(status_code=200, json_data=None, text="", headers=None):
        response = MagicMock()
        response.status_code = status_code
        response.json = MagicMock(return_value=json_data or {})
        response.text = text
        response.headers = headers or {}
        return response
    return _make_response


# ============================================================================
# 测试数据工厂 fixtures
# ============================================================================

@pytest.fixture
def sample_atom():
    """创建一个标准的测试原子数据。"""
    return {
        "id": "test-atom-001",
        "path": "facts/test-atom",
        "type": "fact",
        "title": "测试原子",
        "description": "这是一个用于测试的原子",
        "tags": ["test", "sample"],
        "status": "active",
        "author": "testuser",
        "created": "2026-01-01T00:00:00Z",
        "updated": "2026-06-01T00:00:00Z",
        "content": "# 测试原子\n\n这是测试内容。",
    }


@pytest.fixture
def sample_user():
    """创建一个标准的测试用户数据。"""
    return {
        "username": "testuser",
        "role": "editor",
        "email": "testuser@example.com",
    }


@pytest.fixture
def sample_admin_user():
    """创建一个管理员测试用户数据。"""
    return {
        "username": "admin",
        "role": "admin",
        "email": "admin@example.com",
    }


@pytest.fixture
def sample_kb():
    """创建一个标准的测试知识库数据。"""
    return {
        "id": 1,
        "name": "测试知识库",
        "slug": "test-kb",
        "description": "用于测试的知识库",
        "status": "active",
    }


# ============================================================================
# 环境变量 fixtures
# ============================================================================

@pytest.fixture
def clean_env(monkeypatch):
    """清理测试环境变量，防止测试间干扰。"""
    env_vars = [
        "LLM_WIKI_DB_URL",
        "LLM_WIKI_REDIS_URL",
        "LLM_WIKI_SECRET_KEY",
        "CASDOOR_CLIENT_ID",
        "CASDOOR_CLIENT_SECRET",
    ]
    for var in env_vars:
        monkeypatch.delenv(var, raising=False)
    return monkeypatch
