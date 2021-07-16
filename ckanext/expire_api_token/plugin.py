# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

import ckan.model as model
import ckan.plugins as p
import ckan.lib.api_token as api_token


def default_token_lifetime():
    return p.toolkit.config.get("expire_api_token.default_lifetime", 3600)


class ExpireApiTokenPlugin(p.SingletonPlugin):
    p.implements(p.IApiToken, inherit=True)
    p.implements(p.IConfigurer)
    p.implements(p.ITemplateHelpers)

    # IConfigurer

    def update_config(self, config_):
        p.toolkit.add_template_directory(config_, "templates")

    # ITemplateHelpers

    def get_helpers(self):
        return {
            "expire_api_token_default_token_lifetime": default_token_lifetime
        }

    # IApiToken

    def create_api_token_schema(self, schema):
        schema["expires_in"] = [
            p.toolkit.get_validator("not_empty"),
            p.toolkit.get_validator("is_positive_integer"),
        ]
        schema["unit"] = [
            p.toolkit.get_validator("not_empty"),
            p.toolkit.get_validator("is_positive_integer"),
        ]
        return schema

    def postprocess_api_token(self, data, jti, data_dict):
        seconds = data_dict.get("expires_in", 0) * data_dict.get("unit", 0)
        if not seconds:
            seconds = default_token_lifetime()
        expire_at = datetime.utcnow() + timedelta(seconds=seconds)
        data["exp"] = api_token.into_seconds(
            expire_at
        )
        token = model.ApiToken.get(jti)
        token.set_extra(
            "expire_api_token", {"exp": expire_at.isoformat()}, True
        )
        return data

    # TODO: subscribe to signal, sent from api_token.decode and remove
    # expired tokens
