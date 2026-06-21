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
    cmd_watch, cmd_gaps, cmd_relations, cmd_heads_up, cmd_web_ui,
    cmd_suggest, cmd_batch_ingest, cmd_batch_export, cmd_batch_tag,
    cmd_batch_move, cmd_batch_delete, cmd_serve, cmd_publish, cmd_archive,
    cmd_deprecate, cmd_audit, cmd_comment, cmd_favorite, cmd_rate,
    cmd_submit, cmd_approve, cmd_reject, cmd_stats, cmd_backup, cmd_restore,
    cmd_user_add, cmd_user_remove, cmd_user_list, cmd_user_role, cmd_user_password,
    cmd_login, cmd_logout, cmd_whoami,
    cmd_token_generate, cmd_token_revoke, cmd_token_list,
)
from lib.migration.cli import register_migrate_commands


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
    query_parser.add_argument('--type', '-t', help='按类型过滤（method/fact/definition/data/opinion/question/reference）')
    query_parser.add_argument('--tag', help='按标签过滤')
    query_parser.add_argument('--author', help='按作者过滤')
    query_parser.add_argument('--date-from', help='起始日期（YYYY-MM-DD）')
    query_parser.add_argument('--date-to', help='结束日期（YYYY-MM-DD）')
    query_parser.add_argument('--source-type', help='按来源类型过滤（official/blog/user/document）')
    query_parser.add_argument('--status', help='按状态过滤（draft/review/published/archived/deprecated）')
    query_parser.add_argument('--sort-by', choices=['relevance', 'time', 'title', 'popularity'], default='relevance', help='排序方式')
    query_parser.add_argument('--limit', '-l', type=int, default=10, help='结果数量限制')
    query_parser.set_defaults(func=cmd_query)

    # suggest command
    suggest_parser = subparsers.add_parser('suggest', help='搜索联想建议')
    suggest_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    suggest_parser.add_argument('prefix', nargs='?', help='搜索前缀')
    suggest_parser.add_argument('--hot', action='store_true', help='显示高频搜索词')
    suggest_parser.add_argument('--no-result', action='store_true', help='显示无结果搜索词')
    suggest_parser.add_argument('--limit', '-l', type=int, default=10, help='结果数量限制')
    suggest_parser.set_defaults(func=cmd_suggest)

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

    # batch-ingest command
    batch_ingest_parser = subparsers.add_parser('batch-ingest', help='批量摄入目录')
    batch_ingest_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    batch_ingest_parser.add_argument('source_dir', type=Path, help='源目录')
    batch_ingest_parser.add_argument('--pattern', '-p', default='*', help='文件匹配模式（如 *.md）')
    batch_ingest_parser.add_argument('--no-recursive', action='store_true', help='不递归子目录')
    batch_ingest_parser.add_argument('--dry-run', action='store_true', help='仅预览')
    batch_ingest_parser.set_defaults(func=cmd_batch_ingest)

    # batch-export command
    batch_export_parser = subparsers.add_parser('batch-export', help='批量导出原子')
    batch_export_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    batch_export_parser.add_argument('output', type=Path, help='输出目录')
    batch_export_parser.add_argument('--type', '-t', help='按类型过滤')
    batch_export_parser.add_argument('--tag', help='按标签过滤')
    batch_export_parser.add_argument('--status', help='按状态过滤')
    batch_export_parser.add_argument('--dry-run', action='store_true', help='仅预览')
    batch_export_parser.set_defaults(func=cmd_batch_export)

    # batch-tag command
    batch_tag_parser = subparsers.add_parser('batch-tag', help='批量打标签')
    batch_tag_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    batch_tag_parser.add_argument('--add', help='要添加的标签（逗号分隔）')
    batch_tag_parser.add_argument('--remove', help='要移除的标签（逗号分隔）')
    batch_tag_parser.add_argument('--type', '-t', help='按类型过滤')
    batch_tag_parser.add_argument('--tag', help='按标签过滤')
    batch_tag_parser.add_argument('--dry-run', action='store_true', help='仅预览')
    batch_tag_parser.set_defaults(func=cmd_batch_tag)

    # batch-move command
    batch_move_parser = subparsers.add_parser('batch-move', help='批量迁移类型')
    batch_move_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    batch_move_parser.add_argument('target_type', help='目标类型')
    batch_move_parser.add_argument('--from-type', help='源类型过滤')
    batch_move_parser.add_argument('--tag', help='标签过滤')
    batch_move_parser.add_argument('--dry-run', action='store_true', help='仅预览')
    batch_move_parser.set_defaults(func=cmd_batch_move)

    # batch-delete command
    batch_delete_parser = subparsers.add_parser('batch-delete', help='批量删除原子')
    batch_delete_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    batch_delete_parser.add_argument('--type', '-t', help='按类型过滤')
    batch_delete_parser.add_argument('--tag', help='按标签过滤')
    batch_delete_parser.add_argument('--status', help='按状态过滤')
    batch_delete_parser.add_argument('--force', action='store_true', help='实际执行（默认仅预览）')
    batch_delete_parser.set_defaults(func=cmd_batch_delete)

    # serve command (HTTP API)
    serve_parser = subparsers.add_parser('serve', help='启动 HTTP API 服务')
    serve_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    serve_parser.add_argument('--host', default='127.0.0.1', help='监听地址')
    serve_parser.add_argument('--port', '-p', type=int, default=8000, help='监听端口')
    serve_parser.set_defaults(func=cmd_serve)

    # publish command
    publish_parser = subparsers.add_parser('publish', help='发布原子')
    publish_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    publish_parser.add_argument('atom_path', help='原子文件路径')
    publish_parser.set_defaults(func=cmd_publish)

    # archive command
    archive_parser = subparsers.add_parser('archive', help='归档原子')
    archive_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    archive_parser.add_argument('atom_path', help='原子文件路径')
    archive_parser.set_defaults(func=cmd_archive)

    # deprecate command
    deprecate_parser = subparsers.add_parser('deprecate', help='废弃原子')
    deprecate_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    deprecate_parser.add_argument('atom_path', help='原子文件路径')
    deprecate_parser.set_defaults(func=cmd_deprecate)

    # audit command
    audit_parser = subparsers.add_parser('audit', help='查询审计日志')
    audit_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    audit_parser.add_argument('--since', help='起始日期')
    audit_parser.add_argument('--action', help='按操作类型过滤')
    audit_parser.add_argument('--limit', '-l', type=int, default=50, help='结果数量')
    audit_parser.set_defaults(func=cmd_audit)

    # comment command
    comment_parser = subparsers.add_parser('comment', help='添加评论')
    comment_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    comment_parser.add_argument('atom_path', help='原子文件路径')
    comment_parser.add_argument('text', help='评论内容')
    comment_parser.set_defaults(func=cmd_comment)

    # favorite command
    favorite_parser = subparsers.add_parser('favorite', help='收藏原子')
    favorite_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    favorite_parser.add_argument('atom_path', help='原子文件路径')
    favorite_parser.add_argument('--remove', action='store_true', help='取消收藏')
    favorite_parser.set_defaults(func=cmd_favorite)

    # rate command
    rate_parser = subparsers.add_parser('rate', help='为原子评分')
    rate_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    rate_parser.add_argument('atom_path', help='原子文件路径')
    rate_parser.add_argument('score', type=int, help='评分（1-5）')
    rate_parser.set_defaults(func=cmd_rate)

    # submit command (审批流)
    submit_parser = subparsers.add_parser('submit', help='提交审核')
    submit_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    submit_parser.add_argument('atom_path', help='原子文件路径')
    submit_parser.set_defaults(func=cmd_submit)

    # approve command
    approve_parser = subparsers.add_parser('approve', help='审核通过')
    approve_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    approve_parser.add_argument('atom_path', help='原子文件路径')
    approve_parser.set_defaults(func=cmd_approve)

    # reject command
    reject_parser = subparsers.add_parser('reject', help='审核驳回')
    reject_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    reject_parser.add_argument('atom_path', help='原子文件路径')
    reject_parser.add_argument('--reason', help='驳回原因')
    reject_parser.set_defaults(func=cmd_reject)

    # stats command
    stats_parser = subparsers.add_parser('stats', help='知识库统计')
    stats_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    stats_parser.add_argument('--export', '-e', type=Path, help='导出报告路径')
    stats_parser.set_defaults(func=cmd_stats)

    # backup command
    backup_parser = subparsers.add_parser('backup', help='备份知识库')
    backup_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    backup_parser.add_argument('--output', '-o', type=Path, help='输出路径')
    backup_parser.set_defaults(func=cmd_backup)

    # restore command
    restore_parser = subparsers.add_parser('restore', help='恢复原子')
    restore_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    restore_parser.add_argument('atom_id', help='原子 ID')
    restore_parser.add_argument('--version', help='版本号')
    restore_parser.set_defaults(func=cmd_restore)

    # ========================================================================
    # 用户管理命令
    # ========================================================================

    # user-add
    user_add_parser = subparsers.add_parser('user-add', help='添加用户')
    user_add_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    user_add_parser.add_argument('username', help='用户名')
    user_add_parser.add_argument('--role', '-r', choices=['reader', 'editor', 'admin'], default='reader', help='角色（默认 reader）')
    user_add_parser.add_argument('--password', '-p', help='密码（不指定则交互输入）')
    user_add_parser.set_defaults(func=cmd_user_add)

    # user-remove
    user_remove_parser = subparsers.add_parser('user-remove', help='移除用户')
    user_remove_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    user_remove_parser.add_argument('username', help='用户名')
    user_remove_parser.set_defaults(func=cmd_user_remove)

    # user-list
    user_list_parser = subparsers.add_parser('user-list', help='列出所有用户')
    user_list_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    user_list_parser.set_defaults(func=cmd_user_list)

    # user-role
    user_role_parser = subparsers.add_parser('user-role', help='更新用户角色')
    user_role_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    user_role_parser.add_argument('username', help='用户名')
    user_role_parser.add_argument('role', choices=['reader', 'editor', 'admin'], help='新角色')
    user_role_parser.set_defaults(func=cmd_user_role)

    # user-password
    user_password_parser = subparsers.add_parser('user-password', help='修改用户密码')
    user_password_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    user_password_parser.add_argument('username', help='用户名')
    user_password_parser.add_argument('--password', '-p', help='新密码（不指定则交互输入）')
    user_password_parser.set_defaults(func=cmd_user_password)

    # login
    login_parser = subparsers.add_parser('login', help='用户登录')
    login_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    login_parser.add_argument('username', help='用户名')
    login_parser.add_argument('--password', '-p', help='密码（不指定则交互输入）')
    login_parser.set_defaults(func=cmd_login)

    # logout
    logout_parser = subparsers.add_parser('logout', help='退出登录')
    logout_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    logout_parser.set_defaults(func=cmd_logout)

    # whoami
    whoami_parser = subparsers.add_parser('whoami', help='查看当前登录用户')
    whoami_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    whoami_parser.set_defaults(func=cmd_whoami)

    # token-generate
    token_gen_parser = subparsers.add_parser('token-generate', help='生成 API Token')
    token_gen_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    token_gen_parser.add_argument('username', help='用户名')
    token_gen_parser.add_argument('--role', '-r', choices=['reader', 'editor', 'admin'], help='角色覆盖（默认使用用户角色）')
    token_gen_parser.set_defaults(func=cmd_token_generate)

    # token-revoke
    token_revoke_parser = subparsers.add_parser('token-revoke', help='吊销 API Token')
    token_revoke_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    token_revoke_parser.add_argument('token', help='Token 字符串')
    token_revoke_parser.set_defaults(func=cmd_token_revoke)

    # token-list
    token_list_parser = subparsers.add_parser('token-list', help='列出所有 API Token')
    token_list_parser.add_argument('knowledge_base', nargs='?', help='知识库路径或名称')
    token_list_parser.set_defaults(func=cmd_token_list)

    # ========================================================================
    # 迁移命令
    # ========================================================================

    # 注册迁移命令（使用迁移模块的函数）
    register_migrate_commands(subparsers, None)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == '__main__':
    main()
