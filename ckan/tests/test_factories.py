import pytest
from faker import Faker

import ckan.tests.factories as factories
from ckan import model, types


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
@pytest.mark.usefixtures("non_clean_db")
def test_id_uniqueness(entity):
    first, second = entity(), entity()
    assert first["id"] != second["id"]


# START-CONFIG-OVERRIDE
@pytest.mark.ckan_config("ckan.plugins", "image_view")
@pytest.mark.usefixtures("non_clean_db", "with_plugins")
def test_resource_view_factory():
    resource_view1 = factories.ResourceView()
    resource_view2 = factories.ResourceView()
    assert resource_view1["id"] != resource_view2["id"]


# END-CONFIG-OVERRIDE


@pytest.mark.usefixtures("non_clean_db")
def test_dataset_factory_allows_creation_by_anonymous_user():
    dataset = factories.Dataset(user=None)
    assert dataset["creator_user_id"] is None


@pytest.mark.usefixtures("non_clean_db")
def test_factory_model(package_factory: types.TestFactory, faker: Faker):
    """Factory can create a model object instead of a dictionary."""
    notes = faker.sentence()
    package = package_factory.model(notes=notes)
    assert isinstance(package, model.Package)
    assert package.notes == notes


class UserFollowFactoryWithKey(factories.CKANFactory):
    class Meta:
        model = model.UserFollowingUser
        action = "follow_user"
        primary_key = ("follower_id", "object_id")


class UserFollowFactoryWithoutKey(factories.CKANFactory):
    class Meta:
        model = model.UserFollowingUser
        action = "follow_user"


@pytest.mark.usefixtures("non_clean_db")
def test_factory_model_with_explicit_composite_key(user_factory: types.TestFactory):
    """Factory can create a model object with a composite primary key.

    In this case, the UserFollowingUser model has a composite primary key
    consisting of follower_id and object_id.
    """
    john = user_factory()
    jane = user_factory()

    result = UserFollowFactoryWithKey.model(id=john["id"], user=jane)
    assert isinstance(result, model.UserFollowingUser)
    assert result.object_id == john["id"]
    assert result.follower_id == jane["id"]


@pytest.mark.usefixtures("non_clean_db")
def test_factory_model_with_implicit_composite_key(user_factory: types.TestFactory):
    """If primary key is not specified, factory will guess it."""
    john = user_factory()
    jane = user_factory()

    result = UserFollowFactoryWithoutKey.model(id=john["id"], user=jane)
    assert isinstance(result, model.UserFollowingUser)
    assert result.object_id == john["id"]
    assert result.follower_id == jane["id"]
