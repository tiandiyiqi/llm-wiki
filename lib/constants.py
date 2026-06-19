# OKF Reserved filenames (§3.1)
RESERVED_FILES = {'index.md', 'log.md'}

# OKF Required frontmatter fields (§4.1)
REQUIRED_FIELDS = {'type'}

# OKF Recommended frontmatter fields (§4.1)
RECOMMENDED_FIELDS = ['title', 'description', 'resource', 'tags', 'timestamp']

# Knowledge types mapping
TYPE_DIRS = {
    'fact': 'facts',
    'opinion': 'opinions',
    'definition': 'definitions',
    'method': 'methods',
    'data': 'data',
    'question': 'questions',
    'reference': 'references'
}

# KB Meta Schema for parent-child knowledge base architecture
KB_META_SCHEMA = {
    'kb_type': 'standalone',  # standalone / parent / child
    'name': '',
    'children': [],           # List of child KB names (for parent)
    'children_paths': {},     # Dict of child_name -> relative_path (for parent)
    'parent': None,           # Parent KB name (for child)
    'parent_path': None       # Relative path to parent (for child)
}

# Optional: semantic search dependencies
# 使用顶层 try/except 检测可选依赖是否可用，而非导入时即报错。
# 这允许核心功能在缺少可选依赖时正常工作，语义搜索功能会在此检测失败时优雅降级。
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
