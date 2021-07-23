# encoding: utf-8

import pytest

import ckan.tests.factories as factories

@pytest.mark.parametrize(
    u"entity",
    [
        factories.UserFactory,
        factories.ResourceFactory,
        factories.SysadminFactory,
        factories.GroupFactory,
        factories.OrganizationFactory,
        factories.DatasetFactory,
        factories.MockUserFactory,
    ],
)
@pytest.mark.usefixtures("clean_db", "with_request_context")
def test_id_uniqueness(entity):
    first, second = entity(), entity()
    assert first[u"id"] != second[u"id"]


# START-CONFIG-OVERRIDE
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("clean_db", "with_plugins")
def test_resource_view_factory(resource_view_factory):
    resource_view1 = resource_view_factory()
    resource_view2 = resource_view_factory()
    assert resource_view1[u"id"] != resource_view2[u"id"]


# END-CONFIG-OVERRIDE

def test_dataset_factory_allows_creation_by_anonymous_user(dataset_factory):
    dataset = dataset_factory(user=None)
    assert dataset[u"creator_user_id"] is None
