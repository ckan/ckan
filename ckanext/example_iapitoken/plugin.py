# -*- coding: utf-8 -*-
"""Example of one-time token with "encoding" for additional security
level.

"""
import json
from datetime import datetime

import ckan.plugins as p
import ckan.model as model
from ckan.logic import get_action


class ExampleIApiTokenPlugin(p.SingletonPlugin):
    """Example of plugin, that allows every token to be used only once and
    uses plain JSON instead of JWT.

    """

    p.implements(p.IApiToken)

    # IApiToken

    def create_api_token_schema(self, schema):
        return schema

    def encode_api_token(self, data, **kwargs):
        for k, v in data.items():
            if isinstance(v, datetime):
                data[k] = v.timestamp()

        return json.dumps(data)

    def decode_api_token(self, token, **kwargs):
        return json.loads(token)

    def postprocess_api_token(self, data, jti, data_dict):
        data[u"jti"] = u"!" + jti + u"!"
        return data

    def preprocess_api_token(self, data):
        """Decode token. If it has `last_access` remove it.
        """
        token = data[u"jti"][1:-1]
        data[u"jti"] = token
        obj = model.ApiToken.get(token)
        if obj.last_access:
            model.ApiToken.revoke(token)
        return data

    def add_extra_fields(self, data_dict):
        data_dict[u"hello"] = u"world"
        return data_dict
