"""审计日志系统，记录安全事件和操作日志.

企业版增强审计模块，支持结构化事件记录、日志轮转、查询过滤。
与基础版 lib/audit.py 兼容，提供更丰富的安全审计能力。
"""

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from lib.utils.log_sanitizer import LogSanitizer

logger = logging.getLogger(__name__)


class AuditEventType(str, Enum):
    """审计事件类型."""

    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    AUTH_LOGOUT = "auth.logout"
    TOKEN_CREATE = "token.create"
    TOKEN_REVOKE = "token.revoke"
    PERMISSION_GRANT = "permission.grant"
    PERMISSION_REVOKE = "permission.revoke"
    PERMISSION_DENIED = "permission.denied"
    DATA_ACCESS = "data.access"
    DATA_MODIFY = "data.modify"
    DATA_DELETE = "data.delete"
    CONFIG_CHANGE = "config.change"
    SECURITY_ALERT = "security.alert"
    SESSION_CREATE = "session.create"
    SESSION_DESTROY = "session.destroy"


class AuditSeverity(str, Enum):
    """审计事件严重程度."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """审计事件.

    Attributes:
        event_type: 事件类型
        severity: 严重程度
        user_id: 操作用户 ID
        resource: 操作资源
        action: 操作动作
        details: 事件详情
        timestamp: 事件时间戳
        source_ip: 来源 IP
        request_id: 请求 ID
    """

    event_type: AuditEventType
    severity: AuditSeverity = AuditSeverity.INFO
    user_id: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    source_ip: Optional[str] = None
    request_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（脱敏后）.

        Returns:
            脱敏后的字典，details 和 user_id 中的敏感信息已被掩码
        """
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        # 脱敏 details
        data['details'] = LogSanitizer.sanitize_dict(data.get('details', {}))
        # 脱敏 user_id
        if data.get('user_id'):
            uid = data['user_id']
            data['user_id'] = f"{uid[:8]}***" if len(uid) > 8 else "****"
        return data


class AuditLogger:
    """审计日志记录器.

    企业版审计记录器，支持结构化事件、日志轮转、查询过滤。
    日志以 JSONL 格式存储，按日期分文件，单文件超过阈值自动轮转。
    """

    def __init__(
        self,
        log_dir: Optional[Path] = None,
        max_file_size: int = 10 * 1024 * 1024,
    ):
        """初始化审计日志记录器.

        Args:
            log_dir: 审计日志目录（默认：.llm-wiki/audit/）
            max_file_size: 单个日志文件最大大小（默认 10MB）
        """
        self.log_dir = log_dir or Path('.llm-wiki/audit')
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size = max_file_size
        self._logger = logging.getLogger('audit')

    def log(self, event: AuditEvent) -> None:
        """记录审计事件.

        Args:
            event: 审计事件对象
        """
        event_dict = event.to_dict()
        event_json = json.dumps(event_dict, ensure_ascii=False, default=str)

        # 写入结构化日志
        self._logger.info(event_json)

        # 写入审计文件
        self._write_to_file(event_dict)

    def log_auth(
        self,
        success: bool,
        user_id: str,
        source_ip: Optional[str] = None,
        details: Optional[Dict] = None,
    ) -> None:
        """记录认证事件.

        Args:
            success: 认证是否成功
            user_id: 用户 ID
            source_ip: 来源 IP
            details: 附加详情
        """
        event = AuditEvent(
            event_type=(
                AuditEventType.AUTH_SUCCESS if success
                else AuditEventType.AUTH_FAILURE
            ),
            severity=(
                AuditSeverity.INFO if success
                else AuditSeverity.WARNING
            ),
            user_id=user_id,
            source_ip=source_ip,
            details=details or {},
        )
        self.log(event)

    def log_permission(
        self,
        granted: bool,
        user_id: str,
        resource: str,
        action: str,
        details: Optional[Dict] = None,
    ) -> None:
        """记录权限事件.

        Args:
            granted: 权限是否授予
            user_id: 用户 ID
            resource: 资源标识
            action: 操作类型
            details: 附加详情
        """
        event = AuditEvent(
            event_type=(
                AuditEventType.PERMISSION_GRANT if granted
                else AuditEventType.PERMISSION_DENIED
            ),
            severity=(
                AuditSeverity.INFO if granted
                else AuditSeverity.WARNING
            ),
            user_id=user_id,
            resource=resource,
            action=action,
            details=details or {},
        )
        self.log(event)

    def log_data_access(
        self,
        user_id: str,
        resource: str,
        action: str,
        details: Optional[Dict] = None,
    ) -> None:
        """记录数据访问事件.

        Args:
            user_id: 用户 ID
            resource: 资源标识
            action: 操作类型（read/write/delete）
            details: 附加详情
        """
        event_type_map = {
            'read': AuditEventType.DATA_ACCESS,
            'write': AuditEventType.DATA_MODIFY,
            'delete': AuditEventType.DATA_DELETE,
        }
        event = AuditEvent(
            event_type=event_type_map.get(action, AuditEventType.DATA_ACCESS),
            user_id=user_id,
            resource=resource,
            action=action,
            details=details or {},
        )
        self.log(event)

    def _write_to_file(self, event_dict: Dict[str, Any]) -> None:
        """写入审计日志文件.

        按日期分文件，超过大小阈值自动轮转，设置文件权限为 0600。

        Args:
            event_dict: 事件字典
        """
        try:
            log_file = self.log_dir / f"audit-{time.strftime('%Y-%m-%d')}.jsonl"

            # 检查文件大小，超限则轮转
            if log_file.exists() and log_file.stat().st_size > self.max_file_size:
                rotated = log_file.with_suffix(f'.{int(time.time())}.jsonl')
                log_file.rename(rotated)

            # 追加写入
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(
                    json.dumps(event_dict, ensure_ascii=False, default=str) + '\n'
                )

            # 设置文件权限为仅所有者可读写
            try:
                os.chmod(log_file, 0o600)
            except OSError:
                pass
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def query(
        self,
        event_type: Optional[AuditEventType] = None,
        user_id: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """查询审计日志.

        按条件过滤审计事件，按时间倒序返回。

        Args:
            event_type: 事件类型过滤
            user_id: 用户 ID 过滤（前缀匹配脱敏后的 user_id）
            start_time: 起始时间戳
            end_time: 结束时间戳
            limit: 返回数量上限

        Returns:
            匹配的审计事件列表
        """
        results = []

        for log_file in sorted(
            self.log_dir.glob('audit-*.jsonl'), reverse=True
        ):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            event = json.loads(line.strip())
                        except json.JSONDecodeError:
                            continue

                        # 过滤条件
                        if (
                            event_type
                            and event.get('event_type') != event_type.value
                        ):
                            continue
                        if (
                            user_id
                            and event.get('user_id', '').replace('***', '')
                            != user_id[:8]
                        ):
                            continue
                        if (
                            start_time
                            and event.get('timestamp', 0) < start_time
                        ):
                            continue
                        if end_time and event.get('timestamp', 0) > end_time:
                            continue

                        results.append(event)
                        if len(results) >= limit:
                            return results
            except Exception as e:
                logger.error(f"Failed to read audit log {log_file}: {e}")
                continue

        return results
