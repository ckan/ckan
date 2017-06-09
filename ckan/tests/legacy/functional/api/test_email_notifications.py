# encoding: utf-8

import time

import ckan.model as model
import ckan.lib.base
import ckan.lib.mailer
import ckan.tests.legacy as tests
import ckan.tests.legacy.mock_mail_server as mock_mail_server
import ckan.tests.legacy.pylons_controller as pylons_controller
import ckan.config.middleware

import paste
import paste.deploy
import pylons.test

from ckan.common import config


class TestEmailNotifications(mock_mail_server.SmtpServerHarness,
        pylons_controller.PylonsTestCase):

    @classmethod
    def setup_class(cls):
        mock_mail_server.SmtpServerHarness.setup_class()
        pylons_controller.PylonsTestCase.setup_class()
        tests.CreateTestData.create()
        cls.app = paste.fixture.TestApp(pylons.test.pylonsapp)
        joeadmin = model.User.get('joeadmin')
        cls.joeadmin = {'id': joeadmin.id,
                'apikey': joeadmin.apikey,
                }
        testsysadmin = model.User.get('testsysadmin')
        cls.testsysadmin = {'id': testsysadmin.id,
                'apikey': testsysadmin.apikey,
                }
        annafan = model.User.get('annafan')
        cls.annafan = {'id': annafan.id,
                'apikey': annafan.apikey,
                }

    @classmethod
    def teardown_class(cls):
        mock_mail_server.SmtpServerHarness.teardown_class()
        pylons_controller.PylonsTestCase.teardown_class()
        model.repo.rebuild_db()

    def check_email(self, email, address, name, subject):
        assert email[1] == 'info@test.ckan.net'
        assert email[2] == [address]
        encoded_subject = 'Subject: =?utf-8?q?{subject}'.format(
                subject=subject.replace(' ', '_'))
        assert encoded_subject in email[3]
        # TODO: Check that body contains link to dashboard and email prefs.

    def test_00_send_email_notifications_not_logged_in(self):
        '''Not-logged-in users shouldn't be able to send email notifications.

        '''
        tests.call_action_api(self.app, 'send_email_notifications',
                status=403)

    def test_00_send_email_notifications_not_authorized(self):
        '''Unauthorized users shouldn't be able to send email notifications.

        '''
        tests.call_action_api(self.app, 'send_email_notifications',
                apikey=self.annafan['apikey'], status=403)

    def test_01_no_email_notifications_after_registration(self):
        '''A new user who isn't following anything shouldn't get any emails.'''

        # Clear any emails already sent due to CreateTestData.create().
        tests.call_action_api(self.app, 'send_email_notifications',
                apikey=self.testsysadmin['apikey'])
        self.clear_smtp_messages()

        # Register a new user.
        sara = tests.call_action_api(self.app, 'user_create',
                apikey=self.testsysadmin['apikey'], name='sara',
                email='sara@sararollins.com', password='TestPassword1',
                fullname='Sara Rollins',
                activity_streams_email_notifications=True)

        # Save the user for later tests to use.
        TestEmailNotifications.sara = sara

        # No notification emails should be sent to anyone at this point.
        tests.call_action_api(self.app, 'send_email_notifications',
                apikey=self.testsysadmin['apikey'])
        assert len(self.get_smtp_messages()) == 0

    def test_02_one_new_activity(self):
        '''A user with one new activity should get one email.'''

        # Make Sara follow something, have to do this to get new activity.
        tests.call_action_api(self.app, 'follow_dataset',
                apikey=self.sara['apikey'], id='warandpeace')

        # Make someone else update the dataset Sara's following, this should
        # create a new activity on Sara's dashboard.
        tests.call_action_api(self.app, 'package_update',
                apikey=self.joeadmin['apikey'], name='warandpeace',
                notes='updated')

        # Run the email notifier job, it should send one notification email
        # to Sara.
        tests.call_action_api(self.app, 'send_email_notifications',
                apikey=self.testsysadmin['apikey'])
        assert len(self.get_smtp_messages()) == 1
        email = self.get_smtp_messages()[0]
        self.check_email(email, 'sara@sararollins.com', 'Sara Rollins',
                '1 new activity from CKAN')

        self.clear_smtp_messages()

    def test_03_multiple_new_activities(self):
        '''Test that a user with multiple new activities gets just one email.

        '''
        # Make someone else update the dataset Sara's following three times,
        # this should create three new activities on Sara's dashboard.
        for i in range(1, 4):
            tests.call_action_api(self.app, 'package_update',
                    apikey=self.joeadmin['apikey'], name='warandpeace',
                    notes='updated {0} times'.format(i))

        # Run the email notifier job, it should send one notification email
        # to Sara.
        tests.call_action_api(self.app, 'send_email_notifications',
                apikey=self.testsysadmin['apikey'])
        assert len(self.get_smtp_messages()) == 1
        email = self.get_smtp_messages()[0]
        self.check_email(email, 'sara@sararollins.com', 'Sara Rollins',
                '3 new activities from CKAN')

        self.clear_smtp_messages()

    def test_04_no_repeat_email_notifications(self):
        '''Test that a user does not get a second email notification for the
        same new activity.

        '''
        # TODO: Assert that Sara has some new activities and has already had
        # an email about them.
        tests.call_action_api(self.app, 'send_email_notifications',
                apikey=self.testsysadmin['apikey'])
        assert len(self.get_smtp_messages()) == 0

    def test_05_no_email_if_seen_on_dashboard(self):
        '''Test that emails are not sent for activities already seen on dash.

        If a user gets some new activities in her dashboard activity stream,
        then views her dashboard activity stream, then she should not got any
        email notifications about these new activities.

        '''
        # Make someone else update the dataset Sara's following, this should
        # create a new activity on Sara's dashboard.
        tests.call_action_api(self.app, 'package_update',
                apikey=self.joeadmin['apikey'], name='warandpeace',
                notes='updated by test_05_no_email_if_seen_on_dashboard')

        # At this point Sara should have a new activity on her dashboard.
        num_new_activities = tests.call_action_api(self.app,
                'dashboard_new_activities_count', apikey=self.sara['apikey'])
        assert num_new_activities > 0, num_new_activities

        # View Sara's dashboard.
        tests.call_action_api(self.app, 'dashboard_mark_activities_old',
                apikey=self.sara['apikey'])

        # No email should be sent.
        tests.call_action_api(self.app, 'send_email_notifications',
                apikey=self.testsysadmin['apikey'])
        assert len(self.get_smtp_messages()) == 0

    def test_05_no_email_notifications_when_disabled_site_wide(self):
        '''Users should not get email notifications when the feature is
        disabled site-wide by a sysadmin.'''

    def test_06_enable_email_notifications_sitewide(self):
        '''When a sysadamin enables email notifications site wide, users
        should not get emails for new activities from before email
        notifications were enabled.

        '''


# It's just easier to separate these tests into their own test class.
class TestEmailNotificationsUserPreference(
        mock_mail_server.SmtpServerHarness,
        pylons_controller.PylonsTestCase):
    '''Tests for the email notifications (on/off) user preference.'''

    @classmethod
    def setup_class(cls):
        mock_mail_server.SmtpServerHarness.setup_class()
        pylons_controller.PylonsTestCase.setup_class()
        tests.CreateTestData.create()
        cls.app = paste.fixture.TestApp(pylons.test.pylonsapp)
        joeadmin = model.User.get('joeadmin')
        cls.joeadmin = {'id': joeadmin.id,
                'apikey': joeadmin.apikey,
                }
        testsysadmin = model.User.get('testsysadmin')
        cls.testsysadmin = {'id': testsysadmin.id,
                'apikey': testsysadmin.apikey,
                }

    @classmethod
    def teardown_class(self):
        mock_mail_server.SmtpServerHarness.teardown_class()
        pylons_controller.PylonsTestCase.teardown_class()
        model.repo.rebuild_db()

    def test_00_email_notifications_disabled_by_default(self):
        '''Email notifications should be disabled for new users.'''

        # Register a new user.
        sara = tests.call_action_api(self.app, 'user_create',
                apikey=self.testsysadmin['apikey'], name='sara',
                email='sara@sararollins.com', password='TestPassword1',
                fullname='Sara Rollins')

        # Save the user for later tests to use.
        TestEmailNotificationsUserPreference.sara = sara

        # Email notifications should be disabled for the new user.
        assert sara['activity_streams_email_notifications'] is False
        assert (tests.call_action_api(self.app, 'user_show',
                apikey=self.sara['apikey'], id='sara')[
                    'activity_streams_email_notifications'] is False)

    def test_01_no_email_notifications_when_disabled(self):
        '''Users with email notifications turned off should not get emails.'''

        # First make Sara follow something so she gets some new activity in
        # her dashboard activity stream.
        tests.call_action_api(self.app, 'follow_dataset',
                apikey=self.sara['apikey'], id='warandpeace')

        # Now make someone else update the dataset so Sara gets a new activity.
        tests.call_action_api(self.app, 'package_update',
                apikey=self.joeadmin['apikey'], id='warandpeace',
                notes='updated')

        # Test that Sara has a new activity, just to make sure.
        assert tests.call_action_api(self.app,
            'dashboard_new_activities_count', apikey=self.sara['apikey']) > 0

        # No email notifications should be sent to Sara.
        tests.call_action_api(self.app, 'send_email_notifications',
                apikey=self.testsysadmin['apikey'])
        assert len(self.get_smtp_messages()) == 0

    def test_02_enable_email_notifications(self):
        '''Users should be able to turn email notifications on.'''

        # Mark all Sara's new activities as old, just to get a fresh start.
        tests.call_action_api(self.app, 'dashboard_mark_activities_old',
                apikey=self.sara['apikey'])
        assert tests.call_action_api(self.app,
            'dashboard_new_activities_count', apikey=self.sara['apikey']) == 0

        # Update the followed dataset a few times so Sara gets a few new
        # activities.
        for i in range(1, 4):
            tests.call_action_api(self.app, 'package_update',
                    apikey=self.joeadmin['apikey'], id='warandpeace',
                    notes='updated {0} times'.format(i))

        # Now Sara should have new activities.
        assert tests.call_action_api(self.app,
            'dashboard_new_activities_count', apikey=self.sara['apikey']) == 3

        # Run the email notifier job.
        tests.call_action_api(self.app, 'send_email_notifications',
                apikey=self.testsysadmin['apikey'])
        assert len(self.get_smtp_messages()) == 0

        # Enable email notifications for Sara.
        self.sara['activity_streams_email_notifications'] = True
        tests.call_action_api(self.app, 'user_update', **self.sara)

        tests.call_action_api(self.app, 'send_email_notifications',
                apikey=self.testsysadmin['apikey'])
        assert len(self.get_smtp_messages()) == 0, ("After a user enables "
            "email notifications she should _not_ get emails about activities "
            "that happened before she enabled them, even if those activities "
            "are still marked as 'new' on her dashboard.")

        # Update the package to generate another new activity.
        tests.call_action_api(self.app, 'package_update',
                apikey=self.joeadmin['apikey'], id='warandpeace',
                notes='updated yet again')

        # Check that Sara has a new activity.
        assert tests.call_action_api(self.app,
            'dashboard_new_activities_count', apikey=self.sara['apikey']) == 4

        # Run the email notifier job, this time Sara should get one email.
        tests.call_action_api(self.app, 'send_email_notifications',
                apikey=self.testsysadmin['apikey'])
        assert len(self.get_smtp_messages()) == 1
        self.clear_smtp_messages()

    def test_03_disable_email_notifications(self):
        '''Users should be able to turn email notifications off.'''

        self.sara['activity_streams_email_notifications'] = False
        tests.call_action_api(self.app, 'user_update', **self.sara)

        tests.call_action_api(self.app, 'package_update',
                apikey=self.joeadmin['apikey'], id='warandpeace',
                notes='updated yet again')

        assert tests.call_action_api(self.app,
            'dashboard_new_activities_count', apikey=self.sara['apikey']) > 0

        tests.call_action_api(self.app, 'send_email_notifications',
                apikey=self.testsysadmin['apikey'])
        assert len(self.get_smtp_messages()) == 0


class TestEmailNotificationsIniSetting(
        mock_mail_server.SmtpServerHarness,
        pylons_controller.PylonsTestCase):
    '''Tests for the ckan.activity_streams_email_notifications config setting.

    '''
    @classmethod
    def setup_class(cls):
        cls._original_config = config.copy()

        # Disable the email notifications feature.
        config['ckan.activity_streams_email_notifications'] = False

        wsgiapp = ckan.config.middleware.make_app(config['global_conf'],
                **config)
        cls.app = paste.fixture.TestApp(wsgiapp)

        mock_mail_server.SmtpServerHarness.setup_class()
        pylons_controller.PylonsTestCase.setup_class()
        tests.CreateTestData.create()

        joeadmin = model.User.get('joeadmin')
        cls.joeadmin = {'id': joeadmin.id,
                'apikey': joeadmin.apikey,
                }
        testsysadmin = model.User.get('testsysadmin')
        cls.testsysadmin = {'id': testsysadmin.id,
                'apikey': testsysadmin.apikey,
                }

    @classmethod
    def teardown_class(cls):
        config.clear()
        config.update(cls._original_config)
        mock_mail_server.SmtpServerHarness.teardown_class()
        pylons_controller.PylonsTestCase.teardown_class()
        model.repo.rebuild_db()

    def test_00_send_email_notifications_feature_disabled(self):
        '''Send_email_notifications API should error when feature disabled.'''

        # Register a new user.
        sara = tests.call_action_api(self.app, 'user_create',
                apikey=self.testsysadmin['apikey'], name='sara',
                email='sara@sararollins.com', password='TestPassword1',
                fullname='Sara Rollins')

        # Save the user for later tests to use.
        TestEmailNotificationsIniSetting.sara = sara

        # Enable the new user's email notifications preference.
        sara['activity_streams_email_notifications'] = True
        tests.call_action_api(self.app, 'user_update', **sara)
        assert (tests.call_action_api(self.app, 'user_show',
                apikey=self.sara['apikey'], id='sara')[
                    'activity_streams_email_notifications']
                is True)

        # Make Sara follow something so she gets some new activity in her
        # dashboard activity stream.
        tests.call_action_api(self.app, 'follow_dataset',
                apikey=self.sara['apikey'], id='warandpeace')

        # Now make someone else update the dataset so Sara gets a new activity.
        tests.call_action_api(self.app, 'package_update',
                apikey=self.joeadmin['apikey'], id='warandpeace',
                notes='updated')

        # Test that Sara has a new activity, just to make sure.
        assert tests.call_action_api(self.app,
            'dashboard_new_activities_count', apikey=self.sara['apikey']) > 0

        # We expect an error when trying to call the send_email_notifications
        # API, because the feature is disabled by the ini file setting.
        tests.call_action_api(self.app, 'send_email_notifications',
                apikey=self.testsysadmin['apikey'], status=409)

    def test_01_no_emails_sent_if_turned_off(self):
        '''No emails should be sent if the feature is disabled site-wide.'''

        # No emails should have been sent by the last test.
        assert len(self.get_smtp_messages()) == 0


class TestEmailNotificationsSinceIniSetting(
        mock_mail_server.SmtpServerHarness,
        pylons_controller.PylonsTestCase):
    '''Tests for the ckan.email_notifications_since config setting.'''

    @classmethod
    def setup_class(cls):
        cls._original_config = config.copy()

        # Don't send email notifications for activities older than 1
        # microsecond.
        config['ckan.email_notifications_since'] = '.000001'

        wsgiapp = ckan.config.middleware.make_app(config['global_conf'],
                **config)
        cls.app = paste.fixture.TestApp(wsgiapp)

        mock_mail_server.SmtpServerHarness.setup_class()
        pylons_controller.PylonsTestCase.setup_class()
        tests.CreateTestData.create()

        joeadmin = model.User.get('joeadmin')
        cls.joeadmin = {'id': joeadmin.id,
                'apikey': joeadmin.apikey,
                }
        testsysadmin = model.User.get('testsysadmin')
        cls.testsysadmin = {'id': testsysadmin.id,
                'apikey': testsysadmin.apikey,
                }

    @classmethod
    def teardown_class(self):
        config.clear()
        config.update(self._original_config)
        mock_mail_server.SmtpServerHarness.teardown_class()
        pylons_controller.PylonsTestCase.teardown_class()
        model.repo.rebuild_db()

    def test_00_email_notifications_since(self):
        '''No emails should be sent for activities older than
        email_notifications_since.

        '''
        # Register a new user.
        sara = tests.call_action_api(self.app, 'user_create',
                apikey=self.testsysadmin['apikey'], name='sara',
                email='sara@sararollins.com', password='TestPassword1',
                fullname='Sara Rollins')

        # Save the user for later tests to use.
        TestEmailNotificationsSinceIniSetting.sara = sara

        # Enable the new user's email notifications preference.
        sara['activity_streams_email_notifications'] = True
        tests.call_action_api(self.app, 'user_update', **sara)
        assert (tests.call_action_api(self.app, 'user_show',
                apikey=self.sara['apikey'], id='sara')[
                    'activity_streams_email_notifications']
                is True)

        # Make Sara follow something so she gets some new activity in her
        # dashboard activity stream.
        tests.call_action_api(self.app, 'follow_dataset',
                apikey=self.sara['apikey'], id='warandpeace')

        # Now make someone else update the dataset so Sara gets a new activity.
        tests.call_action_api(self.app, 'package_update',
                apikey=self.joeadmin['apikey'], id='warandpeace',
                notes='updated')

        # Test that Sara has a new activity, just to make sure.
        assert tests.call_action_api(self.app,
            'dashboard_new_activities_count', apikey=self.sara['apikey']) > 0

        # Wait 1 microsecond, just to make sure we're passed the 'since' time.
        time.sleep(0.000001)

        # No emails should be sent.
        tests.call_action_api(self.app, 'send_email_notifications',
                apikey=self.testsysadmin['apikey'])
        assert len(self.get_smtp_messages()) == 0
