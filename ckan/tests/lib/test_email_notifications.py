import json

import ckan.model as model
import ckan.tests.mock_mail_server as mock_mail_server
import ckan.lib.email_notifications as email_notifications
import ckan.tests
import ckan.tests.pylons_controller

import paste
import pylons.test


class TestEmailNotifications(mock_mail_server.SmtpServerHarness,
        ckan.tests.pylons_controller.PylonsTestCase):

    @classmethod
    def setup_class(cls):
        mock_mail_server.SmtpServerHarness.setup_class()
        ckan.tests.pylons_controller.PylonsTestCase.setup_class()
        ckan.tests.CreateTestData.create()
        cls.app = paste.fixture.TestApp(pylons.test.pylonsapp)
        joeadmin = model.User.get('joeadmin')
        cls.joeadmin = {'id': joeadmin.id,
                'apikey': joeadmin.apikey,
                }

    @classmethod
    def teardown_class(self):
        mock_mail_server.SmtpServerHarness.teardown_class()
        ckan.tests.pylons_controller.PylonsTestCase.teardown_class()
        model.repo.rebuild_db()

    def test_01_no_email_notifications_after_registration(self):
        '''Test that a newly registered user who is not following anything
        doesn't get any email notifications.'''

        # Clear any emails already sent due to CreateTestData.create().
        email_notifications.get_and_send_notifications_for_all_users()
        self.clear_smtp_messages()

        # Register a new user.
        params = {'name': 'sara',
                'email': 'sara@sararollins.com',
                'password': 'sara',
                'fullname': 'Sara Rollins',
                }
        extra_environ = {'Authorization': str(self.joeadmin['apikey'])}
        response = self.app.post('/api/action/user_create',
            params=json.dumps(params), extra_environ=extra_environ).json
        assert response['success'] is True

        # Save the user for later tests to use.
        TestEmailNotifications.user = response['result']

        # No notification emails should be sent to anyone at this point.
        email_notifications.get_and_send_notifications_for_all_users()
        assert len(self.get_smtp_messages()) == 0

    def test_02_fuck_yeah_email_notifications(self):

        # You have to follow something or you don't get any emails.
        params = {'id': 'warandpeace'}
        extra_environ = {'Authorization': str(self.user['apikey'])}
        response = self.app.post('/api/action/follow_dataset',
            params=json.dumps(params), extra_environ=extra_environ).json
        assert response['success'] is True

        # Make someone else update the dataset we're following to create an
        # email notification.
        params = {'name': 'warandpeace', 'notes': 'updated'}
        extra_environ = {'Authorization': str(self.joeadmin['apikey'])}
        response = self.app.post('/api/action/package_update',
            params=json.dumps(params), extra_environ=extra_environ).json
        assert response['success'] is True

        # One notification email should be sent to anyone at this point.
        email_notifications.get_and_send_notifications_for_all_users()
        assert len(self.get_smtp_messages()) == 1
