"""审批流与消息通知模块，支持多级审核、驳回批注、Webhook 通知."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

from .lifecycle import LifecycleManager


class WorkflowManager:
    """审批流管理器."""

    def __init__(self, kb_dir: Path):
        self.kb_dir = kb_dir
        self.workflow_path = kb_dir / '.llm-wiki' / 'workflow.json'
        self.workflow_path.parent.mkdir(parents=True, exist_ok=True)
        self.lifecycle = LifecycleManager(kb_dir)
        self.notifier = Notifier(kb_dir)

    def submit(self, atom_path: Path, submitter: str = '') -> bool:
        """提交原子进入审核流.

        Args:
            atom_path: 原子文件路径
            submitter: 提交者

        Returns:
            是否成功
        """
        # 修改状态为 review
        if not self.lifecycle.submit_for_review(atom_path):
            return False

        atom_id = self._get_atom_id(atom_path)
        data = self._load()
        queue = data.setdefault('review_queue', [])
        queue.append({
            'atom_id': atom_id,
            'submitter': submitter or 'anonymous',
            'submitted_at': datetime.now().isoformat(),
            'status': 'pending',
            'reviews': [],
        })
        self._save(data)

        # 发送通知
        self.notifier.notify(
            title=f"新审核待办: {atom_id}",
            message=f"提交者: {submitter or 'anonymous'}",
            event='review_submitted'
        )
        return True

    def approve(self, atom_path: Path, reviewer: str = '',
                comment: str = '') -> bool:
        """审核通过.

        Args:
            atom_path: 原子文件路径
            reviewer: 审核者
            comment: 审核意见

        Returns:
            是否成功
        """
        atom_id = self._get_atom_id(atom_path)
        data = self._load()

        # 更新审核队列
        for item in data.get('review_queue', []):
            if item['atom_id'] == atom_id and item['status'] == 'pending':
                item['status'] = 'approved'
                item['reviewer'] = reviewer
                item['reviewed_at'] = datetime.now().isoformat()
                item['review_comment'] = comment
                break

        self._save(data)

        # 修改状态为 published
        if not self.lifecycle.publish(atom_path):
            return False

        # 发送通知
        self.notifier.notify(
            title=f"审核通过: {atom_id}",
            message=f"审核者: {reviewer}, 意见: {comment}",
            event='review_approved'
        )
        return True

    def reject(self, atom_path: Path, reason: str = '',
               reviewer: str = '') -> bool:
        """审核驳回.

        Args:
            atom_path: 原子文件路径
            reason: 驳回原因
            reviewer: 审核者

        Returns:
            是否成功
        """
        atom_id = self._get_atom_id(atom_path)
        data = self._load()

        # 更新审核队列
        for item in data.get('review_queue', []):
            if item['atom_id'] == atom_id and item['status'] == 'pending':
                item['status'] = 'rejected'
                item['reviewer'] = reviewer
                item['reviewed_at'] = datetime.now().isoformat()
                item['reject_reason'] = reason
                break

        self._save(data)

        # 回退到草稿状态
        self.lifecycle.revert_to_draft(atom_path)

        # 发送通知
        self.notifier.notify(
            title=f"审核驳回: {atom_id}",
            message=f"审核者: {reviewer}, 原因: {reason}",
            event='review_rejected'
        )
        return True

    def get_pending_reviews(self) -> List[Dict]:
        """获取待审核列表."""
        data = self._load()
        return [item for item in data.get('review_queue', [])
                if item.get('status') == 'pending']

    def get_review_history(self, atom_id: Optional[str] = None) -> List[Dict]:
        """获取审核历史."""
        data = self._load()
        queue = data.get('review_queue', [])
        if atom_id:
            return [item for item in queue if item['atom_id'] == atom_id]
        return [item for item in queue if item.get('status') != 'pending']

    def _get_atom_id(self, atom_path: Path) -> str:
        """获取原子 ID."""
        try:
            return str(atom_path.relative_to(self.kb_dir))
        except ValueError:
            return str(atom_path)

    def _load(self) -> Dict:
        """加载工作流数据."""
        try:
            return json.loads(self.workflow_path.read_text(encoding='utf-8'))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save(self, data: Dict) -> None:
        """保存工作流数据."""
        self.workflow_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8'
        )


class Notifier:
    """消息通知器，支持 Webhook 推送到企业微信/钉钉/飞书."""

    def __init__(self, kb_dir: Path):
        self.kb_dir = kb_dir
        self.config_path = kb_dir / '.llm-wiki' / 'notify-config.json'
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

    def notify(self, title: str, message: str, event: str = 'default') -> bool:
        """发送通知.

        Args:
            title: 通知标题
            message: 通知内容
            event: 事件类型

        Returns:
            是否成功
        """
        config = self._load_config()
        webhooks = config.get('webhooks', [])

        if not webhooks:
            # 无 Webhook 配置，仅记录到站内消息
            self._record_inapp(title, message, event)
            return True

        success = False
        for webhook in webhooks:
            if self._send_webhook(webhook, title, message, event):
                success = True

        # 同时记录站内消息
        self._record_inapp(title, message, event)
        return success

    def add_webhook(self, name: str, url: str, wtype: str = 'generic') -> bool:
        """添加 Webhook 配置.

        Args:
            name: Webhook 名称
            url: Webhook URL
            wtype: 类型（generic/wechat/dingtalk/feishu）

        Returns:
            是否成功
        """
        config = self._load_config()
        webhooks = config.setdefault('webhooks', [])
        webhooks.append({
            'name': name,
            'url': url,
            'type': wtype,
            'enabled': True,
        })
        self._save_config(config)
        return True

    def remove_webhook(self, name: str) -> bool:
        """移除 Webhook."""
        config = self._load_config()
        webhooks = config.get('webhooks', [])
        config['webhooks'] = [w for w in webhooks if w.get('name') != name]
        self._save_config(config)
        return True

    def get_inbox(self, limit: int = 20) -> List[Dict]:
        """获取站内消息."""
        config = self._load_config()
        inbox = config.get('inbox', [])
        return inbox[-limit:] if inbox else []

    def _send_webhook(self, webhook: Dict, title: str, message: str, event: str) -> bool:
        """发送 Webhook 请求."""
        url = webhook.get('url')
        if not url:
            return False

        wtype = webhook.get('type', 'generic')
        # 根据类型构造消息体
        if wtype == 'wechat':
            payload = {
                'msgtype': 'text',
                'text': {'content': f"{title}\n{message}"}
            }
        elif wtype == 'dingtalk':
            payload = {
                'msgtype': 'text',
                'text': {'content': f"{title}\n{message}"}
            }
        elif wtype == 'feishu':
            payload = {
                'msg_type': 'text',
                'content': {'text': f"{title}\n{message}"}
            }
        else:
            payload = {
                'title': title,
                'message': message,
                'event': event,
                'timestamp': datetime.now().isoformat()
            }

        try:
            data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            req = Request(url, data=data, headers={'Content-Type': 'application/json'})
            with urlopen(req, timeout=10) as resp:
                return resp.status == 200
        except (URLError, OSError, TimeoutError):
            return False

    def _record_inapp(self, title: str, message: str, event: str) -> None:
        """记录站内消息."""
        config = self._load_config()
        inbox = config.setdefault('inbox', [])
        inbox.append({
            'title': title,
            'message': message,
            'event': event,
            'timestamp': datetime.now().isoformat(),
            'read': False,
        })
        # 仅保留最近 100 条
        if len(inbox) > 100:
            inbox = inbox[-100:]
        config['inbox'] = inbox
        self._save_config(config)

    def _load_config(self) -> Dict:
        """加载通知配置."""
        try:
            return json.loads(self.config_path.read_text(encoding='utf-8'))
        except (FileNotFoundError, json.JSONDecodeError):
            return {'webhooks': [], 'inbox': []}

    def _save_config(self, config: Dict) -> None:
        """保存通知配置."""
        self.config_path.write_text(
            json.dumps(config, indent=2, ensure_ascii=False), encoding='utf-8'
        )
