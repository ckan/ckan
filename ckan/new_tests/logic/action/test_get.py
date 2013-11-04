import nose.tools
import nose.case
import ckan.logic as logic
import ckan.new_tests.helpers as helpers
import ckan.new_tests.factories as factories

class TestBadLimitQueryParameters(object):
    '''test class for #1258 non-int query parameters cause 500 errors'''
    @classmethod
    def setup_class(cls):
        helpers.reset_db()

    def teardown(self):
        import ckan.model as model
        model.repo.rebuild_db()

    def test_user_activity_list(self):
        user = factories.User()
        nose.tools.assert_raises(logic.ValidationError, helpers.call_action, 
            'user_activity_list', id=user['name'], limit='not_an_int',
            offset='not_an_int'
        )
