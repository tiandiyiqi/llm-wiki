"""预览表 Schema 迁移测试

验证 previews 表的 schema 定义：
- preview_format 枚举类型存在且包含所有值
- previews 表字段完整
- 外键约束正确
- 唯一约束存在
- 索引存在
"""

import re
import unittest
from pathlib import Path


SCHEMA_PATH = Path(__file__).parent.parent.parent / 'lib' / 'db' / 'schema.sql'


class TestPreviewSchemaMigration(unittest.TestCase):
    """previews 表 schema 迁移测试"""

    @classmethod
    def setUpClass(cls):
        """加载 schema 文件"""
        cls.schema_content = SCHEMA_PATH.read_text(encoding='utf-8')

    def test_preview_format_enum_exists(self):
        """验证 preview_format 枚举类型存在"""
        self.assertIn(
            'preview_format',
            self.schema_content,
            'preview_format 枚举类型未定义',
        )

    def test_preview_format_enum_values(self):
        """验证 preview_format 枚举包含所有预期值"""
        match = re.search(
            r'CREATE TYPE preview_format AS ENUM\s*\((.*?)\);',
            self.schema_content,
            re.DOTALL,
        )
        self.assertIsNotNone(match, 'preview_format 枚举定义未找到')
        enum_body = match.group(1)

        expected_values = ['pdf', 'word', 'excel', 'ppt', 'image', 'markdown', 'text', 'other']
        for value in expected_values:
            self.assertIn(
                value,
                enum_body,
                f'枚举值 {value} 未在 preview_format 中定义',
            )

    def test_previews_table_exists(self):
        """验证 previews 表存在"""
        self.assertIn(
            'CREATE TABLE previews',
            self.schema_content,
            'previews 表未定义',
        )

    def _extract_previews_block(self) -> str:
        """提取 previews 表定义块"""
        match = re.search(
            r'CREATE TABLE previews\s*\((.*?)\);',
            self.schema_content,
            re.DOTALL,
        )
        self.assertIsNotNone(match, 'previews 表定义未找到')
        return match.group(1)

    def test_atom_id_column_exists(self):
        """验证 atom_id 字段存在"""
        block = self._extract_previews_block()
        self.assertIn('atom_id', block, 'atom_id 字段未定义')

    def test_atom_id_foreign_key(self):
        """验证 atom_id 外键指向 atoms"""
        block = self._extract_previews_block()
        self.assertRegex(
            block,
            r'atom_id\s+INTEGER\s+NOT\s+NULL\s+REFERENCES\s+atoms\s*\(\s*id\s*\)',
            'atom_id 应为外键 REFERENCES atoms(id)',
        )

    def test_atom_id_cascade_delete(self):
        """验证 atom_id 外键 ON DELETE CASCADE"""
        block = self._extract_previews_block()
        self.assertRegex(
            block,
            r'atom_id\s+.*ON\s+DELETE\s+CASCADE',
            'atom_id 外键应为 ON DELETE CASCADE',
        )

    def test_format_column_exists(self):
        """验证 format 字段存在且类型正确"""
        block = self._extract_previews_block()
        self.assertIn('format', block, 'format 字段未定义')
        self.assertRegex(
            block,
            r'format\s+preview_format',
            'format 字段类型应为 preview_format',
        )

    def test_format_not_null(self):
        """验证 format 字段 NOT NULL"""
        block = self._extract_previews_block()
        self.assertRegex(
            block,
            r'format\s+preview_format\s+NOT\s+NULL',
            'format 字段应为 NOT NULL',
        )

    def test_source_mime_type_column(self):
        """验证 source_mime_type 字段存在"""
        block = self._extract_previews_block()
        self.assertIn('source_mime_type', block, 'source_mime_type 字段未定义')

    def test_cache_path_column(self):
        """验证 cache_path 字段存在"""
        block = self._extract_previews_block()
        self.assertIn('cache_path', block, 'cache_path 字段未定义')

    def test_cache_expires_at_column(self):
        """验证 cache_expires_at 字段存在"""
        block = self._extract_previews_block()
        self.assertIn('cache_expires_at', block, 'cache_expires_at 字段未定义')

    def test_file_size_column(self):
        """验证 file_size 字段存在"""
        block = self._extract_previews_block()
        self.assertIn('file_size', block, 'file_size 字段未定义')

    def test_created_at_column(self):
        """验证 created_at 字段存在"""
        block = self._extract_previews_block()
        self.assertIn('created_at', block, 'created_at 字段未定义')

    def test_unique_constraint(self):
        """验证 (atom_id, format) 唯一约束"""
        block = self._extract_previews_block()
        self.assertIn(
            'UNIQUE(atom_id, format)',
            block,
            '(atom_id, format) 唯一约束未定义',
        )

    def test_previews_indexes(self):
        """验证 previews 索引存在"""
        self.assertIn(
            'idx_previews_atom_id',
            self.schema_content,
            'atom_id 索引未创建',
        )
        self.assertIn(
            'idx_previews_format',
            self.schema_content,
            'format 索引未创建',
        )
        self.assertIn(
            'idx_previews_expires_at',
            self.schema_content,
            'cache_expires_at 索引未创建',
        )

    def test_previews_comments(self):
        """验证 previews 表和字段注释存在"""
        self.assertIn(
            "COMMENT ON TABLE previews",
            self.schema_content,
            'previews 表注释未定义',
        )
        self.assertIn(
            "COMMENT ON COLUMN previews.format",
            self.schema_content,
            'previews.format 字段注释未定义',
        )
        self.assertIn(
            "COMMENT ON COLUMN previews.cache_expires_at",
            self.schema_content,
            'previews.cache_expires_at 字段注释未定义',
        )


if __name__ == '__main__':
    unittest.main()
