'''A collection of test helper functions.

'''
import ckan.model as model
import ckan.logic as logic


def reset_db():
    '''Reset CKAN's database.

    Each test module or class should call this function in its setup method.

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
