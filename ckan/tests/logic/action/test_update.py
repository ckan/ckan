# encoding: utf-8
"""Unit tests for ckan/logic/action/update.py."""
import datetime

import mock
import pytest
import six

from werkzeug.datastructures import FileStorage as FlaskFileStorage

import ckan
import ckan.lib.app_globals as app_globals
import ckan.logic as logic
import ckan.plugins as p
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckan import model
from ckan.common import config

from six import BytesIO
from pyfakefs import fake_filesystem

try:
    import __builtin__ as builtins
except ImportError:
    import builtins

real_open = open
fs = fake_filesystem.FakeFilesystem()
fake_os = fake_filesystem.FakeOsModule(fs)
fake_open = fake_filesystem.FakeFileOpen(fs)


class FakeFileStorage(FlaskFileStorage):
    content_type = None

    def __init__(self, stream, filename):
        self.stream = stream
        self.filename = filename
        self.name = "upload"


def mock_open_if_open_fails(*args, **kwargs):
    try:
        return real_open(*args, **kwargs)
    except (OSError, IOError):
        return fake_open(*args, **kwargs)


def datetime_from_string(s):
    """Return a standard datetime.datetime object initialised from a string in
    the same format used for timestamps in dictized activities (the format
    produced by datetime.datetime.isoformat())

    """
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%f")


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestUpdate(object):
    def teardown(self):
        # Since some of the test methods below use the mock module to patch
        # things, we use this teardown() method to remove remove all patches.
        # (This makes sure the patches always get removed even if the test
        # method aborts with an exception or something.)
        mock.patch.stopall()

    # START-AFTER

    def test_user_update_name(self):
        """Test that updating a user's name works successfully."""

        # The canonical form of a test has four steps:
        # 1. Setup any preconditions needed for the test.
        # 2. Call the function that's being tested, once only.
        # 3. Make assertions about the return value and/or side-effects of
        #    of the function that's being tested.
        # 4. Do nothing else!

        # 1. Setup.
        user = factories.User()
        user["name"] = "updated"

        # 2. Make assertions about the return value and/or side-effects.
        with pytest.raises(logic.ValidationError):
            helpers.call_action("user_update", **user)

    # END-BEFORE

    def test_user_generate_apikey(self):
        user = factories.User()
        context = {"user": user["name"]}
        result = helpers.call_action(
            "user_generate_apikey", context=context, id=user["id"]
        )
        updated_user = helpers.call_action(
            "user_show", context=context, id=user["id"]
        )

        assert updated_user["apikey"] != user["apikey"]
        assert result["apikey"] == updated_user["apikey"]

    def test_user_generate_apikey_sysadmin_user(self):
        user = factories.User()
        sysadmin = factories.Sysadmin()
        context = {"user": sysadmin["name"], "ignore_auth": False}
        result = helpers.call_action(
            "user_generate_apikey", context=context, id=user["id"]
        )
        updated_user = helpers.call_action(
            "user_show", context=context, id=user["id"]
        )

        assert updated_user["apikey"] != user["apikey"]
        assert result["apikey"] == updated_user["apikey"]

    def test_user_generate_apikey_nonexistent_user(self):
        user = {
            "id": "nonexistent",
            "name": "nonexistent",
            "email": "does@notexist.com",
        }
        context = {"user": user["name"]}
        with pytest.raises(logic.NotFound):
            helpers.call_action(
                "user_generate_apikey", context=context, id=user["id"]
            )

    def test_user_update_with_id_that_does_not_exist(self):
        user_dict = factories.User.attributes()
        user_dict["id"] = "there's no user with this id"

        with pytest.raises(logic.NotFound):
            helpers.call_action("user_update", **user_dict)

    def test_user_update_with_no_id(self):
        user_dict = factories.User.attributes()
        assert "id" not in user_dict
        with pytest.raises(logic.ValidationError):
            helpers.call_action("user_update", **user_dict)

    @pytest.mark.parametrize(
        "name",
        (
            "",
            "a",
            False,
            0,
            -1,
            23,
            "new",
            "edit",
            "search",
            "a" * 200,
            "Hi!",
            "i++%",
        ),
    )
    def test_user_update_with_invalid_name(self, name):
        user = factories.User()
        user["name"] = name
        with pytest.raises(logic.ValidationError):

            helpers.call_action("user_update", **user)

    def test_user_update_to_name_that_already_exists(self):
        fred = factories.User(name="fred")
        bob = factories.User(name="bob")

        # Try to update fred and change his user name to bob, which is already
        # bob's user name
        fred["name"] = bob["name"]
        with pytest.raises(logic.ValidationError):
            helpers.call_action("user_update", **fred)

    def test_user_update_password(self):
        """Test that updating a user's password works successfully."""

        user = factories.User()

        # FIXME we have to pass the email address to user_update even though
        # we're not updating it, otherwise validation fails.
        helpers.call_action(
            "user_update",
            id=user["name"],
            email=user["email"],
            password="new password",
        )

        # user_show() never returns the user's password, so we have to access
        # the model directly to test it.
        import ckan.model as model

        updated_user = model.User.get(user["id"])
        assert updated_user.validate_password("new password")

    def test_user_update_with_short_password(self):
        user = factories.User()

        user["password"] = "xxx"  # This password is too short.
        with pytest.raises(logic.ValidationError):
            helpers.call_action("user_update", **user)

    def test_user_update_with_empty_password(self):
        """If an empty password is passed to user_update, nothing should
        happen.

        No error (e.g. a validation error) is raised, but the password is not
        changed either.

        """
        user_dict = factories.User.attributes()
        original_password = user_dict["password"]
        user_dict = factories.User(**user_dict)

        user_dict["password"] = ""
        helpers.call_action("user_update", **user_dict)

        import ckan.model as model

        updated_user = model.User.get(user_dict["id"])
        assert updated_user.validate_password(original_password)

    def test_user_update_with_null_password(self):
        user = factories.User()

        user["password"] = None
        with pytest.raises(logic.ValidationError):
            helpers.call_action("user_update", **user)

    def test_user_update_with_invalid_password(self):
        user = factories.User()

        for password in (False, -1, 23, 30.7):
            user["password"] = password
            with pytest.raises(logic.ValidationError):

                helpers.call_action("user_update", **user)

    def test_user_update_without_email_address(self):
        """You have to pass an email address when you call user_update.

        Even if you don't want to change the user's email address, you still
        have to pass their current email address to user_update.

        FIXME: The point of this feature seems to be to prevent people from
        removing email addresses from user accounts, but making them post the
        current email address every time they post to user update is just
        annoying, they should be able to post a dict with no 'email' key to
        user_update and it should simply not change the current email.

        """
        user = factories.User()
        del user["email"]

        with pytest.raises(logic.ValidationError):

            helpers.call_action("user_update", **user)

    # TODO: Valid and invalid values for the rest of the user model's fields.

    def test_user_update_activity_stream(self):
        """Test that the right activity is emitted when updating a user."""

        user = factories.User()
        before = datetime.datetime.utcnow()

        # FIXME we have to pass the email address and password to user_update
        # even though we're not updating those fields, otherwise validation
        # fails.
        helpers.call_action(
            "user_update",
            id=user["name"],
            email=user["email"],
            password=factories.User.attributes()["password"],
            fullname="updated full name",
        )

        activity_stream = helpers.call_action(
            "user_activity_list", id=user["id"]
        )
        latest_activity = activity_stream[0]
        assert latest_activity["activity_type"] == "changed user"
        assert latest_activity["object_id"] == user["id"]
        assert latest_activity["user_id"] == user["id"]
        after = datetime.datetime.utcnow()
        timestamp = datetime_from_string(latest_activity["timestamp"])
        assert timestamp >= before and timestamp <= after

    def test_user_update_with_custom_schema(self):
        """Test that custom schemas passed to user_update do get used.

        user_update allows a custom validation schema to be passed to it in the
        context dict. This is just a simple test that if you pass a custom
        schema user_update does at least call a custom method that's given in
        the custom schema. We assume this means it did use the custom schema
        instead of the default one for validation, so user_update's custom
        schema feature does work.

        """
        import ckan.logic.schema

        user = factories.User()

        # A mock validator method, it doesn't do anything but it records what
        # params it gets called with and how many times.
        mock_validator = mock.MagicMock()

        # Build a custom schema by taking the default schema and adding our
        # mock method to its 'id' field.
        schema = ckan.logic.schema.default_update_user_schema()
        schema["id"].append(mock_validator)

        # Call user_update and pass our custom schema in the context.
        # FIXME: We have to pass email and password even though we're not
        # trying to update them, or validation fails.
        helpers.call_action(
            "user_update",
            context={"schema": schema},
            id=user["name"],
            email=user["email"],
            password=factories.User.attributes()["password"],
            fullname="updated full name",
        )

        # Since we passed user['name'] to user_update as the 'id' param,
        # our mock validator method should have been called once with
        # user['name'] as arg.
        mock_validator.assert_called_once_with(user["name"])

    def test_user_update_multiple(self):
        """Test that updating multiple user attributes at once works."""

        user = factories.User()

        params = {
            "id": user["id"],
            "fullname": "updated full name",
            "about": "updated about",
            # FIXME: We shouldn't have to put email here since we're not
            # updating it, but user_update sucks.
            "email": user["email"],
            # FIXME: We shouldn't have to put password here since we're not
            # updating it, but user_update sucks.
            "password": factories.User.attributes()["password"],
        }

        helpers.call_action("user_update", **params)

        updated_user = helpers.call_action("user_show", id=user["id"])
        assert updated_user["fullname"] == "updated full name"
        assert updated_user["about"] == "updated about"

    def test_user_update_does_not_return_password(self):
        """The user dict that user_update returns should not include the user's
        password."""

        user = factories.User()

        params = {
            "id": user["id"],
            "fullname": "updated full name",
            "about": "updated about",
            "email": user["email"],
            "password": factories.User.attributes()["password"],
        }

        updated_user = helpers.call_action("user_update", **params)
        assert "password" not in updated_user

    def test_user_update_does_not_return_apikey(self):
        """The user dict that user_update returns should not include the user's
        API key."""

        user = factories.User()

        params = {
            "id": user["id"],
            "fullname": "updated full name",
            "about": "updated about",
            "email": user["email"],
            "password": factories.User.attributes()["password"],
        }

        updated_user = helpers.call_action("user_update", **params)
        assert "apikey" not in updated_user

    def test_user_update_does_not_return_reset_key(self):
        """The user dict that user_update returns should not include the user's
        reset key."""

        import ckan.lib.mailer
        import ckan.model

        user = factories.User()
        ckan.lib.mailer.create_reset_key(ckan.model.User.get(user["id"]))

        params = {
            "id": user["id"],
            "fullname": "updated full name",
            "about": "updated about",
            "email": user["email"],
            "password": factories.User.attributes()["password"],
        }

        updated_user = helpers.call_action("user_update", **params)
        assert "reset_key" not in updated_user

    def test_resource_reorder(self):
        resource_urls = ["http://a.html", "http://b.html", "http://c.html"]
        dataset = {
            "name": "basic",
            "resources": [{"url": url} for url in resource_urls],
        }

        dataset = helpers.call_action("package_create", **dataset)
        created_resource_urls = [
            resource["url"] for resource in dataset["resources"]
        ]
        assert created_resource_urls == resource_urls
        mapping = dict(
            (resource["url"], resource["id"])
            for resource in dataset["resources"]
        )

        # This should put c.html at the front
        reorder = {"id": dataset["id"], "order": [mapping["http://c.html"]]}

        helpers.call_action("package_resource_reorder", **reorder)

        dataset = helpers.call_action("package_show", id=dataset["id"])
        reordered_resource_urls = [
            resource["url"] for resource in dataset["resources"]
        ]

        assert reordered_resource_urls == [
            "http://c.html",
            "http://a.html",
            "http://b.html",
        ]

        reorder = {
            "id": dataset["id"],
            "order": [
                mapping["http://b.html"],
                mapping["http://c.html"],
                mapping["http://a.html"],
            ],
        }

        helpers.call_action("package_resource_reorder", **reorder)
        dataset = helpers.call_action("package_show", id=dataset["id"])

        reordered_resource_urls = [
            resource["url"] for resource in dataset["resources"]
        ]

        assert reordered_resource_urls == [
            "http://b.html",
            "http://c.html",
            "http://a.html",
        ]

    def test_update_dataset_cant_change_type(self):
        user = factories.User()
        dataset = factories.Dataset(
            type="dataset", name="unchanging", user=user
        )

        dataset = helpers.call_action(
            "package_update",
            id=dataset["id"],
            name="unchanging",
            type="cabinet",
        )

        assert dataset["type"] == "dataset"
        assert (
            helpers.call_action("package_show", id="unchanging")["type"]
            == "dataset"
        )

    def test_update_organization_cant_change_type(self):
        user = factories.User()
        context = {"user": user["name"]}
        org = factories.Organization(
            type="organization", name="unchanging", user=user
        )

        org = helpers.call_action(
            "organization_update",
            context=context,
            id=org["id"],
            name="unchanging",
            type="ragtagband",
        )

        assert org["type"] == "organization"
        assert (
            helpers.call_action("organization_show", id="unchanging")["type"]
            == "organization"
        )

    def test_update_group_cant_change_type(self):
        user = factories.User()
        context = {"user": user["name"]}
        group = factories.Group(type="group", name="unchanging", user=user)

        group = helpers.call_action(
            "group_update",
            context=context,
            id=group["id"],
            name="unchanging",
            type="favouritecolour",
        )

        assert group["type"] == "group"
        assert (
            helpers.call_action("group_show", id="unchanging")["type"]
            == "group"
        )


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestDatasetUpdate(object):
    def test_missing_id(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)

        with pytest.raises(logic.ValidationError):
            helpers.call_action("package_update")

    def test_name(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)

        dataset_ = helpers.call_action(
            "package_update", id=dataset["id"], name="new-name"
        )

        assert dataset_["name"] == "new-name"
        assert (
            helpers.call_action("package_show", id=dataset["id"])["name"]
            == "new-name"
        )

    def test_title(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)

        dataset_ = helpers.call_action(
            "package_update", id=dataset["id"], title="New Title"
        )

        assert dataset_["title"] == "New Title"
        assert (
            helpers.call_action("package_show", id=dataset["id"])["title"]
            == "New Title"
        )

    def test_extras(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)

        dataset_ = helpers.call_action(
            "package_update",
            id=dataset["id"],
            extras=[{"key": u"original media", "value": u'"book"'}],
        )

        assert dataset_["extras"][0]["key"] == "original media"
        assert dataset_["extras"][0]["value"] == '"book"'
        dataset_ = helpers.call_action("package_show", id=dataset["id"])
        assert dataset_["extras"][0]["key"] == "original media"
        assert dataset_["extras"][0]["value"] == '"book"'

    def test_license(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)

        dataset_ = helpers.call_action(
            "package_update", id=dataset["id"], license_id="other-open"
        )

        assert dataset_["license_id"] == "other-open"
        dataset_ = helpers.call_action("package_show", id=dataset["id"])
        assert dataset_["license_id"] == "other-open"

    def test_notes(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)

        dataset_ = helpers.call_action(
            "package_update", id=dataset["id"], notes="some notes"
        )

        assert dataset_["notes"] == "some notes"
        dataset_ = helpers.call_action("package_show", id=dataset["id"])
        assert dataset_["notes"] == "some notes"

    def test_resources(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)

        dataset_ = helpers.call_action(
            "package_update",
            id=dataset["id"],
            resources=[
                {
                    "alt_url": u"alt123",
                    "description": u"Full text.",
                    "somekey": "somevalue",  # this is how to do resource extras
                    "extras": {u"someotherkey": u"alt234"},  # this isnt
                    "format": u"plain text",
                    "hash": u"abc123",
                    "position": 0,
                    "url": u"http://datahub.io/download/",
                },
                {
                    "description": u"Index of the novel",
                    "format": u"JSON",
                    "position": 1,
                    "url": u"http://datahub.io/index.json",
                },
            ],
        )

        resources_ = dataset_["resources"]
        assert resources_[0]["alt_url"] == "alt123"
        assert resources_[0]["description"] == "Full text."
        assert resources_[0]["somekey"] == "somevalue"
        assert "extras" not in resources_[0]
        assert "someotherkey" not in resources_[0]
        assert resources_[0]["format"] == "plain text"
        assert resources_[0]["hash"] == "abc123"
        assert resources_[0]["position"] == 0
        assert resources_[0]["url"] == "http://datahub.io/download/"
        assert resources_[1]["description"] == "Index of the novel"
        assert resources_[1]["format"] == "JSON"
        assert resources_[1]["url"] == "http://datahub.io/index.json"
        assert resources_[1]["position"] == 1
        resources_ = helpers.call_action("package_show", id=dataset["id"])[
            "resources"
        ]
        assert resources_[0]["alt_url"] == "alt123"
        assert resources_[0]["description"] == "Full text."
        assert resources_[0]["somekey"] == "somevalue"
        assert "extras" not in resources_[0]
        assert "someotherkey" not in resources_[0]
        assert resources_[0]["format"] == "plain text"
        assert resources_[0]["hash"] == "abc123"
        assert resources_[0]["position"] == 0
        assert resources_[0]["url"] == "http://datahub.io/download/"
        assert resources_[1]["description"] == "Index of the novel"
        assert resources_[1]["format"] == "JSON"
        assert resources_[1]["url"] == "http://datahub.io/index.json"
        assert resources_[1]["position"] == 1

    def test_tags(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)

        dataset_ = helpers.call_action(
            "package_update",
            id=dataset["id"],
            tags=[{"name": u"russian"}, {"name": u"tolstoy"}],
        )

        tag_names = sorted([tag_dict["name"] for tag_dict in dataset_["tags"]])
        assert tag_names == ["russian", "tolstoy"]
        dataset_ = helpers.call_action("package_show", id=dataset["id"])
        tag_names = sorted([tag_dict["name"] for tag_dict in dataset_["tags"]])
        assert tag_names == ["russian", "tolstoy"]

    def test_return_id_only(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)

        updated_dataset = helpers.call_action(
            "package_update",
            id=dataset["id"],
            notes="Test",
            context={"return_id_only": True},
        )

        assert updated_dataset == dataset["id"]


@pytest.mark.usefixtures("with_request_context")
class TestUpdateSendEmailNotifications(object):
    @pytest.mark.ckan_config("ckan.activity_streams_email_notifications", True)
    @mock.patch("ckan.logic.action.update.request")
    def test_calling_through_paster_doesnt_validates_auth(self, mock_request):
        mock_request.environ.get.return_value = True
        helpers.call_action("send_email_notifications")

    @pytest.mark.ckan_config("ckan.activity_streams_email_notifications", True)
    @mock.patch("ckan.logic.action.update.request")
    def test_not_calling_through_paster_validates_auth(self, mock_request):
        mock_request.environ.get.return_value = False
        with pytest.raises(logic.NotAuthorized):
            helpers.call_action(
                "send_email_notifications", context={"ignore_auth": False}
            )


@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("clean_db", "with_plugins", "with_request_context")
class TestResourceViewUpdate(object):
    def test_resource_view_update(self):
        resource_view = factories.ResourceView()
        params = {
            "id": resource_view["id"],
            "title": "new title",
            "description": "new description",
        }

        result = helpers.call_action("resource_view_update", **params)

        assert result["title"] == params["title"]
        assert result["description"] == params["description"]

    @mock.patch("ckan.lib.datapreview")
    def test_filterable_views_converts_filter_fields_and_values_into_filters_dict(
        self, datapreview_mock
    ):
        filterable_view = mock.MagicMock()
        filterable_view.info.return_value = {"filterable": True}
        datapreview_mock.get_view_plugin.return_value = filterable_view
        resource_view = factories.ResourceView()
        context = {}
        params = {
            "id": resource_view["id"],
            "filter_fields": ["country", "weather", "country"],
            "filter_values": ["Brazil", "warm", "Argentina"],
        }
        result = helpers.call_action("resource_view_update", context, **params)
        expected_filters = {
            "country": ["Brazil", "Argentina"],
            "weather": ["warm"],
        }
        assert result["filters"] == expected_filters

    def test_resource_view_update_requires_id(self):
        params = {}

        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_view_update", **params)

    def test_resource_view_update_requires_existing_id(self):
        params = {"id": "inexistent_id"}

        with pytest.raises(logic.NotFound):
            helpers.call_action("resource_view_update", **params)

    def test_resource_view_list_reorder(self):
        resource_view_1 = factories.ResourceView(title="View 1")

        resource_id = resource_view_1["resource_id"]

        resource_view_2 = factories.ResourceView(
            resource_id=resource_id, title="View 2"
        )

        resource_view_list = helpers.call_action(
            "resource_view_list", id=resource_id
        )

        assert resource_view_list[0]["title"] == "View 1"
        assert resource_view_list[1]["title"] == "View 2"

        # Reorder views

        result = helpers.call_action(
            "resource_view_reorder",
            id=resource_id,
            order=[resource_view_2["id"], resource_view_1["id"]],
        )
        assert result["order"] == [
            resource_view_2["id"],
            resource_view_1["id"],
        ]

        resource_view_list = helpers.call_action(
            "resource_view_list", id=resource_id
        )

        assert resource_view_list[0]["title"] == "View 2"
        assert resource_view_list[1]["title"] == "View 1"

    def test_resource_view_list_reorder_just_one_id(self):
        resource_view_1 = factories.ResourceView(title="View 1")

        resource_id = resource_view_1["resource_id"]

        resource_view_2 = factories.ResourceView(
            resource_id=resource_id, title="View 2"
        )

        # Reorder Views back just by specifiying a single view to go first

        result = helpers.call_action(
            "resource_view_reorder",
            id=resource_id,
            order=[resource_view_2["id"]],
        )
        assert result["order"] == [
            resource_view_2["id"],
            resource_view_1["id"],
        ]

        resource_view_list = helpers.call_action(
            "resource_view_list", id=resource_id
        )

        assert resource_view_list[0]["title"] == "View 2"
        assert resource_view_list[1]["title"] == "View 1"

    def test_calling_with_only_id_doesnt_update_anything(self):
        resource_view = factories.ResourceView()
        params = {"id": resource_view["id"]}

        result = helpers.call_action("resource_view_update", **params)
        assert result == resource_view


@pytest.mark.ckan_config("ckan.plugins", "image_view recline_view")
@pytest.mark.usefixtures("clean_db", "with_plugins", "with_request_context")
class TestResourceUpdate(object):

    def test_url_only(self):
        dataset = factories.Dataset()
        resource = factories.Resource(package=dataset, url="http://first")

        res_returned = helpers.call_action(
            "resource_update", id=resource["id"], url="http://second"
        )

        assert res_returned["url"] == "http://second"
        resource = helpers.call_action("resource_show", id=resource["id"])
        assert resource["url"] == "http://second"

    def test_extra_only(self):
        dataset = factories.Dataset()
        resource = factories.Resource(package=dataset, newfield="first")

        res_returned = helpers.call_action(
            "resource_update",
            id=resource["id"],
            url=resource["url"],
            newfield="second",
        )

        assert res_returned["newfield"] == "second"
        resource = helpers.call_action("resource_show", id=resource["id"])
        assert resource["newfield"] == "second"

    def test_both_extra_and_url(self):
        dataset = factories.Dataset()
        resource = factories.Resource(
            package=dataset, url="http://first", newfield="first"
        )

        res_returned = helpers.call_action(
            "resource_update",
            id=resource["id"],
            url="http://second",
            newfield="second",
        )

        assert res_returned["url"] == "http://second"
        assert res_returned["newfield"] == "second"

        resource = helpers.call_action("resource_show", id=resource["id"])
        assert res_returned["url"] == "http://second"
        assert resource["newfield"] == "second"

    def test_extra_gets_deleted_on_both_core_and_extra_update(self):
        dataset = factories.Dataset()
        resource = factories.Resource(
            package=dataset, url="http://first", newfield="first"
        )

        res_returned = helpers.call_action(
            "resource_update",
            id=resource["id"],
            url="http://second",
            anotherfield="second",
        )

        assert res_returned["url"] == "http://second"
        assert res_returned["anotherfield"] == "second"
        assert "newfield" not in res_returned

        resource = helpers.call_action("resource_show", id=resource["id"])
        assert res_returned["url"] == "http://second"
        assert res_returned["anotherfield"] == "second"
        assert "newfield" not in res_returned

    def test_extra_gets_deleted_on_extra_only_update(self):
        dataset = factories.Dataset()
        resource = factories.Resource(
            package=dataset, url="http://first", newfield="first"
        )

        res_returned = helpers.call_action(
            "resource_update",
            id=resource["id"],
            url="http://first",
            anotherfield="second",
        )

        assert res_returned["url"] == "http://first"
        assert res_returned["anotherfield"] == "second"
        assert "newfield" not in res_returned

        resource = helpers.call_action("resource_show", id=resource["id"])
        assert res_returned["url"] == "http://first"
        assert res_returned["anotherfield"] == "second"
        assert "newfield" not in res_returned

    def test_datastore_active_is_persisted_if_true_and_not_provided(self):
        dataset = factories.Dataset()
        resource = factories.Resource(
            package=dataset, url="http://example.com", datastore_active=True
        )

        res_returned = helpers.call_action(
            "resource_update",
            id=resource["id"],
            url="http://example.com",
            name="Test",
        )

        assert res_returned["datastore_active"]

    def test_datastore_active_is_persisted_if_false_and_not_provided(self):
        dataset = factories.Dataset()
        resource = factories.Resource(
            package=dataset, url="http://example.com", datastore_active=False
        )

        res_returned = helpers.call_action(
            "resource_update",
            id=resource["id"],
            url="http://example.com",
            name="Test",
        )

        assert not res_returned["datastore_active"]

    def test_datastore_active_is_updated_if_false_and_provided(self):
        dataset = factories.Dataset()
        resource = factories.Resource(
            package=dataset, url="http://example.com", datastore_active=False
        )

        res_returned = helpers.call_action(
            "resource_update",
            id=resource["id"],
            url="http://example.com",
            name="Test",
            datastore_active=True,
        )

        assert res_returned["datastore_active"]

    def test_datastore_active_is_updated_if_true_and_provided(self):
        dataset = factories.Dataset()
        resource = factories.Resource(
            package=dataset, url="http://example.com", datastore_active=True
        )

        res_returned = helpers.call_action(
            "resource_update",
            id=resource["id"],
            url="http://example.com",
            name="Test",
            datastore_active=False,
        )

        assert not res_returned["datastore_active"]

    def test_datastore_active_not_present_if_not_provided_and_not_datastore_plugin_enabled(
        self,
    ):
        assert not p.plugin_loaded("datastore")

        dataset = factories.Dataset()
        resource = factories.Resource(
            package=dataset, url="http://example.com"
        )

        res_returned = helpers.call_action(
            "resource_update",
            id=resource["id"],
            url="http://example.com",
            name="Test",
        )

        assert "datastore_active" not in res_returned

    @helpers.change_config("ckan.storage_path", "/doesnt_exist")
    @mock.patch.object(ckan.lib.uploader, "os", fake_os)
    @mock.patch.object(ckan.lib.uploader, "_storage_path", new="/doesnt_exist")
    def test_mimetype_by_url(self, monkeypatch):
        """
        The mimetype is guessed from the url

        Real world usage would be externally linking the resource and the mimetype would
        be guessed, based on the url
        """
        dataset = factories.Dataset()
        resource = factories.Resource(
            package=dataset, url="http://localhost/data.csv", name="Test"
        )
        monkeypatch.setattr(builtins, 'open', mock_open_if_open_fails)
        res_update = helpers.call_action(
            "resource_update",
            id=resource["id"],
            url="http://localhost/data.json",
        )

        org_mimetype = resource.pop("mimetype")
        upd_mimetype = res_update.pop("mimetype")

        assert org_mimetype != upd_mimetype
        assert upd_mimetype == "application/json"

    def test_mimetype_by_user(self):
        """
        The mimetype is supplied by the user

        Real world usage would be using the FileStore API or web UI form to create a resource
        and the user wanted to specify the mimetype themselves
        """
        dataset = factories.Dataset()
        resource = factories.Resource(
            package=dataset, url="http://localhost/data.csv", name="Test"
        )

        res_update = helpers.call_action(
            "resource_update",
            id=resource["id"],
            url="http://localhost/data.csv",
            mimetype="text/plain",
        )

        org_mimetype = resource.pop("mimetype")
        upd_mimetype = res_update.pop("mimetype")

        assert org_mimetype != upd_mimetype
        assert upd_mimetype == "text/plain"

    @helpers.change_config("ckan.mimetype_guess", "file_contents")
    @helpers.change_config("ckan.storage_path", "/doesnt_exist")
    @mock.patch.object(ckan.lib.uploader, "os", fake_os)
    @mock.patch.object(ckan.lib.uploader, "_storage_path", new="/doesnt_exist")
    def test_mimetype_by_upload_by_file(self, monkeypatch):
        """
        The mimetype is guessed from an uploaded file by the contents inside

        Real world usage would be using the FileStore API or web UI form to upload a file, that has no extension
        If the mimetype can't be guessed by the url or filename, mimetype will be guessed by the contents inside the file
        """
        dataset = factories.Dataset()
        resource = factories.Resource(
            package=dataset, url="http://localhost/data.csv", name="Test"
        )

        update_file = BytesIO()
        update_file.write(six.ensure_binary(
            """
        Snow Course Name, Number, Elev. metres, Date of Survey, Snow Depth cm, Water Equiv. mm, Survey Code, % of Normal, Density %, Survey Period, Normal mm
        SKINS LAKE,1B05,890,2015/12/30,34,53,,98,16,JAN-01,54
        MCGILLIVRAY PASS,1C05,1725,2015/12/31,88,239,,87,27,JAN-01,274
        NAZKO,1C08,1070,2016/01/05,20,31,,76,16,JAN-01,41
        """
        ))
        update_resource = FakeFileStorage(
            update_file, "update_test"
        )
        monkeypatch.setattr(builtins, 'open', mock_open_if_open_fails)
        # Mock url_for as using a test request context interferes with the FS mocking
        with mock.patch("ckan.lib.helpers.url_for"):
            res_update = helpers.call_action(
                "resource_update",
                id=resource["id"],
                url="http://localhost",
                upload=update_resource,
            )

        org_mimetype = resource.pop("mimetype")
        upd_mimetype = res_update.pop("mimetype")

        assert org_mimetype != upd_mimetype
        assert upd_mimetype == "text/plain"

    @helpers.change_config("ckan.storage_path", "/doesnt_exist")
    @mock.patch.object(ckan.lib.uploader, "os", fake_os)
    @mock.patch.object(ckan.lib.uploader, "_storage_path", new="/doesnt_exist")
    def test_mimetype_by_upload_by_filename(self, monkeypatch):
        """
        The mimetype is guessed from an uploaded file with a filename

        Real world usage would be using the FileStore API or web UI form to upload a file, with a filename plus extension
        If there's no url or the mimetype can't be guessed by the url, mimetype will be guessed by the extension in the filename
        """
        test_file = BytesIO()
        test_file.write(six.ensure_binary(
            """
        "info": {
            "title": "BC Data Catalogue API",
            "description": "This API provides information about datasets in the BC Data Catalogue.",
            "termsOfService": "http://www.data.gov.bc.ca/local/dbc/docs/license/API_Terms_of_Use.pdf",
            "contact": {
                "name": "Data BC",
                "url": "http://data.gov.bc.ca/",
                "email": ""
            },
            "license": {
                "name": "Open Government License - British Columbia",
                "url": "http://www.data.gov.bc.ca/local/dbc/docs/license/OGL-vbc2.0.pdf"
            },
            "version": "3.0.0"
        }
        """
        ))
        test_resource = FakeFileStorage(
            test_file, "test.json"
        )
        dataset = factories.Dataset()
        monkeypatch.setattr(builtins, 'open', mock_open_if_open_fails)

        # Mock url_for as using a test request context interferes with the FS mocking
        with mock.patch("ckan.lib.helpers.url_for"):
            resource = factories.Resource(
                package=dataset,
                url="http://localhost",
                name="Test",
                upload=test_resource,
            )

        update_file = BytesIO()
        update_file.write(six.ensure_binary(
            """
        Snow Course Name, Number, Elev. metres, Date of Survey, Snow Depth cm, Water Equiv. mm, Survey Code, % of Normal, Density %, Survey Period, Normal mm
        SKINS LAKE,1B05,890,2015/12/30,34,53,,98,16,JAN-01,54
        MCGILLIVRAY PASS,1C05,1725,2015/12/31,88,239,,87,27,JAN-01,274
        NAZKO,1C08,1070,2016/01/05,20,31,,76,16,JAN-01,41
        """
        ))
        update_resource = FakeFileStorage(
            update_file, "update_test.csv"
        )
        with mock.patch("ckan.lib.helpers.url_for"):
            res_update = helpers.call_action(
                "resource_update",
                id=resource["id"],
                url="http://localhost",
                upload=update_resource,
            )

        org_mimetype = resource.pop("mimetype")
        upd_mimetype = res_update.pop("mimetype")

        assert org_mimetype != upd_mimetype
        assert upd_mimetype == "text/csv"

    def test_size_of_resource_by_user(self):
        """
        The size of the resource is provided by the users

        Real world usage would be using the FileStore API and the user provides a size for the resource
        """
        dataset = factories.Dataset()
        resource = factories.Resource(
            package=dataset,
            url="http://localhost/data.csv",
            name="Test",
            size=500,
        )

        res_update = helpers.call_action(
            "resource_update",
            id=resource["id"],
            url="http://localhost/data.csv",
            size=600,
        )

        org_size = int(resource.pop("size"))
        upd_size = int(res_update.pop("size"))

        assert org_size < upd_size

    @helpers.change_config("ckan.storage_path", "/doesnt_exist")
    @mock.patch.object(ckan.lib.uploader, "os", fake_os)
    @mock.patch.object(ckan.lib.uploader, "_storage_path", new="/doesnt_exist")
    def test_size_of_resource_by_upload(self, monkeypatch):
        """
        The size of the resource determined by the uploaded file
        """
        test_file = BytesIO()
        test_file.write(six.ensure_binary(
            """
        "info": {
            "title": "BC Data Catalogue API",
            "description": "This API provides information about datasets in the BC Data Catalogue.",
            "termsOfService": "http://www.data.gov.bc.ca/local/dbc/docs/license/API_Terms_of_Use.pdf",
            "contact": {
                "name": "Data BC",
                "url": "http://data.gov.bc.ca/",
                "email": ""
            },
            "license": {
                "name": "Open Government License - British Columbia",
                "url": "http://www.data.gov.bc.ca/local/dbc/docs/license/OGL-vbc2.0.pdf"
            },
            "version": "3.0.0"
        }
        """
        ))
        test_resource = FakeFileStorage(
            test_file, "test.json"
        )
        dataset = factories.Dataset()
        monkeypatch.setattr(builtins, 'open', mock_open_if_open_fails)

        # Mock url_for as using a test request context interferes with the FS mocking
        with mock.patch("ckan.lib.helpers.url_for"):
            resource = factories.Resource(
                package=dataset,
                url="http://localhost",
                name="Test",
                upload=test_resource,
            )

        update_file = BytesIO()
        update_file.write(six.ensure_binary(
            """
        Snow Course Name, Number, Elev. metres, Date of Survey, Snow Depth cm, Water Equiv. mm, Survey Code, % of Normal, Density %, Survey Period, Normal mm
        SKINS LAKE,1B05,890,2015/12/30,34,53,,98,16,JAN-01,54
        MCGILLIVRAY PASS,1C05,1725,2015/12/31,88,239,,87,27,JAN-01,274
        NAZKO,1C08,1070,2016/01/05,20,31,,76,16,JAN-01,41
        """
        ))
        update_resource = FakeFileStorage(
            update_file, "update_test.csv"
        )
        with mock.patch("ckan.lib.helpers.url_for"):
            res_update = helpers.call_action(
                "resource_update",
                id=resource["id"],
                url="http://localhost",
                upload=update_resource,
            )

        org_size = int(resource.pop("size"))  # 669 bytes
        upd_size = int(res_update.pop("size"))  # 358 bytes

        assert org_size > upd_size

    def test_extras(self):
        user = factories.User()
        dataset = factories.Dataset(
            user=user,
            resources=[dict(format=u"json", url=u"http://datahub.io/")],
        )

        resource = helpers.call_action(
            "resource_update",
            id=dataset["resources"][0]["id"],
            somekey="somevalue",  # this is how to do resource extras
            extras={u"someotherkey": u"alt234"},  # this isnt
            format=u"plain text",
            url=u"http://datahub.io/download/",
        )

        assert resource["somekey"] == "somevalue"
        assert "extras" not in resource
        assert "someotherkey" not in resource
        resource = helpers.call_action("package_show", id=dataset["id"])[
            "resources"
        ][0]
        assert resource["somekey"] == "somevalue"
        assert "extras" not in resource
        assert "someotherkey" not in resource

    @helpers.change_config(
        "ckan.views.default_views", "image_view recline_view"
    )
    def test_resource_format_update(self):
        dataset = factories.Dataset()

        # Create resource without format
        resource = factories.Resource(
            package=dataset, url="http://localhost", name="Test"
        )
        res_views = helpers.call_action(
            "resource_view_list", id=resource["id"]
        )

        assert len(res_views) == 0

        # Update resource with format
        resource = helpers.call_action(
            "resource_update", id=resource["id"], format="CSV"
        )

        # Format changed
        assert resource["format"] == "CSV"

        res_views = helpers.call_action(
            "resource_view_list", id=resource["id"]
        )

        # View for resource is created
        assert len(res_views) == 1

        second_resource = factories.Resource(
            package=dataset, url="http://localhost", name="Test2", format="CSV"
        )

        res_views = helpers.call_action(
            "resource_view_list", id=second_resource["id"]
        )

        assert len(res_views) == 1

        second_resource = helpers.call_action(
            "resource_update", id=second_resource["id"], format="PNG"
        )

        # Format changed
        assert second_resource["format"] == "PNG"

        res_views = helpers.call_action(
            "resource_view_list", id=second_resource["id"]
        )

        assert len(res_views) == 2

        third_resource = factories.Resource(
            package=dataset, url="http://localhost", name="Test2"
        )

        res_views = helpers.call_action(
            "resource_view_list", id=third_resource["id"]
        )

        assert len(res_views) == 0

        third_resource = helpers.call_action(
            "resource_update", id=third_resource["id"], format="Test format"
        )

        # Format added
        assert third_resource["format"] == "Test format"

        res_views = helpers.call_action(
            "resource_view_list", id=third_resource["id"]
        )

        # No view created, cause no such format
        assert len(res_views) == 0

        third_resource = helpers.call_action(
            "resource_update", id=third_resource["id"], format="CSV"
        )

        # Format changed
        assert third_resource["format"] == "CSV"

        res_views = helpers.call_action(
            "resource_view_list", id=third_resource["id"]
        )

        # View is created
        assert len(res_views) == 1


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestConfigOptionUpdate(object):

    # NOTE: the opposite is tested in
    # ckan/ckanext/example_iconfigurer/tests/test_iconfigurer_update_config.py
    # as we need to enable an external config option from an extension

    def test_app_globals_set_if_defined(self):
        key = "ckan.site_title"
        value = "Test site title"

        params = {key: value}

        helpers.call_action("config_option_update", **params)

        globals_key = app_globals.get_globals_key(key)
        assert hasattr(app_globals.app_globals, globals_key)

        assert getattr(app_globals.app_globals, globals_key) == value


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestUserUpdate(object):
    def test_user_update_with_password_hash(self):
        sysadmin = factories.Sysadmin()
        context = {"user": sysadmin["name"]}

        user = helpers.call_action(
            "user_update",
            context=context,
            email="test@example.com",
            id=sysadmin["name"],
            password_hash="pretend-this-is-a-valid-hash",
        )

        user_obj = model.User.get(user["id"])
        assert user_obj.password == "pretend-this-is-a-valid-hash"

    def test_user_create_password_hash_not_for_normal_users(self):
        normal_user = factories.User()
        context = {"user": normal_user["name"], "ignore_auth": False}

        user = helpers.call_action(
            "user_update",
            context=context,
            email="test@example.com",
            id=normal_user["name"],
            password="required",
            password_hash="pretend-this-is-a-valid-hash",
        )

        user_obj = model.User.get(user["id"])
        assert user_obj.password != "pretend-this-is-a-valid-hash"


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestPackageOwnerOrgUpdate(object):
    def test_package_owner_org_added(self):
        """A package without an owner_org can have one added."""
        sysadmin = factories.Sysadmin()
        org = factories.Organization()
        dataset = factories.Dataset()
        context = {"user": sysadmin["name"]}
        assert dataset["owner_org"] is None
        helpers.call_action(
            "package_owner_org_update",
            context=context,
            id=dataset["id"],
            organization_id=org["id"],
        )
        dataset_obj = model.Package.get(dataset["id"])
        assert dataset_obj.owner_org == org["id"]

    def test_package_owner_org_changed(self):
        """A package with an owner_org can have it changed."""

        sysadmin = factories.Sysadmin()
        org_1 = factories.Organization()
        org_2 = factories.Organization()
        dataset = factories.Dataset(owner_org=org_1["id"])
        context = {"user": sysadmin["name"]}
        assert dataset["owner_org"] == org_1["id"]
        helpers.call_action(
            "package_owner_org_update",
            context=context,
            id=dataset["id"],
            organization_id=org_2["id"],
        )
        dataset_obj = model.Package.get(dataset["id"])
        assert dataset_obj.owner_org == org_2["id"]

    def test_package_owner_org_removed(self):
        """A package with an owner_org can have it removed."""
        sysadmin = factories.Sysadmin()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org["id"])
        context = {"user": sysadmin["name"]}
        assert dataset["owner_org"] == org["id"]
        helpers.call_action(
            "package_owner_org_update",
            context=context,
            id=dataset["id"],
            organization_id=None,
        )
        dataset_obj = model.Package.get(dataset["id"])
        assert dataset_obj.owner_org is None


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestBulkOperations(object):
    def test_bulk_make_private(self):

        org = factories.Organization()

        dataset1 = factories.Dataset(owner_org=org["id"])
        dataset2 = factories.Dataset(owner_org=org["id"])

        helpers.call_action(
            "bulk_update_private",
            {},
            datasets=[dataset1["id"], dataset2["id"]],
            org_id=org["id"],
        )

        # Check search index
        datasets = helpers.call_action(
            "package_search", {}, q="owner_org:{0}".format(org["id"])
        )

        for dataset in datasets["results"]:
            assert dataset["private"]

        # Check DB
        datasets = (
            model.Session.query(model.Package)
            .filter(model.Package.owner_org == org["id"])
            .all()
        )
        for dataset in datasets:
            assert dataset.private

    def test_bulk_make_public(self):

        org = factories.Organization()

        dataset1 = factories.Dataset(owner_org=org["id"], private=True)
        dataset2 = factories.Dataset(owner_org=org["id"], private=True)

        helpers.call_action(
            "bulk_update_public",
            {},
            datasets=[dataset1["id"], dataset2["id"]],
            org_id=org["id"],
        )

        # Check search index
        datasets = helpers.call_action(
            "package_search", {}, q="owner_org:{0}".format(org["id"])
        )

        for dataset in datasets["results"]:
            assert not (dataset["private"])

        # Check DB
        datasets = (
            model.Session.query(model.Package)
            .filter(model.Package.owner_org == org["id"])
            .all()
        )
        for dataset in datasets:
            assert not (dataset.private)

    def test_bulk_delete(self):

        org = factories.Organization()

        dataset1 = factories.Dataset(owner_org=org["id"])
        dataset2 = factories.Dataset(owner_org=org["id"])

        helpers.call_action(
            "bulk_update_delete",
            {},
            datasets=[dataset1["id"], dataset2["id"]],
            org_id=org["id"],
        )

        # Check search index
        datasets = helpers.call_action(
            "package_search", {}, q="owner_org:{0}".format(org["id"])
        )

        assert datasets["results"] == []

        # Check DB
        datasets = (
            model.Session.query(model.Package)
            .filter(model.Package.owner_org == org["id"])
            .all()
        )
        for dataset in datasets:
            assert dataset.state == "deleted"


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestDashboardMarkActivitiesOld(object):
    def test_mark_as_old_some_activities_by_a_followed_user(self):
        # do some activity that will show up on user's dashboard
        user = factories.User()
        # now some activity that is "new" because it is by a followed user
        followed_user = factories.User()
        helpers.call_action(
            "follow_user", context={"user": user["name"]}, **followed_user
        )
        dataset = factories.Dataset(user=followed_user)
        dataset["title"] = "Dataset with changed title"
        helpers.call_action(
            "package_update",
            context={"user": followed_user["name"]},
            **dataset
        )
        assert (
            helpers.call_action(
                "dashboard_new_activities_count", context={"user": user["id"]}
            )
            == 3
        )
        activities = helpers.call_action(
            "dashboard_activity_list", context={"user": user["id"]}
        )
        assert [
            (activity["activity_type"], activity["is_new"])
            for activity in activities[::-1]
        ] == [
            ("new user", False),
            ("new user", True),
            ("new package", True),
            ("changed package", True),
        ]

        helpers.call_action(
            "dashboard_mark_activities_old", context={"user": user["name"]}
        )

        assert (
            helpers.call_action(
                "dashboard_new_activities_count", context={"user": user["id"]}
            )
            == 0
        )
        activities = helpers.call_action(
            "dashboard_activity_list", context={"user": user["id"]}
        )
        assert [
            (activity["activity_type"], activity["is_new"])
            for activity in activities[::-1]
        ] == [
            ("new user", False),
            ("new user", False),
            ("new package", False),
            ("changed package", False),
        ]
