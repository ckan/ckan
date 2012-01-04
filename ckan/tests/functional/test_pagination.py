from ckan.lib.create_test_data import CreateTestData
import ckan.model as model
from ckan.tests import TestController, url_for, setup_test_search_index

class TestPagination(TestController):
    @classmethod
    def setup_class(cls):
        setup_test_search_index()
        model.repo.init_db()

        # no. entities per page is hardcoded into the controllers, so
        # create enough of each here so that we can test pagination
        cls.num_groups = 21
        cls.num_packages_in_large_group = 51
        cls.num_users = 21

        groups = [u'group_%s' % str(i).zfill(2) for i in range(1, cls.num_groups)]
        users = [u'user_%s' % str(i).zfill(2) for i in range(cls.num_users)]
        packages = []
        for i in range(cls.num_packages_in_large_group):
            packages.append({
                'name': u'package_%s' % str(i).zfill(2),
                'groups': u'group_00'
            })

        CreateTestData.create_arbitrary(
            packages, extra_group_names=groups, extra_user_names = users,
        )
        
    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_search(self):
        res = self.app.get(url_for(controller='package', action='search', q='groups:group_00'))
        assert 'href="/dataset?q=groups%3Agroup_00&amp;page=2"' in res
        assert 'href="/dataset/package_00"' in res, res
        assert 'href="/dataset/package_19"' in res, res

        res = self.app.get(url_for(controller='package', action='search', q='groups:group_00', page=2))
        assert 'href="/dataset?q=groups%3Agroup_00&amp;page=1"' in res
        assert 'href="/dataset/package_20"' in res
        assert 'href="/dataset/package_39"' in res

    def test_group_index(self):
        res = self.app.get(url_for(controller='group', action='index'))
        assert 'href="/group?page=2"' in res
        assert 'href="/group/group_19"' in res

        res = self.app.get(url_for(controller='group', action='index', page=2))
        assert 'href="/group?page=1"' in res
        assert 'href="/group/group_20"' in res
        
    def test_group_read(self):
        res = self.app.get(url_for(controller='group', action='read', id='group_00'))
        assert 'href="/group/group_00?page=2' in res
        assert 'href="/dataset/package_29"' in res

        res = self.app.get(url_for(controller='group', action='read', id='group_00', page=2))
        assert 'href="/group/group_00?page=1' in res
        assert 'href="/dataset/package_30"' in res

    def test_users_index(self):
        # allow for 2 extra users shown on user listing, 'logged_in' and 'visitor'
        res = self.app.get(url_for(controller='user', action='index'))
        assert 'href="/user/user_18"' in res
        assert 'href="/user?q=&amp;order_by=name&amp;page=2"' in res

        res = self.app.get(url_for(controller='user', action='index', page=2))
        assert 'href="/user/user_20"' in res
        assert 'href="/user?q=&amp;order_by=name&amp;page=1"' in res

