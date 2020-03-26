# -*- coding: utf-8 -*-
from datetime import datetime

from dateutil.parser import parse as parse_date

import ckan.model as model
import ckan.plugins as p
from ckan.logic import get_action


class ExpireApiTokenPlugin(p.SingletonPlugin):
    p.implements(p.IApiToken, inherit=True)
    p.implements(p.IConfigurer)

    # IConfigurer

    def update_config(self, config_):
        p.toolkit.add_template_directory(config_, u"templates")

    # IApiToken

    def create_api_token_schema(self, schema):
        schema[u"expires_at"] = [
            p.toolkit.get_validator(u"not_empty"),
            p.toolkit.get_validator(u"isodate"),
        ]
        return schema

    def postprocess_api_token(self, data, token, data_dict):
        data[u"expires_at"] = data_dict[u"expires_at"]
        return data

    def preprocess_api_token(self, data):
        expires_at = parse_date(data.get(u"expires_at", u"0001-01-01"))
        token = data["token"]
        obj = model.ApiToken.get(token)
        if obj and expires_at < datetime.now():
            model.ApiToken.revoke(token)
        return data
