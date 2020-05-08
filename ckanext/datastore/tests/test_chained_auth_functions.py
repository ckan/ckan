# -*- coding: utf-8 -*-
import pytest

import ckan.lib.create_test_data as ctd
import ckan.plugins as p
import ckan.tests.factories as factories
from ckan.logic import check_access, NotAuthorized
from ckan.logic.auth.get import user_list as core_user_list


auth_message = u"No search for you"
user_list_message = u"Nothing to see here"


class TestAuthException(Exception):
    pass


@p.toolkit.chained_auth_function
def datastore_search_sql_auth(up_func, context, data_dict):
    # simple checks to confirm that the up_func we've received is the original
    # sql search auth function
    assert up_func.auth_allow_anonymous_access
    assert up_func(context, data_dict) == {u"success": True}
    raise TestAuthException(auth_message)


@p.toolkit.chained_auth_function
def user_list(next_auth, context, data_dict):
    # check it's received the core function as the first arg
    assert next_auth == core_user_list
    raise TestAuthException(user_list_message)


@p.toolkit.chained_auth_function
def user_create(next_auth, context, data_dict):
    return next_auth(context, data_dict)


class ExampleDataStoreSearchSQLPlugin(p.SingletonPlugin):
    p.implements(p.IAuthFunctions)

    def get_auth_functions(self):
        return {
            u"datastore_search_sql": datastore_search_sql_auth,
            u"user_list": user_list,
        }


@pytest.mark.ckan_config(
    u"ckan.plugins", u"datastore example_data_store_search_sql_plugin"
)
@pytest.mark.usefixtures(u"with_request_context", u"with_plugins", u"clean_db")
class TestChainedAuth(object):
    def test_datastore_search_sql_auth(self):
        ctd.CreateTestData.create()
        with pytest.raises(TestAuthException) as raise_context:
            # checking access should call to our chained version defined above
            # first, thus this should throw an exception
            check_access(
                u"datastore_search_sql",
                {u"user": u"annafan", u"table_names": []},
                {},
            )
        # check that exception returned has the message from our auth function
        assert raise_context.value.args == (auth_message, )

    def test_chain_core_auth_functions(self):
        user = factories.User()
        context = {u"user": user[u"name"]}
        with pytest.raises(TestAuthException) as raise_context:
            check_access(u"user_list", context, {})
        assert raise_context.value.args == (user_list_message, )
        # check that the 'auth failed' msg doesn't fail because it's a partial
        with pytest.raises(NotAuthorized):
            check_access(
                u"user_list",
                {u"ignore_auth": False, u"user": u"not_a_real_user"},
                {},
            )


class ExampleExternalProviderPlugin(p.SingletonPlugin):
    p.implements(p.IAuthFunctions)

    def get_auth_functions(self):
        return {u"user_create": user_create}


@pytest.mark.ckan_config(
    u"ckan.plugins", u"datastore example_data_store_search_sql_plugin"
)
@pytest.mark.usefixtures(u"with_plugins", u"clean_db", u"with_request_context")
class TestChainedAuthBuiltInFallback(object):
    def test_user_create_chained_auth(self):
        ctd.CreateTestData.create()
        # check if chained auth fallbacks to built-in user_create
        check_access(u"user_create", {u"user": u"annafan"}, {})
