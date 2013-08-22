import re

from nose.tools import assert_equal

from ckan.lib.create_test_data import CreateTestData
import ckan.model as model
from ckan.tests import TestController, url_for, setup_test_search_index

def scrape_search_results(response, object_type):
    assert object_type in ('dataset', 'group_dataset', 'group', 'user')
    if object_type is not 'group_dataset':
        results = re.findall('href="/%s/%s_(\d\d)"' % (object_type, object_type),
                             str(response))
    else:
        object_type = 'dataset'
        results = re.findall('href="/%s/%s_(\d\d)"' % (object_type, object_type),
                             str(response))
    return results

def test_scrape_user():
    html = '''
          <li class="username">
          <img src="//gravatar.com/avatar/d41d8cd98f00b204e9800998ecf8427e?s=16&amp;d=http://test.ckan.net/images/icons/user.png" /> <a href="/user/user_00">user_00</a>
          </li>
          ...
          <li class="username">
          <img src="//gravatar.com/avatar/d41d8cd98f00b204e9800998ecf8427e?s=16&amp;d=http://test.ckan.net/images/icons/user.png" /> <a href="/user/user_01">user_01</a>
          </li>

      '''
    res = scrape_search_results(html, 'user')
    assert_equal(res, ['00', '01'])


class TestPaginationPackage(TestController):
    @classmethod
    def setup_class(cls):
        setup_test_search_index()
        model.repo.init_db()

        # no. entities per page is hardcoded into the controllers, so
        # create enough of each here so that we can test pagination
        cls.num_packages_in_large_group = 51

        packages = []
        for i in range(cls.num_packages_in_large_group):
            packages.append({
                # CS: nasty_string ignore
                'name': u'dataset_%s' % str(i).zfill(2),
                'groups': u'group_00'
            })

        CreateTestData.create_arbitrary(packages)

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_package_search_p1(self):
        res = self.app.get(url_for(controller='package', action='search', q='groups:group_00'))
        assert 'href="/dataset?q=groups%3Agroup_00&amp;page=2"' in res
        pkg_numbers = scrape_search_results(res, 'dataset')
        assert_equal(['50', '49', '48', '47', '46', '45', '44', '43', '42', '41', '40', '39', '38', '37', '36', '35', '34', '33', '32', '31'], pkg_numbers)

    def test_package_search_p2(self):
        res = self.app.get(url_for(controller='package', action='search', q='groups:group_00', page=2))
        assert 'href="/dataset?q=groups%3Agroup_00&amp;page=1"' in res
        pkg_numbers = scrape_search_results(res, 'dataset')
        assert_equal(['30', '29', '28', '27', '26', '25', '24', '23', '22', '21', '20', '19', '18', '17', '16', '15', '14', '13', '12', '11'], pkg_numbers)

    def test_group_datasets_read_p1(self):
        res = self.app.get(url_for(controller='group', action='read', id='group_00'))
        assert 'href="/group/group_00?page=2' in res, res
        pkg_numbers = scrape_search_results(res, 'group_dataset')
        assert_equal(['50', '49', '48', '47', '46', '45', '44', '43', '42', '41', '40', '39', '38', '37', '36', '35', '34', '33', '32', '31'], pkg_numbers)

    def test_group_datasets_read_p2(self):
        res = self.app.get(url_for(controller='group', action='read', id='group_00', page=2))
        assert 'href="/group/group_00?page=1' in res, res
        pkg_numbers = scrape_search_results(res, 'group_dataset')
        assert_equal(['30', '29', '28', '27', '26', '25', '24', '23', '22', '21', '20', '19', '18', '17', '16', '15', '14', '13', '12', '11'], pkg_numbers)

class TestPaginationGroup(TestController):
    @classmethod
    def setup_class(cls):
        # no. entities per page is hardcoded into the controllers, so
        # create enough of each here so that we can test pagination
        cls.num_groups = 22

        # CS: nasty_string ignore
        groups = [u'group_%s' % str(i).zfill(2) for i in range(0, cls.num_groups)]

        CreateTestData.create_arbitrary(
            [], extra_group_names=groups
        )

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_group_index(self):
        res = self.app.get(url_for(controller='group', action='index'))
        assert 'href="/group?page=2"' in res, res
        grp_numbers = scrape_search_results(res, 'group')
        assert_equal(['00', '01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20'], grp_numbers)

        res = self.app.get(url_for(controller='group', action='index', page=2))
        assert 'href="/group?page=1"' in res
        grp_numbers = scrape_search_results(res, 'group')
        assert_equal(['21'], grp_numbers)

class TestPaginationUsers(TestController):
    @classmethod
    def setup_class(cls):
        # Delete default user as it appears in the first page of results
        model.User.by_name(u'logged_in').purge()
        model.repo.commit_and_remove()

        # no. entities per page is hardcoded into the controllers, so
        # create enough of each here so that we can test pagination
        cls.num_users = 21

        # CS: nasty_string ignore
        users = [u'user_%s' % str(i).zfill(2) for i in range(cls.num_users)]

        CreateTestData.create_arbitrary(
            [], extra_user_names = users,
        )

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_users_index(self):
        # allow for 2 extra users shown on user listing, 'logged_in' and 'visitor'
        res = self.app.get(url_for(controller='user', action='index'))
        assert 'href="/user?q=&amp;order_by=name&amp;page=2"' in res
        user_numbers = scrape_search_results(res, 'user')
        assert_equal(['00', '01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19'], user_numbers)

        res = self.app.get(url_for(controller='user', action='index', page=2))
        assert 'href="/user?q=&amp;order_by=name&amp;page=1"' in res
        user_numbers = scrape_search_results(res, 'user')
        assert_equal(['20'], user_numbers)

