'''A collection of test helper functions.

'''
import ckan.model as model
import ckan.logic as logic


def reset_db():
    '''Reset CKAN's database.

    If a test class uses the database, then it should call this function in
    its setup() method to make sure that it has a clean database to start with
    (nothing left over from other test classes or from previous test runs).

    If a test class doesn't use the database (and most test classes shouldn't
    need to) then it doesn't need to call this function.

    '''
    # Close any database connections that have been left open.
    # This prevents CKAN from hanging waiting for some unclosed connection.
    model.Session.close_all()

    # Clean out any data from the db. This prevents tests failing due to data
    # leftover from other tests or from previous test runs.
    model.repo.clean_db()

    # Initialize the db. This prevents CKAN from crashing if the tests are run
    # and the test db has not been initialized.
    model.repo.init_db()


def call_action(action_name, context=None, **kwargs):
    '''Call the given ckan.logic.action function with the given context
    and params.

    For example:

        call_action('user_create', name='seanh', email='seanh@seanh.com',
                    password='pass')

    This is just a nicer way for user code to call action functions, nicer than
    either calling the action function directly or via get_action().

    If accepted this function should eventually be moved to
    ckan.logic.call_action() and the current get_action() function should be
    deprecated. The tests may still need their own wrapper function for
    logic.call_action(), e.g. to insert 'ignore_auth': True into the context.

    '''
    if context is None:
        context = {}
    context.setdefault('user', '127.0.0.1')
    context.setdefault('ignore_auth', True)
    return logic.get_action(action_name)(context=context, data_dict=kwargs)


def call_auth(auth_name, context, **kwargs):
    '''Call a ckan.logic.auth function and return the result.

    This is just a convenience function for tests in
    ckan.new_tests.logic.auth to use.

    Usage:

        result = self._call_auth('user_update', context=context,
                                    id='some_user_id',
                                    name='updated_user_name')

    :param auth_name: the name of the auth function to call, e.g.
        ``'user_update'``
    :type auth_name: string

    :param context: the context dict to pass to the auth function, must
        contain 'user' and 'model' keys,
        e.g. ``{'user': 'fred', 'model': my_mock_model_object}``
    :type context: dict

    :param kwargs: any arguments to be passed to the auth function, these
        will be wrapped in a dict and passed to the auth function as its
        ``data_dict`` argument

    :type kwargs: keyword arguments

    '''
    import ckan.logic.auth.update

    assert 'user' in context, ('Test methods must put a user name in the '
                               'context dict')
    assert 'model' in context, ('Test methods must put a model in the '
                                'context dict')

    # FIXME: Do we want to go through check_access() here?
    auth_function = ckan.logic.auth.update.__getattribute__(auth_name)
    return auth_function(context=context, data_dict=kwargs)
