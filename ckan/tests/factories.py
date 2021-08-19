# encoding: utf-8

"""This is a collection of factory classes for building CKAN users, datasets,
etc.

These are not meant to be used by tests directly. Instead, use corresponding
pytest fixture to create any objects that are needed for the tests. These
factories are written using ``factory_boy``:

https://factoryboy.readthedocs.org/en/latest/

These are not meant to be used for the actual testing, e.g. if you're writing a
test for the :py:func:`~ckan.logic.action.create.user_create` function then
call :py:func:`~ckan.tests.helpers.call_action`, don't test it via the
:py:class:`~ckan.tests.factories.UserFactory` factory or
:py:func:`~ckan.tests.pytest_ckan.fixtures.user_factory` fixture.

Usage::

 # Create a user with the factory's default attributes, and get back a
 # user dict:
 def test_creation(user_factory):
     user_dict = user_factory()

 # You can create a second user the same way. For attributes that can't be
 # the same (e.g. you can't have two users with the same name) a new value
 # will be generated each time you use the factory:
 def test_creation(user_factory):
     user_dict = user_factory()
     another_user_dict = user_factory()

 # Create a user and specify your own user name and email (this works
 # with any params that CKAN's user_create() accepts):
 def test_creation(user_factory):
     custom_user_dict = user_factory(name='bob', email='bob@bob.com')

 # Get a user dict containing the attributes (name, email, password, etc.)
 # that the factory would use to create a user, but without actually
 # creating the user in CKAN:
 def test_creation(user_factory):
     user_attributes_dict = vars(user_factory.stub())

 # If you later want to create a user using these attributes, just pass them
 # to the factory:
 def test_creation(user_factory):
     user = user_factory(**user_attributes_dict)

 # If you just need random user, you can get ready-to-use dictionary inside
 # your test by requiring `user` fixture (just drop `_factory` suffix):
 def test_creation(user):
     assert isinstance(user, dict)
     assert "name" in user

 # If you need SQLAlchemy model object instead of the plain dictionary, call
 # `model` method of the corresponding factory. All arguments has the same
 # effect as if they were passed directly to the factory:
 def test_creation(user_factory):
     user = user_factory.model(name="bob")
     assert isinstance(user, model.User)


 # In order to create your own factory:
 # * inherit from :py:class:`~ckan.tests.factories.CKANFactory`
 # * create `Meta` class inside it, with the two properties:
 #   * model: corresponding SQLAlchemy model
 #   * action: API action that can create instances of the model
 # * define any extra attributes
 # * register factory as a fixture using :py:func:`~pytest_factoryboy.register`
 import factory
 from pytest_factoryboy import register
 from ckan.tests.factories import CKANFactory

 @register
 class RatingFactory(CKANFactory):

     class Meta:
         model = ckanext.ext.model.Rating
         action = "rating_create"

     # These are the default params that will be used to create new ratings
     value = factory.Faker("pyint")
     comment = factory.Faker("text")
     approved = factory.Faker("boolean")

Factory-fixtures are generated using ``pytest-factoryboy``:

https://pytest-factoryboy.readthedocs.io/en/latest/

"""
import string
import factory
import unittest.mock as mock

import ckan.model
import ckan.logic
import ckan.tests.helpers as helpers
from ckan.lib.maintain import deprecated


def _get_action_user_name(kwargs):
    """Return the name of the user in kwargs, defaulting to the site user

    It can be overriden by explictly setting {'user': None} in the keyword
    arguments. In that case, this method will return None.
    """

    if "user" in kwargs:
        user = kwargs["user"]
    else:
        user = helpers.call_action("get_site_user")

    if user is None:
        user_name = None
    else:
        user_name = user["name"]

    return user_name


def _generate_reset_key(user):
    """Return a reset key for the given User factory stub object."""

    return "{0}_reset_key".format(user.name).lower()


def _name(type_):
    return factory.Faker(
        "pystr_format",
        string_format=type_ + "-????-####-????",
        letters=string.ascii_lowercase,
    )


class CKANOptions(factory.alchemy.SQLAlchemyOptions):
    """CKANFactory options.

    :param action: name of the CKAN API action used for entity creation
    :param primary_key: name of the entity's property that can be used for retriving
        entity object from database

    """

    def _build_default_options(self):
        return super()._build_default_options() + [
            factory.base.OptionDefault("action", None, inherit=True),
            factory.base.OptionDefault("primary_key", "id", inherit=True),
        ]


class CKANFactory(factory.alchemy.SQLAlchemyModelFactory):
    """Extension of SQLAlchemy factory.

    Creates entities via CKAN API using an action specified by the
    `Meta.action`.

    Provides ``model`` method that returns created model object instead of the
    plain dictionary.

    Check factoryboy's documentation for more details:
    https://factoryboy.readthedocs.io/en/stable/orms.html#sqlalchemy

    """

    _options_class = CKANOptions

    class Meta:
        sqlalchemy_session = ckan.model.Session

    @classmethod
    def _api_prepare_args(cls, data_dict):
        """Add any extra details to pass into the action on the entity create stage."""
        if "context" not in data_dict:
            data_dict["context"] = {"user": _get_action_user_name(data_dict)}
        return data_dict

    @classmethod
    def _api_postprocess_result(cls, result):
        """Modify result before returning it to the consumer."""
        return result

    @classmethod
    def api_create(cls, data_dict):
        """Create entity via API call."""
        data_dict = cls._api_prepare_args(data_dict)
        result = helpers.call_action(cls._meta.action, **data_dict)
        return cls._api_postprocess_result(result)

    @classmethod
    def model(cls, **kwargs):
        """Create entity via API and retrive result directly from the DB."""
        result = cls(**kwargs)
        return cls._meta.sqlalchemy_session.query(cls._meta.model).get(
            result[cls._meta.primary_key]
        )

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Replace default entity creation strategy(DB)."""
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        return cls.api_create(kwargs)


class UserFactory(CKANFactory):
    """A factory class for creating CKAN users.

    Prefer using ``user_factory`` and ``user`` fixtures.
    """

    class Meta:
        model = ckan.model.User
        action = "user_create"

    # These are the default params that will be used to create new users.
    fullname = factory.Faker("name")
    password = factory.Faker("password")
    about = factory.Faker("text")
    image_url = factory.Faker("image_url")
    name = factory.Faker("user_name")
    email = factory.Faker("email", domain="ckan.example.com")
    reset_key = None
    sysadmin = False


class ResourceFactory(CKANFactory):
    """A factory class for creating CKAN resources.

    Prefer using ``resource_factory`` and ``resource`` fixtures.
    """

    class Meta:
        model = ckan.model.Resource
        action = "resource_create"

    name = _name("resource")
    description = factory.Faker("text")
    format = factory.Faker("file_extension")
    url = factory.Faker("url")
    package_id = factory.LazyFunction(lambda: PackageFactory()["id"])


class ResourceViewFactory(CKANFactory):
    """A factory class for creating CKAN resource views.

    Note: if you use this factory, you need to load the `image_view` plugin
    on your test class (and unload it later), otherwise you will get an error.

    Example::

        @pytest.mark.ckan_config("ckan.plugins", "image_view")
        @pytest.mark.usefixtures("with_plugins")
        def test_resource_view_factory():
            ...

    Prefer using ``resource_view_factory`` and ``resource_view`` fixtures.
    """

    class Meta:
        model = ckan.model.ResourceView
        action = "resource_view_create"

    title = _name("resource-view")
    description = factory.Faker("text")
    view_type = "image_view"
    resource_id = factory.LazyFunction(lambda: ResourceFactory()["id"])


class SysadminFactory(UserFactory):
    """A factory class for creating sysadmin users.

    Prefer using ``sysadmin_factory`` and ``sysadmin`` fixtures.
    """

    sysadmin = True

    # user_dict = helpers.call_action(
    #     "user_show", id=user.id, context={"user": user.name}
    # )


class GroupFactory(CKANFactory):
    """A factory class for creating CKAN groups.

    Prefer using ``group_factory`` and ``group`` fixtures.
    """

    class Meta:
        model = ckan.model.Group
        action = "group_create"

    name = _name("group")
    title = factory.Faker("company")

    description = factory.Faker("text")
    image_url = factory.Faker("image_url")

    # user = factory.LazyAttribute(
    #     lambda _: helpers.call_action("get_site_user")
    # )


class OrganizationFactory(GroupFactory):
    """A factory class for creating CKAN organizations.

    Prefer using ``organization_factory`` and ``organization`` fixtures.
    """

    class Meta:
        action = "organization_create"

    name = _name("organization")
    is_organization = True
    type = "organization"


class PackageFactory(CKANFactory):
    """A factory class for creating CKAN datasets.

    Prefer using ``package_factory`` and ``package`` fixtures.
    """

    class Meta:
        model = ckan.model.Package
        action = "package_create"

    name = _name("dataset")
    title = factory.Faker("sentence", nb_words=5)
    notes = factory.Faker("text")



class VocabularyFactory(CKANFactory):
    """A factory class for creating tag vocabularies.

    Prefer using ``vocabulary_factory`` and ``vocabulary`` fixtures.
    """

    class Meta:
        model = ckan.model.Vocabulary
        action = "vocabulary_create"

    name = _name("vocabulary")


class ActivityFactory(CKANFactory):
    """A factory class for creating CKAN activity objects.

    Prefer using ``activity_factory`` and ``activity`` fixtures.
    """

    class Meta:
        model = ckan.model.Activity
        action = "activity_create"


class MockUserFactory(factory.Factory):
    """A factory class for creating mock CKAN users using the mock library.

    Prefer using ``mock_user_factory`` fixture.
    """

    class Meta:
        model = mock.MagicMock

    fullname = "Mr. Mock User"
    password = "pass"
    about = "Just another mock user."
    name = factory.Sequence(lambda n: "mock_user_{0:02d}".format(n))
    email = factory.Faker("safe_email")
    reset_key = factory.LazyAttribute(_generate_reset_key)
    id = factory.Faker("uuid4")

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."
        mock_user = mock.MagicMock()
        for name, value in kwargs.items():
            setattr(mock_user, name, value)
        return mock_user


class SystemInfoFactory(factory.alchemy.SQLAlchemyModelFactory):
    """A factory class for creating SystemInfo objects (config objects
    stored in the DB).

    Prefer using ``system_info_factory`` and ``system_info`` fixtures.
    """

    class Meta:
        model = ckan.model.SystemInfo

    key = factory.Sequence(lambda n: "test_config_{0:02d}".format(n))
    value = factory.Faker("pystr")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        ckan.model.system_info.set_system_info(kwargs["key"], kwargs["value"])
        obj = (
            ckan.model.Session.query(ckan.model.system_info.SystemInfo)
            .filter_by(key=kwargs["key"])
            .first()
        )

        return obj


class APIToken(factory.Factory):
    """A factory class for creating CKAN API Tokens"""

    class Meta:
        model = ckan.model.ApiToken

    name = "first token"

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        target_user_name = _get_action_user_name(kwargs)
        context = {"user": target_user_name}
        kwargs["user"] = target_user_name

        token_create = helpers.call_action(
            'api_token_create', context=context, **kwargs
        )
        return token_create["token"]


@deprecated(since="2.10.0")
class User(UserFactory):
    """Deprecated. Use UserFactory instead.
    """
    pass


@deprecated(since="2.10.0")
class Resource(ResourceFactory):
    """Deprecated. Use resource_factory pytest fixture instead.

    """
    pass


@deprecated(since="2.10.0")
class ResourceView(ResourceViewFactory):
    """Deprecated. Use resource_view_factory pytest fixture instead.

    """
    pass


@deprecated(since="2.10.0")
class Sysadmin(SysadminFactory):
    """Deprecated. Use sysadmin_factory pytest fixture instead.

    """
    pass


@deprecated(since="2.10.0")
class Group(GroupFactory):
    """Deprecated. Use group_factory pytest fixture instead.

    """
    pass


@deprecated(since="2.10.0")
class Organization(OrganizationFactory):
    """Deprecated. Use organization_factory pytest fixture instead.

    """
    pass


@deprecated(since="2.10.0")
class Dataset(PackageFactory):
    """Deprecated. Use package_factory pytest fixture instead.

    """
    pass


@deprecated(since="2.10.0")
class MockUser(MockUserFactory):
    """Deprecated. Use mock_user_factory pytest fixture instead.

    """
    pass


@deprecated(since="2.10.0")
class Activity(ActivityFactory):
    """Deprecated. Use activity_factory pytest fixture instead.

    """
    pass


@deprecated(since="2.10.0")
class SystemInfo(SystemInfoFactory):
    """Deprecated. Use system_info_factory pytest fixture instead.

    """
    pass


@deprecated(since="2.10.0")
class Vocabulary(VocabularyFactory):
    """Deprecated. Use vocabulary_factory pytest fixture instead.

    """
    pass
