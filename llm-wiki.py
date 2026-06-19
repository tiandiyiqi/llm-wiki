#!/usr/bin/env python3
"""
LLM Wiki CLI - OKF 知识库管理工具

基于 Open Knowledge Format (OKF) v0.1 规范的知识库管理命令行工具。

Usage:
    llm-wiki <command> [options]

Commands:
    init        初始化知识库目录结构
    ingest      摄入资料提取知识原子
    query       搜索查询知识（支持语义搜索）
    embed       生成向量嵌入（需要 chromadb）
    lint        检查 OKF 兼容性
    index       生成目录索引
    export      导出知识库为 OKF Bundle
    import      导入 OKF Bundle 到知识库
    visualize   生成知识图谱可视化 HTML
    register    注册知识库
    unregister  注销知识库
    list        列出所有知识库
    use         设置当前知识库
    info        查看知识库详情
    capture     一句话捕获知识原子
    watch       启动文件监控

Examples:
    llm-wiki init ./my-kb
    llm-wiki ingest ./my-kb raw/doc.md
    llm-wiki embed ./my-kb                    # 生成向量嵌入
    llm-wiki query ./my-kb "installation"     # 关键词搜索
    llm-wiki query ./my-kb "如何部署" --semantic  # 语义搜索
    llm-wiki lint ./my-kb --okf-check
    llm-wiki visualize ./my-kb --output views/graph.html
    llm-wiki export ./my-kb --output bundle.tar.gz
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from lib import (
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
    KnowledgeWatcher
)


def resolve_kb(args) -> Optional[Path]:
    """解析知识库路径，支持名称、路径或当前知识库"""
    registry = KBRegistry(project_dir=Path.cwd())

    if hasattr(args, 'knowledge_base') and args.knowledge_base:
        # 尝试作为名称解析，失败则作为路径
        resolved = registry.resolve_path(args.knowledge_base)
        if resolved:
            return resolved
        # 作为路径
        path = Path(args.knowledge_base)
        if path.exists():
            return path
        print(f"❌ Knowledge base not found: {args.knowledge_base}")
        return None

    # 使用当前知识库
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

    # 检查是否有 --parent 参数
    parent = getattr(args, 'parent', None)
    kb_type = 'child' if parent else 'standalone'

    # 检查知识库是否有 .kb-meta.json 以确定类型
    meta_path = path / '.kb-meta.json'
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
            kb_type = meta.get('kb_type', 'standalone')
            if not parent and meta.get('parent'):
                parent = meta.get('parent')
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    success = registry.register(
        path=path,
        name=args.name or path.name,
        description=args.description or "",
        tags=args.tags.split(',') if args.tags else [],
        scope=args.scope,
        kb_type=kb_type,
        parent=parent
    )
    sys.exit(0 if success else 1)


def cmd_unregister(args):
    """注销知识库"""
    registry = KBRegistry(project_dir=Path.cwd())
    success = registry.unregister(args.name, scope=args.scope)
    sys.exit(0 if success else 1)


def cmd_list(args):
    """列出所有知识库"""
    registry = KBRegistry(project_dir=Path.cwd())
    kbs = registry.list(scope=args.scope)
    current = registry.get_current()

    if not kbs:
        print("📚 No registered knowledge bases")
        print("\nUse 'llm-wiki register <path> --name <name>' to register a knowledge base")
        return

    print("📚 Registered Knowledge Bases:\n")

    # 按 kb_type 分组显示
    parents = [kb for kb in kbs if kb.get('kb_type') == 'parent']
    children = [kb for kb in kbs if kb.get('kb_type') == 'child']
    standalone = [kb for kb in kbs if kb.get('kb_type', 'standalone') == 'standalone']

    # 先显示父知识库及其子知识库
    for parent in parents:
        marker = " (current)" if parent['name'] == current else ""
        scope_marker = " [project]" if parent.get('scope') == 'project' else " [global]"
        print(f"  📁 {parent['name']}{marker}{scope_marker}")
        print(f"     Path: {parent['path']}")
        stats = parent.get('statistics', {})
        concepts = stats.get('concepts', 'N/A')
        children_list = parent.get('children', [])
        print(f"     Type: parent | Concepts: {concepts} | Children: {len(children_list)}")

        # 显示子知识库
        for child_name in children_list:
            child_kb = next((kb for kb in children if kb['name'] == child_name), None)
            if child_kb:
                child_marker = " (current)" if child_kb['name'] == current else ""
                print(f"     └─ 📄 {child_name}{child_marker}")
                if args.verbose:
                    child_stats = child_kb.get('statistics', {})
                    child_concepts = child_stats.get('concepts', 'N/A')
                    print(f"        Concepts: {child_concepts}")
        print()

    # 显示独立的子知识库（未找到父级）
    displayed_children = set()
    for parent in parents:
        displayed_children.update(parent.get('children', []))

    orphan_children = [kb for kb in children if kb['name'] not in displayed_children]
    for child in orphan_children:
        marker = " (current)" if child['name'] == current else ""
        scope_marker = " [project]" if child.get('scope') == 'project' else " [global]"
        parent_name = child.get('parent', 'N/A')
        print(f"  📄 {child['name']}{marker}{scope_marker}")
        print(f"     Path: {child['path']}")
        print(f"     Type: child | Parent: {parent_name}")
        print()

    # 显示独立知识库
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
            print(f"     Last accessed: {kb.get('last_accessed', 'N/A')[:10]}")
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
        print("❌ No knowledge base specified and no current knowledge base set")
        sys.exit(1)

    kb = registry.get(name)
    if not kb:
        print(f"❌ Knowledge base not found: {name}")
        sys.exit(1)

    print(f"\n📚 Knowledge Base: {name}\n")
    print(f"  Scope: {kb.get('scope', 'unknown')}")
    print(f"  Path: {kb['path']}")
    print(f"  Description: {kb.get('description', 'N/A')}")
    print(f"  Tags: {', '.join(kb.get('tags', [])) or 'N/A'}")
    print(f"  Created: {kb.get('created', 'N/A')[:10]}")
    print(f"  Last accessed: {kb.get('last_accessed', 'N/A')[:10]}")

    # 显示父子知识库关系
    kb_type = kb.get('kb_type', 'standalone')
    if kb_type == 'parent':
        print(f"\n  🔗 Parent Knowledge Base")
        children = kb.get('children', [])
        children_paths = kb.get('children_paths', {})
        print(f"     Children: {len(children)}")
        for child_name in children:
            child_path = children_paths.get(child_name, 'N/A')
            print(f"       - {child_name} → {child_path}")
    elif kb_type == 'child':
        print(f"\n  🔗 Child Knowledge Base")
        print(f"     Parent: {kb.get('parent', 'N/A')}")
        print(f"     Parent path: {kb.get('parent_path', 'N/A')}")
    else:
        print(f"\n  📦 Standalone Knowledge Base")

    stats = kb.get('statistics', {})

    # 如果是父知识库，聚合所有子知识库的统计
    if kb_type == 'parent':
        total_concepts = stats.get('concepts', 0)
        children = kb.get('children', [])
        for child_name in children:
            child_kb = registry.get(child_name)
            if child_kb:
                child_stats = child_kb.get('statistics', {})
                total_concepts += child_stats.get('concepts', 0)
        print(f"\n  Statistics:")
        print(f"    Concepts (parent only): {stats.get('concepts', 'N/A')}")
        print(f"    Concepts (aggregated): {total_concepts}")
    else:
        print(f"\n  Statistics:")
        print(f"    Concepts: {stats.get('concepts', 'N/A')}")

    types = stats.get('types', {})
    if types:
        print(f"    Types:")
        for t, n in sorted(types.items()):
            print(f"      - {t}: {n}")

    # 检查路径是否存在
    kb_path = Path(kb['path'])
    if kb_path.exists():
        print(f"\n  ✅ Path exists")

        # 检查是否有嵌入
        chroma_dir = kb_path / '.chroma'
        if chroma_dir.exists():
            print(f"  ✅ Semantic embeddings available")
        else:
            print(f"  ⚠️  No semantic embeddings (run 'llm-wiki embed {name}')")
    else:
        print(f"\n  ❌ Path does not exist")


def cmd_init(args):
    kb_dir = Path(args.knowledge_base)

    # 检查是否是父/子知识库模式
    is_parent = getattr(args, 'parent', False)
    is_child = getattr(args, 'child', False)
    parent_kb = Path(args.parent_kb) if getattr(args, 'parent_kb', None) else None

    initializer = KBInitializer(
        kb_dir=kb_dir,
        is_parent=is_parent,
        is_child=is_child,
        parent_kb=parent_kb,
        name=args.name
    )
    success = initializer.init()

    # 如果初始化成功且指定了 --register
    if success and args.register:
        registry = KBRegistry(project_dir=Path.cwd())

        # 确定 kb_type
        kb_type = 'parent' if is_parent else ('child' if is_child else 'standalone')
        parent_name = None
        if is_child and parent_kb:
            # 尝试从父知识库的 .kb-meta.json 获取名称
            parent_meta_path = parent_kb / '.kb-meta.json'
            if parent_meta_path.exists():
                parent_meta = json.loads(parent_meta_path.read_text(encoding='utf-8'))
                parent_name = parent_meta.get('name', parent_kb.name)

        registry.register(
            path=kb_dir,
            name=args.name or kb_dir.name,
            description=args.description or "",
            tags=args.tags.split(',') if args.tags else [],
            scope=args.scope,
            kb_type=kb_type,
            parent=parent_name
        )

    sys.exit(0 if success else 1)


def cmd_ingest(args):
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    source_path = Path(args.source)

    ingestor = KnowledgeIngestor(kb_dir, source_path)
    success = ingestor.ingest(
        auto_detect_type=args.auto_type,
        default_type=args.type
    )
    sys.exit(0 if success else 1)


def cmd_embed(args):
    """Generate embeddings for semantic search."""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    engine = SemanticSearchEngine(kb_dir)
    success = engine.embed_all()
    sys.exit(0 if success else 1)


def cmd_query(args):
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    # 检查是否是父知识库（需要聚合查询）
    meta_path = kb_dir / '.kb-meta.json'
    is_parent = False
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
            is_parent = meta.get('kb_type') == 'parent'
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    # 也从注册表检查
    registry = KBRegistry(project_dir=Path.cwd())
    kb_name = kb_dir.name
    kb_info = registry.get(kb_name)
    if kb_info and kb_info.get('kb_type') == 'parent':
        is_parent = True

    # 如果是父知识库，使用聚合查询
    if is_parent and not args.semantic:
        # 获取 child_filter 参数
        child_filter = getattr(args, 'child', None)

        agg_querier = AggregatedQuerier(kb_dir, registry)
        success = agg_querier.aggregate_query(
            query_str=args.query,
            limit=args.limit,
            by_type=args.type,
            child_filter=child_filter
        )
        sys.exit(0 if success else 1)

    # Check if semantic search requested
    if args.semantic:
        engine = SemanticSearchEngine(kb_dir)

        # Check dependencies
        available, msg = engine.check_dependencies()
        if not available:
            print(f"❌ {msg}")
            sys.exit(1)

        # Perform semantic search
        results = engine.search(
            query_str=args.query,
            limit=args.limit,
            by_type=args.type
        )

        if not results:
            print(f"\n   No results found for '{args.query}'")
            sys.exit(0)

        # Display results
        print(f"\n🔍 Semantic search results ({len(results)}):")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. [{result['type']}] {result['title']}")
            print(f"   Path: {result['path']}")
            print(f"   Similarity: {result['similarity']:.3f}")
            print(f"   {result['description'][:80]}...")
    else:
        # Keyword search (default)
        querier = KnowledgeQuerier(kb_dir)
        success = querier.query(
            query_str=args.query,
            limit=args.limit,
            by_type=args.type
        )
        sys.exit(0 if success else 1)


def cmd_lint(args):
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    validator = OKFValidator()

    print(f"📦 Validating OKF conformance: {kb_dir}")

    is_valid, errors, warnings = validator.validate_bundle(kb_dir)

    print(f"\n📊 Results:")
    print(f"   Concepts: {len(validator.concepts)}")
    print(f"   Valid: {'✅ Yes' if is_valid else '❌ No'}")

    if errors:
        print(f"\n❌ Errors ({len(errors)}):")
        for file_path, error in errors:
            print(f"   {file_path}: {error}")

    if warnings:
        print(f"\n⚠️  Warnings ({len(warnings)}):")
        for file_path, warning in warnings[:10]:
            print(f"   {file_path}: {warning}")
        if len(warnings) > 10:
            print(f"   ... and {len(warnings) - 10} more")

    if args.okf_check:
        print(f"\n📋 OKF v0.1 Conformance Check:")
        # Check if any errors relate to frontmatter
        has_frontmatter_errors = any('frontmatter' in e[1].lower() for e in errors)
        print(f"   ✅ All .md files have frontmatter: {'✅ Yes' if not has_frontmatter_errors else '❌ No'}")

        # Check if any errors relate to missing type field
        has_type_errors = any('type' in e[1].lower() and 'missing' in e[1].lower() for e in errors)
        print(f"   ✅ All frontmatter have 'type': {'✅ Yes' if not has_type_errors else '❌ No'}")

        # Check if reserved files have errors
        has_reserved_errors = any('index.md' in e[0] or 'log.md' in e[0] for e in errors)
        print(f"   ✅ Reserved files valid: {'✅ Yes' if not has_reserved_errors else '❌ No'}")

    sys.exit(0 if is_valid else 1)


def cmd_index(args):
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    directory = Path(args.directory) if args.directory else None

    generator = IndexGenerator(kb_dir)
    success = generator.generate(directory)
    sys.exit(0 if success else 1)


def cmd_export(args):
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    output_path = Path(args.output) if args.output else None
    include_children = getattr(args, 'include_children', False)

    exporter = OKFExporter(kb_dir, output_path, include_children=include_children)
    success = exporter.export(
        validate=args.validate and not args.no_validate,
        force=args.force
    )
    sys.exit(0 if success else 1)


def cmd_import(args):
    bundle_path = Path(args.bundle)
    output_dir = Path(args.output) if args.output else Path('.')

    importer = OKFImporter(bundle_path, output_dir)
    success = importer.import_bundle(overwrite=args.overwrite)
    sys.exit(0 if success else 1)


def cmd_visualize(args):
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)
    output_path = Path(args.output) if args.output else kb_dir / 'views' / 'knowledge-graph.html'

    visualizer = KnowledgeVisualizer(kb_dir, output_path)

    if getattr(args, 'interactive', False):
        # Generate enhanced interactive HTML
        success = visualizer.generate_interactive_html(output_path)
    else:
        # Generate standard HTML
        success = visualizer.visualize(name=args.name)
    sys.exit(0 if success else 1)


def cmd_timeline(args):
    """Generate timeline view."""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)
    output_path = Path(args.output) if args.output else kb_dir / 'views' / 'timeline.html'

    generator = TimelineGenerator(kb_dir)
    success = generator.generate(output_path)
    sys.exit(0 if success else 1)


def cmd_capture(args):
    """一句话捕获知识原子"""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    capture = QuickCapture(kb_dir)
    success, message = capture.capture(args.text)

    if success:
        print(f"✅ {message}")
    else:
        print(f"❌ {message}")

    sys.exit(0 if success else 1)


def cmd_watch(args):
    """启动文件监控"""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    registry = KBRegistry(project_dir=Path.cwd())
    watcher = KnowledgeWatcher(kb_dir, registry)

    # 确定监控路径
    watch_paths = [kb_dir]

    # 如果指定了额外路径
    if args.paths:
        for p in args.paths:
            path = Path(p)
            if path.exists():
                watch_paths.append(path)

    # 启动监控
    watcher.start(watch_paths)

    try:
        # 阻塞运行
        watcher.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        watcher.stop()


def cmd_gaps(args):
    """发现知识缺口"""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    # 初始化语义搜索引擎（可选）
    semantic_engine = None
    if args.semantic:
        engine = SemanticSearchEngine(kb_dir)
        available, _ = engine.check_dependencies()
        if available:
            semantic_engine = engine

    discovery = DiscoveryEngine(kb_dir, semantic_engine)
    gaps = discovery.find_gaps()

    if not gaps:
        print("✅ 未发现知识缺口")
        sys.exit(0)

    print(f"\n## 知识缺口报告\n")

    # 按严重程度分组
    by_severity = {'high': [], 'medium': [], 'low': []}
    for gap in gaps:
        by_severity.get(gap['severity'], 'medium').append(gap)

    # 高优先级
    if by_severity['high']:
        print("### 高优先级\n")
        for gap in by_severity['high']:
            print(f"- [{gap['type']}] {gap['title']}")
            print(f"  {gap['description']}")
            print(f"  路径: {gap['path']}\n")

    # 中优先级
    if by_severity['medium']:
        print("### 中优先级\n")
        for gap in by_severity['medium']:
            print(f"- [{gap['type']}] {gap['title']}")
            print(f"  {gap['description']}")
            print(f"  路径: {gap['path']}\n")

    # 低优先级
    if by_severity['low']:
        print("### 低优先级\n")
        for gap in by_severity['low']:
            print(f"- [{gap['type']}] {gap['title']}")
            print(f"  {gap['description']}")
            print(f"  路径: {gap['path']}\n")

    print(f"\n总计: {len(gaps)} 个缺口")
    sys.exit(0)


def cmd_relations(args):
    """发现潜在关联"""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    # 初始化语义搜索引擎（可选）
    semantic_engine = None
    chroma_dir = kb_dir / '.chroma'
    if chroma_dir.exists():
        engine = SemanticSearchEngine(kb_dir)
        available, _ = engine.check_dependencies()
        if available:
            semantic_engine = engine

    discovery = DiscoveryEngine(kb_dir, semantic_engine)
    relations = discovery.find_relations(args.atom_id)

    if not relations:
        print(f"未找到 '{args.atom_id}' 的潜在关联")
        sys.exit(0)

    print(f"\n## 潜在关联发现: {args.atom_id}\n")
    print("| 关联原子 | 类型 | 相似度 | 理由 |")
    print("|----------|------|--------|------|")

    for rel in relations:
        similarity = rel.get('similarity', 0)
        print(f"| [[{rel['atom_id']}]] | {rel['relation_type']} | {similarity:.0%} | {rel['reason']} |")

    print(f"\n总计: {len(relations)} 个潜在关联")
    sys.exit(0)


def cmd_heads_up(args):
    """主动推送相关内容"""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    # 初始化语义搜索引擎（可选）
    semantic_engine = None
    chroma_dir = kb_dir / '.chroma'
    if chroma_dir.exists():
        engine = SemanticSearchEngine(kb_dir)
        available, _ = engine.check_dependencies()
        if available:
            semantic_engine = engine

    discovery = DiscoveryEngine(kb_dir, semantic_engine)
    recommendations = discovery.heads_up(args.context, top_k=args.top_k)

    if not recommendations:
        print("未找到相关知识")
        sys.exit(0)

    print(f"\n## 相关知识推荐\n")
    print(f"基于当前上下文，推荐以下知识原子：\n")

    for i, rec in enumerate(recommendations, 1):
        relevance = rec.get('relevance', 0)
        relevance_str = f"{relevance:.0%}" if relevance <= 1 else f"{relevance:.2f}"

        print(f"{i}. **{rec['title']}** [{rec['type']}]")
        print(f"   相关性: {relevance_str} | {rec['reason']}")
        if rec.get('description'):
            print(f"   > {rec['description'][:100]}")
        print()

    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        prog='llm-wiki',
        description='OKF 知识库管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # init command
    init_parser = subparsers.add_parser('init', help='初始化知识库')
    init_parser.add_argument('knowledge_base', type=Path, help='知识库目录路径')
    init_parser.add_argument('--register', action='store_true', help='初始化后注册')
    init_parser.add_argument('--name', '-n', help='知识库别名')
    init_parser.add_argument('--description', '-d', help='描述')
    init_parser.add_argument('--tags', '-t', help='标签（逗号分隔）')
    init_parser.add_argument('--scope', '-s', choices=['auto', 'project', 'global'], default='auto', help='注册范围')
    # 父子知识库参数
    init_parser.add_argument('--parent', action='store_true', help='创建父知识库')
    init_parser.add_argument('--child', action='store_true', help='创建子知识库')
    init_parser.add_argument('--parent-kb', type=Path, help='父知识库路径（创建子知识库时必需）')
    init_parser.set_defaults(func=cmd_init)

    # register command
    register_parser = subparsers.add_parser('register', help='注册知识库')
    register_parser.add_argument('path', type=Path, help='知识库路径')
    register_parser.add_argument('--name', '-n', help='知识库别名')
    register_parser.add_argument('--description', '-d', help='描述')
    register_parser.add_argument('--tags', '-t', help='标签（逗号分隔）')
    register_parser.add_argument('--scope', '-s', choices=['auto', 'project', 'global'], default='auto', help='注册范围')
    register_parser.add_argument('--parent', '-p', help='父知识库名称（注册子知识库时使用）')
    register_parser.set_defaults(func=cmd_register)

    # unregister command
    unregister_parser = subparsers.add_parser('unregister', help='注销知识库')
    unregister_parser.add_argument('name', help='知识库别名')
    unregister_parser.add_argument('--scope', '-s', choices=['auto', 'project', 'global', 'all'], default='all', help='注销范围')
    unregister_parser.set_defaults(func=cmd_unregister)

    # list command
    list_parser = subparsers.add_parser('list', help='列出所有知识库')
    list_parser.add_argument('--scope', '-s', choices=['all', 'project', 'global'], default='all', help='列出范围')
    list_parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    list_parser.set_defaults(func=cmd_list)

    # use command
    use_parser = subparsers.add_parser('use', help='设置当前知识库')
    use_parser.add_argument('name', help='知识库别名')
    use_parser.add_argument('--scope', '-s', choices=['auto', 'project', 'global'], default='auto', help='设置范围')
    use_parser.set_defaults(func=cmd_use)

    # info command
    info_parser = subparsers.add_parser('info', help='查看知识库详情')
    info_parser.add_argument('name', nargs='?', help='知识库别名（默认当前）')
    info_parser.set_defaults(func=cmd_info)

    # ingest command
    ingest_parser = subparsers.add_parser('ingest', help='摄入资料提取原子')
    ingest_parser.add_argument('source', type=Path, help='源文件路径')
    ingest_parser.add_argument('--kb', '-k', dest='knowledge_base', help='知识库路径或名称（默认当前）')
    ingest_parser.add_argument('--type', '-t', default='method', help='原子类型（默认: method）')
    ingest_parser.add_argument('--auto-type', action='store_true', default=True, help='自动检测类型')
    ingest_parser.set_defaults(func=cmd_ingest)

    # embed command
    embed_parser = subparsers.add_parser('embed', help='生成向量嵌入（语义搜索）')
    embed_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称（默认当前）')
    embed_parser.set_defaults(func=cmd_embed)

    # query command
    query_parser = subparsers.add_parser('query', help='搜索查询知识')
    query_parser.add_argument('query', help='查询关键词或问题')
    query_parser.add_argument('--kb', '-k', dest='knowledge_base', help='知识库路径或名称（默认当前）')
    query_parser.add_argument('--type', '-t', help='按类型过滤')
    query_parser.add_argument('--limit', '-l', type=int, default=10, help='结果数量限制')
    query_parser.add_argument('--semantic', '-s', action='store_true', help='启用语义搜索（需要先运行 embed）')
    query_parser.add_argument('--child', '-c', help='仅搜索指定子知识库')
    query_parser.set_defaults(func=cmd_query)

    # lint command
    lint_parser = subparsers.add_parser('lint', help='OKF 兼容性检查')
    lint_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称（默认当前）')
    lint_parser.add_argument('--okf-check', action='store_true', help='显示 OKF 规范检查详情')
    lint_parser.set_defaults(func=cmd_lint)

    # index command
    index_parser = subparsers.add_parser('index', help='生成目录索引')
    index_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称（默认当前）')
    index_parser.add_argument('--directory', '-d', type=Path, help='指定目录')
    index_parser.set_defaults(func=cmd_index)

    # export command
    export_parser = subparsers.add_parser('export', help='导出为 OKF Bundle')
    export_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称（默认当前）')
    export_parser.add_argument('--output', '-o', type=Path, help='输出文件路径')
    export_parser.add_argument('--validate', '-v', action='store_true', default=True, help='验证 OKF 符合性')
    export_parser.add_argument('--no-validate', action='store_true', help='跳过验证')
    export_parser.add_argument('--force', '-f', action='store_true', help='强制导出')
    export_parser.add_argument('--include-children', action='store_true', help='包含子知识库（仅父知识库）')
    export_parser.set_defaults(func=cmd_export)

    # import command
    import_parser = subparsers.add_parser('import', help='导入 OKF Bundle')
    import_parser.add_argument('bundle', type=Path, help='Bundle 文件路径')
    import_parser.add_argument('--output', '-o', type=Path, default=Path('.'), help='输出目录')
    import_parser.add_argument('--overwrite', action='store_true', help='覆盖现有文件')
    import_parser.set_defaults(func=cmd_import)

    # visualize command
    visualize_parser = subparsers.add_parser('visualize', help='生成知识图谱可视化')
    visualize_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称（默认当前）')
    visualize_parser.add_argument('--output', '-o', type=Path, help='输出 HTML 文件路径')
    visualize_parser.add_argument('--name', '-n', help='图谱名称')
    visualize_parser.add_argument('--interactive', '-i', action='store_true', help='生成增强交互式 HTML')
    visualize_parser.set_defaults(func=cmd_visualize)

    # timeline command
    timeline_parser = subparsers.add_parser('timeline', help='生成知识时间线视图')
    timeline_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称（默认当前）')
    timeline_parser.add_argument('--output', '-o', type=Path, help='输出 HTML 文件路径')
    timeline_parser.set_defaults(func=cmd_timeline)

    # gaps command
    gaps_parser = subparsers.add_parser('gaps', help='发现知识缺口')
    gaps_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称（默认当前）')
    gaps_parser.add_argument('--semantic', '-s', action='store_true', help='使用语义分析增强缺口检测')
    gaps_parser.set_defaults(func=cmd_gaps)

    # relations command
    relations_parser = subparsers.add_parser('relations', help='发现潜在关联')
    relations_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称（默认当前）')
    relations_parser.add_argument('atom_id', help='原子 ID')
    relations_parser.set_defaults(func=cmd_relations)

    # heads-up command
    heads_up_parser = subparsers.add_parser('heads-up', help='主动推送相关内容')
    heads_up_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称（默认当前）')
    heads_up_parser.add_argument('context', help='当前上下文')
    heads_up_parser.add_argument('--top-k', '-k', type=int, default=5, help='返回结果数量')
    heads_up_parser.set_defaults(func=cmd_heads_up)

    # capture command
    capture_parser = subparsers.add_parser('capture', help='一句话捕获知识原子')
    capture_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称（默认当前）')
    capture_parser.add_argument('text', help='要捕获的知识文本')
    capture_parser.set_defaults(func=cmd_capture)

    # watch command
    watch_parser = subparsers.add_parser('watch', help='启动文件监控')
    watch_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称（默认当前）')
    watch_parser.add_argument('paths', nargs='*', help='额外监控路径')
    watch_parser.set_defaults(func=cmd_watch)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == '__main__':
    main()