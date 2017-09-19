# encoding: utf-8

import mock

import ckan.model as model
import ckan.lib.search as search

from ckan.lib.create_test_data import CreateTestData
from ckan.logic import get_action
from ckan.tests.legacy import *
from base import FunctionalTestCase


class TestGroup(FunctionalTestCase):

    @classmethod
    def setup_class(self):
        search.clear_all()
        model.Session.remove()
        CreateTestData.create()

    @classmethod
    def teardown_class(self):
        model.repo.rebuild_db()

    def test_sorting(self):
        model.repo.rebuild_db()

        testsysadmin = model.User(name=u'testsysadmin')
        testsysadmin.sysadmin = True
        model.Session.add(testsysadmin)

        pkg1 = model.Package(name="pkg1")
        pkg2 = model.Package(name="pkg2")
        model.Session.add(pkg1)
        model.Session.add(pkg2)

        CreateTestData.create_groups([{'name': "alpha",
                                       'title': "Alpha",
                                       'packages': []},
                                      {'name': "beta",
                                       'title': "Beta",
                                       'packages': ["pkg1", "pkg2"]},
                                      {'name': "delta",
                                       'title': 'Delta',
                                       'packages': ["pkg1"]},
                                      {'name': "gamma",
                                       'title': "Gamma",
                                       'packages': []}],
                                     admin_user_name='testsysadmin')

        context = {'model': model, 'session': model.Session,
                   'user': 'testsysadmin', 'for_view': True,
                   'with_private': False}
        data_dict = {'all_fields': True}
        results = get_action('group_list')(context, data_dict)
        assert results[0]['name'] == u'alpha', results[0]['name']
        assert results[-1]['name'] == u'gamma', results[-1]['name']

        # Test title forward
        data_dict = {'all_fields': True, 'sort': 'title asc'}
        results = get_action('group_list')(context, data_dict)
        assert results[0]['name'] == u'alpha', results[0]['name']
        assert results[-1]['name'] == u'gamma', results[-1]['name']

        # Test title reverse
        data_dict = {'all_fields': True, 'sort': 'title desc'}
        results = get_action('group_list')(context, data_dict)
        assert results[0]['name'] == u'gamma', results[0]['name']
        assert results[-1]['name'] == u'alpha', results[-1]['name']

        # Test name reverse
        data_dict = {'all_fields': True, 'sort': 'name desc'}
        results = get_action('group_list')(context, data_dict)
        assert results[0]['name'] == u'gamma', results[0]['name']
        assert results[-1]['name'] == u'alpha', results[-1]['name']

        # Test packages reversed
        data_dict = {'all_fields': True, 'sort': 'package_count desc'}
        results = get_action('group_list')(context, data_dict)
        assert results[0]['name'] == u'beta', results[0]['name']
        assert results[1]['name'] == u'delta', results[1]['name']

        # Test packages forward
        data_dict = {'all_fields': True, 'sort': 'package_count asc'}
        results = get_action('group_list')(context, data_dict)
        assert results[-2]['name'] == u'delta', results[-2]['name']
        assert results[-1]['name'] == u'beta', results[-1]['name']

        # Default ordering for packages
        data_dict = {'all_fields': True, 'sort': 'package_count'}
        results = get_action('group_list')(context, data_dict)
        assert results[0]['name'] == u'beta', results[0]['name']
        assert results[1]['name'] == u'delta', results[1]['name']

    def test_read_non_existent(self):
        name = u'group_does_not_exist'
        offset = url_for(controller='group', action='read', id=name)
        res = self.app.get(offset, status=404)


class TestRevisions(FunctionalTestCase):
    @classmethod
    def setup_class(self):
        model.Session.remove()
        CreateTestData.create()
        self.name = u'revisiontest1'

        # create pkg
        self.description = [u'Written by Puccini', u'Written by Rossini',
                            u'Not written at all', u'Written again',
                            u'Written off']
        rev = model.repo.new_revision()
        self.grp = model.Group(name=self.name)
        self.grp.description = self.description[0]
        model.Session.add(self.grp)
        model.repo.commit_and_remove()

        # edit pkg
        for i in range(5)[1:]:
            rev = model.repo.new_revision()
            grp = model.Group.by_name(self.name)
            grp.description = self.description[i]
            model.repo.commit_and_remove()

        self.grp = model.Group.by_name(self.name)

    @classmethod
    def teardown_class(self):
        self.purge_packages([self.name])
        model.repo.rebuild_db()

    def test_2_atom_feed(self):
        offset = url_for(controller='group', action='history',
                         id=self.grp.name)
        offset = "%s?format=atom" % offset
        res = self.app.get(offset)
        assert '<feed' in res, res
        assert 'xmlns="http://www.w3.org/2005/Atom"' in res, res
        assert '</feed>' in res, res


class TestMemberInvite(FunctionalTestCase):
    @classmethod
    def setup_class(self):
        model.Session.remove()
        model.repo.rebuild_db()

    def teardown(self):
        model.repo.rebuild_db()

    @mock.patch('ckan.lib.mailer.mail_user')
    def test_member_new_invites_user_if_received_email(self, mail_user):
        user = CreateTestData.create_user('a_user', sysadmin=True)
        group_name = 'a_group'
        CreateTestData.create_groups([{'name': group_name}], user.name)
        group = model.Group.get(group_name)
        url = url_for(controller='group', action='member_new', id=group.id)
        email = 'invited_user@mailinator.com'
        role = 'member'

        params = {'email': email, 'role': role}
        res = self.app.post(url, params,
                            extra_environ={'REMOTE_USER': str(user.name)})

        users = model.User.by_email(email)
        assert len(users) == 1, users
        user = users[0]
        assert user.email == email, user
        assert group.id in user.get_group_ids(capacity=role)
