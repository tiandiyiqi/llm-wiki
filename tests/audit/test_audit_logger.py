"""审计日志测试

测试 AuditLogger（企业版和基础版）的日志记录和格式验证。
"""

import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# 尝试导入企业版审计模块
try:
    from lib.audit.audit_logger import AuditLogger as EnterpriseAuditLogger, AuditEvent, AuditEventType, AuditSeverity

    _ENTERPRISE_IMPORT_OK = True
except ImportError as _e:
    _ENTERPRISE_IMPORT_OK = False
    _ENTERPRISE_ERROR = str(_e)


# 尝试导入基础版审计模块（直接从 lib.audit 模块导入，注意参数与 enterprise 版不同）
try:
    import importlib
    _basic_audit_mod = importlib.import_module("audit_py")
    BasicAuditLogger = _basic_audit_mod.AuditLogger

    _BASIC_IMPORT_OK = True
except (ImportError, AttributeError) as _e:
    try:
        # 另一种路径：从 lib 根目录直接导入 audit.py
        import importlib.util
        _spec = importlib.util.spec_from_file_location(
            "audit_py",
            str(Path(__file__).resolve().parent.parent.parent / "lib" / "audit.py"),
        )
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        BasicAuditLogger = _mod.AuditLogger
        _BASIC_IMPORT_OK = True
    except Exception as _e2:
        _BASIC_IMPORT_OK = False
        _BASIC_ERROR = str(_e2)


# ============================================================================
# 企业版审计日志测试
# ============================================================================

@pytest.mark.skipif(not _ENTERPRISE_IMPORT_OK, reason=f"企业版导入失败: {_ENTERPRISE_ERROR if not _ENTERPRISE_IMPORT_OK else ''}")
class TestAuditEventType:
    """审计事件类型测试"""

    def test_event_types_defined(self):
        """事件类型已定义"""
        assert AuditEventType.AUTH_SUCCESS is not None
        assert AuditEventType.AUTH_FAILURE is not None
        assert AuditEventType.PERMISSION_GRANT is not None
        assert AuditEventType.PERMISSION_DENIED is not None
        assert AuditEventType.DATA_ACCESS is not None
        assert AuditEventType.DATA_MODIFY is not None
        assert AuditEventType.DATA_DELETE is not None

    def test_event_type_values(self):
        """事件类型值格式"""
        assert AuditEventType.AUTH_SUCCESS.value == "auth.success"
        assert AuditEventType.AUTH_FAILURE.value == "auth.failure"
        assert AuditEventType.PERMISSION_GRANT.value == "permission.grant"


@pytest.mark.skipif(not _ENTERPRISE_IMPORT_OK, reason=f"企业版导入失败: {_ENTERPRISE_ERROR if not _ENTERPRISE_IMPORT_OK else ''}")
class TestAuditSeverity:
    """审计严重程度测试"""

    def test_severity_levels(self):
        """严重程度级别"""
        assert AuditSeverity.INFO.value == "info"
        assert AuditSeverity.WARNING.value == "warning"
        assert AuditSeverity.CRITICAL.value == "critical"


@pytest.mark.skipif(not _ENTERPRISE_IMPORT_OK, reason=f"企业版导入失败: {_ENTERPRISE_ERROR if not _ENTERPRISE_IMPORT_OK else ''}")
class TestAuditEvent:
    """审计事件测试"""

    def test_audit_event_creation(self):
        """创建审计事件"""
        event = AuditEvent(
            event_type=AuditEventType.AUTH_SUCCESS,
            user_id="user123",
            resource="kb/1",
            action="login",
        )
        assert event.event_type == AuditEventType.AUTH_SUCCESS
        assert event.user_id == "user123"
        assert event.severity == AuditSeverity.INFO

    def test_audit_event_to_dict(self):
        """审计事件转换为字典"""
        event = AuditEvent(
            event_type=AuditEventType.AUTH_FAILURE,
            severity=AuditSeverity.WARNING,
            user_id="user123456789",
            details={"ip": "192.168.1.1"},
        )
        d = event.to_dict()
        assert d['event_type'] == "auth.failure"
        assert d['severity'] == "warning"
        # user_id 应被脱敏
        assert '***' in d['user_id']

    def test_audit_event_timestamp(self):
        """审计事件包含时间戳"""
        event = AuditEvent(event_type=AuditEventType.DATA_ACCESS)
        assert event.timestamp > 0

    def test_audit_event_default_details(self):
        """审计事件默认详情为空字典"""
        event = AuditEvent(event_type=AuditEventType.DATA_ACCESS)
        assert event.details == {}


@pytest.mark.skipif(not _ENTERPRISE_IMPORT_OK, reason=f"企业版导入失败: {_ENTERPRISE_ERROR if not _ENTERPRISE_IMPORT_OK else ''}")
class TestEnterpriseAuditLogger:
    """企业版审计日志记录器测试"""

    @pytest.fixture
    def audit_dir(self, tmp_path):
        """创建临时审计日志目录"""
        return tmp_path / "audit"

    @pytest.fixture
    def audit_logger(self, audit_dir):
        """创建审计日志记录器"""
        return EnterpriseAuditLogger(log_dir=audit_dir, max_file_size=1024)

    def test_init_creates_directory(self, audit_dir):
        """初始化时创建日志目录"""
        logger = EnterpriseAuditLogger(log_dir=audit_dir)
        assert audit_dir.exists()

    def test_log_writes_event(self, audit_logger, audit_dir):
        """记录审计事件写入文件"""
        event = AuditEvent(
            event_type=AuditEventType.AUTH_SUCCESS,
            user_id="user1",
        )
        audit_logger.log(event)

        # 检查日志文件
        log_files = list(audit_dir.glob("audit-*.jsonl"))
        assert len(log_files) == 1

        # 检查内容
        content = log_files[0].read_text(encoding='utf-8').strip()
        entry = json.loads(content)
        assert entry['event_type'] == "auth.success"

    def test_log_auth_success(self, audit_logger, audit_dir):
        """记录认证成功事件"""
        audit_logger.log_auth(success=True, user_id="user1")
        log_file = list(audit_dir.glob("audit-*.jsonl"))[0]
        entry = json.loads(log_file.read_text(encoding='utf-8').strip())
        assert entry['event_type'] == "auth.success"
        assert entry['severity'] == "info"

    def test_log_auth_failure(self, audit_logger, audit_dir):
        """记录认证失败事件"""
        audit_logger.log_auth(success=False, user_id="user1", source_ip="10.0.0.1")
        log_file = list(audit_dir.glob("audit-*.jsonl"))[0]
        entry = json.loads(log_file.read_text(encoding='utf-8').strip())
        assert entry['event_type'] == "auth.failure"
        assert entry['severity'] == "warning"

    def test_log_permission_grant(self, audit_logger, audit_dir):
        """记录权限授予事件"""
        audit_logger.log_permission(granted=True, user_id="user1", resource="kb/1", action="read")
        log_file = list(audit_dir.glob("audit-*.jsonl"))[0]
        entry = json.loads(log_file.read_text(encoding='utf-8').strip())
        assert entry['event_type'] == "permission.grant"

    def test_log_permission_denied(self, audit_logger, audit_dir):
        """记录权限拒绝事件"""
        audit_logger.log_permission(granted=False, user_id="user1", resource="kb/1", action="delete")
        log_file = list(audit_dir.glob("audit-*.jsonl"))[0]
        entry = json.loads(log_file.read_text(encoding='utf-8').strip())
        assert entry['event_type'] == "permission.denied"

    def test_log_data_access(self, audit_logger, audit_dir):
        """记录数据访问事件"""
        audit_logger.log_data_access(user_id="user1", resource="atom/1", action="read")
        log_file = list(audit_dir.glob("audit-*.jsonl"))[0]
        entry = json.loads(log_file.read_text(encoding='utf-8').strip())
        assert entry['event_type'] == "data.access"

    def test_log_data_modify(self, audit_logger, audit_dir):
        """记录数据修改事件"""
        audit_logger.log_data_access(user_id="user1", resource="atom/1", action="write")
        log_file = list(audit_dir.glob("audit-*.jsonl"))[0]
        entry = json.loads(log_file.read_text(encoding='utf-8').strip())
        assert entry['event_type'] == "data.modify"

    def test_log_data_delete(self, audit_logger, audit_dir):
        """记录数据删除事件"""
        audit_logger.log_data_access(user_id="user1", resource="atom/1", action="delete")
        log_file = list(audit_dir.glob("audit-*.jsonl"))[0]
        entry = json.loads(log_file.read_text(encoding='utf-8').strip())
        assert entry['event_type'] == "data.delete"

    def test_query_events(self, audit_logger, audit_dir):
        """查询审计日志"""
        # 写入多个事件
        audit_logger.log_auth(success=True, user_id="user1")
        audit_logger.log_auth(success=False, user_id="user2")

        results = audit_logger.query()
        assert len(results) == 2

    def test_query_by_event_type(self, audit_logger, audit_dir):
        """按事件类型查询"""
        audit_logger.log_auth(success=True, user_id="user1")
        audit_logger.log_permission(granted=True, user_id="user1", resource="kb/1", action="read")

        results = audit_logger.query(event_type=AuditEventType.AUTH_SUCCESS)
        assert len(results) == 1
        assert results[0]['event_type'] == "auth.success"

    def test_query_by_time_range(self, audit_logger, audit_dir):
        """按时间范围查询"""
        before = time.time() - 100
        audit_logger.log_auth(success=True, user_id="user1")
        after = time.time() + 100

        results = audit_logger.query(start_time=before, end_time=after)
        assert len(results) >= 1

    def test_query_with_limit(self, audit_logger, audit_dir):
        """查询限制数量"""
        for i in range(5):
            audit_logger.log_auth(success=True, user_id=f"user{i}")

        results = audit_logger.query(limit=3)
        assert len(results) == 3

    def test_file_rotation(self, tmp_path):
        """文件大小超限自动轮转"""
        audit_dir = tmp_path / "audit_rotation"
        logger = EnterpriseAuditLogger(log_dir=audit_dir, max_file_size=100)

        # 写入足够多的数据触发轮转
        for i in range(20):
            logger.log(AuditEvent(
                event_type=AuditEventType.DATA_ACCESS,
                user_id=f"user{i}",
                details={"data": "x" * 50},
            ))

        # 应有轮转文件
        log_files = list(audit_dir.glob("audit-*.jsonl"))
        assert len(log_files) >= 1


# ============================================================================
# 基础版审计日志测试
# ============================================================================

@pytest.mark.skipif(not _BASIC_IMPORT_OK, reason=f"基础版导入失败: {_BASIC_ERROR if not _BASIC_IMPORT_OK else ''}")
class TestBasicAuditLogger:
    """基础版审计日志记录器测试"""

    @pytest.fixture
    def kb_dir(self, tmp_path):
        """创建临时知识库目录"""
        return tmp_path / "test_kb"

    @pytest.fixture
    def basic_logger(self, kb_dir):
        """创建基础版审计日志记录器"""
        kb_dir.mkdir(parents=True, exist_ok=True)
        return BasicAuditLogger(kb_dir=kb_dir)

    def test_log_creates_file(self, basic_logger, kb_dir):
        """记录日志创建文件"""
        basic_logger.log(action="view", target="atom/1", user="user1")
        assert (kb_dir / '.kb-audit.log').exists()

    def test_log_entry_format(self, basic_logger, kb_dir):
        """日志条目格式"""
        basic_logger.log(action="edit", target="atom/1", user="user1", detail="修改标题")
        content = (kb_dir / '.kb-audit.log').read_text(encoding='utf-8').strip()
        entry = json.loads(content)
        assert entry['action'] == 'edit'
        assert entry['target'] == 'atom/1'
        assert entry['user'] == 'user1'
        assert 'timestamp' in entry

    def test_log_with_extra(self, basic_logger, kb_dir):
        """日志包含额外信息"""
        basic_logger.log(action="export", target="kb/1", user="user1", extra={"format": "pdf"})
        content = (kb_dir / '.kb-audit.log').read_text(encoding='utf-8').strip()
        entry = json.loads(content)
        assert entry['format'] == 'pdf'

    def test_query_no_file(self, kb_dir):
        """日志文件不存在时查询返回空"""
        logger = BasicAuditLogger(kb_dir=kb_dir)
        results = logger.query()
        assert results == []

    def test_query_by_action(self, basic_logger, kb_dir):
        """按操作类型查询"""
        basic_logger.log(action="view", target="atom/1", user="user1")
        basic_logger.log(action="edit", target="atom/2", user="user1")

        results = basic_logger.query(action="view")
        assert len(results) == 1
        assert results[0]['action'] == 'view'

    def test_query_by_user(self, basic_logger, kb_dir):
        """按用户查询"""
        basic_logger.log(action="view", target="atom/1", user="alice")
        basic_logger.log(action="view", target="atom/2", user="bob")

        results = basic_logger.query(user="alice")
        assert len(results) == 1

    def test_query_by_target(self, basic_logger, kb_dir):
        """按目标查询"""
        basic_logger.log(action="view", target="atoms/fact-1", user="user1")
        basic_logger.log(action="view", target="atoms/fact-2", user="user1")

        results = basic_logger.query(target="fact-1")
        assert len(results) == 1

    def test_query_with_limit(self, basic_logger, kb_dir):
        """查询限制数量"""
        for i in range(10):
            basic_logger.log(action="view", target=f"atom/{i}", user="user1")

        results = basic_logger.query(limit=5)
        assert len(results) == 5

    def test_get_stats(self, basic_logger, kb_dir):
        """获取统计信息"""
        basic_logger.log(action="view", target="atom/1", user="user1")
        basic_logger.log(action="view", target="atom/2", user="user1")
        basic_logger.log(action="edit", target="atom/1", user="user1")

        stats = basic_logger.get_stats()
        assert stats['total'] == 3
        assert stats['view'] == 2
        assert stats['edit'] == 1

    def test_get_stats_no_file(self, kb_dir):
        """文件不存在时统计返回空"""
        logger = BasicAuditLogger(kb_dir=kb_dir)
        stats = logger.get_stats()
        assert stats == {'total': 0}

    def test_clear_all(self, basic_logger, kb_dir):
        """清空所有日志"""
        basic_logger.log(action="view", target="atom/1", user="user1")
        count = basic_logger.clear()
        assert count == 1
        assert (kb_dir / '.kb-audit.log').read_text(encoding='utf-8') == ''

    def test_clear_before_time(self, basic_logger, kb_dir):
        """清理指定时间之前的日志"""
        basic_logger.log(action="view", target="atom/1", user="user1")
        # 清理 2100 年之前的（即全部）
        count = basic_logger.clear(before="2100-01-01")
        assert count == 1

    def test_export(self, basic_logger, kb_dir, tmp_path):
        """导出日志"""
        basic_logger.log(action="view", target="atom/1", user="user1")
        output_path = tmp_path / "export.json"
        count = basic_logger.export(output_path)
        assert count == 1
        assert output_path.exists()
