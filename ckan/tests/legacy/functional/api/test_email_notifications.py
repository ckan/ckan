# encoding: utf-8

import time
import pytest
import six

import ckan.model as model
import ckan.tests.legacy as tests
import ckan.tests.helpers as helpers
from ckan.tests.legacy import TestController as ControllerTestCase


class TestEmailNotifications(ControllerTestCase):
    @classmethod
    def setup_class(cls):
        model.repo.rebuild_db()
        tests.CreateTestData.create()
        cls.app = helpers._get_test_app()

        joeadmin = model.User.get("joeadmin")
        joeadmin_token = helpers.call_action(u"api_token_create",
                                             context={'model': model,
                                                      'user': joeadmin.name},
                                             user=joeadmin.name,
                                             name=u"first token")
        cls.joeadmin = {"id": joeadmin.id,
                        "apitoken": joeadmin_token['token']}

        testsysadmin = model.User.get("testsysadmin")
        testsysadmin_token = helpers.call_action(
            u"api_token_create",
            context={'model': model, 'user': testsysadmin.name},
            user=testsysadmin.name,
            name=u"first token")
        cls.testsysadmin = {
            "id": testsysadmin.id,
            "apitoken": testsysadmin_token['token'],
        }
        annafan = model.User.get("annafan")
        annafan_token = helpers.call_action(u"api_token_create",
                                            context={'model': model,
                                                     'user': annafan.name},
                                            user=annafan.name,
                                            name=u"first token")
        cls.annafan = {"id": annafan.id,
                       "apitoken": annafan_token['token']}

        # Register a new user.
        cls.sara = tests.call_action_api(
            cls.app,
            "user_create",
            apitoken=six.ensure_str(cls.testsysadmin["apitoken"]),
            name="sara",
            email="sara@sararollins.com",
            password="TestPassword1",
            fullname="Sara Rollins",
            activity_streams_email_notifications=True,
        )
        cls.sara['apitoken'] = helpers.call_action(
            u"api_token_create",
            context={'model': model, 'user': cls.sara['name']},
            user=cls.sara['name'],
            name=u"first token")

    def check_email(self, email, address, name, subject):
        assert email[1] == "info@test.ckan.net"
        assert email[2] == [address]
        encoded_subject = "Subject: =?utf-8?q?{subject}".format(
            subject=subject.replace(" ", "_")
        )
        assert encoded_subject in email[3]
        # TODO: Check that body contains link to dashboard and email prefs.

    def test_00_send_email_notifications_not_logged_in(self, mail_server):
        """Not-logged-in users shouldn't be able to send email notifications.

        """
        tests.call_action_api(self.app, "send_email_notifications", status=403)

        # def test_00_send_email_notifications_not_authorized(self):
        """Unauthorized users shouldn't be able to send email notifications.

        """
        tests.call_action_api(
            self.app,
            "send_email_notifications",
            apitoken=six.ensure_str(self.annafan["apitoken"]),
            status=403,
        )

        # def test_01_no_email_notifications_after_registration(self):
        """A new user who isn't following anything shouldn't get any emails."""

        # Clear any emails already sent due to CreateTestData.create().
        tests.call_action_api(
            self.app,
            "send_email_notifications",
            apitoken=six.ensure_str(self.testsysadmin["apitoken"]),
        )
        mail_server.clear_smtp_messages()

        # No notification emails should be sent to anyone at this point.
        tests.call_action_api(
            self.app,
            "send_email_notifications",
            apitoken=six.ensure_str(self.testsysadmin["apitoken"]),
        )
        assert len(mail_server.get_smtp_messages()) == 0

        # def test_02_one_new_activity(self):
        """A user with one new activity should get one email."""

        # Make Sara follow something, have to do this to get new activity.
        tests.call_action_api(
            self.app,
            "follow_dataset",
            apitoken=six.ensure_str(self.sara['apitoken']["token"]),
            id="warandpeace",
        )

        # Make someone else update the dataset Sara's following, this should
        # create a new activity on Sara's dashboard.
        tests.call_action_api(
            self.app,
            "package_update",
            apitoken=six.ensure_str(self.joeadmin["apitoken"]),
            name="warandpeace",
            notes="updated",
        )

        # Run the email notifier job, it should send one notification email
        # to Sara.
        tests.call_action_api(
            self.app,
            "send_email_notifications",
            apitoken=six.ensure_str(self.testsysadmin["apitoken"]),
        )
        assert len(mail_server.get_smtp_messages()) == 1
        email = mail_server.get_smtp_messages()[0]
        self.check_email(
            email,
            "sara@sararollins.com",
            "Sara Rollins",
            "1 new activity from CKAN",
        )

        # def test_03_multiple_new_activities(self):
        """Test that a user with multiple new activities gets just one email.

        """
        # Make someone else update the dataset Sara's following three times,
        # this should create three new activities on Sara's dashboard.
        for i in range(1, 4):
            tests.call_action_api(
                self.app,
                "package_update",
                apitoken=six.ensure_str(self.joeadmin["apitoken"]),
                name="warandpeace",
                notes="updated {0} times".format(i),
            )

        # Run the email notifier job, it should send one notification email
        # to Sara.
        mail_server.clear_smtp_messages()

        tests.call_action_api(
            self.app,
            "send_email_notifications",
            apitoken=six.ensure_str(self.testsysadmin["apitoken"]),
        )
        assert len(mail_server.get_smtp_messages()) == 1
        email = mail_server.get_smtp_messages()[0]
        self.check_email(
            email,
            "sara@sararollins.com",
            "Sara Rollins",
            "3 new activities from CKAN",
        )

        mail_server.clear_smtp_messages()

        # def test_04_no_repeat_email_notifications(self):
        """Test that a user does not get a second email notification for the
        same new activity.

        """
        # TODO: Assert that Sara has some new activities and has already had
        # an email about them.
        tests.call_action_api(
            self.app,
            "send_email_notifications",
            apitoken=six.ensure_str(self.testsysadmin["apitoken"]),
        )
        assert len(mail_server.get_smtp_messages()) == 0

        # def test_05_no_email_if_seen_on_dashboard(self):
        """Test that emails are not sent for activities already seen on dash.

        If a user gets some new activities in her dashboard activity stream,
        then views her dashboard activity stream, then she should not got any
        email notifications about these new activities.

        """
        # Make someone else update the dataset Sara's following, this should
        # create a new activity on Sara's dashboard.
        tests.call_action_api(
            self.app,
            "package_update",
            apitoken=six.ensure_str(self.joeadmin["apitoken"]),
            name="warandpeace",
            notes="updated by test_05_no_email_if_seen_on_dashboard",
        )

        # At this point Sara should have a new activity on her dashboard.
        num_new_activities = tests.call_action_api(
            self.app,
            "dashboard_new_activities_count",
            apitoken=six.ensure_str(self.sara['apitoken']["token"]),
        )
        assert num_new_activities > 0, num_new_activities

        # View Sara's dashboard.
        tests.call_action_api(
            self.app,
            "dashboard_mark_activities_old",
            apitoken=six.ensure_str(self.sara['apitoken']["token"]),
        )

        # No email should be sent.
        tests.call_action_api(
            self.app,
            "send_email_notifications",
            apitoken=six.ensure_str(self.testsysadmin["apitoken"]),
        )
        assert len(mail_server.get_smtp_messages()) == 0

        # def test_05_no_email_notifications_when_disabled_site_wide(self):
        """Users should not get email notifications when the feature is
        disabled site-wide by a sysadmin."""

        # def test_06_enable_email_notifications_sitewide(self):
        """When a sysadamin enables email notifications site wide, users
        should not get emails for new activities from before email
        notifications were enabled.

        """


# It's just easier to separate these tests into their own test class.
class TestEmailNotificationsUserPreference(ControllerTestCase):
    """Tests for the email notifications (on/off) user preference."""

    @classmethod
    def setup_class(cls):
        model.repo.rebuild_db()
        tests.CreateTestData.create()
        cls.app = helpers._get_test_app()

        joeadmin = model.User.get("joeadmin")
        joeadmin_token = helpers.call_action(u"api_token_create",
                                             context={'model': model,
                                                      'user': joeadmin.name},
                                             user=joeadmin.name,
                                             name=u"first token")
        cls.joeadmin = {"id": joeadmin.id,
                        "apitoken": joeadmin_token['token']}

        testsysadmin = model.User.get("testsysadmin")
        testsysadmin_token = helpers.call_action(
            u"api_token_create",
            context={'model': model, 'user': testsysadmin.name},
            user=testsysadmin.name,
            name=u"first token")
        cls.testsysadmin = {
            "id": testsysadmin.id,
            "apitoken": testsysadmin_token['token'],
        }
        cls.sara = tests.call_action_api(
            cls.app,
            "user_create",
            apitoken=six.ensure_str(cls.testsysadmin["apitoken"]),
            name="sara",
            email="sara@sararollins.com",
            password="TestPassword1",
            fullname="Sara Rollins",
        )
        cls.sara_api = {}
        cls.sara_api['apitoken'] = helpers.call_action(
            u"api_token_create",
            context={'model': model, 'user': cls.sara['name']},
            user=cls.sara['name'],
            name=u"first token")

    def test_00_email_notifications_disabled_by_default(self, mail_server):
        """Email notifications should be disabled for new users."""

        assert self.sara["activity_streams_email_notifications"] is False
        assert (
            tests.call_action_api(
                self.app, "user_show",
                apitoken=six.ensure_str(self.sara_api["apitoken"]["token"]),
                id="sara"
            )["activity_streams_email_notifications"]
            is False
        )

        # def test_01_no_email_notifications_when_disabled(self):
        """Users with email notifications turned off should not get emails."""

        # First make Sara follow something so she gets some new activity in
        # her dashboard activity stream.
        tests.call_action_api(
            self.app,
            "follow_dataset",
            apitoken=six.ensure_str(self.sara_api["apitoken"]["token"]),
            id="warandpeace",
        )

        # Now make someone else update the dataset so Sara gets a new activity.
        tests.call_action_api(
            self.app,
            "package_update",
            apitoken=six.ensure_str(self.joeadmin["apitoken"]),
            id="warandpeace",
            notes="updated",
        )

        # Test that Sara has a new activity, just to make sure.
        assert (
            tests.call_action_api(
                self.app,
                "dashboard_new_activities_count",
                apitoken=six.ensure_str(self.sara_api["apitoken"]["token"]),
            )
            > 0
        )

        # No email notifications should be sent to Sara.
        tests.call_action_api(
            self.app,
            "send_email_notifications",
            apitoken=six.ensure_str(self.testsysadmin["apitoken"]),
        )
        assert len(mail_server.get_smtp_messages()) == 0

        # def test_02_enable_email_notifications(self):
        """Users should be able to turn email notifications on."""

        # Mark all Sara's new activities as old, just to get a fresh start.
        tests.call_action_api(
            self.app,
            "dashboard_mark_activities_old",
            apitoken=six.ensure_str(self.sara_api["apitoken"]["token"]),
        )
        assert (
            tests.call_action_api(
                self.app,
                "dashboard_new_activities_count",
                apitoken=six.ensure_str(self.sara_api["apitoken"]["token"]),
            )
            == 0
        )

        # Update the followed dataset a few times so Sara gets a few new
        # activities.
        for i in range(1, 4):
            tests.call_action_api(
                self.app,
                "package_update",
                apitoken=six.ensure_str(self.joeadmin["apitoken"]),
                id="warandpeace",
                notes="updated {0} times".format(i),
            )

        # Now Sara should have new activities.
        assert (
            tests.call_action_api(
                self.app,
                "dashboard_new_activities_count",
                apitoken=six.ensure_str(self.sara_api["apitoken"]["token"]),
            )
            == 3
        )

        # Run the email notifier job.
        tests.call_action_api(
            self.app,
            "send_email_notifications",
            apitoken=six.ensure_str(self.testsysadmin["apitoken"]),
        )
        assert len(mail_server.get_smtp_messages()) == 0

        # Enable email notifications for Sara.
        self.sara["activity_streams_email_notifications"] = True
        tests.call_action_api(self.app, "user_update", apitoken=six.ensure_str(
            self.sara_api["apitoken"]["token"]), **self.sara)

        tests.call_action_api(
            self.app,
            "send_email_notifications",
            apitoken=six.ensure_str(self.testsysadmin["apitoken"]),
        )
        assert len(mail_server.get_smtp_messages()) == 0, (
            "After a user enables "
            "email notifications she should _not_ get emails about activities "
            "that happened before she enabled them, even if those activities "
            "are still marked as 'new' on her dashboard."
        )

        # Update the package to generate another new activity.
        tests.call_action_api(
            self.app,
            "package_update",
            apitoken=six.ensure_str(self.joeadmin["apitoken"]),
            id="warandpeace",
            notes="updated yet again",
        )

        # Check that Sara has a new activity.
        assert (
            tests.call_action_api(
                self.app,
                "dashboard_new_activities_count",
                apitoken=six.ensure_str(self.sara_api["apitoken"]["token"]),
            )
            == 4
        )

        # Run the email notifier job, this time Sara should get one email.
        tests.call_action_api(
            self.app,
            "send_email_notifications",
            apitoken=six.ensure_str(self.testsysadmin["apitoken"]),
        )
        assert len(mail_server.get_smtp_messages()) == 1
        mail_server.clear_smtp_messages()

        # def test_03_disable_email_notifications(self):
        """Users should be able to turn email notifications off."""

        self.sara["activity_streams_email_notifications"] = False
        tests.call_action_api(
            self.app, "user_update",
            six.ensure_str(self.sara_api["apitoken"]["token"]), **self.sara)

        tests.call_action_api(
            self.app,
            "package_update",
            apitoken=six.ensure_str(self.joeadmin["apitoken"]),
            id="warandpeace",
            notes="updated yet again",
        )

        assert (
            tests.call_action_api(
                self.app,
                "dashboard_new_activities_count",
                apitoken=six.ensure_str(self.sara_api["apitoken"]["token"]),
            )
            > 0
        )

        tests.call_action_api(
            self.app,
            "send_email_notifications",
            apitoken=six.ensure_str(self.testsysadmin["apitoken"]),
        )
        assert len(mail_server.get_smtp_messages()) == 0


class TestEmailNotificationsIniSetting(object):
    """Tests for the ckan.activity_streams_email_notifications config setting.

    """
    @ classmethod
    def setup_class(cls):

        # Disable the email notifications feature.

        cls.app = helpers._get_test_app()
        model.repo.rebuild_db()
        tests.CreateTestData.create()

        joeadmin = model.User.get("joeadmin")
        joeadmin_token = helpers.call_action(u"api_token_create",
                                             context={'model': model,
                                                      'user': joeadmin.name},
                                             user=joeadmin.name,
                                             name=u"first token")
        cls.joeadmin = {"id": joeadmin.id,
                        "apitoken": six.ensure_str(joeadmin_token["token"])}

        testsysadmin = model.User.get("testsysadmin")
        testsysadmin_token = helpers.call_action(
            u"api_token_create",
            context={'model': model, 'user': testsysadmin.name},
            user=testsysadmin.name,
            name=u"first token")
        cls.testsysadmin = {
            "id": testsysadmin.id,
            "apitoken": six.ensure_str(testsysadmin_token["token"]),
        }

    @ pytest.mark.ckan_config("ckan.activity_streams_email_notifications", False)
    def test_00_send_email_notifications_feature_disabled(self, mail_server):
        """Send_email_notifications API should error when feature disabled."""

        # Register a new user.
        sara = tests.call_action_api(
            self.app,
            "user_create",
            apitoken=self.testsysadmin["apitoken"],
            name="sara",
            email="sara@sararollins.com",
            password="TestPassword1",
            fullname="Sara Rollins",
        )
        sara_api = helpers.call_action(u"api_token_create",
                                       context={'model': model,
                                                'user': sara["name"]},
                                       user=sara["name"],
                                       name=u"first token")

        # Save the user for later tests to use.
        TestEmailNotificationsIniSetting.sara = sara
        TestEmailNotificationsIniSetting.sara_api = sara_api

        # Enable the new user's email notifications preference.
        sara["activity_streams_email_notifications"] = True
        tests.call_action_api(self.app, "user_update",
                              apitoken=six.ensure_str(sara_api["token"]),
                              **sara)
        assert (
            tests.call_action_api(
                self.app, "user_show", apitoken=six.ensure_str(
                    sara_api["token"]), id="sara"
            )["activity_streams_email_notifications"]
            is True
        )

        # Make Sara follow something so she gets some new activity in her
        # dashboard activity stream.
        tests.call_action_api(
            self.app,
            "follow_dataset",
            apitoken=six.ensure_str(sara_api["token"]),
            id="warandpeace",
        )

        # Now make someone else update the dataset so Sara gets a new activity.
        tests.call_action_api(
            self.app,
            "package_update",
            apitoken=self.joeadmin["apitoken"],
            id="warandpeace",
            notes="updated",
        )

        # Test that Sara has a new activity, just to make sure.
        assert (
            tests.call_action_api(
                self.app,
                "dashboard_new_activities_count",
                apitoken=six.ensure_str(sara_api["token"]),
            )
            > 0
        )

        # We expect an error when trying to call the send_email_notifications
        # API, because the feature is disabled by the ini file setting.
        tests.call_action_api(
            self.app,
            "send_email_notifications",
            apitoken=self.testsysadmin["apitoken"],
            status=409,
        )

    @ pytest.mark.ckan_config("ckan.activity_streams_email_notifications", False)
    def test_01_no_emails_sent_if_turned_off(self, mail_server):
        """No emails should be sent if the feature is disabled site-wide."""

        # No emails should have been sent by the last test.
        assert len(mail_server.get_smtp_messages()) == 0


class TestEmailNotificationsSinceIniSetting(ControllerTestCase):
    """Tests for the ckan.email_notifications_since config setting."""

    @ classmethod
    def setup_class(cls):
        cls.app = helpers._get_test_app()
        model.repo.rebuild_db()
        tests.CreateTestData.create()

        joeadmin = model.User.get("joeadmin")
        joeadmin_token = helpers.call_action(u"api_token_create",
                                             context={'model': model,
                                                      'user': joeadmin.name},
                                             user=joeadmin.name,
                                             name=u"first token")
        cls.joeadmin = {"id": joeadmin.id,
                        "apitoken": six.ensure_str(joeadmin_token["token"])}
        testsysadmin = model.User.get("testsysadmin")
        testsysadmin_token = helpers.call_action(
            u"api_token_create", context={'model': model,
                                          'user': testsysadmin.name},
            user=testsysadmin.name,
            name=u"first token")
        cls.testsysadmin = {
            "id": testsysadmin.id,
            "apitoken": six.ensure_str(testsysadmin_token["token"]),
        }

    # Don't send email notifications for activities older than 1
    # microsecond
    @ pytest.mark.ckan_config("ckan.email_notifications_since", ".000001")
    def test_00_email_notifications_since(self, mail_server):
        """No emails should be sent for activities older than
        email_notifications_since.

        """
        # Register a new user.
        sara = tests.call_action_api(
            self.app,
            "user_create",
            apitoken=self.testsysadmin["apitoken"],
            name="sara",
            email="sara@sararollins.com",
            password="TestPassword1",
            fullname="Sara Rollins",
        )
        sara_api = helpers.call_action(u"api_token_create",
                                       context={'model': model,
                                                'user': sara["name"]},
                                       user=sara["name"],
                                       name=u"first token")

        # Save the user for later tests to use.
        TestEmailNotificationsSinceIniSetting.sara = sara
        TestEmailNotificationsSinceIniSetting.sara_api = sara_api

        # Enable the new user's email notifications preference.
        sara["activity_streams_email_notifications"] = True
        tests.call_action_api(self.app, "user_update",
                              six.ensure_str(sara_api["token"]), **sara)
        assert (
            tests.call_action_api(
                self.app, "user_show", apitoken=six.ensure_str
                (sara_api["token"]), id="sara"
            )["activity_streams_email_notifications"]
            is True
        )

        # Make Sara follow something so she gets some new activity in her
        # dashboard activity stream.
        tests.call_action_api(
            self.app,
            "follow_dataset",
            apitoken=six.ensure_str(sara_api["token"]),
            id="warandpeace",
        )

        # Now make someone else update the dataset so Sara gets a new activity.
        tests.call_action_api(
            self.app,
            "package_update",
            apitoken=self.joeadmin["apitoken"],
            id="warandpeace",
            notes="updated",
        )

        # Test that Sara has a new activity, just to make sure.
        assert (
            tests.call_action_api(
                self.app,
                "dashboard_new_activities_count",
                apitoken=six.ensure_str(sara_api["token"]),
            )
            > 0
        )

        # Wait 1 microsecond, just to make sure we're passed the 'since' time.
        time.sleep(0.000001)

        # No emails should be sent.
        tests.call_action_api(
            self.app,
            "send_email_notifications",
            apitoken=self.testsysadmin["apitoken"],
        )
        assert len(mail_server.get_smtp_messages()) == 0
