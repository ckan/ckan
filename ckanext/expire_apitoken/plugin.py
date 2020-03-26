# -*- coding: utf-8 -*-

import ckan.plugins as p
import ckan.model as model
from ckan.logic import get_action


class ExpireApiTokenPlugin(p.SingletonPlugin):
    p.implements(p.IApiToken, inherit=True)
    p.implements(p.IConfigurer)

    # IConfigurer

    def update_config(self, config_):
        p.toolkit.add_template_directory(config_, 'templates')

    # IApiToken

    def postprocess_api_token(self, data, token, data_dict):

        return data

    def preprocess_api_token(self, data):
        """Decode token. If it has `last_access` remove it.
        """
        # token = data['token'][1:-1]
        # obj = model.ApiToken.get(token)
        # if obj.last_access:
        #     get_action(u'api_token_revoke')({
        #         u'model': model,
        #         u'user': obj.owner.name
        #     }, {
        #         u'token': token
        #     })
        # data['token'] = token
        return data
