# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from dateutil.parser import parse as parse_date

import ckan.model as model
import ckan.plugins as p
from ckan.logic import get_action


def default_token_lifetime():
    return p.toolkit.config.get(u"expire_api_token.default_lifetime", 3600)


class ExpireApiTokenPlugin(p.SingletonPlugin):
    p.implements(p.IApiToken, inherit=True)
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)

    # IConfigurer

    def update_config(self, config_):
        p.toolkit.add_template_directory(config_, u"templates")

    # ITemplateHelpers

    def get_helpers(self):
        return {
            "expire_api_token_default_token_lifetime": default_token_lifetime
        }

    # IApiToken

    def create_api_token_schema(self, schema):
        schema[u"expires_in"] = [
            p.toolkit.get_validator(u"not_empty"),
            p.toolkit.get_validator(u"is_positive_integer"),
        ]
        schema[u"unit"] = [
            p.toolkit.get_validator(u"not_empty"),
            p.toolkit.get_validator(u"is_positive_integer"),
        ]
        return schema

    def postprocess_api_token(self, data, jti, data_dict):
        seconds = data_dict.get(u"expires_in", 0) * data_dict.get(u"unit", 0)
        if not seconds:
            seconds = default_token_lifetime()
        data[u"exp"] = datetime.utcnow() + timedelta(seconds=seconds)
        token = model.ApiToken.get(jti)
        token.set_extra(
            u"expire_api_token", {u"exp": data[u"exp"].isoformat()}, True
        )
        return data

    # TODO: subscribe to signal, sent from api_token.decode and remove
    # expired tokens
