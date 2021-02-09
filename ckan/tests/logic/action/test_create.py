# encoding: utf-8
"""Unit tests for ckan/logic/action/create.py.

"""
import datetime
import mock
import pytest

import ckan
import ckan.logic as logic
import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckan.common import config

from six import string_types

from freezegun import freeze_time


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestUserInvite(object):
    @mock.patch("ckan.lib.mailer.send_invite")
    def test_invited_user_is_created_as_pending(self, _):
        invited_user = self._invite_user_to_group()

        assert invited_user is not None
        assert invited_user.is_pending()

    @mock.patch("ckan.lib.mailer.send_invite")
    def test_creates_user_with_valid_username(self, _):
        email = "user$%+abc@email.com"
        invited_user = self._invite_user_to_group(email)

        assert invited_user.name.startswith("user---abc"), invited_user

    @mock.patch("ckan.lib.mailer.send_invite")
    def test_assigns_user_to_group_in_expected_role(self, _):
        role = "admin"
        invited_user = self._invite_user_to_group(role=role)

        group_ids = invited_user.get_group_ids(capacity=role)
        assert len(group_ids) == 1, group_ids

    @mock.patch("ckan.lib.mailer.send_invite")
    def test_sends_invite(self, send_invite):
        invited_user = self._invite_user_to_group()

        assert send_invite.called
        assert send_invite.call_args[0][0].id == invited_user.id

    @mock.patch("ckan.lib.mailer.send_invite")
    @mock.patch("random.SystemRandom")
    def test_works_even_if_username_already_exists(self, rand, _):
        # usernames
        rand.return_value.random.side_effect = [1000, 1000, 2000, 3000]
        # passwords (need to set something, otherwise choice will break)
        rand.return_value.choice.side_effect = "TestPassword1" * 3

        for _ in range(3):
            invited_user = self._invite_user_to_group(
                email="same{}@email.com".format(_))
            assert invited_user is not None, invited_user

    @mock.patch("ckan.lib.mailer.send_invite")
    def test_requires_email(self, _):
        with pytest.raises(logic.ValidationError):
            self._invite_user_to_group(email=None)

    @mock.patch("ckan.lib.mailer.send_invite")
    def test_requires_role(self, _):
        with pytest.raises(logic.ValidationError):
            self._invite_user_to_group(role=None)

    @mock.patch("ckan.lib.mailer.send_invite")
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
    def test_requires_group_id(self, _):
        with pytest.raises(logic.ValidationError):
            self._invite_user_to_group(group={"id": None})

    @mock.patch("ckan.lib.mailer.send_invite")
    def test_user_name_lowercase_when_email_is_uppercase(self, _):
        invited_user = self._invite_user_to_group(email="Maria@example.com")

        assert invited_user.name.split("-")[0] == "maria"

    @pytest.mark.ckan_config("smtp.server", "email.example.com")
    @pytest.mark.usefixtures("with_request_context")
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


@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestResourceViewCreate(object):
    def test_resource_view_create(self):
        context = {}
        params = self._default_resource_view_attributes()

        result = helpers.call_action("resource_view_create", context, **params)

        result.pop("id")
        result.pop("package_id")

        assert params == result

    def test_requires_resource_id(self):
        context = {}
        params = self._default_resource_view_attributes()
        params.pop("resource_id")

        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_view_create", context, **params)

    def test_requires_title(self):
        context = {}
        params = self._default_resource_view_attributes()
        params.pop("title")

        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_view_create", context, **params)

    @mock.patch("ckan.lib.datapreview.get_view_plugin")
    def test_requires_view_type(self, get_view_plugin):
        context = {}
        params = self._default_resource_view_attributes()
        params.pop("view_type")

        get_view_plugin.return_value = "mock_view_plugin"

        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_view_create", context, **params)

    def test_raises_if_couldnt_find_resource(self):
        context = {}
        params = self._default_resource_view_attributes(resource_id="unknown")
        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_view_create", context, **params)

    def test_raises_if_couldnt_find_view_extension(self):
        context = {}
        params = self._default_resource_view_attributes(view_type="unknown")
        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_view_create", context, **params)

    @mock.patch("ckan.lib.datapreview")
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


@pytest.mark.ckan_config("ckan.views.default_views", "")
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("clean_db", "with_plugins")
class TestCreateDefaultResourceViews(object):
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


@pytest.mark.usefixtures("clean_db")
class TestResourceCreate:
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

    def test_it_requires_package_id(self):

        data_dict = {"url": "http://data"}

        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_create", **data_dict)

    def test_doesnt_require_url(self):
        dataset = factories.Dataset()
        data_dict = {"package_id": dataset["id"]}
        new_resouce = helpers.call_action("resource_create", **data_dict)

        data_dict = {"id": new_resouce["id"]}
        stored_resource = helpers.call_action("resource_show", **data_dict)

        assert not stored_resource["url"]

    def test_mimetype_by_url(self, monkeypatch, tmpdir):
        """The mimetype is guessed from the url

        Real world usage would be externally linking the resource and
        the mimetype would be guessed, based on the url

        """
        context = {}
        params = {
            "package_id": factories.Dataset()["id"],
            "url": "http://localhost/data.csv",
            "name": "A nice resource",
        }
        monkeypatch.setattr(ckan.lib.uploader, "_storage_path", str(tmpdir))
        result = helpers.call_action("resource_create", context, **params)

        mimetype = result.pop("mimetype")

        assert mimetype
        assert mimetype == "text/csv"

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

    def test_mimetype_by_upload_by_filename(self, create_with_upload):
        """The mimetype is guessed from an uploaded file with a filename

        Real world usage would be using the FileStore API or web UI
        form to upload a file, with a filename plus extension If
        there's no url or the mimetype can't be guessed by the url,
        mimetype will be guessed by the extension in the filename

        """
        content = """
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

        result = create_with_upload(
            content, 'test.json', url="http://data",
            package_id=factories.Dataset()[u"id"]
        )
        mimetype = result.pop("mimetype")

        assert mimetype
        assert mimetype == "application/json"

    @pytest.mark.ckan_config("ckan.mimetype_guess", "file_contents")
    def test_mimetype_by_upload_by_file(self, create_with_upload):
        """The mimetype is guessed from an uploaded file by the contents inside

        Real world usage would be using the FileStore API or web UI
        form to upload a file, that has no extension If the mimetype
        can't be guessed by the url or filename, mimetype will be
        guessed by the contents inside the file

        """

        content = """
        Snow Course Name, Number, Elev. metres, Date of Survey, Snow Depth cm,\
        Water Equiv. mm, Survey Code, % of Normal, Density %, Survey Period, \
        Normal mm
        SKINS LAKE,1B05,890,2015/12/30,34,53,,98,16,JAN-01,54
        MCGILLIVRAY PASS,1C05,1725,2015/12/31,88,239,,87,27,JAN-01,274
        NAZKO,1C08,1070,2016/01/05,20,31,,76,16,JAN-01,41
        """
        result = create_with_upload(
            content, 'test.csv', url="http://data",
            package_id=factories.Dataset()[u"id"]
        )

        mimetype = result.pop("mimetype")

        assert mimetype
        assert mimetype == "text/plain"

    def test_size_of_resource_by_upload(self, create_with_upload):
        """
        The size of the resource determined by the uploaded file
        """

        content = """
        Snow Course Name, Number, Elev. metres, Date of Survey, Snow Depth cm,\
        Water Equiv. mm, Survey Code, % of Normal, Density %, Survey Period, \
        Normal mm
        SKINS LAKE,1B05,890,2015/12/30,34,53,,98,16,JAN-01,54
        MCGILLIVRAY PASS,1C05,1725,2015/12/31,88,239,,87,27,JAN-01,274
        NAZKO,1C08,1070,2016/01/05,20,31,,76,16,JAN-01,41
        """
        result = create_with_upload(
            content, 'test.csv', url="http://data",
            package_id=factories.Dataset()[u"id"]
        )

        size = result.pop("size")

        assert size
        assert size > 0

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

    @pytest.mark.usefixtures("with_request_context")
    def test_extras(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)

        resource = helpers.call_action(
            "resource_create",
            package_id=dataset["id"],
            somekey="somevalue",  # this is how to do resource extras
            extras={u"someotherkey": u"alt234"},  # this isnt
            subobject={u'hello': u'there'},  # JSON objects supported
            sublist=[1, 2, 3],  # JSON lists suppoted
            format=u"plain text",
            url=u"http://datahub.io/download/",
        )

        assert resource["somekey"] == "somevalue"
        assert "extras" not in resource
        assert "someotherkey" not in resource
        assert resource["subobject"] == {u"hello": u"there"}
        assert resource["sublist"] == [1, 2, 3]
        resource = helpers.call_action("package_show", id=dataset["id"])[
            "resources"
        ][0]
        assert resource["somekey"] == "somevalue"
        assert "extras" not in resource
        assert "someotherkey" not in resource
        assert resource["subobject"] == {u"hello": u"there"}
        assert resource["sublist"] == [1, 2, 3]

    @freeze_time('2020-02-25 12:00:00')
    def test_metadata_modified_is_set_to_utcnow_when_created(self):
        context = {}
        params = {
            "package_id": factories.Dataset()["id"],
            "url": "http://data",
            "name": "A nice resource",
        }
        result = helpers.call_action("resource_create", context, **params)

        assert (result['metadata_modified'] ==
                datetime.datetime.utcnow().isoformat())

    @pytest.mark.ckan_config('ckan.auth.allow_dataset_collaborators', True)
    @pytest.mark.ckan_config('ckan.auth.allow_admin_collaborators', True)
    @pytest.mark.parametrize('role', ['admin', 'editor'])
    def test_collaborators_can_create_resources(self, role):

        org1 = factories.Organization()
        dataset = factories.Dataset(owner_org=org1['id'])

        user = factories.User()

        helpers.call_action(
            'package_collaborator_create',
            id=dataset['id'], user_id=user['id'], capacity=role)

        context = {
            'user': user['name'],
            'ignore_auth': False,

        }

        created_resource = helpers.call_action(
            'resource_create',
            context=context,
            package_id=dataset['id'],
            name='created by collaborator',
            url='https://example.com')

        assert created_resource['name'] == 'created by collaborator'


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestMemberCreate(object):
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

    def test_group_member_creation_raises_validation_error_if_id_missing(self):

        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "group_member_create", username="someuser", role="member"
            )

    def test_group_member_creation_raises_validation_error_if_username_missing(
        self,
    ):

        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "group_member_create", id="someid", role="member"
            )

    def test_group_member_creation_raises_validation_error_if_role_missing(
        self,
    ):

        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "group_member_create", id="someid", username="someuser"
            )

    def test_org_member_creation_raises_validation_error_if_id_missing(self):

        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "organization_member_create",
                username="someuser",
                role="member",
            )

    def test_org_member_creation_raises_validation_error_if_username_missing(
        self,
    ):

        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "organization_member_create", id="someid", role="member"
            )

    def test_org_member_creation_raises_validation_error_if_role_missing(self):

        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "organization_member_create", id="someid", username="someuser"
            )


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestDatasetCreate(object):
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

    def test_sysadmin_can_set_id(self):
        user = factories.Sysadmin()
        context = {"user": user["name"], "ignore_auth": False}
        dataset = helpers.call_action(
            "package_create", context=context, id="1234", name="test-dataset"
        )
        assert dataset["id"] == "1234"

    def test_context_is_not_polluted(self):
        user = factories.Sysadmin()
        context = {"user": user["name"], "ignore_auth": False}
        helpers.call_action(
            "package_create", context=context, id="1234", name="test-dataset"
        )
        assert "id" not in context
        assert "package" not in context

    def test_id_cant_already_exist(self):
        dataset = factories.Dataset()
        user = factories.Sysadmin()
        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "package_create", id=dataset["id"], name="test-dataset"
            )

    def test_name_not_changed_during_deletion(self):
        dataset = factories.Dataset()
        helpers.call_action("package_delete", id=dataset["id"])
        deleted_dataset = helpers.call_action("package_show", id=dataset["id"])
        assert deleted_dataset["name"] == dataset["name"]

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

    def test_creation_of_dataset_with_name_same_as_of_previously_removed(self):
        dataset = factories.Dataset()
        initial_name = dataset["name"]
        helpers.call_action("package_delete", id=dataset["id"])
        new_dataset = helpers.call_action("package_create", name=initial_name)
        assert new_dataset["name"] == initial_name
        deleted_dataset = helpers.call_action("package_show", id=dataset["id"])

        assert new_dataset["id"] != deleted_dataset["id"]
        assert deleted_dataset["name"] == deleted_dataset["id"]

    def test_missing_id(self):
        with pytest.raises(logic.ValidationError):
            helpers.call_action("package_create")

    def test_name(self):
        dataset = helpers.call_action("package_create", name="some-name")

        assert dataset["name"] == "some-name"
        assert (
            helpers.call_action("package_show", id=dataset["id"])["name"]
            == "some-name"
        )

    def test_title(self):
        dataset = helpers.call_action(
            "package_create", name="test_title", title="New Title"
        )

        assert dataset["title"] == "New Title"
        assert (
            helpers.call_action("package_show", id=dataset["id"])["title"]
            == "New Title"
        )

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

    def test_return_id_only(self):
        dataset = helpers.call_action(
            "package_create", name="test-id", context={"return_id_only": True}
        )

        assert isinstance(dataset, string_types)


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestGroupCreate(object):
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

    def test_create_group_validation_fail(self):
        user = factories.User()
        context = {"user": user["name"], "ignore_auth": True}

        with pytest.raises(logic.ValidationError):
            group = helpers.call_action(
                "group_create", context=context, name=""
            )

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


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestOrganizationCreate(object):
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

    def test_create_organization_validation_fail(self):
        user = factories.User()
        context = {"user": user["name"], "ignore_auth": True}

        with pytest.raises(logic.ValidationError):
            org = helpers.call_action(
                "organization_create", context=context, name=""
            )

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


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestUserCreate(object):
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

    def test_user_create_password_hash_not_for_normal_users(self):
        normal_user = factories.User()
        context = {"user": normal_user["name"], "ignore_auth": False}

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


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestFollowDataset(object):
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


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestFollowGroup(object):
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


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestFollowOrganization(object):
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


@pytest.mark.usefixtures("clean_db", "with_request_context")
class TestFollowUser(object):
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


@pytest.mark.usefixtures(u"clean_db")
class TestApiToken(object):

    def test_token_created(self):
        from ckan.lib.api_token import decode
        user = factories.User()
        data = helpers.call_action(u"api_token_create", context={
            u"model": model,
            u"user": user[u"name"]
        }, user=user[u"name"], name=u"token-name")
        token = data[u'token']
        jti = decode(token)[u'jti']
        res = model.ApiToken.get(jti)
        assert res.user_id == user[u"id"]
        assert res.last_access is None
        assert res.id == jti


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config(u"ckan.auth.allow_dataset_collaborators", False)
def test_create_package_collaborator_when_config_disabled():

    dataset = factories.Dataset()
    user = factories.User()
    capacity = 'editor'

    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            'package_collaborator_create',
            id=dataset['id'], user_id=user['id'], capacity=capacity)


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config(u"ckan.auth.allow_dataset_collaborators", True)
class TestPackageMemberCreate(object):

    def test_create(self):

        dataset = factories.Dataset()
        user = factories.User()
        capacity = 'editor'

        member = helpers.call_action(
            'package_collaborator_create',
            id=dataset['id'], user_id=user['id'], capacity=capacity)

        assert member['package_id'] == dataset['id']
        assert member['user_id'] == user['id']
        assert member['capacity'] == capacity

        assert model.Session.query(model.PackageMember).count() == 1

    def test_update(self):

        dataset = factories.Dataset()
        user = factories.User()
        capacity = 'editor'

        helpers.call_action(
            'package_collaborator_create',
            id=dataset['id'], user_id=user['id'], capacity=capacity)

        helpers.call_action(
            'package_collaborator_create',
            id=dataset['id'], user_id=user['id'], capacity='member')

        assert model.Session.query(model.PackageMember).count() == 1

        assert model.Session.query(model.PackageMember).one().capacity == 'member'

    def test_create_wrong_capacity(self):
        dataset = factories.Dataset()
        user = factories.User()
        capacity = 'unknown'

        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                'package_collaborator_create',
                id=dataset['id'], user_id=user['id'], capacity=capacity)

    def test_create_dataset_not_found(self):
        dataset = {'id': 'xxx'}
        user = factories.User()
        capacity = 'editor'

        with pytest.raises(logic.NotFound):
            helpers.call_action(
                'package_collaborator_create',
                id=dataset['id'], user_id=user['id'], capacity=capacity)

    def test_create_user_not_found(self):
        dataset = factories.Dataset()
        user = {'id': 'yyy'}
        capacity = 'editor'

        with pytest.raises(logic.NotFound):
            helpers.call_action(
                'package_collaborator_create',
                id=dataset['id'], user_id=user['id'], capacity=capacity)


@pytest.mark.usefixtures("clean_db")
class TestUserPluginExtras(object):

    def test_stored_on_create_if_sysadmin(self):

        sysadmin = factories.Sysadmin()

        user_dict = {
            'name': 'test-user',
            'email': 'test@example.com',
            'password': '12345678',
            'plugin_extras': {
                'plugin1': {
                    'key1': 'value1'
                }
            }
        }

        # helpers.call_action sets 'ignore_auth' to True by default
        context = {'user': sysadmin['name'], 'ignore_auth': False}

        created_user = helpers.call_action(
            'user_create', context=context, **user_dict)

        assert created_user['plugin_extras'] == {
            'plugin1': {
                'key1': 'value1',
            }
        }

        user_dict = helpers.call_action(
            'user_show', context=context, id=created_user['id'], include_plugin_extras=True)

        assert user_dict['plugin_extras'] == {
            'plugin1': {
                'key1': 'value1',
            }
        }

        plugin_extras_from_db = model.Session.execute(
            'SELECT plugin_extras FROM "user" WHERE id=:id',
            {'id': created_user['id']}
        ).first().values()[0]

        assert plugin_extras_from_db == {
            'plugin1': {
                'key1': 'value1',
            }
        }

    def test_ignored_on_create_if_non_sysadmin(self):

        author = factories.User()
        sysadmin = factories.Sysadmin()

        user_dict = {
            'name': 'test-user',
            'email': 'test@example.com',
            'password': '12345678',
            'plugin_extras': {
                'plugin1': {
                    'key1': 'value1'
                }
            }
        }

        # helpers.call_action sets 'ignore_auth' to True by default
        context = {'user': author['name'], 'ignore_auth': False}

        created_user = helpers.call_action(
            'user_create', context=context, **user_dict)

        assert 'plugin_extras' not in created_user

        context = {'user': sysadmin['name'], 'ignore_auth': False}
        user = helpers.call_action(
            'user_show', context=context, id=created_user['id'], include_plugin_extras=True)

        assert user['plugin_extras'] is None


@pytest.mark.usefixtures("clean_db")
class TestUserImageUrl(object):

    def test_upload_picture(self):

        params = {
            'name': 'test_user',
            'email': 'test@example.com',
            'password': '12345678',
            'image_url': 'https://example.com/mypic.png',
        }

        user_dict = helpers.call_action('user_create', {}, **params)

        assert user_dict['image_url'] == 'https://example.com/mypic.png'
        assert user_dict['image_display_url'] == 'https://example.com/mypic.png'
