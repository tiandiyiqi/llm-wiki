"""搜索引擎模块

提供 PostgreSQL 全文检索和向量检索的统一接口，以及 LLM 摘要生成和搜索高亮。

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

    # LLM 摘要
    from lib.search import LLMSummarizer, SummaryConfig
    config = SummaryConfig(llm_api_key="sk-xxx")
    summarizer = LLMSummarizer(config)
    summaries = await summarizer.summarize_batch(results)

    # 独立高亮生成
    from lib.search import HighlightConfig, HighlightGenerator
    config = HighlightConfig(chinese_aware=True)
    generator = HighlightGenerator()
    highlights = generator.generate_highlights("搜索文本", "搜索", config)

    # 搜索联想
    from lib.search import SearchSuggester, SuggestConfig
    suggester = SearchSuggester()
    suggestions = await suggester.suggest(pool, "mach", kb_id=1, limit=10)

    # 向量索引管理
    from lib.search import VectorSearchConfig, VectorIndexManager, BatchEmbeddingUpdater
    config = VectorSearchConfig()
    await VectorIndexManager.create_index_if_needed(pool, 'atoms', 'embedding', config)

    updater = BatchEmbeddingUpdater()
    await updater.update_batch(pool, atom_ids, embeddings)
"""

from .engine import SearchEngine, SearchResult
from .highlight import HighlightConfig, HighlightGenerator
from .postgres_search import PostgreSQLSearchEngine
from .hybrid_search import HybridSearchOptimizer
from .summary import LLMSummarizer, SummaryConfig, SummaryResult
from .suggest import (
    SearchSuggester,
    SuggestConfig,
    SuggestionResult,
    SuggestionType,
)
from .vector_search import (
    BatchEmbeddingUpdater,
    IndexStatus,
    VectorIndexManager,
    VectorIndexType,
    VectorSearchConfig,
)

__all__ = [
    'SearchEngine',
    'SearchResult',
    'PostgreSQLSearchEngine',
    'HybridSearchOptimizer',
    'LLMSummarizer',
    'SummaryConfig',
    'SummaryResult',
    'HighlightConfig',
    'HighlightGenerator',
    'SearchSuggester',
    'SuggestConfig',
    'SuggestionResult',
    'SuggestionType',
    'BatchEmbeddingUpdater',
    'IndexStatus',
    'VectorIndexManager',
    'VectorIndexType',
    'VectorSearchConfig',
]