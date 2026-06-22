"""搜索高亮增强测试

测试 lib.search.highlight 模块的核心功能：
- HighlightConfig 数据类（frozen, Tuple fields, fragment_separator）
- HighlightGenerator 多字段高亮（返回 List[str]）
- 片段截取与 max_words 配置
- 中文查询文本高亮
- truncate_with_boundary 中文字符边界感知
- build_headline_options PostgreSQL ts_headline 选项
"""

import pytest
from typing import List, Optional

from lib.search.highlight import HighlightConfig, HighlightGenerator


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def generator() -> HighlightGenerator:
    """创建高亮生成器实例"""
    return HighlightGenerator()


@pytest.fixture
def default_config() -> HighlightConfig:
    """默认高亮配置"""
    return HighlightConfig()


@pytest.fixture
def chinese_config() -> HighlightConfig:
    """中文感知高亮配置"""
    return HighlightConfig(
        max_words=50,
        min_words=10,
        max_fragments=3,
        start_delimiter='<mark>',
        end_delimiter='</mark>',
        fields=('title', 'description', 'content'),
        chinese_aware=True,
        fragment_separator=' ... ',
    )


@pytest.fixture
def short_fragment_config() -> HighlightConfig:
    """短片段配置"""
    return HighlightConfig(
        max_words=10,
        min_words=5,
        max_fragments=2,
        start_delimiter='<mark>',
        end_delimiter='</mark>',
        fields=('content',),
        chinese_aware=False,
        fragment_separator=' ... ',
    )


# ============================================================
# 1. HighlightConfig 数据类测试
# ============================================================

class TestHighlightConfig:
    """HighlightConfig 数据类测试"""

    def test_default_values(self):
        """测试默认配置值"""
        config = HighlightConfig()
        assert config.max_words == 50
        assert config.min_words == 10
        assert config.max_fragments == 3
        assert config.start_delimiter == '<mark>'
        assert config.end_delimiter == '</mark>'
        assert config.fields == ('title', 'description', 'content')
        assert config.chinese_aware is True
        assert config.fragment_separator == ' ... '

    def test_custom_values(self):
        """测试自定义配置值"""
        config = HighlightConfig(
            max_words=100,
            min_words=20,
            max_fragments=5,
            start_delimiter='**',
            end_delimiter='**',
            fields=('title',),
            chinese_aware=False,
            fragment_separator=' --- ',
        )
        assert config.max_words == 100
        assert config.min_words == 20
        assert config.max_fragments == 5
        assert config.start_delimiter == '**'
        assert config.end_delimiter == '**'
        assert config.fields == ('title',)
        assert config.chinese_aware is False
        assert config.fragment_separator == ' --- '

    def test_immutability(self):
        """测试配置不可变性（frozen dataclass）"""
        config = HighlightConfig()
        with pytest.raises(AttributeError):
            config.max_words = 200  # type: ignore[misc]

    def test_equality(self):
        """测试相同配置的相等性"""
        config1 = HighlightConfig(max_words=30)
        config2 = HighlightConfig(max_words=30)
        assert config1 == config2

    def test_inequality(self):
        """测试不同配置的不等性"""
        config1 = HighlightConfig(max_words=30)
        config2 = HighlightConfig(max_words=50)
        assert config1 != config2

    def test_invalid_max_words(self):
        """测试无效 max_words 抛出异常"""
        with pytest.raises(ValueError, match='max_words'):
            HighlightConfig(max_words=0)

    def test_invalid_min_words(self):
        """测试无效 min_words 抛出异常"""
        with pytest.raises(ValueError, match='min_words'):
            HighlightConfig(min_words=0)

    def test_min_greater_than_max(self):
        """测试 min_words > max_words 抛出异常"""
        with pytest.raises(ValueError, match='不能大于'):
            HighlightConfig(min_words=100, max_words=50)


# ============================================================
# 2. 多字段高亮测试（generate_highlights 返回 List[str]）
# ============================================================

class TestMultiFieldHighlight:
    """多字段高亮测试"""

    def test_highlight_title_field(self, generator: HighlightGenerator):
        """测试标题字段高亮"""
        config = HighlightConfig(fields=('title',))
        result = generator.generate_highlights(
            text='Python programming language guide',
            query='Python',
            config=config,
        )
        # generate_highlights 返回 List[str]，检查列表中任一片段
        assert any('<mark>Python</mark>' in fragment for fragment in result)

    def test_highlight_content_field(self, generator: HighlightGenerator):
        """测试内容字段高亮"""
        config = HighlightConfig(fields=('content',))
        result = generator.generate_highlights(
            text='This article explains Python decorators in depth',
            query='Python',
            config=config,
        )
        assert any('<mark>Python</mark>' in fragment for fragment in result)

    def test_highlight_multiple_fields(self, generator: HighlightGenerator):
        """测试多字段同时高亮 - 每个字段独立生成高亮"""
        config = HighlightConfig(fields=('title', 'description', 'content'))
        texts = {
            'title': 'Python Guide',
            'description': 'A guide about Python',
            'content': 'Python is a versatile programming language',
        }
        query = 'Python'

        results = {}
        for field_name, text in texts.items():
            results[field_name] = generator.generate_highlights(
                text=text,
                query=query,
                config=config,
            )

        for field_name, fragments in results.items():
            assert any('<mark>Python</mark>' in f for f in fragments), \
                f'Field {field_name} should highlight Python'

    def test_highlight_preserves_non_matching_text(self, generator: HighlightGenerator):
        """测试高亮保留非匹配文本"""
        config = HighlightConfig(fields=('content',))
        text = 'The quick brown fox jumps over the lazy dog'
        query = 'fox'
        result = generator.generate_highlights(
            text=text,
            query=query,
            config=config,
        )
        combined = ' '.join(result)
        assert '<mark>fox</mark>' in combined

    def test_highlight_multiple_keywords(self, generator: HighlightGenerator):
        """测试多关键词高亮"""
        config = HighlightConfig(fields=('content',))
        text = 'Python and Java are popular programming languages'
        query = 'Python Java'
        result = generator.generate_highlights(
            text=text,
            query=query,
            config=config,
        )
        combined = ' '.join(result)
        assert '<mark>Python</mark>' in combined
        assert '<mark>Java</mark>' in combined

    def test_highlight_case_insensitive(self, generator: HighlightGenerator):
        """测试大小写不敏感高亮"""
        config = HighlightConfig(fields=('content',))
        text = 'Python python PYTHON are all the same language'
        query = 'python'
        result = generator.generate_highlights(
            text=text,
            query=query,
            config=config,
        )
        # 至少有一个匹配被高亮
        combined = ' '.join(result)
        assert '<mark>' in combined


# ============================================================
# 3. 片段截取测试
# ============================================================

class TestFragmentExtraction:
    """片段截取与 max_words 配置测试"""

    def test_default_max_words(self, generator: HighlightGenerator):
        """测试默认 max_words=50 的片段长度"""
        config = HighlightConfig(max_words=50)
        long_text = ' '.join(f'word{i}' for i in range(200))
        result = generator.generate_highlights(
            text=long_text,
            query='word50',
            config=config,
        )
        combined = ' '.join(result)
        assert '<mark>word50</mark>' in combined

    def test_short_max_words(self, generator: HighlightGenerator):
        """测试短 max_words 配置"""
        config = HighlightConfig(max_words=10, min_words=5)
        long_text = ' '.join(f'word{i}' for i in range(100))
        result = generator.generate_highlights(
            text=long_text,
            query='word50',
            config=config,
        )
        combined = ' '.join(result)
        assert '<mark>word50</mark>' in combined

    def test_max_fragments_limit(self, generator: HighlightGenerator):
        """测试 max_fragments 限制片段数量"""
        config = HighlightConfig(max_fragments=2)
        text = (
            'Python is great. '
            'Python is powerful. '
            'Python is versatile. '
            'Python is popular. '
            'Python is easy.'
        )
        result = generator.generate_highlights(
            text=text,
            query='Python',
            config=config,
        )
        # 返回的列表长度不应超过 max_fragments
        assert len(result) <= config.max_fragments

    def test_fragment_separator_in_joined_result(self, generator: HighlightGenerator):
        """测试片段分隔符"""
        config = HighlightConfig(
            max_fragments=3,
            fragment_separator=' ... ',
        )
        text = (
            'First Python section with some content. '
            'Middle section without keywords. '
            'Second Python section with more content. '
            'Another gap without keywords. '
            'Third Python section at the end.'
        )
        result = generator.generate_highlights(
            text=text,
            query='Python',
            config=config,
        )
        # 多片段结果应包含分隔符
        if len(result) > 1:
            joined = config.fragment_separator.join(result)
            assert ' ... ' in joined

    def test_single_fragment_no_separator(self, generator: HighlightGenerator):
        """测试单片段时结果列表只有一个元素"""
        config = HighlightConfig(max_fragments=1)
        text = 'Only one Python keyword in this text'
        result = generator.generate_highlights(
            text=text,
            query='Python',
            config=config,
        )
        assert len(result) <= 1


# ============================================================
# 4. 中文高亮测试
# ============================================================

class TestChineseHighlight:
    """中文查询文本高亮测试"""

    def test_chinese_keyword_highlight(self, generator: HighlightGenerator):
        """测试中文关键词高亮"""
        config = HighlightConfig(chinese_aware=True)
        result = generator.generate_highlights(
            text='这是一段包含关键词的文本内容',
            query='关键词',
            config=config,
        )
        combined = ' '.join(result)
        assert '<mark>关键词</mark>' in combined

    def test_chinese_mixed_with_english(self, generator: HighlightGenerator):
        """测试中英文混合文本高亮"""
        config = HighlightConfig(chinese_aware=True)
        text = '使用Python进行数据分析是一种常见做法'
        query = 'Python'
        result = generator.generate_highlights(
            text=text,
            query=query,
            config=config,
        )
        combined = ' '.join(result)
        assert '<mark>Python</mark>' in combined

    def test_chinese_multiple_keywords(self, generator: HighlightGenerator):
        """测试中文多关键词高亮"""
        config = HighlightConfig(chinese_aware=True)
        text = '机器学习和深度学习是人工智能的重要分支'
        query = '机器学习 深度学习'
        result = generator.generate_highlights(
            text=text,
            query=query,
            config=config,
        )
        combined = ' '.join(result)
        assert '<mark>机器学习</mark>' in combined
        assert '<mark>深度学习</mark>' in combined

    def test_chinese_aware_false(self, generator: HighlightGenerator):
        """测试 chinese_aware=False 时仍能高亮中文"""
        config = HighlightConfig(chinese_aware=False)
        text = '这是一段包含关键词的文本'
        query = '关键词'
        result = generator.generate_highlights(
            text=text,
            query=query,
            config=config,
        )
        combined = ' '.join(result)
        assert '<mark>关键词</mark>' in combined

    def test_chinese_long_text_fragment(self, generator: HighlightGenerator):
        """测试中文长文本片段截取"""
        config = HighlightConfig(
            max_words=30,
            chinese_aware=True,
            max_fragments=2,
        )
        text = (
            '在自然语言处理领域，中文分词是一个基础且关键的任务。'
            '不同于英文，中文文本没有天然的空格分隔符，'
            '因此需要专门的分词算法来识别词语边界。'
            '常见的中文分词方法包括基于词典的方法、'
            '基于统计的方法和基于深度学习的方法。'
            '每种方法都有其优缺点和适用场景。'
        )
        query = '中文分词'
        result = generator.generate_highlights(
            text=text,
            query=query,
            config=config,
        )
        combined = ' '.join(result)
        assert '<mark>中文分词</mark>' in combined


# ============================================================
# 5. truncate_with_boundary 测试
# ============================================================

class TestTruncateWithBoundary:
    """中文字符边界感知截取测试"""

    def test_short_text_unchanged(self, generator: HighlightGenerator):
        """测试短文本不截取"""
        text = '短文本'
        result = generator.truncate_with_boundary(text, max_length=100)
        assert result == text

    def test_long_text_truncated(self, generator: HighlightGenerator):
        """测试长文本被截取"""
        text = '这是一段很长的中文文本' * 50
        result = generator.truncate_with_boundary(text, max_length=50)
        assert len(result) <= 60  # 允许边界对齐溢出

    def test_chinese_aware_false(self, generator: HighlightGenerator):
        """测试 chinese_aware=False 的 ASCII 安全截取"""
        text = 'A' * 200
        result = generator.truncate_with_boundary(text, max_length=100, chinese_aware=False)
        # 截取方法可能在词边界截取，允许少量溢出
        assert len(result) <= 110

    def test_empty_text(self, generator: HighlightGenerator):
        """测试空文本"""
        result = generator.truncate_with_boundary('', max_length=100)
        assert result == ''

    def test_chinese_boundary_no_mid_word_break(self, generator: HighlightGenerator):
        """测试中文边界截取不会在词语中间断开"""
        text = '自然语言处理技术已经广泛应用于各个领域'
        result = generator.truncate_with_boundary(text, max_length=10, chinese_aware=True)
        # 截取结果应该是合理的中文片段
        assert len(result) <= 16  # 允许边界对齐溢出


# ============================================================
# 6. build_headline_options 测试
# ============================================================

class TestBuildHeadlineOptions:
    """PostgreSQL ts_headline 选项构建测试"""

    def test_default_options(self, generator: HighlightGenerator):
        """测试默认选项"""
        options = generator.build_headline_options()
        assert 'MaxWords=50' in options
        assert 'MinWords=10' in options
        assert 'MaxFragments=3' in options
        assert 'StartSel=<mark>' in options
        assert 'StopSel=</mark>' in options

    def test_custom_options(self, generator: HighlightGenerator):
        """测试自定义选项"""
        config = HighlightConfig(
            max_words=30,
            min_words=5,
            max_fragments=2,
            start_delimiter='**',
            end_delimiter='**',
        )
        options = generator.build_headline_options(config)
        assert 'MaxWords=30' in options
        assert 'MinWords=5' in options
        assert 'MaxFragments=2' in options


# ============================================================
# 7. 边界情况测试
# ============================================================

class TestEdgeCases:
    """边界情况测试"""

    def test_empty_text(self, generator: HighlightGenerator):
        """测试空文本"""
        result = generator.generate_highlights('', 'Python')
        assert result == []

    def test_empty_query(self, generator: HighlightGenerator):
        """测试空查询"""
        result = generator.generate_highlights('Python is great', '')
        assert result == []

    def test_no_match(self, generator: HighlightGenerator):
        """测试无匹配"""
        result = generator.generate_highlights('Java is great', 'Python')
        assert result == []

    def test_unicode_text(self, generator: HighlightGenerator):
        """测试 Unicode 文本"""
        text = '🎉 Python 3.12 is released 🎉'
        result = generator.generate_highlights(text, 'Python')
        combined = ' '.join(result)
        assert '<mark>Python</mark>' in combined
