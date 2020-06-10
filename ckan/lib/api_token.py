import jwt
import logging

from ckan.common import config

log = logging.getLogger(__name__)

_config_secret = u"api_token.jwt.secret"
_config_secret_fallback = u"beaker.session.secret"

_config_algorithm = u"api_token.jwt.algorithm"


def _get_algorithm():
    return config.get(_config_algorithm, "HS256")


def _get_secret():
    secret = config.get(_config_secret)
    if not secret:
        secret = config.get(_config_secret_fallback)
    if not secret:
        log.warning(
            "Neither `%s` nor `%s` specified. "
            "Missing secret key is a critical security issue.",
            _config_secret,
            _config_secret_fallback,
        )
    return secret


def decode(encoded):
    try:
        return jwt.decode(
            encoded, _get_secret(), algorithms=[_get_algorithm()]
        )
    except jwt.InvalidTokenError as e:
        log.error("Cannot decode JWT token: %s", e)


def encode(data):
    return jwt.encode(data, _get_secret(), algorithm=_get_algorithm())
