# -*- coding: utf-8 -*-
import nose
import ckan.plugins as p
from ckan.logic import check_access
import ckan.lib.create_test_data as ctd
import ckan.tests.helpers as helpers

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


class ExampleDataStoreSearchSQLPlugin(p.SingletonPlugin):
    p.implements(p.IAuthFunctions)

    def get_auth_functions(self):
        return {u'datastore_search_sql': datastore_search_sql_auth}


class TestChainedAuth(object):
    @classmethod
    def setup_class(cls):
        p.load(u'datastore')
        p.load(u'example_data_store_search_sql_plugin')
        ctd.CreateTestData.create()

    @classmethod
    def teardown_class(cls):
        p.unload(u'example_data_store_search_sql_plugin')
        p.unload(u'datastore')
        helpers.reset_db()

    def test_datastore_search_sql_auth(self):
        with assert_raises(TestAuthException) as raise_context:
            # checking access should call to our chained version defined above
            # first, thus this should throw an exception
            check_access(u'datastore_search_sql', {
                u'user': u'annafan', u'table_names': []}, {})
        # check that exception returned has the message from our auth function
        assert_equals(raise_context.exception.message, auth_message)
