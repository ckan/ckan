# encoding: utf-8
"""Unit tests for ckan/logic/action/create.py.

"""
import __builtin__ as builtins

import cgi
import mock
import pytest

import ckan
import ckan.logic as logic
import ckan.model as model
import ckan.plugins as p
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckan.common import config

from six import string_types, StringIO

from pyfakefs import fake_filesystem

real_open = open
fs = fake_filesystem.FakeFilesystem()
fake_os = fake_filesystem.FakeOsModule(fs)
fake_open = fake_filesystem.FakeFileOpen(fs)


class FakeFileStorage(cgi.FieldStorage):
    def __init__(self, fp, filename):
        self.file = fp
        self.filename = filename
        self.name = "upload"


def mock_open_if_open_fails(*args, **kwargs):
    try:
        return real_open(*args, **kwargs)
    except (OSError, IOError):
        return fake_open(*args, **kwargs)


class TestUserInvite(object):
    @pytest.mark.usefixtures("clean_db")
    @mock.patch("ckan.lib.mailer.send_invite")
    def test_invited_user_is_created_as_pending(self, _):
        invited_user = self._invite_user_to_group()

        assert invited_user is not None
        assert invited_user.is_pending()

    @mock.patch("ckan.lib.mailer.send_invite")
    @pytest.mark.usefixtures("clean_db")
    def test_creates_user_with_valid_username(self, _):
        email = "user$%+abc@email.com"
        invited_user = self._invite_user_to_group(email)

        assert invited_user.name.startswith("user---abc"), invited_user

    @mock.patch("ckan.lib.mailer.send_invite")
    @pytest.mark.usefixtures("clean_db")
    def test_assigns_user_to_group_in_expected_role(self, _):
        role = "admin"
        invited_user = self._invite_user_to_group(role=role)

        group_ids = invited_user.get_group_ids(capacity=role)
        assert len(group_ids) == 1, group_ids

    @mock.patch("ckan.lib.mailer.send_invite")
    @pytest.mark.usefixtures("clean_db")
    def test_sends_invite(self, send_invite):
        invited_user = self._invite_user_to_group()

        assert send_invite.called
        assert send_invite.call_args[0][0].id == invited_user.id

    @mock.patch("ckan.lib.mailer.send_invite")
    @mock.patch("random.SystemRandom")
    @pytest.mark.usefixtures("clean_db")
    def test_works_even_if_username_already_exists(self, rand, _):
        # usernames
        rand.return_value.random.side_effect = [1000, 1000, 2000, 3000]
        # passwords (need to set something, otherwise choice will break)
        rand.return_value.choice.side_effect = "TestPassword1" * 3

        for _ in range(3):
            invited_user = self._invite_user_to_group(email="same@email.com")
            assert invited_user is not None, invited_user

    @mock.patch("ckan.lib.mailer.send_invite")
    @pytest.mark.usefixtures("clean_db")
    def test_requires_email(self, _):
        with pytest.raises(logic.ValidationError):
            self._invite_user_to_group(email=None)

    @mock.patch("ckan.lib.mailer.send_invite")
    @pytest.mark.usefixtures("clean_db")
    def test_requires_role(self, _):
        with pytest.raises(logic.ValidationError):
            self._invite_user_to_group(role=None)

    @mock.patch("ckan.lib.mailer.send_invite")
    @pytest.mark.usefixtures("clean_db")
    def test_raises_not_found(self, _):
        user = factories.User()

        context = {"user": user["name"]}
        params = {
            "email": "a@example.com",
            "group_id": "group_not_found",
            "role": "admin",
        }
        with pytest.raises(logic.NotFound):
            helpers.call_action("user_invite", context, **params)

    @mock.patch("ckan.lib.mailer.send_invite")
    @pytest.mark.usefixtures("clean_db")
    def test_requires_group_id(self, _):
        with pytest.raises(logic.ValidationError):
            self._invite_user_to_group(group={"id": None})

    @mock.patch("ckan.lib.mailer.send_invite")
    @pytest.mark.usefixtures("clean_db")
    def test_user_name_lowercase_when_email_is_uppercase(self, _):
        invited_user = self._invite_user_to_group(email="Maria@example.com")

        assert invited_user.name.split("-")[0] == "maria"

    @pytest.mark.ckan_config("smtp.server", "email.example.com")
    @pytest.mark.usefixtures("clean_db")
    def test_smtp_error_returns_error_message(self):

        sysadmin = factories.Sysadmin()
        group = factories.Group()

        context = {"user": sysadmin["name"]}
        params = {
            "email": "example-invited-user@example.com",
            "group_id": group["id"],
            "role": "editor",
        }

        with pytest.raises(logic.ValidationError):
            helpers.call_action("user_invite", context, **params)

        # Check that the pending user was deleted
        user = (
            model.Session.query(model.User)
            .filter(model.User.name.like("example-invited-user%"))
            .all()
        )

        assert user[0].state == "deleted"

    def _invite_user_to_group(
        self, email="user@email.com", group=None, role="member"
    ):
        user = factories.User()
        group = group or factories.Group(user=user)

        context = {"user": user["name"]}
        params = {"email": email, "group_id": group["id"], "role": role}

        result = helpers.call_action("user_invite", context, **params)

        return model.User.get(result["id"])


class TestResourceViewCreate(object):
    @pytest.mark.ckan_config("ckan.plugins", "image_view")
    @pytest.mark.usefixtures("clean_db", "with_plugins")
    def test_resource_view_create(self):
        context = {}
        params = self._default_resource_view_attributes()

        result = helpers.call_action("resource_view_create", context, **params)

        result.pop("id")
        result.pop("package_id")

        assert params == result

    @pytest.mark.ckan_config("ckan.plugins", "image_view")
    @pytest.mark.usefixtures("clean_db", "with_plugins")
    def test_requires_resource_id(self):
        context = {}
        params = self._default_resource_view_attributes()
        params.pop("resource_id")

        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_view_create", context, **params)

    @pytest.mark.ckan_config("ckan.plugins", "image_view")
    @pytest.mark.usefixtures("clean_db", "with_plugins")
    def test_requires_title(self):
        context = {}
        params = self._default_resource_view_attributes()
        params.pop("title")

        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_view_create", context, **params)

    @mock.patch("ckan.lib.datapreview.get_view_plugin")
    @pytest.mark.ckan_config("ckan.plugins", "image_view")
    @pytest.mark.usefixtures("clean_db", "with_plugins")
    def test_requires_view_type(self, get_view_plugin):
        context = {}
        params = self._default_resource_view_attributes()
        params.pop("view_type")

        get_view_plugin.return_value = "mock_view_plugin"

        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_view_create", context, **params)

    @pytest.mark.ckan_config("ckan.plugins", "image_view")
    @pytest.mark.usefixtures("clean_db", "with_plugins")
    def test_raises_if_couldnt_find_resource(self):
        context = {}
        params = self._default_resource_view_attributes(resource_id="unknown")
        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_view_create", context, **params)

    @pytest.mark.ckan_config("ckan.plugins", "image_view")
    @pytest.mark.usefixtures("clean_db", "with_plugins")
    def test_raises_if_couldnt_find_view_extension(self):
        context = {}
        params = self._default_resource_view_attributes(view_type="unknown")
        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_view_create", context, **params)

    @mock.patch("ckan.lib.datapreview")
    @pytest.mark.ckan_config("ckan.plugins", "image_view")
    @pytest.mark.usefixtures("clean_db", "with_plugins")
    def test_filterable_views_dont_require_any_extra_fields(
        self, datapreview_mock
    ):
        self._configure_datapreview_to_return_filterable_view(datapreview_mock)
        context = {}
        params = self._default_resource_view_attributes()

        result = helpers.call_action("resource_view_create", context, **params)

        result.pop("id")
        result.pop("package_id")

        assert params == result

    @mock.patch("ckan.lib.datapreview")
    @pytest.mark.ckan_config("ckan.plugins", "image_view")
    @pytest.mark.usefixtures("clean_db", "with_plugins")
    def test_filterable_views_converts_filter_fields_and_values_into_filters_dict(
        self, datapreview_mock
    ):
        self._configure_datapreview_to_return_filterable_view(datapreview_mock)
        context = {}
        filters = {
            "filter_fields": ["country", "weather", "country"],
            "filter_values": ["Brazil", "warm", "Argentina"],
        }
        params = self._default_resource_view_attributes(**filters)
        result = helpers.call_action("resource_view_create", context, **params)
        expected_filters = {
            "country": ["Brazil", "Argentina"],
            "weather": ["warm"],
        }
        assert result["filters"] == expected_filters

    @mock.patch("ckan.lib.datapreview")
    @pytest.mark.ckan_config("ckan.plugins", "image_view")
    @pytest.mark.usefixtures("clean_db", "with_plugins")
    def test_filterable_views_converts_filter_fields_and_values_to_list(
        self, datapreview_mock
    ):
        self._configure_datapreview_to_return_filterable_view(datapreview_mock)
        context = {}
        filters = {"filter_fields": "country", "filter_values": "Brazil"}
        params = self._default_resource_view_attributes(**filters)
        result = helpers.call_action("resource_view_create", context, **params)
        assert result["filter_fields"] == ["country"]
        assert result["filter_values"] == ["Brazil"]
        assert result["filters"] == {"country": ["Brazil"]}

    @mock.patch("ckan.lib.datapreview")
    @pytest.mark.ckan_config("ckan.plugins", "image_view")
    @pytest.mark.usefixtures("clean_db", "with_plugins")
    def test_filterable_views_require_filter_fields_and_values_to_have_same_length(
        self, datapreview_mock
    ):
        self._configure_datapreview_to_return_filterable_view(datapreview_mock)
        context = {}
        filters = {
            "filter_fields": ["country", "country"],
            "filter_values": "Brazil",
        }
        params = self._default_resource_view_attributes(**filters)
        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_view_create", context, **params)

    @pytest.mark.ckan_config("ckan.plugins", "image_view")
    @pytest.mark.usefixtures("clean_db", "with_plugins")
    def test_non_filterable_views_dont_accept_filter_fields_and_values(self):
        context = {}
        filters = {"filter_fields": "country", "filter_values": "Brazil"}
        params = self._default_resource_view_attributes(**filters)
        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_view_create", context, **params)

    def _default_resource_view_attributes(self, **kwargs):
        default_attributes = {
            "resource_id": factories.Resource()["id"],
            "view_type": "image_view",
            "title": "View",
            "description": "A nice view",
        }

        default_attributes.update(kwargs)

        return default_attributes

    def _configure_datapreview_to_return_filterable_view(
        self, datapreview_mock
    ):
        filterable_view = mock.MagicMock()
        filterable_view.info.return_value = {"filterable": True}
        datapreview_mock.get_view_plugin.return_value = filterable_view


class TestCreateDefaultResourceViews(object):
    @pytest.mark.ckan_config("ckan.views.default_views", "")
    @pytest.mark.ckan_config("ckan.plugins", "image_view")
    @pytest.mark.usefixtures("clean_db", "with_plugins")
    def test_add_default_views_to_dataset_resources(self):

        # New resources have no views
        dataset_dict = factories.Dataset(
            resources=[
                {
                    "url": "http://some.image.png",
                    "format": "png",
                    "name": "Image 1",
                },
                {
                    "url": "http://some.image.png",
                    "format": "png",
                    "name": "Image 2",
                },
            ]
        )

        # Change default views config setting
        config["ckan.views.default_views"] = "image_view"

        context = {"user": helpers.call_action("get_site_user")["name"]}
        created_views = helpers.call_action(
            "package_create_default_resource_views",
            context,
            package=dataset_dict,
        )

        assert len(created_views) == 2

        assert created_views[0]["view_type"] == "image_view"
        assert created_views[1]["view_type"] == "image_view"

    @pytest.mark.ckan_config("ckan.views.default_views", "")
    @pytest.mark.ckan_config("ckan.plugins", "image_view")
    @pytest.mark.usefixtures("clean_db", "with_plugins")
    def test_add_default_views_to_resource(self):

        # New resources have no views
        dataset_dict = factories.Dataset()
        resource_dict = factories.Resource(
            package_id=dataset_dict["id"],
            url="http://some.image.png",
            format="png",
        )

        # Change default views config setting
        config["ckan.views.default_views"] = "image_view"

        context = {"user": helpers.call_action("get_site_user")["name"]}
        created_views = helpers.call_action(
            "resource_create_default_resource_views",
            context,
            resource=resource_dict,
            package=dataset_dict,
        )

        assert len(created_views) == 1

        assert created_views[0]["view_type"] == "image_view"

    @pytest.mark.ckan_config("ckan.views.default_views", "")
    @pytest.mark.ckan_config("ckan.plugins", "image_view")
    @pytest.mark.usefixtures("clean_db", "with_plugins")
    def test_add_default_views_to_resource_no_dataset_passed(self):

        # New resources have no views
        dataset_dict = factories.Dataset()
        resource_dict = factories.Resource(
            package_id=dataset_dict["id"],
            url="http://some.image.png",
            format="png",
        )

        # Change default views config setting
        config["ckan.views.default_views"] = "image_view"

        context = {"user": helpers.call_action("get_site_user")["name"]}
        created_views = helpers.call_action(
            "resource_create_default_resource_views",
            context,
            resource=resource_dict,
        )

        assert len(created_views) == 1

        assert created_views[0]["view_type"] == "image_view"


class TestResourceCreate:
    @pytest.mark.usefixtures("clean_db")
    def test_resource_create(self):
        context = {}
        params = {
            "package_id": factories.Dataset()["id"],
            "url": "http://data",
            "name": "A nice resource",
        }
        result = helpers.call_action("resource_create", context, **params)

        id = result.pop("id")

        assert id

        params.pop("package_id")
        for key in params.keys():
            assert params[key] == result[key]

    @pytest.mark.usefixtures("clean_db")
    def test_it_requires_package_id(self):

        data_dict = {"url": "http://data"}

        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_create", **data_dict)

    @pytest.mark.usefixtures("clean_db")
    def test_doesnt_require_url(self):
        dataset = factories.Dataset()
        data_dict = {"package_id": dataset["id"]}
        new_resouce = helpers.call_action("resource_create", **data_dict)

        data_dict = {"id": new_resouce["id"]}
        stored_resource = helpers.call_action("resource_show", **data_dict)

        assert not stored_resource["url"]

    @pytest.mark.ckan_config("ckan.storage_path", "/doesnt_exist")
    @mock.patch.object(ckan.lib.uploader, "os", fake_os)
    @mock.patch.object(builtins, "open", side_effect=mock_open_if_open_fails)
    @mock.patch.object(ckan.lib.uploader, "_storage_path", new="/doesnt_exist")
    @pytest.mark.usefixtures("clean_db")
    def test_mimetype_by_url(self, mock_open):
        """
        The mimetype is guessed from the url

        Real world usage would be externally linking the resource and the mimetype would
        be guessed, based on the url
        """
        context = {}
        params = {
            "package_id": factories.Dataset()["id"],
            "url": "http://localhost/data.csv",
            "name": "A nice resource",
        }
        result = helpers.call_action("resource_create", context, **params)

        mimetype = result.pop("mimetype")

        assert mimetype
        assert mimetype == "text/csv"

    @pytest.mark.usefixtures("clean_db")
    def test_mimetype_by_user(self):
        """
        The mimetype is supplied by the user

        Real world usage would be using the FileStore API or web UI form to create a resource
        and the user wanted to specify the mimetype themselves
        """
        context = {}
        params = {
            "package_id": factories.Dataset()["id"],
            "url": "http://localhost/data.csv",
            "name": "A nice resource",
            "mimetype": "application/csv",
        }
        result = helpers.call_action("resource_create", context, **params)

        mimetype = result.pop("mimetype")
        assert mimetype == "application/csv"

    @pytest.mark.ckan_config("ckan.storage_path", "/doesnt_exist")
    @mock.patch.object(ckan.lib.uploader, "os", fake_os)
    @mock.patch.object(builtins, "open", side_effect=mock_open_if_open_fails)
    @mock.patch.object(ckan.lib.uploader, "_storage_path", new="/doesnt_exist")
    @pytest.mark.usefixtures("clean_db")
    def test_mimetype_by_upload_by_filename(self, mock_open):
        """
        The mimetype is guessed from an uploaded file with a filename

        Real world usage would be using the FileStore API or web UI form to upload a file, with a filename plus extension
        If there's no url or the mimetype can't be guessed by the url, mimetype will be guessed by the extension in the filename
        """

        test_file = StringIO()
        test_file.write(
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
        )
        test_resource = FakeFileStorage(test_file, "test.json")

        context = {}
        params = {
            "package_id": factories.Dataset()["id"],
            "url": "http://data",
            "name": "A nice resource",
            "upload": test_resource,
        }

        # Mock url_for as using a test request context interferes with the FS mocking
        with mock.patch("ckan.lib.helpers.url_for"):
            result = helpers.call_action("resource_create", context, **params)

        mimetype = result.pop("mimetype")

        assert mimetype
        assert mimetype == "application/json"

    @pytest.mark.ckan_config("ckan.mimetype_guess", "file_contents")
    @pytest.mark.ckan_config("ckan.storage_path", "/doesnt_exist")
    @mock.patch.object(ckan.lib.uploader, "os", fake_os)
    @mock.patch.object(builtins, "open", side_effect=mock_open_if_open_fails)
    @mock.patch.object(ckan.lib.uploader, "_storage_path", new="/doesnt_exist")
    @pytest.mark.usefixtures("clean_db")
    def test_mimetype_by_upload_by_file(self, mock_open):
        """
        The mimetype is guessed from an uploaded file by the contents inside

        Real world usage would be using the FileStore API or web UI form to upload a file, that has no extension
        If the mimetype can't be guessed by the url or filename, mimetype will be guessed by the contents inside the file
        """

        test_file = StringIO()
        test_file.write(
            """
        Snow Course Name, Number, Elev. metres, Date of Survey, Snow Depth cm, Water Equiv. mm, Survey Code, % of Normal, Density %, Survey Period, Normal mm
        SKINS LAKE,1B05,890,2015/12/30,34,53,,98,16,JAN-01,54
        MCGILLIVRAY PASS,1C05,1725,2015/12/31,88,239,,87,27,JAN-01,274
        NAZKO,1C08,1070,2016/01/05,20,31,,76,16,JAN-01,41
        """
        )
        test_resource = FakeFileStorage(test_file, "")

        context = {}
        params = {
            "package_id": factories.Dataset()["id"],
            "url": "http://data",
            "name": "A nice resource",
            "upload": test_resource,
        }

        # Mock url_for as using a test request context interferes with the FS mocking
        with mock.patch("ckan.lib.helpers.url_for"):
            result = helpers.call_action("resource_create", context, **params)

        mimetype = result.pop("mimetype")

        assert mimetype
        assert mimetype == "text/plain"

    @pytest.mark.ckan_config("ckan.storage_path", "/doesnt_exist")
    @mock.patch.object(ckan.lib.uploader, "os", fake_os)
    @mock.patch.object(builtins, "open", side_effect=mock_open_if_open_fails)
    @mock.patch.object(ckan.lib.uploader, "_storage_path", new="/doesnt_exist")
    @pytest.mark.usefixtures("clean_db")
    def test_size_of_resource_by_upload(self, mock_open):
        """
        The size of the resource determined by the uploaded file
        """

        test_file = StringIO()
        test_file.write(
            """
        Snow Course Name, Number, Elev. metres, Date of Survey, Snow Depth cm, Water Equiv. mm, Survey Code, % of Normal, Density %, Survey Period, Normal mm
        SKINS LAKE,1B05,890,2015/12/30,34,53,,98,16,JAN-01,54
        MCGILLIVRAY PASS,1C05,1725,2015/12/31,88,239,,87,27,JAN-01,274
        NAZKO,1C08,1070,2016/01/05,20,31,,76,16,JAN-01,41
        """
        )
        test_resource = FakeFileStorage(test_file, "test.csv")

        context = {}
        params = {
            "package_id": factories.Dataset()["id"],
            "url": "http://data",
            "name": "A nice resource",
            "upload": test_resource,
        }

        # Mock url_for as using a test request context interferes with the FS mocking
        with mock.patch("ckan.lib.helpers.url_for"):
            result = helpers.call_action("resource_create", context, **params)

        size = result.pop("size")

        assert size
        assert size > 0

    @pytest.mark.usefixtures("clean_db")
    def test_size_of_resource_by_user(self):
        """
        The size of the resource is provided by the users

        Real world usage would be using the FileStore API and the user provides a size for the resource
        """
        context = {}
        params = {
            "package_id": factories.Dataset()["id"],
            "url": "http://data",
            "name": "A nice resource",
            "size": 500,
        }
        result = helpers.call_action("resource_create", context, **params)

        size = int(result.pop("size"))
        assert size == 500

    @pytest.mark.usefixtures("clean_db")
    def test_extras(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)

        resource = helpers.call_action(
            "resource_create",
            package_id=dataset["id"],
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


class TestMemberCreate(object):
    @pytest.mark.usefixtures("clean_db")
    def test_group_member_creation(self):
        user = factories.User()
        group = factories.Group()

        new_membership = helpers.call_action(
            "group_member_create",
            id=group["id"],
            username=user["name"],
            role="member",
        )

        assert new_membership["group_id"] == group["id"]
        assert new_membership["table_name"] == "user"
        assert new_membership["table_id"] == user["id"]
        assert new_membership["capacity"] == "member"

    @pytest.mark.usefixtures("clean_db")
    def test_organization_member_creation(self):
        user = factories.User()
        organization = factories.Organization()

        new_membership = helpers.call_action(
            "organization_member_create",
            id=organization["id"],
            username=user["name"],
            role="member",
        )

        assert new_membership["group_id"] == organization["id"]
        assert new_membership["table_name"] == "user"
        assert new_membership["table_id"] == user["id"]
        assert new_membership["capacity"] == "member"

    @pytest.mark.usefixtures("clean_db")
    def test_group_member_creation_raises_validation_error_if_id_missing(self):

        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "group_member_create", username="someuser", role="member"
            )

    @pytest.mark.usefixtures("clean_db")
    def test_group_member_creation_raises_validation_error_if_username_missing(
        self,
    ):

        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "group_member_create", id="someid", role="member"
            )

    @pytest.mark.usefixtures("clean_db")
    def test_group_member_creation_raises_validation_error_if_role_missing(
        self,
    ):

        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "group_member_create", id="someid", username="someuser"
            )

    @pytest.mark.usefixtures("clean_db")
    def test_org_member_creation_raises_validation_error_if_id_missing(self):

        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "organization_member_create",
                username="someuser",
                role="member",
            )

    @pytest.mark.usefixtures("clean_db")
    def test_org_member_creation_raises_validation_error_if_username_missing(
        self,
    ):

        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "organization_member_create", id="someid", role="member"
            )

    @pytest.mark.usefixtures("clean_db")
    def test_org_member_creation_raises_validation_error_if_role_missing(self):

        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "organization_member_create", id="someid", username="someuser"
            )


class TestDatasetCreate(object):
    @pytest.mark.usefixtures("clean_db")
    def test_normal_user_cant_set_id(self):
        user = factories.User()
        context = {"user": user["name"], "ignore_auth": False}
        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "package_create",
                context=context,
                id="1234",
                name="test-dataset",
            )

    @pytest.mark.usefixtures("clean_db")
    def test_sysadmin_can_set_id(self):
        user = factories.Sysadmin()
        context = {"user": user["name"], "ignore_auth": False}
        dataset = helpers.call_action(
            "package_create", context=context, id="1234", name="test-dataset"
        )
        assert dataset["id"] == "1234"

    @pytest.mark.usefixtures("clean_db")
    def test_context_is_not_polluted(self):
        user = factories.Sysadmin()
        context = {"user": user["name"], "ignore_auth": False}
        helpers.call_action(
            "package_create", context=context, id="1234", name="test-dataset"
        )
        assert "id" not in context
        assert "package" not in context

    @pytest.mark.usefixtures("clean_db")
    def test_id_cant_already_exist(self):
        dataset = factories.Dataset()
        user = factories.Sysadmin()
        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "package_create", id=dataset["id"], name="test-dataset"
            )

    @pytest.mark.usefixtures("clean_db")
    def test_name_not_changed_during_deletion(self):
        dataset = factories.Dataset()
        helpers.call_action("package_delete", id=dataset["id"])
        deleted_dataset = helpers.call_action("package_show", id=dataset["id"])
        assert deleted_dataset["name"] == dataset["name"]

    @pytest.mark.usefixtures("clean_db")
    def test_name_not_changed_after_restoring(self):
        dataset = factories.Dataset()
        context = {"user": factories.Sysadmin()["name"]}
        helpers.call_action("package_delete", id=dataset["id"])
        deleted_dataset = helpers.call_action("package_show", id=dataset["id"])
        restored_dataset = helpers.call_action(
            "package_patch", context=context, id=dataset["id"], state="active"
        )
        assert deleted_dataset["name"] == restored_dataset["name"]
        assert deleted_dataset["id"] == restored_dataset["id"]

    @pytest.mark.usefixtures("clean_db")
    def test_creation_of_dataset_with_name_same_as_of_previously_removed(self):
        dataset = factories.Dataset()
        initial_name = dataset["name"]
        helpers.call_action("package_delete", id=dataset["id"])
        new_dataset = helpers.call_action("package_create", name=initial_name)
        assert new_dataset["name"] == initial_name
        deleted_dataset = helpers.call_action("package_show", id=dataset["id"])

        assert new_dataset["id"] != deleted_dataset["id"]
        assert deleted_dataset["name"] == deleted_dataset["id"]

    @pytest.mark.usefixtures("clean_db")
    def test_missing_id(self):
        with pytest.raises(logic.ValidationError):
            helpers.call_action("package_create")

    @pytest.mark.usefixtures("clean_db")
    def test_name(self):
        dataset = helpers.call_action("package_create", name="some-name")

        assert dataset["name"] == "some-name"
        assert (
            helpers.call_action("package_show", id=dataset["id"])["name"]
            == "some-name"
        )

    @pytest.mark.usefixtures("clean_db")
    def test_title(self):
        dataset = helpers.call_action(
            "package_create", name="test_title", title="New Title"
        )

        assert dataset["title"] == "New Title"
        assert (
            helpers.call_action("package_show", id=dataset["id"])["title"]
            == "New Title"
        )

    @pytest.mark.usefixtures("clean_db")
    def test_extras(self):
        dataset = helpers.call_action(
            "package_create",
            name="test-extras",
            title="Test Extras",
            extras=[{"key": u"original media", "value": u'"book"'}],
        )

        assert dataset["extras"][0]["key"] == "original media"
        assert dataset["extras"][0]["value"] == '"book"'
        dataset = helpers.call_action("package_show", id=dataset["id"])
        assert dataset["extras"][0]["key"] == "original media"
        assert dataset["extras"][0]["value"] == '"book"'

    @pytest.mark.usefixtures("clean_db")
    def test_license(self):
        dataset = helpers.call_action(
            "package_create",
            name="test-license",
            title="Test License",
            license_id="other-open",
        )

        assert dataset["license_id"] == "other-open"
        dataset = helpers.call_action("package_show", id=dataset["id"])
        assert dataset["license_id"] == "other-open"

    @pytest.mark.usefixtures("clean_db")
    def test_notes(self):
        dataset = helpers.call_action(
            "package_create",
            name="test-notes",
            title="Test Notes",
            notes="some notes",
        )

        assert dataset["notes"] == "some notes"
        dataset = helpers.call_action("package_show", id=dataset["id"])
        assert dataset["notes"] == "some notes"

    @pytest.mark.usefixtures("clean_db")
    def test_resources(self):
        dataset = helpers.call_action(
            "package_create",
            name="test-resources",
            title="Test Resources",
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

        resources = dataset["resources"]
        assert resources[0]["alt_url"] == "alt123"
        assert resources[0]["description"] == "Full text."
        assert resources[0]["somekey"] == "somevalue"
        assert "extras" not in resources[0]
        assert "someotherkey" not in resources[0]
        assert resources[0]["format"] == "plain text"
        assert resources[0]["hash"] == "abc123"
        assert resources[0]["position"] == 0
        assert resources[0]["url"] == "http://datahub.io/download/"
        assert resources[1]["description"] == "Index of the novel"
        assert resources[1]["format"] == "JSON"
        assert resources[1]["url"] == "http://datahub.io/index.json"
        assert resources[1]["position"] == 1
        resources = helpers.call_action("package_show", id=dataset["id"])[
            "resources"
        ]
        assert resources[0]["alt_url"] == "alt123"
        assert resources[0]["description"] == "Full text."
        assert resources[0]["somekey"] == "somevalue"
        assert "extras" not in resources[0]
        assert "someotherkey" not in resources[0]
        assert resources[0]["format"] == "plain text"
        assert resources[0]["hash"] == "abc123"
        assert resources[0]["position"] == 0
        assert resources[0]["url"] == "http://datahub.io/download/"
        assert resources[1]["description"] == "Index of the novel"
        assert resources[1]["format"] == "JSON"
        assert resources[1]["url"] == "http://datahub.io/index.json"
        assert resources[1]["position"] == 1

    @pytest.mark.usefixtures("clean_db")
    def test_tags(self):
        dataset = helpers.call_action(
            "package_create",
            name="test-tags",
            title="Test Tags",
            tags=[{"name": u"russian"}, {"name": u"tolstoy"}],
        )

        tag_names = sorted([tag_dict["name"] for tag_dict in dataset["tags"]])
        assert tag_names == ["russian", "tolstoy"]
        dataset = helpers.call_action("package_show", id=dataset["id"])
        tag_names = sorted([tag_dict["name"] for tag_dict in dataset["tags"]])
        assert tag_names == ["russian", "tolstoy"]

    @pytest.mark.usefixtures("clean_db")
    def test_return_id_only(self):
        dataset = helpers.call_action(
            "package_create", name="test-id", context={"return_id_only": True}
        )

        assert isinstance(dataset, string_types)


class TestGroupCreate(object):
    @pytest.mark.usefixtures("clean_db")
    def test_create_group(self):
        user = factories.User()
        context = {"user": user["name"], "ignore_auth": True}

        group = helpers.call_action(
            "group_create", context=context, name="test-group"
        )

        assert len(group["users"]) == 1
        assert group["display_name"] == u"test-group"
        assert group["package_count"] == 0
        assert not group["is_organization"]
        assert group["type"] == "group"

    @pytest.mark.usefixtures("clean_db")
    def test_create_group_validation_fail(self):
        user = factories.User()
        context = {"user": user["name"], "ignore_auth": True}

        with pytest.raises(logic.ValidationError):
            group = helpers.call_action(
                "group_create", context=context, name=""
            )

    @pytest.mark.usefixtures("clean_db")
    def test_create_group_return_id(self):
        import re

        user = factories.User()
        context = {
            "user": user["name"],
            "ignore_auth": True,
            "return_id_only": True,
        }

        group = helpers.call_action(
            "group_create", context=context, name="test-group"
        )

        assert isinstance(group, str)
        assert re.match(r"([a-f\d]{8}(-[a-f\d]{4}){3}-[a-f\d]{12}?)", group)

    @pytest.mark.usefixtures("clean_db")
    def test_create_matches_show(self):
        user = factories.User()
        context = {"user": user["name"], "ignore_auth": True}

        created = helpers.call_action(
            "organization_create", context=context, name="test-organization"
        )

        shown = helpers.call_action(
            "organization_show", context=context, id="test-organization"
        )

        assert sorted(created.keys()) == sorted(shown.keys())
        for k in created.keys():
            assert created[k] == shown[k], k


class TestOrganizationCreate(object):
    @pytest.mark.usefixtures("clean_db")
    def test_create_organization(self):
        user = factories.User()
        context = {"user": user["name"], "ignore_auth": True}

        org = helpers.call_action(
            "organization_create", context=context, name="test-organization"
        )

        assert len(org["users"]) == 1
        assert org["display_name"] == u"test-organization"
        assert org["package_count"] == 0
        assert org["is_organization"]
        assert org["type"] == "organization"

    @pytest.mark.usefixtures("clean_db")
    def test_create_organization_validation_fail(self):
        user = factories.User()
        context = {"user": user["name"], "ignore_auth": True}

        with pytest.raises(logic.ValidationError):
            org = helpers.call_action(
                "organization_create", context=context, name=""
            )

    @pytest.mark.usefixtures("clean_db")
    def test_create_organization_return_id(self):
        import re

        user = factories.User()
        context = {
            "user": user["name"],
            "ignore_auth": True,
            "return_id_only": True,
        }

        org = helpers.call_action(
            "organization_create", context=context, name="test-organization"
        )

        assert isinstance(org, str)
        assert re.match(r"([a-f\d]{8}(-[a-f\d]{4}){3}-[a-f\d]{12}?)", org)

    @pytest.mark.usefixtures("clean_db")
    def test_create_matches_show(self):
        user = factories.User()
        context = {"user": user["name"], "ignore_auth": True}

        created = helpers.call_action(
            "organization_create", context=context, name="test-organization"
        )

        shown = helpers.call_action(
            "organization_show", context=context, id="test-organization"
        )

        assert sorted(created.keys()) == sorted(shown.keys())
        for k in created.keys():
            assert created[k] == shown[k], k

    @pytest.mark.usefixtures("clean_db")
    def test_create_organization_custom_type(self):
        custom_org_type = "some-custom-type"
        user = factories.User()
        context = {"user": user["name"], "ignore_auth": True}

        org = helpers.call_action(
            "organization_create",
            context=context,
            name="test-organization",
            type=custom_org_type,
        )

        assert len(org["users"]) == 1
        assert org["display_name"] == u"test-organization"
        assert org["package_count"] == 0
        assert org["is_organization"]
        assert org["type"] == custom_org_type


class TestUserCreate(object):
    @pytest.mark.usefixtures("clean_db")
    def test_user_create_with_password_hash(self):
        sysadmin = factories.Sysadmin()
        context = {"user": sysadmin["name"]}

        user = helpers.call_action(
            "user_create",
            context=context,
            email="test@example.com",
            name="test",
            password_hash="pretend-this-is-a-valid-hash",
        )

        user_obj = model.User.get(user["id"])
        assert user_obj.password == "pretend-this-is-a-valid-hash"

    @pytest.mark.usefixtures("clean_db")
    def test_user_create_password_hash_not_for_normal_users(self):
        normal_user = factories.User()
        context = {"user": normal_user["name"]}

        user = helpers.call_action(
            "user_create",
            context=context,
            email="test@example.com",
            name="test",
            password="required",
            password_hash="pretend-this-is-a-valid-hash",
        )

        user_obj = model.User.get(user["id"])
        assert user_obj.password != "pretend-this-is-a-valid-hash"


def _clear_activities():
    from ckan import model

    model.Session.query(model.ActivityDetail).delete()
    model.Session.query(model.Activity).delete()
    model.Session.flush()


class TestFollowDataset(object):
    @pytest.mark.usefixtures("clean_db")
    def test_no_activity(self, app):

        user = factories.User()
        dataset = factories.Dataset(user=user)
        _clear_activities()
        helpers.call_action(
            "follow_dataset", context={"user": user["name"]}, **dataset
        )

        activities = helpers.call_action("user_activity_list", id=user["id"])
        assert [activity["activity_type"] for activity in activities] == []
        # A follow creates no Activity, since:
        # https://github.com/ckan/ckan/pull/317


class TestFollowGroup(object):
    @pytest.mark.usefixtures("clean_db")
    def test_no_activity(self, app):
        user = factories.User()
        group = factories.Group(user=user)
        _clear_activities()
        helpers.call_action(
            "follow_group", context={"user": user["name"]}, **group
        )

        activities = helpers.call_action("user_activity_list", id=user["id"])
        assert [activity["activity_type"] for activity in activities] == []
        # A follow creates no Activity, since:
        # https://github.com/ckan/ckan/pull/317


class TestFollowOrganization(object):
    @pytest.mark.usefixtures("clean_db")
    def test_no_activity(self, app):
        user = factories.User()
        org = factories.Organization(user=user)
        _clear_activities()
        helpers.call_action(
            "follow_group", context={"user": user["name"]}, **org
        )

        activities = helpers.call_action("user_activity_list", id=user["id"])
        assert [activity["activity_type"] for activity in activities] == []
        # A follow creates no Activity, since:
        # https://github.com/ckan/ckan/pull/317


class TestFollowUser(object):
    @pytest.mark.usefixtures("clean_db")
    def test_no_activity(self, app):

        user = factories.User()
        user2 = factories.User()
        _clear_activities()
        helpers.call_action(
            "follow_user", context={"user": user["name"]}, **user2
        )

        activities = helpers.call_action("user_activity_list", id=user["id"])
        assert [activity["activity_type"] for activity in activities] == []
        # A follow creates no Activity, since:
        # https://github.com/ckan/ckan/pull/317
