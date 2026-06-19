"""知识库文件监控器

监控知识库目录的文件变化，自动处理新增或修改的 Markdown 文件。
"""

import time
from pathlib import Path
from typing import Callable, List, Optional

from watchdog.observers import Observer
from watchdog.events import FileSystemEvent, FileSystemEventHandler

from .registry import KBRegistry
from .quick_capture import QuickCapture
from .ingestor import KnowledgeIngestor


class KnowledgeWatcher(FileSystemEventHandler):
    """知识库文件监控器

    监控知识库目录的文件变化，自动：
    - 检测 .md 文件的新增和修改
    - 短内容使用 QuickCapture 快速处理
    - 长内容使用 KnowledgeIngestor 完整处理
    - 忽略 atoms/ 目录避免循环
    """

    # 短内容阈值（字符数）
    SHORT_CONTENT_THRESHOLD = 200

    def __init__(self, kb_dir: Path, registry: KBRegistry):
        """初始化监控器

        Args:
            kb_dir: 知识库根目录
            registry: 知识库注册表实例
        """
        super().__init__()
        self.kb_dir = Path(kb_dir)
        self.registry = registry
        self.observer: Optional[Observer] = None
        self._progress_callback: Optional[Callable[[str], None]] = None

        # 初始化处理器
        self.quick_capture = QuickCapture(self.kb_dir)
        self.ingestor = KnowledgeIngestor(self.kb_dir, self.kb_dir)

    def set_progress_callback(self, callback: Callable[[str], None]) -> None:
        """设置进度回调函数

        Args:
            callback: 进度消息回调函数
        """
        self._progress_callback = callback

    def _report(self, message: str) -> None:
        """报告进度消息

        Args:
            message: 进度消息
        """
        if self._progress_callback:
            self._progress_callback(message)
        print(message)

    def start(self, watch_paths: List[Path]) -> None:
        """开始监控指定路径

        Args:
            watch_paths: 要监控的路径列表
        """
        if self.observer is not None:
            self._report("⚠️  监控器已在运行")
            return

        self.observer = Observer()

        for path in watch_paths:
            path = Path(path)
            if path.exists():
                self.observer.schedule(self, str(path), recursive=True)
                self._report(f"📁 监控目录: {path}")
            else:
                self._report(f"⚠️  路径不存在: {path}")

        self.observer.start()
        self._report("✅ 文件监控已启动 (Ctrl+C 停止)")

    def stop(self) -> None:
        """停止监控"""
        if self.observer is not None:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            self._report("🛑 文件监控已停止")

    def _should_process(self, event: FileSystemEvent) -> bool:
        """判断是否应该处理该事件

        Args:
            event: 文件系统事件

        Returns:
            是否应该处理
        """
        # 只处理 .md 文件
        path = Path(event.src_path)
        if path.suffix != '.md':
            return False

        # 忽略 atoms/ 目录（避免循环）
        if 'atoms/' in str(path) or path.parts[-2:-1] == ('atoms',):
            return False

        # 忽略隐藏文件
        if path.name.startswith('.'):
            return False

        # 忽略 index.md 和 log.md
        if path.name in ('index.md', 'log.md'):
            return False

        return True

    def _get_file_content(self, path: Path) -> Optional[str]:
        """安全读取文件内容

        Args:
            path: 文件路径

        Returns:
            文件内容，读取失败返回 None
        """
        try:
            return path.read_text(encoding='utf-8')
        except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
            self._report(f"⚠️  读取文件失败: {path} - {e}")
            return None

    def _process_file(self, file_path: Path) -> None:
        """处理单个文件

        Args:
            file_path: 文件路径
        """
        content = self._get_file_content(file_path)
        if content is None:
            return

        # 计算内容长度（去除 frontmatter）
        content_body = self._extract_content_body(content)

        if len(content_body) < self.SHORT_CONTENT_THRESHOLD:
            # 短内容：使用 QuickCapture 处理
            self._report(f"📝 短内容处理: {file_path.name}")
            success, message = self.quick_capture.capture(content_body)
            if success:
                self._report(f"   ✅ {message}")
            else:
                self._report(f"   ❌ {message}")
        else:
            # 长内容：使用 KnowledgeIngestor 处理
            self._report(f"📄 长内容处理: {file_path.name}")
            try:
                success = self.ingestor.ingest(
                    source_path=file_path,
                    auto_detect_type=True
                )
                if success:
                    self._report(f"   ✅ 已摄入: {file_path.name}")
                else:
                    self._report(f"   ❌ 摄入失败: {file_path.name}")
            except Exception as e:
                self._report(f"   ❌ 摄入异常: {file_path.name} - {e}")

    def _extract_content_body(self, content: str) -> str:
        """提取内容主体（去除 frontmatter）

        Args:
            content: 原始文件内容

        Returns:
            去除 frontmatter 后的内容
        """
        # 检查是否有 frontmatter
        if not content.startswith('---'):
            return content.strip()

        # 找到第二个 ---
        lines = content.split('\n')
        end_index = -1
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                end_index = i
                break

        if end_index == -1:
            return content.strip()

        # 返回 frontmatter 之后的内容
        body = '\n'.join(lines[end_index + 1:])
        return body.strip()

    def on_created(self, event: FileSystemEvent) -> None:
        """文件创建事件处理

        Args:
            event: 文件系统事件
        """
        if event.is_directory:
            return

        if not self._should_process(event):
            return

        file_path = Path(event.src_path)
        self._report(f"\n🔔 新文件: {file_path}")
        self._process_file(file_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        """文件修改事件处理

        Args:
            event: 文件系统事件
        """
        if event.is_directory:
            return

        if not self._should_process(event):
            return

        file_path = Path(event.src_path)
        self._report(f"\n✏️  文件修改: {file_path}")
        self._process_file(file_path)

    def run_forever(self) -> None:
        """阻塞运行，直到收到停止信号"""
        if self.observer is None:
            self._report("❌ 监控器未启动")
            return

        try:
            while self.observer.is_alive():
                self.observer.join(0.5)
        except KeyboardInterrupt:
            self._report("\n⏹️  收到停止信号")
            self.stop()
