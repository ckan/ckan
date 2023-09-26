from __future__ import annotations

import os
from typing import Optional

import ckan.plugins.toolkit as tk
from ckan.exceptions import CkanConfigurationException

CONFIG_BASE_URL = "ckanext.oidc_pkce.base_url"
CONFIG_CLIENT_ID = "ckanext.oidc_pkce.client_id"
CONFIG_CLIENT_SECRET = "ckanext.oidc_pkce.client_secret"

CONFIG_AUTH_PATH = "ckanext.oidc_pkce.auth_path"
DEFAULT_AUTH_PATH = "/oidc/authorize"

CONFIG_TOKEN_PATH = "ckanext.oidc_pkce.token_path"
DEFAULT_TOKEN_PATH = "/oidc/token"

CONFIG_USERINFO_PATH = "ckanext.oidc_pkce.userinfo_path"
DEFAULT_USERINFO_PATH = "/oidc/userinfo"

CONFIG_REDIRECT_PATH = "ckanext.oidc_pkce.redirect_path"
DEFAULT_REDIRECT_PATH = "/user/login/oidc-pkce/callback"

CONFIG_ERROR_REDIRECT = "ckanext.oidc_pkce.error_redirect"
DEFAULT_ERROR_REDIRECT = None

CONFIG_SCOPE = "ckanext.oidc_pkce.scope"
DEFAULT_SCOPE = "openid email profile"

CONFIG_SAME_ID = "ckanext.oidc_pkce.use_same_id"
DEFAULT_SAME_ID = False

CONFIG_MUNGE_PASSWORD = "ckanext.oidc_pkce.munge_password"
DEFAULT_MUNGE_PASSWORD = False


def client_id() -> str:
    """ClientID for SSO application"""
    id_ = os.environ.get('CKANEXT_OIDC_PKCE_CLIENT_ID')
    if not id_:
        id_ = tk.config.get(CONFIG_CLIENT_ID)
        if not id_:
            raise CkanConfigurationException(
                f"{CONFIG_CLIENT_ID} must be configured"
            )

    return id_


def client_secret() -> str:
    """ClientSecret for SSO application"""
    secret_ = os.environ.get('CKANEXT_OIDC_PKCE_CLIENT_SECRET')
    if not secret_:
        secret_ = tk.config.get(CONFIG_CLIENT_SECRET)
    return secret_


def base_url() -> str:
    """Base URL of the SSO application."""
    url = os.environ.get('CKANEXT_OIDC_PKCE_BASE_URL')
    if not url:
        url = tk.config.get(CONFIG_BASE_URL, None)
        if not url:
            raise CkanConfigurationException(
                f"{CONFIG_BASE_URL} must be configured"
            )

    return url.rstrip("/")


def auth_path() -> str:
    """Path(without base URL) where authentication happens."""
    return tk.config.get(CONFIG_AUTH_PATH, DEFAULT_AUTH_PATH)


def auth_url() -> str:
    """SSO URL where authentication happens."""
    return base_url() + auth_path()


def token_path() -> str:
    """Path(without base URL) where authorization token can be retrived."""
    return tk.config.get(CONFIG_TOKEN_PATH, DEFAULT_TOKEN_PATH)


def token_url() -> str:
    """SSO URL where authorization token can be retrived."""
    return base_url() + token_path()


def redirect_path() -> str:
    """Path(without base URL) that handles authentication response."""

    return tk.config.get(CONFIG_REDIRECT_PATH, DEFAULT_REDIRECT_PATH)


def redirect_url() -> str:
    """CKAN URL that handles authentication response."""
    return tk.config["ckan.site_url"].rstrip("/") + redirect_path()


def userinfo_path() -> str:
    """Path(without base URL) where user info can be retrived."""
    return tk.config.get(CONFIG_USERINFO_PATH, DEFAULT_USERINFO_PATH)


def userinfo_url() -> str:
    """SSO URL where user info can be retrived."""
    return base_url() + userinfo_path()


def error_redirect() -> Optional[str]:
    """Destination for redirect after the failed login attempt."""
    return tk.config.get(CONFIG_ERROR_REDIRECT, DEFAULT_ERROR_REDIRECT)


def same_id() -> bool:
    """Use SSO `sub` as CKAN UserID."""
    return tk.asbool(tk.config.get(CONFIG_SAME_ID, DEFAULT_SAME_ID))


def munge_password() -> bool:
    """Override existing pasword for account with a random one, preventing
    direct login.

    """
    return tk.asbool(
        tk.config.get(CONFIG_MUNGE_PASSWORD, DEFAULT_MUNGE_PASSWORD)
    )


def scope() -> str:
    """Scope of the user info retrived from SSO application"""
    return tk.config.get(CONFIG_SCOPE, DEFAULT_SCOPE)
