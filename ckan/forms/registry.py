'''Discovery of CKAN form plug-ins.
'''
import pkg_resources
from pylons import config

PACKAGE_FORM_KEY = 'package_form'

__all__ = ['get_fieldset']

def get_entrypoints():
    entrypoints = []
    for en in pkg_resources.iter_entry_points('ckan.forms'):
        entrypoints.append(en)
    return entrypoints
#print get_entrypoints()   #[0].load()

def get_fieldset(is_admin=False, package_form=None):
    ''' Returns the appropriate fieldset
    @param is_admin: whether user has admin rights for this package
    @param package_form: form name. Default taken from the config file.
    '''
    fs = None
    if not package_form:
        package_form = config.get(PACKAGE_FORM_KEY)
    if not package_form:
        package_form = 'standard'
    entrypoints = get_entrypoints()
    for entrypoint in entrypoints:
        if entrypoint.name == package_form:
            fs = entrypoint.load()(is_admin)
    if not fs:
        raise ValueError('Could not find package_form name %r in those found: \n%r' % (package_form, [en.name for en in entrypoints]))
    return fs
