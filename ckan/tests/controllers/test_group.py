# encoding: utf-8

from bs4 import BeautifulSoup
from nose.tools import assert_equal, assert_true, assert_in

from routes import url_for

import ckan.tests.helpers as helpers
import ckan.model as model
from ckan.tests import factories

webtest_submit = helpers.webtest_submit
submit_and_follow = helpers.submit_and_follow


class TestGroupController(helpers.FunctionalTestBase):

    def setup(self):
        model.repo.rebuild_db()

    def test_bulk_process_throws_404_for_nonexistent_org(self):
        app = self._get_test_app()
        bulk_process_url = url_for(controller='organization',
                                   action='bulk_process', id='does-not-exist')
        app.get(url=bulk_process_url, status=404)

    def test_page_thru_list_of_orgs_preserves_sort_order(self):
        orgs = [factories.Organization() for _ in range(35)]
        app = self._get_test_app()
        org_url = url_for(controller='organization',
                          action='index',
                          sort='name desc')
        response = app.get(url=org_url)
        assert orgs[-1]['name'] in response
        assert orgs[0]['name'] not in response

        response2 = response.click('2')
        assert orgs[-1]['name'] not in response2
        assert orgs[0]['name'] in response2

    def test_page_thru_list_of_groups_preserves_sort_order(self):
        groups = [factories.Group() for _ in range(35)]
        app = self._get_test_app()
        group_url = url_for(controller='group',
                            action='index',
                            sort='title desc')

        response = app.get(url=group_url)
        assert groups[-1]['title'] in response
        assert groups[0]['title'] not in response

        response2 = response.click(r'^2$')
        assert groups[-1]['title'] not in response2
        assert groups[0]['title'] in response2

    def test_invalid_sort_param_does_not_crash(self):
        app = self._get_test_app()
        group_url = url_for(controller='group',
                            action='index',
                            sort='title desc nope')

        app.get(url=group_url)

        group_url = url_for(controller='group',
                            action='index',
                            sort='title nope desc nope')

        app.get(url=group_url)


def _get_group_new_page(app):
    user = factories.User()
    env = {'REMOTE_USER': user['name'].encode('ascii')}
    response = app.get(
        url=url_for(controller='group', action='new'),
        extra_environ=env,
    )
    return env, response


class TestGroupControllerNew(helpers.FunctionalTestBase):
    def test_not_logged_in(self):
        app = self._get_test_app()
        app.get(url=url_for(controller='group', action='new'),
                status=403)

    def test_form_renders(self):
        app = self._get_test_app()
        env, response = _get_group_new_page(app)
        assert_in('group-edit', response.forms)

    def test_name_required(self):
        app = self._get_test_app()
        env, response = _get_group_new_page(app)
        form = response.forms['group-edit']

        response = webtest_submit(form, 'save', status=200, extra_environ=env)
        assert_true('group-edit' in response.forms)
        assert_true('Name: Missing value' in response)

    def test_saved(self):
        app = self._get_test_app()
        env, response = _get_group_new_page(app)
        form = response.forms['group-edit']
        form['name'] = u'saved'

        response = submit_and_follow(app, form, env, 'save')
        group = model.Group.by_name(u'saved')
        assert_equal(group.title, u'')
        assert_equal(group.type, 'group')
        assert_equal(group.state, 'active')

    def test_all_fields_saved(self):
        app = self._get_test_app()
        env, response = _get_group_new_page(app)
        form = response.forms['group-edit']
        form['name'] = u'all-fields-saved'
        form['title'] = 'Science'
        form['description'] = 'Sciencey datasets'
        form['image_url'] = 'http://example.com/image.png'

        response = submit_and_follow(app, form, env, 'save')
        group = model.Group.by_name(u'all-fields-saved')
        assert_equal(group.title, u'Science')
        assert_equal(group.description, 'Sciencey datasets')


def _get_group_edit_page(app, group_name=None):
    user = factories.User()
    if group_name is None:
        group = factories.Group(user=user)
        group_name = group['name']
    env = {'REMOTE_USER': user['name'].encode('ascii')}
    url = url_for(controller='group',
                  action='edit',
                  id=group_name)
    response = app.get(url=url, extra_environ=env)
    return env, response, group_name


class TestGroupControllerEdit(helpers.FunctionalTestBase):
    def test_not_logged_in(self):
        app = self._get_test_app()
        app.get(url=url_for(controller='group', action='new'),
                status=403)

    def test_group_doesnt_exist(self):
        app = self._get_test_app()
        user = factories.User()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        url = url_for(controller='group',
                      action='edit',
                      id='doesnt_exist')
        app.get(url=url, extra_environ=env,
                status=404)

    def test_form_renders(self):
        app = self._get_test_app()
        env, response, group_name = _get_group_edit_page(app)
        assert_in('group-edit', response.forms)

    def test_saved(self):
        app = self._get_test_app()
        env, response, group_name = _get_group_edit_page(app)
        form = response.forms['group-edit']

        response = submit_and_follow(app, form, env, 'save')
        group = model.Group.by_name(group_name)
        assert_equal(group.state, 'active')

    def test_all_fields_saved(self):
        app = self._get_test_app()
        env, response, group_name = _get_group_edit_page(app)
        form = response.forms['group-edit']
        form['name'] = u'all-fields-edited'
        form['title'] = 'Science'
        form['description'] = 'Sciencey datasets'
        form['image_url'] = 'http://example.com/image.png'

        response = submit_and_follow(app, form, env, 'save')
        group = model.Group.by_name(u'all-fields-edited')
        assert_equal(group.title, u'Science')
        assert_equal(group.description, 'Sciencey datasets')
        assert_equal(group.image_url, 'http://example.com/image.png')


class TestGroupRead(helpers.FunctionalTestBase):
    def setup(self):
        super(TestGroupRead, self).setup()
        self.app = helpers._get_test_app()
        self.user = factories.User()
        self.user_env = {'REMOTE_USER': self.user['name'].encode('ascii')}
        self.group = factories.Group(user=self.user)

    def test_group_read(self):
        response = self.app.get(url=url_for(controller='group',
                                            action='read',
                                            id=self.group['id']),
                                status=200,
                                extra_environ=self.user_env)
        assert_in(self.group['title'], response)
        assert_in(self.group['description'], response)


class TestGroupDelete(helpers.FunctionalTestBase):
    def setup(self):
        super(TestGroupDelete, self).setup()
        self.app = helpers._get_test_app()
        self.user = factories.User()
        self.user_env = {'REMOTE_USER': self.user['name'].encode('ascii')}
        self.group = factories.Group(user=self.user)

    def test_owner_delete(self):
        response = self.app.get(url=url_for(controller='group',
                                            action='delete',
                                            id=self.group['id']),
                                status=200,
                                extra_environ=self.user_env)

        form = response.forms['group-confirm-delete-form']
        response = submit_and_follow(self.app, form, name='delete',
                                     extra_environ=self.user_env)
        group = helpers.call_action('group_show',
                                    id=self.group['id'])
        assert_equal(group['state'], 'deleted')

    def test_sysadmin_delete(self):
        sysadmin = factories.Sysadmin()
        extra_environ = {'REMOTE_USER': sysadmin['name'].encode('ascii')}
        response = self.app.get(url=url_for(controller='group',
                                            action='delete',
                                            id=self.group['id']),
                                status=200,
                                extra_environ=extra_environ)

        form = response.forms['group-confirm-delete-form']
        response = submit_and_follow(self.app, form, name='delete',
                                     extra_environ=self.user_env)
        group = helpers.call_action('group_show',
                                    id=self.group['id'])
        assert_equal(group['state'], 'deleted')

    def test_non_authorized_user_trying_to_delete_fails(self):
        user = factories.User()
        extra_environ = {'REMOTE_USER': user['name'].encode('ascii')}
        self.app.get(url=url_for(controller='group',
                                 action='delete',
                                 id=self.group['id']),
                     status=403,
                     extra_environ=extra_environ)

        group = helpers.call_action('group_show',
                                    id=self.group['id'])
        assert_equal(group['state'], 'active')

    def test_anon_user_trying_to_delete_fails(self):
        self.app.get(url=url_for(controller='group',
                                 action='delete',
                                 id=self.group['id']),
                     status=403)

        group = helpers.call_action('group_show',
                                    id=self.group['id'])
        assert_equal(group['state'], 'active')


class TestGroupMembership(helpers.FunctionalTestBase):

    def _create_group(self, owner_username, users=None):
        '''Create a group with the owner defined by owner_username and
        optionally with a list of other users.'''
        if users is None:
            users = []
        context = {'user': owner_username, 'ignore_auth': True, }
        group = helpers.call_action('group_create', context=context,
                                    name='test-group', users=users)
        return group

    def _get_group_add_member_page(self, app, user, group_name):
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        url = url_for(controller='group',
                      action='member_new',
                      id=group_name)
        response = app.get(url=url, extra_environ=env)
        return env, response

    def test_membership_list(self):
        '''List group admins and members'''
        app = self._get_test_app()
        user_one = factories.User(fullname='User One', name='user-one')
        user_two = factories.User(fullname='User Two')

        other_users = [
            {'name': user_two['id'], 'capacity': 'member'}
        ]

        group = self._create_group(user_one['name'], other_users)

        env = {'REMOTE_USER': user_one['name'].encode('ascii')}

        member_list_url = url_for(controller='group', action='members',
                                  id=group['id'])
        member_list_response = app.get(
            member_list_url, extra_environ=env)

        assert_true('2 members' in member_list_response)

        member_response_html = BeautifulSoup(member_list_response.body)
        user_names = [u.string for u in
                      member_response_html.select('#member-table td.media a')]
        roles = [r.next_sibling.next_sibling.string
                 for r
                 in member_response_html.select('#member-table td.media')]

        user_roles = dict(zip(user_names, roles))

        assert_equal(user_roles['User One'], 'Admin')
        assert_equal(user_roles['User Two'], 'Member')

    def test_membership_add(self):
        '''Member can be added via add member page'''
        app = self._get_test_app()
        owner = factories.User(fullname='My Owner')
        factories.User(fullname="My Fullname", name='my-user')
        group = self._create_group(owner['name'])

        env, response = self._get_group_add_member_page(app,
                                                        owner,
                                                        group['name'])

        add_form = response.forms['add-member-form']
        add_form['username'] = 'my-user'
        add_response = submit_and_follow(app, add_form, env, 'save')

        assert_true('2 members' in add_response)

        add_response_html = BeautifulSoup(add_response.body)
        user_names = [u.string for u in
                      add_response_html.select('#member-table td.media a')]
        roles = [r.next_sibling.next_sibling.string
                 for r in add_response_html.select('#member-table td.media')]

        user_roles = dict(zip(user_names, roles))

        assert_equal(user_roles['My Owner'], 'Admin')
        assert_equal(user_roles['My Fullname'], 'Member')

    def test_admin_add(self):
        '''Admin can be added via add member page'''
        app = self._get_test_app()
        owner = factories.User(fullname='My Owner')
        factories.User(fullname="My Fullname", name='my-user')
        group = self._create_group(owner['name'])

        env, response = self._get_group_add_member_page(app,
                                                        owner,
                                                        group['name'])

        add_form = response.forms['add-member-form']
        add_form['username'] = 'my-user'
        add_form['role'] = 'admin'
        add_response = submit_and_follow(app, add_form, env, 'save')

        assert_true('2 members' in add_response)

        add_response_html = BeautifulSoup(add_response.body)
        user_names = [u.string for u in
                      add_response_html.select('#member-table td.media a')]
        roles = [r.next_sibling.next_sibling.string
                 for r in add_response_html.select('#member-table td.media')]

        user_roles = dict(zip(user_names, roles))

        assert_equal(user_roles['My Owner'], 'Admin')
        assert_equal(user_roles['My Fullname'], 'Admin')

    def test_remove_member(self):
        '''Member can be removed from group'''
        app = self._get_test_app()
        user_one = factories.User(fullname='User One', name='user-one')
        user_two = factories.User(fullname='User Two')

        other_users = [
            {'name': user_two['id'], 'capacity': 'member'}
        ]

        group = self._create_group(user_one['name'], other_users)

        remove_url = url_for(controller='group', action='member_delete',
                             user=user_two['id'], id=group['id'])

        env = {'REMOTE_USER': user_one['name'].encode('ascii')}
        remove_response = app.post(remove_url, extra_environ=env, status=302)
        # redirected to member list after removal
        remove_response = remove_response.follow(extra_environ=env)

        assert_true('Group member has been deleted.' in remove_response)
        assert_true('1 members' in remove_response)

        remove_response_html = BeautifulSoup(remove_response.body)
        user_names = [u.string for u in
                      remove_response_html.select('#member-table td.media a')]
        roles = [r.next_sibling.next_sibling.string
                 for r in
                 remove_response_html.select('#member-table td.media')]

        user_roles = dict(zip(user_names, roles))

        assert_equal(len(user_roles.keys()), 1)
        assert_equal(user_roles['User One'], 'Admin')

    def test_member_users_cannot_add_members(self):

        user = factories.User()
        group = factories.Group(
            users=[{'name': user['name'], 'capacity': 'member'}]
        )

        app = helpers._get_test_app()

        env = {'REMOTE_USER': user['name'].encode('ascii')}

        app.get(
            url_for(
                controller='group',
                action='member_new',
                id=group['id'],
            ),
            extra_environ=env,
            status=403,
        )

        app.post(
            url_for(
                controller='group',
                action='member_new',
                id=group['id'],
            ),
            {'id': 'test', 'username': 'test', 'save': 'save', 'role': 'test'},
            extra_environ=env,
            status=403,
        )

    def test_anonymous_users_cannot_add_members(self):
        group = factories.Group()

        app = helpers._get_test_app()

        app.get(
            url_for(
                controller='group',
                action='member_new',
                id=group['id'],
            ),
            status=403,
        )

        app.post(
            url_for(
                controller='group',
                action='member_new',
                id=group['id'],
            ),
            {'id': 'test', 'username': 'test', 'save': 'save', 'role': 'test'},
            status=403,
        )


class TestGroupFollow(helpers.FunctionalTestBase):

    def test_group_follow(self):
        app = self._get_test_app()

        user = factories.User()
        group = factories.Group()

        env = {'REMOTE_USER': user['name'].encode('ascii')}
        follow_url = url_for(controller='group',
                             action='follow',
                             id=group['id'])
        response = app.post(follow_url, extra_environ=env, status=302)
        response = response.follow()
        assert_true('You are now following {0}'
                    .format(group['display_name'])
                    in response)

    def test_group_follow_not_exist(self):
        '''Pass an id for a group that doesn't exist'''
        app = self._get_test_app()

        user_one = factories.User()

        env = {'REMOTE_USER': user_one['name'].encode('ascii')}
        follow_url = url_for(controller='group',
                             action='follow',
                             id='not-here')
        response = app.post(follow_url, extra_environ=env, status=404)
        assert_true('Group not found' in response)

    def test_group_unfollow(self):
        app = self._get_test_app()

        user_one = factories.User()
        group = factories.Group()

        env = {'REMOTE_USER': user_one['name'].encode('ascii')}
        follow_url = url_for(controller='group',
                             action='follow',
                             id=group['id'])
        app.post(follow_url, extra_environ=env, status=302)

        unfollow_url = url_for(controller='group', action='unfollow',
                               id=group['id'])
        unfollow_response = app.post(unfollow_url, extra_environ=env,
                                     status=302)
        unfollow_response = unfollow_response.follow()

        assert_true('You are no longer following {0}'
                    .format(group['display_name'])
                    in unfollow_response)

    def test_group_unfollow_not_following(self):
        '''Unfollow a group not currently following'''
        app = self._get_test_app()

        user_one = factories.User()
        group = factories.Group()

        env = {'REMOTE_USER': user_one['name'].encode('ascii')}
        unfollow_url = url_for(controller='group', action='unfollow',
                               id=group['id'])
        unfollow_response = app.post(unfollow_url, extra_environ=env,
                                     status=302)
        unfollow_response = unfollow_response.follow()

        assert_true('You are not following {0}'.format(group['id'])
                    in unfollow_response)

    def test_group_unfollow_not_exist(self):
        '''Unfollow a group that doesn't exist.'''
        app = self._get_test_app()

        user_one = factories.User()

        env = {'REMOTE_USER': user_one['name'].encode('ascii')}
        unfollow_url = url_for(controller='group', action='unfollow',
                               id='not-here')
        unfollow_response = app.post(unfollow_url, extra_environ=env,
                                     status=404)
        assert_true('Group not found' in unfollow_response)

    def test_group_follower_list(self):
        '''Following users appear on followers list page.'''
        app = self._get_test_app()

        user_one = factories.Sysadmin()
        group = factories.Group()

        env = {'REMOTE_USER': user_one['name'].encode('ascii')}
        follow_url = url_for(controller='group',
                             action='follow',
                             id=group['id'])
        app.post(follow_url, extra_environ=env, status=302)

        followers_url = url_for(controller='group', action='followers',
                                id=group['id'])

        # Only sysadmins can view the followers list pages
        followers_response = app.get(followers_url, extra_environ=env,
                                     status=200)
        assert_true(user_one['display_name'] in followers_response)


class TestGroupSearch(helpers.FunctionalTestBase):

    '''Test searching for groups.'''

    def setup(self):
        super(TestGroupSearch, self).setup()
        self.app = self._get_test_app()
        factories.Group(name='grp-one', title='AGrp One')
        factories.Group(name='grp-two', title='AGrp Two')
        factories.Group(name='grp-three', title='Grp Three')
        self.search_url = url_for(controller='group', action='index')

    def test_group_search(self):
        '''Requesting group search (index) returns list of groups and search
        form.'''

        index_response = self.app.get(self.search_url)
        index_response_html = BeautifulSoup(index_response.body)
        grp_names = index_response_html.select('ul.media-grid '
                                               'li.media-item '
                                               'h3.media-heading')
        grp_names = [n.string for n in grp_names]

        assert_equal(len(grp_names), 3)
        assert_true('AGrp One' in grp_names)
        assert_true('AGrp Two' in grp_names)
        assert_true('Grp Three' in grp_names)

    def test_group_search_results(self):
        '''Searching via group search form returns list of expected groups.'''

        index_response = self.app.get(self.search_url)
        search_form = index_response.forms['group-search-form']
        search_form['q'] = 'AGrp'
        search_response = webtest_submit(search_form)

        search_response_html = BeautifulSoup(search_response.body)
        grp_names = search_response_html.select('ul.media-grid '
                                                'li.media-item '
                                                'h3.media-heading')
        grp_names = [n.string for n in grp_names]

        assert_equal(len(grp_names), 2)
        assert_true('AGrp One' in grp_names)
        assert_true('AGrp Two' in grp_names)
        assert_true('Grp Three' not in grp_names)

    def test_group_search_no_results(self):
        '''Searching with a term that doesn't apply returns no results.'''

        index_response = self.app.get(self.search_url)
        search_form = index_response.forms['group-search-form']
        search_form['q'] = 'No Results Here'
        search_response = webtest_submit(search_form)

        search_response_html = BeautifulSoup(search_response.body)
        grp_names = search_response_html.select('ul.media-grid '
                                                'li.media-item '
                                                'h3.media-heading')
        grp_names = [n.string for n in grp_names]

        assert_equal(len(grp_names), 0)
        assert_true("No groups found for &#34;No Results Here&#34;"
                    in search_response)


class TestGroupInnerSearch(helpers.FunctionalTestBase):

    '''Test searching within an group.'''

    def test_group_search_within_org(self):
        '''Group read page request returns list of datasets owned by group.'''
        app = self._get_test_app()

        grp = factories.Group()
        factories.Dataset(name="ds-one", title="Dataset One",
                          groups=[{'id': grp['id']}])
        factories.Dataset(name="ds-two", title="Dataset Two",
                          groups=[{'id': grp['id']}])
        factories.Dataset(name="ds-three", title="Dataset Three",
                          groups=[{'id': grp['id']}])

        grp_url = url_for(controller='group', action='read',
                          id=grp['id'])
        grp_response = app.get(grp_url)
        grp_response_html = BeautifulSoup(grp_response.body)

        ds_titles = grp_response_html.select('.dataset-list '
                                             '.dataset-item '
                                             '.dataset-heading a')
        ds_titles = [t.string for t in ds_titles]

        assert_true('3 datasets found' in grp_response)
        assert_equal(len(ds_titles), 3)
        assert_true('Dataset One' in ds_titles)
        assert_true('Dataset Two' in ds_titles)
        assert_true('Dataset Three' in ds_titles)

    def test_group_search_within_org_results(self):
        '''Searching within an group returns expected dataset results.'''
        app = self._get_test_app()

        grp = factories.Group()
        factories.Dataset(name="ds-one", title="Dataset One",
                          groups=[{'id': grp['id']}])
        factories.Dataset(name="ds-two", title="Dataset Two",
                          groups=[{'id': grp['id']}])
        factories.Dataset(name="ds-three", title="Dataset Three",
                          groups=[{'id': grp['id']}])

        grp_url = url_for(controller='group', action='read',
                          id=grp['id'])
        grp_response = app.get(grp_url)
        search_form = grp_response.forms['group-datasets-search-form']
        search_form['q'] = 'One'
        search_response = webtest_submit(search_form)
        assert_true('1 dataset found for &#34;One&#34;' in search_response)

        search_response_html = BeautifulSoup(search_response.body)

        ds_titles = search_response_html.select('.dataset-list '
                                                '.dataset-item '
                                                '.dataset-heading a')
        ds_titles = [t.string for t in ds_titles]

        assert_equal(len(ds_titles), 1)
        assert_true('Dataset One' in ds_titles)
        assert_true('Dataset Two' not in ds_titles)
        assert_true('Dataset Three' not in ds_titles)

    def test_group_search_within_org_no_results(self):
        '''Searching for non-returning phrase within an group returns no
        results.'''
        app = self._get_test_app()

        grp = factories.Group()
        factories.Dataset(name="ds-one", title="Dataset One",
                          groups=[{'id': grp['id']}])
        factories.Dataset(name="ds-two", title="Dataset Two",
                          groups=[{'id': grp['id']}])
        factories.Dataset(name="ds-three", title="Dataset Three",
                          groups=[{'id': grp['id']}])

        grp_url = url_for(controller='group', action='read',
                          id=grp['id'])
        grp_response = app.get(grp_url)
        search_form = grp_response.forms['group-datasets-search-form']
        search_form['q'] = 'Nout'
        search_response = webtest_submit(search_form)

        assert_true('No datasets found for &#34;Nout&#34;' in search_response)

        search_response_html = BeautifulSoup(search_response.body)

        ds_titles = search_response_html.select('.dataset-list '
                                                '.dataset-item '
                                                '.dataset-heading a')
        ds_titles = [t.string for t in ds_titles]

        assert_equal(len(ds_titles), 0)


class TestGroupIndex(helpers.FunctionalTestBase):

    def test_group_index(self):
        app = self._get_test_app()

        for i in xrange(1, 26):
            _i = '0' + str(i) if i < 10 else i
            factories.Group(
                name='test-group-{0}'.format(_i),
                title='Test Group {0}'.format(_i))

        url = url_for(controller='group',
                      action='index')
        response = app.get(url)

        for i in xrange(1, 22):
            _i = '0' + str(i) if i < 10 else i
            assert_in('Test Group {0}'.format(_i), response)

        assert 'Test Group 22' not in response

        url = url_for(controller='group',
                      action='index',
                      page=1)
        response = app.get(url)

        for i in xrange(1, 22):
            _i = '0' + str(i) if i < 10 else i
            assert_in('Test Group {0}'.format(_i), response)

        assert 'Test Group 22' not in response

        url = url_for(controller='group',
                      action='index',
                      page=2)
        response = app.get(url)

        for i in xrange(22, 26):
            assert_in('Test Group {0}'.format(i), response)

        assert 'Test Group 21' not in response
