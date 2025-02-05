# encoding: utf-8
"""Unit tests for ckan/logic/action/create.py.

"""
import datetime
import operator
import unittest.mock as mock
import pytest


import ckan.logic as logic
from ckan.logic.action.get import package_show as core_package_show
import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
from ckan.common import config
from ckan.lib.navl.dictization_functions import DataError

from freezegun import freeze_time


@pytest.mark.usefixtures("non_clean_db")
class TestUserInvite(object):
    @mock.patch("ckan.lib.mailer.send_invite")
    def test_invited_user_is_created_as_pending(self, _):
        invited_user = self._invite_user_to_group(factories.User.stub().email)

        assert invited_user is not None
        assert invited_user.is_pending()

    @mock.patch("ckan.lib.mailer.send_invite")
    def test_creates_user_with_valid_username(self, _):
        name = factories.User.stub().name
        email = f"user$%+abc@{name}.com"
        invited_user = self._invite_user_to_group(email)

        assert invited_user.name.startswith("user---abc"), invited_user

    @mock.patch("ckan.lib.mailer.send_invite")
    def test_assigns_user_to_group_in_expected_role(self, _):
        role = "admin"
        invited_user = self._invite_user_to_group(
            factories.User.stub().email, role=role
        )

        group_ids = invited_user.get_group_ids(capacity=role)
        assert len(group_ids) == 1, group_ids

    @mock.patch("ckan.lib.mailer.send_invite")
    def test_sends_invite(self, send_invite):
        invited_user = self._invite_user_to_group(factories.User.stub().email)

        assert send_invite.called
        assert send_invite.call_args[0][0].id == invited_user.id

    @mock.patch("ckan.lib.mailer.send_invite")
    @mock.patch("random.SystemRandom")
    def test_works_even_if_username_already_exists(self, rand, _):
        # usernames
        rand.return_value.random.side_effect = [1000, 1000, 2000, 3000]
        # passwords (need to set something, otherwise choice will break)
        rand.return_value.choice.side_effect = "TestPassword1" * 3
        name = factories.User.stub().name
        for _ in range(3):
            invited_user = self._invite_user_to_group(
                email="same{}@{}.com".format(_, name)
            )
            assert invited_user is not None, invited_user

    @mock.patch("ckan.lib.mailer.send_invite")
    def test_requires_email(self, _):
        with pytest.raises(logic.ValidationError):
            self._invite_user_to_group(email=None)

    @mock.patch("ckan.lib.mailer.send_invite")
    def test_existed_email(self, _):
        factories.User(email="email@example.com")
        with pytest.raises(logic.ValidationError):
            self._invite_user_to_group(email="email@example.com")

    @mock.patch("ckan.lib.mailer.send_invite")
    def test_requires_role(self, _):
        with pytest.raises(logic.ValidationError):
            self._invite_user_to_group(factories.User.stub().email, role=None)

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
            self._invite_user_to_group(
                factories.User.stub().email, group={"id": None}
            )

    @mock.patch("ckan.lib.mailer.send_invite")
    def test_user_name_lowercase_when_email_is_uppercase(self, _):
        name = factories.User.stub().name
        invited_user = self._invite_user_to_group(email=f"Maria@{name}.com")

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

    def _invite_user_to_group(self, email, group=None, role="member"):
        user = factories.User()
        group = group or factories.Group(user=user)

        context = {"user": user["name"]}
        params = {"email": email, "group_id": group["id"], "role": role}

        result = helpers.call_action("user_invite", context, **params)

        return model.User.get(result["id"])


@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
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
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
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
        config["ckan.views.default_views"] = ["image_view"]

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
        config["ckan.views.default_views"] = ["image_view"]

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
        config["ckan.views.default_views"] = ["image_view"]

        context = {"user": helpers.call_action("get_site_user")["name"]}
        created_views = helpers.call_action(
            "resource_create_default_resource_views",
            context,
            resource=resource_dict,
        )

        assert len(created_views) == 1

        assert created_views[0]["view_type"] == "image_view"


@pytest.mark.usefixtures("non_clean_db")
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

    def test_invalid_characters_in_id(self):

        data_dict = {
            "id": "../../nope.txt",
            "package_id": factories.Dataset()["id"],
            "url": "http://data",
            "name": "A nice resource",
        }

        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_create", **data_dict)

    def test_id_too_long(self):

        data_dict = {
            "id": "x" * 111,
            "package_id": factories.Dataset()["id"],
            "url": "http://data",
            "name": "A nice resource",
        }

        with pytest.raises(logic.ValidationError):
            helpers.call_action("resource_create", **data_dict)

    def test_id_already_exists(self):
        data_dict = {
            'id': 'wont-be-fooled-again',
            'package_id': factories.Dataset()['id'],
        }
        helpers.call_action('resource_create', **data_dict)

        data_dict['package_id'] = factories.Dataset()['id']

        with pytest.raises(logic.ValidationError):
            helpers.call_action('resource_create', **data_dict)

    def test_doesnt_require_url(self):
        dataset = factories.Dataset()
        data_dict = {"package_id": dataset["id"]}
        new_resouce = helpers.call_action("resource_create", **data_dict)

        data_dict = {"id": new_resouce["id"]}
        stored_resource = helpers.call_action("resource_show", **data_dict)

        assert not stored_resource["url"]

    def test_mimetype_by_url(self, monkeypatch, ckan_config, tmpdir):
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
        monkeypatch.setitem(ckan_config, u'ckan.storage_path', str(tmpdir))
        result = helpers.call_action("resource_create", context, **params)

        mimetype = result.pop("mimetype")

        assert mimetype
        assert mimetype == "text/csv"

    def test_mimetype_by_url_without_path(self):
        """
        The mimetype should not be guessed from url if url contains only domain

        """
        context = {}
        params = {
            "package_id": factories.Dataset()["id"],
            "url": "http://example.com",
            "name": "A nice resource",
        }
        result = helpers.call_action("resource_create", context, **params)

        mimetype = result.pop("mimetype")
        assert mimetype is None

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
            content,
            "test.json",
            url="http://data",
            package_id=factories.Dataset()[u"id"],
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
            content,
            "test.csv",
            url="http://data",
            package_id=factories.Dataset()[u"id"],
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
            content,
            "test.csv",
            url="http://data",
            package_id=factories.Dataset()[u"id"],
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

    def test_extras(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)

        resource = helpers.call_action(
            "resource_create",
            package_id=dataset["id"],
            somekey="somevalue",  # this is how to do resource extras
            extras={u"someotherkey": u"alt234"},  # this isn't
            subobject={u"hello": u"there"},  # JSON objects supported
            sublist=[1, 2, 3],  # JSON lists supported
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

    @freeze_time("2020-02-25 12:00:00")
    def test_metadata_modified_is_set_to_utcnow_when_created(self):
        context = {}
        params = {
            "package_id": factories.Dataset()["id"],
            "url": "http://data",
            "name": "A nice resource",
        }
        result = helpers.call_action("resource_create", context, **params)

        assert (
            result["metadata_modified"]
            == datetime.datetime.utcnow().isoformat()
        )

    @pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
    @pytest.mark.ckan_config("ckan.auth.allow_admin_collaborators", True)
    @pytest.mark.parametrize("role", ["admin", "editor"])
    def test_collaborators_can_create_resources(self, role):

        org1 = factories.Organization()
        dataset = factories.Dataset(owner_org=org1["id"])

        user = factories.User()

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity=role,
        )

        context = {
            "user": user["name"],
            "ignore_auth": False,
        }

        created_resource = helpers.call_action(
            "resource_create",
            context=context,
            package_id=dataset["id"],
            name="created by collaborator",
            url="https://example.com",
        )

        assert created_resource["name"] == "created by collaborator"

    def test_resource_create_for_update(self):

        dataset = factories.Dataset()

        mock_package_show = mock.MagicMock()
        mock_package_show.side_effect = lambda context, data_dict: core_package_show(context, data_dict)

        with mock.patch.dict('ckan.logic._actions', {'package_show': mock_package_show}):
            helpers.call_action('resource_create', package_id=dataset['id'], url='http://example.com', description='hey')
            assert mock_package_show.call_args_list[0][0][0].get('for_update') is True


@pytest.mark.usefixtures("non_clean_db")
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
                "group_member_create",
                username=factories.User.stub().name,
                role="member",
            )

    def test_group_member_creation_raises_validation_error_if_username_missing(
        self,
    ):

        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "group_member_create", id="someid", role="member"
            )

    def test_group_member_creation_raises_validation_error_if_role_missing(
        self, faker
    ):

        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "group_member_create",
                id=faker.uuid4(),
                username=factories.User.stub().name,
            )

    def test_org_member_creation_raises_validation_error_if_id_missing(self):

        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "organization_member_create",
                username=factories.User.stub().name,
                role="member",
            )

    def test_org_member_creation_raises_validation_error_if_username_missing(
        self,
    ):

        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "organization_member_create",
                id=factories.Group.stub().name,
                role="member",
            )

    def test_org_member_creation_raises_validation_error_if_role_missing(self, faker):

        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "organization_member_create",
                id=faker.uuid4(),
                username=factories.User.stub().name,
            )


@pytest.mark.usefixtures("non_clean_db")
class TestDatasetCreate(object):
    def test_private_package(self):
        org = factories.Organization()
        stub = factories.Dataset.stub()
        with pytest.raises(logic.ValidationError):
            pkg = helpers.call_action(
                "package_create", name=stub.name, private=True
            )

        pkg = helpers.call_action(
            "package_create", owner_org=org["id"], name=stub.name
        )
        assert not pkg["private"]
        pkg = helpers.call_action(
            "package_create",
            owner_org=org["id"],
            name=factories.Dataset.stub().name,
            private=False,
        )
        assert not pkg["private"]
        pkg = helpers.call_action(
            "package_create",
            owner_org=org["id"],
            name=factories.Dataset.stub().name,
            private=True,
        )
        assert pkg["private"]

    def test_normal_user_cant_set_id(self):
        user = factories.User()
        context = {"user": user["name"], "ignore_auth": False}
        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "package_create",
                context=context,
                id=factories.Dataset.stub().name,
                name=factories.Dataset.stub().name,
            )

    def test_sysadmin_can_set_id(self):
        user = factories.Sysadmin()
        context = {"user": user["name"], "ignore_auth": False}
        stub = factories.Dataset.stub()
        dataset = helpers.call_action(
            "package_create", context=context, id=stub.name, name=stub.name
        )
        assert dataset["id"] == stub.name

    def test_context_is_not_polluted(self):
        user = factories.Sysadmin()
        stub = factories.Dataset.stub()
        context = {"user": user["name"], "ignore_auth": False}
        helpers.call_action(
            "package_create", context=context, id=stub.name, name=stub.name
        )
        assert "id" not in context
        assert "package" not in context

    def test_id_cant_already_exist(self):
        dataset = factories.Dataset()
        factories.Sysadmin()
        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "package_create",
                id=dataset["id"],
                name=factories.Dataset.stub().name,
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
        stub = factories.Dataset.stub()
        dataset = helpers.call_action("package_create", name=stub.name)

        assert dataset["name"] == stub.name
        assert (
            helpers.call_action("package_show", id=dataset["id"])["name"]
            == stub.name
        )

    def test_title(self):
        dataset = helpers.call_action(
            "package_create",
            name=factories.Dataset.stub().name,
            title="New Title",
        )

        assert dataset["title"] == "New Title"
        assert (
            helpers.call_action("package_show", id=dataset["id"])["title"]
            == "New Title"
        )

    def test_extras(self):
        dataset = helpers.call_action(
            "package_create",
            name=factories.Dataset.stub().name,
            title="Test Extras",
            extras=[{"key": "original media", "value": '"book"'}],
        )

        assert dataset["extras"][0]["key"] == "original media"
        assert dataset["extras"][0]["value"] == '"book"'
        dataset = helpers.call_action("package_show", id=dataset["id"])
        assert dataset["extras"][0]["key"] == "original media"
        assert dataset["extras"][0]["value"] == '"book"'

    def test_license(self):
        dataset = helpers.call_action(
            "package_create",
            name=factories.Dataset.stub().name,
            title="Test License",
            license_id="other-open",
        )

        assert dataset["license_id"] == "other-open"
        dataset = helpers.call_action("package_show", id=dataset["id"])
        assert dataset["license_id"] == "other-open"

    def test_notes(self):
        dataset = helpers.call_action(
            "package_create",
            name=factories.Dataset.stub().name,
            title="Test Notes",
            notes="some notes",
        )

        assert dataset["notes"] == "some notes"
        dataset = helpers.call_action("package_show", id=dataset["id"])
        assert dataset["notes"] == "some notes"

    def test_resources(self):
        dataset = helpers.call_action(
            "package_create",
            name=factories.Dataset.stub().name,
            title="Test Resources",
            resources=[
                {
                    "alt_url": u"alt123",
                    "description": u"Full text.",
                    "somekey": "somevalue",  # this is how to do resource extras
                    "extras": {u"someotherkey": u"alt234"},  # this isn't
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
        tag1 = factories.Tag.stub().name
        tag2 = factories.Tag.stub().name
        dataset = helpers.call_action(
            "package_create",
            name=factories.Dataset.stub().name,
            title="Test Tags",
            tags=[{"name": tag1}, {"name": tag2}],
        )

        tag_names = sorted([tag_dict["name"] for tag_dict in dataset["tags"]])
        assert tag_names == sorted([tag1, tag2])
        dataset = helpers.call_action("package_show", id=dataset["id"])
        tag_names = sorted([tag_dict["name"] for tag_dict in dataset["tags"]])
        assert tag_names == sorted([tag1, tag2])

    def test_return_id_only(self):
        dataset = helpers.call_action(
            "package_create",
            name=factories.Dataset.stub().name,
            context={"return_id_only": True},
        )

        assert isinstance(dataset, str)


@pytest.mark.usefixtures("non_clean_db")
class TestGroupCreate(object):
    def test_create_group(self):
        user = factories.User()
        context = {"user": user["name"], "ignore_auth": True}

        group = helpers.call_action(
            "group_create", context=context, name=factories.Group.stub().name
        )

        assert len(group["users"]) == 1
        assert group["display_name"] == group["name"]
        assert group["package_count"] == 0
        assert not group["is_organization"]
        assert group["type"] == "group"

    def test_create_group_validation_fail(self):
        user = factories.User()
        context = {"user": user["name"], "ignore_auth": True}

        with pytest.raises(logic.ValidationError):
            helpers.call_action(
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
            "group_create", context=context, name=factories.Group.stub().name
        )

        assert isinstance(group, str)
        assert re.match(r"([a-f\d]{8}(-[a-f\d]{4}){3}-[a-f\d]{12}?)", group)

    def test_create_matches_show(self):
        user = factories.User()
        context = {"user": user["name"], "ignore_auth": True}

        created = helpers.call_action(
            "organization_create",
            context=context,
            name=factories.Organization.stub().name,
        )

        shown = helpers.call_action(
            "organization_show", context=context, id=created["name"]
        )

        assert sorted(created.keys()) == sorted(shown.keys())
        for k in created.keys():
            assert created[k] == shown[k], k


@pytest.mark.usefixtures("non_clean_db")
class TestOrganizationCreate(object):
    def test_create_organization(self):
        user = factories.User()
        context = {"user": user["name"], "ignore_auth": True}

        org = helpers.call_action(
            "organization_create",
            context=context,
            name=factories.Organization.stub().name,
        )

        assert len(org["users"]) == 1
        assert org["display_name"] == org["name"]
        assert org["package_count"] == 0
        assert org["is_organization"]
        assert org["type"] == "organization"

    def test_create_organization_validation_fail(self):
        user = factories.User()
        context = {"user": user["name"], "ignore_auth": True}

        with pytest.raises(logic.ValidationError):
            helpers.call_action(
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
            "organization_create",
            context=context,
            name=factories.Organization.stub().name,
        )

        assert isinstance(org, str)
        assert re.match(r"([a-f\d]{8}(-[a-f\d]{4}){3}-[a-f\d]{12}?)", org)

    def test_create_matches_show(self):
        user = factories.User()
        context = {"user": user["name"], "ignore_auth": True}

        created = helpers.call_action(
            "organization_create",
            context=context,
            name=factories.Organization.stub().name,
        )

        shown = helpers.call_action(
            "organization_show", context=context, id=created["name"]
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
            name=factories.Organization.stub().name,
            type=custom_org_type,
        )

        assert len(org["users"]) == 1
        assert org["display_name"] == org["name"]
        assert org["package_count"] == 0
        assert org["is_organization"]
        assert org["type"] == custom_org_type


@pytest.mark.usefixtures("non_clean_db")
class TestUserCreate(object):
    def test_user_create_with_password_hash(self):
        sysadmin = factories.Sysadmin()
        context = {"user": sysadmin["name"]}

        user = helpers.call_action(
            "user_create",
            context=context,
            email=factories.User.stub().email,
            name=factories.User.stub().name,
            password_hash="pretend-this-is-a-valid-hash",
        )

        user_obj = model.User.get(user["id"])
        assert user_obj.password == "pretend-this-is-a-valid-hash"

    @pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
    def test_user_create_password_hash_not_for_normal_users(self):
        normal_user = factories.User()
        context = {"user": normal_user["name"], "ignore_auth": False}

        user = helpers.call_action(
            "user_create",
            context=context,
            email=factories.User.stub().email,
            name=factories.User.stub().name,
            password="required",
            password_hash="pretend-this-is-a-valid-hash",
        )

        user_obj = model.User.get(user["id"])
        assert user_obj.password != "pretend-this-is-a-valid-hash"

    def test_user_create_basic_fields(self):
        email = factories.User.stub().email
        name = factories.User.stub().name
        user = helpers.call_action(
            "user_create",
            email=email,
            name=name,
            password="required",
        )
        assert user["email"] == email
        assert user["name"] == name
        assert "password" not in user

    def test_user_create_parameters_missing(self):
        with pytest.raises(logic.ValidationError) as err:
            helpers.call_action("user_create")
        assert err.value.error_dict == {
            "email": ["Missing value"],
            "name": ["Missing value"],
            "password": ["Missing value"],
        }

    def test_user_create_wrong_password(self):
        stub = factories.User.stub()
        user_dict = {
            "name": stub.name,
            "email": stub.email,
            "password": "tes",
        }  # Too short

        with pytest.raises(logic.ValidationError) as err:
            helpers.call_action("user_create", **user_dict)
        assert err.value.error_dict == {
            "password": ["Your password must be 8 characters or longer"]
        }

    def test_user_create_defer_commit(self):
        stub = factories.User.stub()
        user_dict = {
            "name": stub.name,
            "email": stub.email,
            "password": "test1234",
        }
        context = {"defer_commit": True}

        helpers.call_action("user_create", context=context, **user_dict)

        model.Session.close()

        with pytest.raises(logic.NotFound):
            helpers.call_action("user_show", id=user_dict["name"])


@pytest.mark.usefixtures("clean_db")
@pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
class TestUserCreateDb():

    def test_anon_user_create_does_not_update(self):
        user1 = factories.User(about="This is user 1")
        user_dict = {
            "id": user1["id"],
            "name": "some_name",
            "email": "some_email@example.com",
            "password": "test1234",
        }

        context = {
            "user": None,
            "ignore_auth": False,
        }

        user2 = helpers.call_action("user_create", context=context, **user_dict)
        assert user2["id"] != user1["id"]
        assert user2["about"] != "This is user 1"

    def test_normal_user_create_does_not_update(self):
        user1 = factories.User(about="This is user 1")
        user_dict = {
            "id": user1["id"],
            "name": "some_name",
            "email": "some_email@example.com",
            "password": "test1234",
        }

        context = {
            "user": factories.User()["name"],
            "ignore_auth": False,
        }

        user2 = helpers.call_action("user_create", context=context, **user_dict)
        assert user2["id"] != user1["id"]
        assert user2["about"] != "This is user 1"

    def test_sysadmin_user_create_does_not_update(self):
        user1 = factories.User(about="This is user 1")
        user_dict = {
            "id": user1["id"],
            "name": "some_name",
            "email": "some_email@example.com",
            "password": "test1234",
        }

        context = {
            "user": factories.Sysadmin()["name"],
            "ignore_auth": False,
        }

        user2 = helpers.call_action("user_create", context=context, **user_dict)
        assert user2["id"] != user1["id"]
        assert user2["about"] != "This is user 1"

    def test_anon_users_can_not_provide_custom_id(self):

        user_dict = {
            "id": "custom_id",
            "name": "some_name",
            "email": "some_email@example.com",
            "password": "test1234",
        }

        context = {
            "user": None,
            "ignore_auth": False,
        }

        user = helpers.call_action("user_create", context=context, **user_dict)
        assert user["id"] != "custom_id"

    def test_normal_users_can_not_provide_custom_id(self):

        user_dict = {
            "id": "custom_id",
            "name": "some_name",
            "email": "some_email@example.com",
            "password": "test1234",
        }

        context = {
            "user": factories.User()["name"],
            "ignore_auth": False,
        }

        user = helpers.call_action("user_create", context=context, **user_dict)
        assert user["id"] != "custom_id"

    def test_sysadmin_can_provide_custom_id(self):

        user_dict = {
            "id": "custom_id",
            "name": "some_name",
            "email": "some_email@example.com",
            "password": "test1234",
        }
        context = {
            "user": factories.Sysadmin()["name"],
            "ignore_auth": False,
        }

        user = helpers.call_action("user_create", context=context, **user_dict)
        assert user["id"] == "custom_id"


@pytest.mark.usefixtures("non_clean_db")
class TestFollowCommon(object):
    def test_validation(self):
        user = factories.User()
        unfollow_actions = (
            "unfollow_user",
            "unfollow_dataset",
            "unfollow_group",
        )
        follow_actions = ("follow_user", "follow_dataset", "follow_group")
        count_actions = (
            "user_follower_count",
            "dataset_follower_count",
            "group_follower_count",
        )
        list_actions = (
            "user_follower_list",
            "dataset_follower_list",
            "group_follower_list",
        )
        my_actions = (
            "am_following_dataset",
            "am_following_user",
            "am_following_group",
        )
        for action in (
            follow_actions
            + unfollow_actions
            + count_actions
            + list_actions
            + my_actions
        ):
            for object_id in ("bad id", "     ", 3, 35.7, "xxx", None, ""):
                with pytest.raises(logic.ValidationError):
                    context = {"user": user["name"]}
                    helpers.call_action(action, context, id=object_id)


@pytest.mark.usefixtures("non_clean_db")
class TestFollowDataset(object):
    def test_auth(self):
        user = factories.User()
        dataset = factories.Dataset()
        context = {"user": "", "ignore_auth": False}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_action("follow_dataset", context, id=dataset["id"])
        context = {"user": user["name"], "ignore_auth": False}
        helpers.call_action("follow_dataset", context, id=dataset["id"])

    def test_follow_dataset(self):
        user = factories.User()
        dataset = factories.Dataset()
        context = {"user": user["name"]}
        assert (
            helpers.call_action("dataset_follower_count", id=dataset["id"])
            == 0
        )
        assert (
            helpers.call_action("dataset_follower_list", id=dataset["id"])
            == []
        )
        assert not helpers.call_action(
            "am_following_dataset", context, id=dataset["id"]
        )

        helpers.call_action("follow_dataset", context, id=dataset["id"])
        assert (
            helpers.call_action("dataset_follower_count", id=dataset["id"])
            == 1
        )
        assert [
            u["name"]
            for u in helpers.call_action(
                "dataset_follower_list", id=dataset["id"]
            )
        ] == [user["name"]]
        assert helpers.call_action(
            "am_following_dataset", context, id=dataset["id"]
        )

        helpers.call_action("unfollow_dataset", context, id=dataset["id"])
        assert (
            helpers.call_action("dataset_follower_count", id=dataset["id"])
            == 0
        )
        assert (
            helpers.call_action("dataset_follower_list", id=dataset["id"])
            == []
        )
        assert not helpers.call_action(
            "am_following_dataset", context, id=dataset["id"]
        )


@pytest.mark.usefixtures("non_clean_db")
class TestFollowGroup(object):
    def test_auth(self):
        user = factories.User()
        group = factories.Group()
        context = {"user": "", "ignore_auth": False}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_action("follow_group", context, id=group["id"])
        context = {"user": user["name"], "ignore_auth": False}
        helpers.call_action("follow_group", context, id=group["id"])

    def test_follow_group(self):
        user = factories.User()
        group = factories.Group()
        context = {"user": user["name"]}
        assert helpers.call_action("group_follower_count", id=group["id"]) == 0
        assert helpers.call_action("group_follower_list", id=group["id"]) == []
        assert not helpers.call_action(
            "am_following_group", context, id=group["id"]
        )

        helpers.call_action("follow_group", context, id=group["id"])
        assert helpers.call_action("group_follower_count", id=group["id"]) == 1
        assert [
            u["name"]
            for u in helpers.call_action("group_follower_list", id=group["id"])
        ] == [user["name"]]
        assert helpers.call_action(
            "am_following_group", context, id=group["id"]
        )

        helpers.call_action("unfollow_group", context, id=group["id"])
        assert helpers.call_action("group_follower_count", id=group["id"]) == 0
        assert helpers.call_action("group_follower_list", id=group["id"]) == []
        assert not helpers.call_action(
            "am_following_group", context, id=group["id"]
        )


@pytest.mark.usefixtures("non_clean_db")
class TestFollowOrganization(object):
    def test_auth(self):
        user = factories.User()
        organization = factories.Organization()
        context = {"user": "", "ignore_auth": False}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_action("follow_group", context, id=organization["id"])
        context = {"user": user["name"], "ignore_auth": False}
        helpers.call_action("follow_group", context, id=organization["id"])

    def test_follow_organization(self):
        user = factories.User()
        group = factories.Organization()
        context = {"user": user["name"]}
        assert helpers.call_action("group_follower_count", id=group["id"]) == 0
        assert helpers.call_action("group_follower_list", id=group["id"]) == []
        assert not helpers.call_action(
            "am_following_group", context, id=group["id"]
        )

        helpers.call_action("follow_group", context, id=group["id"])
        assert helpers.call_action("group_follower_count", id=group["id"]) == 1
        assert [
            u["name"]
            for u in helpers.call_action("group_follower_list", id=group["id"])
        ] == [user["name"]]
        assert helpers.call_action(
            "am_following_group", context, id=group["id"]
        )

        helpers.call_action("unfollow_group", context, id=group["id"])
        assert helpers.call_action("group_follower_count", id=group["id"]) == 0
        assert helpers.call_action("group_follower_list", id=group["id"]) == []
        assert not helpers.call_action(
            "am_following_group", context, id=group["id"]
        )


@pytest.mark.usefixtures("non_clean_db")
class TestFollowUser(object):
    def test_auth(self):
        user = factories.User()
        second_user = factories.User()

        context = {"user": "", "ignore_auth": False}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_action("follow_user", context, id=second_user["id"])
        context = {"user": user["name"], "ignore_auth": False}
        helpers.call_action("follow_user", context, id=second_user["id"])

    def test_cannot_follow_myself(self):
        user = factories.User()
        context = {"user": user["name"]}
        with pytest.raises(logic.ValidationError):
            helpers.call_action("follow_user", context, id=user["id"])

    def test_follow_user(self):
        user = factories.User()
        another_user = factories.User()
        context = {"user": user["name"]}
        assert (
            helpers.call_action("user_follower_count", id=another_user["id"])
            == 0
        )
        assert (
            helpers.call_action("user_follower_list", id=another_user["id"])
            == []
        )
        assert not helpers.call_action(
            "am_following_user", context, id=another_user["id"]
        )

        helpers.call_action("follow_user", context, id=another_user["id"])
        assert (
            helpers.call_action("user_follower_count", id=another_user["id"])
            == 1
        )
        assert [
            u["name"]
            for u in helpers.call_action(
                "user_follower_list", id=another_user["id"]
            )
        ] == [user["name"]]
        assert helpers.call_action(
            "am_following_user", context, id=another_user["id"]
        )

        helpers.call_action("unfollow_user", context, id=another_user["id"])
        assert (
            helpers.call_action("user_follower_count", id=another_user["id"])
            == 0
        )
        assert (
            helpers.call_action("user_follower_list", id=another_user["id"])
            == []
        )
        assert not helpers.call_action(
            "am_following_user", context, id=another_user["id"]
        )


@pytest.mark.usefixtures("non_clean_db")
class TestApiToken(object):
    def test_token_created(self):
        from ckan.lib.api_token import decode

        user = factories.User()
        data = helpers.call_action(
            u"api_token_create",
            context={u"model": model, u"user": user[u"name"]},
            user=user[u"name"],
            name=u"token-name",
        )
        token = data[u"token"]
        jti = decode(token)[u"jti"]
        res = model.ApiToken.get(jti)
        assert res.user_id == user[u"id"]
        assert res.last_access is None
        assert res.id == jti


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", False)
def test_create_package_collaborator_when_config_disabled():

    dataset = factories.Dataset()
    user = factories.User()
    capacity = "editor"

    with pytest.raises(logic.ValidationError):
        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity=capacity,
        )


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.allow_dataset_collaborators", True)
class TestPackageMemberCreate(object):
    def test_create(self):
        initial = model.Session.query(model.PackageMember).count()
        dataset = factories.Dataset()
        user = factories.User()
        capacity = "editor"

        member = helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity=capacity,
        )

        assert member["package_id"] == dataset["id"]
        assert member["user_id"] == user["id"]
        assert member["capacity"] == capacity

        assert model.Session.query(model.PackageMember).count() == initial + 1

    def test_update(self):
        dataset = factories.Dataset()
        user = factories.User()
        capacity = "editor"

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity=capacity,
        )

        helpers.call_action(
            "package_collaborator_create",
            id=dataset["id"],
            user_id=user["id"],
            capacity="member",
        )

        assert (
            model.Session.query(model.PackageMember)
            .filter_by(package_id=dataset["id"])
            .one()
            .capacity
            == "member"
        )

    def test_create_wrong_capacity(self):
        dataset = factories.Dataset()
        user = factories.User()
        capacity = "unknown"

        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "package_collaborator_create",
                id=dataset["id"],
                user_id=user["id"],
                capacity=capacity,
            )

    def test_create_dataset_not_found(self):
        dataset = {"id": "xxx"}
        user = factories.User()
        capacity = "editor"

        with pytest.raises(logic.NotFound):
            helpers.call_action(
                "package_collaborator_create",
                id=dataset["id"],
                user_id=user["id"],
                capacity=capacity,
            )

    def test_create_user_not_found(self):
        dataset = factories.Dataset()
        user = {"id": "yyy"}
        capacity = "editor"

        with pytest.raises(logic.NotFound):
            helpers.call_action(
                "package_collaborator_create",
                id=dataset["id"],
                user_id=user["id"],
                capacity=capacity,
            )


@pytest.mark.usefixtures("non_clean_db")
@pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
class TestUserPluginExtras(object):
    def test_stored_on_create_if_sysadmin(self):

        sysadmin = factories.Sysadmin()
        stub = factories.User.stub()
        user_dict = {
            "name": stub.name,
            "email": stub.email,
            "password": "12345678",
            "plugin_extras": {"plugin1": {"key1": "value1"}},
        }

        # helpers.call_action sets 'ignore_auth' to True by default
        context = {"user": sysadmin["name"], "ignore_auth": False}

        created_user = helpers.call_action(
            "user_create", context=context, **user_dict
        )

        assert created_user["plugin_extras"] == {
            "plugin1": {
                "key1": "value1",
            }
        }

        user_dict = helpers.call_action(
            "user_show",
            context=context,
            id=created_user["id"],
            include_plugin_extras=True,
        )

        assert user_dict["plugin_extras"] == {
            "plugin1": {
                "key1": "value1",
            }
        }

        plugin_extras_from_db = (
            model.Session.execute(
                'SELECT plugin_extras FROM "user" WHERE id=:id',
                {"id": created_user["id"]},
            )
            .first()[0]
        )

        assert plugin_extras_from_db == {
            "plugin1": {
                "key1": "value1",
            }
        }

    def test_ignored_on_create_if_non_sysadmin(self):

        author = factories.User()
        sysadmin = factories.Sysadmin()
        stub = factories.User.stub()
        user_dict = {
            "name": stub.name,
            "email": stub.email,
            "password": "12345678",
            "plugin_extras": {"plugin1": {"key1": "value1"}},
        }

        # helpers.call_action sets 'ignore_auth' to True by default
        context = {"user": author["name"], "ignore_auth": False}

        created_user = helpers.call_action(
            "user_create", context=context, **user_dict
        )

        assert "plugin_extras" not in created_user

        context = {"user": sysadmin["name"], "ignore_auth": False}
        user = helpers.call_action(
            "user_show",
            context=context,
            id=created_user["id"],
            include_plugin_extras=True,
        )

        assert user["plugin_extras"] is None


@pytest.mark.usefixtures("non_clean_db")
class TestUserImageUrl(object):
    def test_external_picture(self):
        stub = factories.User.stub()
        params = {
            "name": stub.name,
            "email": stub.email,
            "password": "12345678",
            "image_url": "https://example.com/mypic.png",
        }

        user_dict = helpers.call_action("user_create", {}, **params)

        assert user_dict["image_url"] == "https://example.com/mypic.png"
        assert (
            user_dict["image_display_url"] == "https://example.com/mypic.png"
        )

    def test_upload_picture_works_without_extra_config(
            self, create_with_upload, faker):
        params = {
            "name": faker.user_name(),
            "email": faker.email(),
            "password": "12345678",
            "action": "user_create",
            "upload_field_name": "image_upload",
        }
        assert create_with_upload(faker.image(), "image.png", **params)

    def test_upload_non_picture_fails_without_extra_config(
            self, create_with_upload, faker):
        params = {
            "name": faker.user_name(),
            "email": faker.email(),
            "password": "12345678",
            "action": "user_create",
            "upload_field_name": "image_upload",
        }
        with pytest.raises(
                logic.ValidationError, match="Unsupported upload type"):
            create_with_upload("hello world", "file.txt", **params)

    def test_upload_non_picture_html_fails_without_extra_config(
            self, create_with_upload, faker):
        params = {
            "name": faker.user_name(),
            "email": faker.email(),
            "password": "12345678",
            "action": "user_create",
            "upload_field_name": "image_upload",
        }
        with pytest.raises(
                logic.ValidationError, match="Unsupported upload type"):
            create_with_upload("<html><body>hello world</body></html>", "file.html", **params)

    def test_upload_svg_fails_without_extra_config(
            self, create_with_upload, faker):
        params = {
            "name": faker.user_name(),
            "email": faker.email(),
            "password": "12345678",
            "action": "user_create",
            "upload_field_name": "image_upload",
        }
        with pytest.raises(
                logic.ValidationError, match="Unsupported upload type"):
            create_with_upload('<svg xmlns="http://www.w3.org/2000/svg"></svg>', "file.svg", **params)

    def test_upload_svg_wrong_extension_fails_without_extra_config(
            self, create_with_upload, faker):
        params = {
            "name": faker.user_name(),
            "email": faker.email(),
            "password": "12345678",
            "action": "user_create",
            "upload_field_name": "image_upload",
        }
        with pytest.raises(
                logic.ValidationError, match="Unsupported upload type"):
            create_with_upload('<svg xmlns="http://www.w3.org/2000/svg"></svg>', "file.png", **params)

    @pytest.mark.ckan_config("ckan.upload.user.types", "image")
    def test_upload_non_picture_with_png_extension(
            self, create_with_upload, faker):
        params = {
            "name": faker.user_name(),
            "email": faker.email(),
            "password": "12345678",
            "action": "user_create",
            "upload_field_name": "image_upload",
        }
        with pytest.raises(
                logic.ValidationError, match="Unsupported upload type"):
            create_with_upload("hello world", "file.png", **params)

    @pytest.mark.ckan_config("ckan.upload.user.mimetypes", "")
    @pytest.mark.ckan_config("ckan.upload.user.types", "")
    def test_uploads_not_allowed_when_empty_mimetypes_and_types(
            self, create_with_upload, faker):
        params = {
            "name": faker.user_name(),
            "email": faker.email(),
            "password": "12345678",
            "action": "user_create",
            "upload_field_name": "image_upload",
        }
        with pytest.raises(
                logic.ValidationError, match="No uploads allowed for object type"):
            create_with_upload("hello world", "file.png", **params)

    @pytest.mark.ckan_config("ckan.upload.user.mimetypes", "*")
    @pytest.mark.ckan_config("ckan.upload.user.types", "image")
    def test_upload_all_types_allowed_needs_both_options(self, create_with_upload, faker):
        params = {
            "name": faker.user_name(),
            "email": faker.email(),
            "password": "12345678",
            "action": "user_create",
            "upload_field_name": "image_upload",
        }
        with pytest.raises(
                logic.ValidationError, match="Unsupported upload type"):
            assert create_with_upload(faker.json(), "file.json", **params)

    @pytest.mark.ckan_config("ckan.upload.user.mimetypes", "*")
    @pytest.mark.ckan_config("ckan.upload.user.types", "*")
    def test_upload_all_types_allowed(self, create_with_upload, faker):
        params = {
            "name": faker.user_name(),
            "email": faker.email(),
            "password": "12345678",
            "action": "user_create",
            "upload_field_name": "image_upload",
        }
        assert create_with_upload(faker.json(), "file.json", **params)

    @pytest.mark.ckan_config("ckan.upload.user.types", "image")
    def test_upload_picture(self, create_with_upload, faker):
        params = {
            "name": faker.user_name(),
            "email": faker.email(),
            "password": "12345678",
            "action": "user_create",
            "upload_field_name": "image_upload",
        }
        assert create_with_upload(faker.image(), "file.png", **params)

    @pytest.mark.ckan_config("ckan.upload.user.types", "image")
    def test_upload_picture_extension_enforced(self, create_with_upload, faker):
        params = {
            "name": faker.user_name(),
            "email": faker.email(),
            "password": "12345678",
            "action": "user_create",
            "upload_field_name": "image_upload",
        }
        user = create_with_upload(faker.image(image_format="jpeg"), "file.png", **params)

        assert user["image_url"].endswith(".jpg")
        assert user["image_display_url"].endswith(".jpg")


class TestVocabularyCreate(object):
    @pytest.mark.usefixtures("non_clean_db")
    def test_basic(self):
        name = factories.Vocabulary.stub().name
        vocab = helpers.call_action("vocabulary_create", name=name)
        obj = model.Vocabulary.get(name)
        assert obj.id == vocab["id"]

    @pytest.mark.usefixtures("non_clean_db")
    def test_with_tags(self):
        name = factories.Vocabulary.stub().name
        tag1 = factories.Tag.stub().name
        tag2 = factories.Tag.stub().name
        tags = [{"name": tag1}, {"name": tag2}]
        helpers.call_action("vocabulary_create", name=name, tags=tags)
        vocab = helpers.call_action("vocabulary_show", id=name)
        assert vocab["name"] == name
        assert len(vocab["tags"]) == 2
        for tag in vocab["tags"]:
            assert tag["vocabulary_id"] == vocab["id"]
            assert tag["name"] in {tag1, tag2}

    @pytest.mark.usefixtures("non_clean_db")
    def test_with_empty_tags(self):
        name = factories.Vocabulary.stub().name
        resp = helpers.call_action("vocabulary_create", name=name, tags=[])
        assert resp["tags"] == []

    @pytest.mark.usefixtures("non_clean_db")
    def test_with_existing_name(self):
        name = factories.Vocabulary.stub().name
        helpers.call_action("vocabulary_create", name=name, tags=[])
        with pytest.raises(logic.ValidationError):
            helpers.call_action("vocabulary_create", name=name, tags=[])

    @pytest.mark.parametrize(
        "tags",
        [
            [{"id": "xxx"}, {"name": "foo"}],
            [{"name": "foo"}, {"name": None}],
            [{"name": "foo"}, {"name": ""}],
            [{"name": "foo"}, {"name": "f"}],
            [{"name": "f" * 200}, {"name": "foo"}],
            [{"name": "Invalid!"}, {"name": "foo"}],
        ],
    )
    def test_with_bad_tags(self, tags):
        name = factories.Vocabulary.stub().name
        with pytest.raises(logic.ValidationError):
            helpers.call_action("vocabulary_create", name=name, tags=tags)

    def test_with_no_tags(self):
        name = factories.Vocabulary.stub().name
        with pytest.raises(DataError):
            helpers.call_action("vocabulary_create", name=name, tags=None)

    def test_id_not_allowed(self):
        name = factories.Vocabulary.stub().name
        with pytest.raises(logic.ValidationError):
            helpers.call_action("vocabulary_create", name=name, id="xxx")

    def test_no_name(self):
        with pytest.raises(logic.ValidationError):
            helpers.call_action("vocabulary_create")

    @pytest.mark.parametrize("name", (None, "", "a", "foobar" * 100))
    def test_invalid_name(self, name):
        with pytest.raises(logic.ValidationError):
            helpers.call_action("vocabulary_create", name=name)


class TestTagCreate:
    @pytest.mark.usefixtures("non_clean_db")
    def test_add_tag_to_vocab(self):
        tag1 = factories.Tag.stub().name
        tag2 = factories.Tag.stub().name
        vocab = factories.Vocabulary(tags=[{"name": tag1}])
        assert set(map(operator.itemgetter("name"), vocab["tags"])) == {tag1}
        helpers.call_action("tag_create", name=tag2, vocabulary_id=vocab["id"])

        vocab = helpers.call_action("vocabulary_show", id=vocab["id"])
        assert set(map(operator.itemgetter("name"), vocab["tags"])) == {
            tag1,
            tag2,
        }

    def test_no_vocab(self):
        with pytest.raises(logic.ValidationError):
            helpers.call_action("tag_create", name=factories.Tag.stub().name)

    def test_does_not_exist(self):
        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "tag_create",
                name=factories.Tag.stub().name,
                vocabulary_id=factories.Vocabulary.stub().name,
            )

    @pytest.mark.usefixtures("non_clean_db")
    def test_duplicate(self):
        tag1 = factories.Tag.stub().name
        vocab = factories.Vocabulary(tags=[{"name": tag1}])
        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "tag_create", name=tag1, vocabulary_id=vocab["id"]
            )

    @pytest.mark.usefixtures("non_clean_db")
    def test_id_not_allowed(self):
        vocab = factories.Vocabulary()
        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "tag_create", name="foo", id="xxx", vocabulary_id=vocab["id"]
            )

    @pytest.mark.usefixtures("non_clean_db")
    def test_name_is_required(self):
        vocab = factories.Vocabulary()
        with pytest.raises(logic.ValidationError):
            helpers.call_action("tag_create", vocabulary_id=vocab["id"])

    @pytest.mark.usefixtures("non_clean_db")
    def test_invalid_name(self):
        vocab = factories.Vocabulary()
        for name in ("Not a valid tag name!", "", None):
            with pytest.raises(logic.ValidationError):
                helpers.call_action(
                    "tag_create", name=name, vocabulary_id=vocab["id"]
                )


@pytest.mark.usefixtures("non_clean_db")
class TestMemberCreate2:
    def test_member_create_accepts_object_name_or_id(self):
        org = factories.Organization()
        package = factories.Dataset()
        helpers.call_action(
            "member_create",
            object=package["id"],
            id=org["id"],
            object_type="package",
            capacity="member",
        )
        helpers.call_action(
            "member_create",
            object=package["name"],
            id=org["id"],
            object_type="package",
            capacity="member",
        )

    def test_member_create_raises_if_user_unauthorized_to_update_group(self):
        org = factories.Organization()
        pkg = factories.Dataset()
        user = factories.User()
        context = {"ignore_auth": False, "user": user["name"]}
        with pytest.raises(logic.NotAuthorized):
            helpers.call_action(
                "member_create",
                context,
                object=pkg["name"],
                id=org["id"],
                object_type="package",
                capacity="member",
            )

    def test_member_create_raises_if_any_required_parameter_isnt_defined(self):
        org = factories.Organization()
        pkg = factories.Dataset()
        data = dict(
            object=pkg["name"],
            id=org["id"],
            object_type="package",
            capacity="member",
        )
        for key in ["id", "object", "object_type"]:
            payload = data.copy()
            payload.pop(key)
            with pytest.raises(logic.ValidationError):
                helpers.call_action("member_create", **payload)

    def test_member_create_raises_if_group_wasnt_found(self):
        pkg = factories.Dataset()
        with pytest.raises(logic.NotFound):
            helpers.call_action(
                "member_create",
                object=pkg["name"],
                id="not-real",
                object_type="package",
                capacity="member",
            )

    def test_member_create_raises_if_object_wasnt_found(self):
        org = factories.Organization()
        with pytest.raises(logic.NotFound):
            helpers.call_action(
                "member_create",
                object="not-real",
                id=org["id"],
                object_type="package",
                capacity="member",
            )

    def test_member_create_raises_if_object_type_is_invalid(self):
        org = factories.Organization()
        pkg = factories.Dataset()
        with pytest.raises(logic.ValidationError):
            helpers.call_action(
                "member_create",
                object=pkg["name"],
                id=org["id"],
                object_type="notvalid",
                capacity="member",
            )


@pytest.mark.usefixtures("clean_db")
class TestPackagePluginData(object):

    def test_stored_on_create_if_sysadmin(self):
        sysadmin = factories.Sysadmin()

        pkg_dict = {
            "name": "test-dataset",
            "plugin_data": {
                "plugin1": {
                    "key1": "value1"
                }
            }
        }
        context = {
            "user": sysadmin["name"],
            "ignore_auth": False,
            "auth_user_obj": model.User.get(sysadmin["name"])
        }
        created_pkg = helpers.call_action(
            "package_create", context=context, **pkg_dict
        )
        assert created_pkg["plugin_data"] == {
            "plugin1": {
                "key1": "value1"
            }
        }
        plugin_data_from_db = model.Session.execute(
            'SELECT plugin_data FROM "package" WHERE id=:id',
            {'id': created_pkg["id"]}
        ).first()[0]

        assert plugin_data_from_db == {"plugin1": {"key1": "value1"}}

    def test_ignored_on_create_if_non_sysadmin(self):
        user = factories.User()

        pkg_dict = {
            "name": "test-dataset",
            "plugin_data": {
                "plugin1": {
                    "key1": "value1"
                }
            }
        }
        context = {
            "user": user["name"],
            "ignore_auth": False,
        }
        created_pkg = helpers.call_action(
            'package_create', context=context, **pkg_dict
        )
        assert "plugin_data" not in created_pkg

        plugin_data_from_db = model.Session.execute(
            'SELECT plugin_data FROM "package" WHERE id=:id',
            {'id': created_pkg["id"]}
        ).first()[0]
        assert plugin_data_from_db is None
