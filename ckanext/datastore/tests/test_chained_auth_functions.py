# -*- coding: utf-8 -*-
import pytest

import ckan.lib.create_test_data as ctd
import ckan.plugins as p
import ckan.tests.factories as factories
from ckan.logic import check_access, NotAuthorized
from ckan.logic.auth.get import user_list as core_user_list


auth_message = "No search for yo"
user_list_message = "Nothing to see here"


class TestAuthException(Exception):
    pass


@p.toolkit.chained_auth_function
def datastore_search_sql_auth(up_func, context, data_dict):
    # simple checks to confirm that the up_func we've received is the original
    # sql search auth function
    assert up_func.auth_allow_anonymous_access
    assert up_func(context, data_dict) == {"success": True}
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
            "datastore_search_sql": datastore_search_sql_auth,
            "user_list": user_list,
        }


@pytest.mark.ckan_config(
    "ckan.plugins", "datastore example_data_store_search_sql_plugin"
)
@pytest.mark.usefixtures("with_request_context", "with_plugins", "clean_db")
class TestChainedAuth(object):
    def test_datastore_search_sql_auth(self):
        ctd.CreateTestData.create()
        with pytest.raises(TestAuthException) as raise_context:
            # checking access should call to our chained version defined above
            # first, thus this should throw an exception
            check_access(
                "datastore_search_sql",
                {"user": "annafan", "table_names": []},
                {},
            )
        # check that exception returned has the message from our auth function
        assert raise_context.value.args == (auth_message, )

    def test_chain_core_auth_functions(self):
        user = factories.User()
        context = {"user": user["name"]}
        with pytest.raises(TestAuthException) as raise_context:
            check_access("user_list", context, {})
        assert raise_context.value.args == (user_list_message, )
        # check that the 'auth failed' msg doesn't fail because it's a partial
        with pytest.raises(NotAuthorized):
            check_access(
                "user_list",
                {"ignore_auth": False, "user": "not_a_real_user"},
                {},
            )


class ExampleExternalProviderPlugin(p.SingletonPlugin):
    p.implements(p.IAuthFunctions)

    def get_auth_functions(self):
        return {"user_create": user_create}


@pytest.mark.ckan_config(
    "ckan.plugins", "datastore example_data_store_search_sql_plugin"
)
@pytest.mark.usefixtures("with_plugins", "clean_db", "with_request_context")
class TestChainedAuthBuiltInFallback(object):
    def test_user_create_chained_auth(self):
        ctd.CreateTestData.create()
        # check if chained auth fallbacks to built-in user_create
        check_access("user_create", {"user": "annafan"}, {})
