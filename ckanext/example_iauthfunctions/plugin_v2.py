import ckan.plugins as plugins


def group_create(context, data_dict=None):
    return {'success': False, 'msg': 'No one is allowed to create groups'}


class ExampleIAuthFunctionsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IAuthFunctions)

    def get_auth_functions(self):
        return {'group_create': group_create}
