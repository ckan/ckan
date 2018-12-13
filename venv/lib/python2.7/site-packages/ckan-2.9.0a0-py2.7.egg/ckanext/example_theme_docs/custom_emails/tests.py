# encoding: utf-8

import os
from ckan import plugins
import ckan.model as model
import ckan.lib.mailer as mailer
from ckan.tests import factories
from ckan.lib.base import render_jinja2
from ckan.common import config

from ckan.tests.lib.test_mailer import MailerBase
import ckan.tests.helpers as helpers

from nose.tools import assert_equal, assert_in


class TestExampleCustomEmailsPlugin(MailerBase):
    @classmethod
    def setup_class(cls):
        super(TestExampleCustomEmailsPlugin, cls).setup_class()
        if not plugins.plugin_loaded('example_theme_custom_emails'):
            plugins.load('example_theme_custom_emails')

    @classmethod
    def teardown_class(cls):
        super(TestExampleCustomEmailsPlugin, cls).teardown_class()
        plugins.unload('example_theme_custom_emails')

    def _get_template_content(self, name):

        templates_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'templates', 'emails')
        with open(os.path.join(templates_path, name), 'r') as f:
            return f.read()

    def test_reset_password_custom_subject(self):
        user = factories.User()
        user_obj = model.User.by_name(user['name'])

        mailer.send_reset_link(user_obj)

        # check it went to the mock smtp server
        msgs = self.get_smtp_messages()
        assert_equal(len(msgs), 1)
        msg = msgs[0]
        extra_vars = {
            'site_title': config.get('ckan.site_title')
        }
        expected = render_jinja2('emails/reset_password_subject.txt',
                                 extra_vars)
        expected = expected.split('\n')[0]

        subject = self.get_email_subject(msg[3])
        assert_equal(expected, subject)
        assert_in('**test**', subject)

    def test_reset_password_custom_body(self):
        user = factories.User()
        user_obj = model.User.by_name(user['name'])

        mailer.send_reset_link(user_obj)

        # check it went to the mock smtp server
        msgs = self.get_smtp_messages()
        assert_equal(len(msgs), 1)
        msg = msgs[0]
        extra_vars = {
            'reset_link': mailer.get_reset_link(user_obj)
        }
        expected = render_jinja2('emails/reset_password.txt',
                                 extra_vars)
        body = self.get_email_body(msg[3])
        assert_equal(expected, body)
        assert_in('**test**', body)

    def test_invite_user_custom_subject(self):
        user = factories.User()
        user_obj = model.User.by_name(user['name'])

        mailer.send_invite(user_obj)

        # check it went to the mock smtp server
        msgs = self.get_smtp_messages()
        assert_equal(len(msgs), 1)
        msg = msgs[0]
        extra_vars = {
            'site_title': config.get('ckan.site_title'),
        }
        expected = render_jinja2('emails/invite_user_subject.txt',
                                 extra_vars)
        expected = expected.split('\n')[0]

        subject = self.get_email_subject(msg[3])
        assert_equal(expected, subject)
        assert_in('**test**', subject)

    def test_invite_user_custom_body(self):
        user = factories.User()
        user_obj = model.User.by_name(user['name'])

        mailer.send_invite(user_obj)

        # check it went to the mock smtp server
        msgs = self.get_smtp_messages()
        assert_equal(len(msgs), 1)
        msg = msgs[0]
        extra_vars = {
            'reset_link': mailer.get_reset_link(user_obj),
            'user_name': user['name'],
            'site_title': config.get('ckan.site_title'),
        }
        expected = render_jinja2('emails/invite_user.txt',
                                 extra_vars)
        body = self.get_email_body(msg[3])
        assert_equal(expected, body)
        assert_in('**test**', body)
