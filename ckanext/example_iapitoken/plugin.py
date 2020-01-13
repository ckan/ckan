# -*- coding: utf-8 -*-
"""Example of one-time token with "encoding" for additional security
level.

"""
import ckan.plugins as p
import ckan.model as model
from ckan.logic import get_action


class ExampleIApiTokenPlugin(p.SingletonPlugin):

    p.implements(p.IApiToken)

    # IApiToken

    def postprocess_api_token(self, token, original):
        return u"!" + token + u"!"

    def preprocess_api_token(self, token, original):
        """Decode token. If it has `last_access` remove it.
        """
        token = token[1:-1]
        obj = model.ApiToken.get(token)
        if obj.last_access:
            get_action(u'api_token_revoke')({
                u'model': model,
                u'user': obj.owner.name
            }, {
                u'token': token
            })

        return token
