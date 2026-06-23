"""CasdoorConfig 配置模块测试."""

import os
from unittest.mock import patch

import pytest

from lib.auth.casdoor_config import CasdoorConfig


class TestCasdoorConfigFromEnv:
    """CasdoorConfig.from_env() 测试."""

    def test_default_values(self):
        """测试无环境变量时的默认值."""
        with patch.dict(os.environ, {}, clear=True):
            config = CasdoorConfig.from_env()

        assert config.enabled is False
        assert config.endpoint == ""
        assert config.client_id == ""
        assert config.client_secret == ""
        assert config.organization == "llm-wiki"
        assert config.application == "llm-wiki-app"
        assert config.certificate == ""
        assert config.redirect_uri == ""

    def test_sso_enabled_true(self):
        """测试 SSO_ENABLED=true."""
        env = {"SSO_ENABLED": "true"}
        with patch.dict(os.environ, env, clear=True):
            config = CasdoorConfig.from_env()

        assert config.enabled is True

    def test_sso_enabled_variants(self):
        """测试 SSO_ENABLED 的各种真值变体."""
        for value in ("true", "1", "yes", "on", "True", "TRUE"):
            with patch.dict(os.environ, {"SSO_ENABLED": value}, clear=True):
                config = CasdoorConfig.from_env()
                assert config.enabled is True, f"Failed for SSO_ENABLED={value}"

    def test_sso_enabled_false_variants(self):
        """测试 SSO_ENABLED 的假值变体."""
        for value in ("false", "0", "no", "off", ""):
            with patch.dict(os.environ, {"SSO_ENABLED": value}, clear=True):
                config = CasdoorConfig.from_env()
                assert config.enabled is False, f"Failed for SSO_ENABLED={value}"

    def test_env_override(self):
        """测试环境变量覆盖所有字段."""
        env = {
            "SSO_ENABLED": "true",
            "CASDOOR_ENDPOINT": "https://casdoor.example.com",
            "CASDOOR_CLIENT_ID": "test-client-id",
            "CASDOOR_CLIENT_SECRET": "test-client-secret",
            "CASDOOR_ORGANIZATION": "my-org",
            "CASDOOR_APPLICATION": "my-app",
            "CASDOOR_CERTIFICATE": "-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----",
            "CASDOOR_REDIRECT_URI": "https://app.example.com/api/auth/sso/callback",
        }
        with patch.dict(os.environ, env, clear=True):
            config = CasdoorConfig.from_env()

        assert config.enabled is True
        assert config.endpoint == "https://casdoor.example.com"
        assert config.client_id == "test-client-id"
        assert config.client_secret == "test-client-secret"
        assert config.organization == "my-org"
        assert config.application == "my-app"
        assert "BEGIN CERTIFICATE" in config.certificate
        assert config.redirect_uri == "https://app.example.com/api/auth/sso/callback"

    def test_partial_env(self):
        """测试仅设置部分环境变量."""
        env = {
            "SSO_ENABLED": "true",
            "CASDOOR_ENDPOINT": "http://casdoor:8000",
        }
        with patch.dict(os.environ, env, clear=True):
            config = CasdoorConfig.from_env()

        assert config.enabled is True
        assert config.endpoint == "http://casdoor:8000"
        assert config.client_id == ""  # 未设置
        assert config.organization == "llm-wiki"  # 默认值


class TestCasdoorConfigFromDict:
    """CasdoorConfig.from_dict() 测试."""

    def test_from_dict_full(self):
        """测试从完整字典创建."""
        data = {
            "enabled": True,
            "endpoint": "https://casdoor.example.com",
            "client_id": "dict-client-id",
            "client_secret": "dict-secret",
            "organization": "dict-org",
            "application": "dict-app",
            "certificate": "cert-content",
            "redirect_uri": "https://app.example.com/callback",
        }
        config = CasdoorConfig.from_dict(data)

        assert config.enabled is True
        assert config.endpoint == "https://casdoor.example.com"
        assert config.client_id == "dict-client-id"

    def test_from_dict_empty(self):
        """测试从空字典创建（使用默认值）."""
        config = CasdoorConfig.from_dict({})

        assert config.enabled is False
        assert config.endpoint == ""
        assert config.organization == "llm-wiki"

    def test_from_dict_partial(self):
        """测试从部分字典创建."""
        data = {"enabled": True, "endpoint": "http://localhost:8001"}
        config = CasdoorConfig.from_dict(data)

        assert config.enabled is True
        assert config.endpoint == "http://localhost:8001"
        assert config.client_id == ""


class TestCasdoorConfigValidate:
    """CasdoorConfig.validate() 测试."""

    def test_validate_disabled_no_errors(self):
        """测试 SSO 禁用时无校验错误."""
        config = CasdoorConfig(enabled=False)
        errors = config.validate()

        assert errors == []

    def test_validate_disabled_missing_fields(self):
        """测试 SSO 禁用时缺少必填字段不报错."""
        config = CasdoorConfig(enabled=False, endpoint="", client_id="")
        errors = config.validate()

        assert errors == []

    def test_validate_enabled_missing_all_required(self):
        """测试 SSO 启用时缺少所有必填字段."""
        config = CasdoorConfig(enabled=True)
        errors = config.validate()

        assert len(errors) == 5
        assert "CASDOOR_ENDPOINT" in errors[0]
        assert "CASDOOR_CLIENT_ID" in errors[1]
        assert "CASDOOR_CLIENT_SECRET" in errors[2]
        assert "CASDOOR_CERTIFICATE" in errors[3]
        assert "CASDOOR_REDIRECT_URI" in errors[4]

    def test_validate_enabled_all_fields_valid(self):
        """测试 SSO 启用且所有字段有效."""
        config = CasdoorConfig(
            enabled=True,
            endpoint="https://casdoor.example.com",
            client_id="valid-id",
            client_secret="valid-secret",
            certificate="valid-cert",
            redirect_uri="https://app.example.com/callback",
        )
        errors = config.validate()

        assert errors == []

    def test_validate_invalid_endpoint_url(self):
        """测试无效的端点 URL 格式."""
        config = CasdoorConfig(
            enabled=True,
            endpoint="not-a-url",
            client_id="id",
            client_secret="secret",
            certificate="cert",
            redirect_uri="https://app.example.com/callback",
        )
        errors = config.validate()

        assert any("CASDOOR_ENDPOINT" in e and "valid URL" in e for e in errors)

    def test_validate_invalid_redirect_uri(self):
        """测试无效的回调 URL 格式."""
        config = CasdoorConfig(
            enabled=True,
            endpoint="https://casdoor.example.com",
            client_id="id",
            client_secret="secret",
            certificate="cert",
            redirect_uri="ftp://invalid.com/callback",
        )
        errors = config.validate()

        assert any("CASDOOR_REDIRECT_URI" in e and "valid URL" in e for e in errors)

    def test_validate_http_endpoint_allowed(self):
        """测试 http:// 端点 URL 允许（开发环境）."""
        config = CasdoorConfig(
            enabled=True,
            endpoint="http://localhost:8001",
            client_id="id",
            client_secret="secret",
            certificate="cert",
            redirect_uri="http://localhost:8000/api/auth/sso/callback",
        )
        errors = config.validate()

        assert errors == []

    def test_validate_partial_required_fields(self):
        """测试仅缺少部分必填字段."""
        config = CasdoorConfig(
            enabled=True,
            endpoint="https://casdoor.example.com",
            client_id="valid-id",
            # 缺少 client_secret, certificate, redirect_uri
        )
        errors = config.validate()

        assert len(errors) == 3
        assert "CASDOOR_CLIENT_SECRET" in errors[0]
        assert "CASDOOR_CERTIFICATE" in errors[1]
        assert "CASDOOR_REDIRECT_URI" in errors[2]


class TestCasdoorConfigToEnvDict:
    """CasdoorConfig.to_env_dict() 测试."""

    def test_to_env_dict(self):
        """测试导出为环境变量字典."""
        config = CasdoorConfig(
            enabled=True,
            endpoint="https://casdoor.example.com",
            client_id="test-id",
            client_secret="test-secret",
            organization="my-org",
            application="my-app",
            certificate="cert",
            redirect_uri="https://app.example.com/callback",
        )
        env_dict = config.to_env_dict()

        assert env_dict["SSO_ENABLED"] == "true"
        assert env_dict["CASDOOR_ENDPOINT"] == "https://casdoor.example.com"
        assert env_dict["CASDOOR_CLIENT_ID"] == "test-id"
        assert env_dict["CASDOOR_CLIENT_SECRET"] == "test-secret"
        assert env_dict["CASDOOR_ORGANIZATION"] == "my-org"
        assert env_dict["CASDOOR_APPLICATION"] == "my-app"
        assert env_dict["CASDOOR_CERTIFICATE"] == "cert"
        assert env_dict["CASDOOR_REDIRECT_URI"] == "https://app.example.com/callback"

    def test_to_env_dict_disabled(self):
        """测试禁用状态导出."""
        config = CasdoorConfig()
        env_dict = config.to_env_dict()

        assert env_dict["SSO_ENABLED"] == "false"
