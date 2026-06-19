"""Initializes knowledge base directory structure.

Supports three modes:
- standalone: Regular knowledge base (default)
- parent: Parent knowledge base that can contain child knowledge bases
- child: Child knowledge base nested under a parent
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional


class KBInitializer:
    """Initializes knowledge base directory structure."""

    def __init__(self, kb_dir: Path, is_parent: bool = False,
                 is_child: bool = False, parent_kb: Optional[Path] = None,
                 name: str = None):
        self.kb_dir = kb_dir
        self.is_parent = is_parent
        self.is_child = is_child
        self.parent_kb = parent_kb
        self.name = name or kb_dir.name

    def init(self) -> bool:
        """Initialize knowledge base based on mode."""
        if self.is_parent:
            return self._init_parent()
        elif self.is_child:
            return self._init_child()
        else:
            return self._init_standalone()

    def _init_standalone(self) -> bool:
        """Initialize a standalone knowledge base."""
        print(f"📦 Initializing knowledge base: {self.kb_dir}")

        if self.kb_dir.exists() and any(self.kb_dir.iterdir()):
            print(f"❌ Error: Directory not empty: {self.kb_dir}")
            return False

        # Create directory structure
        dirs = [
            'atoms/methods',
            'atoms/facts',
            'atoms/definitions',
            'atoms/opinions',
            'atoms/data',
            'atoms/questions',
            'atoms/references',
            'raw/reference',
            'raw/observations',
            'views'
        ]

        for d in dirs:
            path = self.kb_dir / d
            path.mkdir(parents=True, exist_ok=True)
            print(f"   Created: {d}")

        # Create root index.md
        index_content = """---
okf_version: "0.1"
---

# Knowledge Base Index

This knowledge base follows the Open Knowledge Format (OKF) v0.1 specification.

## Statistics

- Total atoms: 0

## Directory Structure

| Directory | Purpose |
|-----------|---------|
| `atoms/methods/` | How-to guides and procedures |
| `atoms/facts/` | Verifiable facts |
| `atoms/definitions/` | Concept definitions |
| `atoms/opinions/` | Subjective opinions |
| `atoms/data/` | Numerical data and statistics |
| `atoms/questions/` | Open questions |
| `atoms/references/` | External references |
| `raw/` | Source materials |
| `views/` | Generated views and visualizations |

## Quick Start

1. Add source materials to `raw/`
2. Run `llm-wiki ingest` to extract atoms
3. Run `llm-wiki lint` to validate
4. Run `llm-wiki export` to create bundle
"""

        (self.kb_dir / 'index.md').write_text(index_content)
        print(f"   Created: index.md")

        # Create log.md
        log_content = f"""# Knowledge Base Log

## {datetime.now().strftime('%Y-%m-%d')}

* **Initialization**: Created knowledge base directory structure.
"""

        (self.kb_dir / 'log.md').write_text(log_content)
        print(f"   Created: log.md")

        print(f"\n✅ Knowledge base initialized!")
        print(f"   Path: {self.kb_dir}")
        print(f"\nNext steps:")
        print(f"   1. Add source materials to raw/")
        print(f"   2. Run 'llm-wiki ingest' to extract atoms")
        print(f"   3. Run 'llm-wiki lint' to validate")

        return True

    def _init_parent(self) -> bool:
        """Initialize a parent knowledge base."""
        print(f"📦 Initializing parent knowledge base: {self.kb_dir}")

        if self.kb_dir.exists() and any(self.kb_dir.iterdir()):
            print(f"❌ Error: Directory not empty: {self.kb_dir}")
            return False

        # Create standard directory structure (parent also has its own atoms)
        dirs = [
            'atoms/methods',
            'atoms/facts',
            'atoms/definitions',
            'atoms/opinions',
            'atoms/data',
            'atoms/questions',
            'atoms/references',
            'raw/reference',
            'raw/observations',
            'views'
        ]

        for d in dirs:
            path = self.kb_dir / d
            path.mkdir(parents=True, exist_ok=True)
            print(f"   Created: {d}")

        # Create .kb-meta.json for parent
        meta = {
            'kb_type': 'parent',
            'name': self.name,
            'children': [],
            'children_paths': {},
            'parent': None,
            'parent_path': None
        }
        meta_path = self.kb_dir / '.kb-meta.json'
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"   Created: .kb-meta.json (parent)")

        # Create root index.md
        index_content = f"""---
okf_version: "0.1"
---

# {self.name} - Parent Knowledge Base

This is a **parent knowledge base** that can contain multiple child knowledge bases.

## Structure

- `atoms/` - Common knowledge shared across all child knowledge bases
- Child knowledge bases will be created as subdirectories

## Statistics

- Total atoms: 0
- Child knowledge bases: 0

## Quick Start

1. Add common knowledge to `atoms/`
2. Create child knowledge bases: `llm-wiki init <path> --child --parent-kb {self.kb_dir}`
3. Query across all knowledge bases: `llm-wiki query {self.name} "search term"`
"""

        (self.kb_dir / 'index.md').write_text(index_content)
        print(f"   Created: index.md")

        # Create log.md
        log_content = f"""# Knowledge Base Log

## {datetime.now().strftime('%Y-%m-%d')}

* **Initialization**: Created parent knowledge base structure.
"""

        (self.kb_dir / 'log.md').write_text(log_content)
        print(f"   Created: log.md")

        print(f"\n✅ Parent knowledge base initialized!")
        print(f"   Path: {self.kb_dir}")
        print(f"   Name: {self.name}")
        print(f"\nNext steps:")
        print(f"   1. Add common knowledge to atoms/")
        print(f"   2. Create child knowledge bases with --child flag")

        return True

    def _init_child(self) -> bool:
        """Initialize a child knowledge base under a parent."""
        if not self.parent_kb:
            print(f"❌ Error: --parent-kb is required for child knowledge base")
            return False

        parent_path = Path(self.parent_kb)
        if not parent_path.exists():
            print(f"❌ Error: Parent knowledge base not found: {self.parent_kb}")
            return False

        # Check parent is a valid parent knowledge base
        parent_meta_path = parent_path / '.kb-meta.json'
        if not parent_meta_path.exists():
            print(f"❌ Error: Parent is not a parent knowledge base (missing .kb-meta.json)")
            return False

        print(f"📦 Initializing child knowledge base: {self.kb_dir}")
        print(f"   Parent: {self.parent_kb}")

        # Create directory structure
        dirs = [
            'atoms/methods',
            'atoms/facts',
            'atoms/definitions',
            'atoms/opinions',
            'atoms/data',
            'atoms/questions',
            'atoms/references',
            'raw/reference',
            'raw/observations',
            'views'
        ]

        for d in dirs:
            path = self.kb_dir / d
            path.mkdir(parents=True, exist_ok=True)
            print(f"   Created: {d}")

        # Create .kb-meta.json for child
        rel_path = self.kb_dir.name + '/'  # Relative path from parent
        meta = {
            'kb_type': 'child',
            'name': self.name,
            'children': [],
            'children_paths': {},
            'parent': parent_path.name,
            'parent_path': '..'  # Relative path to parent
        }
        meta_path = self.kb_dir / '.kb-meta.json'
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"   Created: .kb-meta.json (child)")

        # Update parent's .kb-meta.json
        try:
            parent_meta = json.loads(parent_meta_path.read_text(encoding='utf-8'))
            if self.name not in parent_meta.get('children', []):
                parent_meta.setdefault('children', []).append(self.name)
            parent_meta.setdefault('children_paths', {})[self.name] = rel_path
            parent_meta_path.write_text(json.dumps(parent_meta, indent=2, ensure_ascii=False), encoding='utf-8')
            print(f"   Updated parent's .kb-meta.json")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"   Warning: Could not update parent's .kb-meta.json: {e}")

        # Create root index.md
        index_content = f"""---
okf_version: "0.1"
---

# {self.name} - Child Knowledge Base

This is a **child knowledge base** under the parent: {parent_path.name}.

## Statistics

- Total atoms: 0

## Quick Start

1. Add knowledge specific to this domain
2. Query will automatically search across parent and siblings
"""

        (self.kb_dir / 'index.md').write_text(index_content)
        print(f"   Created: index.md")

        # Create log.md
        log_content = f"""# Knowledge Base Log

## {datetime.now().strftime('%Y-%m-%d')}

* **Initialization**: Created child knowledge base under {parent_path.name}.
"""

        (self.kb_dir / 'log.md').write_text(log_content)
        print(f"   Created: log.md")

        print(f"\n✅ Child knowledge base initialized!")
        print(f"   Path: {self.kb_dir}")
        print(f"   Name: {self.name}")
        print(f"   Parent: {parent_path.name}")

        return True