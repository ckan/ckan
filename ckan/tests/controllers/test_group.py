from nose.tools import assert_equal, assert_true

from routes import url_for

import ckan.tests.helpers as helpers
import ckan.model as model
from ckan.tests import factories

assert_in = helpers.assert_in
webtest_submit = helpers.webtest_submit
submit_and_follow = helpers.submit_and_follow


class TestGroupController(helpers.FunctionalTestBase):

    def setup(self):
        model.repo.rebuild_db()

    def test_bulk_process_throws_404_for_nonexistent_org(self):
        app = self._get_test_app()
        bulk_process_url = url_for(controller='organization',
                                   action='bulk_process', id='does-not-exist')
        response = app.get(url=bulk_process_url, status=404)

    def test_page_thru_list_of_orgs(self):
        orgs = [factories.Organization() for i in range(35)]
        app = self._get_test_app()
        org_url = url_for(controller='organization', action='index')
        response = app.get(url=org_url)
        assert orgs[0]['name'] in response
        assert orgs[-1]['name'] not in response

        response2 = response.click('2')
        assert orgs[0]['name'] not in response2
        assert orgs[-1]['name'] in response2


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
                status=302)

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
                status=302)

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
