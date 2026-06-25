# 输入验证层集成指南

## 概述

任务组 4 已完成输入验证层的实施，使用 Pydantic 提供类型安全的输入验证。

## 实施内容

### 1. 验证器模块（`lib/api/validators.py`）

创建了完整的 Pydantic 验证模型：

#### 知识库管理验证
- `CreateKBRequest` - 创建知识库请求验证
- `UpdateKBRequest` - 更新知识库请求验证

#### 原子操作验证
- `ListAtomsRequest` - 列出原子请求验证
- `QueryRequest` - 查询请求验证
- `IngestRequest` - 摄入请求验证
- `UpdateAtomRequest` - 更新原子请求验证
- `DeleteAtomRequest` - 删除原子请求验证

#### 成员管理验证
- `MemberRoleRequest` - 成员角色请求验证

### 2. 验证特性

#### 自动类型转换
```python
# 自动去除首尾空格
request = CreateKBRequest(name="  测试知识库  ")
# request.name == "测试知识库"
```

#### 字段验证
```python
# 长度限制
name: str = Field(..., min_length=1, max_length=100)

# 数值范围
kb_id: int = Field(..., ge=1)  # 大于等于 1
limit: int = Field(default=20, ge=1, le=100)  # 1-100 之间
```

#### 自定义验证器
```python
@field_validator('name')
@classmethod
def validate_name(cls, v: str) -> str:
    """验证名称不为空."""
    if not v or len(v.strip()) == 0:
        raise ValueError('Name cannot be empty')
    return v.strip()
```

#### 枚举值验证
```python
@field_validator('scope')
@classmethod
def validate_scope(cls, v: str) -> str:
    """验证 scope 有效."""
    valid_scopes = ['personal', 'department', 'project', 'company']
    if v not in valid_scopes:
        raise ValueError(f'Invalid scope: {v}. Must be one of {valid_scopes}')
    return v
```

### 3. 测试覆盖

创建了完整的测试文件 `tests/test_validators.py`：

- 19 个测试用例全部通过
- 覆盖所有验证模型
- 测试边界情况和错误处理

## 如何在 API 中集成

### 示例 1：创建知识库 API

**修改前：**
```python
def create_kb(self, data: Dict) -> None:
    name = data.get('name', '')
    if not name:
        self._json_response({'error': '名称不能为空'}, 400)
        return
    # ... 创建逻辑
```

**修改后：**
```python
from lib.api.validators import CreateKBRequest
from pydantic import ValidationError

def create_kb(self, data: Dict) -> None:
    try:
        # 验证输入
        request = CreateKBRequest(**data)
        # 使用验证后的数据
        name = request.name
        scope = request.scope
        # ... 创建逻辑
    except ValidationError as e:
        # 返回验证错误
        self._json_response({
            'error': '输入验证失败',
            'details': e.errors()
        }, 400)
        return
```

### 示例 2：查询 API

**修改前：**
```python
def query(self, params: Dict) -> None:
    q = params.get('q', '')
    limit = int(params.get('limit', 10))
    # ... 查询逻辑
```

**修改后：**
```python
from lib.api.validators import QueryRequest
from pydantic import ValidationError

def query(self, params: Dict) -> None:
    try:
        # 验证输入
        request = QueryRequest(**params)
        # 使用验证后的数据
        q = request.q
        limit = request.limit
        semantic = request.semantic
        # ... 查询逻辑
    except ValidationError as e:
        self._json_response({
            'error': '查询参数无效',
            'details': e.errors()
        }, 400)
        return
```

### 示例 3：摄入 API

**修改前：**
```python
def ingest(self, data: Dict) -> None:
    content = data.get('content', '')
    if not content:
        self._json_response({'error': '内容不能为空'}, 400)
        return
    # ... 摄入逻辑
```

**修改后：**
```python
from lib.api.validators import IngestRequest
from pydantic import ValidationError

def ingest(self, data: Dict) -> None:
    try:
        # 验证输入
        request = IngestRequest(**data)
        # 使用验证后的数据
        content = request.content
        metadata = request.metadata
        # ... 摄入逻辑
    except ValidationError as e:
        self._json_response({
            'error': '摄入数据无效',
            'details': e.errors()
        }, 400)
        return
```

## 验证规则

### 1. 字符串验证
- 自动去除首尾空格
- 长度限制（min_length, max_length）
- 非空验证
- 特殊字符过滤

### 2. 数值验证
- 范围限制（ge, le）
- 正整数验证
- 分页参数验证

### 3. 枚举值验证
- scope: personal, department, project, company
- role: owner, editor, reader
- 原子类型: fact, concept, procedure, principle, example

### 4. 元数据验证
- 键必须是字符串
- 值必须是字符串、数字或布尔值

## 错误响应格式

当验证失败时，返回标准化的错误响应：

```json
{
  "error": "输入验证失败",
  "details": [
    {
      "loc": ["name"],
      "msg": "String should have at least 1 character",
      "type": "string_too_short"
    }
  ]
}
```

## 测试运行

```bash
# 运行验证器测试
python -m pytest tests/test_validators.py -v

# 运行所有测试
python -m pytest tests/ -v
```

## 后续工作

### 建议 1：全面集成验证器
将验证器集成到所有 API 端点，替换手动验证逻辑。

### 建议 2：扩展验证模型
根据业务需求，添加更多验证模型：
- `FileUploadRequest` - 文件上传验证
- `BatchOperationRequest` - 批量操作验证
- `ExportRequest` - 导出请求验证

### 建议 3：自定义错误消息
配置 Pydantic 使用中文错误消息，提升用户体验。

## 总结

✅ 已完成：
1. Pydantic 验证模块创建
2. 完整的测试覆盖（19 个测试用例）
3. 集成指南文档

⏭️ 下一步：
1. 在 `lib/web_server.py` 中集成验证器
2. 在 `lib/api/*.py` 中使用验证模型
3. 添加更多验证模型（根据需求）

## 验证器使用示例

```python
from lib.api.validators import CreateKBRequest, QueryRequest
from pydantic import ValidationError

# 示例 1：创建知识库
try:
    request = CreateKBRequest(
        name="测试知识库",
        description="这是一个测试",
        scope="department"
    )
    print(f"创建知识库: {request.name}")
except ValidationError as e:
    print(f"验证失败: {e}")

# 示例 2：查询
try:
    request = QueryRequest(q="测试查询", limit=20)
    print(f"查询: {request.q}, 限制: {request.limit}")
except ValidationError as e:
    print(f"验证失败: {e}")
```

## 参考

- [Pydantic 文档](https://docs.pydantic.dev/)
- [Pydantic 验证器](https://docs.pydantic.dev/latest/concepts/validators/)
- [Pydantic 字段](https://docs.pydantic.dev/latest/concepts/fields/)
