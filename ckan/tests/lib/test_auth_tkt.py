# encoding: utf-8
"""
Test the added methods used by this subclass of
repoze.who.plugins.auth_tkt.AuthTktCookiePlugin

Subclassing FunctionalTestBase ensures the original config is restored
after each test.
"""


import pytest
from ckan.tests import helpers
from ckan.lib.repoze_plugins.auth_tkt import make_plugin


@pytest.mark.ckan_config("who.httponly", True)
def test_httponly_expected_cookies_with_config_httponly_true():
    """
    The returned cookies are in the format we expect, with HttpOnly flag.
    """
    plugin = make_plugin(secret="sosecret")
    cookies = plugin._get_cookies(
        environ={"SERVER_NAME": "0.0.0.0"}, value="HELLO"
    )
    expected_cookies = [
        ("Set-Cookie", 'auth_tkt="HELLO"; Path=/; HttpOnly'),
        ("Set-Cookie", 'auth_tkt="HELLO"; Path=/; Domain=0.0.0.0; HttpOnly'),
        ("Set-Cookie", 'auth_tkt="HELLO"; Path=/; Domain=.0.0.0.0; HttpOnly'),
    ]
    assert cookies == expected_cookies


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config("who.httponly", False)
def test_httponly_expected_cookies_with_config_httponly_false():
    """
    The returned cookies are in the format we expect, without HttpOnly
    flag.
    """
    plugin = make_plugin(secret="sosecret")
    cookies = plugin._get_cookies(
        environ={"SERVER_NAME": "0.0.0.0"}, value="HELLO"
    )
    expected_cookies = [
        ("Set-Cookie", 'auth_tkt="HELLO"; Path=/'),
        ("Set-Cookie", 'auth_tkt="HELLO"; Path=/; Domain=0.0.0.0'),
        ("Set-Cookie", 'auth_tkt="HELLO"; Path=/; Domain=.0.0.0.0'),
    ]
    assert cookies == expected_cookies


def test_httponly_expected_cookies_without_config_httponly():
    """
    The returned cookies are in the format we expect, with HttpOnly flag.
    """
    plugin = make_plugin(secret="sosecret")
    cookies = plugin._get_cookies(
        environ={"SERVER_NAME": "0.0.0.0"}, value="HELLO"
    )
    expected_cookies = [
        ("Set-Cookie", 'auth_tkt="HELLO"; Path=/; HttpOnly'),
        ("Set-Cookie", 'auth_tkt="HELLO"; Path=/; Domain=0.0.0.0; HttpOnly'),
        ("Set-Cookie", 'auth_tkt="HELLO"; Path=/; Domain=.0.0.0.0; HttpOnly'),
    ]
    assert cookies == expected_cookies


@pytest.mark.ckan_config("who.secure", True)
def test_secure_expected_cookies_with_config_secure_true():
    """
    The returned cookies are in the format we expect, with secure flag.
    """
    plugin = make_plugin(secret="sosecret")
    cookies = plugin._get_cookies(
        environ={"SERVER_NAME": "0.0.0.0"}, value="HELLO"
    )
    expected_cookies = [
        ("Set-Cookie", 'auth_tkt="HELLO"; Path=/; secure; HttpOnly'),
        (
            "Set-Cookie",
            'auth_tkt="HELLO"; Path=/; Domain=0.0.0.0; secure; HttpOnly',
        ),
        (
            "Set-Cookie",
            'auth_tkt="HELLO"; Path=/; Domain=.0.0.0.0; secure; HttpOnly',
        ),
    ]
    assert cookies == expected_cookies


@pytest.mark.ckan_config("who.secure", False)
def test_secure_expected_cookies_with_config_secure_false():
    """
    The returned cookies are in the format we expect, without secure
    flag.
    """
    plugin = make_plugin(secret="sosecret")
    cookies = plugin._get_cookies(
        environ={"SERVER_NAME": "0.0.0.0"}, value="HELLO"
    )
    expected_cookies = [
        ("Set-Cookie", 'auth_tkt="HELLO"; Path=/; HttpOnly'),
        ("Set-Cookie", 'auth_tkt="HELLO"; Path=/; Domain=0.0.0.0; HttpOnly'),
        ("Set-Cookie", 'auth_tkt="HELLO"; Path=/; Domain=.0.0.0.0; HttpOnly'),
    ]
    assert cookies == expected_cookies


def test_secure_expected_cookies_without_config_secure():
    """
    The returned cookies are in the format we expect, without secure flag.
    """
    plugin = make_plugin(secret="sosecret")
    cookies = plugin._get_cookies(
        environ={"SERVER_NAME": "0.0.0.0"}, value="HELLO"
    )
    expected_cookies = [
        ("Set-Cookie", 'auth_tkt="HELLO"; Path=/; HttpOnly'),
        ("Set-Cookie", 'auth_tkt="HELLO"; Path=/; Domain=0.0.0.0; HttpOnly'),
        ("Set-Cookie", 'auth_tkt="HELLO"; Path=/; Domain=.0.0.0.0; HttpOnly'),
    ]
    assert cookies == expected_cookies


def test_timeout_not_set_in_config():
    """
    Creating a CkanAuthTktCookiePlugin instance without setting timeout in
    config sets correct values in CkanAuthTktCookiePlugin instance.
    """
    plugin = make_plugin(secret="sosecret")

    assert plugin.timeout is None
    assert plugin.reissue_time is None


@pytest.mark.ckan_config("who.timeout", 9000)
def test_timeout_set_in_config():
    """
    Setting who.timeout in config sets correct values in
    CkanAuthTktCookiePlugin instance.
    """
    plugin = make_plugin(secret="sosecret")

    assert plugin.timeout == 9000
    assert plugin.reissue_time == 900


@pytest.mark.ckan_config("who.timeout", 9000)
@pytest.mark.ckan_config("who.reissue_time", 200)
def test_reissue_set_in_config():
    """
    Setting who.reissue in config sets correct values in
    CkanAuthTktCookiePlugin instance.
    """
    plugin = make_plugin(secret="sosecret")

    assert plugin.timeout == 9000
    assert plugin.reissue_time == 200
