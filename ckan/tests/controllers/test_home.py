# encoding: utf-8

from nose.tools import eq_
from ckan.lib.helpers import url_for
from bs4 import BeautifulSoup

from ckan.tests import factories
import ckan.tests.helpers as helpers


class TestHome(helpers.FunctionalTestBase):

    def test_home_renders(self):
        app = self._get_test_app()
        response = app.get(url_for('home'))
        assert 'Welcome to CKAN' in response.body

    def test_template_head_end(self):
        app = self._get_test_app()
        # test-core.ini sets ckan.template_head_end to this:
        test_link = '<link rel="stylesheet" ' \
            'href="TEST_TEMPLATE_HEAD_END.css" type="text/css">'
        response = app.get(url_for('home'))
        assert test_link in response.body

    def test_template_footer_end(self):
        app = self._get_test_app()
        # test-core.ini sets ckan.template_footer_end to this:
        test_html = '<strong>TEST TEMPLATE_FOOTER_END TEST</strong>'
        response = app.get(url_for('home'))
        assert test_html in response.body

    def test_email_address_nag(self):
        # before CKAN 1.6, users were allowed to have no email addresses
        app = self._get_test_app()
        # can't use factory to create user as without email it fails validation
        from ckan import model
        model.repo.new_revision()
        user = model.user.User(name='has-no-email')
        model.Session.add(user)
        model.Session.commit()
        env = {'REMOTE_USER': user.name.encode('ascii')}

        response = app.get(url=url_for('home'), extra_environ=env)

        assert 'update your profile' in response.body
        assert url_for(controller='user', action='edit') in response.body
        assert ' and add your email address.' in response.body

    def test_email_address_no_nag(self):
        app = self._get_test_app()
        user = factories.User(email='filled_in@nicely.com')
        env = {'REMOTE_USER': user['name'].encode('ascii')}

        response = app.get(url=url_for('home'), extra_environ=env)

        assert 'add your email address' not in response


class TestI18nURLs(helpers.FunctionalTestBase):

    def test_right_urls_are_rendered_on_language_selector(self):
        app = self._get_test_app()
        response = app.get(url_for('home'))
        html = BeautifulSoup(response.body)

        select = html.find(id='field-lang-select')
        for option in select.find_all('option'):
            if option.text.strip() == u'English':
                eq_(option['value'], '/en/')
            elif option.text.strip() == u'čeština (Česká republika)':
                eq_(option['value'], '/cs_CZ/')
            elif option.text.strip() == u'português (Brasil)':
                eq_(option['value'], '/pt_BR/')
            elif option.text.strip() == u'srpski (latinica)':
                eq_(option['value'], '/sr_Latn/')

    def test_default_english_option_is_selected_on_language_selector(self):
        app = self._get_test_app()
        response = app.get(url_for('home'))
        html = BeautifulSoup(response.body)

        select = html.find(id='field-lang-select')
        for option in select.find_all('option'):
            if option['value'] == '/en/':
                eq_(option['selected'], 'selected')
            else:
                assert not option.has_attr('selected')

    def test_right_option_is_selected_on_language_selector(self):
        app = self._get_test_app()
        response = app.get(url_for('home', locale='ca'))
        html = BeautifulSoup(response.body)

        select = html.find(id='field-lang-select')
        for option in select.find_all('option'):
            if option['value'] == '/ca/':
                eq_(option['selected'], 'selected')
            else:
                assert not option.has_attr('selected')
