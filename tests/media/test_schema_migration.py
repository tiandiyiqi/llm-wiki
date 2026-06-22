"""Schema 迁移测试

验证 atom_assets 表的变体字段迁移：
- variant_type 字段存在且类型正确
- variant_of_id 外键正确
- 默认值为 'original'
- thumbnail 字段已移除
"""

import re
import unittest
from pathlib import Path


SCHEMA_PATH = Path(__file__).parent.parent.parent / 'lib' / 'db' / 'schema.sql'


class TestSchemaMigration(unittest.TestCase):
    """atom_assets 表 schema 迁移测试"""

    @classmethod
    def setUpClass(cls):
        """加载 schema 文件"""
        cls.schema_content = SCHEMA_PATH.read_text(encoding='utf-8')

    def _extract_atom_assets_block(self) -> str:
        """提取 atom_assets 表定义块"""
        match = re.search(
            r'CREATE TABLE atom_assets\s*\((.*?)\);',
            self.schema_content,
            re.DOTALL,
        )
        self.assertIsNotNone(match, 'atom_assets 表定义未找到')
        return match.group(1)

    def test_variant_type_enum_exists(self):
        """验证 asset_variant_type 枚举类型存在"""
        self.assertIn(
            'asset_variant_type',
            self.schema_content,
            'asset_variant_type 枚举类型未定义',
        )

    def test_variant_type_enum_values(self):
        """验证 asset_variant_type 枚举包含所有预期值"""
        match = re.search(
            r'CREATE TYPE asset_variant_type AS ENUM\s*\((.*?)\);',
            self.schema_content,
            re.DOTALL,
        )
        self.assertIsNotNone(match, 'asset_variant_type 枚举定义未找到')
        enum_body = match.group(1)

        expected_values = ['original', 'thumbnail', 'medium', 'large']
        for value in expected_values:
            self.assertIn(
                value,
                enum_body,
                f'枚举值 {value} 未在 asset_variant_type 中定义',
            )

    def test_variant_type_column_exists(self):
        """验证 variant_type 字段存在于 atom_assets 表"""
        block = self._extract_atom_assets_block()
        self.assertIn(
            'variant_type',
            block,
            'variant_type 字段未在 atom_assets 表中定义',
        )

    def test_variant_type_column_type(self):
        """验证 variant_type 字段类型为 asset_variant_type"""
        block = self._extract_atom_assets_block()
        self.assertRegex(
            block,
            r'variant_type\s+asset_variant_type',
            'variant_type 字段类型应为 asset_variant_type',
        )

    def test_variant_type_default_value(self):
        """验证 variant_type 默认值为 'original'"""
        block = self._extract_atom_assets_block()
        self.assertRegex(
            block,
            r"variant_type\s+asset_variant_type\s+DEFAULT\s+'original'",
            "variant_type 默认值应为 'original'",
        )

    def test_variant_of_id_column_exists(self):
        """验证 variant_of_id 字段存在于 atom_assets 表"""
        block = self._extract_atom_assets_block()
        self.assertIn(
            'variant_of_id',
            block,
            'variant_of_id 字段未在 atom_assets 表中定义',
        )

    def test_variant_of_id_self_reference(self):
        """验证 variant_of_id 是自引用外键"""
        block = self._extract_atom_assets_block()
        self.assertRegex(
            block,
            r'variant_of_id\s+INTEGER\s+REFERENCES\s+atom_assets\s*\(\s*id\s*\)',
            'variant_of_id 应为自引用外键 REFERENCES atom_assets(id)',
        )

    def test_variant_of_id_on_delete_set_null(self):
        """验证 variant_of_id 外键 ON DELETE 策略为 SET NULL"""
        block = self._extract_atom_assets_block()
        self.assertRegex(
            block,
            r'variant_of_id\s+.*ON\s+DELETE\s+SET\s+NULL',
            'variant_of_id 外键应为 ON DELETE SET NULL',
        )

    def test_thumbnail_column_removed(self):
        """验证 thumbnail BYTEA 字段已移除"""
        block = self._extract_atom_assets_block()
        self.assertNotRegex(
            block,
            r'thumbnail\s+BYTEA',
            'thumbnail BYTEA 字段应已移除（改为独立变体记录）',
        )

    def test_variant_consistency_constraint(self):
        """验证变体一致性约束存在"""
        block = self._extract_atom_assets_block()
        self.assertIn(
            'chk_variant_consistency',
            block,
            '变体一致性约束 chk_variant_consistency 未定义',
        )

    def test_variant_index_exists(self):
        """验证变体查询索引存在"""
        self.assertIn(
            'idx_atom_assets_variant_of_id',
            self.schema_content,
            '变体外键索引 idx_atom_assets_variant_of_id 未创建',
        )
        self.assertIn(
            'idx_atom_assets_variant_type',
            self.schema_content,
            '变体类型索引 idx_atom_assets_variant_type 未创建',
        )

    def test_variant_type_comment_exists(self):
        """验证 variant_type 和 variant_of_id 字段注释存在"""
        self.assertIn(
            "COMMENT ON COLUMN atom_assets.variant_type",
            self.schema_content,
            'variant_type 字段注释未定义',
        )
        self.assertIn(
            "COMMENT ON COLUMN atom_assets.variant_of_id",
            self.schema_content,
            'variant_of_id 字段注释未定义',
        )


if __name__ == '__main__':
    unittest.main()
