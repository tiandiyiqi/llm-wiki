"""事务管理工具，提供上下文管理器和回滚保障.

为多步数据库操作提供原子性保障：
- TransactionContext: 跟踪事务状态和操作历史
- transaction(): 异步上下文管理器，自动提交/回滚
- with_retry(): 带重试的事务执行
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Callable, Awaitable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .db_storage import DatabaseStorage

logger = logging.getLogger(__name__)


class TransactionError(Exception):
    """事务操作错误."""

    pass


class TransactionContext:
    """事务上下文，跟踪事务状态和操作历史.

    Attributes:
        storage: 数据库存储适配器
        committed: 是否已提交
        rolled_back: 是否已回滚
        operations: 已执行的操作记录列表
    """

    def __init__(self, storage: 'DatabaseStorage') -> None:
        self.storage = storage
        self.committed: bool = False
        self.rolled_back: bool = False
        self.operations: list[str] = []

    def record_operation(self, operation: str) -> None:
        """记录已执行的操作（用于调试和回滚追踪）.

        Args:
            operation: 操作描述
        """
        self.operations.append(operation)

    @property
    def is_active(self) -> bool:
        """事务是否活跃（未提交且未回滚）."""
        return not self.committed and not self.rolled_back

    @property
    def operation_count(self) -> int:
        """已执行的操作数量."""
        return len(self.operations)


@asynccontextmanager
async def transaction(
    storage: 'DatabaseStorage',
    description: str = "",
) -> AsyncGenerator[TransactionContext, None]:
    """事务上下文管理器.

    自动管理事务的开始、提交和回滚。
    正常退出时自动提交，异常时自动回滚。

    Usage:
        async with transaction(storage, "Update KB") as txn:
            await storage.update_kb(kb_id, data)
            txn.record_operation("update_kb")
            await storage.create_atom(atom_data)
            txn.record_operation("create_atom")

    Args:
        storage: 数据库存储适配器
        description: 事务描述（用于日志）

    Yields:
        TransactionContext: 事务上下文
    """
    ctx = TransactionContext(storage)

    try:
        await storage.begin_transaction()
        logger.debug("Transaction started: %s", description)
        yield ctx

        if ctx.is_active:
            await storage.commit_transaction()
            ctx.committed = True
            logger.debug(
                "Transaction committed: %s (%d operations)",
                description,
                ctx.operation_count,
            )

    except Exception as e:
        if ctx.is_active:
            try:
                await storage.rollback_transaction()
                ctx.rolled_back = True
                logger.warning(
                    "Transaction rolled back: %s - %s "
                    "(completed %d operations before failure)",
                    description,
                    e,
                    ctx.operation_count,
                )
            except Exception as rollback_error:
                logger.error(
                    "Transaction rollback failed: %s - "
                    "original error: %s, rollback error: %s",
                    description,
                    e,
                    rollback_error,
                )
                raise TransactionError(
                    f"Rollback failed after error: {e}. "
                    f"Rollback error: {rollback_error}"
                ) from rollback_error
        raise


async def with_retry(
    storage: 'DatabaseStorage',
    operation: Callable[[TransactionContext], Awaitable[Any]],
    max_retries: int = 3,
    base_delay: float = 0.1,
    description: str = "",
) -> Any:
    """带重试的事务执行.

    每次重试都会创建新事务。重试间隔采用线性退避策略。

    Args:
        storage: 数据库存储适配器
        operation: 接收 TransactionContext 的异步操作函数
        max_retries: 最大重试次数（含首次执行）
        base_delay: 基础退避延迟（秒），实际延迟 = base_delay * attempt
        description: 操作描述

    Returns:
        操作结果

    Raises:
        TransactionError: 重试次数耗尽后仍失败
    """
    last_error: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            async with transaction(storage, description) as txn:
                result = await operation(txn)
                return result
        except TransactionError:
            raise
        except Exception as e:
            last_error = e
            logger.warning(
                "Transaction attempt %d/%d failed: %s - %s",
                attempt + 1,
                max_retries,
                description,
                e,
            )
            if attempt < max_retries - 1:
                delay = base_delay * (attempt + 1)
                await asyncio.sleep(delay)

    raise TransactionError(
        f"Transaction failed after {max_retries} retries: {description}"
    ) from last_error
