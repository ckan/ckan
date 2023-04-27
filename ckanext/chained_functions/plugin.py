# -*- coding: utf-8 -*-
from __future__ import annotations

from ckan.types import Action, AuthFunction, Context, DataDict
from typing import Any, Callable, Optional
import ckan.plugins as p
from ckan.plugins.toolkit import (auth_allow_anonymous_access,
                                  chained_auth_function,
                                  chained_action,
                                  side_effect_free,
                                  chained_helper
                                  )


class ChainedFunctionsPlugin(p.SingletonPlugin):
    p.implements(p.IAuthFunctions)
    p.implements(p.IActions)
    p.implements(p.ITemplateHelpers)

    def get_auth_functions(self):
        return {
            "user_show": user_show
        }

    def get_actions(self):
        return {
            "package_search": package_search
        }

    def get_helpers(self) -> dict[str, Callable[..., Any]]:
        return {
            "ckan_version": ckan_version
        }


@auth_allow_anonymous_access
@chained_auth_function
def user_show(next_auth: AuthFunction, context: Context,
              data_dict: Optional[DataDict] = None):
    return next_auth(context, data_dict)  # type: ignore


@side_effect_free
@chained_action
def package_search(original_action: Action, context: Context,
                   data_dict: DataDict):
    return original_action(context, data_dict)


@chained_helper
def ckan_version(next_func: Callable[..., Any], **kw: Any):
    return next_func(**kw)


setattr(ckan_version, "some_attribute", "some_value")
