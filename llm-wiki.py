#!/usr/bin/env python3
"""LLM Wiki CLI - OKF 知识库管理工具

Usage: llm-wiki <command> [options]

Commands:
    init        初始化知识库
    ingest      摄入资料
    query       查询知识
    embed       生成向量嵌入
    lint        OKF 兼容性检查
    index       生成目录索引
    export      导出 OKF Bundle
    import      导入 OKF Bundle
    visualize   生成知识图谱
    web-ui      创建 Web UI
    register    注册知识库
    list        列出知识库
    use         设置当前知识库
    info        查看知识库详情
    capture     快速捕获
    watch       文件监控

Run: llm-wiki <command> --help
"""

import argparse
import sys
from pathlib import Path

from lib.cli_commands import (
    cmd_register, cmd_unregister, cmd_list, cmd_use, cmd_info,
    cmd_init, cmd_ingest, cmd_embed, cmd_query, cmd_lint, cmd_index,
    cmd_export, cmd_import, cmd_visualize, cmd_timeline, cmd_capture,
    cmd_watch, cmd_gaps, cmd_relations, cmd_heads_up, cmd_web_ui
)


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
    init_parser.add_argument('--parent', action='store_true', help='创建父知识库')
    init_parser.add_argument('--child', action='store_true', help='创建子知识库')
    init_parser.add_argument('--parent-kb', type=Path, help='父知识库路径')
    init_parser.add_argument('--force', '-f', action='store_true', help='强制覆盖')
    init_parser.set_defaults(func=cmd_init)

    # register command
    register_parser = subparsers.add_parser('register', help='注册知识库')
    register_parser.add_argument('path', type=Path, help='知识库路径')
    register_parser.add_argument('--name', '-n', help='知识库别名')
    register_parser.add_argument('--description', '-d', help='描述')
    register_parser.add_argument('--tags', '-t', help='标签（逗号分隔）')
    register_parser.add_argument('--scope', '-s', choices=['auto', 'project', 'global'], default='auto', help='注册范围')
    register_parser.add_argument('--parent', help='父知识库名称（注册子知识库时使用）')
    register_parser.set_defaults(func=cmd_register)

    # unregister command
    unregister_parser = subparsers.add_parser('unregister', help='注销知识库')
    unregister_parser.add_argument('name', help='知识库名称')
    unregister_parser.add_argument('--scope', '-s', choices=['auto', 'project', 'global'], default='auto', help='注销范围')
    unregister_parser.set_defaults(func=cmd_unregister)

    # list command
    list_parser = subparsers.add_parser('list', help='列出知识库')
    list_parser.add_argument('--scope', '-s', choices=['auto', 'project', 'global'], default='auto', help='列出范围')
    list_parser.add_argument('--verbose', '-v', action='store_true', help='详细信息')
    list_parser.set_defaults(func=cmd_list)

    # use command
    use_parser = subparsers.add_parser('use', help='设置当前知识库')
    use_parser.add_argument('name', help='知识库名称')
    use_parser.add_argument('--scope', '-s', choices=['auto', 'project', 'global'], default='auto', help='设置范围')
    use_parser.set_defaults(func=cmd_use)

    # info command
    info_parser = subparsers.add_parser('info', help='查看知识库详情')
    info_parser.add_argument('name', nargs='?', help='知识库名称（默认当前）')
    info_parser.set_defaults(func=cmd_info)

    # ingest command
    ingest_parser = subparsers.add_parser('ingest', help='摄入资料')
    ingest_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    ingest_parser.add_argument('source', help='资料文件路径')
    ingest_parser.set_defaults(func=cmd_ingest)

    # embed command
    embed_parser = subparsers.add_parser('embed', help='生成向量嵌入')
    embed_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    embed_parser.set_defaults(func=cmd_embed)

    # query command
    query_parser = subparsers.add_parser('query', help='查询知识')
    query_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    query_parser.add_argument('question', help='查询问题')
    query_parser.add_argument('--semantic', '-s', action='store_true', help='语义搜索')
    query_parser.add_argument('--child', '-c', help='仅搜索指定子知识库')
    query_parser.set_defaults(func=cmd_query)

    # lint command
    lint_parser = subparsers.add_parser('lint', help='OKF 兼容性检查')
    lint_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    lint_parser.add_argument('--okf-check', action='store_true', help='显示详情')
    lint_parser.set_defaults(func=cmd_lint)

    # index command
    index_parser = subparsers.add_parser('index', help='生成目录索引')
    index_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    index_parser.add_argument('--directory', '-d', type=Path, help='指定目录')
    index_parser.set_defaults(func=cmd_index)

    # export command
    export_parser = subparsers.add_parser('export', help='导出 OKF Bundle')
    export_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    export_parser.add_argument('--output', '-o', type=Path, help='输出文件路径')
    export_parser.add_argument('--validate', '-v', action='store_true', default=True, help='验证')
    export_parser.add_argument('--no-validate', action='store_true', help='跳过验证')
    export_parser.add_argument('--force', '-f', action='store_true', help='强制导出')
    export_parser.add_argument('--include-children', action='store_true', help='包含子知识库')
    export_parser.set_defaults(func=cmd_export)

    # import command
    import_parser = subparsers.add_parser('import', help='导入 OKF Bundle')
    import_parser.add_argument('bundle', type=Path, help='Bundle 文件路径')
    import_parser.add_argument('--output', '-o', type=Path, default=Path('.'), help='输出目录')
    import_parser.add_argument('--overwrite', action='store_true', help='覆盖现有文件')
    import_parser.set_defaults(func=cmd_import)

    # visualize command
    visualize_parser = subparsers.add_parser('visualize', help='生成知识图谱')
    visualize_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    visualize_parser.add_argument('--output', '-o', type=Path, help='输出文件路径')
    visualize_parser.add_argument('--name', '-n', help='图谱名称')
    visualize_parser.add_argument('--interactive', '-i', action='store_true', help='增强交互')
    visualize_parser.set_defaults(func=cmd_visualize)

    # timeline command
    timeline_parser = subparsers.add_parser('timeline', help='生成时间线')
    timeline_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    timeline_parser.add_argument('--output', '-o', type=Path, help='输出文件路径')
    timeline_parser.set_defaults(func=cmd_timeline)

    # capture command
    capture_parser = subparsers.add_parser('capture', help='快速捕获')
    capture_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    capture_parser.add_argument('content', help='知识内容')
    capture_parser.add_argument('--type', '-t', default='fact', help='原子类型')
    capture_parser.set_defaults(func=cmd_capture)

    # watch command
    watch_parser = subparsers.add_parser('watch', help='文件监控')
    watch_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    watch_parser.set_defaults(func=cmd_watch)

    # gaps command
    gaps_parser = subparsers.add_parser('gaps', help='发现知识缺口')
    gaps_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    gaps_parser.set_defaults(func=cmd_gaps)

    # relations command
    relations_parser = subparsers.add_parser('relations', help='发现原子关系')
    relations_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    relations_parser.set_defaults(func=cmd_relations)

    # heads-up command
    heads_up_parser = subparsers.add_parser('heads-up', help='主动推送')
    heads_up_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    heads_up_parser.set_defaults(func=cmd_heads_up)

    # web-ui command
    webui_parser = subparsers.add_parser('web-ui', help='创建 Web UI（一键生成所有视图）')
    webui_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    webui_parser.set_defaults(func=cmd_web_ui)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == '__main__':
    main()
