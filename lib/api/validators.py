"""API 输入验证模块.

使用 Pydantic 进行输入参数验证,防止无效数据进入系统。
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class CreateKBRequest(BaseModel):
    """创建知识库请求验证模型."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    scope: str = Field(default='personal')

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """验证名称不为空."""
        if not v or len(v.strip()) == 0:
            raise ValueError('Name cannot be empty')
        return v.strip()

    @field_validator('scope')
    @classmethod
    def validate_scope(cls, v: str) -> str:
        """验证 scope 有效."""
        valid_scopes = ['personal', 'department', 'project', 'company']
        if v not in valid_scopes:
            raise ValueError(f'Invalid scope: {v}. Must be one of {valid_scopes}')
        return v


class UpdateKBRequest(BaseModel):
    """更新知识库请求验证模型."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """验证名称不为空."""
        if v is not None:
            if not v or len(v.strip()) == 0:
                raise ValueError('Name cannot be empty')
            return v.strip()
        return v


class ListAtomsRequest(BaseModel):
    """列出原子请求验证模型."""

    kb_id: int = Field(..., ge=1)
    page: int = Field(default=1, ge=1, le=1000)
    limit: int = Field(default=20, ge=1, le=100)


class QueryRequest(BaseModel):
    """查询请求验证模型."""

    model_config = ConfigDict(str_strip_whitespace=True)

    q: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=100)
    semantic: bool = Field(default=False)

    @field_validator('q')
    @classmethod
    def validate_query(cls, v: str) -> str:
        """验证查询不为空."""
        if not v or len(v.strip()) == 0:
            raise ValueError('Query cannot be empty')
        return v.strip()


class IngestRequest(BaseModel):
    """摄入请求验证模型."""

    model_config = ConfigDict(str_strip_whitespace=True)

    content: str = Field(..., min_length=1, max_length=10000)
    metadata: Optional[dict] = Field(default=None)

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """验证内容不为空."""
        if not v or len(v.strip()) == 0:
            raise ValueError('Content cannot be empty')
        return v.strip()

    @field_validator('metadata')
    @classmethod
    def validate_metadata(cls, v: Optional[dict]) -> Optional[dict]:
        """验证 metadata 字典."""
        if v is not None:
            # 确保所有键值都是字符串或数字
            for key, value in v.items():
                if not isinstance(key, str):
                    raise ValueError('Metadata keys must be strings')
                if not isinstance(value, (str, int, float, bool)):
                    raise ValueError('Metadata values must be strings, numbers, or booleans')
        return v


class UpdateAtomRequest(BaseModel):
    """更新原子请求验证模型."""

    model_config = ConfigDict(str_strip_whitespace=True)

    content: Optional[str] = Field(None, min_length=1, max_length=10000)
    metadata: Optional[dict] = Field(default=None)

    @field_validator('content')
    @classmethod
    def validate_content(cls, v: Optional[str]) -> Optional[str]:
        """验证内容不为空."""
        if v is not None:
            if not v or len(v.strip()) == 0:
                raise ValueError('Content cannot be empty')
            return v.strip()
        return v


class DeleteAtomRequest(BaseModel):
    """删除原子请求验证模型."""

    atom_id: int = Field(..., ge=1)


class MemberRoleRequest(BaseModel):
    """成员角色请求验证模型."""

    model_config = ConfigDict(str_strip_whitespace=True)

    user_id: str = Field(..., min_length=1, max_length=50)
    role: str = Field(...)

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """验证用户 ID 不为空."""
        if not v or len(v.strip()) == 0:
            raise ValueError('User ID cannot be empty')
        return v.strip()

    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        """验证角色有效."""
        valid_roles = ['owner', 'editor', 'reader']
        if v not in valid_roles:
            raise ValueError(f'Invalid role: {v}. Must be one of {valid_roles}')
        return v
