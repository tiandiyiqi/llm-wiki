"""测试 DatabaseManager 抽象基类

测试抽象方法的定义和接口契约。
"""

import pytest
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

# 使用测试辅助模块处理导入
from tests.core.test_helper import get_DatabaseManager

# 获取实际的类
DatabaseManager = get_DatabaseManager()


class TestDatabaseManagerAbstractInterface:
    """测试 DatabaseManager 抽象接口定义"""

    def test_is_abstract_class(self):
        """验证 DatabaseManager 是抽象类"""
        assert issubclass(DatabaseManager, ABC)

    def test_cannot_instantiate_directly(self):
        """验证不能直接实例化抽象类"""
        with pytest.raises(TypeError):
            DatabaseManager()

    def test_has_initialize_method(self):
        """验证 initialize 是抽象方法"""
        assert hasattr(DatabaseManager, 'initialize')
        assert getattr(DatabaseManager.initialize, '__isabstractmethod__', False)

    def test_has_close_method(self):
        """验证 close 是抽象方法"""
        assert hasattr(DatabaseManager, 'close')
        assert getattr(DatabaseManager.close, '__isabstractmethod__', False)

    def test_has_is_connected_method(self):
        """验证 is_connected 是抽象方法"""
        assert hasattr(DatabaseManager, 'is_connected')
        assert getattr(DatabaseManager.is_connected, '__isabstractmethod__', False)


class TestDatabaseManagerKnowledgeBaseMethods:
    """测试知识库相关抽象方法"""

    def test_has_create_kb_method(self):
        """验证 create_kb 是抽象方法"""
        assert hasattr(DatabaseManager, 'create_kb')
        assert getattr(DatabaseManager.create_kb, '__isabstractmethod__', False)

    def test_has_get_kb_method(self):
        """验证 get_kb 是抽象方法"""
        assert hasattr(DatabaseManager, 'get_kb')
        assert getattr(DatabaseManager.get_kb, '__isabstractmethod__', False)

    def test_has_get_kb_by_name_method(self):
        """验证 get_kb_by_name 是抽象方法"""
        assert hasattr(DatabaseManager, 'get_kb_by_name')
        assert getattr(DatabaseManager.get_kb_by_name, '__isabstractmethod__', False)

    def test_has_list_kbs_method(self):
        """验证 list_kbs 是抽象方法"""
        assert hasattr(DatabaseManager, 'list_kbs')
        assert getattr(DatabaseManager.list_kbs, '__isabstractmethod__', False)

    def test_has_update_kb_method(self):
        """验证 update_kb 是抽象方法"""
        assert hasattr(DatabaseManager, 'update_kb')
        assert getattr(DatabaseManager.update_kb, '__isabstractmethod__', False)

    def test_has_delete_kb_method(self):
        """验证 delete_kb 是抽象方法"""
        assert hasattr(DatabaseManager, 'delete_kb')
        assert getattr(DatabaseManager.delete_kb, '__isabstractmethod__', False)


class TestDatabaseManagerAtomMethods:
    """测试知识原子相关抽象方法"""

    def test_has_create_atom_method(self):
        """验证 create_atom 是抽象方法"""
        assert hasattr(DatabaseManager, 'create_atom')
        assert getattr(DatabaseManager.create_atom, '__isabstractmethod__', False)

    def test_has_get_atom_method(self):
        """验证 get_atom 是抽象方法"""
        assert hasattr(DatabaseManager, 'get_atom')
        assert getattr(DatabaseManager.get_atom, '__isabstractmethod__', False)

    def test_has_get_atom_by_path_method(self):
        """验证 get_atom_by_path 是抽象方法"""
        assert hasattr(DatabaseManager, 'get_atom_by_path')
        assert getattr(DatabaseManager.get_atom_by_path, '__isabstractmethod__', False)

    def test_has_update_atom_method(self):
        """验证 update_atom 是抽象方法"""
        assert hasattr(DatabaseManager, 'update_atom')
        assert getattr(DatabaseManager.update_atom, '__isabstractmethod__', False)

    def test_has_delete_atom_method(self):
        """验证 delete_atom 是抽象方法"""
        assert hasattr(DatabaseManager, 'delete_atom')
        assert getattr(DatabaseManager.delete_atom, '__isabstractmethod__', False)

    def test_has_list_atoms_method(self):
        """验证 list_atoms 是抽象方法"""
        assert hasattr(DatabaseManager, 'list_atoms')
        assert getattr(DatabaseManager.list_atoms, '__isabstractmethod__', False)


class TestDatabaseManagerSearchMethods:
    """测试搜索相关抽象方法"""

    def test_has_search_atoms_method(self):
        """验证 search_atoms 是抽象方法"""
        assert hasattr(DatabaseManager, 'search_atoms')
        assert getattr(DatabaseManager.search_atoms, '__isabstractmethod__', False)

    def test_has_search_atoms_advanced_method(self):
        """验证 search_atoms_advanced 是抽象方法"""
        assert hasattr(DatabaseManager, 'search_atoms_advanced')
        assert getattr(DatabaseManager.search_atoms_advanced, '__isabstractmethod__', False)


class TestDatabaseManagerHierarchyMethods:
    """测试父子知识库相关抽象方法"""

    def test_has_register_child_kb_method(self):
        """验证 register_child_kb 是抽象方法"""
        assert hasattr(DatabaseManager, 'register_child_kb')
        assert getattr(DatabaseManager.register_child_kb, '__isabstractmethod__', False)

    def test_has_get_child_kbs_method(self):
        """验证 get_child_kbs 是抽象方法"""
        assert hasattr(DatabaseManager, 'get_child_kbs')
        assert getattr(DatabaseManager.get_child_kbs, '__isabstractmethod__', False)

    def test_has_get_parent_kb_method(self):
        """验证 get_parent_kb 是抽象方法"""
        assert hasattr(DatabaseManager, 'get_parent_kb')
        assert getattr(DatabaseManager.get_parent_kb, '__isabstractmethod__', False)


class TestDatabaseManagerStatsMethods:
    """测试统计相关抽象方法"""

    def test_has_get_kb_stats_method(self):
        """验证 get_kb_stats 是抽象方法"""
        assert hasattr(DatabaseManager, 'get_kb_stats')
        assert getattr(DatabaseManager.get_kb_stats, '__isabstractmethod__', False)

    def test_has_get_atom_count_method(self):
        """验证 get_atom_count 是抽象方法"""
        assert hasattr(DatabaseManager, 'get_atom_count')
        assert getattr(DatabaseManager.get_atom_count, '__isabstractmethod__', False)


class TestDatabaseManagerTransactionMethods:
    """测试事务相关抽象方法"""

    def test_has_begin_transaction_method(self):
        """验证 begin_transaction 是抽象方法"""
        assert hasattr(DatabaseManager, 'begin_transaction')
        assert getattr(DatabaseManager.begin_transaction, '__isabstractmethod__', False)

    def test_has_commit_transaction_method(self):
        """验证 commit_transaction 是抽象方法"""
        assert hasattr(DatabaseManager, 'commit_transaction')
        assert getattr(DatabaseManager.commit_transaction, '__isabstractmethod__', False)

    def test_has_rollback_transaction_method(self):
        """验证 rollback_transaction 是抽象方法"""
        assert hasattr(DatabaseManager, 'rollback_transaction')
        assert getattr(DatabaseManager.rollback_transaction, '__isabstractmethod__', False)


class TestDatabaseManagerUtilityMethods:
    """测试工具方法"""

    def test_has_get_timestamp_method(self):
        """验证 _get_timestamp 方法存在"""
        assert hasattr(DatabaseManager, '_get_timestamp')

    def test_get_timestamp_returns_iso_format(self):
        """验证 _get_timestamp 返回 ISO 格式时间戳"""
        # 创建一个最小实现类来测试工具方法
        class MinimalManager(DatabaseManager):
            async def initialize(self) -> None: pass
            async def close(self) -> None: pass
            async def is_connected(self) -> bool: return True
            async def create_kb(self, kb_data: Dict[str, Any]) -> int: return 1
            async def get_kb(self, kb_id: int) -> Optional[Dict[str, Any]]: return None
            async def get_kb_by_name(self, name: str) -> Optional[Dict[str, Any]]: return None
            async def list_kbs(self, user_id: Optional[str] = None, scope: str = 'all') -> List[Dict[str, Any]]: return []
            async def update_kb(self, kb_id: int, kb_data: Dict[str, Any]) -> bool: return False
            async def delete_kb(self, kb_id: int) -> bool: return False
            async def create_atom(self, atom_data: Dict[str, Any]) -> int: return 1
            async def get_atom(self, atom_id: int) -> Optional[Dict[str, Any]]: return None
            async def get_atom_by_path(self, kb_id: int, path: str) -> Optional[Dict[str, Any]]: return None
            async def update_atom(self, atom_id: int, atom_data: Dict[str, Any]) -> bool: return False
            async def delete_atom(self, atom_id: int) -> bool: return False
            async def list_atoms(self, kb_id: int, by_type: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]: return []
            async def search_atoms(self, query: str, kb_id: Optional[int] = None, by_type: Optional[str] = None, tags: Optional[List[str]] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]: return []
            async def search_atoms_advanced(self, query: str, filters: Optional[Dict[str, Any]] = None, sort_by: str = 'relevance', limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]: return []
            async def register_child_kb(self, parent_id: int, child_id: int, child_path: str) -> bool: return False
            async def get_child_kbs(self, parent_id: int) -> List[Dict[str, Any]]: return []
            async def get_parent_kb(self, child_id: int) -> Optional[Dict[str, Any]]: return None
            async def get_kb_stats(self, kb_id: int) -> Dict[str, Any]: return {}
            async def get_atom_count(self, kb_id: int, by_type: Optional[str] = None) -> int: return 0
            async def begin_transaction(self) -> None: pass
            async def commit_transaction(self) -> None: pass
            async def rollback_transaction(self) -> None: pass

        manager = MinimalManager()
        timestamp = manager._get_timestamp()

        # 验证时间戳是字符串且包含 T（ISO 格式特征）
        assert isinstance(timestamp, str)
        assert 'T' in timestamp

    def test_has_validate_kb_data_method(self):
        """验证 _validate_kb_data 方法存在"""
        assert hasattr(DatabaseManager, '_validate_kb_data')

    def test_validate_kb_data_with_valid_data(self):
        """验证有效知识库数据通过校验"""
        class MinimalManager(DatabaseManager):
            async def initialize(self) -> None: pass
            async def close(self) -> None: pass
            async def is_connected(self) -> bool: return True
            async def create_kb(self, kb_data: Dict[str, Any]) -> int: return 1
            async def get_kb(self, kb_id: int) -> Optional[Dict[str, Any]]: return None
            async def get_kb_by_name(self, name: str) -> Optional[Dict[str, Any]]: return None
            async def list_kbs(self, user_id: Optional[str] = None, scope: str = 'all') -> List[Dict[str, Any]]: return []
            async def update_kb(self, kb_id: int, kb_data: Dict[str, Any]) -> bool: return False
            async def delete_kb(self, kb_id: int) -> bool: return False
            async def create_atom(self, atom_data: Dict[str, Any]) -> int: return 1
            async def get_atom(self, atom_id: int) -> Optional[Dict[str, Any]]: return None
            async def get_atom_by_path(self, kb_id: int, path: str) -> Optional[Dict[str, Any]]: return None
            async def update_atom(self, atom_id: int, atom_data: Dict[str, Any]) -> bool: return False
            async def delete_atom(self, atom_id: int) -> bool: return False
            async def list_atoms(self, kb_id: int, by_type: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]: return []
            async def search_atoms(self, query: str, kb_id: Optional[int] = None, by_type: Optional[str] = None, tags: Optional[List[str]] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]: return []
            async def search_atoms_advanced(self, query: str, filters: Optional[Dict[str, Any]] = None, sort_by: str = 'relevance', limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]: return []
            async def register_child_kb(self, parent_id: int, child_id: int, child_path: str) -> bool: return False
            async def get_child_kbs(self, parent_id: int) -> List[Dict[str, Any]]: return []
            async def get_parent_kb(self, child_id: int) -> Optional[Dict[str, Any]]: return None
            async def get_kb_stats(self, kb_id: int) -> Dict[str, Any]: return {}
            async def get_atom_count(self, kb_id: int, by_type: Optional[str] = None) -> int: return 0
            async def begin_transaction(self) -> None: pass
            async def commit_transaction(self) -> None: pass
            async def rollback_transaction(self) -> None: pass

        manager = MinimalManager()

        # 有效数据
        assert manager._validate_kb_data({'name': 'test', 'path': '/test'}) is True
        assert manager._validate_kb_data({'name': 'test', 'path': '/test', 'description': 'desc'}) is True

    def test_validate_kb_data_with_missing_name(self):
        """验证缺少 name 字段的数据被拒绝"""
        class MinimalManager(DatabaseManager):
            async def initialize(self) -> None: pass
            async def close(self) -> None: pass
            async def is_connected(self) -> bool: return True
            async def create_kb(self, kb_data: Dict[str, Any]) -> int: return 1
            async def get_kb(self, kb_id: int) -> Optional[Dict[str, Any]]: return None
            async def get_kb_by_name(self, name: str) -> Optional[Dict[str, Any]]: return None
            async def list_kbs(self, user_id: Optional[str] = None, scope: str = 'all') -> List[Dict[str, Any]]: return []
            async def update_kb(self, kb_id: int, kb_data: Dict[str, Any]) -> bool: return False
            async def delete_kb(self, kb_id: int) -> bool: return False
            async def create_atom(self, atom_data: Dict[str, Any]) -> int: return 1
            async def get_atom(self, atom_id: int) -> Optional[Dict[str, Any]]: return None
            async def get_atom_by_path(self, kb_id: int, path: str) -> Optional[Dict[str, Any]]: return None
            async def update_atom(self, atom_id: int, atom_data: Dict[str, Any]) -> bool: return False
            async def delete_atom(self, atom_id: int) -> bool: return False
            async def list_atoms(self, kb_id: int, by_type: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]: return []
            async def search_atoms(self, query: str, kb_id: Optional[int] = None, by_type: Optional[str] = None, tags: Optional[List[str]] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]: return []
            async def search_atoms_advanced(self, query: str, filters: Optional[Dict[str, Any]] = None, sort_by: str = 'relevance', limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]: return []
            async def register_child_kb(self, parent_id: int, child_id: int, child_path: str) -> bool: return False
            async def get_child_kbs(self, parent_id: int) -> List[Dict[str, Any]]: return []
            async def get_parent_kb(self, child_id: int) -> Optional[Dict[str, Any]]: return None
            async def get_kb_stats(self, kb_id: int) -> Dict[str, Any]: return {}
            async def get_atom_count(self, kb_id: int, by_type: Optional[str] = None) -> int: return 0
            async def begin_transaction(self) -> None: pass
            async def commit_transaction(self) -> None: pass
            async def rollback_transaction(self) -> None: pass

        manager = MinimalManager()

        # 缺少 name
        assert manager._validate_kb_data({'path': '/test'}) is False

    def test_validate_kb_data_with_missing_path(self):
        """验证缺少 path 字段的数据被拒绝"""
        class MinimalManager(DatabaseManager):
            async def initialize(self) -> None: pass
            async def close(self) -> None: pass
            async def is_connected(self) -> bool: return True
            async def create_kb(self, kb_data: Dict[str, Any]) -> int: return 1
            async def get_kb(self, kb_id: int) -> Optional[Dict[str, Any]]: return None
            async def get_kb_by_name(self, name: str) -> Optional[Dict[str, Any]]: return None
            async def list_kbs(self, user_id: Optional[str] = None, scope: str = 'all') -> List[Dict[str, Any]]: return []
            async def update_kb(self, kb_id: int, kb_data: Dict[str, Any]) -> bool: return False
            async def delete_kb(self, kb_id: int) -> bool: return False
            async def create_atom(self, atom_data: Dict[str, Any]) -> int: return 1
            async def get_atom(self, atom_id: int) -> Optional[Dict[str, Any]]: return None
            async def get_atom_by_path(self, kb_id: int, path: str) -> Optional[Dict[str, Any]]: return None
            async def update_atom(self, atom_id: int, atom_data: Dict[str, Any]) -> bool: return False
            async def delete_atom(self, atom_id: int) -> bool: return False
            async def list_atoms(self, kb_id: int, by_type: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]: return []
            async def search_atoms(self, query: str, kb_id: Optional[int] = None, by_type: Optional[str] = None, tags: Optional[List[str]] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]: return []
            async def search_atoms_advanced(self, query: str, filters: Optional[Dict[str, Any]] = None, sort_by: str = 'relevance', limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]: return []
            async def register_child_kb(self, parent_id: int, child_id: int, child_path: str) -> bool: return False
            async def get_child_kbs(self, parent_id: int) -> List[Dict[str, Any]]: return []
            async def get_parent_kb(self, child_id: int) -> Optional[Dict[str, Any]]: return None
            async def get_kb_stats(self, kb_id: int) -> Dict[str, Any]: return {}
            async def get_atom_count(self, kb_id: int, by_type: Optional[str] = None) -> int: return 0
            async def begin_transaction(self) -> None: pass
            async def commit_transaction(self) -> None: pass
            async def rollback_transaction(self) -> None: pass

        manager = MinimalManager()

        # 缺少 path
        assert manager._validate_kb_data({'name': 'test'}) is False

    def test_validate_kb_data_with_empty_dict(self):
        """验证空字典被拒绝"""
        class MinimalManager(DatabaseManager):
            async def initialize(self) -> None: pass
            async def close(self) -> None: pass
            async def is_connected(self) -> bool: return True
            async def create_kb(self, kb_data: Dict[str, Any]) -> int: return 1
            async def get_kb(self, kb_id: int) -> Optional[Dict[str, Any]]: return None
            async def get_kb_by_name(self, name: str) -> Optional[Dict[str, Any]]: return None
            async def list_kbs(self, user_id: Optional[str] = None, scope: str = 'all') -> List[Dict[str, Any]]: return []
            async def update_kb(self, kb_id: int, kb_data: Dict[str, Any]) -> bool: return False
            async def delete_kb(self, kb_id: int) -> bool: return False
            async def create_atom(self, atom_data: Dict[str, Any]) -> int: return 1
            async def get_atom(self, atom_id: int) -> Optional[Dict[str, Any]]: return None
            async def get_atom_by_path(self, kb_id: int, path: str) -> Optional[Dict[str, Any]]: return None
            async def update_atom(self, atom_id: int, atom_data: Dict[str, Any]) -> bool: return False
            async def delete_atom(self, atom_id: int) -> bool: return False
            async def list_atoms(self, kb_id: int, by_type: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]: return []
            async def search_atoms(self, query: str, kb_id: Optional[int] = None, by_type: Optional[str] = None, tags: Optional[List[str]] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]: return []
            async def search_atoms_advanced(self, query: str, filters: Optional[Dict[str, Any]] = None, sort_by: str = 'relevance', limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]: return []
            async def register_child_kb(self, parent_id: int, child_id: int, child_path: str) -> bool: return False
            async def get_child_kbs(self, parent_id: int) -> List[Dict[str, Any]]: return []
            async def get_parent_kb(self, child_id: int) -> Optional[Dict[str, Any]]: return None
            async def get_kb_stats(self, kb_id: int) -> Dict[str, Any]: return {}
            async def get_atom_count(self, kb_id: int, by_type: Optional[str] = None) -> int: return 0
            async def begin_transaction(self) -> None: pass
            async def commit_transaction(self) -> None: pass
            async def rollback_transaction(self) -> None: pass

        manager = MinimalManager()

        # 空字典
        assert manager._validate_kb_data({}) is False

    def test_has_validate_atom_data_method(self):
        """验证 _validate_atom_data 方法存在"""
        assert hasattr(DatabaseManager, '_validate_atom_data')

    def test_validate_atom_data_with_valid_data(self):
        """验证有效原子数据通过校验"""
        class MinimalManager(DatabaseManager):
            async def initialize(self) -> None: pass
            async def close(self) -> None: pass
            async def is_connected(self) -> bool: return True
            async def create_kb(self, kb_data: Dict[str, Any]) -> int: return 1
            async def get_kb(self, kb_id: int) -> Optional[Dict[str, Any]]: return None
            async def get_kb_by_name(self, name: str) -> Optional[Dict[str, Any]]: return None
            async def list_kbs(self, user_id: Optional[str] = None, scope: str = 'all') -> List[Dict[str, Any]]: return []
            async def update_kb(self, kb_id: int, kb_data: Dict[str, Any]) -> bool: return False
            async def delete_kb(self, kb_id: int) -> bool: return False
            async def create_atom(self, atom_data: Dict[str, Any]) -> int: return 1
            async def get_atom(self, atom_id: int) -> Optional[Dict[str, Any]]: return None
            async def get_atom_by_path(self, kb_id: int, path: str) -> Optional[Dict[str, Any]]: return None
            async def update_atom(self, atom_id: int, atom_data: Dict[str, Any]) -> bool: return False
            async def delete_atom(self, atom_id: int) -> bool: return False
            async def list_atoms(self, kb_id: int, by_type: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]: return []
            async def search_atoms(self, query: str, kb_id: Optional[int] = None, by_type: Optional[str] = None, tags: Optional[List[str]] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]: return []
            async def search_atoms_advanced(self, query: str, filters: Optional[Dict[str, Any]] = None, sort_by: str = 'relevance', limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]: return []
            async def register_child_kb(self, parent_id: int, child_id: int, child_path: str) -> bool: return False
            async def get_child_kbs(self, parent_id: int) -> List[Dict[str, Any]]: return []
            async def get_parent_kb(self, child_id: int) -> Optional[Dict[str, Any]]: return None
            async def get_kb_stats(self, kb_id: int) -> Dict[str, Any]: return {}
            async def get_atom_count(self, kb_id: int, by_type: Optional[str] = None) -> int: return 0
            async def begin_transaction(self) -> None: pass
            async def commit_transaction(self) -> None: pass
            async def rollback_transaction(self) -> None: pass

        manager = MinimalManager()

        # 有效数据
        assert manager._validate_atom_data({'kb_id': 1, 'path': '/test', 'type': 'note', 'title': 'Test'}) is True
        assert manager._validate_atom_data({'kb_id': 1, 'path': '/test', 'type': 'note', 'title': 'Test', 'body': 'content'}) is True

    def test_validate_atom_data_with_missing_fields(self):
        """验证缺少必需字段的原子数据被拒绝"""
        class MinimalManager(DatabaseManager):
            async def initialize(self) -> None: pass
            async def close(self) -> None: pass
            async def is_connected(self) -> bool: return True
            async def create_kb(self, kb_data: Dict[str, Any]) -> int: return 1
            async def get_kb(self, kb_id: int) -> Optional[Dict[str, Any]]: return None
            async def get_kb_by_name(self, name: str) -> Optional[Dict[str, Any]]: return None
            async def list_kbs(self, user_id: Optional[str] = None, scope: str = 'all') -> List[Dict[str, Any]]: return []
            async def update_kb(self, kb_id: int, kb_data: Dict[str, Any]) -> bool: return False
            async def delete_kb(self, kb_id: int) -> bool: return False
            async def create_atom(self, atom_data: Dict[str, Any]) -> int: return 1
            async def get_atom(self, atom_id: int) -> Optional[Dict[str, Any]]: return None
            async def get_atom_by_path(self, kb_id: int, path: str) -> Optional[Dict[str, Any]]: return None
            async def update_atom(self, atom_id: int, atom_data: Dict[str, Any]) -> bool: return False
            async def delete_atom(self, atom_id: int) -> bool: return False
            async def list_atoms(self, kb_id: int, by_type: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]: return []
            async def search_atoms(self, query: str, kb_id: Optional[int] = None, by_type: Optional[str] = None, tags: Optional[List[str]] = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]: return []
            async def search_atoms_advanced(self, query: str, filters: Optional[Dict[str, Any]] = None, sort_by: str = 'relevance', limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]: return []
            async def register_child_kb(self, parent_id: int, child_id: int, child_path: str) -> bool: return False
            async def get_child_kbs(self, parent_id: int) -> List[Dict[str, Any]]: return []
            async def get_parent_kb(self, child_id: int) -> Optional[Dict[str, Any]]: return None
            async def get_kb_stats(self, kb_id: int) -> Dict[str, Any]: return {}
            async def get_atom_count(self, kb_id: int, by_type: Optional[str] = None) -> int: return 0
            async def begin_transaction(self) -> None: pass
            async def commit_transaction(self) -> None: pass
            async def rollback_transaction(self) -> None: pass

        manager = MinimalManager()

        # 缺少 kb_id
        assert manager._validate_atom_data({'path': '/test', 'type': 'note', 'title': 'Test'}) is False
        # 缺少 path
        assert manager._validate_atom_data({'kb_id': 1, 'type': 'note', 'title': 'Test'}) is False
        # 缺少 type
        assert manager._validate_atom_data({'kb_id': 1, 'path': '/test', 'title': 'Test'}) is False
        # 缺少 title
        assert manager._validate_atom_data({'kb_id': 1, 'path': '/test', 'type': 'note'}) is False
        # 空字典
        assert manager._validate_atom_data({}) is False


class TestDatabaseManagerMethodSignatures:
    """测试方法签名正确性"""

    @pytest.mark.asyncio
    async def test_initialize_signature(self):
        """验证 initialize 方法签名"""
        import inspect
        sig = inspect.signature(DatabaseManager.initialize)
        params = list(sig.parameters.keys())
        assert 'self' in params

    @pytest.mark.asyncio
    async def test_create_kb_signature(self):
        """验证 create_kb 方法签名"""
        import inspect
        sig = inspect.signature(DatabaseManager.create_kb)
        params = list(sig.parameters.keys())
        assert 'self' in params
        assert 'kb_data' in params

    @pytest.mark.asyncio
    async def test_get_kb_signature(self):
        """验证 get_kb 方法签名"""
        import inspect
        sig = inspect.signature(DatabaseManager.get_kb)
        params = list(sig.parameters.keys())
        assert 'self' in params
        assert 'kb_id' in params

    @pytest.mark.asyncio
    async def test_create_atom_signature(self):
        """验证 create_atom 方法签名"""
        import inspect
        sig = inspect.signature(DatabaseManager.create_atom)
        params = list(sig.parameters.keys())
        assert 'self' in params
        assert 'atom_data' in params

    @pytest.mark.asyncio
    async def test_search_atoms_signature(self):
        """验证 search_atoms 方法签名"""
        import inspect
        sig = inspect.signature(DatabaseManager.search_atoms)
        params = list(sig.parameters.keys())
        assert 'self' in params
        assert 'query' in params
        assert 'kb_id' in params
        assert 'limit' in params
        assert 'offset' in params

    @pytest.mark.asyncio
    async def test_list_atoms_signature(self):
        """验证 list_atoms 方法签名"""
        import inspect
        sig = inspect.signature(DatabaseManager.list_atoms)
        params = list(sig.parameters.keys())
        assert 'self' in params
        assert 'kb_id' in params
        assert 'by_type' in params
        assert 'limit' in params
        assert 'offset' in params


class TestDatabaseManagerAbstractCount:
    """测试抽象方法数量"""

    def test_abstract_methods_count(self):
        """验证抽象方法数量正确（确保接口完整）"""
        abstract_methods = [
            'initialize', 'close', 'is_connected',
            'create_kb', 'get_kb', 'get_kb_by_name', 'list_kbs', 'update_kb', 'delete_kb',
            'create_atom', 'get_atom', 'get_atom_by_path', 'update_atom', 'delete_atom', 'list_atoms',
            'search_atoms', 'search_atoms_advanced',
            'register_child_kb', 'get_child_kbs', 'get_parent_kb',
            'get_kb_stats', 'get_atom_count',
            'begin_transaction', 'commit_transaction', 'rollback_transaction'
        ]

        actual_abstract_methods = [
            name for name in dir(DatabaseManager)
            if getattr(getattr(DatabaseManager, name), '__isabstractmethod__', False)
        ]

        assert set(abstract_methods) == set(actual_abstract_methods), \
            f"Expected: {set(abstract_methods)}, Got: {set(actual_abstract_methods)}"
