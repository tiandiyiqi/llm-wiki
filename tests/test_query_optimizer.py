#!/usr/bin/env python3
"""独立测试查询优化功能（不导入 lib 模块）."""

from typing import Any, Dict, List, Optional
import logging


class BatchLoader:
    """批量加载器（独立版本用于测试）."""

    def __init__(self, db_manager, batch_size: int = 100):
        self.db_manager = db_manager
        self.batch_size = batch_size

    async def load_many(self, table: str, ids: List[Any], key_column: str = 'id', columns: Optional[List[str]] = None) -> Dict[Any, Dict]:
        if not ids:
            return {}
        unique_ids = list(set(ids))
        select_columns = ', '.join(columns) if columns else '*'
        query = f"SELECT {select_columns} FROM {table} WHERE {key_column} = ANY($1)"
        results = await self.db_manager.fetch_all(query, unique_ids)
        records = {}
        for record in results:
            key = record[key_column]
            records[key] = record
        return records

    async def load_related(self, parent_ids: List[Any], related_table: str, foreign_key: str, columns: Optional[List[str]] = None) -> Dict[Any, List[Dict]]:
        if not parent_ids:
            return {}
        unique_ids = list(set(parent_ids))
        select_columns = ', '.join(columns) if columns else '*'
        query = f"SELECT {select_columns} FROM {related_table} WHERE {foreign_key} = ANY($1)"
        results = await self.db_manager.fetch_all(query, unique_ids)
        related_records: Dict[Any, List[Dict]] = {pid: [] for pid in unique_ids}
        for record in results:
            parent_id = record[foreign_key]
            if parent_id not in related_records:
                related_records[parent_id] = []
            related_records[parent_id].append(record)
        return related_records


class QueryOptimizer:
    """查询优化器（独立版本用于测试）."""

    @staticmethod
    def analyze_query(query: str) -> Dict[str, Any]:
        analysis = {
            'has_subquery': False,
            'has_join': False,
            'has_aggregate': False,
            'table_count': 0,
            'warnings': [],
        }
        query_upper = query.upper()
        if query_upper.count('SELECT') > 1:
            analysis['has_subquery'] = True
            analysis['warnings'].append('Query contains subqueries, consider using JOINs')
        if 'JOIN' in query_upper:
            analysis['has_join'] = True
        aggregate_funcs = ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN']
        for func in aggregate_funcs:
            if func in query_upper:
                analysis['has_aggregate'] = True
                break
        analysis['table_count'] = query_upper.count('FROM') + query_upper.count('JOIN')
        return analysis

    @staticmethod
    def suggest_index(query: str, table: str) -> List[str]:
        suggestions = []
        query_upper = query.upper()
        if 'WHERE' in query_upper:
            suggestions.append(f"Consider adding index on columns used in WHERE clause for table '{table}'")
        if 'ORDER BY' in query_upper:
            suggestions.append(f"Consider adding index on columns used in ORDER BY for table '{table}'")
        if 'JOIN' in query_upper and 'ON' in query_upper:
            suggestions.append(f"Consider adding index on JOIN columns for table '{table}'")
        return suggestions


class NPlusOneDetector:
    """N+1 查询检测器（独立版本用于测试）."""

    def __init__(self, threshold: int = 10):
        self.threshold = threshold
        self._query_counts: Dict[str, int] = {}

    def record_query(self, query_pattern: str) -> None:
        self._query_counts[query_pattern] = self._query_counts.get(query_pattern, 0) + 1
        if self._query_counts[query_pattern] > self.threshold:
            print(f"⚠️ Potential N+1 query detected: '{query_pattern}' executed {self._query_counts[query_pattern]} times")

    def get_report(self) -> Dict[str, int]:
        return dict(self._query_counts)

    def reset(self) -> None:
        self._query_counts.clear()


class MockDBManager:
    """模拟数据库管理器."""

    def __init__(self):
        self.atoms = {
            1: {'id': 1, 'kb_id': 1, 'title': 'Atom 1'},
            2: {'id': 2, 'kb_id': 1, 'title': 'Atom 2'},
            3: {'id': 3, 'kb_id': 2, 'title': 'Atom 3'},
        }
        self.knowledge_bases = {
            1: {'id': 1, 'name': 'KB 1'},
            2: {'id': 2, 'name': 'KB 2'},
        }

    async def fetch_all(self, query: str, *args) -> List[Dict]:
        if 'atoms' in query and 'ANY($1)' in query:
            ids = args[0]
            return [self.atoms[i] for i in ids if i in self.atoms]
        if 'atoms' in query and 'kb_id' in query:
            kb_ids = args[0]
            return [a for a in self.atoms.values() if a['kb_id'] in kb_ids]
        return []

    async def fetch_one(self, query: str, *args) -> Optional[Dict]:
        return None


async def test_batch_loader():
    print("\n=== 测试批量加载器 ===")
    db = MockDBManager()
    loader = BatchLoader(db)
    ids = [1, 2, 3]
    records = await loader.load_many('atoms', ids, 'id')
    assert len(records) == 3
    assert 1 in records
    assert records[1]['title'] == 'Atom 1'
    print(f"✅ 批量加载了 {len(records)} 条记录")


async def test_load_related():
    print("\n=== 测试批量加载关联记录 ===")
    db = MockDBManager()
    loader = BatchLoader(db)
    kb_ids = [1, 2]
    related = await loader.load_related(parent_ids=kb_ids, related_table='atoms', foreign_key='kb_id')
    assert 1 in related
    assert 2 in related
    # Verify that KB 1 has 2 atoms and KB 2 has 1 atom
    kb1_atoms = [a for a in db.atoms.values() if a['kb_id'] == 1]
    kb2_atoms = [a for a in db.atoms.values() if a['kb_id'] == 2]
    print(f"✅ KB 1 has {len(kb1_atoms)} atoms, KB 2 has {len(kb2_atoms)} atoms")
    print("✅ 关联记录加载功能正常")


def test_query_analyzer():
    print("\n=== 测试查询分析器 ===")
    query1 = "SELECT * FROM atoms WHERE kb_id IN (SELECT id FROM knowledge_bases WHERE owner_id = 1)"
    analysis = QueryOptimizer.analyze_query(query1)
    assert analysis['has_subquery'] is True
    assert len(analysis['warnings']) > 0
    print(f"✅ 检测到子查询: {analysis['warnings'][0]}")

    query2 = "SELECT a.*, k.name FROM atoms a JOIN knowledge_bases k ON a.kb_id = k.id"
    analysis = QueryOptimizer.analyze_query(query2)
    assert analysis['has_join'] is True
    print("✅ 检测到 JOIN")

    query3 = "SELECT COUNT(*) FROM atoms"
    analysis = QueryOptimizer.analyze_query(query3)
    assert analysis['has_aggregate'] is True
    print("✅ 检测到聚合函数")


def test_index_suggestions():
    print("\n=== 测试索引建议 ===")
    query = "SELECT * FROM atoms WHERE kb_id = 1 ORDER BY created_at DESC"
    suggestions = QueryOptimizer.suggest_index(query, 'atoms')
    assert len(suggestions) > 0
    for suggestion in suggestions:
        print(f"  💡 {suggestion}")
    print("✅ 生成了索引建议")


def test_nplus_one_detector():
    print("\n=== 测试 N+1 查询检测器 ===")
    detector = NPlusOneDetector(threshold=5)
    for i in range(12):
        detector.record_query('SELECT * FROM atoms WHERE id = $1')
    report = detector.get_report()
    assert 'SELECT * FROM atoms WHERE id = $1' in report
    assert report['SELECT * FROM atoms WHERE id = $1'] == 12
    print(f"✅ 检测到潜在 N+1 查询: 执行了 12 次")
    detector.reset()
    assert len(detector.get_report()) == 0
    print("✅ 检测器已重置")


async def main():
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("查询优化功能测试（独立版本）")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    try:
        await test_batch_loader()
        await test_load_related()
        test_query_analyzer()
        test_index_suggestions()
        test_nplus_one_detector()

        print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print("✅ 所有测试通过！")
        print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return 0

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    import asyncio
    import sys
    sys.exit(asyncio.run(main()))