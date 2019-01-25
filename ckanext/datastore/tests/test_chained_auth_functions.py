# -*- coding: utf-8 -*-
import nose
import ckan.plugins as p
from ckan.logic import check_access
import ckan.lib.create_test_data as ctd
import ckan.tests.helpers as helpers

from ckanext.datastore.tests.helpers import DatastoreFunctionalTestBase

assert_equals = nose.tools.assert_equals
assert_raises = nose.tools.assert_raises


auth_message = u'No search for you'


class TestAuthException(Exception):
    pass


@p.toolkit.chained_auth_function
def datastore_search_sql_auth(up_func, context, data_dict):
    # simple checks to confirm that the up_func we've received is the original
    # sql search auth function
    assert_equals(up_func.auth_allow_anonymous_access, True)
    assert_equals(up_func(context, data_dict), {u'success': True})
    raise TestAuthException(auth_message)


@p.toolkit.chained_auth_function
def user_create(up_func, context, data_dict):
    return up_func(context, data_dict)


class ExampleDataStoreSearchSQLPlugin(p.SingletonPlugin):
    p.implements(p.IAuthFunctions)

    def get_auth_functions(self):
        return {u'datastore_search_sql': datastore_search_sql_auth}


class TestChainedAuth(DatastoreFunctionalTestBase):
    _load_plugins = (
        u'datastore',
        u'example_data_store_search_sql_plugin')

    def test_datastore_search_sql_auth(self):
        ctd.CreateTestData.create()
        with assert_raises(TestAuthException) as raise_context:
            # checking access should call to our chained version defined above
            # first, thus this should throw an exception
            check_access(u'datastore_search_sql', {
                u'user': u'annafan', u'table_names': []}, {})
        # check that exception returned has the message from our auth function
        assert_equals(raise_context.exception.message, auth_message)


class ExampleExternalProviderPlugin(p.SingletonPlugin):
    p.implements(p.IAuthFunctions)

    def get_auth_functions(self):
        return {u'user_create': user_create}


class TestChainedAuthBuiltInFallback(DatastoreFunctionalTestBase):
    _load_plugins = (
        u'datastore',
        u'example_external_provider_plugin')

    def test_user_create_chained_auth(self):
        ctd.CreateTestData.create()
        # check if chained auth fallbacks to built-in user_create
        check_access(u'user_create', {u'user': u'annafan'}, {})
