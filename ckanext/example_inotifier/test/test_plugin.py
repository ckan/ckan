import pytest
from unittest.mock import patch
from ckan.tests.factories import User
from ckan.lib.mailer import mail_recipient, send_reset_link
from ckan import plugins, model


test_email = {
    "recipient_name": "Bob",
    "recipient_email": "bob@example.com",
    "subject": "Meeting",
    "body": "The meeting is cancelled",
    "headers": {"header1": "value1"},
}


def _mock_null(*args, **kwargs):
    return 'null'


def _mock_notify_about_topic(user_obj):
    notification_sent = False
    for plugin in plugins.PluginImplementations(plugins.INotifier):
        notification_sent = plugin.notify_about_topic(
            notification_sent,
            'request_password_reset',
            {'user': user_obj}
        )
    if not notification_sent:
        send_reset_link(user_obj)


@pytest.mark.ckan_config(
    "ckan.plugins", "example_inotifier1 example_inotifier2"
)
@pytest.mark.usefixtures("with_plugins", "non_clean_db")
class TestINotifier:
    @classmethod
    def setup_method(self, method):
        test_user = User()
        self.test_user_obj = model.User.get(test_user['name'])

    @patch("ckan.lib.mailer._mail_recipient")
    @patch("ckanext.example_inotifier.plugin.ExampleINotifier1Plugin.notify_recipient")
    @patch("ckanext.example_inotifier.plugin.ExampleINotifier2Plugin.notify_recipient")
    @patch("ckanext.example_inotifier.plugin.ExampleINotifier1Plugin.notify_about_topic")
    @patch("ckanext.example_inotifier.plugin.ExampleINotifier2Plugin.notify_about_topic")
    def test_inotifier_full(self, nat2, nat1, nr2, nr1, mr):
        mail_recipient(**test_email)
        mr.assert_not_called()

        nr1.assert_called()
        assert nr1.call_args_list[0][0][1] == test_email["recipient_name"]
        nr2.assert_called()
        assert nr2.call_args_list[0][0][1] == test_email["recipient_name"]

        _mock_notify_about_topic(self.test_user_obj)
        nat1.assert_called()
        assert nat1.call_args_list[0][0][1] == 'request_password_reset'
        assert nat1.call_args_list[0][0][2] == {'user': self.test_user_obj}
        nat2.assert_called()
        assert nat2.call_args_list[0][0][1] == 'request_password_reset'
        assert nat2.call_args_list[0][0][2] == {'user': self.test_user_obj}

    @patch("ckan.lib.mailer._mail_recipient")
    @patch("ckanext.example_inotifier.plugin.ExampleINotifier1Plugin.notify_recipient", return_value=True)
    @patch("ckanext.example_inotifier.plugin.ExampleINotifier2Plugin.notify_recipient", return_value=True)
    def test_inotifier_notify_recipient_no_mailer(self, nr2, nr1, mr):
        mail_recipient(**test_email)
        # We do not send email because we send custom notifications for all plugins
        mr.assert_not_called()
        nr1.assert_called()
        assert nr1.call_args_list[0][0][0] is False
        assert nr1.call_args_list[0][0][1] == test_email["recipient_name"]
        nr2.assert_called()
        assert nr2.call_args_list[0][0][0] is True
        assert nr2.call_args_list[0][0][1] == test_email["recipient_name"]

    @patch("ckan.lib.mailer._mail_recipient")
    @patch("ckanext.example_inotifier.plugin.ExampleINotifier1Plugin.notify_recipient", return_value=False)
    @patch("ckanext.example_inotifier.plugin.ExampleINotifier2Plugin.notify_recipient", return_value=False)
    def test_inotifier_notify_recipient_mailer(self, nr2, nr1, mr):
        mail_recipient(**test_email)
        mr.assert_called()
        nr1.assert_called()
        assert nr1.call_args_list[0][0][0] is False
        assert nr1.call_args_list[0][0][1] == test_email["recipient_name"]
        nr2.assert_called()
        assert nr2.call_args_list[0][0][0] is False
        assert nr2.call_args_list[0][0][1] == test_email["recipient_name"]

    @patch("ckan.lib.mailer.render", _mock_null)
    @patch("ckan.lib.mailer.get_reset_link_body", _mock_null)
    @patch("ckan.lib.mailer.mail_user")
    @patch("ckanext.example_inotifier.plugin.ExampleINotifier1Plugin.notify_about_topic")
    @patch("ckanext.example_inotifier.plugin.ExampleINotifier2Plugin.notify_about_topic")
    def test_inotifier_notify_about_topic_no_mailer(self, nat2, nat1, mu):
        _mock_notify_about_topic(self.test_user_obj)
        # We do not send email because we have custom topic handlers for all plugins
        mu.assert_not_called()
        nat1.assert_called()
        assert nat1.call_args_list[0][0][1] == 'request_password_reset'
        assert nat1.call_args_list[0][0][2] == {'user': self.test_user_obj}
        nat2.assert_called()
        assert nat2.call_args_list[0][0][1] == 'request_password_reset'
        assert nat2.call_args_list[0][0][2] == {'user': self.test_user_obj}

    @patch("ckan.lib.mailer.render", _mock_null)
    @patch("ckan.lib.mailer.get_reset_link_body", _mock_null)
    @patch("ckan.lib.mailer.mail_user")
    @patch("ckanext.example_inotifier.plugin.ExampleINotifier1Plugin.notify_about_topic", return_value=False)
    @patch("ckanext.example_inotifier.plugin.ExampleINotifier2Plugin.notify_about_topic", return_value=False)
    def test_inotifier_notify_about_topic_mailer(self, nat2, nat1, mu):
        _mock_notify_about_topic(self.test_user_obj)
        mu.assert_called()
        nat1.assert_called()
        assert nat1.call_args_list[0][0][1] == 'request_password_reset'
        assert nat1.call_args_list[0][0][2] == {'user': self.test_user_obj}
        nat2.assert_called()
        assert nat2.call_args_list[0][0][1] == 'request_password_reset'
        assert nat2.call_args_list[0][0][2] == {'user': self.test_user_obj}
