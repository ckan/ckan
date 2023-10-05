import pytest

from ckan.lib.api_token import _get_secret


@pytest.mark.ckan_config("secret_key", "super_secret")
@pytest.mark.ckan_config("api_token.jwt.encode.secret", None)
@pytest.mark.ckan_config("api_token.jwt.decode.secret", None)
def test_secrets_default_to_secret_key():
    assert _get_secret(True) == "super_secret"  # Encode
    assert _get_secret(False) == "super_secret"  # Decode
