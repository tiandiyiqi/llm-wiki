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

    if kb_path.exists() and any(kb_path.iterdir()) and not args.force:
        print(f"❌ Directory already exists: {kb_path}")
        print("   Use --force to overwrite")
        sys.exit(1)

    # --force 时清空目录
    if args.force and kb_path.exists() and any(kb_path.iterdir()):
        import shutil
        shutil.rmtree(kb_path)
        kb_path.mkdir(parents=True, exist_ok=True)

    # 构造初始化器参数
    init_kwargs = {
        'is_parent': args.parent,
        'is_child': args.child,
        'name': args.name or kb_path.name,
    }
    if args.child and args.parent_kb:
        init_kwargs['parent_kb'] = Path(args.parent_kb).resolve()

    initializer = KBInitializer(kb_path, **init_kwargs)
    if not initializer.init():
        print(f"❌ 初始化失败")
        sys.exit(1)

    print(f"✅ Knowledge base initialized: {kb_path}")

    if args.register:
        registry = KBRegistry(project_dir=Path.cwd())
        name = args.name or kb_path.name
        registry.register(kb_path, name=name, scope=args.scope)
        print(f"✅ Registered as: {name}")


def cmd_ingest(args):
    """摄入资料（支持多格式解析和长文档拆分）"""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    ingestor = KnowledgeIngestor(kb_dir)
    source = Path(args.source)
    success = ingestor.ingest(source)
    if success:
        print(f"✅ Ingested: {source}")
    else:
        print(f"❌ Failed to ingest: {source}")
        sys.exit(1)


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
    """查询知识（支持关键词高亮、多维筛选、排序、语义搜索）"""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    # 构建过滤条件
    filters = {}
    if getattr(args, 'tag', None):
        filters['tag'] = args.tag
    if getattr(args, 'author', None):
        filters['author'] = args.author
    if getattr(args, 'date_from', None):
        filters['date_from'] = args.date_from
    if getattr(args, 'date_to', None):
        filters['date_to'] = args.date_to
    if getattr(args, 'source_type', None):
        filters['source_type'] = args.source_type
    if getattr(args, 'status', None):
        filters['status'] = args.status

    by_type = getattr(args, 'type', None)
    sort_by = getattr(args, 'sort_by', 'relevance')
    limit = getattr(args, 'limit', 10)
    semantic = getattr(args, 'semantic', False)

    if getattr(args, 'child', None):
        querier = AggregatedQuerier(kb_dir)
        results = querier.query_child(args.child, args.question, limit=limit, **filters)
    else:
        querier = KnowledgeQuerier(kb_dir)
        results = querier.query(
            args.question, limit=limit, by_type=by_type,
            semantic=semantic, sort_by=sort_by, **filters
        )

    print(f"\n🔍 Results for: '{args.question}'\n")
    if not results:
        print("   No results found.")
        return

    for i, r in enumerate(results, 1):
        score = r.get('score', 0)
        title = r.get('title_highlighted', r['title'])
        print(f"{i}. [{r.get('type', '?')}] {title}  (score: {score})")
        print(f"   Path: {r['path']}")
        desc = r.get('description_highlighted', r.get('description', ''))
        if desc:
            print(f"   Desc: {desc[:100]}")
        if r.get('snippet'):
            snippet = r.get('snippet_highlighted', r['snippet'])
            print(f"   Snippet: {snippet[:150]}")
        if r.get('tags'):
            print(f"   Tags: {', '.join(r['tags'])}")
        print()


def cmd_suggest(args):
    """搜索联想建议"""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)
    querier = KnowledgeQuerier(kb_dir)
    if getattr(args, 'hot', False):
        hot = querier.get_hot_queries(limit=args.limit)
        print(f"\n🔥 高频搜索词 Top {len(hot)}：")
        for i, (q, count) in enumerate(hot, 1):
            print(f"   {i}. {q} ({count} 次)")
    elif getattr(args, 'no_result', False):
        no_result = querier.get_no_result_queries(limit=args.limit)
        print(f"\n❌ 无结果搜索词（共 {len(no_result)} 条）：")
        for i, q in enumerate(no_result, 1):
            print(f"   {i}. {q}")
    else:
        suggestions = querier.get_suggestions(args.prefix, limit=args.limit)
        print(f"\n💡 联想建议（前缀: '{args.prefix}'）：")
        for i, s in enumerate(suggestions, 1):
            print(f"   {i}. {s}")


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
    """生成知识图谱数据

    将知识库中的原子数据导出为 JSON 格式，用于前端图谱渲染。
    不再生成 HTML 文件，由前端 JavaScript 库负责渲染。

    输出文件: views/data/graph-data.json
    """
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)

    # 输出到 data 目录，便于前端加载
    output = args.output or kb_dir / 'views' / 'data' / 'graph-data.json'
    output.parent.mkdir(parents=True, exist_ok=True)

    visualizer = KnowledgeVisualizer(kb_dir, output)
    success = visualizer.export_graph_data()

    if success:
        print(f"\n💡 提示：")
        print(f"   图谱数据已导出为 JSON 格式")
        print(f"   请使用前端 JavaScript 库渲染图谱")
        print(f"   推荐库: Cytoscape.js, D3.js, vis-network, Sigma.js")
        print(f"\n   启动 HTTP 服务器查看：")
        print(f"   cd {kb_dir}/views && python3 -m http.server 8080")
    else:
        sys.exit(1)


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


# ============================================================================
# 批量操作命令
# ============================================================================

def cmd_batch_ingest(args):
    """批量摄入目录下的文件."""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)
    from .batch_ops import BatchOperations
    ops = BatchOperations(kb_dir)
    source_dir = Path(args.source_dir)
    pattern = getattr(args, 'pattern', '*') or '*'
    recursive = not getattr(args, 'no_recursive', False)
    dry_run = getattr(args, 'dry_run', False)
    ops.batch_ingest(source_dir, pattern, recursive, dry_run)


def cmd_batch_export(args):
    """按条件批量导出原子."""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)
    from .batch_ops import BatchOperations
    ops = BatchOperations(kb_dir)
    output_dir = Path(args.output)
    dry_run = getattr(args, 'dry_run', False)
    ops.batch_export(
        output_dir,
        by_type=getattr(args, 'type', None),
        by_tag=getattr(args, 'tag', None),
        by_status=getattr(args, 'status', None),
        dry_run=dry_run
    )


def cmd_batch_tag(args):
    """批量添加或移除标签."""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)
    from .batch_ops import BatchOperations
    ops = BatchOperations(kb_dir)
    add_tags = args.add.split(',') if getattr(args, 'add', None) else None
    remove_tags = args.remove.split(',') if getattr(args, 'remove', None) else None
    dry_run = getattr(args, 'dry_run', False)
    ops.batch_tag(
        add_tags=add_tags,
        remove_tags=remove_tags,
        by_type=getattr(args, 'type', None),
        by_tag=getattr(args, 'tag', None),
        dry_run=dry_run
    )


def cmd_batch_move(args):
    """批量迁移原子类型."""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)
    from .batch_ops import BatchOperations
    ops = BatchOperations(kb_dir)
    dry_run = getattr(args, 'dry_run', False)
    ops.batch_move(
        target_type=args.target_type,
        by_type=getattr(args, 'from_type', None),
        by_tag=getattr(args, 'tag', None),
        dry_run=dry_run
    )


def cmd_batch_delete(args):
    """批量删除原子（默认 dry_run 安全模式）."""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)
    from .batch_ops import BatchOperations
    ops = BatchOperations(kb_dir)
    # 默认 dry_run=True，需 --force 才实际执行
    force = getattr(args, 'force', False)
    ops.batch_delete(
        by_type=getattr(args, 'type', None),
        by_tag=getattr(args, 'tag', None),
        by_status=getattr(args, 'status', None),
        dry_run=not force
    )


# ============================================================================
# HTTP API 服务命令
# ============================================================================

def cmd_serve(args):
    """启动统一 Web 服务（前端 + API）."""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)
    from .web_server import UnifiedWebServer
    server = UnifiedWebServer(kb_dir, host=args.host, port=args.port)
    server.run()


# ============================================================================
# 内容生命周期管理命令
# ============================================================================

def cmd_publish(args):
    """发布原子（状态改为 published）."""
    _change_status(args, 'published')


def cmd_archive(args):
    """归档原子（状态改为 archived）."""
    _change_status(args, 'archived')


def cmd_deprecate(args):
    """废弃原子（状态改为 deprecated）."""
    _change_status(args, 'deprecated')


def _change_status(args, new_status: str):
    """修改原子状态."""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)
    # 权限检查
    action_map = {'published': 'publish', 'archived': 'archive', 'deprecated': 'deprecate'}
    action = action_map.get(new_status, 'publish')
    username, has_perm = _get_current_user_or_warn(args, action)
    if not has_perm:
        sys.exit(1)
    from .lifecycle import LifecycleManager
    from .audit import AuditLogger
    manager = LifecycleManager(kb_dir)
    atom_path = Path(args.atom_path)
    if not atom_path.is_absolute():
        atom_path = kb_dir / atom_path
    if manager.change_status(atom_path, new_status):
        # 记录审计日志
        AuditLogger(kb_dir).log(
            action=f'status:{new_status}',
            target=str(atom_path.relative_to(kb_dir)) if atom_path.is_relative_to(kb_dir) else str(atom_path),
            user=username,
        )
        print(f"✅ {atom_path.name} 状态已改为: {new_status}（by {username}）")
    else:
        print(f"❌ 状态修改失败: {atom_path}")
        sys.exit(1)


# ============================================================================
# 操作日志审计命令
# ============================================================================

def cmd_audit(args):
    """查询操作审计日志."""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)
    from .audit import AuditLogger
    logger = AuditLogger(kb_dir)
    entries = logger.query(
        since=getattr(args, 'since', None),
        action=getattr(args, 'action', None),
        limit=getattr(args, 'limit', 50)
    )
    if not entries:
        print("（无审计记录）")
        return
    print(f"\n📋 审计日志（共 {len(entries)} 条）\n")
    for e in entries:
        print(f"  [{e.get('timestamp', '')}] {e.get('action', '')} {e.get('target', '')}")
        if e.get('user'):
            print(f"    User: {e['user']}")
        if e.get('detail'):
            print(f"    Detail: {e['detail']}")


# ============================================================================
# 协同反馈命令
# ============================================================================

def cmd_comment(args):
    """为原子添加评论."""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)
    username, has_perm = _get_current_user_or_warn(args, 'comment')
    if not has_perm:
        sys.exit(1)
    from .feedback import FeedbackManager
    from .audit import AuditLogger
    fm = FeedbackManager(kb_dir)
    atom_path = Path(args.atom_path)
    if not atom_path.is_absolute():
        atom_path = kb_dir / atom_path
    if fm.add_comment(atom_path, args.text, author=username):
        AuditLogger(kb_dir).log('comment', str(atom_path), user=username, detail=args.text[:100])
        print(f"✅ 评论已添加（by {username}）")
    else:
        print(f"❌ 评论失败")
        sys.exit(1)


def cmd_favorite(args):
    """收藏/取消收藏原子."""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)
    username, has_perm = _get_current_user_or_warn(args, 'favorite')
    if not has_perm:
        sys.exit(1)
    from .feedback import FeedbackManager
    from .audit import AuditLogger
    fm = FeedbackManager(kb_dir)
    atom_path = Path(args.atom_path)
    if not atom_path.is_absolute():
        atom_path = kb_dir / atom_path
    if getattr(args, 'remove', False):
        fm.remove_favorite(atom_path, user=username)
        AuditLogger(kb_dir).log('unfavorite', str(atom_path), user=username)
        print(f"✅ 已取消收藏: {atom_path.name}（by {username}）")
    else:
        fm.add_favorite(atom_path, user=username)
        AuditLogger(kb_dir).log('favorite', str(atom_path), user=username)
        print(f"✅ 已收藏: {atom_path.name}（by {username}）")


def cmd_rate(args):
    """为原子评分."""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)
    username, has_perm = _get_current_user_or_warn(args, 'rate')
    if not has_perm:
        sys.exit(1)
    from .feedback import FeedbackManager
    from .audit import AuditLogger
    fm = FeedbackManager(kb_dir)
    atom_path = Path(args.atom_path)
    if not atom_path.is_absolute():
        atom_path = kb_dir / atom_path
    if fm.rate(atom_path, args.score, user=username):
        AuditLogger(kb_dir).log('rate', str(atom_path), user=username, detail=f"score={args.score}")
        print(f"✅ 评分 {args.score} 已记录（by {username}）")
    else:
        print(f"❌ 评分失败")
        sys.exit(1)


# ============================================================================
# 审批流命令
# ============================================================================

def cmd_submit(args):
    """提交原子进入审核流."""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)
    username, has_perm = _get_current_user_or_warn(args, 'submit')
    if not has_perm:
        sys.exit(1)
    from .workflow import WorkflowManager
    from .audit import AuditLogger
    wf = WorkflowManager(kb_dir)
    atom_path = Path(args.atom_path)
    if not atom_path.is_absolute():
        atom_path = kb_dir / atom_path
    if wf.submit(atom_path, submitter=username):
        AuditLogger(kb_dir).log('submit', str(atom_path), user=username)
        print(f"✅ 已提交审核: {atom_path.name}（by {username}）")
    else:
        print(f"❌ 提交失败")
        sys.exit(1)


def cmd_approve(args):
    """审核通过."""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)
    username, has_perm = _get_current_user_or_warn(args, 'approve')
    if not has_perm:
        sys.exit(1)
    from .workflow import WorkflowManager
    from .audit import AuditLogger
    wf = WorkflowManager(kb_dir)
    atom_path = Path(args.atom_path)
    if not atom_path.is_absolute():
        atom_path = kb_dir / atom_path
    if wf.approve(atom_path, reviewer=username):
        AuditLogger(kb_dir).log('approve', str(atom_path), user=username)
        print(f"✅ 审核通过: {atom_path.name}（by {username}）")
    else:
        print(f"❌ 审核失败")
        sys.exit(1)


def cmd_reject(args):
    """审核驳回."""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)
    username, has_perm = _get_current_user_or_warn(args, 'reject')
    if not has_perm:
        sys.exit(1)
    from .workflow import WorkflowManager
    from .audit import AuditLogger
    wf = WorkflowManager(kb_dir)
    atom_path = Path(args.atom_path)
    if not atom_path.is_absolute():
        atom_path = kb_dir / atom_path
    if wf.reject(atom_path, reason=args.reason, reviewer=username):
        AuditLogger(kb_dir).log('reject', str(atom_path), user=username, detail=args.reason or '')
        print(f"✅ 已驳回: {atom_path.name}（by {username}）")
        if args.reason:
            print(f"   原因: {args.reason}")
    else:
        print(f"❌ 驳回失败")
        sys.exit(1)


# ============================================================================
# 数据统计命令
# ============================================================================

def cmd_stats(args):
    """显示知识库统计数据."""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)
    from .analytics import AnalyticsEngine
    engine = AnalyticsEngine(kb_dir)
    stats = engine.get_stats()

    print(f"\n📊 知识库统计: {kb_dir.name}\n")
    print(f"  原子总数: {stats.get('total_atoms', 0)}")
    print(f"  类型分布:")
    for t, n in sorted(stats.get('by_type', {}).items(), key=lambda x: x[1], reverse=True):
        print(f"    {t}: {n}")
    print(f"  状态分布:")
    for s, n in stats.get('by_status', {}).items():
        print(f"    {s}: {n}")
    print(f"  标签数: {stats.get('total_tags', 0)}")
    print(f"  作者数: {stats.get('total_authors', 0)}")

    if stats.get('recent_activity'):
        print(f"\n  最近活动（{len(stats['recent_activity'])} 条）:")
        for act in stats['recent_activity'][:5]:
            print(f"    {act}")

    if getattr(args, 'export', None):
        engine.export_report(args.export)
        print(f"\n  📄 报告已导出: {args.export}")


# ============================================================================
# 备份恢复命令
# ============================================================================

def cmd_backup(args):
    """备份知识库."""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)
    from .backup import BackupManager
    bm = BackupManager(kb_dir)
    output = bm.backup(getattr(args, 'output', None))
    print(f"✅ 备份完成: {output}")


def cmd_restore(args):
    """从备份恢复原子."""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)
    from .backup import BackupManager
    bm = BackupManager(kb_dir)
    if bm.restore_atom(args.atom_id, getattr(args, 'version', None)):
        print(f"✅ 恢复成功: {args.atom_id}")
    else:
        print(f"❌ 恢复失败")
        sys.exit(1)


# ============================================================================
# 用户管理命令
# ============================================================================

def _get_auth_manager(args):
    """获取 AuthManager 实例."""
    kb_dir = resolve_kb(args)
    if not kb_dir:
        sys.exit(1)
    from .auth import AuthManager
    return AuthManager(kb_dir), kb_dir


def cmd_user_add(args):
    """添加用户."""
    auth, _ = _get_auth_manager(args)
    import getpass
    password = getattr(args, 'password', None)
    if not password:
        password = getpass.getpass(f"请输入 {args.username} 的密码: ")
    if auth.add_user(args.username, args.role, password):
        print(f"✅ 用户已添加: {args.username} (角色: {args.role})")
    else:
        print(f"❌ 添加用户失败（角色无效或用户已存在）")
        sys.exit(1)


def cmd_user_remove(args):
    """移除用户."""
    auth, _ = _get_auth_manager(args)
    if auth.remove_user(args.username):
        print(f"✅ 用户已移除: {args.username}")
    else:
        print(f"❌ 用户不存在: {args.username}")
        sys.exit(1)


def cmd_user_list(args):
    """列出所有用户."""
    auth, _ = _get_auth_manager(args)
    users = auth.list_users()
    if not users:
        print("（无用户）")
        return
    print(f"\n👥 用户列表（共 {len(users)} 人）\n")
    current = auth.get_current_username()
    for u in users:
        marker = ' ← 当前登录' if u['username'] == current else ''
        print(f"  {u['username']:20s}  角色: {u['role']:8s}  创建: {u.get('created', '')[:10]}{marker}")


def cmd_user_role(args):
    """更新用户角色."""
    auth, _ = _get_auth_manager(args)
    if auth.update_user_role(args.username, args.role):
        print(f"✅ {args.username} 角色已更新为: {args.role}")
    else:
        print(f"❌ 更新失败（用户不存在或角色无效）")
        sys.exit(1)


def cmd_user_password(args):
    """修改用户密码."""
    auth, _ = _get_auth_manager(args)
    import getpass
    new_password = getattr(args, 'password', None)
    if not new_password:
        new_password = getpass.getpass("请输入新密码: ")
    if auth.change_password(args.username, new_password):
        print(f"✅ {args.username} 密码已修改")
    else:
        print(f"❌ 修改失败（用户不存在）")
        sys.exit(1)


def cmd_login(args):
    """用户登录."""
    auth, _ = _get_auth_manager(args)
    import getpass
    password = getattr(args, 'password', None)
    if not password:
        password = getpass.getpass(f"请输入 {args.username} 的密码: ")
    if auth.login(args.username, password):
        role = auth.get_current_role()
        print(f"✅ 登录成功: {args.username} (角色: {role})")
    else:
        print(f"❌ 登录失败（用户名或密码错误）")
        sys.exit(1)


def cmd_logout(args):
    """退出登录."""
    auth, _ = _get_auth_manager(args)
    user = auth.get_current_username()
    if auth.logout():
        print(f"✅ 已退出登录: {user}")
    else:
        print(f"⚠️  当前未登录")
        sys.exit(1)


def cmd_whoami(args):
    """查看当前登录用户."""
    auth, _ = _get_auth_manager(args)
    user = auth.get_current_user()
    if user:
        print(f"👤 当前用户: {user.get('username', 'unknown')}")
        print(f"   角色: {user.get('role', 'unknown')}")
        print(f"   登录时间: {user.get('login_at', 'unknown')}")
    else:
        print("👤 当前未登录")
        print("   使用 'llm-wiki login <username>' 登录")
        print("   使用 'llm-wiki user-add <username>' 添加用户")


def cmd_token_generate(args):
    """生成 API Token."""
    auth, _ = _get_auth_manager(args)
    token = auth.generate_token(args.username, getattr(args, 'role', None))
    if token:
        print(f"✅ Token 已生成")
        print(f"   用户: {args.username}")
        print(f"   Token: {token}")
        print(f"   ⚠️  请妥善保管，此 Token 仅显示一次")
    else:
        print(f"❌ 生成失败（用户不存在）")
        sys.exit(1)


def cmd_token_revoke(args):
    """吊销 Token."""
    auth, _ = _get_auth_manager(args)
    if auth.revoke_token(args.token):
        print(f"✅ Token 已吊销")
    else:
        print(f"❌ Token 不存在")
        sys.exit(1)


def cmd_token_list(args):
    """列出所有 Token."""
    auth, _ = _get_auth_manager(args)
    tokens = auth.list_tokens()
    if not tokens:
        print("（无 Token）")
        return
    print(f"\n🔑 Token 列表（共 {len(tokens)} 个）\n")
    for t in tokens:
        print(f"  {t['token']:20s}  用户: {t['username']:15s}  角色: {t['role']:8s}  创建: {t.get('created', '')[:10]}")


def _get_current_user_or_warn(args, action: str):
    """获取当前登录用户，未登录时警告并返回 anonymous.

    Args:
        args: 命令参数
        action: 操作名称（用于权限检查）

    Returns:
        (用户名, 是否有权限)
    """
    auth, _ = _get_auth_manager(args)
    username = auth.require_user()
    has_permission = auth.require_permission(action)
    if not has_permission:
        print(f"❌ 权限不足：当前用户 '{username}' 无权执行 '{action}' 操作")
    return username, has_permission
