"""CLI command handlers for LLM Wiki."""

import json
import sys
from pathlib import Path
from typing import Optional

from . import (
    KBRegistry,
    OKFValidator,
    OKFExporter,
    OKFImporter,
    KBInitializer,
    IndexGenerator,
    KnowledgeIngestor,
    AggregatedQuerier,
    KnowledgeQuerier,
    SemanticSearchEngine,
    KnowledgeVisualizer,
    TimelineGenerator,
    QuickCapture,
    DiscoveryEngine,
    KnowledgeWatcher,
    WebDataExporter,
    create_web_ui
)


def resolve_kb(args) -> Optional[Path]:
    """解析知识库路径，支持名称、路径或当前知识库"""
    registry = KBRegistry(project_dir=Path.cwd())

    if hasattr(args, 'knowledge_base') and args.knowledge_base:
        resolved = registry.resolve_path(args.knowledge_base)
        if resolved:
            return resolved
        path = Path(args.knowledge_base)
        if path.exists():
            return path
        print(f"❌ Knowledge base not found: {args.knowledge_base}")
        return None

    current = registry.get_current()
    if current:
        kb = registry.get(current)
        if kb:
            return Path(kb['path'])

    print("❌ 未指定知识库，请使用 'llm-wiki use <name>' 设置当前知识库")
    return None


def cmd_register(args):
    """注册知识库"""
    registry = KBRegistry(project_dir=Path.cwd())
    path = Path(args.path).resolve()

    parent = getattr(args, 'parent', None)
    kb_type = 'child' if parent else 'standalone'

    meta_path = path / '.kb-meta.json'
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
            kb_type = meta.get('kb_type', 'standalone')
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    success = registry.register(
        path=path,
        name=args.name,
        description=getattr(args, 'description', None),
        tags=getattr(args, 'tags', '').split(',') if getattr(args, 'tags', None) else None,
        scope=args.scope,
        kb_type=kb_type,
        parent=parent
    )

    if success:
        print(f"✅ Registered: {args.name or path.name}")
        print(f"   Path: {path}")
        print(f"   Type: {kb_type}")
        if parent:
            print(f"   Parent: {parent}")
    else:
        print(f"❌ Failed to register: {path}")
        sys.exit(1)


def cmd_unregister(args):
    """注销知识库"""
    registry = KBRegistry(project_dir=Path.cwd())
    success = registry.unregister(args.name, scope=args.scope)
    if success:
        print(f"✅ Unregistered: {args.name}")
    else:
        print(f"❌ Not found: {args.name}")
        sys.exit(1)


def cmd_list(args):
    """列出所有知识库"""
    registry = KBRegistry(project_dir=Path.cwd())
    kbs = registry.list(scope=args.scope)
    current = registry.get_current()

    if not kbs:
        print("📚 No registered knowledge bases")
        print("\nUse 'llm-wiki register <path> --name <name>' to register")
        return

    print("📚 Registered Knowledge Bases:\n")

    parents = [kb for kb in kbs if kb.get('kb_type') == 'parent']
    children = [kb for kb in kbs if kb.get('kb_type') == 'child']
    standalone = [kb for kb in kbs if kb.get('kb_type', 'standalone') == 'standalone']

    for parent in parents:
        marker = " (current)" if parent['name'] == current else ""
        scope_marker = " [project]" if parent.get('scope') == 'project' else " [global]"
        print(f"  📁 {parent['name']}{marker}{scope_marker}")
        print(f"     Path: {parent['path']}")
        stats = parent.get('statistics', {})
        concepts = stats.get('concepts', 'N/A')
        children_list = parent.get('children', [])
        print(f"     Type: parent | Concepts: {concepts} | Children: {len(children_list)}")

        for child_name in children_list:
            child_kb = next((kb for kb in children if kb['name'] == child_name), None)
            if child_kb:
                child_marker = " (current)" if child_kb['name'] == current else ""
                print(f"     └─ 📄 {child_name}{child_marker}")
                if args.verbose:
                    child_stats = child_kb.get('statistics', {})
                    print(f"        Concepts: {child_stats.get('concepts', 'N/A')}")
        print()

    displayed_children = set()
    for parent in parents:
        displayed_children.update(parent.get('children', []))

    orphan_children = [kb for kb in children if kb['name'] not in displayed_children]
    for child in orphan_children:
        marker = " (current)" if child['name'] == current else ""
        scope_marker = " [project]" if child.get('scope') == 'project' else " [global]"
        print(f"  📄 {child['name']}{marker}{scope_marker}")
        print(f"     Path: {child['path']}")
        print(f"     Type: child | Parent: {child.get('parent', 'N/A')}")
        print()

    for kb in standalone:
        marker = " (current)" if kb['name'] == current else ""
        scope_marker = " [project]" if kb.get('scope') == 'project' else " [global]"
        print(f"  📦 {kb['name']}{marker}{scope_marker}")
        print(f"     Path: {kb['path']}")

        stats = kb.get('statistics', {})
        concepts = stats.get('concepts', 'N/A')
        if args.verbose:
            types = stats.get('types', {})
            types_str = ', '.join(f"{t}({n})" for t, n in types.items()) if types else 'N/A'
            print(f"     Concepts: {concepts} | Types: {types_str}")
            print(f"     Description: {kb.get('description', 'N/A')}")
            print(f"     Tags: {', '.join(kb.get('tags', [])) or 'N/A'}")
        else:
            print(f"     Concepts: {concepts}")
        print()


def cmd_use(args):
    """设置当前知识库"""
    registry = KBRegistry(project_dir=Path.cwd())
    success = registry.set_current(args.name, scope=args.scope)
    if success:
        print(f"✅ Current knowledge base: {args.name}")
    sys.exit(0 if success else 1)


def cmd_info(args):
    """查看知识库详情"""
    registry = KBRegistry(project_dir=Path.cwd())
    name = args.name or registry.get_current()
    if not name:
        print("❌ No current knowledge base. Use 'llm-wiki use <name>'")
        sys.exit(1)

    kb = registry.get(name)
    if not kb:
        print(f"❌ Knowledge base not found: {name}")
        sys.exit(1)

    print(f"📚 {kb['name']}")
    print(f"   Path: {kb['path']}")
    print(f"   Type: {kb.get('kb_type', 'standalone')}")

    if kb.get('description'):
        print(f"   Description: {kb['description']}")

    if kb.get('tags'):
        print(f"   Tags: {', '.join(kb['tags'])}")

    stats = kb.get('statistics', {})
    if stats:
        print(f"   Concepts: {stats.get('concepts', 'N/A')}")
        types = stats.get('types', {})
        if types:
            print(f"   Types: {', '.join(f'{t}({n})' for t, n in types.items())}")

    if kb.get('kb_type') == 'parent':
        children = kb.get('children', [])
        print(f"   Children: {len(children)}")
        for child in children:
            print(f"      - {child}")

    if kb.get('kb_type') == 'child':
        print(f"   Parent: {kb.get('parent', 'N/A')}")

    print(f"   Last accessed: {kb.get('last_accessed', 'N/A')[:10]}")
    print(f"   Registered: {kb.get('registered', 'N/A')[:10]}")


def cmd_init(args):
    """初始化知识库"""
    kb_path = Path(args.knowledge_base).resolve()

    if kb_path.exists() and not args.force:
        print(f"❌ Directory already exists: {kb_path}")
        print("   Use --force to overwrite")
        sys.exit(1)

    initializer = KBInitializer(kb_path)
    kwargs = {}
    if args.name:
        kwargs['name'] = args.name
    if args.description:
        kwargs['description'] = args.description
    if args.tags:
        kwargs['tags'] = args.tags.split(',')

    if args.parent:
        initializer.init_parent(**kwargs)
        print(f"✅ Parent knowledge base initialized: {kb_path}")
    elif args.child:
        if not args.parent_kb:
            print("❌ --parent-kb is required for child knowledge base")
            sys.exit(1)
        parent_kb_path = Path(args.parent_kb).resolve()
        initializer.init_child(parent_kb_path, **kwargs)
        print(f"✅ Child knowledge base initialized: {kb_path}")
        print(f"   Parent: {parent_kb_path}")
    else:
        initializer.init_standalone(**kwargs)
        print(f"✅ Knowledge base initialized: {kb_path}")

    if args.register:
        registry = KBRegistry(project_dir=Path.cwd())
        name = args.name or kb_path.name
        registry.register(kb_path, name=name, scope=args.scope)
        print(f"✅ Registered as: {name}")


def cmd_ingest(args):
    """摄入资料"""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    ingestor = KnowledgeIngestor(kb_dir)
    source = Path(args.source)
    ingestor.ingest(source)
    print(f"✅ Ingested: {source}")


def cmd_embed(args):
    """生成向量嵌入"""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    try:
        from lib import SemanticSearchEngine
        engine = SemanticSearchEngine(kb_dir)
        count = engine.embed_all()
        print(f"✅ Embedded {count} atoms")
    except ImportError:
        print("❌ Semantic search requires: pip install chromadb sentence-transformers")
        sys.exit(1)


def cmd_query(args):
    """查询知识"""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    if args.child:
        querier = AggregatedQuerier(kb_dir)
        results = querier.query_child(args.child, args.question)
    else:
        querier = KnowledgeQuerier(kb_dir)
        results = querier.query(args.question, semantic=args.semantic)

    print(f"\n🔍 Results for: '{args.question}'\n")
    for r in results[:10]:
        print(f"  [{r.get('score', 0):.2f}] {r['title']}")
        print(f"         {r['path']}")
        if r.get('snippet'):
            print(f"         {r['snippet'][:100]}...")


def cmd_lint(args):
    """OKF 兼容性检查"""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    validator = OKFValidator()
    valid, errors, warnings = validator.validate_bundle(kb_dir)

    if valid:
        print(f"✅ Valid OKF bundle: {kb_dir}")
    else:
        print(f"❌ Invalid OKF bundle: {kb_dir}")

    for path, msg in errors:
        print(f"   ERROR: {path}: {msg}")

    for path, msg in warnings:
        print(f"   WARNING: {path}: {msg}")

    if args.okf_check:
        print(f"\n📊 Statistics:")
        types = validator._count_types()
        for t, n in types.items():
            print(f"   {t}: {n}")

    sys.exit(0 if valid else 1)


def cmd_index(args):
    """生成目录索引"""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    generator = IndexGenerator(kb_dir)
    if args.directory:
        target = Path(args.directory)
        generator.generate(target)
    else:
        generator.generate_all()
    print(f"✅ Index generated")


def cmd_export(args):
    """导出 OKF Bundle"""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    output = args.output or Path(f"{kb_dir.name}.tar.gz")
    exporter = OKFExporter(kb_dir)
    exporter.export(output, validate=args.validate, include_children=args.include_children)
    print(f"✅ Exported to: {output}")


def cmd_import(args):
    """导入 OKF Bundle"""
    importer = OKFImporter()
    importer.import_bundle(args.bundle, args.output, overwrite=args.overwrite)
    print(f"✅ Imported to: {args.output}")


def cmd_visualize(args):
    """生成知识图谱"""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    output = args.output or kb_dir / 'views' / 'knowledge-graph.html'
    output.parent.mkdir(parents=True, exist_ok=True)

    visualizer = KnowledgeVisualizer(kb_dir, output)
    visualizer.visualize(name=args.name or kb_dir.name)
    print(f"✅ Knowledge graph: {output}")


def cmd_timeline(args):
    """生成时间线"""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    output = args.output or kb_dir / 'views' / 'timeline.html'
    output.parent.mkdir(parents=True, exist_ok=True)

    generator = TimelineGenerator(kb_dir)
    generator.generate(output)
    print(f"✅ Timeline: {output}")


def cmd_capture(args):
    """快速捕获"""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    capture = QuickCapture(kb_dir)
    atom_id = capture.capture(args.content, atom_type=args.type)
    print(f"✅ Captured: {atom_id}")


def cmd_watch(args):
    """文件监控"""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    watcher = KnowledgeWatcher(kb_dir)
    watcher.watch()


def cmd_gaps(args):
    """发现知识缺口"""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    discovery = DiscoveryEngine(kb_dir)
    gaps = discovery.find_gaps()

    print(f"\n📊 Knowledge Gaps ({len(gaps)})\n")
    for gap in gaps[:20]:
        priority = gap.get('priority', 'medium')
        icon = "🔴" if priority == "high" else "🟡" if priority == "medium" else "🟢"
        print(f"  {icon} [{priority}] {gap['id']}")
        print(f"      {gap.get('description', 'No description')}")


def cmd_relations(args):
    """发现原子关系"""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    discovery = DiscoveryEngine(kb_dir)
    relations = discovery.find_relations()

    print(f"\n🔗 Discovered Relations ({len(relations)})\n")
    for rel in relations[:20]:
        print(f"  {rel['source']} --[{rel['type']}]--> {rel['target']}")


def cmd_heads_up(args):
    """主动推送"""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    discovery = DiscoveryEngine(kb_dir)
    recommendations = discovery.recommend()

    print(f"\n💡 Recommendations ({len(recommendations)})\n")
    for rec in recommendations[:10]:
        print(f"  [{rec['type']}] {rec['title']}")
        print(f"      {rec['description'][:100]}")


def cmd_web_ui(args):
    """创建 Web UI - 一键生成所有视图文件。"""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    create_web_ui(kb_dir)
    sys.exit(0)
