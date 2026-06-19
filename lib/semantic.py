"""Semantic search using ChromaDB and sentence-transformers."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .constants import RESERVED_FILES, CHROMA_AVAILABLE, EMBEDDINGS_AVAILABLE
from .yaml_parser import SimpleYAMLParser


class SemanticSearchEngine:
    """Semantic search using ChromaDB and sentence-transformers."""

    def __init__(self, kb_dir: Path):
        self.kb_dir = kb_dir
        self.yaml_parser = SimpleYAMLParser()
        self.chroma_dir = kb_dir / '.chroma'
        self.collection_name = 'knowledge_atoms'
        self.model = None
        self.collection = None
        self.concepts: List[Dict] = []

    def is_available(self) -> bool:
        """Check if semantic search dependencies are available."""
        return CHROMA_AVAILABLE and EMBEDDINGS_AVAILABLE

    def check_dependencies(self) -> Tuple[bool, str]:
        """Check and report dependency status."""
        missing = []
        if not CHROMA_AVAILABLE:
            missing.append('chromadb')
        if not EMBEDDINGS_AVAILABLE:
            missing.append('sentence-transformers')

        if missing:
            return False, f"Missing dependencies: {', '.join(missing)}. Install with: pip install {' '.join(missing)}"
        return True, "All dependencies available"

    def initialize(self) -> bool:
        """Initialize the embedding model and ChromaDB."""
        if not self.is_available():
            return False

        try:
            import chromadb
            from chromadb.config import Settings
            from sentence_transformers import SentenceTransformer

            # Initialize embedding model (download if needed)
            print("   Loading embedding model (first run may take a while)...")
            self.model = SentenceTransformer('all-MiniLM-L6-v2')

            # Initialize ChromaDB
            self.chroma_dir.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(self.chroma_dir))

            # Get or create collection
            self.collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )

            return True
        except (ImportError, RuntimeError, OSError) as e:
            # ImportError: chromadb 或 sentence_transformers 安装问题
            # RuntimeError: 模型加载失败
            # OSError: 文件系统问题
            print(f"   ❌ Error initializing semantic search: {e}")
            return False

    def embed_all(self) -> bool:
        """Generate embeddings for all concepts in the knowledge base."""
        available, msg = self.check_dependencies()
        if not available:
            print(f"❌ {msg}")
            return False

        print(f"📊 Generating embeddings for: {self.kb_dir}")

        # Load all concepts
        self._load_concepts()

        if not self.concepts:
            print("   No concepts found in knowledge base")
            return False

        print(f"   Concepts to embed: {len(self.concepts)}")

        # Initialize
        if not self.initialize():
            return False

        # Prepare documents for embedding
        ids = []
        documents = []
        metadatas = []

        for concept in self.concepts:
            # Create document text for embedding
            doc_text = self._create_embedding_text(concept)
            ids.append(concept['id'])
            documents.append(doc_text)
            metadatas.append({
                'type': concept['type'],
                'title': concept['title'],
                'path': concept['path']
            })

        # Generate embeddings
        print("   Generating embeddings...")
        embeddings = self.model.encode(documents, show_progress_bar=True)

        # Upsert to ChromaDB
        print("   Storing in ChromaDB...")
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings.tolist(),
            documents=documents,
            metadatas=metadatas
        )

        print(f"\n✅ Embeddings generated for {len(self.concepts)} concepts")
        print(f"   Stored in: {self.chroma_dir}")

        return True

    def search(self, query_str: str, limit: int = 10, by_type: Optional[str] = None) -> List[Dict]:
        """Perform semantic search."""
        if not self.is_available():
            return []

        # Initialize if needed
        if self.collection is None:
            if not self.initialize():
                return []

        # Check if collection has data
        if self.collection.count() == 0:
            print("   ⚠️  No embeddings found. Run 'llm-wiki embed' first.")
            return []

        # Generate query embedding
        query_embedding = self.model.encode([query_str])[0].tolist()

        # Build where filter
        where_filter = None
        if by_type:
            where_filter = {"type": by_type}

        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=limit,
            where=where_filter,
            include=['documents', 'metadatas', 'distances']
        )

        # Format results
        formatted_results = []
        for i, doc_id in enumerate(results['ids'][0]):
            distance = results['distances'][0][i] if 'distances' in results else 0
            similarity = 1 - distance  # Convert distance to similarity

            formatted_results.append({
                'id': doc_id,
                'path': results['metadatas'][0][i].get('path', ''),
                'type': results['metadatas'][0][i].get('type', 'Unknown'),
                'title': results['metadatas'][0][i].get('title', ''),
                'description': results['documents'][0][i][:200] if results['documents'] else '',
                'score': int(similarity * 100),
                'match_type': 'semantic',
                'similarity': round(similarity, 3)
            })

        return formatted_results

    def _load_concepts(self) -> None:
        """Load all concepts from knowledge base."""
        for md_file in self.kb_dir.rglob('*.md'):
            if md_file.name in RESERVED_FILES:
                continue

            content = md_file.read_text(encoding='utf-8')

            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    fm = self.yaml_parser.parse(parts[1])
                    if fm:
                        body = parts[2] if len(parts) >= 3 else ''
                        self.concepts.append({
                            'id': str(md_file.relative_to(self.kb_dir)).replace('.md', ''),
                            'path': str(md_file.relative_to(self.kb_dir)),
                            'type': fm.get('type', 'Unknown'),
                            'title': fm.get('title', md_file.stem),
                            'description': fm.get('description', ''),
                            'tags': fm.get('tags', []),
                            'body': body
                        })

    def _create_embedding_text(self, concept: Dict) -> str:
        """Create text for embedding from concept."""
        parts = []

        # Title is most important
        parts.append(f"Title: {concept['title']}")

        # Type
        parts.append(f"Type: {concept['type']}")

        # Description
        if concept['description']:
            parts.append(f"Description: {concept['description']}")

        # Tags
        if concept['tags']:
            parts.append(f"Tags: {', '.join(concept['tags'])}")

        # Body (truncated)
        body_clean = re.sub(r'[#*\[\]]', '', concept['body'][:500])
        parts.append(f"Content: {body_clean}")

        return '\n'.join(parts)