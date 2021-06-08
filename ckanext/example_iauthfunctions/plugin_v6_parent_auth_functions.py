# encoding: utf-8

import ckan.plugins as plugins


def package_delete(context, data_dict=None):
    return {'success': False,
            'msg': 'Only sysadmins can delete packages'}


class ExampleIAuthFunctionsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IAuthFunctions)

    def get_auth_functions(self):
        return {'package_delete': package_delete}
