import json
import email.mime.text

import ckan.model as model
import ckan.lib.email_notifications as email_notifications
import ckan.lib.base
import ckan.lib.mailer
import ckan.tests.pylons_controller
import ckan.tests.mock_mail_server as mock_mail_server

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

    def mime_encode(self, msg, recipient_name):
        sender_name = ckan.lib.base.g.site_title
        sender_url = ckan.lib.base.g.site_url
        body = ckan.lib.mailer.add_msg_niceties(
                recipient_name, msg, sender_name, sender_url)
        encoded_body = email.mime.text.MIMEText(
                body.encode('utf-8'), 'plain', 'utf-8').get_payload().strip()
        return encoded_body

    def check_email(self, email, address, name, subject, body):
        assert email[1] == 'info@test.ckan.net'
        assert email[2] == [address]
        encoded_subject = 'Subject: =?utf-8?q?{subject}'.format(
                subject=subject.replace(' ', '_'))
        assert encoded_subject in email[3]
        encoded_body = self.mime_encode(body, name)
        assert encoded_body in email[3]
        # TODO: Check that body contains link to dashboard and email prefs.

    def test_01_no_email_notifications_after_registration(self):
        '''A new user who isn't following anything shouldn't get any emails.'''

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
        TestEmailNotifications.sara = response['result']

        # No notification emails should be sent to anyone at this point.
        email_notifications.get_and_send_notifications_for_all_users()
        assert len(self.get_smtp_messages()) == 0

    def test_02_one_new_activity(self):
        '''A user with one new activity should get one email.'''

        # Make Sara follow something, have to do this to get new activity.
        params = {'id': 'warandpeace'}
        extra_environ = {'Authorization': str(self.sara['apikey'])}
        response = self.app.post('/api/action/follow_dataset',
            params=json.dumps(params), extra_environ=extra_environ).json
        assert response['success'] is True

        # Make someone else update the dataset Sara's following, this should
        # create a new activity on Sara's dashboard.
        params = {'name': 'warandpeace', 'notes': 'updated'}
        extra_environ = {'Authorization': str(self.joeadmin['apikey'])}
        response = self.app.post('/api/action/package_update',
            params=json.dumps(params), extra_environ=extra_environ).json
        assert response['success'] is True

        # Run the email notifier job, it should send one notification email
        # to Sara.
        email_notifications.get_and_send_notifications_for_all_users()
        assert len(self.get_smtp_messages()) == 1
        email = self.get_smtp_messages()[0]
        self.check_email(email, 'sara@sararollins.com', 'Sara Rollins',
                'You have new activity', 'You have new activity')

        self.clear_smtp_messages()

    def test_03_multiple_new_activities(self):
        '''Test that a user with multiple new activities gets just one email.

        '''
        # Make someone else update the dataset Sara's following three times,
        # this should create three new activities on Sara's dashboard.
        for i in range(1, 4):
            params = {'name': 'warandpeace',
                    'notes': 'updated {0} times'.format(i)}
            extra_environ = {'Authorization': str(self.joeadmin['apikey'])}
            response = self.app.post('/api/action/package_update',
                params=json.dumps(params), extra_environ=extra_environ).json
            assert response['success'] is True

        # Run the email notifier job, it should send one notification email
        # to Sara.
        email_notifications.get_and_send_notifications_for_all_users()
        assert len(self.get_smtp_messages()) == 1
        email = self.get_smtp_messages()[0]
        self.check_email(email, 'sara@sararollins.com', 'Sara Rollins',
                'You have new activity', 'You have new activity')

        self.clear_smtp_messages()

    def test_04_no_repeat_email_notifications(self):
        '''Test that a user does not get a second email notification for the
        same new activity.

        '''
        # TODO: Assert that Sara has some new activities and has already had
        # an email about them.
        email_notifications.get_and_send_notifications_for_all_users()
        assert len(self.get_smtp_messages()) == 0

    def test_05_no_email_notifications_when_disabled_site_wide(self):
        '''Users should not get email notifications when the feature is
        disabled site-wide by a sysadmin.'''

    def test_06_enable_email_notifications_sitewide(self):
        '''When a sysadamin enables email notifications site wide, users
        should not get emails for new activities from before email
        notifications were enabled.

        '''

    def test_07_no_email_notifications_when_disabled_by_user(self):
        '''Users should not get email notifications when they have disabled
        the feature in their user preferences.'''

    def test_08_enable_email_notifications_by_user(self):
        '''When a user enables email notifications in her user preferences,
        she should not get emails for new activities from before email
        notifications were enabled.

        '''
