# encoding: utf-8

import pytest

import ckan.tests.factories as factories


@pytest.fixture(scope="module", autouse=True)
def cleanup(reset_db):
    """Reset DB only once, because there are no updates in this module, so
    thests won't become statefull.
    """
    reset_db()


@pytest.mark.parametrize(
    "entity",
    [
        factories.User,
        factories.Resource,
        factories.Sysadmin,
        factories.Group,
        factories.Organization,
        factories.Dataset,
        factories.MockUser,
    ],
)
@pytest.mark.usefixtures("with_request_context")
def test_id_uniqueness(entity):
    first, second = entity(), entity()
    assert first["id"] != second["id"]


# START-CONFIG-OVERRIDE
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("with_plugins")
def test_resource_view_factory():
    resource_view1 = factories.ResourceView()
    resource_view2 = factories.ResourceView()
    assert resource_view1["id"] != resource_view2["id"]


# END-CONFIG-OVERRIDE


def test_dataset_factory_allows_creation_by_anonymous_user():
    dataset = factories.Dataset(user=None)
    assert dataset["creator_user_id"] is None
