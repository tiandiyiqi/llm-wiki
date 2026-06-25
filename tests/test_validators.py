"""输入验证测试."""

import pytest
from pydantic import ValidationError
from lib.api.validators import (
    CreateKBRequest,
    UpdateKBRequest,
    ListAtomsRequest,
    QueryRequest,
    IngestRequest,
    UpdateAtomRequest,
    MemberRoleRequest
)


class TestCreateKBRequest:
    """测试创建知识库请求验证."""

    def test_valid_request(self):
        """测试有效请求."""
        request = CreateKBRequest(
            name="Test KB",
            description="Test description",
            scope="personal"
        )
        assert request.name == "Test KB"
        assert request.description == "Test description"
        assert request.scope == "personal"

    def test_empty_name(self):
        """测试空名称返回错误."""
        with pytest.raises(ValidationError) as exc_info:
            CreateKBRequest(name="", scope="personal")
        # Pydantic 默认错误消息
        assert 'String should have at least 1 character' in str(exc_info.value) or 'Name cannot be empty' in str(exc_info.value)

    def test_long_name(self):
        """测试超长名称返回错误."""
        with pytest.raises(ValidationError) as exc_info:
            CreateKBRequest(name="x" * 101, scope="personal")
        assert 'at most 100 characters' in str(exc_info.value)

    def test_invalid_scope(self):
        """测试非法 scope 返回错误."""
        with pytest.raises(ValidationError) as exc_info:
            CreateKBRequest(name="Test", scope="invalid")
        assert 'Invalid scope' in str(exc_info.value)

    def test_default_scope(self):
        """测试默认 scope."""
        request = CreateKBRequest(name="Test")
        assert request.scope == "personal"


class TestQueryRequest:
    """测试查询请求验证."""

    def test_valid_request(self):
        """测试有效请求."""
        request = QueryRequest(q="test query")
        assert request.q == "test query"
        assert request.limit == 10
        assert request.semantic is False

    def test_empty_query(self):
        """测试空查询返回错误."""
        with pytest.raises(ValidationError) as exc_info:
            QueryRequest(q="")
        assert 'String should have at least 1 character' in str(exc_info.value) or 'Query cannot be empty' in str(exc_info.value)

    def test_long_query(self):
        """测试超长查询返回错误."""
        with pytest.raises(ValidationError) as exc_info:
            QueryRequest(q="x" * 501)
        assert 'at most 500 characters' in str(exc_info.value)

    def test_invalid_limit(self):
        """测试超限 limit 返回错误."""
        with pytest.raises(ValidationError) as exc_info:
            QueryRequest(q="test", limit=101)
        assert 'less than or equal to 100' in str(exc_info.value)

    def test_valid_limit(self):
        """测试有效输入正常处理."""
        request = QueryRequest(q="test", limit=50, semantic=True)
        assert request.limit == 50
        assert request.semantic is True


class TestIngestRequest:
    """测试摄入请求验证."""

    def test_valid_request(self):
        """测试有效请求."""
        request = IngestRequest(
            content="Test content",
            metadata={"key": "value"}
        )
        assert request.content == "Test content"
        assert request.metadata == {"key": "value"}

    def test_empty_content(self):
        """测试空内容返回错误."""
        with pytest.raises(ValidationError) as exc_info:
            IngestRequest(content="")
        assert 'String should have at least 1 character' in str(exc_info.value) or 'Content cannot be empty' in str(exc_info.value)

    def test_invalid_metadata(self):
        """测试无效 metadata 类型."""
        with pytest.raises(ValidationError) as exc_info:
            IngestRequest(content="Test", metadata={"key": {"nested": "dict"}})
        assert 'must be strings, numbers, or booleans' in str(exc_info.value)


class TestListAtomsRequest:
    """测试列出原子请求验证."""

    def test_valid_request(self):
        """测试有效请求."""
        request = ListAtomsRequest(kb_id=1, page=1, limit=20)
        assert request.kb_id == 1
        assert request.page == 1
        assert request.limit == 20

    def test_invalid_page(self):
        """测试无效页码返回错误."""
        with pytest.raises(ValidationError):
            ListAtomsRequest(kb_id=1, page=0)

    def test_invalid_limit(self):
        """测试无效限制返回错误."""
        with pytest.raises(ValidationError):
            ListAtomsRequest(kb_id=1, limit=101)


class TestMemberRoleRequest:
    """测试成员角色请求验证."""

    def test_valid_request(self):
        """测试有效请求."""
        request = MemberRoleRequest(user_id="user123", role="editor")
        assert request.user_id == "user123"
        assert request.role == "editor"

    def test_empty_user_id(self):
        """测试空用户 ID 返回错误."""
        with pytest.raises(ValidationError) as exc_info:
            MemberRoleRequest(user_id="", role="editor")
        assert 'String should have at least 1 character' in str(exc_info.value) or 'User ID cannot be empty' in str(exc_info.value)

    def test_invalid_role(self):
        """测试无效角色返回错误."""
        with pytest.raises(ValidationError) as exc_info:
            MemberRoleRequest(user_id="user123", role="invalid")
        assert 'Invalid role' in str(exc_info.value)
