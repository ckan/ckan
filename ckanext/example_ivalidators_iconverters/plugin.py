from ckan.plugins import toolkit
from ckan import plugins

class ExampleIValidatorsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IValidators)

    def get_validators(self):
        return {
            'equals_fortytwo': equals_fortytwo,
            }


class ExampleIConvertersPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConverters)

    def get_converters(self):
        return {
            'negate': negate,
            }

def equals_fortytwo(value):
    if value != 42:
        raise toolkit.Invalid('not 42')
    return value


def negate(value):
    return -value
