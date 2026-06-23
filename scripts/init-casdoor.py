#!/usr/bin/env python3
"""Casdoor SSO 初始化脚本.

自动配置 Casdoor 组织、应用和 IdP，输出所需的环境变量。

Usage:
    python scripts/init-casdoor.py [--endpoint URL] [--admin-username USER] [--admin-password PASS]
"""

import argparse
import json
import sys
import urllib.request
import urllib.error
import base64


def make_request(url: str, method: str = "GET", data: dict | None = None, token: str = "") -> dict:
    """发送 HTTP 请求到 Casdoor API."""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = json.dumps(data).encode("utf-8") if data else None

    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        print(f"❌ HTTP {exc.code}: {error_body}", file=sys.stderr)
        raise
    except urllib.error.URLError as exc:
        print(f"❌ Connection error: {exc.reason}", file=sys.stderr)
        raise


def get_casdoor_token(endpoint: str, admin_username: str, admin_password: str) -> str:
    """获取 Casdoor 管理员 Token."""
    url = f"{endpoint}/api/login"
    data = {
        "username": admin_username,
        "password": admin_password,
        "organization": "built-in",
        "application": "app-built-in",
    }
    result = make_request(url, method="POST", data=data)
    token = result.get("data", result.get("token", ""))
    if not token:
        print("❌ Failed to get Casdoor token", file=sys.stderr)
        sys.exit(1)
    return token


def create_organization(endpoint: str, token: str, org_name: str) -> str:
    """创建 Casdoor 组织."""
    url = f"{endpoint}/api/add-organization"
    data = {
        "name": org_name,
        "displayName": org_name,
    }
    try:
        result = make_request(url, method="POST", data=data, token=token)
        org_id = result.get("data", result.get("name", org_name))
        print(f"✅ 组织 '{org_name}' 创建成功 (ID: {org_id})")
        return org_id
    except Exception:
        print(f"⚠️  组织 '{org_name}' 可能已存在，跳过")
        return org_name


def create_application(
    endpoint: str,
    token: str,
    app_name: str,
    org_name: str,
    redirect_uri: str,
) -> dict:
    """创建 Casdoor 应用并返回 client_id 和 client_secret."""
    url = f"{endpoint}/api/add-application"
    data = {
        "name": app_name,
        "displayName": app_name,
        "organization": org_name,
        "redirectUris": [redirect_uri],
        "tokenFormat": "JWT",
        "expireInHours": 24,
    }
    try:
        result = make_request(url, method="POST", data=data, token=token)
        app_data = result.get("data", result)
        client_id = app_data.get("clientId", "")
        client_secret = app_data.get("clientSecret", "")
        print(f"✅ 应用 '{app_name}' 创建成功")
        return {"client_id": client_id, "client_secret": client_secret}
    except Exception:
        print(f"⚠️  应用 '{app_name}' 可能已存在，尝试获取现有配置")
        # 尝试获取现有应用
        try:
            get_url = f"{endpoint}/api/get-application?id={org_name}/{app_name}"
            result = make_request(get_url, token=token)
            app_data = result.get("data", result)
            client_id = app_data.get("clientId", "")
            client_secret = app_data.get("clientSecret", "")
            print(f"✅ 获取到现有应用配置")
            return {"client_id": client_id, "client_secret": client_secret}
        except Exception:
            print("❌ 无法获取应用配置", file=sys.stderr)
            return {"client_id": "", "client_secret": ""}


def get_certificate(endpoint: str, token: str, app_name: str, org_name: str) -> str:
    """获取应用的 JWT 证书."""
    try:
        url = f"{endpoint}/api/get-application?id={org_name}/{app_name}"
        result = make_request(url, token=token)
        app_data = result.get("data", result)
        cert = app_data.get("cert", "")
        if cert:
            print("✅ 获取到 JWT 证书")
        return cert
    except Exception:
        print("⚠️  无法获取 JWT 证书，需手动配置")
        return ""


def main():
    parser = argparse.ArgumentParser(description="Casdoor SSO 初始化脚本")
    parser.add_argument(
        "--endpoint",
        default="http://localhost:8001",
        help="Casdoor 服务地址 (默认: http://localhost:8001)",
    )
    parser.add_argument(
        "--admin-username",
        default="admin",
        help="Casdoor 管理员用户名 (默认: admin)",
    )
    parser.add_argument(
        "--admin-password",
        default="123",
        help="Casdoor 管理员密码 (默认: 123)",
    )
    parser.add_argument(
        "--org-name",
        default="llm-wiki",
        help="组织名称 (默认: llm-wiki)",
    )
    parser.add_argument(
        "--app-name",
        default="llm-wiki-app",
        help="应用名称 (默认: llm-wiki-app)",
    )
    parser.add_argument(
        "--redirect-uri",
        default="http://localhost:8000/api/auth/sso/callback",
        help="OAuth2 回调地址 (默认: http://localhost:8000/api/auth/sso/callback)",
    )
    args = parser.parse_args()

    endpoint = args.endpoint.rstrip("/")

    print("=" * 60)
    print("🚀 Casdoor SSO 初始化")
    print("=" * 60)
    print(f"端点: {endpoint}")
    print(f"组织: {args.org_name}")
    print(f"应用: {args.app_name}")
    print(f"回调: {args.redirect_uri}")
    print()

    # 步骤 1：获取管理员 Token
    print("步骤 1/4：获取管理员 Token...")
    token = get_casdoor_token(endpoint, args.admin_username, args.admin_password)
    print("✅ Token 获取成功")
    print()

    # 步骤 2：创建组织
    print("步骤 2/4：创建组织...")
    org_id = create_organization(endpoint, token, args.org_name)
    print()

    # 步骤 3：创建应用
    print("步骤 3/4：创建应用...")
    app_creds = create_application(
        endpoint, token, args.app_name, args.org_name, args.redirect_uri
    )
    print()

    # 步骤 4：获取证书
    print("步骤 4/4：获取 JWT 证书...")
    certificate = get_certificate(endpoint, token, args.app_name, args.org_name)
    print()

    # 输出环境变量
    print("=" * 60)
    print("📋 环境变量配置（添加到 .env 文件）")
    print("=" * 60)
    print(f"""
SSO_ENABLED=true
CASDOOR_ENDPOINT={endpoint}
CASDOOR_CLIENT_ID={app_creds.get('client_id', '<YOUR_CLIENT_ID>')}
CASDOOR_CLIENT_SECRET={app_creds.get('client_secret', '<YOUR_CLIENT_SECRET>')}
CASDOOR_ORGANIZATION={args.org_name}
CASDOOR_APPLICATION={args.app_name}
CASDOOR_CERTIFICATE={certificate[:50] + '...' if certificate else '<YOUR_CERTIFICATE>'}
CASDOOR_REDIRECT_URI={args.redirect_uri}
""")

    if not app_creds.get("client_id") or not app_creds.get("client_secret"):
        print("⚠️  Client ID 或 Client Secret 未获取到")
        print("   请登录 Casdoor 管理后台手动获取：")
        print(f"   {endpoint}")
        print()

    print("✅ 初始化完成！")
    print()
    print("下一步：")
    print("1. 将上述环境变量添加到 .env 文件")
    print("2. 重启 llm-wiki 服务")
    print("3. 访问登录页面，应该能看到 '企业 SSO 登录' 按钮")
    print()
    print("💡 提示：")
    print("   - Casdoor 管理后台: " + endpoint)
    print("   - 默认管理员: admin / 123（请及时修改密码）")
    print("   - 企业微信/钉钉/飞书 IdP 需在 Casdoor 管理后台中配置")


if __name__ == "__main__":
    main()
