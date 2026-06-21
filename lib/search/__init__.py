"""搜索引擎模块

提供 PostgreSQL 全文检索和向量检索的统一接口。

使用示例:
    from lib.search import PostgreSQLSearchEngine, SearchResult

    # 创建搜索引擎
    engine = PostgreSQLSearchEngine(pool)

    # 全文搜索
    results = await engine.search("machine learning", kb_id=1, limit=10)

    # 向量搜索
    results = await engine.search_by_embedding(embedding, kb_id=1)

    # 混合搜索
    results = await engine.hybrid_search(query, embedding, text_weight=0.5)
"""

from .engine import SearchEngine, SearchResult
from .postgres_search import PostgreSQLSearchEngine
from .hybrid_search import HybridSearchOptimizer

__all__ = [
    'SearchEngine',
    'SearchResult',
    'PostgreSQLSearchEngine',
    'HybridSearchOptimizer',
]