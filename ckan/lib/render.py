import os
import re

from pylons import config

_template_info_cache = {}

def reset_template_info_cache():
    '''Reset the template cache'''
    _template_info_cache.clear()

def find_template(template_name):
    ''' looks through the possible template paths to find a template
    returns the full path is it exists. '''
    template_paths = config['pylons.app_globals'].template_paths
    for path in template_paths:
        if os.path.exists(os.path.join(path, template_name.encode('utf-8'))):
            return os.path.join(path, template_name)

def template_type(template_path):
    ''' returns best guess for template type
    returns 'jinja2', 'genshi', 'genshi-text' '''
    if template_path.endswith('.txt'):
        return 'genshi-text'
    try:
        f = open(template_path, 'r')
    except IOError:
        # do the import here due to circular import hell functions like
        # abort should be in a none circular importing file but that
        # refactor has not yet happened
        import ckan.lib.base as base
        base.abort(404)
    source = f.read()
    f.close()
    if re.search('genshi\.edgewall\.org', source):
        return 'genshi'
    return 'jinja2'

class TemplateNotFound(Exception):
    pass

def template_info(template_name):
    ''' Returns the path and type for a template '''

    if template_name in _template_info_cache:
        t_data = _template_info_cache[template_name]
        return t_data['template_path'], t_data['template_type']

    template_path = find_template(template_name)
    if not template_path:
        raise TemplateNotFound('Template %s cannot be found' % template_name)
    t_type = template_type(template_path)

    # if in debug mode we always want to search for templates so we
    # don't want to store it.
    if not config.get('debug', False):
        t_data = {'template_path' : template_path,
                  'template_type' : t_type,}
        _template_info_cache[template_name] = t_data
    return template_path, t_type
