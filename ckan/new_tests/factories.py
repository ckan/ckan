'''This is a collection of factory classes for building CKAN users, datasets,
etc.

These are meant to be used by tests to create any objects that are needed for
the tests. They're written using ``factory_boy``:

http://factoryboy.readthedocs.org/en/latest/

These are not meant to be used for the actual testing, e.g. if you're writing a
test for the :py:func:`~ckan.logic.action.create.user_create` function then
call :py:func:`~ckan.new_tests.helpers.call_action`, don't test it
via the :py:class:`~ckan.new_tests.factories.User` factory below.

Usage::

 # Create a user with the factory's default attributes, and get back a
 # user dict:
 user_dict = factories.User()

 # You can create a second user the same way. For attributes that can't be
 # the same (e.g. you can't have two users with the same name) a new value
 # will be generated each time you use the factory:
 another_user_dict = factories.User()

 # Create a user and specify your own user name and email (this works
 # with any params that CKAN's user_create() accepts):
 custom_user_dict = factories.User(name='bob', email='bob@bob.com')

 # Get a user dict containing the attributes (name, email, password, etc.)
 # that the factory would use to create a user, but without actually
 # creating the user in CKAN:
 user_attributes_dict = factories.User.attributes()

 # If you later want to create a user using these attributes, just pass them
 # to the factory:
 user = factories.User(**user_attributes_dict)

'''
import factory
import mock

import ckan.model
import ckan.logic
import ckan.new_tests.helpers as helpers


def _generate_email(user):
    '''Return an email address for the given User factory stub object.'''

    return '{0}@ckan.org'.format(user.name).lower()


def _generate_reset_key(user):
    '''Return a reset key for the given User factory stub object.'''

    return '{0}_reset_key'.format(user.name).lower()


def _generate_user_id(user):
    '''Return a user id for the given User factory stub object.'''

    return '{0}_user_id'.format(user.name).lower()


class User(factory.Factory):
    '''A factory class for creating CKAN users.'''

    # This is the class that UserFactory will create and return instances
    # of.
    FACTORY_FOR = ckan.model.User

    # These are the default params that will be used to create new users.
    fullname = 'Mr. Test User'
    password = 'pass'
    about = 'Just another test user.'

    # Generate a different user name param for each user that gets created.
    name = factory.Sequence(lambda n: 'test_user_{n}'.format(n=n))

    # Compute the email param for each user based on the values of the other
    # params above.
    email = factory.LazyAttribute(_generate_email)

    # I'm not sure how to support factory_boy's .build() feature in CKAN,
    # so I've disabled it here.
    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    # To make factory_boy work with CKAN we override _create() and make it call
    # a CKAN action function.
    # We might also be able to do this by using factory_boy's direct SQLAlchemy
    # support: http://factoryboy.readthedocs.org/en/latest/orms.html#sqlalchemy
    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."
        user_dict = helpers.call_action('user_create', **kwargs)
        return user_dict


class Group(factory.Factory):
    '''A factory class for creating CKAN groups.'''

    # This is the class that GroupFactory will create and return instances
    # of.
    FACTORY_FOR = ckan.model.Group

    # These are the default params that will be used to create new groups.
    type = 'group'
    is_organization = False

    title = 'Test Group'
    description = 'Just another test group.'
    image_url = 'http://placekitten.com/g/200/200'

    # Generate a different group name param for each user that gets created.
    name = factory.Sequence(lambda n: 'test_group_{n}'.format(n=n))

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        #TODO: we will need to be able to define this when creating the
        #      instance perhaps passing a 'user' param?
        context = {
            'user': helpers.call_action('get_site_user')['name']
        }

        group_dict = helpers.call_action('group_create',
                                         context=context,
                                         **kwargs)
        return group_dict


class Organization(factory.Factory):
    '''A factory class for creating CKAN organizations.'''

    # This is the class that OrganizationFactory will create and return
    # instances of.
    FACTORY_FOR = ckan.model.Group

    # These are the default params that will be used to create new
    # organizations.
    type = 'organization'
    is_organization = True

    title = 'Test Organization'
    description = 'Just another test organization.'
    image_url = 'http://placekitten.com/g/200/100'

    # Generate a different group name param for each user that gets created.
    name = factory.Sequence(lambda n: 'test_org_{n}'.format(n=n))

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        #TODO: we will need to be able to define this when creating the
        #      instance perhaps passing a 'user' param?
        context = {
            'user': helpers.call_action('get_site_user')['name']
        }

        group_dict = helpers.call_action('organization_create',
                                         context=context,
                                         **kwargs)
        return group_dict


class MockUser(factory.Factory):
    '''A factory class for creating mock CKAN users using the mock library.'''

    FACTORY_FOR = mock.MagicMock

    fullname = 'Mr. Mock User'
    password = 'pass'
    about = 'Just another mock user.'
    name = factory.Sequence(lambda n: 'mock_user_{n}'.format(n=n))
    email = factory.LazyAttribute(_generate_email)
    reset_key = factory.LazyAttribute(_generate_reset_key)
    id = factory.LazyAttribute(_generate_user_id)

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


def validator_data_dict():
    '''Return a data dict with some arbitrary data in it, suitable to be passed
    to validator functions for testing.

    '''
    return {('other key',): 'other value'}


def validator_errors_dict():
    '''Return an errors dict with some arbitrary errors in it, suitable to be
    passed to validator functions for testing.

    '''
    return {('other key',): ['other error']}
