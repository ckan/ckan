from ckan import model
from ckan.lib.create_test_data import CreateTestData
from ckan.lib.authztool import RightsTool
from ckan.tests import assert_equal, TestRoles

class TestRightsTool:
    @classmethod
    def setup_class(cls):
        CreateTestData.create()

    @classmethod
    def teardown_class(cls):
        model.repo.rebuild_db()
 
    def test_make_role(self):
        assert_equal(TestRoles.get_roles('annakarenina', user_ref='tester'), [])
        RightsTool.make_or_remove_roles('make', 'tester', 'admin', 'annakarenina')
        assert_equal(TestRoles.get_roles('annakarenina', user_ref='tester'), [u'"tester" is "admin" on "annakarenina"'])

    def test_remove_role(self):
        assert_equal(TestRoles.get_roles('system', user_ref='testsysadmin'), ['"testsysadmin" is "admin" on "System"'])
        RightsTool.make_or_remove_roles('remove', 'testsysadmin', 'admin', 'system')
        assert_equal(TestRoles.get_roles('system', user_ref='testsysadmin'), [])

