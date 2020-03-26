# -*- coding: utf-8 -*-
"""Example of one-time token with "encoding" for additional security
level.

"""
import json

import ckan.plugins as p
import ckan.model as model
from ckan.logic import get_action


class ExampleIApiTokenPlugin(p.SingletonPlugin):

    p.implements(p.IApiToken)

    # IApiToken
    def encode_api_token(self, data):
        return json.dumps(data)

    def decode_api_token(self, token):
        return json.loads(token)

    def postprocess_api_token(self, data, token, data_dict):
        data[u'token'] = u"!" + token + u"!"
        return data

    def preprocess_api_token(self, data):
        """Decode token. If it has `last_access` remove it.
        """
        token = data['token'][1:-1]
        obj = model.ApiToken.get(token)
        if obj.last_access:
            get_action(u'api_token_revoke')({
                u'model': model,
                u'user': obj.owner.name
            }, {
                u'token': token
            })
        data['token'] = token
        return data
