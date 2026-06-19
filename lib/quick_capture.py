"""QuickCapture - 一句话捕获知识原子

从简短文本快速创建知识原子，自动检测类型并生成结构。
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple
from urllib.parse import quote


class QuickCapture:
    """一句话知识捕获器

    从简短文本快速创建 OKF 知识原子，自动：
    - 检测知识类型（facts/config/commands/guides）
    - 提取主题生成 slug
    - 生成 frontmatter
    """

    # 类型检测关键词映射
    TYPE_KEYWORDS = {
        'facts': ['端口', 'port', '地址', 'address', 'ip', '版本', 'version', '状态', 'status'],
        'config': ['配置', 'config', '设置', 'setting', '环境变量', 'env', '参数', 'parameter'],
        'commands': ['命令', 'command', '执行', 'run', '启动', 'start', '停止', 'stop', '重启', 'restart'],
        'guides': ['安装', 'install', '部署', 'deploy', '升级', 'upgrade', '配置步骤', '教程', 'tutorial']
    }

    def __init__(self, kb_dir: Path):
        """初始化捕获器

        Args:
            kb_dir: 知识库根目录
        """
        self.kb_dir = Path(kb_dir)

    def capture(self, text: str) -> Tuple[bool, str]:
        """从一句话创建知识原子

        Args:
            text: 输入的简短文本

        Returns:
            (success, message): 成功状态和消息
        """
        if not text or not text.strip():
            return False, "文本不能为空"

        text = text.strip()

        # 解析事实信息
        parsed = self._parse_fact(text)

        # 检测类型
        kb_type = self._detect_type(text)

        # 确定目标目录
        type_dir = self.kb_dir / kb_type
        type_dir.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        slug = parsed['slug']
        filename = f"{slug}-{timestamp}.md"
        filepath = type_dir / filename

        # 生成 frontmatter
        frontmatter = self._generate_frontmatter(parsed, kb_type)

        # 写入文件
        content = f"---\n{frontmatter}---\n\n{parsed['content']}\n"
        filepath.write_text(content, encoding='utf-8')

        return True, f"已创建: {filepath.relative_to(self.kb_dir)}"

    def _parse_fact(self, text: str) -> Dict:
        """解析事实信息

        Args:
            text: 输入文本

        Returns:
            包含 title, slug, subject, content 的字典
        """
        # 提取主题（第一个名词性短语或关键词）
        subject = self._extract_subject(text)

        # 生成 slug
        slug = self._generate_slug(subject)

        # 清理内容
        content = text.strip()

        # 生成标题（取前 50 字符）
        title = text[:50].rstrip()
        if len(text) > 50:
            title += "..."

        return {
            'title': title,
            'slug': slug,
            'subject': subject,
            'content': content
        }

    def _detect_type(self, text: str) -> str:
        """检测知识类型

        Args:
            text: 输入文本

        Returns:
            类型目录名（facts/config/commands/guides）
        """
        text_lower = text.lower()

        # 按优先级检测（guides > commands > config > facts）
        for kb_type in ['guides', 'commands', 'config', 'facts']:
            keywords = self.TYPE_KEYWORDS.get(kb_type, [])
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    return kb_type

        # 默认为 facts
        return 'facts'

    def _extract_subject(self, text: str) -> str:
        """提取主题

        Args:
            text: 输入文本

        Returns:
            主题字符串
        """
        # 尝试匹配常见模式
        patterns = [
            r'(.+?)的',           # "XXX的..."
            r'(.+?)是',           # "XXX是..."
            r'(.+?)为',           # "XXX为..."
            r'关于(.+?)[，,]',    # "关于XXX，"
            r'(.+?)[：:]',        # "XXX："
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                subject = match.group(1).strip()
                if subject and len(subject) <= 20:
                    return subject

        # 无法提取时，取前 15 字符
        return text[:15].strip()

    def _generate_slug(self, subject: str) -> str:
        """生成 URL 友好的 slug

        Args:
            subject: 主题字符串

        Returns:
            slug 字符串
        """
        # 移除特殊字符
        slug = re.sub(r'[^\w一-鿿-]', '-', subject)
        # 合并多个连字符
        slug = re.sub(r'-+', '-', slug)
        # 移除首尾连字符
        slug = slug.strip('-')
        # 限制长度
        if len(slug) > 30:
            slug = slug[:30].rstrip('-')

        return slug or 'note'

    def _generate_frontmatter(self, parsed: Dict, kb_type: str) -> str:
        """生成 frontmatter

        Args:
            parsed: 解析后的信息
            kb_type: 知识类型

        Returns:
            YAML frontmatter 字符串
        """
        timestamp = datetime.now().isoformat()

        lines = [
            f"type: {kb_type.rstrip('s')}",  # 单数形式
            f"title: {parsed['title']}",
            f"description: {parsed['content'][:100]}",
            f"timestamp: {timestamp}",
        ]

        # 添加标签
        if parsed['subject']:
            lines.append(f"tags: ['{parsed['subject']}']")

        return '\n'.join(lines) + '\n'
