"""OCR 任务表 Schema 迁移测试

验证 ocr_tasks 表的 schema 定义：
- ocr_task_status 枚举类型存在且包含所有值
- ocr_tasks 表字段完整
- 外键约束正确
- 索引存在
- 触发器存在
"""

import re
import unittest
from pathlib import Path


SCHEMA_PATH = Path(__file__).parent.parent.parent / 'lib' / 'db' / 'schema.sql'


class TestOCRSchemaMigration(unittest.TestCase):
    """ocr_tasks 表 schema 迁移测试"""

    @classmethod
    def setUpClass(cls):
        """加载 schema 文件"""
        cls.schema_content = SCHEMA_PATH.read_text(encoding='utf-8')

    def test_ocr_task_status_enum_exists(self):
        """验证 ocr_task_status 枚举类型存在"""
        self.assertIn(
            'ocr_task_status',
            self.schema_content,
            'ocr_task_status 枚举类型未定义',
        )

    def test_ocr_task_status_enum_values(self):
        """验证 ocr_task_status 枚举包含所有预期值"""
        match = re.search(
            r'CREATE TYPE ocr_task_status AS ENUM\s*\((.*?)\);',
            self.schema_content,
            re.DOTALL,
        )
        self.assertIsNotNone(match, 'ocr_task_status 枚举定义未找到')
        enum_body = match.group(1)

        expected_values = ['pending', 'processing', 'completed', 'failed', 'dead_letter']
        for value in expected_values:
            self.assertIn(
                value,
                enum_body,
                f'枚举值 {value} 未在 ocr_task_status 中定义',
            )

    def test_ocr_tasks_table_exists(self):
        """验证 ocr_tasks 表存在"""
        self.assertIn(
            'CREATE TABLE ocr_tasks',
            self.schema_content,
            'ocr_tasks 表未定义',
        )

    def _extract_ocr_tasks_block(self) -> str:
        """提取 ocr_tasks 表定义块"""
        match = re.search(
            r'CREATE TABLE ocr_tasks\s*\((.*?)\);',
            self.schema_content,
            re.DOTALL,
        )
        self.assertIsNotNone(match, 'ocr_tasks 表定义未找到')
        return match.group(1)

    def test_asset_id_column_exists(self):
        """验证 asset_id 字段存在"""
        block = self._extract_ocr_tasks_block()
        self.assertIn('asset_id', block, 'asset_id 字段未在 ocr_tasks 表中定义')

    def test_asset_id_foreign_key(self):
        """验证 asset_id 外键指向 atom_assets"""
        block = self._extract_ocr_tasks_block()
        self.assertRegex(
            block,
            r'asset_id\s+INTEGER\s+NOT\s+NULL\s+REFERENCES\s+atom_assets\s*\(\s*id\s*\)',
            'asset_id 应为外键 REFERENCES atom_assets(id)',
        )

    def test_asset_id_cascade_delete(self):
        """验证 asset_id 外键 ON DELETE CASCADE"""
        block = self._extract_ocr_tasks_block()
        self.assertRegex(
            block,
            r'asset_id\s+.*ON\s+DELETE\s+CASCADE',
            'asset_id 外键应为 ON DELETE CASCADE',
        )

    def test_status_column_exists(self):
        """验证 status 字段存在且类型正确"""
        block = self._extract_ocr_tasks_block()
        self.assertIn('status', block, 'status 字段未定义')
        self.assertRegex(
            block,
            r'status\s+ocr_task_status',
            'status 字段类型应为 ocr_task_status',
        )

    def test_status_default_pending(self):
        """验证 status 默认值为 'pending'"""
        block = self._extract_ocr_tasks_block()
        self.assertRegex(
            block,
            r"status\s+ocr_task_status\s+DEFAULT\s+'pending'",
            "status 默认值应为 'pending'",
        )

    def test_language_column_exists(self):
        """验证 language 字段存在"""
        block = self._extract_ocr_tasks_block()
        self.assertIn('language', block, 'language 字段未定义')

    def test_language_default(self):
        """验证 language 默认值为 'chi_sim+eng'"""
        block = self._extract_ocr_tasks_block()
        self.assertIn('chi_sim+eng', block, "language 默认值应为 'chi_sim+eng'")

    def test_result_columns_exist(self):
        """验证 result_text 和 result_json 字段存在"""
        block = self._extract_ocr_tasks_block()
        self.assertIn('result_text', block, 'result_text 字段未定义')
        self.assertIn('result_json', block, 'result_json 字段未定义')

    def test_error_message_column_exists(self):
        """验证 error_message 字段存在"""
        block = self._extract_ocr_tasks_block()
        self.assertIn('error_message', block, 'error_message 字段未定义')

    def test_retry_columns_exist(self):
        """验证 retry_count 和 max_retries 字段存在"""
        block = self._extract_ocr_tasks_block()
        self.assertIn('retry_count', block, 'retry_count 字段未定义')
        self.assertIn('max_retries', block, 'max_retries 字段未定义')

    def test_max_retries_default(self):
        """验证 max_retries 默认值为 3"""
        block = self._extract_ocr_tasks_block()
        self.assertRegex(
            block,
            r'max_retries\s+INTEGER\s+DEFAULT\s+3',
            'max_retries 默认值应为 3',
        )

    def test_timestamp_columns_exist(self):
        """验证时间戳字段存在"""
        block = self._extract_ocr_tasks_block()
        self.assertIn('processing_started_at', block, 'processing_started_at 字段未定义')
        self.assertIn('processing_completed_at', block, 'processing_completed_at 字段未定义')
        self.assertIn('created_at', block, 'created_at 字段未定义')
        self.assertIn('updated_at', block, 'updated_at 字段未定义')

    def test_created_by_foreign_key(self):
        """验证 created_by 外键指向 users"""
        block = self._extract_ocr_tasks_block()
        self.assertRegex(
            block,
            r'created_by\s+VARCHAR\(64\)\s+REFERENCES\s+users\s*\(\s*id\s*\)',
            'created_by 应为外键 REFERENCES users(id)',
        )

    def test_ocr_tasks_indexes(self):
        """验证 ocr_tasks 索引存在"""
        self.assertIn(
            'idx_ocr_tasks_asset_id',
            self.schema_content,
            'asset_id 索引未创建',
        )
        self.assertIn(
            'idx_ocr_tasks_status',
            self.schema_content,
            'status 索引未创建',
        )
        self.assertIn(
            'idx_ocr_tasks_created_at',
            self.schema_content,
            'created_at 索引未创建',
        )

    def test_ocr_tasks_trigger(self):
        """验证 ocr_tasks 的 updated_at 触发器存在"""
        self.assertIn(
            'ocr_tasks_updated_at',
            self.schema_content,
            'ocr_tasks 的 updated_at 触发器未定义',
        )

    def test_ocr_tasks_comments(self):
        """验证 ocr_tasks 表和字段注释存在"""
        self.assertIn(
            "COMMENT ON TABLE ocr_tasks",
            self.schema_content,
            'ocr_tasks 表注释未定义',
        )
        self.assertIn(
            "COMMENT ON COLUMN ocr_tasks.status",
            self.schema_content,
            'ocr_tasks.status 字段注释未定义',
        )


if __name__ == '__main__':
    unittest.main()
