import os
import re

from pylons import config

_template_info_cache = {}

def find_template(template_name):
    ''' looks through the possible template paths to find a template
    returns the full path is it exists. '''
    template_paths = config['pylons.app_globals'].template_paths
    for path in template_paths:
        if os.path.exists(os.path.join(path, template_name)):
            return os.path.join(path, template_name)

def template_type(template_path):
    ''' returns best guess for template type
    returns 'jinja2', 'genshi', 'genshi-text' '''
    if template_path.endswith('.txt'):
        return 'genshi-text'
    f = open(template_path, 'r')
    source = f.read()
    if re.search('genshi\.edgewall\.org', source):
        return 'genshi'
    return 'jinja2'

def template_info(template_name):
    ''' Returns the path and type for a template '''

    if template_name in _template_info_cache:
        t_data = _template_info_cache[template_name]
        return t_data['template_type'], t_data['template_type']

    template_path = find_template(template_name)
    if not template_path:
        raise Exception('Template %s cannot be found' % template_name)
    t_type = template_type(template_path)

    t_data = {'template_path' : template_path,
              'template_type' : t_type,}
    _template_info_cache[template_name] = t_data
    return template_path, t_type
