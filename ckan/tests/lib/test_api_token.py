import pytest

from ckan.lib.api_token import _get_secret
from ckan.exceptions import CkanConfigurationException

@pytest.mark.ckan_config("SECRET_KEY", "super_secret")
@pytest.mark.ckan_config("api_token.jwt.encode.secret", None)
@pytest.mark.ckan_config("api_token.jwt.decode.secret", None)
def test_secrets_default_to_SECRET_KEY():
    assert _get_secret(True) == "super_secret"  # Encode
    assert _get_secret(False) == "super_secret"  # Decode


@pytest.mark.parametrize("encode", [True, False])
@pytest.mark.ckan_config("SECRET_KEY", NONE)
@pytest.mark.ckan_config("api_token.jwt.encode.secret", None)
@pytest.mark.ckan_config("api_token.jwt.decode.secret", None)
def test_secrets_raise_error_if_no_fallback(encode):
    with pytest.raises(CkanConfigurationException):
        _get_secret(encode)
