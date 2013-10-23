'''This is a collection of helper functions for use in tests.

We want to avoid sharing test helper functions between test modules as
much as possible, and we definitely don't want to share test fixtures between
test modules, or to introduce a complex hierarchy of test class subclasses,
etc.

We want to reduce the amount of "travel" that a reader needs to undertake to
understand a test method -- reducing the number of other files they need to go
and read to understand what the test code does. And we want to avoid tightly
coupling test modules to each other by having them share code.

But some test helper functions just increase the readability of tests so much
and make writing tests so much easier, that it's worth having them despite the
potential drawbacks.

This module is reserved for these very useful functions.

'''
import ckan.model as model
import ckan.logic as logic


def reset_db():
    '''Reset CKAN's database.

    If a test class uses the database, then it should call this function in its
    ``setup()`` method to make sure that it has a clean database to start with
    (nothing left over from other test classes or from previous test runs).

    If a test class doesn't use the database (and most test classes shouldn't
    need to) then it doesn't need to call this function.

    :returns: ``None``

    '''
    # Close any database connections that have been left open.
    # This prevents CKAN from hanging waiting for some unclosed connection.
    model.Session.close_all()

    model.repo.rebuild_db()


def call_action(action_name, context=None, **kwargs):
    '''Call the named ``ckan.logic.action`` function and return the result.

    For example::

        user_dict = call_action('user_create', name='seanh',
                                email='seanh@seanh.com', password='pass')

    Any keyword arguments given will be wrapped in a dict and passed to the
    action function as its ``data_dict`` argument.

    This is just a nicer way for user code to call action functions, nicer than
    either calling the action function directly or via
    :py:func:`ckan.logic.get_action`.

    This function should eventually be moved to
    :py:func:`ckan.logic.call_action` and the current
    :py:func:`ckan.logic.get_action` function should be
    deprecated. The tests may still need their own wrapper function for
    :py:func:`ckan.logic.call_action`, e.g. to insert ``'ignore_auth': True``
    into the ``context`` dict.

    :param action_name: the name of the action function to call, e.g.
        ``'user_update'``
    :type action_name: string
    :param context: the context dict to pass to the action function
        (optional, if no context is given a default one will be supplied)
    :type context: dict
    :returns: the dict or other value that the action function returns

    '''
    if context is None:
        context = {}
    context.setdefault('user', '127.0.0.1')
    context.setdefault('ignore_auth', True)
    return logic.get_action(action_name)(context=context, data_dict=kwargs)


def call_auth(auth_name, context, **kwargs):
    '''Call the named ``ckan.logic.auth`` function and return the result.

    This is just a convenience function for tests in
    :py:mod:`ckan.new_tests.logic.auth` to use.

    Usage::

        result = helpers.call_auth('user_update', context=context,
                                   id='some_user_id',
                                   name='updated_user_name')

    :param auth_name: the name of the auth function to call, e.g.
        ``'user_update'``
    :type auth_name: string

    :param context: the context dict to pass to the auth function, must
        contain ``'user'`` and ``'model'`` keys,
        e.g. ``{'user': 'fred', 'model': my_mock_model_object}``
    :type context: dict

    :returns: the dict that the auth function returns, e.g.
        ``{'success': True}`` or ``{'success': False, msg: '...'}``
        or just ``{'success': False}``
    :rtype: dict

    '''
    import ckan.logic.auth.update

    assert 'user' in context, ('Test methods must put a user name in the '
                               'context dict')
    assert 'model' in context, ('Test methods must put a model in the '
                                'context dict')

    # FIXME: Do we want to go through check_access() here?
    auth_function = ckan.logic.auth.update.__getattribute__(auth_name)
    return auth_function(context=context, data_dict=kwargs)
