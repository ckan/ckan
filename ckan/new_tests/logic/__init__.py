'''Some wrappers.'''
import ckan.logic as logic


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
    deprecated. ckan.tests.logic.action  may still need its own wrapper
    function, e.g. to insert 'ignore_auth': True into the context.

    '''
    if context is None:
        context = {}
    context.setdefault('user', '127.0.0.1')
    context.setdefault('ignore_auth', True)
    return logic.get_action(action_name)(context=context, data_dict=kwargs)
