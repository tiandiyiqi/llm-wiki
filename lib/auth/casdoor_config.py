"""Casdoor SSO 配置模块.

从环境变量读取 Casdoor 连接配置，支持启用/禁用开关和配置校验。
"""

import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class CasdoorConfig:
    """Casdoor SSO 连接配置.

    环境变量:
        SSO_ENABLED: 是否启用 SSO（默认 false）
        CASDOOR_ENDPOINT: Casdoor 服务地址
        CASDOOR_CLIENT_ID: OAuth2 客户端 ID
        CASDOOR_CLIENT_SECRET: OAuth2 客户端密钥
        CASDOOR_ORGANIZATION: Casdoor 组织名（默认 llm-wiki）
        CASDOOR_APPLICATION: Casdoor 应用名（默认 llm-wiki-app）
        CASDOOR_CERTIFICATE: JWT 验证公钥（PEM 格式）
        CASDOOR_REDIRECT_URI: OAuth2 回调地址
    """

    enabled: bool = False
    endpoint: str = ""
    client_id: str = ""
    client_secret: str = ""
    organization: str = "llm-wiki"
    application: str = "llm-wiki-app"
    certificate: str = ""
    redirect_uri: str = ""

    # 内部状态
    _env_source: str = field(default="", repr=False)

    @classmethod
    def from_env(cls) -> "CasdoorConfig":
        """从环境变量创建配置.

        Returns:
            CasdoorConfig 实例
        """
        sso_enabled_str = os.getenv("SSO_ENABLED", "false").lower()
        enabled = sso_enabled_str in ("true", "1", "yes", "on")

        config = cls(
            enabled=enabled,
            endpoint=os.getenv("CASDOOR_ENDPOINT", ""),
            client_id=os.getenv("CASDOOR_CLIENT_ID", ""),
            client_secret=os.getenv("CASDOOR_CLIENT_SECRET", ""),
            organization=os.getenv("CASDOOR_ORGANIZATION", "llm-wiki"),
            application=os.getenv("CASDOOR_APPLICATION", "llm-wiki-app"),
            certificate=os.getenv("CASDOOR_CERTIFICATE", ""),
            redirect_uri=os.getenv("CASDOOR_REDIRECT_URI", ""),
            _env_source="environment",
        )

        return config

    @classmethod
    def from_dict(cls, data: dict) -> "CasdoorConfig":
        """从字典创建配置.

        Args:
            data: 配置字典

        Returns:
            CasdoorConfig 实例
        """
        return cls(
            enabled=data.get("enabled", False),
            endpoint=data.get("endpoint", ""),
            client_id=data.get("client_id", ""),
            client_secret=data.get("client_secret", ""),
            organization=data.get("organization", "llm-wiki"),
            application=data.get("application", "llm-wiki-app"),
            certificate=data.get("certificate", ""),
            redirect_uri=data.get("redirect_uri", ""),
            _env_source="dict",
        )

    def validate(self) -> List[str]:
        """校验配置有效性.

        SSO 禁用时不检查必填字段，启用时检查所有必填项。

        Returns:
            校验错误列表（空列表表示配置有效）
        """
        errors: List[str] = []

        # 禁用时跳过校验
        if not self.enabled:
            return errors

        # 必填字段检查
        if not self.endpoint:
            errors.append("CASDOOR_ENDPOINT is required when SSO is enabled")

        if not self.client_id:
            errors.append("CASDOOR_CLIENT_ID is required when SSO is enabled")

        if not self.client_secret:
            errors.append("CASDOOR_CLIENT_SECRET is required when SSO is enabled")

        if not self.certificate:
            errors.append("CASDOOR_CERTIFICATE is required when SSO is enabled")

        if not self.redirect_uri:
            errors.append("CASDOOR_REDIRECT_URI is required when SSO is enabled")

        # 端点 URL 格式校验
        if self.endpoint and not self._is_valid_url(self.endpoint):
            errors.append(
                f"CASDOOR_ENDPOINT must be a valid URL (http/https): {self.endpoint}"
            )

        # 回调 URL 格式校验
        if self.redirect_uri and not self._is_valid_url(self.redirect_uri):
            errors.append(
                f"CASDOOR_REDIRECT_URI must be a valid URL (http/https): {self.redirect_uri}"
            )

        return errors

    def to_env_dict(self) -> dict:
        """导出为环境变量字典.

        Returns:
            环境变量名 → 值的映射
        """
        return {
            "SSO_ENABLED": str(self.enabled).lower(),
            "CASDOOR_ENDPOINT": self.endpoint,
            "CASDOOR_CLIENT_ID": self.client_id,
            "CASDOOR_CLIENT_SECRET": self.client_secret,
            "CASDOOR_ORGANIZATION": self.organization,
            "CASDOOR_APPLICATION": self.application,
            "CASDOOR_CERTIFICATE": self.certificate,
            "CASDOOR_REDIRECT_URI": self.redirect_uri,
        }

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """检查 URL 格式是否有效.

        Args:
            url: URL 字符串

        Returns:
            是否为有效的 http/https URL
        """
        return url.startswith(("http://", "https://"))
