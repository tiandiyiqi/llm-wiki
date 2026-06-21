"""测试辅助模块

处理模块导入问题，确保测试可以独立运行。
"""

import sys
from pathlib import Path
import importlib.util
import types

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent

# 确保 lib 在 sys.path 中
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 模块缓存
_module_cache = {}


def setup_module_imports():
    """设置模块导入，解决相对导入问题"""

    # 创建 lib 和 lib.core 的空模块
    if 'lib' not in sys.modules:
        lib_module = types.ModuleType('lib')
        lib_module.__path__ = [str(PROJECT_ROOT / 'lib')]
        lib_module.__package__ = 'lib'
        sys.modules['lib'] = lib_module

    if 'lib.core' not in sys.modules:
        lib_core_module = types.ModuleType('lib.core')
        lib_core_module.__path__ = [str(PROJECT_ROOT / 'lib' / 'core')]
        lib_core_module.__package__ = 'lib.core'
        lib_core_module.__file__ = str(PROJECT_ROOT / 'lib' / 'core' / '__init__.py')
        sys.modules['lib.core'] = lib_core_module
        # Load the real lib.core.__init__ to populate all exports
        core_init_spec = importlib.util.spec_from_file_location(
            'lib.core',
            PROJECT_ROOT / 'lib' / 'core' / '__init__.py',
            submodule_search_locations=[str(PROJECT_ROOT / 'lib' / 'core')]
        )
        if core_init_spec and core_init_spec.loader:
            try:
                core_init_spec.loader.exec_module(lib_core_module)
            except Exception as e:
                import warnings
                warnings.warn(
                    f"lib.core 部分模块加载失败（某些导入可能缺少依赖）: {e}",
                    ImportWarning,
                    stacklevel=2,
                )

    # 加载 config 模块
    if 'lib.core.config' not in sys.modules:
        config_spec = importlib.util.spec_from_file_location(
            'lib.core.config',
            PROJECT_ROOT / 'lib' / 'core' / 'config.py'
        )
        config_module = importlib.util.module_from_spec(config_spec)
        sys.modules['lib.core.config'] = config_module
        config_spec.loader.exec_module(config_module)
        _module_cache['config'] = config_module
    else:
        config_module = sys.modules['lib.core.config']

    # 加载 db_manager 模块
    if 'lib.core.db_manager' not in sys.modules:
        db_manager_spec = importlib.util.spec_from_file_location(
            'lib.core.db_manager',
            PROJECT_ROOT / 'lib' / 'core' / 'db_manager.py'
        )
        db_manager_module = importlib.util.module_from_spec(db_manager_spec)
        sys.modules['lib.core.db_manager'] = db_manager_module
        db_manager_spec.loader.exec_module(db_manager_module)
        _module_cache['db_manager'] = db_manager_module
    else:
        db_manager_module = sys.modules['lib.core.db_manager']

    return {
        'config': config_module,
        'db_manager': db_manager_module
    }


def load_sqlite_manager():
    """加载 SQLiteManager 模块"""
    setup_module_imports()

    if 'lib.core.sqlite_manager' not in sys.modules:
        sqlite_spec = importlib.util.spec_from_file_location(
            'lib.core.sqlite_manager',
            PROJECT_ROOT / 'lib' / 'core' / 'sqlite_manager.py'
        )
        sqlite_module = importlib.util.module_from_spec(sqlite_spec)
        sys.modules['lib.core.sqlite_manager'] = sqlite_module
        sqlite_spec.loader.exec_module(sqlite_module)
        _module_cache['sqlite_manager'] = sqlite_module

    return sys.modules['lib.core.sqlite_manager']


def load_postgres_manager():
    """加载 PostgreSQLManager 模块"""
    setup_module_imports()

    if 'lib.core.postgres_manager' not in sys.modules:
        postgres_spec = importlib.util.spec_from_file_location(
            'lib.core.postgres_manager',
            PROJECT_ROOT / 'lib' / 'core' / 'postgres_manager.py'
        )
        postgres_module = importlib.util.module_from_spec(postgres_spec)
        sys.modules['lib.core.postgres_manager'] = postgres_module
        postgres_spec.loader.exec_module(postgres_module)
        _module_cache['postgres_manager'] = postgres_module

    return sys.modules['lib.core.postgres_manager']


def get_StorageConfig():
    return setup_module_imports()['config'].StorageConfig


def get_StorageType():
    return setup_module_imports()['config'].StorageType


def get_DatabaseManager():
    return setup_module_imports()['db_manager'].DatabaseManager


def get_SQLiteManager():
    return load_sqlite_manager().SQLiteManager


def get_PostgreSQLManager():
    return load_postgres_manager().PostgreSQLManager


# 直接导出函数供测试使用
__all__ = [
    'get_StorageConfig',
    'get_StorageType',
    'get_DatabaseManager',
    'get_SQLiteManager',
    'get_PostgreSQLManager',
    'setup_module_imports',
]