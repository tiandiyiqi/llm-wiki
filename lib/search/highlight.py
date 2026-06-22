"""搜索高亮增强模块

提供独立于数据库的高亮生成器，支持多字段高亮、自定义片段长度、
高亮标签配置和中文字符边界感知截取。

使用示例:
    from lib.search.highlight import HighlightConfig, HighlightGenerator

    config = HighlightConfig(chinese_aware=True)
    generator = HighlightGenerator()
    result = generator.generate_highlights("搜索文本内容", "搜索", config)
"""

import re
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Tuple


# CJK 统一汉字范围
_CJK_RANGE = re.compile(r'[一-鿿㐀-䶿豈-﫿]')
# 中文字符边界：前一个字符是中文且后一个不是，或反之
_CJK_BOUNDARY = re.compile(
    r'(?<=[一-鿿㐀-䶿豈-﫿])'
    r'(?=[^一-鿿㐀-䶿豈-﫿])'
    r'|'
    r'(?<=[^一-鿿㐀-䶿豈-﫿])'
    r'(?=[一-鿿㐀-䶿豈-﫿])'
)
# 中文标点
_CJK_PUNCTUATION = re.compile(r'[，。、；：！？""''（）【】《》…—]')


@dataclass(frozen=True)
class HighlightConfig:
    """高亮配置数据类

    Attributes:
        fields: 需要高亮的字段列表（如 ['title', 'description', 'content']）
        max_words: 片段最大词数
        min_words: 片段最小词数
        max_fragments: 最大片段数
        start_delimiter: 高亮开始标签
        end_delimiter: 高亮结束标签
        chinese_aware: 是否启用中文字符边界感知截取
        fragment_separator: 多片段之间的分隔符
        max_char_length: 中文字符模式下最大字符长度（优先于 max_words）
    """

    fields: Tuple[str, ...] = ('title', 'description', 'content')
    max_words: int = 50
    min_words: int = 10
    max_fragments: int = 3
    start_delimiter: str = '<mark>'
    end_delimiter: str = '</mark>'
    chinese_aware: bool = True
    fragment_separator: str = ' ... '
    max_char_length: int = 150

    def __post_init__(self) -> None:
        """校验配置参数"""
        if self.max_words < 1:
            raise ValueError(f'max_words 必须 >= 1，当前值: {self.max_words}')
        if self.min_words < 1:
            raise ValueError(f'min_words 必须 >= 1，当前值: {self.min_words}')
        if self.min_words > self.max_words:
            raise ValueError(
                f'min_words ({self.min_words}) 不能大于 max_words ({self.max_words})'
            )
        if self.max_fragments < 1:
            raise ValueError(f'max_fragments 必须 >= 1，当前值: {self.max_fragments}')
        if not self.start_delimiter:
            raise ValueError('start_delimiter 不能为空')
        if not self.end_delimiter:
            raise ValueError('end_delimiter 不能为空')
        if self.max_char_length < 1:
            raise ValueError(f'max_char_length 必须 >= 1，当前值: {self.max_char_length}')


class HighlightGenerator:
    """独立的高亮生成器

    不依赖数据库，可对任意文本生成高亮片段。
    支持中文字符边界感知截取，避免在中文词语中间截断。
    """

    # 允许的 PostgreSQL ts_headline 高亮标签
    _ALLOWED_DELIMITERS: FrozenSet[str] = frozenset({
        '<mark>', '<strong>', '<b>', '<em>', '<span>', '**', '__',
    })

    def generate_highlights(
        self,
        text: str,
        query: str,
        config: Optional[HighlightConfig] = None,
    ) -> List[str]:
        """对单文本生成高亮片段

        在文本中查找查询词出现的位置，围绕匹配位置截取片段，
        并用配置的标签包裹匹配词。

        Args:
            text: 待高亮的原始文本
            query: 查询字符串
            config: 高亮配置，为空则使用默认配置

        Returns:
            高亮片段列表，每个片段已包含高亮标签
        """
        if not text or not query:
            return []

        cfg = config or HighlightConfig()
        normalized_query = self._normalize_query(query)
        if not normalized_query:
            return []

        match_positions = self._find_match_positions(text, normalized_query)
        if not match_positions:
            return []

        fragments = self._extract_fragments(text, match_positions, cfg)
        highlighted = self._apply_delimiters(fragments, normalized_query, cfg)

        return highlighted[:cfg.max_fragments]

    def truncate_with_boundary(
        self,
        text: str,
        max_length: int = 150,
        chinese_aware: bool = True,
    ) -> str:
        """中文字符边界感知截取

        在指定长度范围内截取文本，优先在句子或词语边界处截断，
        避免在中文词语中间截断。

        Args:
            text: 原始文本
            max_length: 最大字符长度
            chinese_aware: 是否启用中文边界感知

        Returns:
            截取后的文本
        """
        if not text:
            return ''
        if len(text) <= max_length:
            return text

        if not chinese_aware or not self._contains_cjk(text):
            return self._truncate_ascii_safe(text, max_length)

        return self._truncate_cjk_safe(text, max_length)

    def build_headline_options(self, config: Optional[HighlightConfig] = None) -> str:
        """构建 PostgreSQL ts_headline 选项字符串

        根据 HighlightConfig 生成符合 PostgreSQL ts_headline 函数
        的选项字符串。

        Args:
            config: 高亮配置，为空则使用默认配置

        Returns:
            ts_headline 选项字符串，如
            'MaxWords=50, MinWords=10, MaxFragments=3,
             StartSel=<mark>, StopSel=</mark>'
        """
        cfg = config or HighlightConfig()
        start_sel = self._sanitize_delimiter(cfg.start_delimiter)
        stop_sel = self._sanitize_delimiter(cfg.end_delimiter)

        parts = [
            f'MaxWords={cfg.max_words}',
            f'MinWords={cfg.min_words}',
            f'MaxFragments={cfg.max_fragments}',
            f'StartSel={start_sel}',
            f'StopSel={stop_sel}',
        ]

        return ', '.join(parts)

    # ========== 内部方法 ==========

    def _normalize_query(self, query: str) -> str:
        """规范化查询字符串

        去除特殊字符，保留中文、英文和数字，
        将多个空白字符合并为单个空格。

        Args:
            query: 原始查询

        Returns:
            规范化后的查询字符串
        """
        cleaned = re.sub(r'[^\w一-鿿㐀-䶿\s]', ' ', query)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    def _find_match_positions(
        self, text: str, query: str,
    ) -> List[Tuple[int, int]]:
        """查找查询词在文本中的所有匹配位置

        对查询中的每个词独立搜索，支持中文和英文。

        Args:
            text: 目标文本
            query: 规范化后的查询

        Returns:
            匹配位置列表 [(start, end), ...]
        """
        positions: List[Tuple[int, int]] = []
        query_terms = query.split()

        for term in query_terms:
            if not term:
                continue
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            for match in pattern.finditer(text):
                positions.append((match.start(), match.end()))

        # 按起始位置排序并合并重叠区间
        return self._merge_overlaps(positions)

    def _merge_overlaps(
        self, positions: List[Tuple[int, int]],
    ) -> List[Tuple[int, int]]:
        """合并重叠的匹配区间

        Args:
            positions: 原始匹配位置列表

        Returns:
            合并后的不重叠区间列表
        """
        if not positions:
            return []

        sorted_pos = sorted(positions, key=lambda p: (p[0], p[1]))
        merged: List[Tuple[int, int]] = [sorted_pos[0]]

        for start, end in sorted_pos[1:]:
            prev_start, prev_end = merged[-1]
            if start <= prev_end:
                merged[-1] = (prev_start, max(prev_end, end))
            else:
                merged.append((start, end))

        return merged

    def _deduplicate_fragments(
        self, fragments: List[str], config: HighlightConfig,
    ) -> List[str]:
        """对重叠或高度相似的片段进行去重合并

        当两个片段有大量重叠内容时，合并为一个更长的片段。

        Args:
            fragments: 原始片段列表
            config: 高亮配置

        Returns:
            去重后的片段列表
        """
        if len(fragments) <= 1:
            return fragments

        deduped: List[str] = [fragments[0]]

        for frag in fragments[1:]:
            last = deduped[-1]
            overlap = self._compute_overlap_ratio(last, frag)
            if overlap > 0.5:
                merged = self._merge_fragment_texts(last, frag)
                deduped[-1] = merged
            else:
                deduped.append(frag)

        return deduped[:config.max_fragments]

    def _compute_overlap_ratio(self, text_a: str, text_b: str) -> float:
        """计算两个文本的重叠比例

        基于最长公共子串占较短文本的比例。

        Args:
            text_a: 第一个文本
            text_b: 第二个文本

        Returns:
            重叠比例 (0.0 - 1.0)
        """
        if not text_a or not text_b:
            return 0.0

        shorter = text_a if len(text_a) <= len(text_b) else text_b
        longer = text_b if len(text_a) <= len(text_b) else text_a

        max_overlap = 0
        for i in range(len(longer) - len(shorter) + 1):
            match_len = 0
            for j in range(len(shorter)):
                if longer[i + j] == shorter[j]:
                    match_len += 1
                elif match_len > max_overlap:
                    max_overlap = match_len
                    match_len = 0
                else:
                    match_len = 0
            if match_len > max_overlap:
                max_overlap = match_len

        return max_overlap / len(shorter) if shorter else 0.0

    def _merge_fragment_texts(self, text_a: str, text_b: str) -> str:
        """合并两个有重叠的片段文本

        找到重叠部分后拼接为单一文本。

        Args:
            text_a: 第一个片段
            text_b: 第二个片段

        Returns:
            合并后的文本
        """
        # 寻找 text_a 的后缀与 text_b 的前缀的最大重叠
        max_overlap_len = 0
        max_check = min(len(text_a), len(text_b))

        for overlap_len in range(1, max_check + 1):
            if text_a[-overlap_len:] == text_b[:overlap_len]:
                max_overlap_len = overlap_len

        if max_overlap_len > 0:
            return text_a + text_b[max_overlap_len:]

        return text_a + ' ' + text_b

    def _extract_fragments(
        self,
        text: str,
        positions: List[Tuple[int, int]],
        config: HighlightConfig,
    ) -> List[str]:
        """围绕匹配位置提取文本片段

        根据配置决定使用词数模式或中文字符模式截取。
        提取后对重叠片段进行合并去重。

        Args:
            text: 原始文本
            positions: 匹配位置列表
            config: 高亮配置

        Returns:
            文本片段列表
        """
        if config.chinese_aware and self._contains_cjk(text):
            raw_fragments = self._extract_fragments_cjk(text, positions, config)
        else:
            raw_fragments = self._extract_fragments_word(text, positions, config)

        return self._deduplicate_fragments(raw_fragments, config)

    def _extract_fragments_word(
        self,
        text: str,
        positions: List[Tuple[int, int]],
        config: HighlightConfig,
    ) -> List[str]:
        """按词数模式提取片段

        以空格为词边界，围绕匹配位置提取指定词数的片段。

        Args:
            text: 原始文本
            positions: 匹配位置列表
            config: 高亮配置

        Returns:
            文本片段列表
        """
        fragments: List[str] = []
        words = text.split()
        word_boundaries = self._compute_word_boundaries(text, words)

        for match_start, match_end in positions[:config.max_fragments]:
            frag = self._extract_single_word_fragment(
                text, words, word_boundaries, match_start, match_end, config,
            )
            if frag:
                fragments.append(frag)

        return fragments

    def _compute_word_boundaries(
        self, text: str, words: List[str],
    ) -> List[Tuple[int, int]]:
        """计算每个词在原文中的字符位置

        Args:
            text: 原始文本
            words: 分词结果

        Returns:
            每个词的 (start, end) 位置列表
        """
        boundaries: List[Tuple[int, int]] = []
        pos = 0
        for word in words:
            idx = text.find(word, pos)
            if idx == -1:
                boundaries.append((pos, pos + len(word)))
                pos += len(word) + 1
            else:
                boundaries.append((idx, idx + len(word)))
                pos = idx + len(word)
        return boundaries

    def _extract_single_word_fragment(
        self,
        text: str,
        words: List[str],
        word_boundaries: List[Tuple[int, int]],
        match_start: int,
        match_end: int,
        config: HighlightConfig,
    ) -> str:
        """提取单个词数模式片段

        Args:
            text: 原始文本
            words: 分词列表
            word_boundaries: 词边界位置
            match_start: 匹配起始字符位置
            match_end: 匹配结束字符位置
            config: 高亮配置

        Returns:
            提取的片段文本
        """
        if not words or not word_boundaries:
            return text[:config.max_words * 5]

        # 找到匹配位置所在的词索引
        center_idx = self._find_word_index(word_boundaries, match_start, match_end)
        half_words = config.max_words // 2
        start_idx = max(0, center_idx - half_words)
        end_idx = min(len(words), start_idx + config.max_words)

        # 保证最小词数
        if end_idx - start_idx < config.min_words:
            end_idx = min(len(words), start_idx + config.min_words)

        char_start = word_boundaries[start_idx][0]
        char_end = word_boundaries[end_idx - 1][1]

        return text[char_start:char_end]

    def _find_word_index(
        self,
        boundaries: List[Tuple[int, int]],
        match_start: int,
        match_end: int,
    ) -> int:
        """找到匹配位置对应的中心词索引

        Args:
            boundaries: 词边界列表
            match_start: 匹配起始位置
            match_end: 匹配结束位置

        Returns:
            中心词的索引
        """
        center = (match_start + match_end) // 2
        for i, (start, end) in enumerate(boundaries):
            if start <= center < end:
                return i
        return len(boundaries) // 2

    def _extract_fragments_cjk(
        self,
        text: str,
        positions: List[Tuple[int, int]],
        config: HighlightConfig,
    ) -> List[str]:
        """按中文字符模式提取片段

        以中文字符边界为截断点，避免在词语中间截断。

        Args:
            text: 原始文本
            positions: 匹配位置列表
            config: 高亮配置

        Returns:
            文本片段列表
        """
        fragments: List[str] = []

        for match_start, match_end in positions[:config.max_fragments]:
            frag = self._extract_single_cjk_fragment(
                text, match_start, match_end, config,
            )
            fragments.append(frag)

        return fragments

    def _extract_single_cjk_fragment(
        self,
        text: str,
        match_start: int,
        match_end: int,
        config: HighlightConfig,
    ) -> str:
        """提取单个中文模式片段

        以匹配位置为中心，在 max_char_length 范围内截取，
        优先在中文标点或空格处截断。

        Args:
            text: 原始文本
            match_start: 匹配起始位置
            match_end: 匹配结束位置
            config: 高亮配置

        Returns:
            截取的片段
        """
        center = (match_start + match_end) // 2
        half_len = config.max_char_length // 2

        raw_start = max(0, center - half_len)
        raw_end = min(len(text), center + half_len)

        # 调整起始位置到边界
        adj_start = self._adjust_cjk_start(text, raw_start)
        adj_end = self._adjust_cjk_end(text, raw_end)

        return text[adj_start:adj_end]

    def _adjust_cjk_start(self, text: str, pos: int) -> int:
        """调整中文片段起始位置到合适的边界

        优先在标点、空格或中英文边界处截断。

        Args:
            text: 原始文本
            pos: 原始起始位置

        Returns:
            调整后的起始位置
        """
        if pos == 0:
            return 0

        # 向后搜索最近的边界点
        search_range = min(20, pos)
        for offset in range(search_range):
            check_pos = pos - offset
            if check_pos <= 0:
                return 0
            if self._is_boundary_position(text, check_pos):
                return check_pos

        return pos

    def _adjust_cjk_end(self, text: str, pos: int) -> int:
        """调整中文片段结束位置到合适的边界

        优先在标点、空格或中英文边界处截断。

        Args:
            text: 原始文本
            pos: 原始结束位置

        Returns:
            调整后的结束位置
        """
        if pos >= len(text):
            return len(text)

        search_range = min(20, len(text) - pos)
        for offset in range(search_range):
            check_pos = pos + offset
            if check_pos >= len(text):
                return len(text)
            if self._is_boundary_position(text, check_pos):
                return check_pos

        return pos

    def _is_boundary_position(self, text: str, pos: int) -> bool:
        """判断指定位置是否为合适的截断边界

        边界条件：中文标点之后、空格、中英文切换处。

        Args:
            text: 原始文本
            pos: 待检查的位置

        Returns:
            是否为边界位置
        """
        if pos <= 0 or pos >= len(text):
            return True

        prev_char = text[pos - 1]
        curr_char = text[pos]

        # 中文标点之后
        if _CJK_PUNCTUATION.match(prev_char):
            return True

        # 空格
        if prev_char.isspace() or curr_char.isspace():
            return True

        # 中英文边界
        prev_is_cjk = bool(_CJK_RANGE.match(prev_char))
        curr_is_cjk = bool(_CJK_RANGE.match(curr_char))
        if prev_is_cjk != curr_is_cjk:
            return True

        return False

    def _apply_delimiters(
        self,
        fragments: List[str],
        query: str,
        config: HighlightConfig,
    ) -> List[str]:
        """为片段中的匹配词添加高亮标签

        Args:
            fragments: 原始片段列表
            query: 查询字符串
            config: 高亮配置

        Returns:
            已添加高亮标签的片段列表
        """
        query_terms = query.split()
        highlighted: List[str] = []

        for fragment in fragments:
            result = self._highlight_terms(
                fragment, query_terms,
                config.start_delimiter, config.end_delimiter,
            )
            highlighted.append(result)

        return highlighted

    def _highlight_terms(
        self,
        text: str,
        terms: List[str],
        start_delim: str,
        end_delim: str,
    ) -> str:
        """对文本中的匹配词添加高亮标签

        按匹配词在文本中出现的位置逐一包裹标签，
        已被标签包裹的词不再重复包裹。

        Args:
            text: 原始文本
            terms: 匹配词列表
            start_delim: 开始标签
            end_delim: 结束标签

        Returns:
            高亮后的文本
        """
        result = text
        for term in terms:
            if not term:
                continue
            # 构建正则：避免匹配已在标签内的内容
            escaped = re.escape(term)
            # 匹配不在已有标签内的 term
            pattern = re.compile(
                rf'(?<!{re.escape(start_delim)}){escaped}(?!{re.escape(end_delim)})',
                re.IGNORECASE,
            )
            result = pattern.sub(
                f'{start_delim}{term}{end_delim}', result, count=0,
            )
        return result

    def _truncate_ascii_safe(self, text: str, max_length: int) -> str:
        """ASCII 安全截取

        在最大长度内优先在空格处截断。

        Args:
            text: 原始文本
            max_length: 最大长度

        Returns:
            截取后的文本
        """
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > max_length // 2:
            truncated = truncated[:last_space]
        return truncated + ' ...'

    def _truncate_cjk_safe(self, text: str, max_length: int) -> str:
        """中文安全截取

        在最大长度内优先在中文标点或中英文边界处截断。

        Args:
            text: 原始文本
            max_length: 最大长度

        Returns:
            截取后的文本
        """
        truncated = text[:max_length]
        end_pos = self._adjust_cjk_end(truncated, len(truncated))
        truncated = text[:end_pos]
        return truncated + ' ...'

    def _contains_cjk(self, text: str) -> bool:
        """检查文本是否包含 CJK 字符

        Args:
            text: 待检查文本

        Returns:
            是否包含 CJK 字符
        """
        return bool(_CJK_RANGE.search(text))

    def _sanitize_delimiter(self, delimiter: str) -> str:
        """清理并验证高亮标签

        对于 PostgreSQL ts_headline 兼容的标签直接通过，
        其他标签进行基本的 HTML 安全检查。

        Args:
            delimiter: 原始标签字符串

        Returns:
            清理后的标签字符串
        """
        if delimiter in self._ALLOWED_DELIMITERS:
            return delimiter

        # HTML 标签格式：允许字母和连字符
        html_tag = re.match(r'^<(/?[a-zA-Z][a-zA-Z0-9-]*)>$', delimiter)
        if html_tag:
            return delimiter

        # 纯文本标记（如 **、__）
        if re.match(r'^[*_]+$', delimiter):
            return delimiter

        # 默认回退
        return '<mark>'
