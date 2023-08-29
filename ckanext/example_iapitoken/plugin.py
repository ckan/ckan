# -*- coding: utf-8 -*-
"""Example of one-time token with "encoding" for additional security
level.

"""
from __future__ import annotations

from typing import Any
from ckan.types import Schema
import json
from datetime import datetime

import ckan.plugins as p
import ckan.model as model


class ExampleIApiTokenPlugin(p.SingletonPlugin):
    """Example of plugin, that allows every token to be used only once and
    uses plain JSON instead of JWT.

    """

    p.implements(p.IApiToken)

    # IApiToken

    def create_api_token_schema(self, schema: Schema):
        return schema

    def encode_api_token(self, data: dict[str, Any], **kwargs: Any):
        for k, v in data.items():
            if isinstance(v, datetime):
                data[k] = v.timestamp()

        return json.dumps(data)

    def decode_api_token(self, token: str, **kwargs: Any):
        return json.loads(token)

    def postprocess_api_token(self, data: dict[str, Any], jti: str,
                              data_dict: dict[str, Any]):
        data[u"jti"] = u"!" + jti + u"!"
        return data

    def preprocess_api_token(self, data: dict[str, Any]):
        """Decode token. If it has `last_access` remove it.
        """
        token = data[u"jti"][1:-1]
        data[u"jti"] = token
        obj = model.ApiToken.get(token)
        assert obj
        if obj.last_access:
            model.ApiToken.revoke(token)
        return data

    def add_extra_fields(self, data_dict: dict[str, Any]):
        data_dict[u"hello"] = u"world"
        return data_dict
