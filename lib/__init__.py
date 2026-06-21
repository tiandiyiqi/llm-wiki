"""LLM Wiki 核心库

OKF (Open Knowledge Format) 知识库管理工具的核心模块。
"""

from .constants import (
    RESERVED_FILES,
    REQUIRED_FIELDS,
    RECOMMENDED_FIELDS,
    TYPE_DIRS,
    KB_META_SCHEMA,
    CHROMA_AVAILABLE,
    EMBEDDINGS_AVAILABLE
)

from .registry import KBRegistry
from .yaml_parser import SimpleYAMLParser
from .validator import OKFValidator
from .exporter import OKFExporter
from .importer import OKFImporter
from .initializer import KBInitializer
from .indexer import IndexGenerator
from .ingestor import KnowledgeIngestor
from .querier import AggregatedQuerier, KnowledgeQuerier, SearchHistory
from .semantic import SemanticSearchEngine
from .visualizer import KnowledgeVisualizer
from .timeline import TimelineGenerator
from .quick_capture import QuickCapture
from .discovery import DiscoveryEngine
from .watcher import KnowledgeWatcher
from .web_data import WebDataExporter
from .web_ui import create_web_ui

# 新增模块
from .multi_format_parser import MultiFormatParser, LongDocumentSplitter
from .batch_ops import BatchOperations
from .api_server import APIServer
from .auth import AuthManager
from .lifecycle import LifecycleManager
from .audit import AuditLogger
from .analytics import AnalyticsEngine
from .feedback import FeedbackManager
from .workflow import WorkflowManager, Notifier
from .fts_index import FTSIndex
from .cache import ConceptCache, EmbedIncremental, PaginatedQuerier
from .backup import BackupManager
from .web_server import UnifiedWebServer
from .ai_helper import (
    QAEngine, DuplicateDetector, QualityChecker,
    ShareLinkManager, SensitiveInfoMasker, WebhookNotifier
)
from .migration import MigrationManager, MigrationResult, MigrationValidator, ValidationResult

__all__ = [
    'RESERVED_FILES',
    'REQUIRED_FIELDS',
    'RECOMMENDED_FIELDS',
    'TYPE_DIRS',
    'KB_META_SCHEMA',
    'CHROMA_AVAILABLE',
    'EMBEDDINGS_AVAILABLE',
    'KBRegistry',
    'SimpleYAMLParser',
    'OKFValidator',
    'OKFExporter',
    'OKFImporter',
    'KBInitializer',
    'IndexGenerator',
    'KnowledgeIngestor',
    'AggregatedQuerier',
    'KnowledgeQuerier',
    'SearchHistory',
    'SemanticSearchEngine',
    'KnowledgeVisualizer',
    'TimelineGenerator',
    'QuickCapture',
    'DiscoveryEngine',
    'KnowledgeWatcher',
    'WebDataExporter',
    'create_web_ui',
    # 新增模块
    'MultiFormatParser',
    'LongDocumentSplitter',
    'BatchOperations',
    'APIServer',
    'AuthManager',
    'LifecycleManager',
    'AuditLogger',
    'AnalyticsEngine',
    'FeedbackManager',
    'WorkflowManager',
    'Notifier',
    'FTSIndex',
    'ConceptCache',
    'EmbedIncremental',
    'PaginatedQuerier',
    'BackupManager',
    'UnifiedWebServer',
    'QAEngine',
    'DuplicateDetector',
    'QualityChecker',
    'ShareLinkManager',
    'SensitiveInfoMasker',
    'WebhookNotifier',
    # 迁移工具
    'MigrationManager',
    'MigrationResult',
    'MigrationValidator',
    'ValidationResult',
]
