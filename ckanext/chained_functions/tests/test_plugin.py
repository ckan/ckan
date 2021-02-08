# -*- coding: utf-8 -*-

import pytest


@pytest.mark.ckan_config(u"ckan.plugins", u"chained_functions")
@pytest.mark.usefixtures(u"with_plugins")
class TestChainedFunctionsPlugin(object):
    def test_auth_attributes_are_retained(self):
        from ckan.authz import _AuthFunctions
        user_show = _AuthFunctions.get(u"user_show")
        assert hasattr(user_show, u"auth_allow_anonymous_access") is True

    def test_action_attributes_are_retained(self):
        from ckan.plugins.toolkit import get_action
        package_search = get_action(u"package_search")
        assert hasattr(package_search, u"side_effect_free") is True
