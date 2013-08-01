'''A collection of factory classes for building CKAN users, datasets, etc.

These are meant to be used by tests to create any objects or "test fixtures"
that are needed for the tests. They're written using factory_boy:

    http://factoryboy.readthedocs.org/en/latest/

These are not meant to be used for the actual testing, e.g. if you're writing a
test for the user_create action function then call user_create, don't test it
via the User factory below.

Usage:

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

import ckan.model
import ckan.logic
import ckan.new_tests.helpers as helpers


def generate_email(user):
    '''Return an email address for the given User factory stub object.'''

    return '{0}@ckan.org'.format(user.name).lower()


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
    email = factory.LazyAttribute(generate_email)

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
