'''Discovery of CKAN form plug-ins.
'''
import pkg_resources
from pylons import config

PACKAGE_FORM_KEY = 'package_form'
GROUP_FORM_KEY = 'group_form'
PACKAGE_GROUP_FORM_KEY = 'package_group_form'

__all__ = ['get_package_fieldset', 'get_group_fieldset', 'get_package_group_fieldset']

def get_entrypoints():
    entrypoints = []
    for en in pkg_resources.iter_entry_points('ckan.forms'):
        entrypoints.append(en)
    return entrypoints
#print get_entrypoints()   #[0].load()

def get_package_fieldset(package_form=None, **kwargs):
    return get_fieldset(package_form, PACKAGE_FORM_KEY, 'package', **kwargs)

def get_group_fieldset(group_form=None, **kwargs):
    return get_fieldset(group_form, GROUP_FORM_KEY, 'group', **kwargs)
    
def get_package_group_fieldset(package_group_form=None, **kwargs):
    return get_fieldset(package_group_form, PACKAGE_GROUP_FORM_KEY, 'package_group')

def get_fieldset(form, config_key, fallback, **kwargs):
    ''' Returns the appropriate fieldset.
    The form it uses is the form parameter, or failing that it looks in the
    config under the config_key, or finally it tries the fallback parameter.
    @param form: name of the form to use by default
    @param config_key: config file key specifying the form name if
                       not specified in form parameter.
    @param fallback: name of the form to use as final fallback.
    @param is_admin: whether user has admin rights for this package.
    @param package_form: form name. Default taken from the config file.
    '''
    fs = None
    if not form:
        form = config.get(config_key)
    if not form:
        form = fallback
    entrypoints = get_entrypoints()
    for entrypoint in entrypoints:
        if entrypoint.name == form:
            fs = entrypoint.load()(**kwargs)
    if fs is None:
        raise ValueError('Could not find form name %r in those found: \n%r' % (form, [en.name for en in entrypoints]))
    return fs
