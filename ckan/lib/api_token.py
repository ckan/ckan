# -*- coding: utf-8 -*-

import jwt
import logging

from calendar import timegm

import ckan.plugins as plugins
import ckan.model as model
from ckan.common import config
from ckan.logic.schema import default_create_api_token_schema
from ckan.exceptions import CkanConfigurationException

log = logging.getLogger(__name__)

_config_encode_secret = u"api_token.jwt.encode.secret"
_config_decode_secret = u"api_token.jwt.decode.secret"
_config_secret_fallback = u"beaker.session.secret"

_config_algorithm = u"api_token.jwt.algorithm"


def _get_plugins():
    return plugins.PluginImplementations(plugins.IApiToken)


def _get_algorithm():
    return config.get(_config_algorithm, u"HS256")


def _get_secret(encode):
    config_key = _config_encode_secret if encode else _config_decode_secret
    secret = config.get(config_key)
    if not secret:
        secret = u"string:" + config.get(_config_secret_fallback, u"")
    type_, value = secret.split(u":", 1)
    if type_ == u"file":
        with open(value, u"rb") as key_file:
            value = key_file.read()
    if not value:
        raise CkanConfigurationException(
            (
                u"Neither `{key}` nor `{fallback}` specified. "
                u"Missing secret key is a critical security issue."
            ).format(
                key=config_key, fallback=_config_secret_fallback,
            )
        )
    return value


def into_seconds(dt):
    return timegm(dt.timetuple())


def get_schema():
    schema = default_create_api_token_schema()
    for plugin in _get_plugins():
        schema = plugin.create_api_token_schema(schema)
    return schema


def postprocess(data, jti, data_dict):
    for plugin in _get_plugins():
        data = plugin.postprocess_api_token(data, jti, data_dict)
    return data


def decode(encoded, **kwargs):
    for plugin in _get_plugins():
        data = plugin.decode_api_token(encoded, **kwargs)
        if data:
            break
    else:
        try:
            data = jwt.decode(
                encoded,
                _get_secret(encode=False),
                algorithms=_get_algorithm(),
                **kwargs
            )
        except jwt.InvalidTokenError as e:
            # TODO: add signal for performing extra work, like removing
            # expired tokens
            log.error(u"Cannot decode JWT token: %s", e)
            data = None
    return data


def encode(data, **kwargs):
    for plugin in _get_plugins():
        token = plugin.encode_api_token(data, **kwargs)
        if token:
            break
    else:
        token = jwt.encode(
            data,
            _get_secret(encode=True),
            algorithm=_get_algorithm(),
            **kwargs
        )

    return token


def add_extra(result):
    for plugin in _get_plugins():
        result = plugin.add_extra_fields(result)
    return result


def get_user_from_token(token, update_access_time=True):
    data = decode(token)
    if not data:
        return
    # do preprocessing in reverse order, allowing onion-like
    # "unwrapping" of the data, added during postprocessing, when
    # token was created
    for plugin in reversed(list(_get_plugins())):
        data = plugin.preprocess_api_token(data)
    if not data or u"jti" not in data:
        return
    token_obj = model.ApiToken.get(data[u"jti"])
    if not token_obj:
        return
    if update_access_time:
        token_obj.touch(True)
    return token_obj.owner
