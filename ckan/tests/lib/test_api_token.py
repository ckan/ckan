import pytest
from faker import Faker
from ckan.lib.api_token import _get_secret, encode_token, decode_token


@pytest.mark.ckan_config("SECRET_KEY", "super_secret")
@pytest.mark.ckan_config("api_token.jwt.encode.secret", None)
@pytest.mark.ckan_config("api_token.jwt.decode.secret", None)
def test_secrets_default_to_SECRET_KEY():
    assert _get_secret(True) == "super_secret"  # Encode
    assert _get_secret(False) == "super_secret"  # Decode


class TestToken:
    def test_data_integrity(self, faker: Faker):
        """Data does not change after a cycle of encoding-decoding."""
        data = faker.pydict(allowed_types=(bool, int, float, str))
        token = encode_token(data)
        assert decode_token(token) == data
