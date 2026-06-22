"""Search tests conftest - handles lib package import workaround.

lib/__init__.py imports sentence_transformers which may not be available
in test environments. This conftest pre-registers an empty lib module
so that lib.search and lib.db submodules can be imported normally.
"""

import sys
import types
from pathlib import Path


def _ensure_lib_package_registered() -> None:
    """Pre-register empty lib package to avoid triggering lib/__init__.py imports."""
    if 'lib' not in sys.modules:
        lib_module = types.ModuleType('lib')
        lib_module.__path__ = [str(Path(__file__).parent.parent.parent / 'lib')]
        lib_module.__package__ = 'lib'
        sys.modules['lib'] = lib_module


_ensure_lib_package_registered()
