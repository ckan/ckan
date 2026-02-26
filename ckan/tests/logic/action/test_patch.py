# encoding: utf-8
"""Unit tests for ckan/logic/action/patch.py."""
import pytest

from unittest import mock

from ckan.tests import helpers, factories
from ckan.logic.action.get import package_show as core_package_show
from ckan.logic import ValidationError
from ckan.plugins.toolkit import config
from ckan import model


@pytest.mark.usefixtures("non_clean_db")
class TestPatch(object):
    def test_package_patch_updating_single_field(self):
        user = factories.User()
        dataset = factories.Dataset(notes="some test now", user=user)
        stub = factories.Dataset.stub()
        dataset = helpers.call_action(
            "package_patch", id=dataset["id"], name=stub.name
        )

        assert dataset["name"] == stub.name
        assert dataset["notes"] == "some test now"

        dataset2 = helpers.call_action("package_show", id=dataset["id"])

        assert dataset2["name"] == stub.name
        assert dataset2["notes"] == "some test now"

    def test_package_patch_invalid_characters_in_resource_id(self):
        user = factories.User()
        dataset = factories.Dataset(user=user)

        with pytest.raises(ValidationError):
            helpers.call_action(
                "package_patch",
                id=dataset["id"],
                resources=[
                    {
                        "id": "../../nope.txt",
                        "url": "http://data",
                        "name": "A nice resource",
                    },
                ],
            )

    def test_resource_patch_updating_single_field(self):
        user = factories.User()
        dataset = factories.Dataset(
            notes="some test now",
            user=user,
            resources=[{"url": "http://example.com/resource"}],
        )

        resource = helpers.call_action(
            "resource_patch",
            id=dataset["resources"][0]["id"],
            name="somethingnew",
        )

        assert resource["name"] == "somethingnew"
        assert resource["url"] == "http://example.com/resource"

        dataset2 = helpers.call_action("package_show", id=dataset["id"])

        resource2 = dataset2["resources"][0]
        assert resource2["name"] == "somethingnew"
        assert resource2["url"] == "http://example.com/resource"

    def test_group_patch_updating_single_field(self):
        user = factories.User()
        group = factories.Group(description="some test now", user=user)
        name = group["name"]
        group = helpers.call_action(
            "group_patch",
            id=group["id"],
            description="somethingnew",
            context={"user": user["name"]},
        )

        assert group["name"] == name
        assert group["description"] == "somethingnew"

        group2 = helpers.call_action("group_show", id=group["id"])

        assert group2["name"] == name
        assert group2["description"] == "somethingnew"

    @pytest.mark.ckan_config(u"ckan.auth.public_user_details", u"false")
    def test_group_patch_updating_single_field_when_public_user_details_is_false(
        self,
    ):
        user = factories.User()
        group = factories.Group(description="some test now", user=user)
        name = group["name"]
        group = helpers.call_action(
            "group_patch",
            id=group["id"],
            description="somethingnew",
            context={"user": user["name"]},
        )

        assert group["name"] == name
        assert group["description"] == "somethingnew"

        group2 = helpers.call_action(
            "group_show", id=group["id"], include_users=True
        )

        assert group2["name"] == name
        assert group2["description"] == "somethingnew"
        assert len(group2["users"]) == 1
        assert group2["users"][0]["name"] == user["name"]

    def test_group_patch_preserve_datasets(self):
        user = factories.User()
        group = factories.Group(description="some test now", user=user)
        factories.Dataset(groups=[{"name": group["name"]}])

        group2 = helpers.call_action("group_show", id=group["id"])
        assert 1 == group2["package_count"]

        group = helpers.call_action(
            "group_patch", id=group["id"], context={"user": user["name"]}
        )

        group3 = helpers.call_action("group_show", id=group["id"])
        assert 1 == group3["package_count"]

        group = helpers.call_action(
            "group_patch",
            id=group["id"],
            packages=[],
            context={"user": user["name"]},
        )

        group4 = helpers.call_action(
            "group_show", id=group["id"], include_datasets=True
        )
        assert 0 == group4["package_count"]

    def test_organization_patch_updating_single_field(self):
        user = factories.User()
        organization = factories.Organization(
            description="some test now", user=user
        )
        name = organization["name"]

        organization = helpers.call_action(
            "organization_patch",
            id=organization["id"],
            description="somethingnew",
            context={"user": user["name"]},
        )

        assert organization["name"] == name
        assert organization["description"] == "somethingnew"

        organization2 = helpers.call_action(
            "organization_show", id=organization["id"]
        )

        assert organization2["name"] == name
        assert organization2["description"] == "somethingnew"

    @pytest.mark.ckan_config(u"ckan.auth.public_user_details", u"false")
    def test_organization_patch_updating_single_field_when_public_user_details_is_false(
        self,
    ):
        user = factories.User()
        organization = factories.Organization(
            description="some test now", user=user
        )
        name = organization["name"]
        organization = helpers.call_action(
            "organization_patch",
            id=organization["id"],
            description="somethingnew",
            context={"user": user["name"]},
        )

        assert organization["name"] == name
        assert organization["description"] == "somethingnew"

        organization2 = helpers.call_action(
            "organization_show", id=organization["id"], include_users=True
        )

        assert organization2["name"] == name
        assert organization2["description"] == "somethingnew"
        assert len(organization2["users"]) == 1
        assert organization2["users"][0]["name"] == user["name"]

    def test_user_patch_updating_single_field(self):
        user = factories.User(
            fullname="Mr. Test User",
            about="Just another test user.",
        )

        user = helpers.call_action(
            "user_patch",
            id=user["id"],
            about="somethingnew",
            context={"user": user["name"]},
        )

        assert user["fullname"] == "Mr. Test User"
        assert user["about"] == "somethingnew"

        user2 = helpers.call_action("user_show", id=user["id"])

        assert user2["fullname"] == "Mr. Test User"
        assert user2["about"] == "somethingnew"

    def test_extensions_successful_patch_updating_user_name(self):
        user = factories.User()

        updated_user = helpers.call_action(
            "user_patch",
            context={"user": user["name"], "ignore_auth": True},
            id=user["id"],
            name="somethingnew"
        )

        assert updated_user["name"] == "somethingnew"

        user2 = helpers.call_action("user_show", id=user["id"])

        assert user2["name"] == "somethingnew"

    def test_extensions_failed_patch_updating_user_name(self):
        user = factories.User()

        with pytest.raises(ValidationError):
            helpers.call_action(
                "user_patch",
                context={"user": user["name"], "ignore_auth": False},
                id=user["id"],
                name="somethingnew2"
            )

    def test_package_patch_for_update(self):

        dataset = factories.Dataset()

        mock_package_show = mock.MagicMock()
        mock_package_show.side_effect = lambda context, data_dict: core_package_show(context, data_dict)

        with mock.patch.dict('ckan.logic._actions', {'package_show': mock_package_show}):
            helpers.call_action('package_patch', id=dataset['id'], notes='hey')
            assert mock_package_show.call_args_list[0][0][0].get('for_update') is True

    def test_resource_patch_for_update(self):

        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset['id'])

        mock_package_show = mock.MagicMock()
        mock_package_show.side_effect = lambda context, data_dict: core_package_show(context, data_dict)

        with mock.patch.dict('ckan.logic._actions', {'package_show': mock_package_show}):
            helpers.call_action('resource_patch', id=resource['id'], description='hey')
            assert mock_package_show.call_args_list[0][0][0].get('for_update') is True

    def test_resource_patch_copies_other_resources(self):
        from ckan.lib.dictization import model_save
        res1 = factories.Resource()
        res2 = factories.Resource(
            package_id=res1['package_id'],
            url="http://data",
        )
        params = {
            "id": res2['id'],
            "url": "http://data2",
        }
        with mock.patch(
                'ckan.lib.dictization.model_save.package_dict_save',
                wraps=model_save.package_dict_save,
                ) as m:
            helpers.call_action("resource_patch", **params)
            assert m.call_args.args[3] == {0: 0}, 'res 0 unmodified'

    def test_user_patch_sysadmin(self):

        sysadmin = factories.Sysadmin()
        user = factories.User()

        # cannot change your own sysadmin privs
        with pytest.raises(ValidationError):
            helpers.call_action(
                "user_patch",
                id=sysadmin["id"],
                sysadmin=False,
                context={"user": sysadmin["name"]},
            )

        # cannot change system user privs
        site_id = config.get('ckan.site_id')
        with pytest.raises(ValidationError):
            helpers.call_action(
                "user_patch",
                id=site_id,
                sysadmin=False,
                context={"user": sysadmin["name"]},
            )

        assert user["sysadmin"] is False

        helpers.call_action(
                "user_patch",
                id=user["id"],
                sysadmin=True,
                context={"user": sysadmin["name"]},
            )

        # user dicts do not have sysadmin key, get from db
        new_sysadmin = model.User.get(user["id"])

        assert new_sysadmin.sysadmin is True

    def test_package_patch_sysadmin_can_set_date_fields(self):
        """
        Sysadmins can patch metadata_created and metadata_modified field.
        """
        user = factories.Sysadmin()
        context = {"user": user["name"], "ignore_auth": False}
        dataset = factories.Dataset(user=user)
        dataset = helpers.call_action(
            "package_patch", id=dataset["id"],
            context=context,
            metadata_modified='1994-01-01T00:00:01',
            metadata_created='1994-01-01T00:00:01',
        )

        dataset = helpers.call_action("package_show", id=dataset["id"])

        assert dataset["metadata_modified"] == "1994-01-01T00:00:01"
        assert dataset["metadata_created"] == "1994-01-01T00:00:01"

    def test_package_patch_normal_user_can_not_set_date_fields(self):
        """
        Normal users can NOT patch metadata_created and metadata_modified field.
        """
        user = factories.User()
        context = {"user": user["name"], "ignore_auth": False}
        dataset = factories.Dataset(user=user)
        dataset = helpers.call_action(
            "package_patch", id=dataset["id"],
            context=context,
            metadata_modified='1994-01-01T00:00:01',
            metadata_created='1994-01-01T00:00:01',
        )

        dataset = helpers.call_action("package_show", id=dataset["id"])

        assert dataset["metadata_modified"] != "1994-01-01T00:00:01"
        assert dataset["metadata_created"] != "1994-01-01T00:00:01"

    def test_resource_patch_sysadmin_can_set_date_fields(self):
        """
        Sysadmins can set metadata_modified field.
        """
        user = factories.Sysadmin()
        context = {"user": user["name"], "ignore_auth": False}
        resource = factories.Resource(
            package_id=factories.Dataset()["id"], user=user,
            name="A nice resource")

        resource = helpers.call_action(
            "resource_patch", id=resource["id"],
            context=context,
            created='1994-01-01T00:00:01',
            last_modified='1994-01-01T00:00:01',
            metadata_modified='1994-01-01T00:00:01',
        )

        resource = helpers.call_action("resource_show", id=resource["id"])
        assert resource["created"] == "1994-01-01T00:00:01"
        assert resource["last_modified"] == "1994-01-01T00:00:01"
        assert resource["metadata_modified"] == "1994-01-01T00:00:01"

    def test_resource_patch_normal_user_can_not_set_date_fields(self):
        """
        Normal users can set metadata_modified field.
        """
        user = factories.User()
        context = {"user": user["name"], "ignore_auth": False}
        resource = factories.Resource(
            package_id=factories.Dataset()["id"], user=user,
            name="A nice resource")

        resource = helpers.call_action(
            "resource_patch", id=resource["id"],
            context=context,
            created='1994-01-01T00:00:01',
            last_modified='1994-01-01T00:00:01',
            metadata_modified='1994-01-01T00:00:01',
        )

        resource = helpers.call_action("resource_show", id=resource["id"])
        assert resource["created"] == "1994-01-01T00:00:01"
        assert resource["last_modified"] == "1994-01-01T00:00:01"
        assert resource["metadata_modified"] != "1994-01-01T00:00:01"
