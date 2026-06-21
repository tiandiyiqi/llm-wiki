"""搜索引擎抽象基类

定义统一的搜索接口，支持全文搜索、向量搜索和混合搜索。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class SearchResult:
    """搜索结果数据结构

    Attributes:
        atom_id: 知识原子 ID
        slug: URL 友好标识
        title: 标题
        content: 正文内容
        score: 相关性得分
        highlights: 高亮片段列表
        metadata: 元数据字典
        kb_id: 知识库 ID
        kb_name: 知识库名称
        atom_type: 原子类型
        created_at: 创建时间
        updated_at: 更新时间
        match_type: 匹配类型（fulltext/vector/hybrid）
    """

    atom_id: int
    slug: str
    title: str
    content: str
    score: float
    highlights: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 扩展字段
    kb_id: Optional[int] = None
    kb_name: Optional[str] = None
    atom_type: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    match_type: str = 'fulltext'  # fulltext | vector | hybrid

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式

        Returns:
            字典表示
        """
        return {
            'atom_id': self.atom_id,
            'slug': self.slug,
            'title': self.title,
            'content': self.content,
            'score': self.score,
            'highlights': self.highlights,
            'metadata': self.metadata,
            'kb_id': self.kb_id,
            'kb_name': self.kb_name,
            'atom_type': self.atom_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'match_type': self.match_type,
        }


@dataclass
class SearchFilters:
    """搜索过滤条件

    Attributes:
        kb_id: 知识库 ID
        atom_type: 原子类型
        tags: 标签列表
        author_id: 作者 ID
        date_from: 起始日期
        date_to: 结束日期
        status: 状态
        min_confidence: 最小置信度
    """

    kb_id: Optional[int] = None
    atom_type: Optional[str] = None
    tags: Optional[List[str]] = None
    author_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    status: Optional[str] = None
    min_confidence: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {}
        if self.kb_id is not None:
            result['kb_id'] = self.kb_id
        if self.atom_type:
            result['type'] = self.atom_type
        if self.tags:
            result['tags'] = self.tags
        if self.author_id:
            result['author_id'] = self.author_id
        if self.date_from:
            result['date_from'] = self.date_from.isoformat()
        if self.date_to:
            result['date_to'] = self.date_to.isoformat()
        if self.status:
            result['status'] = self.status
        if self.min_confidence is not None:
            result['min_confidence'] = self.min_confidence
        return result


class SearchEngine(ABC):
    """搜索引擎抽象基类

    定义统一的搜索接口，支持：
    - 全文搜索（tsvector + tsquery）
    - 向量搜索（pgvector）
    - 混合搜索（全文 + 向量 + RRF 重排序）
    - 搜索建议

    所有方法均为异步，支持高并发场景。
    """

    @abstractmethod
    async def search(
        self,
        query: str,
        kb_id: Optional[int] = None,
        filters: Optional[SearchFilters] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[SearchResult]:
        """执行全文搜索

        Args:
            query: 查询字符串
            kb_id: 知识库 ID（可选，不指定则全局搜索）
            filters: 过滤条件
            limit: 返回数量上限
            offset: 偏移量（分页）

        Returns:
            搜索结果列表
        """
        pass

    @abstractmethod
    async def search_by_embedding(
        self,
        embedding: List[float],
        kb_id: Optional[int] = None,
        filters: Optional[SearchFilters] = None,
        limit: int = 50,
    ) -> List[SearchResult]:
        """执行向量相似度搜索

        Args:
            embedding: 查询向量（384 维，对应 all-MiniLM-L6-v2）
            kb_id: 知识库 ID（可选）
            filters: 过滤条件
            limit: 返回数量上限

        Returns:
            搜索结果列表（按余弦相似度排序）
        """
        pass

    @abstractmethod
    async def hybrid_search(
        self,
        query: str,
        embedding: List[float],
        kb_id: Optional[int] = None,
        filters: Optional[SearchFilters] = None,
        text_weight: float = 0.5,
        vector_weight: float = 0.5,
        limit: int = 50,
    ) -> List[SearchResult]:
        """执行混合搜索（全文 + 向量）

        使用 RRF (Reciprocal Rank Fusion) 算法合并结果。

        Args:
            query: 查询字符串
            embedding: 查询向量
            kb_id: 知识库 ID（可选）
            filters: 过滤条件
            text_weight: 全文搜索权重（0-1）
            vector_weight: 向量搜索权重（0-1）
            limit: 返回数量上限

        Returns:
            混合搜索结果列表
        """
        pass

    @abstractmethod
    async def suggest(
        self,
        prefix: str,
        kb_id: Optional[int] = None,
        limit: int = 5,
    ) -> List[str]:
        """获取搜索联想建议

        Args:
            prefix: 输入前缀
            kb_id: 知识库 ID（可选）
            limit: 返回数量上限

        Returns:
            联想建议列表
        """
        pass

    @abstractmethod
    async def get_search_stats(
        self,
        kb_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """获取搜索统计信息

        Args:
            kb_id: 知识库 ID（可选）

        Returns:
            统计信息字典
        """
        pass

    # ========== 可选方法 ==========

    async def search_with_highlights(
        self,
        query: str,
        kb_id: Optional[int] = None,
        filters: Optional[SearchFilters] = None,
        limit: int = 50,
        offset: int = 0,
        highlight_config: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """执行全文搜索并生成高亮片段

        Args:
            query: 查询字符串
            kb_id: 知识库 ID
            filters: 过滤条件
            limit: 返回数量上限
            offset: 偏移量
            highlight_config: 高亮配置
                - max_words: 最大词数
                - max_fragments: 最大片段数
                - start_delimiter: 开始标记
                - end_delimiter: 结束标记

        Returns:
            包含高亮片段的搜索结果
        """
        # 默认实现：调用 search 方法
        results = await self.search(query, kb_id, filters, limit, offset)
        return results

    async def explain_search(
        self,
        query: str,
        kb_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """解释搜索查询（调试用）

        Args:
            query: 查询字符串
            kb_id: 知识库 ID

        Returns:
            查询解释信息
        """
        return {
            'query': query,
            'kb_id': kb_id,
            'message': 'Not implemented',
        }