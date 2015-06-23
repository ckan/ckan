from nose.tools import assert_true, assert_equal

from bs4 import BeautifulSoup
from routes import url_for

import ckan.tests.helpers as helpers
import ckan.tests.factories as factories


submit_and_follow = helpers.submit_and_follow
webtest_submit = helpers.webtest_submit


def _get_admin_config_page(app):
    user = factories.Sysadmin()
    env = {'REMOTE_USER': user['name'].encode('ascii')}
    response = app.get(
        url=url_for(controller='admin', action='config'),
        extra_environ=env,
    )
    return env, response


class TestConfig(helpers.FunctionalTestBase):
    '''View tests to go along with 'Customizing look and feel' docs.'''

    def _reset_config(self):
        '''Reset config via action'''
        app = self._get_test_app()
        user = factories.Sysadmin()
        env = {'REMOTE_USER': user['name'].encode('ascii')}
        app.get(
            url=url_for(controller='admin', action='reset_config'),
            extra_environ=env,
        )

    def teardown(self):
        '''Make sure the config is reset after tests'''
        self._reset_config()
        helpers.reset_db()

    def test_form_renders(self):
        '''admin-config-form in the response'''
        app = self._get_test_app()
        env, response = _get_admin_config_page(app)
        assert_true('admin-config-form' in response.forms)

    def test_site_title(self):
        '''Configure the site title'''
        # current site title
        app = self._get_test_app()

        index_response = app.get('/')
        assert_true('Welcome - CKAN' in index_response)

        # change site title
        env, config_response = _get_admin_config_page(app)
        config_form = config_response.forms['admin-config-form']
        config_form['ckan.site_title'] = 'Test Site Title'
        webtest_submit(config_form, 'save', status=302, extra_environ=env)

        # new site title
        new_index_response = app.get('/')
        assert_true('Welcome - Test Site Title' in new_index_response)

    def test_main_css_list(self):
        '''Style list contains pre-configured styles'''

        STYLE_NAMES = [
            'Default',
            'Red',
            'Green',
            'Maroon',
            'Fuchsia'
        ]

        app = self._get_test_app()

        env, config_response = _get_admin_config_page(app)
        config_response_html = BeautifulSoup(config_response.body)
        style_select_options = \
            config_response_html.select('#field-ckan-main-css option')
        for option in style_select_options:
            assert_true(option.string in STYLE_NAMES)

    def test_main_css(self):
        '''Select a colour style'''
        app = self._get_test_app()

        # current style
        index_response = app.get('/')
        assert_true('main.css' in index_response)

        # set new style css
        env, config_response = _get_admin_config_page(app)
        config_form = config_response.forms['admin-config-form']
        config_form['ckan.main_css'] = '/base/css/red.css'
        webtest_submit(config_form, 'save', status=302, extra_environ=env)

        # new style
        new_index_response = app.get('/')
        assert_true('red.css' in new_index_response)
        assert_true('main.css' not in new_index_response)

    def test_tag_line(self):
        '''Add a tag line (only when no logo)'''
        app = self._get_test_app()

        # current tagline
        index_response = app.get('/')
        assert_true('Special Tagline' not in index_response)

        # set new tagline css
        env, config_response = _get_admin_config_page(app)
        config_form = config_response.forms['admin-config-form']
        config_form['ckan.site_description'] = 'Special Tagline'
        webtest_submit(config_form, 'save', status=302, extra_environ=env)

        # new tagline not visible yet
        new_index_response = app.get('/')
        assert_true('Special Tagline' not in new_index_response)

        # remove logo
        env, config_response = _get_admin_config_page(app)
        config_form = config_response.forms['admin-config-form']
        config_form['ckan.site_logo'] = ''
        webtest_submit(config_form, 'save', status=302, extra_environ=env)

        # new tagline
        new_index_response = app.get('/')
        assert_true('Special Tagline' in new_index_response)

    def test_about(self):
        '''Add some About tag text'''
        app = self._get_test_app()

        # current about
        about_response = app.get('/about')
        assert_true('My special about text' not in about_response)

        # set new about
        env, config_response = _get_admin_config_page(app)
        config_form = config_response.forms['admin-config-form']
        config_form['ckan.site_about'] = 'My special about text'
        webtest_submit(config_form, 'save', status=302, extra_environ=env)

        # new about
        new_about_response = app.get('/about')
        assert_true('My special about text' in new_about_response)

    def test_intro(self):
        '''Add some Intro tag text'''
        app = self._get_test_app()

        # current intro
        intro_response = app.get('/')
        assert_true('My special intro text' not in intro_response)

        # set new intro
        env, config_response = _get_admin_config_page(app)
        config_form = config_response.forms['admin-config-form']
        config_form['ckan.site_intro_text'] = 'My special intro text'
        webtest_submit(config_form, 'save', status=302, extra_environ=env)

        # new intro
        new_intro_response = app.get('/')
        assert_true('My special intro text' in new_intro_response)

    def test_custom_css(self):
        '''Add some custom css to the head element'''
        app = self._get_test_app()

        # current tagline
        intro_response_html = BeautifulSoup(app.get('/').body)
        style_tag = intro_response_html.select('head style')
        assert_equal(len(style_tag), 0)

        # set new tagline css
        env, config_response = _get_admin_config_page(app)
        config_form = config_response.forms['admin-config-form']
        config_form['ckan.site_custom_css'] = 'body {background-color:red}'
        webtest_submit(config_form, 'save', status=302, extra_environ=env)

        # new tagline not visible yet
        new_intro_response_html = BeautifulSoup(app.get('/').body)
        style_tag = new_intro_response_html.select('head style')
        assert_equal(len(style_tag), 1)
        assert_equal(style_tag[0].text.strip(), 'body {background-color:red}')

    def test_homepage_style(self):
        '''Select a homepage style'''
        app = self._get_test_app()

        # current style
        index_response = app.get('/')
        assert_true('<!-- Snippet home/layout1.html start -->'
                    in index_response)

        # set new style css
        env, config_response = _get_admin_config_page(app)
        config_form = config_response.forms['admin-config-form']
        config_form['ckan.homepage_style'] = '2'
        webtest_submit(config_form, 'save', status=302, extra_environ=env)

        # new style
        new_index_response = app.get('/')
        assert_true('<!-- Snippet home/layout1.html start -->'
                    not in new_index_response)
        assert_true('<!-- Snippet home/layout2.html start -->'
                    in new_index_response)
