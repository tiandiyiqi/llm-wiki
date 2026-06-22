"""测试密码哈希功能."""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lib.auth import hash_password, verify_password


def test_password_hash():
    """测试密码哈希功能."""
    password = "test_password_123"

    # 测试哈希
    hashed = hash_password(password)
    print(f"✅ 密码哈希成功: {hashed[:20]}...")

    # 验证哈希值不为空
    assert hashed, "哈希值不应为空"
    assert hashed != password, "哈希值不应等于原密码"

    # 测试验证
    assert verify_password(password, hashed), "密码验证应成功"
    print("✅ 密码验证成功")


def test_password_verification():
    """测试密码验证功能."""
    password = "another_test_password"
    hashed = hash_password(password)

    # 测试正确密码
    assert verify_password(password, hashed), "正确密码应验证成功"
    print("✅ 正确密码验证成功")

    # 测试错误密码
    wrong_password = "wrong_password"
    assert not verify_password(wrong_password, hashed), "错误密码应验证失败"
    print("✅ 错误密码验证失败")


def test_hash_uniqueness():
    """测试不同密码的哈希唯一性."""
    password1 = "password1"
    password2 = "password2"

    hash1 = hash_password(password1)
    hash2 = hash_password(password2)

    # 不同密码应有不同哈希
    assert hash1 != hash2, "不同密码应有不同哈希值"
    print("✅ 不同密码产生不同哈希")

    # 相同密码多次哈希应产生不同哈希（因为盐不同）
    hash1_again = hash_password(password1)
    assert hash1 != hash1_again, "相同密码再次哈希应产生不同结果（不同盐）"
    print("✅ 相同密码产生不同哈希（随机盐）")


def test_bcrypt_rounds():
    """测试 bcrypt 迭代次数."""
    password = "test_rounds"

    # 默认 rounds=12
    hashed = hash_password(password)

    # bcrypt 哈希格式: $2b$12$...
    assert hashed.startswith("$2b$12$"), "应使用 bcrypt 格式和 12 轮迭代"
    print(f"✅ bcrypt 格式正确: {hashed[:10]}...")


if __name__ == "__main__":
    print("\n" + "="*50)
    print("开始测试密码哈希功能")
    print("="*50 + "\n")

    test_password_hash()
    test_password_verification()
    test_hash_uniqueness()
    test_bcrypt_rounds()

    print("\n" + "="*50)
    print("✅ 所有测试通过")
    print("="*50 + "\n")
